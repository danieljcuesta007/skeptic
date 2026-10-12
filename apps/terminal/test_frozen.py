import unittest
from unittest.mock import patch
from pathlib import Path
import sessions as h
import switcher as s
ID='11111111-2222-3333-4444-555555555555'
def row(uid,parent,role,text,**kw):
 return {'sessionId':ID,'type':role,'uuid':uid,'parentUuid':parent,'message':{'content':text},**kw}
def extract(rows):return h.extract_claude([(0,n+1,r) for n,r in enumerate(rows)],ID)
def document(data):return h.session_document(dict(data,updated='2026-10-09',partial=False))['text']
class FrozenTests(unittest.TestCase):
 def test_quota_not_task(self):
  data=extract([row('u',None,'user','Implement recovery. Preserve all dirty work.'),row('a','u','assistant','Parser remains unfinished.'),row('q','a','assistant',"You've hit your limit · resets Sunday",isApiErrorMessage=True)])
  text=document(data);self.assertIn('Implement recovery',text);self.assertIn('Parser remains unfinished',text);self.assertNotIn("You've hit your limit",text)
 def test_broken_chain_recovers_substantive_request(self):
  data=extract([row('u',None,'user','Implement accurate continuity, no deployment.'),row('a','u','assistant','Index added; tests still pending.'),row('q','missing','assistant',"You've hit your limit · resets Sunday",isApiErrorMessage=True)])
  text=document(data);self.assertTrue(data['chain_gap']);self.assertIn('Implement accurate continuity',text);self.assertIn('outside recovered chain',text);self.assertTrue(any(r['role'].startswith('historical-user-request') for r in data['records']));self.assertIn('Index added',text);self.assertIn('outside recovered chain; unverified',text)
 def test_detached_quota_root(self):
  data=extract([row('u',None,'user','Finish the switching engine.'),row('q',None,'assistant','Usage limit reached')]);self.assertIn('Finish the switching engine',document(data));self.assertTrue(data['chain_gap'])
 def test_gap_no_false_completion(self):
  data=extract([row('a',None,'assistant','ALL WORK COMPLETE'),row('q','missing','assistant','Usage limit reached')]);self.assertIn('unverified',document(data));self.assertIn('NOT recovered',document(data))
 def test_long_quota_tail_preserves_task(self):
  rows=[row('u',None,'user','Fix the parser and keep Claude intact.')]
  for n in range(2000):rows.append(row('q'+str(n),'u' if n==0 else 'q'+str(n-1),'assistant','Usage limit reached'))
  text=document(extract(rows));self.assertIn('Fix the parser',text);self.assertLess(len(text.encode()),h.SESSION_TEXT_LIMIT)
 def test_original_objective_and_latest_request_survive_tools(self):
  rows=[row('goal',None,'user','Build provider-neutral switching. Never deploy.'),row('u','goal','user','Fix the transcript parser next.')]
  for n in range(500):rows.append(row('t'+str(n),'u' if n==0 else 't'+str(n-1),'assistant',[{'type':'tool_use','name':'Read','input':{'file_path':'/approved/project/file.md'}}]))
  text=document(extract(rows));self.assertIn('Never deploy',text);self.assertIn('Fix the transcript parser next',text)
 def test_unicode_briefing_byte_limit(self):
  data=extract([row('u',None,'user','实现任务 '+('🧠'*1900))])
  self.assertLessEqual(len(document(data).encode('utf-8')),h.SESSION_TEXT_LIMIT)
 def test_message_clipping_disclosed(self):
  data=extract([row('u',None,'user','Important instructions '+('detail '*1800))])
  snapshot=dict(data,updated='2026-10-09',partial=False)
  self.assertTrue(h.session_document(snapshot)['truncated'])
 def test_control_followups_do_not_replace_substantive_task(self):
  data=extract([row('u',None,'user','Implement the continuation engine; leave drafts unsent.'),row('c','u','user','continue'),row('q','missing','assistant','Usage limit reached')])
  text=document(data);self.assertIn('Latest recorded human request (completion unverified):\nImplement the continuation engine',text)
 def test_do_not_filter_actual_quota_feature_request(self):
  self.assertFalse(h.provider_notice('Implement a rate limit handler.'))
 def test_recovered_secrets_withheld(self):
  data=extract([row('u',None,'user','Implement recovery\npassword=SECRETVALUE'),row('q','missing','assistant','Usage limit reached')]);text=document(data);self.assertIn('Implement recovery',text);self.assertNotIn('SECRETVALUE',text)
 def test_missing_body_types(self):
  data=extract([row('u',None,'user',[{'type':'thinking','thinking':'HIDDEN'}]),row('q',None,'assistant','Usage limit reached')]);self.assertNotIn('HIDDEN',document(data))
 def test_explicit_native_model_safe_argv(self):
  calls=[];model=s.requested_model({'id':'codex','executable':'/fake/codex','local':False},'user-chosen-model')
  s.launch(model,'/tmp','untrusted $(command)',lambda argv,**kw:calls.append((argv,kw)) or type('Result',(),{'returncode':0})())
  self.assertEqual(calls[0][0],['/fake/codex','--model','user-chosen-model','--','untrusted $(command)']);self.assertNotIn('shell',calls[0][1])
 def test_invalid_model_and_no_local_download(self):
  with self.assertRaises(s.host.Denied):s.requested_model({'local':False},'--unsafe')
  with self.assertRaises(s.host.Denied):s.requested_model({'local':True,'model':'installed'},'new-model')
 def test_auth_and_quota_unknown(self):
  models=s.providers(which=lambda name:'/fake/'+name,fetch=lambda url:None)
  self.assertIn('authentication/quota/model unknown',models[0]['availability'])

