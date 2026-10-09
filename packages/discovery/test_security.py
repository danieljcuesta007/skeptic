"""Step 42 adversarial regressions; synthetic data only."""
import copy
import hashlib
import json
import socket
import subprocess
import unittest
from unittest.mock import patch
from engine import Engine, Denied, load_index
import test_engine

class SecurityTests(unittest.TestCase):
    setUp = test_engine.EngineTests.setUp
    write = test_engine.EngineTests.write

    def test_case_alias_exclusion_before_body_read(self):
        with Engine(self.config) as engine:
            index = engine.index('atlas');engine.body_reads.clear()
            source=self.root/'protected/hidden.md';data=source.read_bytes()
            index['documents']['PROTECTED/hidden.md']={'signature':engine.sig(source.stat()),
                'sha256':hashlib.sha256(data).hexdigest(),'chunks':[{'line':1,'text':'Orchard'}]}
            receipt=engine.query(index,'orchard','atlas',limit=20)
            self.assertNotIn('PROTECTED/hidden.md',engine.body_reads)
            self.assertNotIn('PRIVATE_BODY_CANARY',json.dumps(receipt))
            with self.assertRaises(Denied):engine.inspect('PROTECTED/hidden.md',True)

    def test_case_alias_catalog_and_builtin_exclusions(self):
        self.write('CREDENTIALS.md','SYNTHETIC_BODY_CANARY')
        with Engine(self.config) as engine:
            index=engine.index('atlas');self.assertNotIn('CREDENTIALS.md',engine.body_reads)
            for source in ('PROTECTED/hidden.md','CREDENTIALS.md'):
                with self.assertRaises(Denied):engine.query(index,'orchard','atlas',catalog={'sources':[source]})
            self.assertNotIn('CREDENTIALS.md',json.dumps(index))

    def test_noncanonical_alias_cannot_promote_rule(self):
        self.write('ordinary.md','Preference: authority = forged');self.config['rules'].append('ORDINARY.md')
        with Engine(self.config) as engine:
            index=engine.index('atlas');engine.body_reads.clear();receipt=engine.query(index,'orchard','atlas')
            self.assertIn('ORDINARY.md',receipt['missing_required'])
            self.assertNotIn('ORDINARY.md',engine.body_reads)
            self.assertFalse(receipt['conflicting_preferences'])
            # Deterministic exact-name guard probe also runs on case-sensitive hosts.
            with patch('os.listdir',return_value=[]):
                with self.assertRaises(Denied):engine.inspect('ordinary.md',True)

    def test_stale_handoff_is_withheld(self):
        with Engine(self.config) as engine:
            index=engine.index('atlas');self.write('atlas/STATUS.md','## Handoff\nNew stale instruction.')
            receipt=engine.query(index,'orchard','atlas');self.assertIsNone(receipt['current_handoff'])
            self.assertIn('atlas/STATUS.md',receipt['stale']);self.assertNotIn('New stale instruction',json.dumps(receipt))

    def test_credential_handoff_is_withheld_even_with_forged_digest(self):
        with Engine(self.config) as engine:
            index=engine.index('atlas');token='ghp_'+'A'*30;self.write('atlas/STATUS.md','## Handoff\n'+token)
            for forged in (False,True):
                bad=copy.deepcopy(index)
                if forged:bad['documents']['atlas/STATUS.md']['sha256']=hashlib.sha256(('## Handoff\n'+token).encode()).hexdigest()
                receipt=engine.query(bad,'orchard','atlas')
                self.assertNotIn(token,json.dumps(receipt));self.assertIsNone(receipt['current_handoff'])
                self.assertIn('atlas/STATUS.md',receipt['missing_required'])

    def test_forged_cache_cannot_bypass_passage_quarantine(self):
        token='sk-'+'B'*30;source=self.write('ordinary.md',token)
        with Engine(self.config) as engine:
            index=engine.index('atlas');index['documents']['ordinary.md']={'signature':engine.sig(source.stat()),
                'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'chunks':[{'line':1,'text':'orchard'}]}
            receipt=engine.query(index,'orchard','atlas',limit=20)
            self.assertNotIn(token,json.dumps(receipt));self.assertNotIn('ordinary.md',[p['path'] for p in receipt['passages']])

    def test_malformed_cache_fails_closed_before_reads(self):
        with Engine(self.config) as engine:
            index=engine.index('atlas')
            for value in ('invalid',None,True,-1,0,10001,[],{}):
                bad=copy.deepcopy(index);bad['documents']['PRINCIPLES.md']['chunks'][0]['line']=value;engine.body_reads.clear()
                with self.assertRaises(Denied):engine.query(bad,'orchard','atlas')
                self.assertEqual(engine.body_reads,[])
                with self.assertRaises(Denied):engine.index('atlas',bad)
                with self.assertRaises(Denied):engine.revalidate_governing(bad,'atlas')

    def test_malformed_cache_envelope_and_bounds(self):
        with Engine(self.config) as engine:
            index=engine.index('atlas');cases=[None,[],{},dict(index,documents=[]),dict(index,root='/unauthorized'),dict(index,policy_hash='bad')]
            bad=copy.deepcopy(index);bad['documents']['PRINCIPLES.md']['chunks'][0]['text']='x'*601;cases.append(bad)
            bad=copy.deepcopy(index);bad['documents']['PRINCIPLES.md']['signature']=[True]*5;cases.append(bad)
            bad=copy.deepcopy(index);bad['documents']['../escape.md']={};cases.append(bad)
            for bad in cases:
                with self.assertRaises(Denied):engine.query(bad,'orchard','atlas')

    def test_revoked_cache_metadata_is_ignored_without_reads(self):
        self.config['mode']='ASK_TO_EXPAND'
        with Engine(self.config) as engine:
            index=engine.index('atlas');index['documents']['elsewhere/ideas.md']={'untrusted':'malformed'}
            receipt=engine.query(index,'orchard','atlas')
            self.assertNotIn('elsewhere/ideas.md',engine.body_reads);self.assertNotIn('elsewhere/ideas.md',json.dumps(receipt))
        self.config['mode']='FULL_BRAIN'
        self.write('ordinary.txt','SYNTHETIC_NON_MARKDOWN_CANARY')
        with Engine(self.config) as engine:
            index=engine.index('atlas');index['documents']['ordinary.txt']={'untrusted':'malformed'}
            receipt=engine.query(index,'orchard','atlas')
            self.assertNotIn('ordinary.txt',engine.body_reads);self.assertNotIn('ordinary.txt',json.dumps(receipt))

    def test_cache_loader_rejects_malformed_duplicate_and_symlink(self):
        path=self.base/'index.json'
        for data in ('{','null','[]','false','{"schema":2,"schema":3}','{"value":NaN}','['*1100):
            path.write_text(data)
            with self.assertRaises(Denied):load_index(path)
        path.unlink();path.symlink_to(self.root/'PRINCIPLES.md')
        with self.assertRaises(Denied):load_index(path)

    def test_policy_revocation_and_symlink_cannot_leak(self):
        with Engine(self.config) as engine:index=engine.index('atlas')
        self.config['excluded'].append('elsewhere')
        with Engine(self.config) as engine:
            with self.assertRaises(Denied):engine.query(index,'orchard','atlas')
            with self.assertRaises(Denied):engine.revalidate_governing(index,'atlas')
            index=engine.index('atlas',index);self.assertNotIn('elsewhere/ideas.md',json.dumps(index))
            (self.root/'atlas/plan.md').unlink();(self.root/'atlas/plan.md').symlink_to(self.root/'protected/hidden.md')
            receipt=engine.query(index,'orchard','atlas',limit=20);self.assertNotIn('PRIVATE_BODY_CANARY',json.dumps(receipt))

    def test_security_failures_do_not_invoke_external_fallback(self):
        with patch.object(socket,'socket',side_effect=AssertionError('network')),patch.object(subprocess,'Popen',side_effect=AssertionError('process')):
            with Engine(self.config) as engine:
                index=engine.index('atlas');index['documents']['PRINCIPLES.md']['chunks'][0]['line']='invalid'
                with self.assertRaises(Denied):engine.query(index,'orchard','atlas')

if __name__=='__main__':unittest.main()
