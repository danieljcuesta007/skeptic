"""Authenticated fixture-only Unix socket observation/control interface.

Listener lifetime is independent of clients and desktop windows. No provider launch.
"""
from pathlib import Path
import argparse,fcntl,hmac,json,os,secrets,socket,stat,threading,time
import checkpoints as c
import checkpoint_writer as writer
import continuity_service as state
import recovery_contract as recovery
REQUEST_LIMIT=16384
RESPONSE_LIMIT=512*1024

def private_root(root):
 p=Path(root)
 if p.is_symlink():raise c.Rejected('Symlink service root refused')
 p=writer.fixture(p);s=p.stat()
 if s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=0o700:raise c.Rejected('Owner-only fixture directory required')
 return p

def authenticate_file(fd):
 s=os.fstat(fd)
 if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1 or s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=0o600:raise c.Rejected('Unsafe service file')

class Engine:
 def __init__(self,packages):
  if not isinstance(packages,list) or len(packages)>32:raise c.Rejected('Bounded fixture package list required')
  self.packages={};self.paused=False;self.stopping=False;self.lock=threading.RLock()
  for p in packages:
   private=c.markdown(p);writer.fixture(p['snapshot']['root']);writer.fixture(p['snapshot']['canonical_root'])
   if p['session'] in self.packages:raise c.Rejected('Duplicate session identity')
   self.packages[p['session']]=p
 def request(self,request):
  if not isinstance(request,dict) or not isinstance(request.get('op'),str):raise c.Rejected('Structured operation required')
  op=request['op'];scope={'op'} if op in ('health','observe','sessions','pause','resume','shutdown') else {'op','session'} if op in ('checkpoint','evidence') else {'op','session','destination'} if op=='prepare' else set()
  if set(request)!=scope:raise c.Rejected('Unknown operation or fields')
  with self.lock:
   if op=='health':return {'version':1,'engine':'offline_fixture','transport':'unix_socket','monitoring':'paused' if self.paused else 'fixture_only','live_providers':False}
   if op=='pause':self.paused=True;return {'monitoring':'paused'}
   if op=='resume':self.paused=False;return {'monitoring':'fixture_only'}
   if op=='shutdown':self.stopping=True;return {'engine':'stopping'}
   if op in ('observe','sessions'):
    data=recovery.observation(list(self.packages.values())) if not self.paused else recovery.observation([])
    data['monitoring']='paused' if self.paused else 'fixture_only';data['capabilities']['pause_monitoring']=True;data['capabilities']['prepare_offline']=not self.paused
    return data
   if self.paused:raise c.Rejected('Fixture monitoring paused')
   p=self.packages.get(request['session'])
   if p is None:raise c.Rejected('Unknown selected session')
   if op=='checkpoint':return {'session':p['session'],'markdown':c.markdown(p),'fresh':c.fresh(p['snapshot']),'fingerprint':p['fingerprint'],'canonical':str(Path(p['snapshot']['canonical_root'])/p['snapshot']['canonical'])}
   if op=='evidence':return {'session':p['session'],'evidence':[{'state':c.receipt_state(r,p['snapshot']),'command':r['command'],'provenance':r['provenance'],'location':r['evidence'],'exit_status':r['exit_status']} for r in p['receipts']]}
   if request['destination'] not in ('claude','hermes','codex'):raise c.Rejected('Unsupported destination')
   return {'session':p['session'],'assessment':recovery.assess(p,request['destination'],'unknown',p['writer'],False),'markdown':c.markdown(p),'delivery':'not_sent','provenance':'offline proposal; source identity and destination unavailable'}

def exchange(peer,engine,token):
 """One bounded request per connection. Rejection never changes engine state."""
 peer.settimeout(2);raw=bytearray()
 try:
  if hasattr(peer,'getpeereid') and peer.getpeereid()[0]!=os.getuid():raise c.Rejected('Foreign peer')
  while b'\n' not in raw:
   chunk=peer.recv(min(4096,REQUEST_LIMIT+1-len(raw)))
   if not chunk:raise c.Rejected('Incomplete request')
   raw.extend(chunk)
   if len(raw)>REQUEST_LIMIT:raise c.Rejected('Oversized request')
  line,extra=raw.split(b'\n',1)
  if extra:raise c.Rejected('Multiple requests refused')
  req=json.loads(line)
  if not isinstance(req,dict) or set(req)!={'token','request'} or not isinstance(req['token'],str) or not hmac.compare_digest(req['token'],token):raise c.Rejected('Unauthorized client')
  response={'ok':True,'result':engine.request(req['request'])}
 except (c.Rejected,OSError,ValueError,KeyError,TypeError):response={'ok':False,'error':'Request rejected; no action performed'}
 payload=json.dumps(response).encode()+b'\n'
 if len(payload)>RESPONSE_LIMIT:payload=b'{"ok":false,"error":"Response exceeds bound"}\n'
 try:peer.sendall(payload)
 except OSError:pass

class Client:
 def __init__(self,root):self.root=private_root(root)
 def request(self,request):
  token=state.read_private(self.root/'socket-token.json')
  if not isinstance(token,dict) or set(token)!={'token'} or not isinstance(token['token'],str):raise c.Rejected('Invalid local token')
  with socket.socket(socket.AF_UNIX) as peer:
   peer.settimeout(3);peer.connect(str(self.root/'engine.sock'));peer.sendall(json.dumps({'token':token['token'],'request':request}).encode()+b'\n');raw=bytearray()
   while b'\n' not in raw:
    chunk=peer.recv(65536)
    if not chunk:raise c.Rejected('Disconnected engine')
    raw.extend(chunk)
    if len(raw)>RESPONSE_LIMIT:raise c.Rejected('Oversized response')
   response=json.loads(raw)
   if not isinstance(response,dict) or set(response)!={'ok','result'} or response['ok'] is not True:raise c.Rejected('Malformed or rejected engine response')
   if not response.get('ok'):raise c.Rejected('Engine rejected request')
   return response['result']

def serve(root,packages):
 root=private_root(root);endpoint=root/'engine.sock'
 if len(os.fsencode(endpoint))>=104:raise c.Rejected('Socket path too long')
 engine=Engine(packages);fd=os.open(root/'socket-service.lock',os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW,0o600);authenticate_file(fd)
 listener=None;bound=None
 try:
  fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
  if endpoint.exists() or endpoint.is_symlink():raise c.Rejected('Existing socket refused; inspect owned stale state')
  listener=socket.socket(socket.AF_UNIX);listener.bind(str(endpoint));bound=endpoint.lstat();endpoint.chmod(0o600);listener.listen(8);listener.settimeout(.5)
  state.atomic(root,'socket-token.json',{'token':secrets.token_urlsafe(32)});token=state.read_private(root/'socket-token.json')['token']
  while not engine.stopping:
   try:peer,_=listener.accept()
   except socket.timeout:continue
   with peer:exchange(peer,engine,token)
 finally:
  if listener:listener.close()
  if bound:
   try:
    current=endpoint.lstat()
    if stat.S_ISSOCK(current.st_mode) and (current.st_dev,current.st_ino)==(bound.st_dev,bound.st_ino):endpoint.unlink()
   except FileNotFoundError:pass
  os.close(fd)

if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',required=True);p.add_argument('--packages',required=True);args=p.parse_args()
 try:serve(args.state,state.read_private(Path(args.packages)))
 except (c.Rejected,OSError,ValueError,KeyError,TypeError):raise SystemExit(2)
