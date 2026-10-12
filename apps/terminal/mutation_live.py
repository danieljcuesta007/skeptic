"""Planted faults for live readiness: each must be caught by test_live_sessions."""
import importlib.util, sys, types, unittest
from pathlib import Path

here = Path(__file__).parent
source = (here / 'live_sessions.py').read_text()
faults = [
    ('busy-read-as-idle', "if status == 'busy' or meta.get('busy') is True: return 'working'", "if False: return 'working'", 'test_status_busy_means_wait'),
    ('home-is-a-project', "if str(parent) == home or str(parent) == '/': return None", "if str(parent) == '/': return None", 'test_home_without_repository_needs_project'),
    ('ready-while-peer-works', "if busy_peers: blockers.append(", "if False: blockers.append(", 'test_busy_peer_in_same_repository_blocks'),
    ('loose-pid-match', "abs(expected - actual) <= 2.5", "abs(expected - actual) <= 1e9", 'test_start_time_within_tolerance_but_pid_reuse_refused'),
    ('automation-ignored', "elif row.get('automation_pending') or row.get('queued_turns'):", "elif False:", 'test_idle_with_automatic_or_queued_work_waits'),
    ('frozen-never-switchable', "if row['activity'] == 'working' and not frozen:", "if row['activity'] == 'working':", 'test_frozen_busy_session_is_switchable_with_warning'),
    ('ignore-touched-files', "            if root: work = root; break", "            if root: break", 'test_home_session_project_from_touched_files'),
    ('ignore-tab-title', "row['label'] = row.get('tab_title') or", "row['label'] = '' or", 'test_session_named_by_its_terminal_tab'),
    ('wrong-destination', "DESTINATION = {'claude': 'codex',", "DESTINATION = {'claude': 'claude',", 'test_idle_session_in_a_repository_is_ready_with_command'),
]
spec = importlib.util.spec_from_file_location('test_live_sessions', here / 'test_live_sessions.py')
tests = importlib.util.module_from_spec(spec); spec.loader.exec_module(tests)
caught = 0
for name, old, new, method in faults:
    if source.count(old) != 1: raise RuntimeError('Mutation target drift: ' + name)
    module = types.ModuleType('live_sessions'); module.__file__ = str(here / 'live_sessions.py')
    exec(compile(source.replace(old, new), module.__file__, 'exec'), module.__dict__)
    original = tests.live; tests.live = module
    try:
        result = unittest.TestResult()
        unittest.defaultTestLoader.loadTestsFromName('VerdictTests.' + method, tests).run(result)
        if result.wasSuccessful(): raise RuntimeError('Planted fault survived: ' + name)
        caught += 1; print('Caught planted fault: ' + name)
    finally: tests.live = original
assert (here / 'live_sessions.py').read_text() == source
print(f'{caught}/{len(faults)} live readiness faults caught; production source unchanged.')
