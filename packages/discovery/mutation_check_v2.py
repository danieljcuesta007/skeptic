"""Run one targeted in-memory fault per V2 regression test."""
from pathlib import Path
import types
import unittest
from unittest.mock import patch
import test_engine
source=Path('engine.py').read_text()
cases={
'governing_revalidated_outside_passage_budget':("required = self.rules + ([p['status']] if p else [])", "required = self.rules[:1]"),
'conflicting_preferences_only_from_designated_rules':("if len(values)>1", "if False"),
'catalog_cannot_expand_authority':("set(catalog) != {'sources'}", "False"),
'cache_cannot_expand_scope':("if not self.scoped(path,p): continue", "if False: continue"),
'cache_destination_rejects_git_repository':("if any((parent/'.git').exists()", "if False and any((parent/'.git').exists()"),
'neutral_package_current_handoff_and_hashes':("'current_handoff':governing['handoff']", "'current_handoff':None"),
'quarantined_filename_not_exposed':("and k not in quarantined", ""),
'full_brain_and_new_note_discovery':("if self.mode == 'FULL_BRAIN': return True","if self.mode == 'FULL_BRAIN': return path.startswith('atlas/')"),
'scope_before_reads':("if not self.scoped(path, p): continue","if False: continue"),
'ask_to_expand_does_not_expand':("if self.mode == 'ASK_TO_EXPAND': return False","if self.mode == 'ASK_TO_EXPAND': return True"),
'excluded_bodies_never_opened':("self.exclusions = BUILTIN_EXCLUSIONS + config.get('excluded', [])","self.exclusions = []"),
'symlink_file_directory_and_hardlink_rejected':(" or info.st_nlink != 1",""),
'cache_unchanged_and_changed_rule':("if path in old and old[path]['signature'] == signature:","if path in old:"),
'deletion_and_rename':("'rename_candidates':renames","'rename_candidates':[]"),
 'task_changes_and_bounded_context':("text=live_text[path][start:start+min(600,max_chars-used)]","text=live_text[path]"),
'stale_selected_source_is_not_returned':("checked[path]=hashlib.sha256(data).hexdigest()==index['documents'][path]['sha256']","checked[path]=True"),
'policy_change_revokes_cached_text':("if index['policy_hash']!=policy_hash or index['project']!=project or index['root_identity']!=self.root_identity:","if False:"),
'untrusted_notes_remain_data':("else 'data'","else 'rule'"),
'ambiguous_project_and_unsafe_paths':("if len(hits) != 1:","if not hits:"),
'credential_heuristic_quarantines_no_content':("if re.search(r'-----BEGIN", "if False and re.search(r'-----BEGIN"),
'private_index_and_no_note_writes_or_external_actions':("os.fchmod(fd,0o600)","os.fchmod(fd,0o644)"),
'full_brain_without_project':("'handoff':p['status']+'#handoff' if p else None","'handoff':p['status']+'#handoff' if p else 'wrong'"),
'missing_rule_blocks_next_action':("'missing_required':missing","'missing_required':[]"),
 'tampered_cached_passage_never_returned':("text=live_text[path][start:start+min(600,max_chars-used)]","text=chunk['text'][:max_chars-used]")}
for name,(old,new) in cases.items():
 assert old in source,name
 modified=source.replace(old,new)
 if name=='scope_before_reads': modified=modified.replace("if self.mode != 'FULL_BRAIN':",'if False:')
 m=types.ModuleType('mutant');exec(compile(modified,'<fault>','exec'),m.__dict__)
 with patch.object(test_engine,'Engine',m.Engine),patch.object(test_engine,'Denied',m.Denied),patch.object(test_engine,'save_index',m.save_index):
  result=unittest.TestResult();test_engine.EngineTests('test_'+name).run(result)
 assert result.errors or result.failures,'Fault survived: '+name
 print('Caught:',name)
print(str(len(cases))+'/'+str(len(cases))+' targeted planted faults caught. No production source modified.')
