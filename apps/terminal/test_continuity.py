"""Provider-neutral catch-up using synthetic Git/vaults and fake executables only."""
import contextlib
import copy
import fcntl
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

import continuity as c
import switcher as s
import test_switcher as fixtures


class ContinuityTests(unittest.TestCase):
    setUp = fixtures.SwitchTests.setUp
    seed = fixtures.SwitchTests.seed
    tearDown = fixtures.SwitchTests.tearDown

    def view(self, provider='claude'):
        return s.assemble(self.state, str(self.repo), str(self.vault), target=provider)

    def record(self, provider='claude', phase='explicit_checkpoint', code=None, seed=False):
        self.view(provider)
        self.assertIsNone(c.Index(self.state).record(self.state.observation, provider, phase, code, seed))

    def advance(self):
        self.status.write_text(self.status.read_text().replace('Newest milestone pending', 'Codex reports UI implemented; browser review pending').replace('Keep files', 'Keep files\n- Use provider-neutral routing').replace('- [ ] Test UI', '- [x] Fixture says UI completed\n- [ ] Verify in browser'))
        (self.repo / 'new.py').write_text('new_work = True\n')

    def test_claude_codex_claude_receives_newer_state(self):
        self.record('claude', 'selected_source_checkpoint')
        self.record('codex', 'launch_started')
        self.advance(); self.record('codex', 'provider_exited', 0)
        current, packet = self.view('claude')
        self.assertTrue(current['catchup']['stale']); self.assertTrue(current['catchup']['git_changed'])
        self.assertIn('Use provider-neutral routing', packet); self.assertIn('new.py', packet)
        self.assertEqual(current['catchup']['intervening_transitions'][-1]['provider'], 'codex')
        self.assertIn('not proof of completed work', packet)
        capture = self.root / 'fake-launch.json'; fake = self.root / 'claude'
        fake.write_text('#!' + sys.executable + '\nimport os,sys,json\nfrom pathlib import Path\nPath(' + repr(str(capture)) + ').write_text(json.dumps({"cwd":os.getcwd(),"argv":sys.argv[1:]}))\n')
        fake.chmod(0o700)
        original = self.repo / 'original-session.jsonl'; original.write_text('ORIGINAL\n')
        model = {'id': 'claude', 'local': False, 'executable': str(fake)}
        self.assertEqual(s.tracked_launch(self.state, model, str(self.repo), packet, str(self.vault), ''), 0)
        launch = json.loads(capture.read_text()); self.assertEqual(launch['cwd'], str(self.repo))
        self.assertIn('Codex reports UI implemented', launch['argv'][1])
        self.assertEqual(original.read_text(), 'ORIGINAL\n'); self.assertTrue((self.repo / 'new.py').exists())

    def test_codex_claude_codex(self):
        self.record('codex'); self.advance(); self.record('claude', 'provider_exited', 0)
        summary, packet = self.view('codex')
        self.assertTrue(summary['catchup']['stale']); self.assertIn('provider-neutral routing', packet)

    def test_local_model_participation(self):
        self.record('ollama:fixture'); self.advance(); self.record('claude')
        summary, _ = self.view('ollama:fixture')
        self.assertTrue(summary['catchup']['stale'])
        self.assertEqual(c.Index(self.state).read()['events'][0]['model'], 'fixture')

    def test_first_use_and_missing_transcripts_disclosed(self):
        summary, _ = self.view('claude'); self.assertIsNone(summary['catchup']['baseline'])
        self.record(); self.advance(); summary, _ = self.view()
        self.assertIn('Intervening unsaved session decisions unavailable', ' '.join(summary['catchup']['gaps']))

    def test_dirty_file_changes_when_porcelain_same(self):
        file = self.repo / 'task.py'; file.write_text('one\n'); self.record()
        file.write_text('newer-content\n')
        summary, _ = self.view()
        self.assertIn(str(file), summary['catchup']['changed_dirty_file_metadata'])

    def test_conflicting_checkpoint_and_session_claims_preserved(self):
        self.record(); self.advance()
        source = str(self.repo / 'fixture-session.jsonl')
        evidence = {'source_key': source, 'source': 'codex', 'id': 'fixture', 'snapshot_sha256': 'a'*64,
                    'document': {'text': 'Unverified session claim: UI remains unfinished', 'sha256': 'a'*64, 'modified_at': '2026-10-09', 'kind': 'session'}}
        summary, packet = s.assemble(self.state, str(self.repo), str(self.vault), session=evidence, target='claude')
        self.assertIn('UI remains unfinished', packet); self.assertIn('UI completed', packet)
        self.assertTrue(summary['catchup']['checkpoint_changed']); self.assertIn('semantic conflicts require review', packet)

    def test_seed_does_not_advance_old_source_baseline(self):
        self.record('claude', 'selected_source_checkpoint', seed=True)
        before = copy.deepcopy(c.Index(self.state).read()['events'][0])
        self.advance(); self.record('claude', 'selected_source_checkpoint', seed=True)
        self.assertEqual(c.Index(self.state).read()['events'], [before])
        self.assertTrue(self.view()[0]['catchup']['stale'])

    def test_never_restores_stale_handoff(self):
        self.record(); self.status.write_text(self.status.read_text().replace('FIXTURE_NEXT', 'LATEST_CANONICAL_ACTION'))
        _, packet = self.view()
        self.assertIn('LATEST_CANONICAL_ACTION', packet); self.assertNotIn('Continue FIXTURE_NEXT', packet)

    def test_index_never_stores_bodies_or_prompts(self):
        self.record(); data = (self.root / 'state/transitions.json').read_text()
        self.assertNotIn('FIXTURE_NEXT', data); self.assertNotIn('Truth over claims', data)
        self.assertEqual((self.root / 'state/transitions.json').stat().st_mode & 0o777, 0o600)

    def test_protected_exclusions(self):
        (self.repo / '.env').write_text('password=TOP_SECRET\n'); self.record()
        _, packet = self.view(); index = (self.root / 'state/transitions.json').read_text()
        self.assertNotIn('TOP_SECRET', packet + index); self.assertNotIn('/.env', index)
        self.assertIsNone(c.safe_reference(str(self.repo / 'password=TOP_SECRET.md')))

    def test_claim_secret_filtering(self):
        self.status.write_text(self.status.read_text() + '\n## Decisions\npassword=TOP_SECRET\n')
        _, packet = self.view(); self.record(); self.assertNotIn('TOP_SECRET', packet)
        self.assertNotIn('TOP_SECRET', (self.root / 'state/transitions.json').read_text())

    def test_context_and_index_bounded(self):
        self.record()
        for n in range(30):
            self.status.write_text(self.status.read_text() + '\n## Decisions\n' + ('Documented change ' + str(n) + ' ') * 100)
            self.record('codex')
        _, packet = self.view()
        self.assertLessEqual(len(packet.encode()), s.MAX_PACKET)
        self.assertLessEqual((self.root / 'state/transitions.json').stat().st_size, c.LIMIT)
        self.assertLess(len(c.Index(self.state).read()['events']), 31)

    def test_index_lock_contention_does_not_block(self):
        self.view(); lock = self.root / 'state/transitions.lock'
        fd = os.open(lock, os.O_RDWR | os.O_CREAT, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            warning = c.Index(self.state).record(self.state.observation, 'claude', 'explicit_checkpoint')
            self.assertIn('switching still works', warning)
        finally: os.close(fd)

    def test_corrupt_index_degrades_without_rewrite(self):
        path = self.root / 'state/transitions.json'; path.write_text('{"version":1,"events":[{}]}'); path.chmod(0o600)
        summary, packet = self.view(); self.assertIsNone(summary['catchup']['baseline'])
        self.assertIn('index unavailable', packet)
        self.assertIsNotNone(c.Index(self.state).record(self.state.observation, 'claude', 'explicit_checkpoint'))
        self.assertEqual(json.loads(path.read_text())['events'], [{}])

    def test_index_symlink_refused(self):
        target = self.root / 'outside.json'; target.write_text('UNCHANGED')
        (self.root / 'state/transitions.json').symlink_to(target)
        self.view(); self.assertIsNotNone(c.Index(self.state).record(self.state.observation, 'claude', 'explicit_checkpoint'))
        self.assertEqual(target.read_text(), 'UNCHANGED')

    def test_launch_failure_not_participation_success(self):
        _, packet = self.view()
        with self.assertRaises(OSError): s.tracked_launch(self.state, {'id':'codex', 'local':False, 'executable':str(self.root/'missing')}, str(self.repo), packet, str(self.vault), '')
        self.assertEqual(c.Index(self.state).read()['events'][-1]['phase'], 'launch_failed')
        self.assertIsNone(self.view('codex')[0]['catchup']['baseline'])

    def test_nonzero_provider_exit_unverified(self):
        _, packet = self.view(); fake = self.root / 'codex'; fake.write_text('#!/bin/sh\nexit 7\n'); fake.chmod(0o700)
        self.assertEqual(s.tracked_launch(self.state, {'id':'codex','local':False,'executable':str(fake)}, str(self.repo), packet, str(self.vault), ''), 7)
        baseline = self.view('codex')[0]['catchup']['baseline']
        self.assertEqual(baseline['exit_code'], 7); self.assertIn('success unknown', baseline['verification'])

    def test_permission_revocation_refuses_source_reads(self):
        self.record(); self.state.settings['grants'].pop(str(self.vault)); self.state.save()
        with patch('sys.stdin.isatty', return_value=False), self.assertRaises(s.host.Denied): self.view()

    def test_cli_checkpoint_and_catchup_without_provider(self):
        command = ['checkpoint', '--with', 'claude', '--vault', str(self.vault), '--state-dir', str(self.root/'state')]
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch('os.getcwd', return_value=str(self.repo)), patch.object(s, 'providers', return_value=[]):
            self.assertEqual(s.main(command), 0)
            self.advance(); command[0] = 'catchup'; output.seek(0); output.truncate()
            self.assertEqual(s.main(command), 0)
        self.assertIn('"stale": true', output.getvalue()); self.assertIn('provider-neutral routing', output.getvalue())

    def test_catchup_briefing_byte_limit(self):
        result = {'target':'claude', 'stale':True, 'baseline':None, 'gaps':[], 'changed_sources':['/source/' + 'x'*900 for _ in range(16)], 'new_or_changed_documented_claims':[{'text':'claim '*100} for _ in range(8)]}
        brief = c.bounded_briefing(result)
        self.assertLessEqual(len(json.dumps(brief).encode()), 6000)
        self.assertTrue(brief['stale']); self.assertIn('trimmed', ' '.join(brief['gaps']))

    def test_untracked_directory_file_changes_detected(self):
        folder = self.repo / 'unfinished'; folder.mkdir()
        file = folder / 'work.py'; file.write_text('Friday\n'); self.record()
        file.write_text('Newer Saturday work\n')
        summary, _ = self.view()
        self.assertIn(str(file), summary['catchup']['changed_dirty_file_metadata'])
        self.assertTrue(summary['catchup']['stale'])

    def test_explicit_task_secret_omitted(self):
        _, packet = s.assemble(self.state, str(self.repo), str(self.vault), task='password=DO_NOT_SEND_THIS', target='claude')
        self.assertNotIn('DO_NOT_SEND_THIS', packet); self.assertIn('Sensitive request text withheld', packet)

    def test_latest_accessible_handoff_reference(self):
        self.status.write_text(self.status.read_text().replace('## Handoff', '## Historical transfer'))
        older = self.project / 'a-handoff.md'; newer = self.project / 'z-handoff.md'
        older.write_text('Older documented transfer'); newer.write_text('Newer documented transfer')
        os.utime(older, (100, 100)); os.utime(newer, (200, 200))
        self.view(); self.assertEqual(self.state.observation['handoff'], str(newer))

    def test_continuity_gaps_preserved(self):
        self.status.write_text(self.status.read_text().replace('## Handoff', '## Historical transfer'))
        self.record(); event = c.Index(self.state).read()['events'][0]
        self.assertIn('No canonical Handoff', ' '.join(event['observation']['continuity_gaps']))

    def test_changed_root_identity_is_a_new_project(self):
        self.record(); self.repo.rename(self.root / 'old-code'); self.repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        self.seed(self.repo, 'repository')
        self.assertIsNone(self.view()[0]['catchup']['baseline'])



if __name__ == '__main__': unittest.main()
