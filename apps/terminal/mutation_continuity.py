"""Deliberate catch-up/review faults in memory, synthetic sources/fake CLIs only."""
import contextlib
import io
from pathlib import Path
import sys
import types
import unittest

import continuity
import switcher
import test_continuity as tests
import test_sessions as session_tests

faults = [
 ('returning-claude-stale', 'index', "result['stale'] = bool(result['changed_sources'] or result['no_longer_accessible_sources'] or result['changed_dirty_file_metadata'] or result['git_changed'])", "result['stale'] = False", 'test_claude_codex_claude_receives_newer_state'),
 ('returning-codex-stale', 'index', "result['stale'] = bool(result['changed_sources'] or result['no_longer_accessible_sources'] or result['changed_dirty_file_metadata'] or result['git_changed'])", "result['stale'] = False", 'test_codex_claude_codex'),
 ('local-model-identity', 'index', "'model': provider.split(':', 1)[1] if ':' in provider else None", "'model': None", 'test_local_model_participation'),
 ('hide-missing-transcripts', 'index', "if observation['session'] is None:", 'if False:', 'test_first_use_and_missing_transcripts_disclosed'),
 ('ignore-dirty-metadata', 'index', "'git': git_record, 'files': files", "'git': git_record, 'files': []", 'test_dirty_file_changes_when_porcelain_same'),
 ('hide-checkpoint-conflict', 'index', "result['checkpoint_changed'] = old.get('checkpoint') != observation['checkpoint'] or before.get(observation['checkpoint']) != now.get(observation['checkpoint'])", "result['checkpoint_changed'] = False", 'test_conflicting_checkpoint_and_session_claims_preserved'),
 ('old-source-overwrites-baseline', 'index', 'if seed and old: return None', 'if False: return None', 'test_seed_does_not_advance_old_source_baseline'),
 ('restore-old-handoff', 'index', '    return record, current_claims', "    if checkpoint: docs[checkpoint]['text'] = docs[checkpoint]['text'].replace('LATEST_CANONICAL_ACTION', 'FIXTURE_NEXT')\n    return record, current_claims", 'test_never_restores_stale_handoff'),
 ('store-note-body', 'index', "'gaps': ['Index retains bounded fingerprints only; exact semantic diff/history is unavailable.'", "'gaps': ['FIXTURE_NEXT'", 'test_index_never_stores_bodies_or_prompts'),
 ('permit-protected-reference', 'index', "    if not isinstance(path, str) or len(path) > 1024 or any(history.sanitize(part) != part for part in Path(path).parts): return None", "    if not isinstance(path, str): return None\n    return path", 'test_protected_exclusions'),
 ('omit-outgoing-secret-filter', 'engine', "safe = continuity.history.sanitize(doc['text'])", "safe = doc['text']", 'test_claim_secret_filtering'),
 ('unbounded-index', 'index', 'while len(json.dumps(data).encode()) > LIMIT and len(data[\'events\']) > 1:', 'while False:', 'test_context_and_index_bounded'),
 ('disable-concurrent-writer-lock', 'index', 'fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)', 'pass', 'test_index_lock_contention_does_not_block'),
 ('rewrite-corrupt-index', 'index', "data = self.state.read('transitions.json', {'version': 1, 'events': []})", "data = {'version': 1, 'events': []}", 'test_corrupt_index_degrades_without_rewrite'),
 ('ignore-symlink-index', 'index', "data = self.state.read('transitions.json', {'version': 1, 'events': []})", "data = {'version': 1, 'events': []}", 'test_index_symlink_refused'),
 ('failed-launch-is-participation', 'index', "previous = next((e for e in reversed(relevant) if e['provider'] == provider and e.get('phase') not in ('launch_started', 'launch_failed')), None)", "previous = next((e for e in reversed(relevant) if e['provider'] == provider), None)", 'test_launch_failure_not_participation_success'),
 ('process-exit-is-success', 'index', "'verification': 'Filesystem/source snapshot observed; continuation success unknown'", "'verification': 'Continuation succeeded'", 'test_nonzero_provider_exit_unverified'),
 ('ignore-source-revocation', 'engine', "if old and old.get('kind') == kind and host.identity_matches(old.get('identity'), info):", 'if True:', 'test_permission_revocation_refuses_source_reads'),
 ('no-cli-catchup', 'engine', "if target: summary['catchup'] = continuity.Index(state).briefing(state.observation, state.current_claims, target)", 'if False: pass', 'test_cli_checkpoint_and_catchup_without_provider'),
 ('ignore-root-replacement', 'index', 'key = digest([repo, identity, knowledge])', 'key = digest([repo, knowledge])', 'test_changed_root_identity_is_a_new_project'),
 ('unbounded-catchup', 'index', '    if len(json.dumps(result).encode()) <= 6000: return result', '    return result', 'test_catchup_briefing_byte_limit'),
 ('older-accessible-handoff', 'index', "max(named_handoffs, key=lambda p: docs[p]['modified_at'])", "min(named_handoffs, key=lambda p: docs[p]['modified_at'])", 'test_latest_accessible_handoff_reference'),
 ('lose-continuity-gaps', 'index', "'continuity_gaps': [history.sanitize(g)[:300] for g in summary['gaps'][:6]]", "'continuity_gaps': []", 'test_continuity_gaps_preserved'),
 ('hide-untracked-file-changes', 'engine', "'--untracked-files=all'", "'--untracked-files=normal'", 'test_untracked_directory_file_changes_detected'),
 ('send-explicit-task-secret', 'engine', 'task = filtered_task', 'task = task', 'test_explicit_task_secret_omitted'),
 ('send-without-review', 'session', "if answer != 'send':", 'if False:', 'test_session_sending_requires_review'),
    ('hide-complete-recovery-packet', 'session', "    print('COMPLETE FILTERED RECOVERY PACKET\\n' + packet, flush=True)", '    pass', 'test_declined_send_displays_packet_without_launch_or_persistence'),
 ('send-changed-context', 'session', 'if refreshed != packet:', 'if False:', 'test_context_changed_during_review_requires_new_review'),
]
sources = {'index': Path(continuity.__file__).read_text(), 'engine': Path(switcher.__file__).read_text(), 'session': Path(switcher.__file__).read_text()}
caught = 0
for name, target, old, new, method in faults:
    source = sources[target]
    if source.count(old) != 1: raise RuntimeError('Mutation target drift: ' + name)
    module = types.ModuleType('continuity_fault'); module.__file__ = continuity.__file__ if target == 'index' else switcher.__file__
    exec(compile(source.replace(old, new), module.__file__, 'exec'), module.__dict__)
    original_c, original_s, original_session_s, fixture_s = tests.c, tests.s, session_tests.s, tests.fixtures.s
    if target == 'index': tests.c = module; sys.modules['continuity'] = module
    elif target == 'engine': tests.s = module; tests.fixtures.s = module
    else: session_tests.s = module
    try:
        result = unittest.TestResult()
        test = session_tests.SessionTests(method) if target == 'session' else tests.ContinuityTests(method)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()): unittest.TestSuite([test]).run(result)
        if result.wasSuccessful(): raise AssertionError('Survived catch-up fault: ' + name)
        caught += 1; print('Caught catch-up fault: ' + name)
    finally:
        tests.c, tests.s, session_tests.s = original_c, original_s, original_session_s
        sys.modules['continuity'] = continuity
        tests.fixtures.s = fixture_s
print(f'{caught}/{len(faults)} catch-up/review faults caught; production sources unchanged.')
