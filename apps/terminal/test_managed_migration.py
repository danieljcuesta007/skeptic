"""Reversible archival migration rehearsal using temporary synthetic registries only."""
import json,tempfile,unittest,uuid
from pathlib import Path
import managed_migration as migration
from managed_engine import Denied,Registry
from managed_switch import initialize

class MigrationRehearsal(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='sk-migrate-');self.addCleanup(self.tmp.cleanup)
  self.root=Path(self.tmp.name).resolve();self.source=self.root/'source';self.destination=self.root/'destination'
  initialize(self.source);self.sid=str(uuid.uuid4());self.project=self.root/'project';self.project.mkdir()
  registry=Registry(self.source)
  registry.create(self.sid,self.project,str(uuid.uuid4()))
  with registry.db:registry.db.execute("UPDATE sessions SET status='exited',supervisor=NULL,agent=NULL WHERE id=?",(self.sid,))
  registry.close()
  (self.source/(self.sid+'.startup')).write_text(json.dumps({'session':self.sid,'cwd':str(self.project),'synthetic':True}));(self.source/(self.sid+'.startup')).chmod(0o600)
  (self.source/'sample.handoff').write_text('Synthetic objective only');(self.source/'sample.handoff').chmod(0o600)
 def test_plan_copy_and_rollback_preserve_source_and_snapshot(self):
  before={path.name:path.read_bytes() for path in self.source.iterdir() if path.is_file()}
  plan=migration.inspect(self.source,self.destination)
  with self.assertRaisesRegex(Denied,'plan changed'):migration.apply(self.source,self.destination,'wrong')
  copied=migration.apply(self.source,self.destination,plan['plan_hash'])
  self.assertEqual((self.destination/'registry.sqlite').read_bytes(),(self.source/'registry.sqlite').read_bytes())
  self.assertEqual((self.destination/'sample.handoff').read_text(),'Synthetic objective only')
  self.assertEqual({path.name:path.read_bytes() for path in self.source.iterdir() if path.is_file()},before)
  backup=Path(migration.rollback(self.destination,copied['migration_id']))
  self.assertFalse(self.destination.exists());self.assertTrue(backup.is_dir());self.assertTrue(self.source.is_dir())
  self.assertEqual((backup/'registry.sqlite').read_bytes(),before['registry.sqlite'])
 def test_active_or_owned_process_session_refused(self):
  registry=Registry(self.source)
  with registry.db:registry.db.execute("UPDATE sessions SET status='detached' WHERE id=?",(self.sid,))
  registry.close()
  with self.assertRaisesRegex(Denied,'Only archived synthetic'):migration.inspect(self.source,self.destination)
 def test_source_change_after_preview_refused(self):
  plan=migration.inspect(self.source,self.destination)
  with (self.source/'sample.handoff').open('a') as stream:stream.write('changed')
  with self.assertRaisesRegex(Denied,'plan changed'):migration.apply(self.source,self.destination,plan['plan_hash'])
  self.assertFalse(self.destination.exists())
 def test_rollback_refuses_new_destination_files(self):
  plan=migration.inspect(self.source,self.destination);copied=migration.apply(self.source,self.destination,plan['plan_hash'])
  extra=self.destination/'user-added.txt';extra.write_text('keep');extra.chmod(0o600)
  with self.assertRaisesRegex(Denied,'Destination changed'):migration.rollback(self.destination,copied['migration_id'])
  self.assertEqual(extra.read_text(),'keep');self.assertTrue(self.destination.exists())

if __name__=='__main__':unittest.main()
