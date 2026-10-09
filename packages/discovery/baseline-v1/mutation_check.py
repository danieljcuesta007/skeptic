"""Each regression test must catch one deliberately planted implementation fault."""
import contextlib
import io
from pathlib import Path
import types
import unittest
from unittest.mock import patch
import test_discovery

source = Path('discovery.py').read_text()
cases = {
 'authorized_discovery_and_receipt': ("'handoff_location': project['status'] + '#handoff'", "'handoff_location': 'wrong'"),
 'private_exclusion_before_open': ("for pat in self.excluded):", "for pat in []):"),
 'explicit_exclusion_rejected_before_any_open': ('reader.parts(key)\n    current', 'pass\n    current'),
 'unauthorized_selection_never_read': ('or not set(explicit) <= set(keys)', 'or False'),
 'unauthorized_alias_and_traversal': ("alias not in self.roots or any(b in ('', '.', '..') for b in bits)", "False"),
 'symlink_file_escape': ('os.O_NOFOLLOW', '0'),
 'symlink_directory_escape': ('os.O_NOFOLLOW', '0'),
 'changed_instructions': ("if previous and signature == previous.get('signature'):", 'if previous:'),
 'task_change_without_body_rereads': ("task.lower()", "'alpha'"),
 'explicit_selection_has_priority': ("0 if key in explicit", "4 if key in explicit"),
 'deleted_and_renamed_sources': ("renames = [{'from': a", "renames = [{'from': a"),
 'ambiguous_or_unknown_project_before_reads': ("if len(matches) != 1:", "if not matches:"),
 'stale_handoff_blocks_action': ("'stale_handoff': stale", "'stale_handoff': False"),
 'conflicting_preferences_not_promoted': ("'conflicts': conflicts", "'conflicts': []"),
 'no_external_actions_or_writes': ("matches = [p", "os.system('forbidden-test-action')\n    matches = [p"),
 'missing_status_rejected': ("if project['status'] not in current:", "if False:"),
 'revoked_source_not_leaked_from_cache': ("for key, value in previous.get('files', {}).items():", "old = dict(previous.get('files', {}))\n    for key, value in previous.get('files', {}).items():"),
 'root_change_invalidates_cache': ("previous = {}  # never reuse", "pass  # never reuse"),
}
for name, (old, new) in cases.items():
    modified = source.replace(old, new)
    if name == 'symlink_file_escape':
        modified = modified.replace('follow_symlinks=False', 'follow_symlinks=True')
    if name == 'deleted_and_renamed_sources':
        modified = modified.replace("'rename_candidates': renames", "'rename_candidates': []")
    assert modified != source, name
    module = types.ModuleType('mutant')
    exec(compile(modified, '<planted-fault>', 'exec'), module.__dict__)
    test = test_discovery.DiscoveryTests('test_' + name)
    with patch.object(test_discovery, 'discover', module.discover):
        result = unittest.TestResult()
        test.run(result)
    assert result.failures or result.errors, 'Fault survived: ' + name
    print('Caught planted fault:', name)
print(str(len(cases)) + '/' + str(len(cases)) + ' planted faults caught; production module unchanged')
