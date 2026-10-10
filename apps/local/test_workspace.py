"""Synthetic workspace and security regressions. No real vault or Git processes."""
import json
import os
from pathlib import Path
import socketserver
import subprocess
from unittest.mock import patch
import unittest
import app
import workspace
import test_app


class WorkspaceTests(test_app.Fixture):
    def setUp(self):
        super().setUp()
        self.vault = self.base / 'vault'; self.vault.mkdir()
        self.project = self.vault / '03 Projects' / 'Atlas'; self.project.mkdir(parents=True)
        (self.vault/'PRINCIPLES.md').write_text('# Rules\nPreserve original notes.\n')
        (self.vault/'AGENTS.md').write_text('# Rules\nPreserve unrelated work.\n')
        (self.project/'STATUS.md').write_text('## Objective\nBuild Atlas.\n## Current State\nStep 3 unfinished.\n## Next Actions\n- [ ] Finish acceptance.\n## Handoff\nResume checkpoint three.\n')
        (self.project/'handoff.md').write_text('# Handoff\nOlder standalone claim.\n')
        (self.project/'notes.md').write_text('# Ordinary project notes\nRetain detail.\n')
        (self.vault/'ordinary.md').write_text('# Ordinary knowledge\nNo project identity.\n')
        self.repos=self.base/'repos';self.repos.mkdir()
        self.repo=self.repos/'atlas';self.repo.mkdir()
        git=self.repo/'.git';(git/'refs/heads').mkdir(parents=True)
        (git/'HEAD').write_text('ref: refs/heads/main\n')
        (git/'refs/heads/main').write_text('a'*40+'\n')
        (self.repo/'AGENTS.md').write_text('# Repository instructions\nDo not deploy.\n')
        (self.repos/'AGENTS.md').write_text('# Parent repository instructions\nInspect Git state.\n')
        self.ws=workspace.Workspace(self.registry,app)

    def connect(self,path=None,kind='vault',policy='FULL_BRAIN',excluded=None):
        return self.ws.request('connect',{'path':str(path or self.vault),'kind':kind,'policy':policy,'excluded':excluded or [],'approval':True})['id']

    def project_id(self):
        return next(p['id'] for p in self.ws.inventory()['projects'] if p['name']=='Atlas')

    def link(self):
        p=self.project/'STATUS.md';p.write_text('---\npaths:\n  - '+str(self.repo)+'\n---\n'+p.read_text())

    def test_no_discovery_before_approval(self):
        with patch.object(app.ScopedEngine,'inspect',side_effect=AssertionError('Unauthorized read')):
            self.assertEqual(self.ws.inventory()['projects'],[])
            with self.assertRaises(app.Denied): self.ws.detail('unknown')

    def test_explicit_approval_and_schema(self):
        for approval in (False,1,'true'):
            with self.assertRaises(app.Denied): self.ws.request('connect',{'path':str(self.vault),'kind':'vault','policy':'FULL_BRAIN','excluded':[],'approval':approval})
        for policy in ('ALL','',None):
            with self.assertRaises(app.Denied): self.connect(policy=policy)
        self.assertEqual(self.registry.listing(),[])

    def test_full_brain_boundaries(self):
        (self.base/'outside.md').write_text('Forbidden outside source')
        self.connect()
        result=self.ws.inventory()
        self.assertIn(str(self.vault/'ordinary.md'),result['reads'])
        self.assertNotIn(str(self.base/'outside.md'),result['reads'])
        self.assertEqual(result['roots'][0]['policy'],'FULL_BRAIN')

    def test_policy_scopes(self):
        key=self.connect(policy='PROJECT_SCOPED')
        reads=self.ws.inventory()['reads']
        self.assertIn(str(self.project/'notes.md'),reads)
        self.assertNotIn(str(self.vault/'ordinary.md'),reads)
        self.connect(policy='ASK_TO_EXPAND')
        reads=self.ws.inventory()['reads']
        self.assertIn(str(self.project/'STATUS.md'),reads)
        self.assertIn(str(self.vault/'AGENTS.md'),reads)
        self.assertNotIn(str(self.project/'notes.md'),reads)
        self.assertNotIn(str(self.project/'handoff.md'),reads)
        with self.assertRaises(app.Denied): self.registry.snapshot(key)

    def test_vault_approval_only(self):
        # Mock only home identity, retaining actual ancestry/no-follow validation.
        with patch.object(app.Path,'home',return_value=self.base):
            with self.assertRaises(app.Denied): self.connect(self.base)
            brain=self.base/'brain';brain.mkdir()
            with self.assertRaises(app.Denied): self.connect(brain,kind='projects')
            self.connect(brain,kind='vault')

    def test_protected_exclusions_and_quarantine(self):
        for name in ('private','.AWS','ＳＥＣＲＥＴＳ','Cache','Protected'):
            folder=self.vault/name;folder.mkdir();(folder/'STATUS.md').write_text('Do not disclose')
        (self.vault/'custom.md').write_text('Custom excluded')
        (self.project/'leak.md').write_text('ghp_'+'q'*30)
        self.connect(excluded=['custom.md'])
        result=self.ws.inventory();detail=self.ws.detail(self.project_id())[1]
        payload=json.dumps({**result,'_snapshots':None})+json.dumps(detail)
        self.assertNotIn('Do not disclose',payload)
        self.assertNotIn('leak.md',payload)
        self.assertNotIn(str(self.vault/'custom.md'),result['reads'])
        self.assertTrue(result['excluded'])

    def test_links_traversal_aliases(self):
        (self.vault/'alias').symlink_to(self.base,target_is_directory=True)
        self.connect();result=self.ws.inventory()
        self.assertFalse(any('/alias/' in p for p in result['reads']))
        for path in (str(self.vault)+'/../vault',str(self.vault).replace('/vault','/VAULT'),str(self.vault/'alias')):
            with self.assertRaises((app.Denied,OSError)): self.connect(path)

    def test_projects_and_duplicate_prevention(self):
        nested=self.project/'checkpoints';nested.mkdir();(nested/'STATUS.md').write_text('## Current State\nOlder checkpoint')
        template=self.vault/'03 Projects/_template';template.mkdir();(template/'STATUS.md').write_text('# Template')
        self.connect();self.connect()
        projects=self.ws.inventory()['projects']
        self.assertEqual([p['name'] for p in projects],['Atlas'])
        self.assertEqual(len(self.ws.roots()),1)

    def test_missing_checkpoint(self):
        (self.project/'STATUS.md').unlink()
        self.connect();p,s=self.ws.detail(self.project_id())
        self.assertEqual(p['readiness'],'MISSING CHECKPOINT')
        self.assertIsNone(p['current']);self.assertTrue(any('progress unknown' in x for x in s['missing']))

    def test_instruction_parent_and_linked_sources(self):
        (self.vault/'shared.md').write_text('## Summary\nShared canonical source.\n')
        p=self.project/'STATUS.md';p.write_text(p.read_text()+'\n[Canonical](shared.md)\n[[shared]]\n[Escape](../../outside.md)\n')
        self.connect();_,s=self.ws.detail(self.project_id())
        self.assertIn(str(self.vault/'AGENTS.md'),s['instructions'])
        self.assertIn(str(self.vault/'PRINCIPLES.md'),s['instructions'])
        self.assertIn(str(self.vault/'shared.md'),s['documents'])
        self.assertNotIn(str(self.base/'outside.md'),s['documents'])

    def test_linked_parent_source_inside_root(self):
        (self.vault/'shared.md').write_text('## Summary\nApproved parent source.')
        p=self.project/'STATUS.md';p.write_text(p.read_text()+'\n[Shared](../../shared.md)\n')
        self.connect();_,s=self.ws.detail(self.project_id())
        self.assertIn(str(self.vault/'shared.md'),s['documents'])

    def test_existing_markdown_repository_labels(self):
        p=self.project/'STATUS.md';p.write_text(p.read_text()+'\n- **Product source:** `'+str(self.repo)+'`, existing repository.\n')
        self.connect();self.connect(self.repos,'repositories');p,_=self.ws.detail(self.project_id())
        self.assertEqual(p['repository']['path'],str(self.repo))
        self.assertEqual(p['repository']['evidence_sources'][0]['path'],str(self.project/'STATUS.md'))

    def test_linked_sources_need_separate_root_approval(self):
        extra=self.base/'additional';extra.mkdir();source=extra/'canonical.md';source.write_text('## Summary\nAdditional canonical source.')
        p=self.project/'STATUS.md';p.write_text(p.read_text()+'\n[Canonical]('+str(source)+')\n')
        self.connect();_,s=self.ws.detail(self.project_id());self.assertNotIn(str(source),s['documents'])
        root=self.connect(extra,'projects');_,s=self.ws.detail(self.project_id())
        self.assertIn(str(source),s['documents']);self.assertIn(str(source),s['default_selection'])
        self.ws.request('disconnect',{'id':root});_,s=self.ws.detail(self.project_id())
        self.assertNotIn(str(source),s['documents'])

    def test_attribution_and_canonical_handoff(self):
        self.connect();p,s=self.ws.detail(self.project_id())
        self.assertEqual(s['handoffs'][0]['path'],str(self.project/'STATUS.md'))
        self.assertEqual(p['pending']['line'],5)
        self.assertEqual(p['pending']['source'],str(self.project/'STATUS.md'))
        self.assertIn('Resume checkpoint three',s['handoffs'][0]['text'])
        self.assertTrue(all(len(x['sha256'])==64 for x in s['sources']))

    def test_summary_beyond_global_excerpt_limit(self):
        big=self.vault/'00 Early.md';big.write_text(('## Summary\nUnrelated claim\n')*150)
        self.connect();p,s=self.ws.detail(self.project_id())
        self.assertIn('Step 3 unfinished',p['current']['text'])
        self.assertTrue(any('Step 3 unfinished' in x['text'] for x in s['sections']))

    def test_exact_repository_association_and_git(self):
        self.link();self.connect();self.connect(self.repos,'repositories')
        result=self.ws.inventory();projects=result['projects']
        self.assertEqual(len(projects),1)
        self.assertEqual(projects[0]['repository']['path'],str(self.repo))
        self.assertEqual(projects[0]['repository']['branch'],'main')
        self.assertEqual(projects[0]['repository']['commit'],'a'*40)
        _,s=self.ws.detail(projects[0]['id'])
        self.assertIn(str(self.repo/'AGENTS.md'),s['instructions'])
        self.assertIn(str(self.repos/'AGENTS.md'),s['instructions'])

    def test_ambiguous_repository_matching_requires_confirmation(self):
        self.connect();self.connect(self.repos,'repositories')
        p,_=self.ws.detail(self.project_id())
        self.assertIsNone(p['repository']);self.assertEqual(len(p['suggestions']),1)
        with self.assertRaises(app.Denied): self.ws.request('confirm',{'id':p['id'],'repository':p['suggestions'][0]['id'],'approval':False})
        self.ws.request('confirm',{'id':p['id'],'repository':p['suggestions'][0]['id'],'approval':True})
        p,_=self.ws.detail(p['id']);self.assertEqual(p['repository']['path'],str(self.repo))
        self.assertIn('User-confirmed',p['repository']['evidence'])

    def test_multiple_exact_matches_not_merged(self):
        second=self.repos/'second';second.mkdir();(second/'.git').mkdir();(second/'.git/HEAD').write_text('b'*40)
        p=self.project/'STATUS.md';p.write_text('---\npaths:\n - '+str(self.repo)+'\n - '+str(second)+'\n---\n'+p.read_text())
        self.connect();self.connect(self.repos,'repositories');p,_=self.ws.detail(self.project_id())
        self.assertIsNone(p['repository']);self.assertEqual(len(p['suggestions']),2)

    def test_unapproved_repository_reference_is_never_scanned(self):
        self.link();self.connect()
        p,_=self.ws.detail(self.project_id());self.assertIsNone(p['repository'])
        self.assertEqual(self.ws.inventory()['repositories'],[])

    def test_git_no_commands_config_hooks_or_pointer_escape(self):
        (self.repo/'.git/config').write_text('[include]\npath = /outside/secret\n')
        hooks=self.repo/'.git/hooks';hooks.mkdir();(hooks/'post-checkout').write_text('exit 1')
        with patch.object(subprocess,'run',side_effect=AssertionError('No command')), patch.object(subprocess,'Popen',side_effect=AssertionError('No process')):
            self.connect(self.repos,'repositories');repo=self.ws.inventory()['repositories'][0]
        self.assertEqual(repo['commit'],'a'*40)
        (self.repo/'.git/HEAD').unlink();(self.repo/'.git/HEAD').symlink_to(self.base/'outside')
        self.assertIsNone(self.ws.inventory()['repositories'][0]['commit'])

    def test_git_detached_packed_and_malformed_head(self):
        self.connect(self.repos,'repositories')
        head=self.repo/'.git/HEAD';head.write_text('c'*40)
        self.assertEqual(self.ws.inventory()['repositories'][0]['branch'],'Detached HEAD')
        head.write_text('ref: refs/heads/main');(self.repo/'.git/refs/heads/main').unlink()
        (self.repo/'.git/packed-refs').write_text('d'*40+' refs/heads/main\n')
        self.assertEqual(self.ws.inventory()['repositories'][0]['commit'],'d'*40)
        head.write_text('ref: refs/heads/../../outside')
        self.assertIsNone(self.ws.inventory()['repositories'][0]['branch'])

    def test_prompt_grounding_and_provider_selection(self):
        self.link();self.connect();self.connect(self.repos,'repositories');key=self.project_id()
        _,s=self.ws.detail(key)
        for provider in ('Claude Code','Codex'):
            result=self.ws.request('resume',{'id':key,'selected':[str(self.project/'STATUS.md')],'provider':provider,'task':''})
            prompt=result['prompt']
            for expected in (provider,'Project: Atlas','Step 3 unfinished','Finish acceptance','Resume checkpoint three',str(self.vault/'AGENTS.md'),str(self.repo),'a'*40,'Preserve unrelated','Next recommended action'):
                self.assertIn(expected,prompt)
            self.assertNotIn('ordinary.md',prompt)
        with self.assertRaises(app.Denied): self.ws.request('resume',{'id':key,'selected':[str(self.base/'outside.md')],'provider':'Codex','task':''})

    def test_freshness_and_revocation(self):
        key=self.connect();id=self.project_id()
        p=self.project/'STATUS.md';p.write_text(p.read_text().replace('Step 3 unfinished','Step 4 unfinished'))
        result=self.ws.request('resume',{'id':id,'selected':[str(p)],'provider':'Codex','task':''})
        self.assertIn('Step 4 unfinished',result['prompt'])
        self.ws.request('disconnect',{'id':key})
        with self.assertRaises(app.Denied): self.ws.detail(id)
        self.assertEqual(self.ws.inventory()['reads'],[])
        self.assertTrue(p.exists())

    def test_restart_no_grants_or_content_storage(self):
        self.connect();self.ws.inventory()
        payload=(self.base/'state/projects.json').read_bytes()
        self.assertNotIn(b'Build Atlas',payload)
        self.assertNotIn(b'checkpoint three',payload)
        other=app.Registry(self.base/'state');self.addCleanup(other.close)
        other_ws=workspace.Workspace(other,app)
        self.assertFalse(other_ws.roots()[0]['approved'])
        self.assertEqual(other_ws.inventory()['projects'],[])
        with self.assertRaises(app.Denied): other_ws.knowledge(next(iter(other.projects.values())))

    def test_project_removal_and_root_replacement(self):
        self.connect();id=self.project_id();self.ws.request('remove',{'id':id})
        self.assertFalse(self.ws.inventory()['projects'])
        self.assertTrue((self.project/'STATUS.md').exists())
        self.vault.rename(self.base/'old-vault');self.vault.mkdir()
        with self.assertRaises(app.Denied): self.ws.inventory()

    def test_operation_bounds(self):
        self.connect()
        with patch.object(app,'MAX_ENTRIES',0):
            # Repository enumeration uses the same bound without knowledge reads.
            self.connect(self.repos,'repositories')
            with self.assertRaises(app.Denied): self.ws.inventory()
        with patch.object(self.ws,'knowledge',wraps=self.ws.knowledge):
            record=self.registry.projects[next(r['id'] for r in self.ws.roots() if r['kind']=='vault')]
            with self.assertRaises(app.Denied): self.ws.knowledge(record,budget=1)


