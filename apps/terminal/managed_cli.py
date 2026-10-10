"""Thin managed-session client; temporary fixtures only, no production migration."""
import argparse,base64,fcntl,json,os,select,signal,subprocess,sys,termios,time,tty,uuid
from pathlib import Path
from managed_engine import Client,Denied,Registry,endpoint,fixture_path,observation

def start(root,cwd,sid=None,timeout=5,provider="skeptic-fake-v1",approved=False,packet=""):
 root=fixture_path(root);cwd=fixture_path(cwd)
 if not cwd.is_dir():raise Denied('Temporary working directory required')
 from managed_engine import session_id
 sid=session_id(sid) if sid else str(uuid.uuid4())
 # Validate the Darwin AF_UNIX pathname before creating registry state or spawning.
 endpoint(root,sid)
 registry=Registry(root);registry.close()
 launch_plan=None
 if provider!='skeptic-fake-v1':
  from managed_providers import plan
  launch_plan=plan(provider,cwd,prompt=packet,approved=approved)
 from managed_engine import private_file
 receipt=Path(root)/(sid+'.startup')
 fd=None
 process=None;guard=None
 try:
  if launch_plan is not None:
   guard=private_file(Path(root)/'provider-launch.lock',True);fcntl.flock(guard,fcntl.LOCK_EX)
   from managed_switch import overlaps
   # Startup receipts cover the spawn/registry gap. Refuse unresolved overlaps.
   for other in Path(root).glob('*.startup'):
    if other==receipt:continue
    otherfd=private_file(other,readonly=True)
    try:record=json.loads(os.read(otherfd,300001))
    finally:os.close(otherfd)
    if not overlaps(record['cwd'],cwd):continue
    row=observation(root,record['session'])
    if row.get('reachability')!='reachable' or row['status']!='exited':raise Denied('Overlapping managed project may still have a writer; fresh launch refused')
   registry=Registry(root,readonly=True)
   try:
    tables={r[0] for r in registry.db.execute('SELECT name FROM sqlite_master WHERE type=\'table\'')}
    if 'project_locks' in tables:
     for project,transaction in registry.db.execute('SELECT project,transaction_id FROM project_locks'):
      if overlaps(project,cwd):
       tx=registry.db.execute('SELECT target FROM switches WHERE id=?',(transaction,)).fetchone()
       if not tx or tx[0]!=sid:raise Denied('Project reserved by another switch')
   finally:registry.close()

  fd=private_file(receipt,True)
  fcntl.flock(fd,fcntl.LOCK_EX)
  existing=os.read(fd,300001)
  if existing:
   record=json.loads(existing)
   if record['cwd']!=str(cwd) or record.get('provider','skeptic-fake-v1')!=provider or record.get('packet','')!=packet:raise Denied('Startup identity belongs to a different project')
   try:
    client=Client(root,sid)
    try:return sid,None,client.request('status')
    finally:client.close()
   except (OSError,Denied):
    raise Denied('Startup '+sid+' unresolved; inspect status/receipt; duplicate launch refused')
  # Durable intent precedes spawn. A crash in this gap is deliberately fail-closed.
  record=json.dumps({'session':sid,'cwd':str(cwd),'provider':provider,'native_id':launch_plan['native_id'] if launch_plan else None,'version':launch_plan['version'] if launch_plan else 'fake-v1','packet':packet,'state':'launch_intent'}).encode()
  remaining=memoryview(record)
  while remaining:
   count=os.write(fd,remaining)
   if count<=0:raise Denied('Startup intent could not be written; no spawn attempted')
   remaining=remaining[count:]
  os.fsync(fd)
  directory=os.open(root,os.O_RDONLY|os.O_DIRECTORY)
  try:os.fsync(directory)
  finally:os.close(directory)
  process=subprocess.Popen([sys.executable,'-B',str(Path(__file__).with_name('managed_engine.py')),str(root),sid,str(cwd),provider,'approved' if approved else 'unapproved'],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True,close_fds=True)
 finally:
  if fd is not None:os.close(fd)
  if guard is not None:os.close(guard)
 deadline=time.monotonic()+timeout
 while time.monotonic()<deadline:
  if process.poll() is not None:raise Denied('Supervisor failed for startup '+sid+'; inspect status/receipt; no retry attempted')
  try:
   client=Client(root,sid)
   try:info=client.request('status')
   finally:client.close()
   return sid,process,info
  except (OSError,Denied):time.sleep(.02)
 raise Denied('Readiness unknown for startup '+sid+'; inspect status/receipt; retry --id '+sid+' never duplicates launch')

