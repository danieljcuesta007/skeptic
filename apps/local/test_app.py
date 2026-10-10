"""Synthetic-only acceptance of the local host and discovery boundaries."""
import contextlib
import http.client
import io
import json
import os
import re
from pathlib import Path
import socket
import socketserver
import tempfile
import threading
import unittest
from unittest.mock import patch

import app


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / 'project'
        self.root.mkdir()
        (self.root / 'STATUS.md').write_text('# Atlas\n## Objective\nBuild a synthetic tool.\n## Current State\nStep 2 incomplete.\n## Next Actions\n- [ ] Verify fixtures.\n## Handoff\nResume Step 2.\n')
        (self.root / 'AGENTS.md').write_text('# Instructions\nAsk before deploying.\n')
        (self.root / 'research.md').write_text('# Research\nAn ordinary source.\n')
        self.registry = app.Registry(self.base / 'state')
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(self.registry.close)

    def approve(self, root=None, excluded=None):
        return self.registry.approve(str(root or self.root), excluded or [])


class DiscoveryTests(Fixture):
    def test_unapproved_roots(self):
        with self.assertRaises(app.Denied): self.registry.snapshot('unknown')
        self.assertEqual(self.registry.listing(), [])

    def test_explicit_root_scope(self):
        (self.base / 'outside.md').write_text('Outside approval')
        key = self.approve()
        snapshot = self.registry.snapshot(key)
        self.assertEqual(set(snapshot['documents']), {'STATUS.md', 'AGENTS.md', 'research.md'})
        self.assertNotIn('outside.md', snapshot['reads'])

    def test_broad_roots_and_protected_root(self):
        for path in (str(Path.home()), str(Path.home() / 'brain'), '/', str(self.base / '.AWS')):
            with self.subTest(path=path), self.assertRaises(app.Denied): app.approve_root(path)

    def test_traversal(self):
        for suffix in ('/../project', '/./', '//child', '/'):
            with self.subTest(suffix=suffix), self.assertRaises(app.Denied): app.approve_root(str(self.root) + suffix)
        key = self.approve()
        for path in ('../outside.md', '/outside.md', 'a/../STATUS.md', 'a//b.md'):
            with app.ScopedEngine(str(self.root), self.registry.active[key], []) as engine:
                with self.assertRaises(app.Denied): engine.inspect(path, True)

    def test_symlink_root_and_parent(self):
        alias = self.base / 'alias'
        alias.symlink_to(self.root, target_is_directory=True)
        for path in (alias, alias / 'child'):
            with self.subTest(path=path), self.assertRaises((app.Denied, OSError)): app.approve_root(str(path))

    def test_symlink_hardlink_special_files(self):
        outside = self.base / 'outside.md'; outside.write_text('Forbidden body')
        (self.root / 'link.md').symlink_to(outside)
        (self.root / 'directory').symlink_to(self.base, target_is_directory=True)
        os.link(outside, self.root / 'hard.md')
        os.mkfifo(self.root / 'pipe.md')
        key = self.approve(); snapshot = self.registry.snapshot(key)
        self.assertFalse({'link.md','hard.md','pipe.md'} & set(snapshot['documents']))
        self.assertGreaterEqual(len(snapshot['excluded']), 4)
        with app.ScopedEngine(str(self.root), self.registry.active[key], []) as engine:
            for path in ('link.md', 'hard.md', 'pipe.md', 'directory/outside.md'):
                with self.assertRaises((app.Denied, OSError)): engine.inspect(path, True)

    def test_case_alias_root_and_source(self):
        with self.assertRaises((app.Denied, OSError)): app.approve_root(str(self.root).replace('/project','/PROJECT'))
        key = self.approve()
        with app.ScopedEngine(str(self.root), self.registry.active[key], []) as engine:
            for path in ('status.md', 'agents.md'):
                with self.assertRaises(app.Denied): engine.inspect(path, True)

    def test_protected_names_case_unicode_and_custom(self):
        protected_identities = set()
        for name in ('.AWS', 'ＳＥＣＲＥＴＳ', '.env-prod', 'private', 'Protected', '.git'):
            folder = self.root / name; folder.mkdir(); (folder/'hidden.md').write_text('Never read')
            protected_identities.add((folder.stat().st_dev,folder.stat().st_ino))
        key = self.approve(excluded=['private'])
        listdir = os.listdir
        def checked_listdir(fd):
            if isinstance(fd,int):
                info=os.fstat(fd)
                if (info.st_dev,info.st_ino) in protected_identities:
                    raise AssertionError('Protected directory enumerated')
            return listdir(fd)
        with patch.object(os,'listdir',side_effect=checked_listdir):
            snapshot = self.registry.snapshot(key)
        self.assertEqual(set(snapshot['reads']), {'STATUS.md', 'AGENTS.md', 'research.md'})
        self.assertNotIn('hidden.md', json.dumps(snapshot['excluded']))

    def test_credential_quarantine(self):
        token = 'ghp_' + 'X'*30
        (self.root/'STATUS.md').write_text('## Handoff\n'+token)
        key = self.approve(); snapshot = self.registry.snapshot(key)
        self.assertNotIn('STATUS.md',snapshot['documents'])
        prompt = app.continuation(str(self.root), snapshot, ['AGENTS.md'], 'Codex', '')
        self.assertNotIn(token, prompt)
        self.assertIn('No exact STATUS.md', prompt)

    def test_malformed_markdown(self):
        (self.root/'bad.md').write_bytes(b'\xff\xfe')
        (self.root/'binary.md').write_bytes(b'a\x00b')
        (self.root/'research.md').write_text('##\n```\n<script>alert(1)</script>\n## Next Actions\nUnclosed fence remains data\n')
        snapshot = self.registry.snapshot(self.approve())
        self.assertNotIn('bad.md',snapshot['documents'])
        self.assertNotIn('binary.md',snapshot['documents'])
        self.assertIn('research.md', snapshot['documents'])

    def test_missing_checkpoint_handoff_and_actions(self):
        (self.root/'STATUS.md').unlink()
        snapshot = self.registry.snapshot(self.approve())
        self.assertEqual(snapshot['checkpoints'], [])
        self.assertEqual(snapshot['handoffs'], [])
        self.assertTrue(any('Next Actions' in s for s in snapshot['missing']))
        self.assertTrue(any('No exact STATUS.md' in s for s in snapshot['missing']))

    def test_attribution_actual_lines_and_verbatim(self):
        snapshot = self.registry.snapshot(self.approve())
        section = next(s for s in snapshot['sections'] if s['heading']=='Next Actions')
        self.assertEqual(section['line'], 6)
        self.assertEqual(section['path'], 'STATUS.md')
        self.assertEqual(section['text'], '- [ ] Verify fixtures.')
        self.assertEqual(len(section['sha256']), 64)

    def test_nested_checkpoint_sections_and_handoff_named_files(self):
        (self.root/'STATUS.md').write_text('## Current State\n### Latest checkpoint\nIncomplete milestone\n## Handoff\n### Latest transfer\nResume safely\n## Next Actions\n- [ ] Pending task\n')
        (self.root/'handoff.md').write_text('Standalone transfer fixture')
        snapshot=self.registry.snapshot(self.approve())
        self.assertIn('Resume safely',snapshot['handoffs'][0]['text'])
        self.assertTrue(any('Standalone transfer fixture' in s['text'] for s in snapshot['handoffs']))
        self.assertTrue(any('Incomplete milestone' in s['text'] for s in snapshot['sections']))
        task=next(s for s in snapshot['sections'] if s['heading'].startswith('Unchecked'))
        self.assertEqual(task['line'],8)

    def test_multiple_projects_and_remove(self):
        other = self.base/'other'; other.mkdir(); (other/'STATUS.md').write_text('## Current State\nOther project')
        first, second = self.approve(), self.approve(other)
        self.assertEqual(len(self.registry.listing()),2)
        self.assertNotIn('Other project',json.dumps(self.registry.snapshot(first)))
        self.assertIn('Other project',json.dumps(self.registry.snapshot(second)))
        self.registry.remove(first)
        with self.assertRaises(app.Denied): self.registry.snapshot(first)
        self.assertTrue((self.root/'STATUS.md').exists())

    def test_restart_requires_fresh_approval_no_content_persisted(self):
        key = self.approve(); self.registry.snapshot(key)
        state = (self.base/'state/projects.json').read_text()
        self.assertNotIn('synthetic tool',state)
        self.assertNotIn('Resume Step 2',state)
        with contextlib.closing(app.Registry(self.base/'state')) as registry:
            self.assertFalse(registry.listing()[0]['approved'])
            with self.assertRaises(app.Denied): registry.snapshot(key)
        self.assertEqual((self.base/'state/projects.json').stat().st_mode & 0o777,0o600)

    def test_replaced_root_is_denied(self):
        key = self.approve()
        self.root.rename(self.base/'old')
        self.root.mkdir(); (self.root/'STATUS.md').write_text('Unauthorized replacement')
        with self.assertRaises(app.Denied): self.registry.snapshot(key)

    def test_resume_generation_and_selection_scope(self):
        snapshot = self.registry.snapshot(self.approve())
        for provider in ('Claude Code','Codex'):
            prompt = app.continuation(str(self.root),snapshot,['STATUS.md'],provider,'Finish fixtures')
            self.assertIn(provider,prompt)
            self.assertIn(str(self.root/'STATUS.md'),prompt)
            self.assertIn(str(self.root/'AGENTS.md'),prompt)
            self.assertIn('Step 2 incomplete',prompt)
            self.assertIn('not permission',prompt)
            self.assertNotIn('An ordinary source',prompt)
        for selection in (['../outside.md'], ['/etc/passwd'], ['status.md'], [], ['STATUS.md']*2):
            with self.assertRaises(app.Denied): app.continuation(str(self.root),snapshot,selection,'Codex','')
        with self.assertRaises(app.Denied): app.continuation(str(self.root),snapshot,['STATUS.md'],'Live API','')

    def test_fresh_prompt_and_removed_source(self):
        key = self.approve()
        self.registry.snapshot(key)
        (self.root/'STATUS.md').write_text('## Current State\nNew checkpoint')
        snapshot = self.registry.snapshot(key)
        prompt = app.continuation(str(self.root),snapshot,['STATUS.md'],'Codex','')
        self.assertIn('New checkpoint',prompt)
        self.assertNotIn('Step 2 incomplete',prompt)
        (self.root/'STATUS.md').unlink()
        with self.assertRaises(app.Denied): app.continuation(str(self.root),self.registry.snapshot(key),['STATUS.md'],'Codex','')

    def test_limits_oversize_and_no_partial_overview(self):
        (self.root/'large.md').write_bytes(b'x'*128001)
        key = self.approve(); snapshot = self.registry.snapshot(key)
        self.assertNotIn('large.md',snapshot['documents'])
        with patch.object(app,'MAX_FILES',1), self.assertRaises(app.Denied): self.registry.snapshot(key)
        with patch.object(app,'MAX_ENTRIES',1), self.assertRaises(app.Denied): self.registry.snapshot(key)
        with patch.object(app,'MAX_BYTES',20), self.assertRaises(app.Denied): self.registry.snapshot(key)

    def test_no_project_writes_or_network(self):
        key = self.approve()
        before = {p.name:p.read_bytes() for p in self.root.iterdir()}
        with patch.object(socket,'socket',side_effect=AssertionError('Network forbidden')):
            snapshot=self.registry.snapshot(key)
            app.continuation(str(self.root),snapshot,['STATUS.md'],'Codex','')
        self.assertEqual(before,{p.name:p.read_bytes() for p in self.root.iterdir()})

    def test_registry_symlink_refused(self):
        alias=self.base/'alias'; alias.symlink_to(self.base/'state',target_is_directory=True)
        with self.assertRaises(OSError): app.Registry(alias)

    def test_registry_malformed_and_linked_file(self):
        (self.base/'state/projects.json').write_text('null')
        os.chmod(self.base/'state/projects.json',0o600)
        with self.assertRaises(app.Denied): app.Registry(self.base/'state')
        (self.base/'state/projects.json').unlink()
        outside=self.base/'outside.json';outside.write_text('[]')
        (self.base/'state/projects.json').symlink_to(outside)
        with self.assertRaises(OSError): app.Registry(self.base/'state')

    def test_public_asset_links_refused(self):
        for name,_ in app.ASSETS.values(): (self.root/name).write_text('Synthetic public asset')
        outside=self.base/'outside.html';outside.write_text('Private fixture')
        (self.root/'index.html').unlink();(self.root/'index.html').symlink_to(outside)
        with patch.object(app,'HERE',self.root), self.assertRaises(app.Denied): app.public_assets()


