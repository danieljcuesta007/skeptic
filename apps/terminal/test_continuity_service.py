import json,os,subprocess,sys,tempfile,time,unittest
from pathlib import Path
import continuity_service as service
import checkpoints as c
import test_checkpoints as fixtures
class Service(unittest.TestCase):
 setUp=fixtures.Checkpoints.setUp
 g=fixtures.Checkpoints.g
 snap=fixtures.Checkpoints.snap
 def test_process_lifecycle_pause_shutdown_restart(self):
  with tempfile.TemporaryDirectory(prefix='sk-service-') as t:
   root=Path(t);root.chmod(0o700);packages=root/'packages.json';packages.write_text(json.dumps([c.proposal(self.snap(),'claude','one','continue',pending=['finish'])]));packages.chmod(0o600)
   def launch():
    p=subprocess.Popen([sys.executable,'-B',str(Path(service.__file__)),'--state',str(root),'--packages',str(packages)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    return p
   def until(predicate):
    deadline=time.monotonic()+8
    while time.monotonic()<deadline:
     try:
      data=service.load_observation(root)
      if predicate(data):return data
     except (FileNotFoundError,c.Rejected):pass
     time.sleep(.05)
    self.fail('Service observation timeout')
   p=launch()
   try:
    self.assertEqual(until(lambda d:d['engine']=='offline_fixture')['sessions'][0]['activity'],'unknown')
    p.stdin.write(b'pause\n');p.stdin.flush();self.assertEqual(until(lambda d:d['monitoring']=='paused')['sessions'],[])
    p.stdin.write(b'resume\n');p.stdin.flush();until(lambda d:d['monitoring']=='fixture_only')
    p.stdin.write(b'shutdown\n');p.stdin.flush();out,err=p.communicate(timeout=8);self.assertEqual(p.returncode,0,err.decode());self.assertEqual(service.load_observation(root)['engine'],'stopped')
   finally:
    if p.poll() is None:p.kill();p.communicate()
   p=launch()
   try:
    until(lambda d:d['engine']=='offline_fixture');p.communicate(input=b'shutdown\n',timeout=8);self.assertEqual(p.returncode,0)
   finally:
    if p.poll() is None:p.kill();p.communicate()
 def test_disconnected_permissions_and_malformed(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);root.chmod(0o700);service.atomic(root,'observation.json',{'version':1,'sessions':[],'observed_epoch':0})
   self.assertEqual(service.load_observation(root)['engine'],'disconnected')
   (root/'observation.json').chmod(0o644)
   with self.assertRaises(c.Rejected):service.load_observation(root)
   (root/'observation.json').chmod(0o600);(root/'observation.json').write_text('{}')
   with self.assertRaises(c.Rejected):service.load_observation(root)
 def test_default_never_discovers(self):
  self.assertEqual(service.load_observation(None)['sessions'],[]);self.assertEqual(service.load_observation(None)['monitoring'],'disabled')

 def test_future_and_nonfinite_heartbeat_not_running(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);root.chmod(0o700)
   for stamp in (time.time()+1000,float('nan'),float('inf'),True):
    service.atomic(root,'observation.json',{'version':1,'sessions':[],'observed_epoch':stamp})
    self.assertEqual(service.load_observation(root)['engine'],'disconnected')
 def test_linked_token_refused(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t);service.atomic(root,'token.json',{'token':'fixture'})
   os.link(root/'token.json',root/'linked.json')
   with self.assertRaises(c.Rejected):service.read_private(root/'token.json')
