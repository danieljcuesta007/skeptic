import hashlib
import subprocess
import unittest
from unittest.mock import Mock
import widget_switch as w


class WidgetSwitchTests(unittest.TestCase):
    def confirm(self, result=None, error=None):
        run = Mock(side_effect=error, return_value=result or subprocess.CompletedProcess([], 0, 'Switch\n', ''))
        evidence = {'id': 'selected-uuid', 'title': 'Vitals restart', 'document': {'text': 'Latest recorded human request (completion unverified):\nwhy does cadence ask twice?\n' + 'x' * 400 + '\n[message m1; user]\nrest'}}
        approved = w.confirm({'cwd': '/project/" & do shell script "bad'}, evidence, 'Codex', 'exact packet', run=run)
        return approved, run

    def test_switch_approves_the_displayed_packet_and_writer_check(self):
        approved, run = self.confirm()
        self.assertTrue(approved)
        argv = run.call_args.args[0]
        self.assertEqual(argv[:3], ['/usr/bin/osascript', '-e', w.SCRIPT])
        self.assertIn(hashlib.sha256(b'exact packet').hexdigest(), argv[3])
        self.assertIn('selected-uuid', argv[3])
        self.assertIn('automatic work', argv[3])
        self.assertIn('Conversation: Vitals restart (selected-uuid)', argv[3])
        self.assertIn('Last request: why does cadence ask twice?', argv[3])
        self.assertNotIn('[message', argv[3]); self.assertLess(len(argv[3]), 1200)
        self.assertNotIn('/project/', argv[2])

    def test_cancel_errors_and_unexpected_output_never_approve(self):
        for code, output in ((1, 'Switch'), (0, 'Cancel'), (0, ''), (0, 'Switch extra')):
            with self.subTest(code=code, output=output):
                self.assertFalse(self.confirm(subprocess.CompletedProcess([], code, output, ''))[0])
        for error in (OSError('unavailable'), subprocess.TimeoutExpired('osascript', 300)):
            self.assertFalse(self.confirm(error=error)[0])


class ExistingWindowTests(unittest.TestCase):
    def test_show_only_the_unique_lock_holders_terminal(self):
        run = Mock(side_effect=[subprocess.CompletedProcess([], 0, '123\n', ''), subprocess.CompletedProcess([], 0, 'p123\nn/dev/ttys007\n', ''), subprocess.CompletedProcess([], 0, '', '')])
        self.assertTrue(w.show_existing('/state/lock', run=run))
        self.assertEqual(run.call_args.args[0][-1], '/dev/ttys007')
        self.assertEqual(run.call_count, 3)

    def test_ambiguous_holder_does_not_guess_window(self):
        run = Mock(return_value=subprocess.CompletedProcess([], 0, '123\n456\n', ''))
        self.assertFalse(w.show_existing('/state/lock', run=run))
        self.assertEqual(run.call_count, 1)
