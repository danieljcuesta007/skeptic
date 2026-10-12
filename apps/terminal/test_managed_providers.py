"""Provider contracts at the executable boundary; no model calls."""
import os,tempfile,unittest,uuid
from pathlib import Path
from unittest.mock import Mock
import managed_providers as p
from managed_engine import Denied
class Providers(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='sk-adapter-');self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve();self.exe=self.root/'provider';self.exe.write_text('#!/bin/sh\nexit 0\n');self.exe.chmod(0o700)
 def descriptor(self,provider):return {'provider':provider,'executable':str(self.exe),'version':p.VERSIONS[provider]}
 def test_claude_launch_explicit_id_and_prompt_option_boundary(self):
  sid=str(uuid.uuid4());plan=p.plan('claude',self.root,'--not-an-option',sid,True,self.descriptor('claude'))
  self.assertEqual(plan['argv'],[str(self.exe),'--session-id',sid,'--','--not-an-option']);self.assertEqual(plan['cwd'],str(self.root))
 def test_codex_dedicated_process_and_directory(self):
  plan=p.plan('codex',self.root,'objective',approved=True,descriptor=self.descriptor('codex'))
  self.assertEqual(plan['argv'],[str(self.exe),'--no-daemon','--cd',str(self.root),'--','objective']);self.assertIsNone(plan['native_id'])
 def test_approval_required(self):
  with self.assertRaises(Denied):p.plan('claude',self.root,descriptor=self.descriptor('claude'))
 def test_invalid_arguments(self):
  for prompt in ['\x00','x'*48001]:
   with self.assertRaises(Denied):p.plan('claude',self.root,prompt,approved=True,descriptor=self.descriptor('claude'))
  with self.assertRaises(ValueError):p.plan('claude',self.root,native_id='bad',approved=True,descriptor=self.descriptor('claude'))
  with self.assertRaises(Denied):p.plan('codex',self.root,native_id=str(uuid.uuid4()),approved=True,descriptor=self.descriptor('codex'))
 def test_version_incompatibility(self):
  for version in ('0.0.1','unknown'):
   with self.assertRaises(Denied):p.probe('codex',Mock(return_value=Mock(returncode=0,stdout=version)),lambda _:str(self.exe))
 def test_authentication_not_invented_from_version(self):
  result=p.probe('claude',Mock(return_value=Mock(returncode=0,stdout='2.1.296 (Claude Code)')),lambda _:str(self.exe))
  self.assertIn('not inspected',result['capabilities']['authentication']);self.assertFalse(result['capabilities']['automatic_recovery_verification'])
 def test_missing_and_unsafe_executable(self):
  with self.assertRaises(Denied):p.executable('claude',lambda _:None)
  self.exe.chmod(0o777)
  with self.assertRaises(Denied):p.executable('claude',lambda _:str(self.exe))
 def test_wrong_descriptor_provider(self):
  with self.assertRaises(Denied):p.plan('codex',self.root,approved=True,descriptor=self.descriptor('claude'))
 def test_capability_disclosure(self):
  self.assertFalse(p.CAPABILITIES['process_adoption']);self.assertFalse(p.CAPABILITIES['safe_quiescence']);self.assertFalse(p.CAPABILITIES['supervisor_restart_reattach'])
if __name__=='__main__':unittest.main()
