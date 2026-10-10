"""Fake-only PTY acceptance in isolated temporary directories."""
import base64,os,pty,select,signal,sqlite3,subprocess,sys,tempfile,time,unittest,uuid
from pathlib import Path
import managed_engine as e
import managed_cli as cli

class ManagedTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='sk-');self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve();self.state=self.root/'state';self.cwd=self.root/'project';self.cwd.mkdir();self.clients=[];self.process=None
  self.sid,self.process,self.info=cli.start(self.state,self.cwd)
  self.addCleanup(self.tearDown)
  probe=self.client();data=bytearray();cursor=0
  def ready():
   nonlocal cursor
   result=probe.request('output',cursor=cursor);cursor=result['cursor'];data.extend(base64.b64decode(result['data']));return b'FAKE_READY' in data or probe.request('status')['status']=='exited'
  self.wait(ready);self.assertIn(b'FAKE_READY',data,str(probe.request('status')))
 def tearDown(self):
  for c in self.clients:c.close()
  if self.process and self.process.poll() is None:
   try:os.kill(self.info['agent'],signal.SIGCONT);os.kill(self.info['agent'],signal.SIGTERM)
   except ProcessLookupError:pass
   try:
    c=e.Client(self.state,self.sid);self.wait(lambda:c.request('status')['status']=='exited');c.request('shutdown');c.close();self.process.wait(timeout=3)
   except (e.Denied,OSError,AssertionError,subprocess.TimeoutExpired):self.process.kill();self.process.wait()
  self.tmp.cleanup()
 def client(self):
  c=e.Client(self.state,self.sid);self.clients.append(c);return c
 def wait(self,predicate):
  deadline=time.monotonic()+4
  while time.monotonic()<deadline:
   value=predicate()
   if value:return value
   time.sleep(.01)
  self.fail('Fixture event timeout')
 def output(self,c,needle,cursor=0):
  body=bytearray()
  def poll():
   nonlocal cursor
   result=c.request('output',cursor=cursor);cursor=result['cursor'];body.extend(base64.b64decode(result['data']));return needle in body
  self.wait(poll);return bytes(body),cursor
 def send(self,c,text):
  body=text.encode();count=c.request('input',data=base64.b64encode(body).decode())['written'];self.assertEqual(count,len(body))
 def test_detach_reconnect_identity_output_and_cwd(self):
  c=self.client();c.request('attach');data,cursor=self.output(c,b'FAKE_READY');self.assertIn(str(self.cwd).encode(),data);self.assertIn(b'TTY=True',data)
  self.send(c,'before\n');_,cursor=self.output(c,b'ECHO=before',cursor);c.close();self.clients.remove(c)
  observer=self.client();self.wait(lambda:observer.request('status')['status']=='detached');self.assertIsNone(self.process.poll())
  d=self.client();d.request('attach');self.send(d,'after\n');data,_=self.output(d,b'ECHO=after',cursor)
  self.assertNotIn(b'ECHO=before',data);info=d.request('status');self.assertEqual(info['agent'],self.info['agent']);self.assertEqual(info['id'],self.sid);self.assertEqual(info['cwd'],str(self.cwd));self.assertEqual(info['project'],self.info['project'])
 def test_single_writer_observation_disconnect_and_transfer(self):
  a,b=self.client(),self.client();a.request('attach');b.request('attach',mode='observe')
  with self.assertRaises(e.Denied):b.request('attach')
  with self.assertRaises(e.Denied):self.send(b,'forbidden\n')
  self.output(b,b'FAKE_READY');a.request('detach');b.request('claim');self.send(b,'new-owner\n');self.output(b,b'ECHO=new-owner');b.close();self.clients.remove(b);self.wait(lambda:a.request('status')['status']=='detached');a.request('claim')
 def test_exit_status_no_silent_relaunch(self):
  c=self.client();c.request('attach');self.send(c,'fail\n');self.wait(lambda:c.request('status')['status']=='exited');self.assertEqual(c.request('status')['exit_code'],7)
  with self.assertRaises(e.Denied):c.request('claim')
  self.assertEqual(c.request('status')['agent'],self.info['agent'])
 def test_supervisor_failure_disclosed_not_reattached(self):
  self.process.kill();self.process.wait(timeout=3);info=e.observation(self.state,self.sid);self.assertEqual(info['status'],'stale');self.assertEqual(info['reachability'],'unreachable');self.assertIn('no supervisor reconnection',info['screen'])
  with self.assertRaises((OSError,e.Denied)):self.client()
 def test_stale_registry_never_adopts_pid(self):
  registry=e.Registry(self.state);sid=str(uuid.uuid4());registry.create(sid,self.cwd,str(uuid.uuid4()));registry.update(sid,agent=os.getpid(),status='live');registry.close();info=e.observation(self.state,sid);self.assertEqual(info['status'],'stale');self.assertEqual(info['agent'],os.getpid())
 def test_interrupted_transaction_preserves_metadata(self):
  registry=e.Registry(self.state);before=registry.get(self.sid);registry.db.execute('BEGIN');registry.db.execute("UPDATE sessions SET status='invented' WHERE id=?",(self.sid,));registry.close();registry=e.Registry(self.state);self.assertEqual(registry.get(self.sid),before);registry.close()
 def test_registry_never_stores_terminal_bodies(self):
  c=self.client();c.request('attach');self.send(c,'SYNTHETIC_PRIVATE_TEXT\n');self.output(c,b'ECHO=SYNTHETIC_PRIVATE_TEXT');self.assertNotIn(b'SYNTHETIC_PRIVATE_TEXT',(self.state/'registry.sqlite').read_bytes())
 def test_authentication_and_generation(self):
  c=self.client();key=c.key;c.key='wrong'
  with self.assertRaises(e.Denied):c.request('attach')
  c.key=key;c.metadata['generation']='wrong'
  with self.assertRaises(e.Denied):c.request('attach')
 def test_resize_interrupt_stop_continue(self):
  c=self.client();c.request('attach');self.output(c,b'FAKE_READY');c.request('resize',rows=33,cols=101);self.output(c,b'SIZE=33x101');self.send(c,'\x03');self.output(c,b'INTERRUPT');self.send(c,'stop\n');self.wait(lambda:c.request('status')['status']=='suspended');c.request('continue');self.output(c,b'CONTINUED');self.wait(lambda:c.request('status')['status']=='live')
 def test_output_overflow_disclosed(self):
  c=self.client();c.request('attach');self.send(c,'burst\n');self.wait(lambda:c.request('output',cursor=0)['gap']);r=c.request('output',cursor=0);self.assertGreater(r['start'],0)
 def test_observer_cannot_resize_or_continue(self):
  c=self.client();c.request('attach',mode='observe')
  for op,kwargs in [('resize',dict(rows=20,cols=80)),('continue',{})]:
   with self.assertRaises(e.Denied):c.request(op,**kwargs)
 def test_shutdown_cannot_terminate_live_agent(self):
  c=self.client()
  with self.assertRaises(e.Denied):c.request('shutdown')
  self.assertIsNone(self.process.poll())

 def test_simultaneous_writer_claims_exactly_one_winner(self):
  import threading
  a,b=self.client(),self.client();barrier=threading.Barrier(3);results=[]
  def claim(c):
   barrier.wait()
   try:c.request('attach');results.append('writer')
   except e.Denied:results.append('denied')
  workers=[threading.Thread(target=claim,args=(c,)) for c in (a,b)]
  for worker in workers:worker.start()
  barrier.wait()
  for worker in workers:worker.join(timeout=3);self.assertFalse(worker.is_alive())
  self.assertCountEqual(results,['writer','denied'])
 def test_crashed_sqlite_writer_rolls_back(self):
  script="import sqlite3,sys,os;db=sqlite3.connect(sys.argv[1]);db.execute('BEGIN IMMEDIATE');db.execute(\"UPDATE sessions SET status='invented' WHERE id=?\",(sys.argv[2],));os._exit(9)"
  result=subprocess.run([sys.executable,'-B','-c',script,str(self.state/'registry.sqlite'),self.sid],check=False)
  self.assertEqual(result.returncode,9);registry=e.Registry(self.state)
  try:self.assertNotEqual(registry.get(self.sid)['status'],'invented')
  finally:registry.close()
 def test_fragmented_request_and_oversize_do_not_block_other_clients(self):
  import json,struct
  c=self.client();message=e.frame(dict(v=1,id=2,op='status',key=c.key,generation=c.metadata['generation']))
  c.socket.sendall(message[:3]);other=self.client();self.assertEqual(other.request('status')['id'],self.sid)
  c.socket.sendall(message[3:]);size=struct.unpack('!I',c.socket.recv(4))[0];body=b''
  while len(body)<size:body+=c.socket.recv(size-len(body))
  self.assertTrue(json.loads(body)['ok']);c.socket.sendall(struct.pack('!I',e.FRAME_LIMIT+1));self.assertEqual(c.socket.recv(1),b'');self.assertEqual(other.request('status')['id'],self.sid)
 def test_deep_nested_and_invalid_request_id_survive(self):
  import json,struct
  c=self.client();other=self.client()
  for raw in [b'{"data":'+b'['*1500+b'0'+b']'*1500+b'}',json.dumps(dict(v=1,id='x'*32000,op='status',key=c.key,generation=c.metadata['generation'])).encode()]:
   c.socket.sendall(struct.pack('!I',len(raw))+raw)
   def receive(size):
    result=b''
    while len(result)<size:result+=c.socket.recv(size-len(result))
    return result
   result=json.loads(receive(struct.unpack('!I',receive(4))[0]))
   self.assertFalse(result['ok']);self.assertEqual(other.request('status')['id'],self.sid)
  self.assertIsNone(self.process.poll())

 def test_state_alias_and_real_project_refused(self):
  alias=self.root/'alias';alias.symlink_to(self.state)
  with self.assertRaises(e.Denied):e.Registry(alias)
  with self.assertRaises(e.Denied):e.fixture_path(Path.home())
 def test_exit_output_fully_drained_and_owned_process_group_gone(self):
  c=self.client();c.request('attach');self.send(c,'exit\n');data,_=self.output(c,b'FAKE_EXIT');self.assertIn(b'FAKE_EXIT',data);self.wait(lambda:c.request('status')['output_complete']);status=c.request('status');self.assertEqual(status['exit_code'],0);self.assertTrue(status['agent_process_group_quiescent'])

 def test_shared_registry_stable_project_mapping(self):
  sid,process,info=cli.start(self.state,self.cwd);c=e.Client(self.state,sid)
  try:
   self.assertNotEqual(sid,self.sid);self.assertEqual(info['project'],self.info['project']);self.assertNotEqual(info['supervisor'],self.info['supervisor']);c.request('attach');self.send(c,'exit\n');self.wait(lambda:c.request('status')['status']=='exited');c.request('shutdown');process.wait(timeout=3)
  finally:
   c.close()
   if process.poll() is None:process.kill();process.wait()

 def test_skeptic_dispatch_never_opens_production_state(self):
  import contextlib,io,json,switcher
  from unittest.mock import patch
  output=io.StringIO()
  with contextlib.redirect_stdout(output),patch.object(switcher,'State',side_effect=AssertionError('Production State accessed')):
   result=switcher.main(['managed','status','--state',str(self.state),'--id',self.sid])
  self.assertEqual(result,0);self.assertEqual(json.loads(output.getvalue())['agent'],self.info['agent'])