def finished(status,cursor):
 return status['status']=='exited' and status['output_complete'] and cursor>=status['final_cursor']

def detach_input(pending,incoming):
 return len(pending)+len(incoming.replace(b'\x1d',b'',1))

def capture_recovery_output(client,tx):
 """Capture a bounded, gap-free output prefix with a stable final cursor."""
 output=bytearray();cursor=0
 def identity(status):
  return status.get('id')==tx['target'] and status.get('reachability')=='reachable' and status.get('status') in ('live','detached') and status.get('provider')==tx['provider'] and status.get('project')==tx['project']
 for _ in range(8):
  status=client.request('status')
  if not identity(status):raise Denied('Destination identity/status mismatch; recovery remains unverified')
  end=status.get('final_cursor')
  if type(end) is not int or end<cursor:raise Denied('Destination output cursor changed; recovery remains unverified')
  while cursor<end:
   part=client.request('output',cursor=cursor)
   try:data=base64.b64decode(part['data'],validate=True)
   except (KeyError,ValueError,TypeError) as error:raise Denied('Invalid destination output; recovery remains unverified') from error
   if part.get('gap') or part.get('cursor',cursor)<=cursor or len(output)+len(data)>65536:raise Denied('Destination output gap/limit; recovery remains unverified')
   output.extend(data);cursor=part['cursor']
  latest=client.request('status')
  if not identity(latest):raise Denied('Destination identity/status changed; recovery remains unverified')
  if latest.get('final_cursor')==cursor:
   if not output:raise Denied('No complete destination response available; recovery remains unverified')
   return bytes(output)
  if type(latest.get('final_cursor')) is not int or latest['final_cursor']<cursor:raise Denied('Destination output cursor changed; recovery remains unverified')
 if not output:raise Denied('No complete destination response available; recovery remains unverified')
 raise Denied('Destination output did not stabilize; recovery remains unverified')

def attach(root,sid,observe=False,cursor=0):
 if not sys.stdin.isatty() or not sys.stdout.isatty():raise Denied('Interactive terminal required')
 client=Client(root,sid);old=termios.tcgetattr(0);handlers={};resized=True;pending=b''
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
   if finished(status,cursor):
    os.write(1,('\r\n[Agent exited: '+str(status['exit_code'])+']\r\n').encode());break
   if select.select([0],[],[],.03)[0]:
    incoming=os.read(0,4096)
    if not incoming or b'\x1d' in incoming:
     abandoned=detach_input(pending,incoming)
     client.request('detach');os.write(1,('\r\n[Detached; cursor='+str(cursor)+'; agent preserved; unsent bytes='+str(abandoned)+'; never replayed]\r\n').encode());pending=b'';break
    if not observe:pending+=incoming
   if pending:
    amount=client.request('input',data=base64.b64encode(pending[:4096]).decode())['written'];pending=pending[amount:]
    if len(pending)>65536:raise Denied('Input backpressure; no input duplicated')
 finally:
  if pending:os.write(2,('\r\n[Unacknowledged input bytes='+str(len(pending))+'; delivery may be partial; never replayed]\r\n').encode())
  termios.tcsetattr(0,termios.TCSADRAIN,old)
  for sig,handler in handlers.items():signal.signal(sig,handler)
  client.close()

