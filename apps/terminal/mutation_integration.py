"""Socket-independent behavioral faults; modules restored after each planted bug."""
import contextlib,io,types,unittest
from pathlib import Path
import test_managed_hardening as h
import test_managed_providers as p
import test_managed_switch as s
import test_managed_migration as m
import managed_switch
faults=[
 ('fixture-path-traversal',h,'e',"if '..' in path.parts:",'if False:',h.Hardening,'test_fixture_parent_traversal_refused'),
 ('reset-hello-id',h,'e',"self.request('hello')","self.request('hello'); self.number = 0",h.Hardening,'test_client_hello_sequence_not_reset'),
 ('stale-final-cursor',h,'cli',"cursor>=status['final_cursor']",'cursor>=0',h.Hardening,'test_final_output_race'),
 ('lost-detach-input',h,'cli',"return len(pending)+len(incoming.replace(b'\\x1d',b'',1))",'return 0',h.Hardening,'test_detach_mixed_chunk_and_partial_write'),
 ('unbounded-json-depth',h,'e','if depth > 32:','if depth > 10000:',h.Hardening,'test_nested_protocol_and_malformed'),
 ('accept-repeated-ids',h,'e',"number <= state['last_id']",'number < 0',h.Hardening,'test_request_sequence'),
 ('mutating-inspection',h,'e','if readonly:\n            info = self.root.stat()', 'if False:\n            info = self.root.stat()',h.Hardening,'test_absent_inspection_creates_nothing'),
 ('duplicate-startup',h,'cli','if existing:', 'if False:',h.Hardening,'test_durable_timeout_retry_does_not_spawn'),
 ('provider-no-approval',p,'p','if not approved:', 'if False:',p.Providers,'test_approval_required'),
 ('shared-codex-server',p,'p',"argv+=['--no-daemon','--cd',str(cwd)]", "argv+=['--cd',str(cwd)]",p.Providers,'test_codex_dedicated_process_and_directory'),
 ('unknown-provider-version',p,'p',"found[0]!=VERSIONS[provider]",'False',p.Providers,'test_version_incompatibility'),
]
for name,module,attribute,old,new,case,method in faults:
 original=getattr(module,attribute);source=Path(original.__file__).read_text();assert source.count(old)==1,name
 mutated=types.ModuleType(original.__name__);mutated.__file__=original.__file__;exec(compile(source.replace(old,new),original.__file__,'exec'),mutated.__dict__)
 setattr(module,attribute,mutated)
 try:
  result=unittest.TestResult()
  with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):case(method).run(result)
  assert result.failures and not result.errors,(name,result.failures,result.errors)
 finally:setattr(module,attribute,original)
 print('Caught integration fault: '+name)
# Journal class reference lives directly in the test module.
for name,old,new,method in [
 ('accept-changed-checkpoint',"if continuity.digest([tx['source'],tx['provider'],packet,tx['objective']])!=tx['hash']:",'if False:','test_changed_checkpoint_rejected'),
 ('accept-wrong-recovery','if receipt!=expected or','if False or','test_wrong_receipt_never_reports_recovery'),
 ('forget-launch-intent',"self.event(tid,'target_launching')","self.event(tid,'target_launch_authorized')",'test_failed_batch_source_survives_and_other_project_proceeds'),
 ('ignore-project-overlap','return a==b or a in b.parents or b in a.parents','return False','test_project_overlap_excludes_other_writer'),
]:
 source=Path(managed_switch.__file__).read_text();assert source.count(old)==1,name
 module=types.ModuleType('switch_mutation');module.__file__=managed_switch.__file__;exec(compile(source.replace(old,new),module.__file__,'exec'),module.__dict__)
 original=s.Manager;s.Manager=module.Manager
 try:
  result=unittest.TestResult();s.Switching(method).run(result)
  assert result.failures and not result.errors,(name,result.failures,result.errors)
 finally:s.Manager=original
 print('Caught integration fault: '+name)
print('15 integration faults caught; production sources unchanged')
# Reversible migration rehearsal must reject changed approval, active sessions,
# and user files added after migration. Each planted mutation runs only on fixtures.
for name,old,new,method in [
 ('ignore-migration-plan','if plan[\'plan_hash\']!=approved_plan_hash:','if False:','test_source_change_after_preview_refused'),
 ('copy-active-session',"if any(row[1]!='exited' or row[2] is not None or row[3] is not None for row in sessions):",'if False:','test_active_or_owned_process_session_refused'),
 ('rollback-user-added-file','if actual!=expected:','if False:','test_rollback_refuses_new_destination_files'),
]:
 source=Path(m.migration.__file__).read_text();assert source.count(old)==1,name
 mutated=types.ModuleType('migration_mutation');mutated.__file__=m.migration.__file__;exec(compile(source.replace(old,new,1),mutated.__file__,'exec'),mutated.__dict__)
 original=m.migration;m.migration=mutated
 try:
  result=unittest.TestResult();m.MigrationRehearsal(method).run(result)
  assert result.failures and not result.errors,(name,result.failures,result.errors)
 finally:m.migration=original
 print('Caught migration rehearsal fault: '+name)
print('3 migration rehearsal faults caught; production state untouched')
