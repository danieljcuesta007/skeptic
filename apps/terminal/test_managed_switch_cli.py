"""Three-scope CLI acceptance at provider/permission boundaries, no native providers."""
import contextlib,io,json,tempfile,unittest,uuid
from pathlib import Path
from unittest.mock import Mock,patch
from managed_engine import Registry,Denied
from managed_switch import Manager,initialize
import managed_switch_cli as cli
import managed_cli
import switcher

class Scopes(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='sk-scopes-');self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name).resolve();self.state=self.root/'state';initialize(self.state);self.rows={};self.ids=[]
  r=Registry(self.state)
  for name in ('Daily Brief','Website','Research'):
   cwd=self.root/name;cwd.mkdir();sid=str(uuid.uuid4());r.create(sid,cwd,str(uuid.uuid4()));r.update(sid,status='exited');row=r.get(sid);row.update(provider='claude',reachability='reachable',agent_process_group_quiescent=True,output_complete=True);self.rows[sid]=row;self.ids.append(sid)
  r.close()
  self.permissions=Mock();self.permissions.settings={};self.permissions.read.return_value={};self.permissions.observation={'observed_at':'synthetic','sources':['bounded fixture']}
 def manager(self,root,readonly=False):return Manager(root,inspect=lambda root,sid:dict(self.rows[sid]),readonly=readonly)
 def launch(self,root,cwd,sid,**kwargs):
  r=Registry(root);r.create(sid,cwd,str(uuid.uuid4()));row=r.get(sid);r.close();row.update(provider=kwargs['provider'],status='detached',reachability='reachable');self.rows[sid]=row;return sid,None,row
 def invoke(self,args,answers,launch=None,packets=None):
  self.output=io.StringIO()
  with patch.object(cli,'Manager',side_effect=self.manager),patch.object(switcher,'State',return_value=self.permissions),patch.object(switcher,'assemble',side_effect=packets,return_value=({},'Reviewed bounded project context')) as assemble,patch.object(managed_cli,'start',side_effect=launch or self.launch) as spawn,patch('builtins.input',side_effect=answers),contextlib.redirect_stdout(self.output):
   result=cli.main(['codex','--state',str(self.state),*args])
  return result,spawn,assemble
 def test_current_explicit_identity_and_recovery_not_claimed(self):
  result,spawn,assemble=self.invoke(['--id',self.ids[0],'--task','Daily objective'],['preflight','send'])
  self.assertEqual(result,2);self.assertEqual(spawn.call_count,1);self.assertEqual(assemble.call_args_list[0].kwargs['task'],'Daily objective');self.assertIn('recovery remains unverified',self.output.getvalue())
 def test_selected_two_independent_objectives_and_third_unchanged(self):
  third=dict(self.rows[self.ids[2]])
  # Registry orders stable IDs rather than creation order; select from that display.
  selected=sorted(self.ids)[:2];third_sid=sorted(self.ids)[2];third=dict(self.rows[third_sid])
  result,spawn,assemble=self.invoke(['--select','--task','explicit objectives follow'],['1,2','First objective','Second objective','preflight','send','send'])
  self.assertEqual(result,2);self.assertEqual(spawn.call_count,2);self.assertEqual(self.rows[third_sid],third)
  self.assertEqual([c.kwargs['task'] for c in assemble.call_args_list],['First objective','First objective','Second objective','Second objective'])
 def test_all_excludes_detached_and_reports_reason(self):
  self.rows[self.ids[2]]['status']='detached'
  result,spawn,_=self.invoke(['--all','--task','explicit objectives follow'],['First objective','Second objective','preflight','send','send'])
  self.assertEqual(spawn.call_count,2);self.assertIn('live/detached/suspended',self.output.getvalue());self.assertEqual(self.rows[self.ids[2]]['status'],'detached')
 def test_partial_batch_failure_keeps_independent_launch(self):
  def launcher(*args,**kwargs):
   if not getattr(launcher,'called',False):launcher.called=True;raise Denied('synthetic launch failure')
   return self.launch(*args,**kwargs)
  result,spawn,_=self.invoke(['--all','--task','explicit objectives follow'],['One','Two','Three','preflight','send','send','send'],launch=launcher)
  self.assertEqual(spawn.call_count,3);self.assertIn('Target launch unresolved',self.output.getvalue());self.assertTrue(all(self.rows[sid]['status']=='exited' for sid in self.ids))
 def test_changed_evidence_after_send_never_launched(self):
  result,spawn,_=self.invoke(['--id',self.ids[0],'--task','Objective'],['preflight','send'],packets=[({},'Reviewed context'),({},'Changed context')])
  spawn.assert_not_called();self.assertEqual(result,2)
 def test_confirmation_required(self):
  result,spawn,_=self.invoke(['--id',self.ids[0],'--task','Objective'],['cancel'])
  self.assertEqual(result,1);spawn.assert_not_called()
 def existing_recovery_packet(self,revoke):
  from test_switcher import SwitchTests
  fixture=SwitchTests();fixture.setUp()
  try:
   sid=str(uuid.uuid4());r=Registry(self.state);r.create(sid,fixture.repo,str(uuid.uuid4()));r.update(sid,status='exited');row=r.get(sid);r.close();row.update(provider='claude',reachability='reachable',agent_process_group_quiescent=True,output_complete=True);self.rows[sid]=row
   actual_start=Mock(side_effect=self.launch)
   def answer(prompt):
    if prompt.startswith('Type preflight'):return 'preflight'
    if prompt.startswith('Type send'):
     if revoke:fixture.state.settings['grants']={};fixture.state.save()
     return 'send'
    raise AssertionError('Unexpected question '+prompt)
   with patch.object(cli,'Manager',side_effect=self.manager),patch.object(managed_cli,'start',actual_start),patch('builtins.input',side_effect=answer),contextlib.redirect_stdout(io.StringIO()) as output:
    result=cli.main(['codex','--state',str(self.state),'--id',sid,'--task','Fix input focus','--vault',str(fixture.vault),'--permissions-state',str(fixture.root/'state')])
   self.assertEqual(result,2)
   if revoke:actual_start.assert_not_called()
   else:self.assertEqual(actual_start.call_count,1)
   manager=self.manager(self.state)
   try:
    tx=manager.db.execute('SELECT packet,stage FROM switches WHERE source=?',(sid,)).fetchone()
    self.assertIsNotNone(tx,output.getvalue())
    self.assertIn('FIXTURE_NEXT',Path(tx[0]).read_text());self.assertEqual(tx[1],'target_launching' if revoke else 'recovery_verifying')
   finally:manager.close()
  finally:fixture.tearDown()

 def test_existing_recovery_packet_and_grant_revocation(self):self.existing_recovery_packet(True)
 def test_existing_recovery_packet_fresh_launch(self):self.existing_recovery_packet(False)

 def test_dispatch_missing_managed_identity_fails_closed(self):
  with patch.dict('os.environ',{},clear=True),patch.object(switcher,'State',side_effect=AssertionError('Legacy state must not open')),contextlib.redirect_stderr(io.StringIO()):
   self.assertEqual(switcher.main(['switch','codex']),2)

if __name__=='__main__':unittest.main()