class WorkspaceHTTPTests(test_app.Fixture):
    request=test_app.ServerTests.request
    def setUp(self):
        super().setUp()
        with patch.object(socketserver.TCPServer,'server_bind'), patch.object(socketserver.TCPServer,'server_activate'):
            self.server=app.LocalServer(self.registry,4317)
        self.addCleanup(self.server.server_close)

    def test_workspace_http_workflow_and_no_raw_endpoint(self):
        status,_,body=self.request('POST','/api/workspace/connect',{'path':str(self.root),'kind':'projects','policy':'FULL_BRAIN','excluded':[],'approval':True})
        self.assertEqual(status,200);root=json.loads(body)['id']
        status,_,body=self.request('POST','/api/workspace/inventory',{})
        self.assertEqual(status,200);key=json.loads(body)['projects'][0]['id'];self.assertNotIn('_snapshots',json.loads(body))
        status,_,body=self.request('POST','/api/workspace/detail',{'id':key})
        self.assertEqual(status,200);detail=json.loads(body);self.assertNotIn('documents',detail)
        status,_,body=self.request('POST','/api/workspace/resume',{'id':key,'selected':detail['default_selection'],'provider':'Codex','task':''})
        self.assertEqual(status,200);self.assertIn('Step 2 incomplete',json.loads(body)['prompt'])
        self.assertEqual(self.request('GET','/api/workspace/file?path='+str(self.root/'STATUS.md'))[0],404)
        self.assertNotEqual(self.request('POST','/api/overview',{'id':root})[0],200)
        self.assertEqual(self.request('POST','/api/workspace/disconnect',{'id':root})[0],200)
        self.assertNotEqual(self.request('POST','/api/workspace/detail',{'id':key})[0],200)

    def test_workspace_cross_origin_csrf_traversal(self):
        data={'path':str(self.root),'kind':'vault','policy':'FULL_BRAIN','excluded':[],'approval':True}
        for headers in ({'Origin':'https://evil.example'},{'Origin':''},{'X-Skeptic-Token':'invalid'},{'Host':'evil.example'},{'Sec-Fetch-Site':'cross-site'}):
            self.assertNotEqual(self.request('POST','/api/workspace/connect',data,headers)[0],200)
        data['path']=str(self.root)+'/../project'
        self.assertNotEqual(self.request('POST','/api/workspace/connect',data)[0],200)
        data['path']=str(self.root);data['approval']=False
        self.assertNotEqual(self.request('POST','/api/workspace/connect',data)[0],200)
        self.assertEqual(self.registry.listing(),[])


if __name__=='__main__': unittest.main()
