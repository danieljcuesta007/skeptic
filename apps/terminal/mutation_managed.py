"""Meaningful injected faults in temporary engine copies; fake processes only."""
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
import test_managed as tests

source = Path(tests.e.__file__).read_text()
faults = [
 ('two-writers', "if writer is not None and writer is not connection:", 'if False:', 'test_simultaneous_writer_claims_exactly_one_winner'),
 ('observer-input', "if writer is not connection: raise Denied('Writer lease required')", 'if False: pass', 'test_single_writer_observation_disconnect_and_transfer'),
 ('lost-disconnect-lease', 'if connection is writer: writer = None; update_status()', 'if False: writer = None; update_status()', 'test_single_writer_observation_disconnect_and_transfer'),
 ('wrong-exit-code', 'code = os.waitstatus_to_exitcode(status)', 'code = 0', 'test_exit_status_no_silent_relaunch'),
 ('hide-output-gap', "'gap': cursor < start", "'gap': False", 'test_output_overflow_disclosed'),
 ('invent-stale-liveness', "row['status'] = 'stale' if", "row['status'] = 'live' if", 'test_stale_registry_never_adopts_pid'),
 ('wrong-project-cwd', 'os.fchdir(cwd_fd)', 'os.chdir(root)', 'test_detach_reconnect_identity_output_and_cwd'),
 ('persist-private-output', 'if len(body) > 4096:', "registry.db.execute('UPDATE sessions SET project=? WHERE id=?', (body.decode(), sid)); registry.db.commit()\n                if len(body) > 4096:", 'test_registry_never_stores_terminal_bodies'),
]
for name, old, new, method in faults:
 assert source.count(old) == 1, name
 with tempfile.TemporaryDirectory(prefix='sk-mut-') as tmp:
  root = Path(tmp).resolve()
  (root/'managed_engine.py').write_text(source.replace(old,new))
  (root/'managed_fake.py').write_text(Path(tests.e.__file__).with_name('managed_fake.py').read_text())
  old_cli = tests.cli.__file__
  tests.cli.__file__ = str(root/'managed_cli.py')
  try:
   # Client-side stale observation lives in the imported module; fault it in memory.
   if name == 'invent-stale-liveness':
    import types
    mutated=types.ModuleType('managed_mutation');mutated.__file__=tests.e.__file__
    exec(compile(source.replace(old,new),mutated.__file__,'exec'),mutated.__dict__)
    original=tests.e;tests.e=mutated
   result=unittest.TestResult()
   with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
    unittest.TestSuite([tests.ManagedTests(method)]).run(result)
   assert result.failures and not result.errors, 'Expected behavioral assertion failure, not infrastructure error: '+name
  finally:
   tests.cli.__file__=old_cli
   if name == 'invent-stale-liveness':tests.e=original
 print('Caught managed fault: '+name)
print(str(len(faults))+' managed faults caught; production files unchanged')
