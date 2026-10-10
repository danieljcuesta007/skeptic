import test_sessions as fixture
import unittest
ID=fixture.ID
from pathlib import Path
from unittest.mock import patch
import switcher as s
import sessions as h
class RecoveryTests(unittest.TestCase):
 setUp=fixture.SessionTests.setUp
 tearDown=fixture.SessionTests.tearDown
 rows=fixture.SessionTests.rows
 write_session=fixture.SessionTests.write_session
 approved=fixture.SessionTests.approved
 discover=fixture.SessionTests.discover
 snapshot=fixture.SessionTests.snapshot
 def test_id_independent_of_project(self):
  before=self.file.read_bytes()
  items=self.approved(lambda:self.adapter.discover(self.access,str(self.root/'unrelated'),session_id=ID))
  self.assertEqual(items[0]['path'],str(self.file.relative_to(self.storage)))
  self.assertEqual(self.file.read_bytes(),before)
 def test_missing_bucket_actionable(self):
  with self.assertRaisesRegex(s.host.Denied,'--id UUID'):self.adapter.discover(self.access,str(self.root/'missing'))
 def test_home_and_separate_repo(self):
  self.write_session(str(Path.home()))
  items=self.approved(lambda:self.adapter.discover(self.access,str(self.repo),session_id=ID))
  self.assertEqual({i['cwd'] for i in items},{str(Path.home()),str(self.repo)})
 def test_conversation_no_git_no_vault(self):
  snapshot=self.snapshot();e={'source_key':str(self.file),'document':h.session_document(snapshot),'conversation_only':True}
  with patch.object(s,'git_state',side_effect=AssertionError('Git must not run')):summary,packet=s.assemble(self.state,str(self.repo),str(self.vault),session=e)
  self.assertIsNone(summary['git']['head']);self.assertIsNone(summary['knowledge']);self.assertIn('Continue the reply',packet);self.assertNotIn('GOVERNING_SOURCE',packet)
 def test_linked_pointer_fallback(self):
  unsafe=self.root/'linked';unsafe.mkdir();(unsafe/'.git').write_text('gitdir: /outside/private')
  snapshot=self.snapshot();e={'source_key':str(self.file),'document':h.session_document(snapshot)}
  summary,packet=s.assemble(self.state,str(unsafe),str(self.root/'absent'),session=e)
  self.assertIsNone(summary['git']['head']);self.assertIn('could not be safely verified',packet);self.assertIn('Continue the reply',packet)
 def test_home_does_not_probe_pointer(self):
  with patch.object(Path,'home',return_value=self.root),patch.object(Path,'lstat',side_effect=AssertionError('No home scan')):self.assertEqual(s.repository(self.root),str(self.root))

 def test_explicit_additional_repository(self):
  snapshot=self.snapshot();e={'source_key':str(self.file),'document':h.session_document(snapshot),'repositories':[str(self.repo)]}
  summary,packet=s.assemble(self.state,str(Path.home()),str(self.root/'absent'),session=e)
  self.assertEqual(summary['additional_repositories'][0]['root'],str(self.repo))
  self.assertIn('Preserve local changes',packet)
