"""Socket-independent regressions; live lifecycle coverage stays in test_managed."""
import base64,contextlib,io,os,pty,select,subprocess,sys,tempfile,time,unittest,uuid
from pathlib import Path
from unittest.mock import patch,Mock
import managed_engine as e
import managed_cli as cli

class Hardening(unittest.TestCase):
 def test_three_session_probes_deliver_complete_lines_to_fake_child(self):
  from test_managed import ThreeSessionPTYAcceptance
  fixture=ThreeSessionPTYAcceptance('test_three_isolated_agents_reconnect_and_selected_synthetic_switches');fixture.last_inputs={}
  master,slave=pty.openpty();process=None;output=bytearray();inputs=[]
  class DirectPTY:
   metadata={'id':'synthetic-direct-pty'}
   def request(self,op,**values):
    if op!='input':raise AssertionError(op)
    body=base64.b64decode(values['data']);inputs.append(body)
    return {'written':os.write(master,body)}
  def until(needle):
   deadline=time.monotonic()+2
   while needle not in output and time.monotonic()<deadline:
    if select.select([master],[],[],.02)[0]:
     try:output.extend(os.read(master,4096))
     except OSError:break
   self.assertIn(needle,output,repr(bytes(output[-1024:])))
  try:
   process=subprocess.Popen([sys.executable,'-B',str(Path(e.__file__).with_name('managed_fake.py'))],stdin=slave,stdout=slave,stderr=slave,close_fds=True)
   os.close(slave);slave=None
   until(b'FAKE_READY')
   for marker in ('IDENTITY-Daily Brief','IDENTITY-Website','IDENTITY-Research','RESTORED|synthetic-context','RESEARCH_STILL_OWNED'):
    fixture.send(DirectPTY(),marker);until(('ECHO='+marker+'\r\n').encode());self.assertEqual(inputs[-1],(marker+'\n').encode())
   fixture.send(DirectPTY(),'exit\n');until(b'FAKE_EXIT');process.wait(timeout=2);self.assertEqual(process.returncode,0)
   self.assertEqual(inputs[-1],b'exit\n')
  finally:
   if process and process.poll() is None:process.terminate();process.wait(timeout=2)
   os.close(master)
   if slave is not None:os.close(slave)

 def test_three_session_timeout_reports_bounded_child_input_and_replay_state(self):
  import json
  from test_managed import ThreeSessionPTYAcceptance
  for state,code in (('live',None),('exited',7)):
   with self.subTest(state=state):
    fixture=ThreeSessionPTYAcceptance('test_three_isolated_agents_reconnect_and_selected_synthetic_switches')
    fixture.processes={'synthetic':Mock()};fixture.processes['synthetic'].poll.return_value=None
    fixture.last_inputs={'synthetic':{'bytes':16,'pty_bytes_accepted':16,'newline_terminated':True}}
    body=b'FAKE_READY\r\n'+b'x'*6000+b'IDENTITY-marker'
    class Replay:
     metadata={'id':'synthetic'}
     def request(self,op,**values):
      if op=='output':
       if values['cursor']!=0:raise AssertionError('Unexpected starting cursor')
       return {'data':base64.b64encode(body).decode(),'cursor':len(body),'start':0,'end':len(body),'gap':True}
      if op=='status':return {'status':state,'exit_code':code,'agent':123,'writer_attached':True,'output_complete':state=='exited','final_cursor':len(body)}
      raise AssertionError(op)
    with patch('test_managed.time.monotonic',side_effect=[0,0,6]),patch('test_managed.time.sleep'),self.assertRaisesRegex(AssertionError,'Three-session PTY fixture timed out') as failure:
     fixture.output(Replay(),b'ECHO=IDENTITY-marker')
    diagnostic=str(failure.exception).split('; ',1)[1];self.assertLessEqual(len(diagnostic),4096);report=json.loads(diagnostic)
    self.assertTrue(report['child_ready_observed']);self.assertFalse(report['child_echo_observed'])
    self.assertEqual(report['last_input']['pty_bytes_accepted'],16);self.assertTrue(report['last_input']['newline_terminated'])
    self.assertEqual(report['status']['status'],state);self.assertEqual(report['status']['exit_code'],code)
    self.assertEqual(report['bytes_observed'],len(body));self.assertEqual(report['replay']['cursor'],len(body));self.assertTrue(report['replay_gap'])
    self.assertIn('IDENTITY-marker',report['output_tail']);self.assertLess(len(report['output_tail']),1200)

 def test_recovery_capture_retries_cursor_race_and_rejects_gaps(self):
  tx={'target':'target-id','provider':'codex','project':'project-id'}
  def status(cursor):return {'id':'target-id','reachability':'reachable','status':'detached','provider':'codex','project':'project-id','final_cursor':cursor}
  class Client:
   def __init__(self,statuses,gap=False):self.statuses=list(statuses);self.cursor=0;self.gap=gap
   def request(self,op,**kwargs):
    if op=='status':return status(self.statuses.pop(0) if len(self.statuses)>1 else self.statuses[0])
    data=b'abcdef'[kwargs['cursor']:min(kwargs['cursor']+3,6)]
    self.cursor+=len(data)
    return {'data':base64.b64encode(data).decode(),'cursor':kwargs['cursor']+len(data),'gap':self.gap}
  client=Client([3,6,6,6]);self.assertEqual(cli.capture_recovery_output(client,tx),b'abcdef')
  with self.assertRaisesRegex(e.Denied,'gap'):cli.capture_recovery_output(Client([3,3],True),tx)
  with self.assertRaisesRegex(e.Denied,'identity'):cli.capture_recovery_output(Client([3,3]),dict(tx,project='wrong'))

 def test_owned_process_group_quiescence_fails_closed(self):
  with patch.object(e.os,'killpg',side_effect=ProcessLookupError):self.assertTrue(e.process_group_clear(12345))
  with patch.object(e.os,'killpg',return_value=None):self.assertFalse(e.process_group_clear(12345))
  with patch.object(e.os,'killpg',side_effect=PermissionError):self.assertFalse(e.process_group_clear(12345))
  self.assertFalse(e.process_group_clear(0));self.assertFalse(e.process_group_clear(True))

 def test_fixture_parent_traversal_refused(self):
  with self.assertRaises(e.Denied):e.fixture_path('/private/tmp/../../Users/example')

 def test_final_output_race(self):
  status={'status':'exited','output_complete':True,'final_cursor':20}
  self.assertFalse(cli.finished(status,10));self.assertTrue(cli.finished(status,20))
  status['output_complete']=False;self.assertFalse(cli.finished(status,20))
 def test_nested_protocol_and_malformed(self):
  for raw in [b'{"data":'+b'['*33+b'0'+b']'*33+b'}',b'['*1500+b'0'+b']'*1500,b'{',b'[]',b'"'+b'x'*e.FRAME_LIMIT+b'"']:
   with self.assertRaises(e.Denied):e.decode_request(raw)
  self.assertEqual(e.decode_request(b'{"data":"[[["}'),{'data':'[[['})
 def test_request_sequence(self):
  state={'last_id':0,'hello':False}
  e.sequence(state,{'id':1,'op':'hello'});e.sequence(state,{'id':2,'op':'status'})
  for number in [2,1,True,'3',None]:
   with self.assertRaises(e.Denied):e.sequence(state,{'id':number,'op':'status'})
  with self.assertRaises(e.Denied):e.sequence(state,{'id':3,'op':'hello'})
  with self.assertRaises(e.Denied):e.sequence({'last_id':0,'hello':False},{'id':1,'op':'status'})
 def test_detach_mixed_chunk_and_partial_write(self):
  self.assertEqual(cli.detach_input(b'partial',b'before\x1dafter'),18)
  self.assertEqual(cli.detach_input(b'',b'\x1d'),0);self.assertEqual(cli.detach_input(b'pending',b''),7)
 def test_absent_inspection_creates_nothing(self):
  with tempfile.TemporaryDirectory(prefix='sk-ro-') as tmp:
   root=Path(tmp).resolve()/'absent'
   with self.assertRaises(OSError):e.Registry(root,readonly=True)
   self.assertFalse(root.exists())
   with contextlib.redirect_stderr(io.StringIO()):self.assertEqual(cli.main(['list','--state',str(root)]),2)
   self.assertFalse(root.exists())
 def test_readonly_database_unchanged(self):
  with tempfile.TemporaryDirectory(prefix='sk-ro-') as tmp:
   root=Path(tmp).resolve()/'state';r=e.Registry(root);r.close();before=(root/'registry.sqlite').read_bytes();r=e.Registry(root,readonly=True)
   try:
    with self.assertRaises(__import__('sqlite3').OperationalError):r.db.execute('CREATE TABLE bad (x)')
   finally:r.close()
   self.assertEqual(before,(root/'registry.sqlite').read_bytes())
 def test_corrupt_inspection_unchanged(self):
  with tempfile.TemporaryDirectory(prefix='sk-ro-') as tmp:
   root=Path(tmp).resolve()/'state';root.mkdir(mode=0o700);db=root/'registry.sqlite';db.write_bytes(b'corrupt');db.chmod(0o600)
   with contextlib.redirect_stderr(io.StringIO()):self.assertEqual(cli.main(['list','--state',str(root)]),2)
   self.assertEqual(db.read_bytes(),b'corrupt')
 def test_durable_timeout_retry_does_not_spawn(self):
  with tempfile.TemporaryDirectory(prefix='sk-start-') as tmp:
   root=Path(tmp).resolve();cwd=root/'project';cwd.mkdir();sid=str(uuid.uuid4());process=Mock()
   with patch.object(cli.subprocess,'Popen',return_value=process) as spawn:
    with self.assertRaisesRegex(e.Denied,sid):cli.start(root/'state',cwd,sid,timeout=0)
    self.assertTrue((root/'state'/(sid+'.startup')).exists())
    with self.assertRaisesRegex(e.Denied,'duplicate launch refused'):cli.start(root/'state',cwd,sid)
    self.assertEqual(spawn.call_count,1)
 def test_socket_path_rejected_before_registry_or_spawn(self):
  with tempfile.TemporaryDirectory(prefix='sk-path-') as tmp:
   base=Path(tmp).resolve();cwd=base/'project';cwd.mkdir();root=base/('r'*110)
   with patch.object(cli.subprocess,'Popen') as spawn:
    with self.assertRaisesRegex(e.Denied,'path too long for macOS socket'):cli.start(root,cwd)
    spawn.assert_not_called()
   self.assertFalse(root.exists())
 def test_client_hello_sequence_not_reset(self):
  import os,stat,struct,json
  class Transport:
   def __init__(self):self.buffer=b'';self.ids=[]
   def settimeout(self,value):pass
   def connect(self,value):pass
   def close(self):pass
   def sendall(self,body):
    request=json.loads(body[4:]);self.ids.append(request['id'])
    self.buffer=e.frame({'v':1,'id':request['id'],'ok':True,'result':{}})
   def recv(self,size):
    part=self.buffer[:size];self.buffer=self.buffer[size:];return part
  with tempfile.TemporaryDirectory(prefix='sk-client-') as tmp:
   root=Path(tmp).resolve();sid=str(uuid.uuid4());key=root/(sid+'.key');key.write_text('synthetic-capability');key.chmod(0o600);transport=Transport()
   registry=Mock();registry.get.return_value={'generation':'synthetic'}
   info=Mock(st_mode=stat.S_IFSOCK|0o600,st_uid=os.getuid())
   with patch.object(e,'Registry',return_value=registry),patch.object(e.os,'lstat',return_value=info),patch.object(e.socket,'socket',return_value=transport),patch.object(e,'peer_uid',return_value=os.getuid()):
    client=e.Client(root,sid);client.request('status');client.close()
   self.assertEqual(transport.ids,[1,2])

if __name__=='__main__':unittest.main()
