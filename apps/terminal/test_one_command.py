import contextlib
import fcntl
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import install
import open_sessions as live
import session_review as review
import switcher as s
import test_sessions as fixture
from types import SimpleNamespace

class NativeMetadataTests(unittest.TestCase):
    def test_exact_pid_record_only_and_never_automatic_proof(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve()
            record=root/'23.json'
            record.write_text(json.dumps(dict(pid=23,sessionId=fixture.ID,cwd='/project',busy=False,name='Work')))
            value=live.native_record(23,root)
            self.assertEqual(value['id'],fixture.ID)
            self.assertIsNone(live.native_record(24,root))
            record.write_text(json.dumps(dict(pid=24,sessionId=fixture.ID,cwd='/project')))
            self.assertIsNone(live.native_record(23,root))
    def test_symlink_and_oversize_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve(); body=root/'body'
            body.write_text(json.dumps(dict(pid=23,sessionId=fixture.ID)))
            (root/'23.json').symlink_to(body)
            self.assertIsNone(live.native_record(23,root))
            (root/'24.json').write_text('x'*16385)
            self.assertIsNone(live.native_record(24,root))
    def test_native_prefill_needs_confirmation_without_uuid_typing(self):
        candidate=dict(pid=23,id=fixture.ID,cwd='/project',name='Work',busy=False)
        row=dict(window=1,tab=1,tty='/dev/ttys001',busy=True,pids=[23],process='Claude',candidates=[candidate])
        adapter=__import__('unittest.mock',fromlist=['Mock']).Mock()
        adapter.discover.return_value=[dict(id=fixture.ID)]
        args=SimpleNamespace(continue_open=True)
        answers=iter(['discover','skip','confirm'])
        with patch('session_review.continue_selected',return_value=0) as continuation:
            live.run(args,None,adapter,None,'/project',picker=lambda *_:0,ask=lambda _:next(answers),collector=lambda:[row])
            args.open_source_check()
        continuation.assert_called_once()
        adapter.discover.assert_called_once_with(None,'/project',True,fixture.ID,None)
    def test_busy_source_refuses_before_transcript(self):
        candidate=dict(pid=23,id=fixture.ID,busy=True)
        row=dict(window=1,tab=1,tty='/dev/ttys001',busy=True,pids=[23],process='Claude',candidates=[candidate])
        adapter=__import__('unittest.mock',fromlist=['Mock']).Mock(); answers=iter(['discover','skip','confirm'])
        with self.assertRaises(s.host.Denied):
            live.run(SimpleNamespace(continue_open=True),None,adapter,None,'/project',picker=lambda *_:0,
                ask=lambda _:next(answers),collector=lambda:[row])
        adapter.discover.assert_not_called()

class LauncherTests(unittest.TestCase):
    def test_retarget_backup_idempotent_preserves_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            home=Path(directory).resolve(); (home/'.local/bin').mkdir(parents=True)
            target=home/'.local/bin/skeptic'
            old='#!/bin/sh\n# Skeptic launcher; rerun installer after moving repository.\nexec python3 -B /old/apps/terminal/switcher.py "$@"\n'
            target.write_text(old); target.chmod(0o700)
            (home/'.zshrc').write_text('unrelated shell settings')
            source=home/'Developer/integration/apps/terminal'
            install.activate_launcher(home,source); install.activate_launcher(home,source)
            self.assertEqual(target.with_name('skeptic.before-integration').read_text(),old)
            self.assertIn('"$HOME/Developer/integration/apps/terminal/switcher.py"',target.read_text())
            self.assertEqual((home/'.zshrc').read_text(),'unrelated shell settings')
    def test_custom_launcher_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            home=Path(directory).resolve(); (home/'.local/bin').mkdir(parents=True)
            target=home/'.local/bin/skeptic'; target.write_text('#!/bin/sh\necho customized\n')
            before=target.read_bytes()
            with self.assertRaises(ValueError): install.activate_launcher(home,home/'source')
            self.assertEqual(target.read_bytes(),before)

class ContinuationTests(unittest.TestCase):
    setUp=fixture.SessionTests.setUp
    tearDown=fixture.SessionTests.tearDown
    rows=fixture.SessionTests.rows
    write_session=fixture.SessionTests.write_session
    approved=fixture.SessionTests.approved
    discover=fixture.SessionTests.discover
    snapshot=fixture.SessionTests.snapshot
    def args(self):
        return SimpleNamespace(cwd=str(self.repo),vault=str(self.vault),conversation_only=False,repo=[],provider='codex',model=None)
    def model(self):
        fake=self.root/'fake-codex'; capture=self.root/'capture.json'
        fake.write_text('#!'+__import__('sys').executable+'\nimport sys,json,os\nfrom pathlib import Path\nPath('+repr(str(capture))+').write_text(json.dumps({"cwd":os.getcwd(),"prompt":sys.argv[-1]}))\n')
        fake.chmod(0o700)
        return dict(id='codex',label='Fixture Codex',executable=str(fake),local=False),capture
    def test_selected_earlier_task_reaches_fake_provider_with_canonical_and_inventory(self):
        source=self.rows(); source[1]['message']['content']='Fix the export. Preserve the staging changes.'
        source[2]['message']['content']=[dict(type='text',text='The export is not done.')]
        self.file=self.write_session(self.origin,source)
        item=self.discover(session_id=fixture.ID)[0]; before=self.file.read_bytes()
        model,capture=self.model()
        class Terminal(io.StringIO):
            def isatty(self): return True
        with contextlib.redirect_stdout(Terminal()),patch('sys.stdin.isatty',return_value=True),patch.object(s,'providers',return_value=[model]),patch('builtins.input',side_effect=['project-clear','send']):
            result=review.continue_selected(self.args(),self.state,self.adapter,self.access,item,picker=lambda *_:0)
        self.assertEqual(result,0); self.assertEqual(before,self.file.read_bytes())
        packet=json.loads(capture.read_text())
        self.assertEqual(packet['cwd'],str(self.repo))
        for expected in ('Fix the export','Continue the reply','CANONICAL_NEXT','GOVERNING_SOURCE','task_inventory','Preserve the staging changes'):
            self.assertIn(expected,packet['prompt'])
        self.assertNotIn('RAW_TOOL_SECRET',packet['prompt'])
    def test_preview_never_launches(self):
        item=self.discover(session_id=fixture.ID)[0]
        picks=iter([0,1])
        with patch.object(s,'launch',side_effect=AssertionError('Preview launched')),contextlib.redirect_stdout(io.StringIO()):
            self.approved(lambda:review.continue_selected(self.args(),self.state,self.adapter,self.access,item,picker=lambda *_:next(picks)))
    def test_writer_decline_never_launches(self):
        item=self.discover(session_id=fixture.ID)[0]; model,capture=self.model()
        class Terminal(io.StringIO):
            def isatty(self): return True
        with contextlib.redirect_stdout(Terminal()),patch('sys.stdin.isatty',return_value=True),patch.object(s,'providers',return_value=[model]),patch('builtins.input',side_effect=lambda prompt: 'cancel' if 'project-clear' in prompt else 'send'):
            with self.assertRaises(s.host.Denied): review.continue_selected(self.args(),self.state,self.adapter,self.access,item,picker=lambda *_:0)
        self.assertFalse(capture.exists())
    def test_source_append_during_send_refuses_launch(self):
        item=self.discover(session_id=fixture.ID)[0]; model,capture=self.model()
        class Terminal(io.StringIO):
            def isatty(self): return True
        def answer(prompt):
            if 'project-clear' in prompt:return 'project-clear'
            with self.file.open('a') as out:out.write('\n')
            return 'send'
        with contextlib.redirect_stdout(Terminal()),patch('sys.stdin.isatty',return_value=True),patch.object(s,'providers',return_value=[model]),patch('builtins.input',side_effect=answer):
            with self.assertRaises(s.host.Denied):review.continue_selected(self.args(),self.state,self.adapter,self.access,item,picker=lambda *_:0)
        self.assertFalse(capture.exists())

    def test_cooperative_writer_reservation_refuses_second_launch(self):
        fd=os.open('continuation-writer.lock',os.O_RDWR|os.O_CREAT,0o600,dir_fd=self.state.fd)
        try:
            fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with patch.object(s,'launch',side_effect=AssertionError('Overlapping writer launched')):
                with self.assertRaisesRegex(s.host.Denied,'writer is active'):
                    s.tracked_launch(self.state,{},str(self.repo),'packet',str(self.vault),'task')
        finally:os.close(fd)
    def test_bare_entry_routes_to_live_continuation_without_history(self):
        with patch.object(s,'State',return_value=self.state),patch.object(self.state,'close'),patch.object(s,'session_cli',return_value=0) as entry:
            self.assertEqual(s.main([]),0)
        args=entry.call_args.args[0]
        self.assertEqual((args.command,args.action,args.provider,args.continue_open),('sessions','open','codex',True))
    def test_actual_cli_open_tab_to_fake_codex_on_pty(self):
        import pty, select, sys, time
        model,capture=self.model(); before=self.file.read_bytes()
        candidate=dict(pid=23,id=fixture.ID,cwd=str(self.repo),name='Fixture work',busy=False)
        row=dict(window=1,tab=1,tty='/dev/ttys001',busy=True,pids=[23],process='Claude',candidates=[candidate])
        wrapper=self.root/'run_cli_fixture.py'
        wrapper.write_text('import sys\nsys.path.insert(0,'+repr(str(Path(s.__file__).parent))+')\nimport switcher,open_sessions\nopen_sessions.collect=lambda: '+repr([row])+'\nswitcher.providers=lambda: '+repr([model])+'\nsys.exit(switcher.main(sys.argv[1:]))\n')
        master,slave=pty.openpty()
        process=subprocess.Popen([sys.executable,'-B',str(wrapper),'sessions','open','--continue','--with','codex',
            '--project',self.origin,'--cwd',str(self.repo),'--state-dir',str(self.root/'state'),
            '--session-root',str(self.storage),'--vault',str(self.vault)],stdin=slave,stdout=slave,stderr=slave,cwd=str(self.repo))
        os.close(slave); seen=bytearray(); cursor=0
        def expect(text,send=b''):
            nonlocal cursor
            deadline=time.monotonic()+10
            while text.encode() not in seen[cursor:]:
                if time.monotonic()>deadline:self.fail('PTY timeout '+text+'\n'+seen.decode(errors='replace')[-3000:])
                if select.select([master],[],[],.1)[0]:
                    try:chunk=os.read(master,65536)
                    except OSError:chunk=b''
                    if not chunk:self.fail('CLI ended before '+text+'\n'+seen.decode(errors='replace')[-3000:])
                    seen.extend(chunk)
            cursor=seen.index(text.encode(),cursor)+len(text.encode())
            if send:os.write(master,send)
        try:
            expect('Type discover',b'discover\n')
            expect('Type identify',b'identify\n')
            expect('Type approve:',b'approve\n')
            expect('Type approve:',b'approve\n')
            expect('Open Terminal sessions first',b'\r')
            expect('Type confirm if',b'confirm\n')
            expect('Choose the work to resume',b'\x1b[B\r')
            expect('Continue this selected request',b'\r')
            expect('type project-clear',b'project-clear\n')
            expect('Type send',b'send\n')
            self.assertEqual(process.wait(timeout=10),0)
        finally:
            if process.poll() is None:process.kill();process.wait()
            os.close(master)
        self.assertEqual(self.file.read_bytes(),before)
        packet=json.loads(capture.read_text())
        self.assertIn('Continue the reply',packet['prompt']); self.assertIn('CANONICAL_NEXT',packet['prompt'])
        self.assertIn('task_inventory',packet['prompt']);self.assertNotIn('RAW_TOOL_SECRET',packet['prompt'])
        self.assertNotIn('Exact session UUID or transcript path',seen.decode(errors='replace'))
        self.assertIn('Last user request — CANDIDATE ONLY',seen.decode(errors='replace'))
        self.assertIn('Email contact with Boris',seen.decode(errors='replace'))