import test_sessions as fixture
import contextlib,io,json,tempfile
class FrozenWorkflowTests(unittest.TestCase):
 setUp=fixture.SessionTests.setUp
 tearDown=fixture.SessionTests.tearDown
 rows=fixture.SessionTests.rows
 write_session=fixture.SessionTests.write_session
 approved=fixture.SessionTests.approved
 discover=fixture.SessionTests.discover
 snapshot=fixture.SessionTests.snapshot
 def test_default_menu_recovery_launches_only_approved_fake(self):
  self.approved(lambda:self.adapter.discover(self.access,self.origin,session_id=ID))
  self.snapshot()
  fake=self.root/'fake-codex';capture=self.root/'capture.json'
  fake.write_text('#!'+__import__('sys').executable+'\nimport os,sys,json\nfrom pathlib import Path\nPath('+repr(str(capture))+').write_text(json.dumps({"cwd":os.getcwd(),"prompt":sys.argv[-1]}))\n');fake.chmod(0o700)
  model={'id':'codex','label':'Fake Codex','availability':'Synthetic installed; auth unknown','executable':str(fake),'local':False}
  before=self.file.read_bytes()
  class Terminal(io.StringIO):
   def isatty(self):return True
  terminal=Terminal()
  with contextlib.redirect_stdout(terminal),patch('sys.stdin.isatty',return_value=True),patch.object(s,'providers',return_value=[model]),patch.object(s,'choose',return_value=0),patch('builtins.input',side_effect=['project-clear','evidence','send']):
   result=s.main(['--id',ID,'--cwd',str(self.repo),'--session-root',str(self.storage),'--state-dir',str(self.root/'state'),'--vault',str(self.vault)])
  self.assertEqual(result,0);self.assertEqual(self.file.read_bytes(),before)
  data=json.loads(capture.read_text());self.assertEqual(data['cwd'],str(self.repo));self.assertIn('Continue the reply',data['prompt']);self.assertIn(data['prompt'],terminal.getvalue())