@unittest.skipUnless(sys.platform=='darwin','macOS terminal acceptance')
class ThreeSessionPTYAcceptance(unittest.TestCase):
 """Three real managed PTYs; provider recovery remains deliberately synthetic."""
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='sk3-');self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve();self.state=self.root/'state';self.processes={};self.clients={};self.ids={};self.provider_map={};self.last_inputs={}
  self.state.mkdir(mode=0o700);import managed_switch;managed_switch.initialize(self.state)
  self.assertLess(len(e.endpoint(self.state,str(uuid.uuid4())).encode()),104,'short temporary prefix is required by macOS AF_UNIX pathname limit')
  self.manager=None;self.addCleanup(self.cleanup_owned)
  for name in ('Daily Brief','Website','Research'):
   cwd=self.root/name;cwd.mkdir();sid,proc,_=cli.start(self.state,cwd);self.ids[name]=sid;self.processes[sid]=proc
 def client(self,sid):
  client=e.Client(self.state,sid);self.clients[sid]=client;return client
 def wait(self,predicate,timeout=5,diagnostics=None):
  deadline=time.monotonic()+timeout
  while time.monotonic()<deadline:
   value=predicate()
   if value:return value
   time.sleep(.01)
  self.fail('Three-session PTY fixture timed out'+ ('; '+diagnostics() if diagnostics else ''))
 def send(self,client,text):
  # These fixture commands target a line-reading fake, not a raw terminal UI.
  body=(text if text.endswith('\n') else text+'\n').encode()
  count=client.request('input',data=base64.b64encode(body).decode())['written']
  self.last_inputs[client.metadata['id']]={'bytes':len(body),'pty_bytes_accepted':count,'newline_terminated':body.endswith(b'\n')}
  self.assertEqual(count,len(body))
 def output(self,client,needle,cursor=0):
  data=bytearray();replay={};gap=False
  def poll():
   nonlocal cursor,gap,replay
   result=client.request('output',cursor=cursor);gap=gap or result['gap'];replay={k:result[k] for k in ('start','end','cursor')};cursor=result['cursor'];data.extend(base64.b64decode(result['data']));return needle in data
  def diagnostics():
   sid=client.metadata['id'];process=self.processes.get(sid)
   report={'session':sid,'supervisor_exit':process.poll() if process else None,'last_input':self.last_inputs.get(sid),'replay':replay,'replay_gap':gap,'bytes_observed':len(data),'child_ready_observed':b'FAKE_READY' in data,'child_echo_observed':b'ECHO=' in data,'expected':repr(needle[:200]),'output_tail':repr(bytes(data[-1024:])),'input_note':'PTY acknowledgement is not proof the child consumed input; ECHO= is the fake child response.'}
   try:
    status=client.request('status');report['status']={k:status.get(k) for k in ('id','agent','supervisor','status','exit_code','output_complete','final_cursor','writer_attached','reachability')}
   except (e.Denied,OSError) as error:report['status_error']=str(error)[:200]
   return __import__('json').dumps(report)[:4096]
  self.wait(poll,diagnostics=diagnostics);return bytes(data),cursor
 def quiescent(self,client):
  status=client.request('status')
  return status['status']=='exited' and status['output_complete'] and status['agent_process_group_quiescent']
 def cleanup_owned(self):
  clients=dict(self.clients)
  for sid in self.processes:
   if sid not in clients:
    try:clients[sid]=e.Client(self.state,sid)
    except (e.Denied,OSError):pass
  for client in clients.values():
   try:
    status=client.request('status')
    if status['status'] in ('live','detached','suspended'):
     if status['status']=='suspended':os.killpg(status['agent'],signal.SIGCONT)
     try:client.request('claim')
     except e.Denied:pass
     client.request('input',data=base64.b64encode(b'exit\n').decode())
    self.wait(lambda:client.request('status')['status']=='exited',timeout=3)
    client.request('shutdown')
   except (e.Denied,OSError,AssertionError):
    pass
   client.close()
  for process in self.processes.values():
   if process.poll() is None:
    try:process.wait(timeout=3)
    except subprocess.TimeoutExpired:
     # Only this fixture's owned supervisor handle is signaled.
     process.terminate();process.wait(timeout=3)
  if self.manager:self.manager.close()
 def test_three_isolated_agents_reconnect_and_selected_synthetic_switches(self):
  import managed_switch
  for name,sid in self.ids.items():
   client=self.client(sid);client.request('attach');status=client.request('status')
   self.assertEqual(Path(status['cwd']).name,name);self.assertEqual(status['id'],sid)
   self.send(client,'IDENTITY-'+name);data,_=self.output(client,('ECHO=IDENTITY-'+name).encode())
   for other in set(self.ids)-{name}:self.assertNotIn(('IDENTITY-'+other).encode(),data)
  # Simultaneous independent writer leases and context, then detach/reconnect all.
  for name,sid in self.ids.items():
   self.clients[sid].request('detach');self.clients[sid].close()
   client=self.client(sid);client.request('attach')
   status=client.request('status');self.assertEqual(status['cwd'],str(self.root/name));self.assertEqual(status['id'],sid)
  # Completed source processes are quiescent; Research remains live and excluded.
  selected=('Daily Brief','Website')
  for name in selected:self.send(self.clients[self.ids[name]],'exit\n')
  for name in selected:
   client=self.clients[self.ids[name]]
   self.wait(lambda:self.quiescent(client))
   self.assertEqual(self.clients[self.ids['Research']].request('status')['status'],'live')
  def inspect(root,sid):
   row=e.observation(root,sid)
   if sid in self.provider_map:row['provider']=self.provider_map[sid]
   return row
  self.manager=managed_switch.Manager(self.state,inspect=inspect)
  for name,sid in self.ids.items():self.manager.register(sid,name)
  preview=self.manager.preview('codex');eligible={row['id'] for row in preview if row['eligible']}
  self.assertEqual(eligible,{self.ids[name] for name in selected})
  research=next(row for row in preview if row['id']==self.ids['Research']);self.assertFalse(research['eligible']);self.assertIn('still live',research['exclusion'])
  transactions=[]
  for name in selected:
   sid=self.ids[name];objective='Continue the '+name+' task';packet='SYNTHETIC_CONTEXT|'+name+'|'+objective+'|pending item'
   tx=self.manager.prepare(sid,'codex',packet,objective);self.manager.authorize(tx['id'],tx['hash'])
   def launch(root,cwd,target,provider,context):
    self.provider_map[target]=provider
    _,process,_=cli.start(root,cwd,target,provider='skeptic-fake-v1',packet=context);self.processes[target]=process
    client=self.client(target);client.request('attach');marker='RESTORED|'+context
    self.send(client,marker);data,_=self.output(client,('ECHO='+marker).encode())
    self.assertIn(marker.encode(),data);self.assertNotIn(('SYNTHETIC_CONTEXT|'+('Website' if name=='Daily Brief' else 'Daily Brief')).encode(),data)
   self.manager.execute(tx['id'],launch)
   receipt={'target':tx['target'],'project':tx['project'],'objective':tx['objective'],'checkpoint':tx['hash'],'provider':tx['provider']}
   done=self.manager.verify(tx['id'],receipt);transactions.append(done['id'])
   self.assertEqual(self.manager.details(done['target'])['task_state'],'recovered')
   self.assertEqual(self.manager.db.execute('SELECT COUNT(*) FROM project_locks WHERE transaction_id=?',(done['id'],)).fetchone()[0],1)
   with self.assertRaises(e.Denied):self.manager.prepare(sid,'codex',packet,objective)
  self.assertEqual(len(set(transactions)),2)
  self.assertEqual(e.observation(self.state,self.ids['Research'])['status'],'live')
  self.send(self.clients[self.ids['Research']],'RESEARCH_STILL_OWNED')
  data,_=self.output(self.clients[self.ids['Research']],b'ECHO=RESEARCH_STILL_OWNED')
  self.assertIn(b'ECHO=RESEARCH_STILL_OWNED',data)


