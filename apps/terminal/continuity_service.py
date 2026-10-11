"""Standalone fixture-only observer. No login install, private history or provider calls."""
from pathlib import Path
import argparse,fcntl,json,math,os,select,sys,time
import checkpoint_writer as writer
import checkpoints as c
import recovery_contract as recovery
LIMIT=512*1024

def read_private(path):
 fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  s=os.fstat(fd)
  import stat
  if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1 or s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=0o600 or s.st_size>LIMIT:raise c.Rejected('Private bounded file required')
  with os.fdopen(fd,'rb',closefd=False) as f:raw=f.read(LIMIT+1)
  if len(raw)>LIMIT:raise c.Rejected('Oversized state')
  return json.loads(raw)
 finally:os.close(fd)

def atomic(root,name,value):
 raw=json.dumps(value).encode()
 if len(raw)>LIMIT:raise c.Rejected('Observation too large')
 tmp=root/('.pending-'+str(os.getpid()))
 fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
 try:
  with os.fdopen(fd,'wb') as out:out.write(raw);out.flush();os.fsync(out.fileno())
  os.replace(tmp,root/name)
 finally:
  if tmp.exists():tmp.unlink()

def load_observation(root):
 if root is None:return {'version':1,'engine':'unconnected','monitoring':'disabled','sessions':[],'capabilities':{'live_switch':False,'pause_monitoring':False}}
 root=writer.fixture(root);data=read_private(root/'observation.json')
 if not isinstance(data,dict) or data.get('version')!=1 or not isinstance(data.get('sessions'),list):raise c.Rejected('Invalid observation schema')
 # Never treat a stale persisted snapshot as a running engine.
 stamp=data.get('observed_epoch')
 if type(stamp) not in (int,float) or not math.isfinite(stamp) or not 0<=time.time()-stamp<=5:
  return {'version':1,'engine':'disconnected','monitoring':'unknown','sessions':[],'capabilities':{'live_switch':False,'pause_monitoring':False}}
 return data

def serve(root,packages,stream=sys.stdin):
 root=writer.fixture(root);info=root.stat()
 import stat
 if info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)!=0o700:raise c.Rejected('Owner-only service directory required')
 for p in packages:writer.fixture(p['snapshot']['root']);writer.fixture(p['snapshot']['canonical_root']);c.markdown(p)
 fd=os.open(root/'service.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600);paused=False
 try:
  fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
  while True:
   try:data=recovery.observation(packages) if not paused else {'version':1,'engine':'offline_fixture','sessions':[],'capabilities':{'live_switch':False,'pause_monitoring':False}}
   except (c.Rejected,OSError,ValueError):data={'version':1,'engine':'error','sessions':[],'uncertainty':['Fixture source unavailable'],'capabilities':{'live_switch':False,'pause_monitoring':False}}
   data['monitoring']='paused' if paused else 'fixture_only';data['observed_epoch']=time.time();atomic(root,'observation.json',data)
   readable,_,_=select.select([stream],[],[],1)
   if readable:
    line=stream.readline(128)
    if not line or line.strip()=='shutdown':break
    if line.strip()=='pause':paused=True
    elif line.strip()=='resume':paused=False
  atomic(root,'observation.json',{'version':1,'engine':'stopped','monitoring':'disabled','sessions':[],'observed_epoch':time.time(),'capabilities':{'live_switch':False,'pause_monitoring':False}})
 finally:os.close(fd)
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--state',required=True);p.add_argument('--packages',required=True);a=p.parse_args()
 try:
  packages=read_private(Path(a.packages))
  if not isinstance(packages,list) or len(packages)>32:raise c.Rejected('Bounded package list required')
  serve(Path(a.state),packages)
 except (c.Rejected,OSError,ValueError):sys.exit(2)
