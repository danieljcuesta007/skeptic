import json,os,socket,tempfile,threading,unittest
from pathlib import Path
import checkpoints as c
import continuity_socket as runtime
import test_checkpoints as fixtures
class SocketTests(unittest.TestCase):
 setUp=fixtures.Checkpoints.setUp
 g=fixtures.Checkpoints.g
 snap=fixtures.Checkpoints.snap
 def engine(self):return runtime.Engine([c.proposal(self.snap(),'claude','one','continue',pending=['finish'],writer='unknown')])
 def exchange(self,raw,engine=None):
  engine=engine or self.engine();a,b=socket.socketpair();t=threading.Thread(target=runtime.exchange,args=(a,engine,'fixture-token'));t.start()
  try:
   b.settimeout(5);b.sendall(raw);b.shutdown(socket.SHUT_WR);parts=[]
   while True:
    v=b.recv(65536)
    if not v:break
    parts.append(v)
    if b'\n' in v:break
   return json.loads(b''.join(parts))
  finally:b.close();t.join(5);a.close()
 def req(self,request,token='fixture-token',engine=None):return self.exchange(json.dumps({'token':token,'request':request}).encode()+b'\n',engine)
 def test_actual_socketpair_health_and_authorization(self):
  e=self.engine();self.assertEqual(self.req({'op':'health'},engine=e)['result']['transport'],'unix_socket')
  self.assertFalse(self.req({'op':'shutdown'},'wrong',e)['ok']);self.assertFalse(e.stopping)
 def test_malformed_oversized_and_unknown_fields(self):
  for raw in [b'{}\n',b'{bad}\n',b'x'*16385+b'\n',b'{}\n{}\n']:
   self.assertFalse(self.exchange(raw)['ok'])
  self.assertFalse(self.req({'op':'health','path':'/etc/passwd'})['ok'])
 def test_checkpoint_evidence_and_blocked_prepare(self):
  e=self.engine();self.assertTrue(self.req({'op':'checkpoint','session':'one'},engine=e)['result']['fresh'])
  self.assertEqual(self.req({'op':'evidence','session':'one'},engine=e)['result']['evidence'],[])
  p=self.req({'op':'prepare','session':'one','destination':'hermes'},engine=e)['result'];self.assertEqual(p['delivery'],'not_sent');self.assertEqual(p['assessment']['state'],'handoff_blocked')
  (self.root/'code.py').write_text('changed');self.assertFalse(self.req({'op':'checkpoint','session':'one'},engine=e)['result']['fresh'])
 def test_independent_clients_pause_and_disconnect(self):
  e=self.engine();a,b=socket.socketpair();t=threading.Thread(target=runtime.exchange,args=(a,e,'fixture-token'));t.start();b.close();t.join(3);a.close();self.assertFalse(e.stopping)
  self.req({'op':'pause'},engine=e);self.assertEqual(self.req({'op':'observe'},engine=e)['result']['sessions'],[])
  self.req({'op':'resume'},engine=e);self.assertEqual(len(self.req({'op':'sessions'},engine=e)['result']['sessions']),1)
  self.req({'op':'shutdown'},engine=e);self.assertTrue(e.stopping)
 def test_private_root_and_duplicates(self):
  self.root.chmod(0o755)
  with self.assertRaises(c.Rejected):runtime.private_root(self.root)
  self.root.chmod(0o700);p=c.proposal(self.snap(),'claude','one','continue')
  with self.assertRaises(c.Rejected):runtime.Engine([p,p])
 def test_real_bound_listener_when_host_permits(self):
  with tempfile.TemporaryDirectory(prefix='s45-') as t:
   root=Path(t);root.chmod(0o700);probe=socket.socket(socket.AF_UNIX)
   try:probe.bind(str(root/'probe.sock'))
   except PermissionError:self.skipTest('Host denies AF_UNIX bind; socketpair does not prove listener startup')
   finally:probe.close()
   p=c.proposal(self.snap(),'claude','one','continue');thread=threading.Thread(target=runtime.serve,args=(root,[p]));thread.start()
   import time
   try:
    deadline=time.monotonic()+5
    while not (root/'socket-token.json').exists() and time.monotonic()<deadline:time.sleep(.02)
    client=runtime.Client(root);self.assertEqual(client.request({'op':'health'})['engine'],'offline_fixture');client.request({'op':'shutdown'})
   finally:thread.join(8)
   self.assertFalse(thread.is_alive());self.assertFalse((root/'engine.sock').exists())

 def test_missing_socket_and_token_symlink_refused(self):
  with tempfile.TemporaryDirectory(prefix='s45-') as t:
   root=Path(t);root.chmod(0o700);runtime.state.atomic(root,'socket-token.json',{'token':'fixture'})
   with self.assertRaises(OSError):runtime.Client(root).request({'op':'health'})
   (root/'socket-token.json').unlink();(root/'socket-token.json').symlink_to(self.root/'STATUS.md')
   with self.assertRaises(OSError):runtime.Client(root).request({'op':'health'})
 def test_existing_endpoint_never_removed(self):
  with tempfile.TemporaryDirectory(prefix='s45-') as t:
   root=Path(t);root.chmod(0o700);endpoint=root/'engine.sock';endpoint.write_text('preserve owned stale path')
   with self.assertRaises(c.Rejected):runtime.serve(root,[])
   self.assertEqual(endpoint.read_text(),'preserve owned stale path')