class CLIAcceptance(unittest.TestCase):
 setUp=ManagedTests.setUp
 tearDown=ManagedTests.tearDown
 wait=ManagedTests.wait
 client=ManagedTests.client
 def test_new_cli_attachment_same_agent_and_terminal_restoration(self):
  def spawn(action):
   master,slave=pty.openpty();before=__import__('termios').tcgetattr(slave)
   wrapper='import sys,termios;sys.path.insert(0,'+repr(str(Path(cli.__file__).parent))+');import managed_cli;before=termios.tcgetattr(0);code=managed_cli.main();after=termios.tcgetattr(0);after[3]&=~termios.PENDIN;before[3]&=~termios.PENDIN;assert after==before;sys.exit(code)'
   argv=[sys.executable,'-B','-c',wrapper,'attach','--state',str(self.state),'--id',self.sid]
   process=subprocess.Popen(argv,stdin=slave,stdout=slave,stderr=slave);data=bytearray()
   def until(needle):
    def read():
     if select.select([master],[],[],.02)[0]:
      try:data.extend(os.read(master,65536))
      except OSError:pass
     return needle in data
    try:self.wait(read)
    except AssertionError:self.fail(repr(bytes(data)))
   try:
    until(b'FAKE_READY');os.write(master,b'cli-'+action+b'\n');until(b'ECHO=cli-'+action);os.write(master,b'\x1d');until(b'[Detached;');process.wait(timeout=3);self.assertEqual(process.returncode,0,bytes(data));after=__import__('termios').tcgetattr(slave);after[3]&=~__import__('termios').PENDIN;before[3]&=~__import__('termios').PENDIN;self.assertEqual(after,before)
   finally:
    if process.poll() is None:process.kill();process.wait()
    os.close(master);os.close(slave)
  spawn(b'first');self.assertIsNone(self.process.poll());spawn(b'second');self.assertEqual(e.observation(self.state,self.sid)['agent'],self.info['agent'])

