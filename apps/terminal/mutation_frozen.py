"""In-memory planted frozen-session faults, synthetic evidence only."""
from pathlib import Path
import unittest,types,contextlib,io
import test_frozen as tests
faults=[('quota-is-task','h',"provider_notice(text) or row.get('isApiErrorMessage')",'False','test_quota_not_task'),('lose-gap-recovery','h','if (gap or not substantive) and not historical_pass:','if False:','test_broken_chain_recovers_substantive_request'),('trust-unlinked-request','h',"historical.append({'role': 'historical-user-request (unverified; outside recovered chain)'","historical.append({'role': 'user'",'test_broken_chain_recovers_substantive_request'),('drop-explicit-model','s',"elif provider.get('model'): argv += ['--model', provider['model']]","elif provider.get('model'): pass",'test_explicit_native_model_safe_argv')]
faults += [
 ('break-attachment-bridge','h',"and not row.get('isSidechain') and not row.get('teamName')]", "and not row.get('isSidechain') and not row.get('teamName') and row.get('type') != 'attachment']", 'test_attachment_bridge_and_last_work'),
 ('generated-is-human','h',"return bool(isinstance(text, str) and re.match", "return bool(False and re.match",'test_absent_task_stays_absent'),
 ('lose-brief-tail','h'," + tail", " + ''", 'test_long_brief_keeps_tail'),
 ('claim-unfinished','h','Current unfinished task: NOT established','Current unfinished task: established','test_unfinished_status_not_inferred'),
 ('drop-last-work','h',"if latest_work: text +=", "if False: text +=", 'test_attachment_bridge_and_last_work')]

faults += [('compaction-false-gap','h','if historical and not compacted: gap = True','if historical: gap = True','test_compaction_is_not_missing_ancestry'), ('bury-summary','h','if checkpoint:\n        text +=','if False:\n        text +=','test_summary_tail_survives_packet_budget')]

for name,target,before,after,method in faults:
 original=getattr(tests,target);source=Path(original.__file__).read_text();assert source.count(before)==1,name
 mutated=types.ModuleType('frozen_mutation');mutated.__file__=original.__file__;exec(compile(source.replace(before,after),original.__file__,'exec'),mutated.__dict__)
 setattr(tests,target,mutated)
 try:
  result=unittest.TestResult()
  with contextlib.redirect_stdout(io.StringIO()):unittest.TestSuite([(tests.FrozenTests if hasattr(tests.FrozenTests, method) else tests.RealRecoveryRegressionTests if hasattr(tests.RealRecoveryRegressionTests, method) else tests.SeamlessContinuationTests)(method)]).run(result)
  assert not result.wasSuccessful(),name
 finally:setattr(tests,target,original)
print('11 planted frozen-session faults caught; production unchanged')
