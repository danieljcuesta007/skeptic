import os,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import checkpoints as c
class Checkpoints(unittest.TestCase):
 def setUp(self):
  self.t=tempfile.TemporaryDirectory(prefix='sk-checkpoint-');self.addCleanup(self.t.cleanup);self.root=Path(self.t.name)
  self.g('init','-q');self.g('config','user.email','fixture@example.invalid');self.g('config','user.name','Fixture')
  (self.root/'STATUS.md').write_text('# Fixture\n');(self.root/'code.py').write_text('a=1\n');(self.root/'.gitignore').write_text('evidence.log\n')
  self.g('add','.');self.g('commit','-qm','fixture');(self.root/'evidence.log').write_text('pass\n')
 def g(self,*a):return subprocess.check_output(['git','-C',str(self.root),*a],stderr=subprocess.DEVNULL)
 def snap(self,scope=None):return c.inspect(self.root,scope or ['STATUS.md','code.py'],'fixture','STATUS.md')
 def test_claims(self):
  s=self.snap();p=c.proposal(s,'claude','one','continue',claims=['Feature complete']);self.assertIn('Unverified completion claims',c.markdown(p));self.assertTrue(c.fresh(s))
 def test_dirty_preservation(self):
  (self.root/'code.py').write_text('a=2');self.g('add','code.py');(self.root/'code.py').write_text('a=3');(self.root/'new').write_text('new')
  before=self.g('status','--porcelain=v1','-z');s=self.snap(['STATUS.md','code.py','new']);self.assertEqual(before,self.g('status','--porcelain=v1','-z'));self.assertIn(b'MM code.py',bytes.fromhex(s['status_hex']));self.g('add','code.py');self.assertFalse(c.fresh(s))
 def test_rename_detached(self):
  self.g('mv','code.py','renamed.py');s=self.snap(['STATUS.md','code.py','renamed.py']);self.assertEqual(s['sources']['code.py']['state'],'missing');self.g('checkout','--detach','-q');self.assertIsNone(self.snap()['branch'])
 def test_unborn(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);subprocess.run(['git','init','-q',t],check=True);(r/'STATUS.md').write_text('new');self.assertIsNone(c.inspect(r,['STATUS.md'],'new','STATUS.md')['head'])
 def test_evidence_and_source_stale(self):
  s=self.snap();r=c.receipt(s,['test'],0,'evidence.log');self.assertEqual(c.receipt_state(r,s),'command_passed');(self.root/'evidence.log').write_text('altered');self.assertEqual(c.receipt_state(r,s),'stale');(self.root/'code.py').write_text('different');self.assertFalse(c.fresh(s))
 def test_failed_malformed(self):
  s=self.snap();r=c.receipt(s,['test'],1,'evidence.log');self.assertEqual(c.receipt_state(r,s),'command_failed');r['exit_status']=0
  with self.assertRaises(c.Rejected):c.receipt_state(r,s)
 def test_scope_and_missing(self):
  for scope in [['STATUS.md','../escape'],['STATUS.md','STATUS.md'],['STATUS.md','.env']]:
   with self.assertRaises(c.Rejected):self.snap(scope)
  (self.root/'STATUS.md').unlink()
  with self.assertRaises(c.Rejected):self.snap()
 def test_wrong_checkout(self):
  sub=self.root/'sub';sub.mkdir()
  with self.assertRaises(c.Rejected):c.inspect(sub,['STATUS.md'],'fixture','STATUS.md')
 def test_symlink_and_denied(self):
  (self.root/'link').symlink_to('code.py')
  with self.assertRaises(c.Rejected):self.snap(['STATUS.md','link'])
  with patch('checkpoints.os.open',side_effect=PermissionError):
   with self.assertRaises(c.Rejected):c.fingerprint(self.root,'code.py')
 def test_concurrent_read(self):
  real=os.read;once=[False]
  def read(fd,n):
   v=real(fd,n)
   if not once[0]:once[0]=True;(self.root/'code.py').write_text('changed')
   return v
  with patch('checkpoints.os.read',side_effect=read):
   with self.assertRaises(c.Rejected):c.fingerprint(self.root,'code.py')
 def test_stale_proposal(self):
  s=self.snap();(self.root/'STATUS.md').write_text('new state')
  with self.assertRaises(c.Rejected):c.proposal(s,'codex','one','continue')
 def test_fixture_write_preserves_and_rejects(self):
  import checkpoint_writer as w
  (self.root/'.gitignore').write_text('evidence.log\n.skeptic-*\n');self.g('add','.gitignore');self.g('commit','-qm','ignore bookkeeping')
  s=self.snap();p=c.proposal(s,'claude','one','continue');old=(self.root/'STATUS.md').read_bytes()
  with self.assertRaises(c.Rejected):w.write(p,'wrong',self.root/'STATUS.md')
  r=w.write(p,w.review(p),self.root/'STATUS.md');self.assertTrue((self.root/'STATUS.md').read_bytes().startswith(old));self.assertEqual(r['operation'],'reviewed append; fixture only')
  with self.assertRaises(c.Rejected):w.write(p,w.review(p),self.root/'STATUS.md')
 def test_interrupted_write_and_concurrent_change(self):
  import checkpoint_writer as w
  (self.root/'.gitignore').write_text('evidence.log\n.skeptic-*\n');self.g('add','.gitignore');self.g('commit','-qm','ignore bookkeeping')
  p=c.proposal(self.snap(),'codex','one','continue');old=(self.root/'STATUS.md').read_bytes()
  with patch('checkpoint_writer.os.replace',side_effect=OSError('injected')):
   with self.assertRaises(OSError):w.write(p,w.review(p),self.root/'STATUS.md')
  self.assertEqual((self.root/'STATUS.md').read_bytes(),old)
  with self.assertRaises(c.Rejected):w.write(p,w.review(p),self.root/'STATUS.md',lambda:(self.root/'STATUS.md').write_text('concurrent'))
  self.assertEqual((self.root/'STATUS.md').read_text(),'concurrent')
 def test_observed_execution_receipt(self):
  import sys
  (self.root/'evidence.log').unlink();s=self.snap()
  with self.assertRaises(c.Rejected):c.execute_fixture(s,[sys.executable,'-c','print(123)'],'evidence.log')
  r=c.execute_fixture(s,[sys.executable,'-c','print(123)'],'evidence.log',True);self.assertEqual(c.receipt_state(r,s),'command_passed');self.assertIn('observed subprocess',r['provenance'])
 def test_command_edit_rejects_receipt(self):
  import sys
  (self.root/'evidence.log').unlink();s=self.snap()
  with self.assertRaises(c.Rejected):c.execute_fixture(s,[sys.executable,'-c',"open('code.py','w').write('changed')"],'evidence.log',True)
  self.assertFalse((self.root/'evidence.log').exists())
 def test_external_canonical_root_freshness(self):
  with tempfile.TemporaryDirectory() as t:
   record=Path(t);(record/'STATUS.md').write_text('canonical outside checkout')
   s=c.inspect(self.root,['code.py'],'fixture','STATUS.md',record)
   self.assertTrue(c.fresh(s));(record/'STATUS.md').write_text('new canonical state');self.assertFalse(c.fresh(s))
 def test_worktree_identity_separate_repository_lineage(self):
  with tempfile.TemporaryDirectory() as t:
   other=Path(t)/'other';self.g('worktree','add','-q','--detach',str(other))
   try:
    a=self.snap();b=c.inspect(other,['STATUS.md','code.py'],'fixture','STATUS.md');self.assertEqual(a['common_gitdir'],b['common_gitdir']);self.assertNotEqual(a['gitdir'],b['gitdir']);self.assertNotEqual(a['fingerprint'],b['fingerprint'])
   finally:self.g('worktree','remove',str(other))
 def test_inspection_does_not_run_repository_fsmonitor(self):
  marker=self.root/'monitor-ran';script=self.root/'monitor.sh';script.write_text('#!/bin/sh\ntouch "'+str(marker)+'"\n');script.chmod(0o700)
  self.g('config','core.fsmonitor',str(script));self.snap();self.assertFalse(marker.exists())