class MemorySocket:
    """Socket I/O boundary only; actual request parsing and responses remain exercised."""
    def __init__(self, data):
        self.input = io.BytesIO(data)
        self.output = io.BytesIO()
    def makefile(self, *args, **kwargs): return self.input
    def sendall(self, data): self.output.write(data)


class ServerTests(Fixture):
    def setUp(self):
        super().setUp()
        # Mock only the denied socket bind/listen boundary, not the HTTP parser or host logic.
        with patch.object(socketserver.TCPServer, 'server_bind'), patch.object(socketserver.TCPServer, 'server_activate'):
            self.server = app.LocalServer(self.registry, 4317)
        self.addCleanup(self.server.server_close)

    def request(self, method, path, data=None, headers=None, raw=None):
        body = raw if raw is not None else json.dumps(data).encode() if data is not None else None
        hdr={'Host':f'127.0.0.1:{self.server.server_port}'}
        if method=='POST':
            hdr.update({'Origin':self.server.origin,'Content-Type':'application/json','X-Skeptic-Token':self.server.token})
        if headers: hdr.update(headers)
        if body is not None: hdr['Content-Length'] = str(len(body))
        request = f'{method} {path} HTTP/1.1\r\n' + ''.join(f'{k}: {v}\r\n' for k,v in hdr.items()) + '\r\n'
        transport = MemorySocket(request.encode() + (body or b''))
        app.Handler(transport, ('127.0.0.1', 54321), self.server)
        response = http.client.HTTPResponse(MemorySocket(transport.output.getvalue()))
        response.begin()
        try: return response.status, dict(response.getheaders()), response.read()
        finally: response.close()

    def test_usage_route_requires_session_and_refuses_extra_fields(self):
        status,_,body=self.request('POST','/api/usage',{'op':'read'})
        self.assertEqual(status,200);self.assertFalse(json.loads(body)['local_enabled'])
        status,_,_=self.request('POST','/api/usage',{'op':'enable'},headers={'X-Skeptic-Token':'wrong'})
        self.assertEqual(status,400)
        self.assertFalse(self.server.usage.enabled)
        status,_,_=self.request('POST','/api/usage',{'op':'read','path':'/etc/passwd'})
        self.assertEqual(status,400)

    def test_usage_http_save_restore_and_no_file_context(self):
        reading={'provider':'midjourney','model':'Synthetic MJ','remaining':2,'limit':10,'unit':'GPU hours','resets_at':None,'observed_at':None}
        status,_,body=self.request('POST','/api/usage',{'op':'save','reading':reading})
        self.assertEqual(status,200)
        parsed=json.loads(body);self.assertEqual(parsed['rows'][0]['windows'][0]['remaining'],2)
        self.assertNotIn('documents',parsed)
        self.assertTrue((self.base/'state/usage.json').exists())

    def test_loopback_only_and_asset_allowlist(self):
        self.assertEqual(self.server.server_address[0],'127.0.0.1')
        for path in ('/','/app.js','/style.css'):
            status, headers, _ = self.request('GET',path)
            self.assertEqual(status,200)
            self.assertIn("default-src 'none'",headers['Content-Security-Policy'])
            self.assertEqual(headers['Cache-Control'],'no-store')
            self.assertNotIn('Access-Control-Allow-Origin',headers)
        for path in ('/../../etc/passwd','/%2e%2e/STATUS.md','/STATUS.md','/.skeptic-local/projects.json','/app.py','/api/overview?id=1'):
            self.assertEqual(self.request('GET',path)[0],404)

    def test_no_dns_lookup_on_start(self):
        with patch.object(socket,'getfqdn',side_effect=AssertionError('DNS forbidden')):
            with patch.object(socketserver.TCPServer,'server_bind'), patch.object(socketserver.TCPServer,'server_activate'):
                server=app.LocalServer(self.registry,4318)
                server.server_close()

    def test_host_origin_csrf_and_fetch_site(self):
        for headers in ({'Host':'evil.example'}, {'Host':f'localhost:{self.server.server_port}'},
                        {'Origin':'https://evil.example'}, {'X-Skeptic-Token':'wrong'},
                        {'Origin':''}, {'Sec-Fetch-Site':'cross-site'}):
            with self.subTest(headers=headers):
                self.assertNotEqual(self.request('POST','/api/projects',{},headers)[0],200)
        self.assertEqual(self.request('GET','/api/session',headers={'Sec-Fetch-Site':'cross-site'})[0],403)
        self.assertEqual(self.request('OPTIONS','/api/approve')[0],405)

    def test_no_read_without_approval_or_extra_authority(self):
        for request in ({'path':str(self.root),'excluded':[],'approval':False},
                        {'path':str(self.root),'excluded':[],'approval':True,'mode':'FULL_BRAIN'}):
            self.assertNotEqual(self.request('POST','/api/approve',request)[0],200)
        self.assertNotEqual(self.request('POST','/api/overview',{'id':'unknown'})[0],200)
        self.assertEqual(self.registry.listing(),[])

    def test_complete_http_workflow(self):
        status, _, raw = self.request('POST','/api/approve',{'path':str(self.root),'excluded':[],'approval':True})
        self.assertEqual(status,200); key=json.loads(raw)['id']
        status, _, raw = self.request('POST','/api/overview',{'id':key})
        self.assertEqual(status,200); self.assertNotIn('documents',json.loads(raw))
        status, _, raw = self.request('POST','/api/resume',{'id':key,'selected':['STATUS.md'],'provider':'Codex','task':''})
        self.assertEqual(status,200); self.assertIn('Step 2 incomplete',json.loads(raw)['prompt'])
        self.assertEqual(self.request('POST','/api/remove',{'id':key})[0],200)
        self.assertNotEqual(self.request('POST','/api/overview',{'id':key})[0],200)

    def test_malformed_request_and_size_bounds(self):
        self.assertNotEqual(self.request('POST','/api/projects',raw=b'{}'+b' '*16383)[0],200)
        for raw in (b'[]',b'{broken',b'{"id":{}}',b'null', b'x'*16385):
            self.assertNotEqual(self.request('POST','/api/overview',raw=raw)[0],200)
        self.assertNotEqual(self.request('POST','/api/projects',{}, {'Content-Type':'text/plain'})[0],200)
        self.assertEqual(self.request('POST','/api/execute',{'command':'anything'})[0],404)

    def test_ui_private_content_is_text_only(self):
        script = (app.HERE/'app.js').read_text()
        self.assertNotIn('innerHTML',script)
        self.assertNotIn('localStorage',script)
        self.assertNotIn('sessionStorage',script)
        self.assertNotIn('https://',script)
        html=(app.HERE/'index.html').read_text()
        self.assertNotIn('onclick=',html)
        self.assertIn('textContent',script)

    def test_monochrome_palette(self):
        css = (app.HERE / 'style.css').read_text()
        for color in re.findall(r'#([a-fA-F0-9]{3,8})\b', css):
            if len(color) not in (3, 4, 6, 8): continue
            channels = list(color[:3]) if len(color) <= 4 else [color[:2], color[2:4], color[4:6]]
            self.assertEqual(len(set(c.lower() for c in channels)), 1, color)
        self.assertNotRegex(css, r'--red|(?:color|background)\s*:\s*(?:red|blue|green)|(?:rgb|hsl)a?\(')
        self.assertIn('.brand span{color:var(--ink)}', css)
        self.assertIn('accent-color:var(--ink)', css)

    def test_monochrome_control_contrast(self):
        css = (app.HERE / 'style.css').read_text()
        self.assertIn('--ink:#000000;--paper:#FFFFFF', css)
        self.assertRegex(css, r'button\{[^}]*background:var\(--ink\);color:#fff')
        self.assertIn('background:white;color:black', css)
        self.assertRegex(css, r'#global-nav button\[aria-pressed=true\]\{background:#fff;color:#000;')
        self.assertIn(':focus-visible{outline:3px solid #000;outline-offset:3px}', css)
        self.assertRegex(css, r'button:disabled\{background:#555;color:#fff;[^}]*opacity:1;')
        gray = (85 / 255 + .055) / 1.055
        self.assertGreaterEqual(1.05 / (gray ** 2.4 + .05), 7)


if __name__ == '__main__': unittest.main()
