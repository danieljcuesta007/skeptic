import contextlib,io,types,unittest
from pathlib import Path
import test_recovery as tests
import sessions,switcher
faults=[('lookup','h','all_projects = all_projects or bool(session_id)','all_projects = all_projects','test_id_independent_of_project'),('conversation','s','conversation_only = bool(session and session.get("conversation_only"))','conversation_only = False','test_conversation_no_git_no_vault'),('fallback','s','except (host.Denied, OSError):\n        if session is None: raise','except FileNotFoundError:\n        if session is None: raise','test_linked_pointer_fallback'),('multiple','s','if session and not conversation_only:','if False:','test_explicit_additional_repository')]
for name,target,before,after,method in faults:
 original=getattr(tests,target);source=Path(original.__file__).read_text();assert source.count(before)==1
 mutated=types.ModuleType('recovery_fault');mutated.__file__=original.__file__;exec(compile(source.replace(before,after),original.__file__,'exec'),mutated.__dict__)
 setattr(tests,target,mutated)
 # Shared fixture uses original adapters; patch the actual method for lookup fault.
 old=None
 if target=='h':old=tests.fixture.h.ClaudeAdapter.discover;tests.fixture.h.ClaudeAdapter.discover=mutated.ClaudeAdapter.discover
 try:
  result=unittest.TestResult()
  with contextlib.redirect_stdout(io.StringIO()):unittest.TestSuite([tests.RecoveryTests(method)]).run(result)
  assert not result.wasSuccessful(),name
 finally:
  if old is not None:tests.fixture.h.ClaudeAdapter.discover=old
  setattr(tests,target,original)
print('4 planted recovery faults caught; production unchanged')
