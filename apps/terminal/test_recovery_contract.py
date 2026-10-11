import itertools,tempfile,unittest
from pathlib import Path
import checkpoints as c
import recovery_contract as r
import continuity_adapters as a
import test_checkpoints as fixtures
class Recovery(unittest.TestCase):
 setUp=fixtures.Checkpoints.setUp
 g=fixtures.Checkpoints.g
 snap=fixtures.Checkpoints.snap
 def package(self,agent='claude'):
  return c.proposal(self.snap(),agent,agent+'-session','finish feature',claims=['done'],pending=['implement feature'],writer='clear')
 def test_six_directions(self):
  for source,target in itertools.permutations(a.AGENTS,2):
   p=self.package(source);assessment=r.assess(p,target,'confirmed','clear',True)
   ack=r.reconcile(p,self.root,'fixture',target+'-session',target,p['pending'],True)
   self.assertEqual(r.complete(p,assessment,ack,p['fingerprint'])['state'],'handoff_complete')
 def test_false_success_blocked(self):
  p=self.package();assessment=r.assess(p,'hermes','confirmed','clear',True)
  for ack in [None,{'state':'destination_launched'}]:
   with self.assertRaises(c.Rejected):r.complete(p,assessment,ack,p['fingerprint'])
  for identity,writer,available in [('unknown','clear',True),('confirmed','active',True),('confirmed','clear',False)]:self.assertEqual(r.assess(p,'hermes',identity,writer,available)['state'],'handoff_blocked')
 def test_wrong_identity_and_changed_source(self):
  p=self.package()
  with self.assertRaises(c.Rejected):r.reconcile(p,self.root,'wrong','dest','hermes',p['pending'],True)
  (self.root/'code.py').write_text('new')
  self.assertEqual(r.assess(p,'hermes','confirmed','clear',True)['state'],'handoff_blocked')
 def test_returning_agent_latest(self):
  old=self.package();(self.root/'code.py').write_text('hermes work');new=self.package('hermes')
  self.assertFalse(c.fresh(old['snapshot']));self.assertNotEqual(old['snapshot']['fingerprint'],new['snapshot']['fingerprint'])
  ack=r.reconcile(new,self.root,'fixture','return-claude','claude',new['pending'],True);self.assertEqual(ack['source_fingerprint'],new['snapshot']['fingerprint'])
 def test_batch_and_unknown_observation(self):
  p=self.package();out=r.batch([{'package':p,'identity':'confirmed','writer':'clear','available':True},{'package':self.package('codex'),'writer':'conflict'}],'hermes');self.assertEqual([x['state'] for x in out],['awaiting_approval','handoff_blocked'])
  o=r.observation([p]);self.assertEqual(o['sessions'][0]['activity'],'unknown');self.assertEqual(o['sessions'][0]['verification'],'unknown');self.assertFalse(o['capabilities']['live_switch'])
 def test_adapter_events_and_skill_packaging(self):
  e=a.event('claude',{'hook_event_name':'Stop','session_id':'one','cwd':str(self.root)});self.assertEqual(e['writer'],'unknown');self.assertEqual(e['automatic_actions'],[])
  with self.assertRaises(c.Rejected):a.event('claude',{'hook_event_name':'fake'})
  source=Path(__file__).resolve().parents[2]/'skills/skeptic'
  for agent in a.AGENTS:
   result=a.package_skill(source,self.root/agent,agent);self.assertFalse(result['runtime_loaded']);self.assertTrue((self.root/agent/'SKILL.md').exists())
   with self.assertRaises(c.Rejected):a.package_skill(source,self.root/agent,agent)
 def test_real_fixture_claude_hermes_return_scenario(self):
  import sys
  (self.root/'code.py').write_text('value = 1\n');self.g('add','code.py');(self.root/'unfinished.txt').write_text('preserve this')
  outgoing=c.proposal(self.snap(['STATUS.md','code.py','unfinished.txt']),'claude','source','raise value to 2',claims=['feature done'],pending=['raise value to 2'],failures=['interrupted tool; completion unverified'],writer='clear')
  before=self.g('status','--porcelain=v1','-z');ack=r.reconcile(outgoing,self.root,'fixture','hermes-target','hermes',outgoing['pending'],True);self.assertEqual(before,self.g('status','--porcelain=v1','-z'))
  r.complete(outgoing,r.assess(outgoing,'hermes','confirmed','clear',True),ack,outgoing['fingerprint'])
  (self.root/'code.py').write_text('value = 2\n');(self.root/'evidence.log').unlink()
  snapshot=self.snap(['STATUS.md','code.py','unfinished.txt']);receipt=c.execute_fixture(snapshot,[sys.executable,'-c',"assert open('code.py').read() == 'value = 2\\n'"],'evidence.log',True)
  returning=c.proposal(snapshot,'hermes','hermes-target','finish documentation',claims=['value updated'],pending=['documentation'],receipts=[receipt],decisions=['Hermes changed value to 2'],writer='clear')
  ack=r.reconcile(returning,self.root,'fixture','claude-return','claude',returning['pending'],True)
  result=r.complete(returning,r.assess(returning,'claude','confirmed','clear',True),ack,returning['fingerprint'])
  self.assertEqual(result['state'],'handoff_complete');self.assertFalse(c.fresh(outgoing['snapshot']));self.assertEqual((self.root/'unfinished.txt').read_text(),'preserve this')
  self.assertEqual(c.receipt_state(receipt,snapshot),'command_passed');self.assertIn(b'?? unfinished.txt',self.g('status','--porcelain=v1','-z'))

 def test_completion_rejects_forged_destination_identity(self):
  p=self.package();assessment=r.assess(p,'hermes','confirmed','clear',True)
  valid=r.reconcile(p,self.root,'fixture','destination','hermes',p['pending'],True)
  for field,value in [('version',2),('project_id','wrong'),('checkout','/wrong'),('session_id',''),('session_id',None)]:
   with self.subTest(field=field),self.assertRaises(c.Rejected):r.complete(p,assessment,{**valid,field:value},p['fingerprint'])

 def test_real_fixture_codex_return_preserves_dirty_work(self):
  (self.root/'code.py').write_text('codex pending = 1')
  (self.root/'untracked.txt').write_text('keep')
  self.g('add','code.py')
  old=c.proposal(self.snap(['STATUS.md','code.py','untracked.txt']),'claude','claude-start','continue',pending=['finish'],writer='clear')
  ack=r.reconcile(old,self.root,'fixture','codex-dest','codex',old['pending'],True)
  before=self.g('status','--porcelain=v1','-z');r.complete(old,r.assess(old,'codex','confirmed','clear',True),ack,old['fingerprint']);self.assertEqual(before,self.g('status','--porcelain=v1','-z'))
  (self.root/'code.py').write_text('codex completed = 2')
  new=c.proposal(self.snap(['STATUS.md','code.py','untracked.txt']),'codex','codex-dest','review',pending=['review'],writer='clear')
  ack=r.reconcile(new,self.root,'fixture','claude-return','claude',new['pending'],True)
  self.assertEqual(r.complete(new,r.assess(new,'claude','confirmed','clear',True),ack,new['fingerprint'])['verification'],'offline_contract_only')
  self.assertFalse(c.fresh(old['snapshot']));self.assertEqual((self.root/'untracked.txt').read_text(),'keep')
  with self.assertRaises(c.Rejected):r.complete(new,r.assess(new,'claude','confirmed','clear',True),{**ack,'pending':[]},new['fingerprint'])
