"""Journal acceptance with synthetic observations/launch boundary; no live PTYs."""
import json,tempfile,unittest,uuid
from pathlib import Path
from unittest.mock import Mock
from managed_engine import Registry,Denied
from managed_switch import Manager,initialize

class Switching(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='sk-switch-');self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve();self.state=self.root/'state';initialize(self.state)
  self.rows={};self.ids=[]
  r=Registry(self.state)
  for name in ('Daily Brief','Website','Research'):
   cwd=self.root/name;cwd.mkdir();sid=str(uuid.uuid4());r.create(sid,cwd,str(uuid.uuid4()));r.update(sid,status='exited',exit_code=0)
   row=r.get(sid);row.update(provider='claude',reachability='reachable',agent_process_group_quiescent=True,output_complete=True);self.rows[sid]=row;self.ids.append(sid)
  r.close();self.manager=Manager(self.state,inspect=lambda root,sid:dict(self.rows[sid]));self.addCleanup(self.manager.close)
  for sid,name in zip(self.ids,('Daily Brief','Website','Research')):self.manager.register(sid,name)
 def prepare(self,index=0,tid=None):
  sid=self.ids[index];return self.manager.prepare(sid,'codex','User-authored objective for '+sid,'Continue '+sid,tid)
 def launch(self,root,cwd,sid,provider,packet):
  source=next(row for row in self.rows.values() if row['cwd']==cwd)
  r=Registry(root);r.create(sid,cwd,str(uuid.uuid4()));row=r.get(sid);r.close();row.update(provider=provider,status='detached',reachability='reachable');self.rows[sid]=row
 def receipt(self,tx):return {key:tx[value] for key,value in [('target','target'),('project','project'),('objective','objective'),('checkpoint','hash'),('provider','provider')]}
 def run_tx(self,tx):
  self.manager.authorize(tx['id'],tx['hash']);self.manager.execute(tx['id'],self.launch);return self.manager.verify(tx['id'],self.receipt(tx))
 def test_three_project_selected_isolation_and_source_preservation(self):
  third=dict(self.rows[self.ids[2]])
  for index in (0,1):
   tx=self.prepare(index);done=self.run_tx(tx);self.assertEqual(done['stage'],'source_retained')
   self.assertEqual(self.manager.details(done['target'])['stable_id'],self.ids[index]);self.assertEqual(self.rows[self.ids[index]]['status'],'exited')
  self.assertEqual(self.rows[self.ids[2]],third)
  self.assertEqual(self.manager.db.execute('SELECT COUNT(*) FROM switches').fetchone()[0],2)
 def test_all_excludes_live_detached_unreachable_same_provider_and_overlap(self):
  self.rows[self.ids[0]]['status']='detached';self.rows[self.ids[1]]['reachability']='unreachable'
  rows=self.manager.preview('codex');self.assertEqual(sum(r['eligible'] for r in rows),1)
  self.rows[self.ids[2]]['provider']='codex';self.assertFalse(any(r['eligible'] for r in self.manager.preview('codex')))
 def test_unresolved_process_group_and_output_drain_excluded(self):
  sid=sorted(self.ids)[0]
  self.rows[sid]['agent_process_group_quiescent']=False
  row=next(r for r in self.manager.preview('codex') if r['id']==sid);self.assertIn('process group',row['exclusion'])
  self.rows[sid]['agent_process_group_quiescent']=True;self.rows[sid]['output_complete']=False
  row=next(r for r in self.manager.preview('codex') if r['id']==sid);self.assertIn('output drain',row['exclusion'])
 def test_duplicate_prepare_and_execute_launch_once(self):
  tx=self.prepare();self.assertEqual(tx,self.prepare(tid=tx['id']));self.manager.authorize(tx['id'],tx['hash']);launch=Mock(side_effect=self.launch)
  self.manager.execute(tx['id'],launch);self.manager.execute(tx['id'],launch);self.assertEqual(launch.call_count,1)
 def test_changed_checkpoint_rejected(self):
  tx=self.prepare();Path(tx['packet']).write_text('Changed')
  with self.assertRaisesRegex(Denied,'changed'):self.manager.authorize(tx['id'],tx['hash'])
 def test_revoked_approval_no_launch(self):
  tx=self.prepare();self.manager.authorize(tx['id'],tx['hash']);self.manager.revoke(tx['id']);launch=Mock()
  with self.assertRaises(Denied):self.manager.execute(tx['id'],launch)
  launch.assert_not_called()
 def test_wrong_receipt_never_reports_recovery(self):
  tx=self.prepare();self.manager.authorize(tx['id'],tx['hash']);self.manager.execute(tx['id'],self.launch)
  for key in ('objective','project','checkpoint','provider','target'):
   receipt=self.receipt(tx);receipt[key]='WRONG'
   with self.assertRaises(Denied):self.manager.verify(tx['id'],receipt)
  self.assertEqual(self.manager.transaction(tx['id'])['stage'],'recovery_verifying')
 def test_operator_ack_is_required_and_bound_to_destination_output(self):
  tx=self.prepare();self.manager.authorize(tx['id'],tx['hash']);self.manager.execute(tx['id'],self.launch)
  self.manager.synthetic=False
  answers={'session':tx['target'],'project':tx['project'],'objective':tx['objective'],'checkpoint':tx['hash'],'provider':tx['provider'],'pending':'Review the next source task'}
  with self.assertRaisesRegex(Denied,'output'):self.manager.acknowledge(tx['id'],answers,b'')
  wrong=dict(answers,objective='different objective')
  with self.assertRaisesRegex(Denied,'did not match'):self.manager.acknowledge(tx['id'],wrong,b'continued objective')
  done=self.manager.acknowledge(tx['id'],answers,b'continued objective')
  self.assertEqual(done['stage'],'source_retained');self.assertEqual(self.manager.details(tx['target'])['task_state'],'operator_verified_recovered')
  self.assertEqual(self.manager.db.execute('SELECT COUNT(*) FROM project_locks WHERE transaction_id=?',(tx['id'],)).fetchone()[0],1)
  evidence=json.loads(self.manager.db.execute('SELECT evidence FROM recovery_acknowledgements WHERE transaction_id=?',(tx['id'],)).fetchone()[0])
  self.assertEqual(evidence['output_sha256'],__import__('hashlib').sha256(b'continued objective').hexdigest());self.assertTrue(evidence['operator_confirmed'])
 def test_project_reservation_releases_only_after_owned_group_quiesces(self):
  done=self.run_tx(self.prepare());target=done['target'];self.assertEqual(self.manager.db.execute('SELECT COUNT(*) FROM project_locks').fetchone()[0],1)
  with self.assertRaisesRegex(Denied,'reservation retained'):self.manager.release_project(target)
  self.rows[target].update(status='exited',agent_process_group_quiescent=True,output_complete=True)
  source_row=next(row for row in self.manager.preview('codex') if row['id']==done['source'])
  self.assertIn('Project reserved',source_row['exclusion'])
  self.assertEqual(self.manager.release_project(target)['session'],target)
  self.assertEqual(self.manager.db.execute('SELECT COUNT(*) FROM project_locks').fetchone()[0],0)
 def test_failed_batch_source_survives_and_other_project_proceeds(self):
  tx=self.prepare();self.manager.authorize(tx['id'],tx['hash'])
  with self.assertRaises(Denied):self.manager.execute(tx['id'],Mock(side_effect=RuntimeError('synthetic fault')))
  self.assertEqual(self.rows[self.ids[0]]['status'],'exited');self.assertEqual(self.run_tx(self.prepare(1))['stage'],'source_retained')
  self.assertEqual(self.manager.transaction(tx['id'])['stage'],'target_launching')
 def test_interrupted_launch_never_duplicates(self):
  tx=self.prepare();self.manager.authorize(tx['id'],tx['hash'])
  with self.manager.db:self.manager.event(tx['id'],'target_launching')
  launch=Mock()
  with self.assertRaisesRegex(Denied,'Interrupted'):self.manager.execute(tx['id'],launch)
  launch.assert_not_called();self.launch(self.state,self.rows[tx['source']]['cwd'],tx['target'],'codex','packet')
  self.assertEqual(self.manager.reconcile(tx['id'])['stage'],'recovery_verifying')
 def test_project_overlap_excludes_other_writer(self):
  self.rows[self.ids[1]]['cwd']=self.rows[self.ids[0]]['cwd']+'/nested';self.rows[self.ids[1]]['status']='live'
  with self.assertRaisesRegex(Denied,'Overlapping'):self.prepare()
 def test_concurrent_prepare_project_lock(self):
  tx=self.prepare()
  with self.assertRaises(Denied):self.prepare()
  self.assertEqual(self.manager.transaction(tx['id'])['stage'],'checkpoint_validated')
 def test_project_identity_changed_before_launch(self):
  tx=self.prepare();self.rows[tx['source']]['ino']=-1
  with self.assertRaisesRegex(Denied,'identity changed'):self.manager.authorize(tx['id'],tx['hash'])
 def test_unknown_schema_no_migration(self):
  with self.manager.db:self.manager.db.execute('UPDATE managed_schema SET version=999')
  with self.assertRaises(Denied):Manager(self.state)
 def test_existing_dirty_and_untracked_work_untouched(self):
  project=Path(self.rows[self.ids[0]]['cwd']);dirty=project/'dirty.txt';dirty.write_text('existing work');secret=project/'.env';secret.write_text('synthetic-private');before={p.name:p.read_bytes() for p in (dirty,secret)}
  self.run_tx(self.prepare());self.assertEqual({p.name:p.read_bytes() for p in (dirty,secret)},before)
 def test_no_cross_session_contamination(self):
  a,b=self.prepare(0),self.prepare(1)
  self.assertNotEqual(a['hash'],b['hash']);self.assertNotIn(self.ids[1],Path(a['packet']).read_text())
  with self.assertRaises(Denied):self.manager.prepare(self.ids[1],'codex','different','objective',a['id'])

if __name__=='__main__':unittest.main()
