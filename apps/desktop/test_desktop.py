import io,json,os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'local'))
from app import Registry
from preferences import Preferences
import backend
import importlib.util
spec=importlib.util.spec_from_file_location("desktop_build",Path(__file__).parent/"build.py");build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)
class DesktopTests(unittest.TestCase):
 def test_preferences_restart(self):
  with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
   r=Registry(Path(tmp)/'state');p=Preferences(r.statefd)
   self.assertEqual(p.request({'action':'get'}),{'theme':'system','welcomed':False})
   p.request({'action':'save','theme':'dark','welcomed':True});r.close()
   r=Registry(Path(tmp)/'state')
   try:self.assertEqual(Preferences(r.statefd).request({'action':'get'})['theme'],'dark');self.assertEqual(r.active,{})
   finally:r.close()
 def test_bad_settings(self):
  with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
   r=Registry(Path(tmp)/'state')
   try:
    for d in [{'action':'save','theme':'remote','welcomed':True},{'action':'save','theme':'dark','welcomed':1},{'action':'get','path':'/etc'}]:
     with self.assertRaises(ValueError):Preferences(r.statefd).request(d)
   finally:r.close()
 def test_symlink_preferences(self):
  with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp:
   state=Path(tmp)/'state';r=Registry(state);(state/'preferences.json').symlink_to('/etc/passwd')
   try:
    with self.assertRaises(OSError):Preferences(r.statefd).request({'action':'get'})
   finally:r.close()
 def test_lease_shutdown_ephemeral(self):
  calls=[]
  class Server:
   origin='http://127.0.0.1:49152'
   def __init__(self,r,port):self.port=port;calls.append(('port',port))
   def __enter__(self):return self
   def __exit__(self,*args):calls.append('close')
   def serve_forever(self):calls.append('serve')
   def shutdown(self):calls.append('shutdown')
  with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp,patch.object(backend,'LocalServer',Server):
   output=io.StringIO();backend.serve(Path(tmp)/'state',io.BytesIO(),output)
   self.assertEqual(json.loads(output.getvalue())['origin'],Server.origin);self.assertIn(('port',0),calls);self.assertIn('shutdown',calls);self.assertIn('close',calls)
 def test_bundle_allowlist(self):
  with tempfile.TemporaryDirectory(dir="/private/tmp") as tmp,patch.object(build.subprocess,'run') as compile:
   target=build.build(Path(tmp)/'Skeptic.app')
   files=[str(p.relative_to(target)) for p in target.rglob('*') if p.is_file()]
   self.assertFalse(any('usage.json' in p or 'projects.json' in p or '.claude' in p for p in files))
   args=compile.call_args.args[0];self.assertEqual(args[0],'swiftc');self.assertNotIn('shell',compile.call_args.kwargs)
 def test_acceptance_state_explicit_private_fixture(self):
  with tempfile.TemporaryDirectory(dir='/private/tmp') as tmp:
   root=Path(tmp);root.chmod(0o700)
   with patch.dict(os.environ,{'SKEPTIC_DESKTOP_STATE':str(root)}):self.assertEqual(backend.selected_state(),root.resolve())
   root.chmod(0o755)
   with patch.dict(os.environ,{'SKEPTIC_DESKTOP_STATE':str(root)}),self.assertRaises(ValueError):backend.selected_state()
   with patch.dict(os.environ,{'SKEPTIC_DESKTOP_STATE':str(Path.home())}),self.assertRaises(ValueError):backend.selected_state()
 def test_navigation_and_termination(self):
  source=(Path(__file__).parent/'Skeptic.swift').read_text()
  self.assertIn('url.host==allowed.host',source);self.assertIn('url.port==allowed.port',source);self.assertIn('decisionHandler(.cancel)',source);self.assertIn('fileHandleForWriting.close()',source);self.assertIn('applicationShouldTerminateAfterLastWindowClosed',source)
if __name__=='__main__':unittest.main()
