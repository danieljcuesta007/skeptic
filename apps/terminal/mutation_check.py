"""Plant faults in memory only; real providers and source edits are forbidden."""
import contextlib
import io
from pathlib import Path
import types
import unittest
import test_switcher as tests
import switcher

source = Path(switcher.__file__).read_text()
faults = [
 ('wrong-project', "cwd = Path(os.path.abspath(cwd))", "cwd = Path.home()", 'test_current_directory_repository'),
 ('invented-match', "if repo in references(doc['text'])", "if True", 'test_no_invented_match'),
 ('skip-vault-context', "if matches:\n                folder", "if False:\n                folder", 'test_exact_repository_match'),
 ('ignore-mapping', "if mapped in eligible: matches = [mapped]", "if False: matches = [mapped]", 'test_ambiguous_mapping_picker'),
 ('missing-grant-bypass', "if old and old.get('kind') == kind and host.identity_matches(old.get('identity'), info):", "if True:", 'test_approval_missing_noninteractive'),
 ('repeat-approval', "if old and old.get('kind') == kind and host.identity_matches(old.get('identity'), info):", "if False:", 'test_approval_once_and_reuse'),
 ('reboot-revokes-approval', "if old['identity'] != signature:  # pre-durable grant", "if old['identity'] != signature and False:  # pre-durable grant", 'test_reboot_renumbered_device_keeps_approval'),
 ('ignore-decline', "if ask('Type approve: ').strip() != 'approve':", "if False:", 'test_declined_approval'),
 ('forget-revoke', "state.settings['grants'].pop(path, None)", "pass", 'test_revocation'),
 ('no-repo-instructions', "docs = {str(Path(repo) / p): d for p, d in snapshot['documents'].items()}", "docs = {}", 'test_instruction_and_user_task'),
 ('no-subfolder-instructions', "instructions.extend(str(parent / name) for name in RULES)", "pass", 'test_subdirectory_instructions'),
 ('no-linked-context', "if linked:", "if False:", 'test_exact_link_in_scope'),
 ('hide-continuity-gap', "'Unsaved conversation/current request and hidden reasoning were not recovered. No transcript scraping.'", "'Unknown.'", 'test_unsaved_gap'),
 ('wrong-launch-directory', "return run(argv, cwd=cwd, check=False).returncode", "return run(argv, cwd='/', check=False).returncode", 'test_safe_launch_both_directions_and_failure'),
 ('shell-launch', "return run(argv, cwd=cwd, check=False).returncode", "return run(argv, cwd=cwd, shell=True, check=False).returncode", 'test_safe_launch_both_directions_and_failure'),
 ('drop-context', "argv += ['--', packet]", "argv += ['--', '']", 'test_safe_launch_both_directions_and_failure'),
 ('local-wrong-adapter', "argv += ['--oss', '--local-provider', provider['provider'], '--model', provider['model']]", "argv += ['--oss']", 'test_local_launch_adapter'),
 ('analytics-default-on', "if not self.settings['analytics']: return", "if False: return", 'test_optional_analytics'),
 ('execute-git-filters', "if re.search(r'(?im)^\\s*\\[\\s*(?:filter|include|includeIf)\\b', config):", "if False:", 'test_git_filters_cannot_execute'),
 ('global-git-config', "GIT_CONFIG_GLOBAL=os.devnull", "GIT_CONFIG_GLOBAL='/unsafe'", 'test_git_global_config_isolation'),
 ('empty-model-list', "return result\n\n\nclass NoRedirect", "return []\n\n\nclass NoRedirect", 'test_cloud_detection_missing_and_available'),
]
caught = 0
for name, old, new, method in faults:
    if source.count(old) != 1: raise RuntimeError('Mutation target drift: ' + name)
    module = types.ModuleType('switcher_mutation'); module.__file__ = switcher.__file__
    exec(compile(source.replace(old, new), switcher.__file__, 'exec'), module.__dict__)
    original = tests.s; tests.s = module
    try:
        result = unittest.TestResult()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            unittest.TestSuite([tests.SwitchTests(method)]).run(result)
        if result.wasSuccessful(): raise AssertionError('Survived planted fault: ' + name)
        caught += 1; print('Caught planted fault: ' + name)
    finally: tests.s = original
print(f'{caught}/{len(faults)} terminal faults caught; production source unchanged.')
