"""Each Step 42 regression must reject a targeted in-memory fault."""
from pathlib import Path
import types
import unittest
from unittest.mock import patch
import test_security
source=Path('engine.py').read_text()
cases={
 'case_alias_exclusion_before_body_read': [('return unicodedata.normalize(\'NFKC\', text).casefold()','return text'),("if part not in os.listdir(fd):","if False:"),("if bits[-1] not in os.listdir(fd):","if False:")],
 'case_alias_catalog_and_builtin_exclusions': [("return unicodedata.normalize('NFKC', text).casefold()","return text")],
 'noncanonical_alias_cannot_promote_rule': [("if part not in os.listdir(fd):","if False:"),("if bits[-1] not in os.listdir(fd):","if False:")],
 'stale_handoff_is_withheld': [("if digest != record['sha256']:\n                    continue", "if False:\n                    continue")],
 'credential_handoff_is_withheld_even_with_forged_digest': [('if credential_like(text):','if False and credential_like(text):'),('if credential_like(live_text[path]):','if False and credential_like(live_text[path]):'),("if digest != record['sha256']:\n                    continue", "if False:\n                    continue")],
 'forged_cache_cannot_bypass_passage_quarantine': [('if credential_like(live_text[path]):','if False and credential_like(live_text[path]):')],
 'malformed_cache_fails_closed_before_reads': [('type(line) is not int or not 1<=line<=10000','False')],
 'malformed_cache_envelope_and_bounds': [(" or len(text)>600",'')],
 'revoked_cache_metadata_is_ignored_without_reads': [('if not self.scoped(path, p): continue','if False: continue')],
 'cache_loader_rejects_malformed_duplicate_and_symlink': [("if key in result:","if False:")],
 'policy_revocation_and_symlink_cannot_leak': [("if index['policy_hash']!=policy_hash or index['project']!=project or index['root_identity']!=self.root_identity:","if False:")],
 'security_failures_do_not_invoke_external_fallback': [('index = self.validate_cache(index, project)','index = index')],
}
for name,changes in cases.items():
    modified=source
    for before,after in changes:
        assert before in modified,name
        modified=modified.replace(before,after)
    module=types.ModuleType('security_mutant');exec(compile(modified,'<security-fault>','exec'),module.__dict__)
    with patch.object(test_security,'Engine',module.Engine),patch.object(test_security,'Denied',module.Denied),patch.object(test_security,'load_index',module.load_index):
        result=unittest.TestResult();test_security.SecurityTests('test_'+name).run(result)
    assert result.failures or result.errors,'Fault survived: '+name
    print('Caught security fault:',name)
print(str(len(cases))+'/'+str(len(cases))+' security faults caught; application files unchanged.')
