"""Workspace faults are planted only in memory, on temporary synthetic fixtures."""
from pathlib import Path
import types
import unittest
from unittest.mock import patch
import app
import workspace
import test_app
import test_workspace

FAULTS = [
 ('connect-approval','workspace',"if data['approval'] is not True: raise self.h.Denied('Explicit workspace read approval required')",'if False: pass','test_explicit_approval_and_schema'),
 ('policy-body-boundary','workspace',"if record['policy'] != 'FULL_BRAIN':",'if False:','test_policy_scopes'),
 ('full-brain-search','workspace','allowed = paths','allowed = []','test_full_brain_boundaries'),
 ('vault-boundary','app','if vault:', 'if False:','test_vault_approval_only'),
 ('quarantine-audit','app',"sorted(p for p in set(engine.body_reads) if p in documents)",'sorted(set(engine.body_reads))','test_protected_exclusions_and_quarantine'),
 ('root-link','app','child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)', 'child = os.open(part, os.O_RDONLY | os.O_DIRECTORY, dir_fd=fd)','test_links_traversal_aliases'),
 ('candidate-dedup','workspace','p != q and Path(q) in Path(p).parents','False','test_projects_and_duplicate_prevention'),
 ('missing-checkpoint','workspace',"'readiness': 'NEEDS REVIEW' if checkpoint else 'MISSING CHECKPOINT'","'readiness': 'READY TO RESUME'",'test_missing_checkpoint'),
 ('parent-instructions','workspace','(Path(p).name in RULES and Path(p).parent in (folder, *folder.parents))','False','test_instruction_parent_and_linked_sources'),
 ('handoff-priority','workspace',"s['path'] != project['checkpoint']","s['path'] == project['checkpoint']",'test_attribution_and_canonical_handoff'),
 ('project-section-budget','workspace',"{p: full['documents'][p] for p in wanted}",'{}','test_summary_beyond_global_excerpt_limit'),
 ('exact-association','workspace','if len(exact) == 1:','if False:','test_exact_repository_association_and_git'),
 ('auto-name-merge','workspace','elif confirmed:','elif confirmed or project["name"] == "Atlas":','test_ambiguous_repository_matching_requires_confirmation'),
 ('multiple-matches','workspace','if len(exact) == 1:','if len(exact) >= 1:','test_multiple_exact_matches_not_merged'),
 ('unapproved-scan','workspace',"active = [r for r in roots if r['approved']]",'active = roots','test_restart_no_grants_or_content_storage'),
 ('git-process','workspace','head = read(\'HEAD\') or \'\'','__import__("subprocess").run(["git", "status"])\n        head = read(\'HEAD\') or \'\'','test_git_no_commands_config_hooks_or_pointer_escape'),
 ('packed-ref','workspace',"commit = matches[0] if len(matches) == 1 else None",'commit = None','test_git_detached_packed_and_malformed_head'),
 ('prompt-identity','workspace',"f\"Project: {project['name']}\\nKnowledge folder: {project['path']}\\nAccess policy: {project['policy']}\"",'"Missing identity"','test_prompt_grounding_and_provider_selection'),
 ('revocation','workspace',"self.registry.remove(data['id']); self.confirmed.clear(); self.hidden.clear()",'self.confirmed.clear(); self.hidden.clear()','test_freshness_and_revocation'),
 ('project-removal','workspace',"self.detail(data['id']); self.hidden.add(data['id']); self.confirmed.pop(data['id'], None)","self.detail(data['id']); self.confirmed.pop(data['id'], None)",'test_project_removal_and_root_replacement'),
 ('repository-bounds','workspace','count > self.h.MAX_ENTRIES or depth > 8 or len(repos) >= 50','False','test_operation_bounds'),
 ('linked-parent','workspace','candidate = posixpath.normpath(candidate)','candidate = candidate','test_linked_parent_source_inside_root'),
 ('source-evidence','workspace',"if exact[0]['path'] in references(d['text'])",'if False','test_existing_markdown_repository_labels'),
 ('legacy-policy-bypass','app',"if 'kind' in record:", 'if False:','HTTP.test_workspace_http_workflow_and_no_raw_endpoint'),
 ('workspace-origin','app',"self.headers.get_all('Origin') != [self.server.origin]",'False','HTTP.test_workspace_cross_origin_csrf_traversal'),
 ('preapproval-check','workspace',"if key not in self.registry.active:",'if False:','test_restart_no_grants_or_content_storage'),
 ('cross-root-source','workspace','if exact in approved_lookup: external[exact] = approved_lookup[exact]','if False: pass','test_linked_sources_need_separate_root_approval'),
]


def main():
    for name, module, old, new, test in FAULTS:
        original = app if module == 'app' else workspace
        source=Path(original.__file__).read_text()
        if source.count(old)!=1: raise AssertionError('Mutation anchor: '+name)
        mutant=types.ModuleType('workspace_mutant');mutant.__file__=original.__file__
        exec(compile(source.replace(old,new),original.__file__,'exec'),mutant.__dict__)
        cls='WorkspaceHTTPTests' if test.startswith('HTTP.') else 'WorkspaceTests'
        method=test.removeprefix('HTTP.')
        result=unittest.TestResult()
        with patch.object(test_workspace,module,mutant), patch.object(test_app,'app',mutant if module=='app' else app):
            unittest.defaultTestLoader.loadTestsFromName(cls+'.'+method,test_workspace).run(result)
        if result.wasSuccessful(): raise AssertionError('Fault survived: '+name)
        print('Caught workspace fault:',name)
    print(f'{len(FAULTS)} workspace mutations caught.')


if __name__=='__main__': main()