def main(argv=None):
 parser=argparse.ArgumentParser(description='Managed Skeptic sessions in explicitly selected temporary fixtures')
 parser.add_argument('action',choices=['start','attach','status','list','shutdown','initialize','transactions','revoke','reconcile','acknowledge','release','providers']);parser.add_argument('--state',required=True);parser.add_argument('--cwd');parser.add_argument('--provider',choices=['skeptic-fake-v1','claude','codex'],default='skeptic-fake-v1');parser.add_argument('--approve-provider',action='store_true');parser.add_argument('--id');parser.add_argument('--transaction');parser.add_argument('--name');parser.add_argument('--observe',action='store_true');parser.add_argument('--cursor',type=int,default=0);args=parser.parse_args(argv)
 try:
  if args.action=='providers':
   from managed_providers import probe
   for provider in ('claude','codex'):
    try:print(json.dumps(probe(provider),indent=2))
    except (Denied,OSError,subprocess.SubprocessError) as error:print(provider+': '+str(error))
   return 0
  if args.action=='initialize':
   from managed_switch import initialize
   initialize(args.state);print('Temporary integration schema initialized; production state untouched');return 0
  if args.action in ('transactions','revoke','reconcile','release'):
   from managed_switch import Manager
   manager=Manager(args.state,readonly=args.action=='transactions')
   try:
    if args.action=='transactions':print(json.dumps([dict(zip(['id','source','target','provider','stage','error'],row)) for row in manager.db.execute('SELECT id,source,target,provider,stage,error FROM switches')],indent=2))
    else:
     if not args.id:raise Denied('--id required')
     if args.action=='revoke':manager.revoke(args.id)
     elif args.action=='reconcile':print(json.dumps(manager.reconcile(args.id),indent=2))
     else:print(json.dumps(manager.release_project(args.id),indent=2))
   finally:manager.close()
   return 0
  if args.action=='acknowledge':
   if not args.id or not args.transaction:raise Denied('--id destination session and --transaction are required')
   from managed_switch import Manager
   manager=Manager(args.state)
   try:
    tx=manager.transaction(args.transaction)
    if tx['target']!=args.id:raise Denied('Transaction does not target this session')
    client=Client(args.state,args.id)
    try:output=capture_recovery_output(client,tx)
    finally:client.close()
    packet_fd=__import__('managed_engine').private_file(tx['packet'],readonly=True)
    try:packet=os.read(packet_fd,48001).decode()
    finally:os.close(packet_fd)
    print('Checkpoint to verify (inspect the user objective, project, pending work, and source preservation):\n'+packet)
    # Escape terminal controls from provider output. The PTY transcript is
    # untrusted content and must not execute terminal escape sequences here.
    visible=''.join(ch if ch in '\n\r\t' or 32<=ord(ch)<127 else ('\\x%02x'%ord(ch)) for ch in output.decode('utf-8','replace'))
    print('Captured destination response (terminal controls escaped):\n'+visible)
    expected={'session':tx['target'],'project':tx['project'],'objective':tx['objective'],'checkpoint':tx['hash'],'provider':tx['provider']}
    answers={key:input('After inspecting, enter exact '+key+' value: ') for key in expected}
    answers['pending']=input('State the next pending item you verified (8+ characters): ')
    done=manager.acknowledge(args.transaction,answers,output)
    print('Operator-verified recovery recorded. The CLI verified session/project/provider identity and bound this attestation to the checkpoint and captured PTY output; the operator verified context semantics. Source retained. Project remains reserved while destination may write. Transaction '+done['id'])
   finally:manager.close()
   return 0
  if args.action=='start':
   if not args.cwd:raise Denied('--cwd required')
   if args.name:
    from managed_switch import Manager
    manager=Manager(args.state,readonly=True);manager.close()
   sid,process,info=start(args.state,args.cwd,args.id,provider=args.provider,approved=args.approve_provider)
   if args.name:
    manager=Manager(args.state)
    try:manager.register(sid,args.name)
    finally:manager.close()
   print('SESSION '+sid,flush=True)
   if sys.stdin.isatty():attach(args.state,sid)
   return 0
  if args.action=='list':
   registry=Registry(args.state,readonly=True)
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
 except (Denied,OSError,ValueError,__import__("sqlite3").DatabaseError,KeyboardInterrupt) as error:
  print('Managed session unavailable: '+str(error)+'. No relaunch attempted.',file=sys.stderr);return 2
if __name__=='__main__':sys.exit(main())