class RealRecoveryRegressionTests(unittest.TestCase):
 def test_attachment_bridge_and_last_work(self):
  data=extract([row('u',None,'user','Build the shared engine.'),row('a','u','assistant','Lock repair remains pending.'),row('bridge','a','attachment','PRIVATE_ATTACHMENT'),row('q','bridge','assistant','Usage limit reached')]);text=document(data)
  self.assertFalse(data['chain_gap']);self.assertIn('Lock repair remains pending',text);self.assertNotIn('PRIVATE_ATTACHMENT',text)
 def test_machine_records_never_replace_human(self):
  data=extract([row('u',None,'user','Repair the engine.'),row('n','u','user','<task-notification>Review finished</task-notification>'),row('c','n','user','<command-name>/rate-limit-options</command-name>'),row('o','c','user','<local-command-stdout>Claude Code will continue automatically at Sunday.</local-command-stdout>')])
  self.assertEqual([r['message_id'] for r in data['records'] if r['role']=='user'],['u'])
 def test_long_brief_keeps_tail(self):
  text=document(extract([row('u',None,'user','Build the engine. '+('context '*4000)+'FINAL CONSTRAINT: never publish.')]))
  self.assertIn('FINAL CONSTRAINT: never publish',text);self.assertIn('omitted',text);self.assertLessEqual(len(text.encode()),h.SESSION_TEXT_LIMIT)
 def test_absent_task_stays_absent(self):
  text=document(extract([row('n',None,'user','<task-notification>done</task-notification>'),row('c','n','user','<local-command-stdout>wait</local-command-stdout>')]))
  self.assertIn('Substantive user task NOT recovered',text)
 def test_unfinished_status_not_inferred(self):
  self.assertIn('Current unfinished task: NOT established',document(extract([row('u',None,'user','Build it.'),row('a','u','assistant','All done.')])) )
 def test_real_missing_parent_remains_gap(self):
  data=extract([row('u',None,'user','Historical task'),row('q','missing','assistant','Usage limit reached')]);self.assertTrue(data['chain_gap']);self.assertIn('outside recovered chain',document(data))
 def test_legitimate_quota_request_and_pasted_brief(self):
  data=extract([row('u',None,'user','<pasted_content>Implement quota notifications.</pasted_content>')]);self.assertEqual(data['records'][0]['role'],'user')
 def test_unknown_structural_bridge_body_withheld(self):
  data=extract([row('u',None,'user','Keep task'),row('b','u','structural-event','PRIVATE_BODY'),row('q','b','assistant','Usage limit reached')]);self.assertFalse(data['chain_gap']);self.assertNotIn('PRIVATE_BODY',document(data))
 def test_notifications_on_broken_branch_not_tasks(self):
  data=extract([row('u',None,'user','Real historical task'),row('n','u','user','<task-notification>done</task-notification>'),row('q','missing','assistant','Usage limit reached')]);self.assertEqual([r['message_id'] for r in data['records'] if r['role'].startswith('historical-user-request')],['u'])
 def test_review_summary_readable(self):
  import contextlib,io
  packet='EXACT_UNTRUSTED_PACKET'
  evidence={'document':{'text':packet,'truncated':False},'chain_gap':False,'partial':False,'source_key':'/synthetic/session'}
  out=io.StringIO()
  with contextlib.redirect_stdout(out):s.review_summary({'repository':'/synthetic','knowledge':'/synthetic/vault','git':{'branch':'main','head':'a'*40,'changes':' M file'}},evidence)
  self.assertIn(packet,out.getvalue());self.assertNotIn('"changes"',out.getvalue())

 def test_latest_request_survives_anchor_reordering(self):
  rows=[row('original',None,'user','Original objective'),row('latest','original','user','LATEST requested repair')]
  for n in range(100):rows.append(row('tool'+str(n),'latest' if n==0 else 'tool'+str(n-1),'assistant',[{'type':'tool_use','name':'Read','input':{}}]))
  self.assertTrue(document(extract(rows)).startswith('Latest recorded human request (completion unverified):\nLATEST requested repair'))

if __name__=='__main__':unittest.main()
