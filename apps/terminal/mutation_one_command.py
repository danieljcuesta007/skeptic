"""Focused planted regressions on disposable copies; no native providers."""
from pathlib import Path
import os,shutil,subprocess,sys,tempfile
here=Path(__file__).resolve().parent
faults=[
 ('row_metadata_leak','open_sessions.py','label = str.__new__(history.SessionLabel, heading)',"label = history.SessionLabel(dict(title=heading, updated='unknown', cwd=cwd or 'unknown', id=sid))",'test_candidate_identification.CandidateIdentificationTests.test_offline_recognizable_context_before_association'),
 ('independent_changed_source_accepted','open_sessions.py',"if receipt and adapter.verify(access, receipt)['appended_bytes']:",'if False:','test_candidate_identification.CandidateIdentificationTests.test_independent_transcript_does_not_bypass_changed_receipt'),
 ('independent_association_lost','session_review.py',"'SESSION ASSOCIATION: ' + selected['session_association'] + '\\n'", "'SESSION ASSOCIATION: unavailable\\n'",'test_candidate_identification.CandidateIdentificationTests.test_independent_transcript_keeps_association_unknown_and_existing_continuation'),
 ('candidate_uuid_scope_lost','open_sessions.py','adapter.discover(access, project, True, sid, None)','adapter.discover(access, project, True, None, None)','test_candidate_identification.CandidateIdentificationTests.test_only_exact_candidates_read_and_duplicate_uuid_reuses_approvals'),
 ('old_request_instead_of_latest','open_sessions.py','request = users[-1] if users else None','request = users[0] if users else None','test_candidate_identification.CandidateIdentificationTests.test_offline_recognizable_context_before_association'),
 ('candidate_promoted_to_confirmed','open_sessions.py',"('UNCONFIRMED' if candidate else 'UNMATCHED')","('CONFIRMED' if candidate else 'UNMATCHED')",'test_candidate_identification.CandidateIdentificationTests.test_offline_recognizable_context_before_association'),
 ('native_pid_mismatch','open_sessions.py',"or data['pid'] != pid",'or False','NativeMetadataTests.test_exact_pid_record_only_and_never_automatic_proof'),
 ('source_append_accepted','switcher.py',"if adapter.verify(access, snapshot)['appended_bytes']: raise host.Denied('Source appended; refresh the review before launch')", "if False: raise host.Denied('Source appended; refresh the review before launch')",'ContinuationTests.test_source_append_during_send_refuses_launch'),
 ('writer_gate_bypassed','switcher.py',"if approval not in ('project-clear', 'project-clear send'):", "if False:",'ContinuationTests.test_writer_decline_never_launches'),
 ('reservation_bypassed','switcher.py',"def tracked_launch(state, model, cwd, packet, vault, task):", "def tracked_launch(state, model, cwd, packet, vault, task):\n    return _tracked_launch(state, model, cwd, packet, vault, task)",'ContinuationTests.test_cooperative_writer_reservation_refuses_second_launch'),
 ('bare_entry_preview_only','switcher.py',"['sessions', 'open', '--continue', '--with', 'codex', '--project', str(Path.home())]", "['sessions', 'open', '--with', 'codex', '--project', str(Path.home())]",'ContinuationTests.test_bare_entry_routes_to_live_continuation_without_history'),
]
for name,file,old,new,test in faults:
 with tempfile.TemporaryDirectory(prefix='sk-one-',dir='/private/tmp') as directory:
  root=Path(directory)
  shutil.copytree(here,root/'terminal',ignore=shutil.ignore_patterns('__pycache__'))
  shutil.copytree(here.parent/'local',root/'local',ignore=shutil.ignore_patterns('__pycache__','node_modules','dist'))
  path=root/'terminal'/file; text=path.read_text()
  if old not in text:raise AssertionError('Fault anchor missing: '+name)
  path.write_text(text.replace(old,new))
  result=subprocess.run([sys.executable,'-B','-W','error::ResourceWarning','-m','unittest',test if test.startswith('test_') else 'test_one_command.'+test],cwd=root/'terminal',
       capture_output=True,text=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),timeout=30)
  if result.returncode==0:raise AssertionError('Fault survived: '+name)
  if 'FAILED (' not in result.stderr:raise AssertionError('Mutation setup failure: '+name+'\n'+result.stderr[-1500:])
  print('Caught planted fault: '+name)
print(str(len(faults))+'/'+str(len(faults))+' one-command faults caught; production sources unchanged')
