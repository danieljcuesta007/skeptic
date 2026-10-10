"""Session faults planted in memory only. Fixtures and fake providers exclusively."""
import contextlib
import io
from pathlib import Path
import types
import unittest
import test_sessions as tests
import sessions
import switcher

faults = [
 ('no-metadata-approval', 'history', "if not sys.stdin.isatty(): raise host.Denied('Session approval required in a second Terminal; original Claude can stay open')", "if not sys.stdin.isatty(): self.data['grants'][key] = identity; atomic_json(self.state, 'sessions.json', self.data); return", 'test_no_metadata_reads_without_approval'),
 ('no-transcript-approval', 'history', "if not sys.stdin.isatty(): raise host.Denied('Session approval required in a second Terminal; original Claude can stay open')", "if not sys.stdin.isatty(): self.data['grants'][key] = identity; atomic_json(self.state, 'sessions.json', self.data); return", 'test_discovery_does_not_grant_transcript'),
 ('ignore-decline', 'history', "if self.ask('Type approve: ').strip() != 'approve':", 'if False:', 'test_declined_scope'),
 ('no-revoke', 'history', "self.data['grants'] = {}; atomic_json", "self.data['grants'] = self.data['grants']; atomic_json", 'test_permission_reuse_and_revoke'),
 ('title-filter', 'history', 'if title and title.casefold() not in label.casefold(): continue', 'if title: continue', 'test_title_timestamp_directory_selection'),
 ('wrong-origin-directory', 'history', "'cwd': cwd or (project if not all_projects else None)", "'cwd': '/'", 'test_title_timestamp_directory_selection'),
 ('no-user-text', 'history', "if kind == 'text':\n                text = excerpt(block.get('text'), 6000 if row['type'] == 'user' else 2000)", "if kind == 'text':\n                text = ''", 'test_visible_messages_tasks_tools_and_refs'),
 ('no-unfinished-tasks', 'history', "if name == 'TodoWrite' and isinstance(inputs.get('todos'), list):", 'if False:', 'test_visible_messages_tasks_tools_and_refs'),
 ('no-file-references', 'history', "if value: paths.add(value); references.append(value)", 'if False: paths.add(value); references.append(value)', 'test_visible_messages_tasks_tools_and_refs'),
 ('secret-leak', 'history', "    if not isinstance(text, str): return ''", "    if isinstance(text, str): return text\n    if not isinstance(text, str): return ''", 'test_secret_and_protected_filtering_every_surface'),
 ('combine-old-branch', 'history', '        chain.reverse()', '        chain = messages', 'test_active_branch_excludes_abandoned_work'),
 ('drop-compaction', 'history', "if row.get('isMeta') or row.get('type') not in ('user', 'assistant', 'system', 'progress'): continue", "if row.get('isMeta') or row.get('isCompactSummary') or row.get('type') not in ('user', 'assistant', 'system', 'progress'): continue", 'test_compaction_summary_supported'),
 ('hide-chain-gap', 'history', "'chain_gap': gap}", "'chain_gap': False}", 'test_cycle_or_parent_gap_disclosed'),
 ('lose-latest-user', 'history', "retained = [r for r in anchors if r and r not in retained] + retained", 'retained = retained', 'test_latest_user_survives_many_tool_events'),
 ('wrong-home-repository', 'switch', "home_session = session is not None and (Path(cwd) == Path.home() or conversation_only)", 'home_session = False', 'test_home_sessions_no_home_scan'),
 ('ignore-destination-confirmation', 'switch', '            else: cwd = candidates[choice]', '            else: cwd = candidates[0]', 'test_home_referenced_repository_confirmed'),
 ('drop-session-from-context', 'switch', "docs[session['source_key']] = session['document']", 'pass', 'test_obsidian_matching_and_context_attribution'),
 ('source-hash-not-checked', 'history', "if digest != snapshot['snapshot_sha256']:", 'if False:', 'test_changed_snapshot_blocks_launch'),
 ('identity-not-checked', 'history', "if current.get('grants', {}).get(key) != [info.st_dev, info.st_ino]:", 'if False:', 'test_permission_reuse_and_revoke'),
 ('unbounded-snapshot', 'history', 'chunks = read_chunks(fd, info, SNAPSHOT_LIMIT)', 'chunks = read_chunks(fd, info, info.st_size)', 'test_snapshot_byte_limit'),
 ('raw-tool-result', 'history', "'detail': 'Raw tool result withheld'", "'detail': block.get('content')", 'test_visible_messages_tasks_tools_and_refs'),
 ('wrong-codex-content', 'history', "if text: records.append({**origin, 'role': payload['role'], 'untrusted_text': text})", 'if False: records.append({})', 'test_reverse_codex_adapter'),
 ('skip-duplicate-picker', 'history', "return sessions[picker('SKEPTIC — SELECT CLAUDE SESSION', labels)]", 'return sessions[0]', 'test_duplicate_title_requires_selection'),
 ('codex-metadata-sibling-grant', 'history', "scope = str(path.parent); key = 'metadata-file:' + str(path)", "scope = str(path.parent); key = 'metadata:' + scope", 'test_codex_metadata_consent_is_file_specific'),
 ('ignore-exact-id', 'history', 'if session_id and name[:-6].lower() != session_id.lower(): continue', 'if False: continue', 'test_exact_id_and_all_projects'),
]
original_h, original_s = tests.h, tests.s
sources = {'history': Path(sessions.__file__).read_text(), 'switch': Path(switcher.__file__).read_text()}
caught = 0
for name, target, old, new, method in faults:
    source = sources[target]
    if source.count(old) != 1: raise RuntimeError('Mutation target drift: ' + name)
    module = types.ModuleType('session_mutation'); module.__file__ = sessions.__file__ if target == 'history' else switcher.__file__
    exec(compile(source.replace(old, new), module.__file__, 'exec'), module.__dict__)
    # No-op consent then original check/read must fail safely or be rejected by assertions.
    module.skip_consent = lambda *args, **kwargs: None
    tests.h, tests.s = (module, original_s) if target == 'history' else (original_h, module)
    try:
        result = unittest.TestResult()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            unittest.TestSuite([tests.SessionTests(method)]).run(result)
        if result.wasSuccessful(): raise AssertionError('Survived session fault: ' + name)
        caught += 1; print('Caught session fault: ' + name)
    finally: tests.h, tests.s = original_h, original_s
print(f'{caught}/{len(faults)} session faults caught; production sources unchanged.')
