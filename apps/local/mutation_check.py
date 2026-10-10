"""Plant targeted faults in memory. Never change source files or use real projects."""
import io
from pathlib import Path
import types
import unittest
from unittest.mock import patch
import app
import test_app

# The unchanged engine's alias/traversal/link regressions also run in the full suite.
FAULTS = [
 ('broad-root', "if protected(path) or any(root == p or root in p.parents for p in forbidden):", "if False:", 'DiscoveryTests.test_broad_roots_and_protected_root'),
 ('root-alias', "if part not in os.listdir(fd):", "if False:", 'DiscoveryTests.test_case_alias_root_and_source'),
 ('parent-link', 'child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)', 'child = os.open(part, os.O_RDONLY | os.O_DIRECTORY, dir_fd=fd)', 'DiscoveryTests.test_symlink_root_and_parent'),
 ('protected', 'if self.excluded(rel):', 'if False:', 'DiscoveryTests.test_protected_names_case_unicode_and_custom'),
 ('quarantine', 'if credential_like(text):', 'if False:', 'DiscoveryTests.test_credential_quarantine'),
 ('binary', "if '\\x00' in text:", 'if False:', 'DiscoveryTests.test_malformed_markdown'),
 ('attribution', "'line': i + 1,", "'line': i + 2,", 'DiscoveryTests.test_attribution_actual_lines_and_verbatim'),
 ('nested-handoff', 'len(boundary[1]) <= len(match[1])', 'True', 'DiscoveryTests.test_nested_checkpoint_sections_and_handoff_named_files'),
 ('missing-checkpoint', "if not status: missing.append('No exact STATUS.md checkpoint found. Progress is unknown.')", 'if False: pass', 'DiscoveryTests.test_missing_checkpoint_handoff_and_actions'),
 ('selection', "or any(p not in snapshot['documents'] for p in selected)", 'or False', 'DiscoveryTests.test_resume_generation_and_selection_scope'),
 ('provider', "if provider not in ('Claude Code', 'Codex') or", 'if False or', 'DiscoveryTests.test_resume_generation_and_selection_scope'),
 ('instructions', "for p in snapshot['instructions']]", 'for p in []]', 'DiscoveryTests.test_resume_generation_and_selection_scope'),
 ('root-identity', 'if Engine.sig(os.fstat(check))[:2] != Engine.sig(os.fstat(self.active[key]))[:2]:', 'if False:', 'DiscoveryTests.test_replaced_root_is_denied'),
 ('approval', 'if not isinstance(key, str) or key not in self.active:', 'if False:', 'DiscoveryTests.test_unapproved_roots'),
 ('file-budget', 'if files > MAX_FILES:', 'if False:', 'DiscoveryTests.test_limits_oversize_and_no_partial_overview'),
 ('source-body', "body = doc['text'][:min(3000, budget)]", "body = ''", 'DiscoveryTests.test_fresh_prompt_and_removed_source'),
 ('removal', 'if key in self.active: os.close(self.active.pop(key))', 'if False: pass', 'DiscoveryTests.test_multiple_projects_and_remove'),
 ('registry-write', 'output.write(payload)', "output.write(b'[]')", 'DiscoveryTests.test_restart_requires_fresh_approval_no_content_persisted'),
 ('registry-schema', 'if not isinstance(records, list) or len(records) > 50:', 'if False:', 'DiscoveryTests.test_registry_malformed_and_linked_file'),
 ('registry-link', 'os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parentfd)', 'os.O_DIRECTORY, dir_fd=parentfd)', 'DiscoveryTests.test_registry_symlink_refused'),
 ('host', "if self.headers.get_all('Host') != [expected]:", 'if False:', 'ServerTests.test_host_origin_csrf_and_fetch_site'),
 ('dns', "self.server_name = '127.0.0.1'", "self.server_name = __import__('socket').getfqdn('127.0.0.1')", 'ServerTests.test_no_dns_lookup_on_start'),
 ('token', "or self.headers.get_all('X-Skeptic-Token') != [self.server.token]", 'or False', 'ServerTests.test_host_origin_csrf_and_fetch_site'),
 ('approval-boolean', "if data['approval'] is not True: raise Denied('Explicit read approval required')", 'if False: pass', 'ServerTests.test_no_read_without_approval_or_extra_authority'),
 ('request-size', 'not 0 < int(lengths[0]) <= 16384', 'not 0 < int(lengths[0]) <= 100000', 'ServerTests.test_malformed_request_and_size_bounds'),
 ('html-sink', "self.send_header('Cache-Control', 'no-store')", "self.send_header('Cache-Control', 'public')", 'ServerTests.test_loopback_only_and_asset_allowlist'),
 ('http-prompt', "self.reply(200, {'prompt': prompt,", "self.reply(200, {'prompt': '',", 'ServerTests.test_complete_http_workflow'),
]


def main():
    source = Path(app.__file__).read_text()
    for name, old, new, test in FAULTS:
        if source.count(old) != 1: raise AssertionError('Mutation anchor: '+name)
        mutant=types.ModuleType('local_mutant')
        mutant.__file__=app.__file__
        exec(compile(source.replace(old,new), app.__file__, 'exec'), mutant.__dict__)
        result=unittest.TestResult()
        with patch.object(test_app,'app',mutant):
            unittest.defaultTestLoader.loadTestsFromName(test, test_app).run(result)
        if result.wasSuccessful(): raise AssertionError('Fault survived: '+name)
        print('Caught:',name)
    print(f'{len(FAULTS)} local host mutations caught.')


if __name__ == '__main__': main()
