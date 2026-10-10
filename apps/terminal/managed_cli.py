"""Thin fake-session client. Real providers and production state are unsupported."""
import argparse,base64,json,os,select,signal,subprocess,sys,termios,time,tty,uuid
from pathlib import Path
from managed_engine import Client,Denied,Registry,fixture_path,observation

def start(root,cwd):
 registry=Registry(root);registry.close();cwd=fixture_path(cwd)
 if not cwd.is_dir():raise Denied('Temporary working directory required')
 sid=str(uuid.uuid4())
 process=subprocess.Popen([sys.executable,'-B',str(Path(__file__).with_name('managed_engine.py')),str(root),sid,str(cwd)],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True,close_fds=True)
 deadline=time.monotonic()+5
 while time.monotonic()<deadline:
  if process.poll() is not None:raise Denied('Supervisor failed; no retry attempted')
  try:
   client=Client(root,sid)
   try:info=client.request('status')
   finally:client.close()
   return sid,process,info
  except (OSError,Denied):time.sleep(.02)
 raise Denied('Readiness unknown; no duplicate launch attempted')

def attach(root,sid,observe=False,cursor=0):
 if not sys.stdin.isatty() or not sys.stdout.isatty():raise Denied('Interactive terminal required')
 client=Client(root,sid);old=termios.tcgetattr(0);handlers={};resized=True
 def resize(*_):
  nonlocal resized
  resized=True
 def interrupted(*_):raise KeyboardInterrupt
 try:
  client.request('attach',mode='observe' if observe else 'write')
  handlers[signal.SIGWINCH]=signal.signal(signal.SIGWINCH,resize)
  for sig in (signal.SIGTERM,signal.SIGHUP):handlers[sig]=signal.signal(sig,interrupted)
  print('Attached '+sid+(' (observer)' if observe else ' (writer)')+'. Ctrl+] detaches; bounded replay, no exact screen restoration.',flush=True)
  tty.setraw(0);pending=b''
  while True:
   if resized and not observe:
    size=os.get_terminal_size(0)
    if size.lines and size.columns:client.request('resize',rows=size.lines,cols=size.columns)
    resized=False
   result=client.request('output',cursor=cursor)
   if result['gap']:os.write(1,b'\r\n[Output gap: older bytes unavailable]\r\n')
   data=base64.b64decode(result['data']);cursor=result['cursor']
   if data:os.write(1,data)
   status=client.request('status')
   if status['status']=='exited' and status['output_complete'] and cursor>=result['end']:
    os.write(1,('\r\n[Agent exited: '+str(status['exit_code'])+']\r\n').encode());break
   if select.select([0],[],[],.03)[0]:
    incoming=os.read(0,4096)
    if not incoming or b'\x1d' in incoming:
     client.request('detach');os.write(1,('\r\n[Detached; cursor='+str(cursor)+'; agent preserved]\r\n').encode());break
    if not observe:pending+=incoming
   if pending:
    amount=client.request('input',data=base64.b64encode(pending[:4096]).decode())['written'];pending=pending[amount:]
    if len(pending)>65536:raise Denied('Input backpressure; no input duplicated')
 finally:
  termios.tcsetattr(0,termios.TCSADRAIN,old)
  for sig,handler in handlers.items():signal.signal(sig,handler)
  client.close()

def main(argv=None):
 parser=argparse.ArgumentParser(description='Synthetic managed Skeptic sessions only')
 parser.add_argument('action',choices=['start','attach','status','list','shutdown']);parser.add_argument('--state',required=True);parser.add_argument('--cwd');parser.add_argument('--id');parser.add_argument('--observe',action='store_true');parser.add_argument('--cursor',type=int,default=0);args=parser.parse_args(argv)
 try:
  if args.action=='start':
   if not args.cwd:raise Denied('--cwd required')
   sid,process,info=start(args.state,args.cwd);print('SESSION '+sid,flush=True)
   if sys.stdin.isatty():attach(args.state,sid)
   return 0
  if args.action=='list':
   registry=Registry(args.state)
   try:ids=[r[0] for r in registry.db.execute('SELECT id FROM sessions ORDER BY id')]
   finally:registry.close()
   print(json.dumps([observation(args.state,sid) for sid in ids],indent=2));return 0
  if not args.id:raise Denied('--id required')
  if args.action=='attach':attach(args.state,args.id,args.observe,args.cursor)
  elif args.action=='status':print(json.dumps(observation(args.state,args.id),indent=2))
  else:
   client=Client(args.state,args.id)
   try:client.request('shutdown')
   finally:client.close()
  return 0
 except (Denied,OSError,ValueError,KeyboardInterrupt) as error:
  print('Managed fake session unavailable: '+str(error)+'. No relaunch attempted.',file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