@unittest.skipUnless(sys.platform=='darwin','macOS terminal launch acceptance')
class TerminalLaunch(unittest.TestCase):
 def test_terminal_start_detach_new_terminal_reconnect(self):
  with tempfile.TemporaryDirectory(prefix='sk-cli-') as tmp:
   root=Path(tmp).resolve();state=root/'state';cwd=root/'project';cwd.mkdir();sid=None;client=None;process=None;master=None;slave=None
   def until(needle):
    deadline=time.monotonic()+4
    while needle not in data and time.monotonic()<deadline:
     if select.select([master],[],[],.02)[0]:
      try:data.extend(os.read(master,65536))
      except OSError:break
    self.assertIn(needle,data)
   try:
    master,slave=pty.openpty();data=bytearray()
    process=subprocess.Popen([sys.executable,'-B',str(Path(cli.__file__)),'start','--state',str(state),'--cwd',str(cwd)],stdin=slave,stdout=slave,stderr=slave)
    until(b'FAKE_READY');import re
    sid=re.search(rb'SESSION ([a-f0-9-]{36})',data)[1].decode();client=e.Client(state,sid);before=client.request('status');os.write(master,b'\x1d');until(b'[Detached;');process.wait(timeout=3);self.assertEqual(process.returncode,0)
    os.close(master);os.close(slave);master=slave=None
    master,slave=pty.openpty();data=bytearray()
    process=subprocess.Popen([sys.executable,'-B',str(Path(cli.__file__)),'attach','--state',str(state),'--id',sid],stdin=slave,stdout=slave,stderr=slave)
    until(b'FAKE_READY');self.assertEqual(client.request('status')['agent'],before['agent']);self.assertEqual(client.request('status')['cwd'],str(cwd));os.write(master,b'exit\n');until(b'[Agent exited: 0]');process.wait(timeout=3);self.assertEqual(process.returncode,0);client.request('shutdown')
   finally:
    if process and process.poll() is None:process.kill();process.wait()
    if client:
     try:
      status=client.request('status')
      if status['status']!='exited':client.request('claim');client.request('input',data=base64.b64encode(b'exit\n').decode())
      deadline=time.monotonic()+3
      while client.request('status')['status']!='exited' and time.monotonic()<deadline:time.sleep(.01)
      client.request('shutdown')
     except (e.Denied,OSError):pass
     client.close()
    if master is not None:os.close(master)
    if slave is not None:os.close(slave)

if __name__=='__main__':unittest.main()
