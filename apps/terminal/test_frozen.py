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
  with contextlib.redirect_stdout(terminal),patch('sys.stdin.isatty',return_value=True),patch.object(s,'providers',return_value=[model]),patch.object(s,'choose',side_effect=lambda title,*a,**k: 1 if title=='Continue your work' else 0),patch('builtins.input',side_effect=getattr(self, 'approval_inputs', ['project-clear','evidence','send'])):
   result=s.main(['--id',ID,'--cwd',str(self.repo),'--session-root',str(self.storage),'--state-dir',str(self.root/'state'),'--vault',str(self.vault)])
  self.assertEqual(result,0);self.assertEqual(self.file.read_bytes(),before)
  data=json.loads(capture.read_text());self.assertEqual(data['cwd'],str(self.repo));self.assertIn('Continue the reply',data['prompt']);self.assertIn(data['prompt'],terminal.getvalue())

class CombinedReviewTests(FrozenWorkflowTests):
 def test_combined_writer_and_exact_packet_approval(self):
  self.approval_inputs = ['project-clear send']
  FrozenWorkflowTests.test_default_menu_recovery_launches_only_approved_fake(self)

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


class SeamlessContinuationTests(unittest.TestCase):
 def test_compaction_is_not_missing_ancestry(self):
  data=extract([row('u',None,'user','Recover days.'),row('a','u','assistant','Recovery shipped.'),row('boundary',None,'system',''),row('summary','boundary','user','Summary: Recovery shipped. Next: verify morning brief.',isCompactSummary=True)])
  self.assertFalse(data['chain_gap'])
  text=document(data)
  self.assertIn('Latest continuity checkpoint (assistant summary, unverified)',text)
  self.assertIn('verify morning brief',text)
 def test_summary_tail_survives_packet_budget(self):
  data=extract([row('u',None,'user','Old request '+('context '*700)),row('a','u','assistant','Completed '+('detail '*400)),row('b',None,'system',''),row('s','b','user','Earlier work '+('detail '*1500)+' NEXT: verify the morning brief.',isCompactSummary=True)])
  text=document(data)
  self.assertIn('NEXT: verify the morning brief.',text)
  self.assertLessEqual(len(text.encode()),h.SESSION_TEXT_LIMIT)
 def test_recent_followup_and_tool_pending_preserved(self):
  data=extract([row('u',None,'user','Repair parser.'),row('c','u','user','continue'),row('a','c','assistant',[{'type':'tool_use','name':'TodoWrite','input':{'todos':[{'status':'in_progress','content':'Run parser regressions'}]}}])])
  text=document(data)
  self.assertIn('Run parser regressions',text)
  self.assertIn('user-followup',text)
 def test_actual_gap_after_compaction_stays_gap(self):
  data=extract([row('s','missing','user','Summary: repair pending.',isCompactSummary=True)])
  self.assertTrue(data['chain_gap'])

 def test_compaction_boilerplate_never_reaches_receiver(self):
  # Claude Code appends "continue without asking" instructions to every
  # summary; historical text must never instruct the receiving agent.
  summary=('This session is being continued from a previous conversation that ran out of context. The summary below covers the earlier portion of the conversation.\n\nSummary:\n## Work\nRecovered days.\n### Still open / next\n- Verify the morning brief.\n\n'
   'If you need specific details from before compaction (like exact code snippets), read the full transcript at: /x/y.jsonl\nContinue the conversation from where it left off without asking the user any further questions. Resume directly — do not acknowledge the summary.\n\nThe messages after this summary are the most recent messages from before compaction, kept verbatim.')
  text=document(extract([row('b',None,'system',''),row('s','b','user',summary,isCompactSummary=True)]))
  self.assertIn('Verify the morning brief.',text)
  for leaked in ('without asking the user','Resume directly','being continued from a previous','kept verbatim'):self.assertNotIn(leaked,text)
 def test_requests_and_progress_outrank_tool_noise(self):
  rows=[row('u',None,'user','Fix the keychain prompt.'),row('f','u','user','Also keep the old store backed up.'),row('p','f','assistant','Writing the fix in a separate worktree now.')]
  prev='p'
  for n in range(200):
   rows.append(row('t'+str(n),prev,'assistant',[{'type':'tool_use','name':'Bash','input':{'command':'make'}}]));rows.append(row('r'+str(n),'t'+str(n),'user',[{'type':'tool_result','content':'ok'}]));prev='r'+str(n)
  rows.append(row('e',prev,'assistant',[{'type':'tool_use','name':'Edit','input':{'file_path':'/approved/project/Keychain.swift'}}]))
  rows.append(row('l','e','assistant','Tests pass. Next: install the build.'))
  data=extract(rows);data['records']=h.extract_claude([(0,n+1,r) for n,r in enumerate(rows)],ID)['records']
  text=document(data)
  self.assertIn('Also keep the old store backed up.',text)
  self.assertIn('Writing the fix in a separate worktree now.',text)
  self.assertIn('/approved/project/Keychain.swift',text)
  self.assertIn('Bash',text)
  self.assertLessEqual(text.count('Raw tool result withheld'),2)
 def test_evidence_listed_in_source_order(self):
  rows=[row('u',None,'user','Repair parser.')]+[row('a'+str(n),'u' if n==0 else 'a'+str(n-1),'assistant','Step '+str(n)+' done.') for n in range(6)]
  text=document(extract(rows))
  positions=[text.index('Step '+str(n)+' done.') for n in range(5)]
  self.assertEqual(positions,sorted(positions))

 def test_packet_clipping_disclosed_without_missing_records(self):
  data=extract([row('b',None,'system',''),row('s','b','user','Summary: '+('detail '*700),isCompactSummary=True)])
  self.assertTrue(h.session_document(dict(data,updated='',partial=False))['truncated'])

if __name__=='__main__':unittest.main()
