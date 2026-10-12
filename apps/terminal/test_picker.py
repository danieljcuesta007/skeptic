"""Picker regressions using synthetic labels and terminal input only."""
import io
import os
from pathlib import Path
import pty
import select
import signal
import struct
import subprocess
import sys
import termios
import time
import fcntl
import unittest
import unicodedata
from unittest.mock import patch

import switcher as s
import sessions as history


class Terminal(io.StringIO):
    def isatty(self): return True
    def fileno(self): return 99


class PickerTests(unittest.TestCase):
    def run_picker(self, keys, sizes=None, options=None, on_enter=None):
        data = bytearray(keys)
        output = Terminal()
        frames = []
        def read(fd, count):
            result = bytes(data[:count]); del data[:count]
            return result
        def flush(): frames.append(output.getvalue()); output.seek(0); output.truncate()
        output.flush = flush
        sizes = sizes or [(32, 8)]
        calls = iter(sizes)
        last = sizes[-1]
        def size(fd): return os.terminal_size(next(calls, last))
        with patch.object(s.termios, 'tcgetattr', return_value=['saved']), \
             patch.object(s.termios, 'tcsetattr') as restore, \
             patch.object(s.tty, 'setcbreak'), \
             patch.object(s.os, 'read', side_effect=read), \
             patch.object(s.os, 'get_terminal_size', side_effect=size), \
             patch.object(s.select, 'select', side_effect=lambda *args: ([99] if data or args[-1] == .1 else [], [], [])):
            try:
                result = s.choose('Sessions', options or ['session-%02d' % n for n in range(20)], Terminal(), output, on_enter=on_enter)
            except KeyboardInterrupt:
                result = 'cancelled'
            restore.assert_called_once_with(99, s.termios.TCSADRAIN, ['saved'])
        return result, frames

    def selected(self, frame):
        return [line.strip()[2:] for line in frame.splitlines() if line.startswith('› ')]

    def test_long_list_navigation_and_scroll(self):
        result, frames = self.run_picker(b'\x1b[B' * 9 + b'\x1b[A' * 3 + b'\r')
        self.assertEqual(result, 6)
        self.assertEqual([self.selected(f) for f in frames[:-1]],
                         [['session-%02d' % n] for n in [*range(10), 8, 7, 6]])
        for frame in frames[:-1]:
            self.assertIn('\x1b[H', frame)
            self.assertLessEqual(len(frame.splitlines()), 7)
        self.assertIn('session-09', frames[9])
        self.assertNotIn('session-00', frames[9])
        self.assertIn('\x1b[?1049l', frames[-1])

    def test_long_unicode_labels_do_not_wrap(self):
        _, frames = self.run_picker(b'\r', options=['界' * 80, 'x' * 120])
        for line in frames[0].splitlines():
            # Remove only the picker control sequences.
            import re
            line = re.sub(r'\x1b\[[?0-9;]*[A-Za-z]', '', line)
            width = sum(2 if unicodedata.east_asian_width(c) in ('W', 'F') else 1 for c in line)
            self.assertLessEqual(width, 31)

    def test_resize_and_unknown_input_preserve_selection(self):
        result, frames = self.run_picker(b'j' * 9 + b'x\x1b[A\r', sizes=[(32, 8)] * 10 + [(20, 5)] * 3)
        self.assertEqual(result, 8)
        self.assertEqual(self.selected(frames[9]), ['session-09'])
        self.assertEqual(self.selected(frames[10]), ['session-09'])
        self.assertEqual(self.selected(frames[11]), ['session-08'])
        self.assertLessEqual(len(frames[10].splitlines()), 4)

    def test_wraparound_and_application_cursor_keys(self):
        result, frames = self.run_picker(b'\x1bOA\x1bOB\r')
        self.assertEqual(result, 0)
        self.assertEqual(self.selected(frames[1]), ['session-19'])
        self.assertEqual(self.selected(frames[2]), ['session-00'])

    def test_zero_terminal_size_uses_fallback_and_combining_labels(self):
        result, frames = self.run_picker(b'\x1b[B\r', sizes=[(0, 0)], options=['e\u0301' * 100, 'second'])
        self.assertEqual(result, 1)
        self.assertIn('Esc/q cancels.', frames[0])
        self.assertEqual(s.picker_line('e\u0301' * 100, 5), 'e\u0301' * 4)

    def test_cancel_restores_terminal(self):
        for key in (b'q', b'\x1b', b'\x04', b''):
            with self.subTest(key=key):
                result, frames = self.run_picker(key)
                self.assertEqual(result, 'cancelled')
                self.assertIn('\x1b[?25h', frames[-1])
                self.assertIn('\x1b[?1049l', frames[-1])

    def test_multi_toggle_keeps_cursor_and_scrolled_viewport(self):
        options = ['[ ] session-%02d' % n for n in range(60)]
        selected, visits = set(), []
        def toggle(index):
            visits.append(index)
            if len(visits) == 4: return True
            if index in selected: selected.remove(index)
            else: selected.add(index)
            options[index] = ('[x] ' if index in selected else '[ ] ') + 'session-%02d' % index
            return False
        result, frames = self.run_picker(b'j' * 30 + b'\rj\rk\rj\r', options=options, on_enter=toggle)
        self.assertEqual(visits, [30, 31, 30, 31])
        self.assertEqual(result, 31)
        self.assertEqual(selected, {31})
        self.assertEqual(self.selected(frames[30]), ['[ ] session-30'])
        self.assertEqual(self.selected(frames[31]), ['[x] session-30'])
        def viewport(frame):
            import re
            return re.findall(r'session-\d+', frame)
        self.assertEqual(viewport(frames[30]), viewport(frames[31]))
        self.assertNotIn('session-00', frames[31])
        # No leave/re-enter of alternate screen or terminal mode at toggles.
        self.assertEqual(''.join(frames).count('\x1b[?1049h'), 1)
        self.assertEqual(''.join(frames).count('\x1b[?1049l'), 1)

    def test_toggle_resize_and_cancel_preserve_cursor_restore_terminal(self):
        options = ['session-%02d' % n for n in range(40)]
        visits = []
        def toggle(index): visits.append(index); return False
        result, frames = self.run_picker(b'j' * 20 + b'\rx\rjq',
            sizes=[(32, 8)] * 21 + [(24, 6)] * 4, options=options, on_enter=toggle)
        self.assertEqual(result, 'cancelled')
        self.assertEqual(visits, [20, 20])
        self.assertEqual(self.selected(frames[21]), ['session-20'])
        self.assertNotIn('session-00', frames[21])

    def test_selected_session_title_and_full_details_use_spare_space(self):
        session = {'title': 'Discuss the detailed next steps for the current project',
                   'updated': '2026-10-10T12:34:56', 'cwd': '/fixture/projects/' + 'long-directory-' * 4,
                   'id': '01234567-89ab-cdef-0123-456789abcdef'}
        label = history.SessionLabel(session)
        result, frames = self.run_picker(b'\r', sizes=[(40, 24)], options=[label, 'other session'])
        self.assertEqual(result, 0)
        self.assertIn('› Discuss the detailed next steps', frames[0])
        # Every field is readable across wrapped rows, with no spacer pushing
        # details to the bottom of the terminal.
        readable = ''.join(frames[0].split())
        for name, value in [('Selected', session['title']), *label.picker_details]:
            self.assertIn(''.join((name + ': ' + str(value)).split()), readable)
        self.assertNotIn('\r\n\r\n', frames[0])
        for line in frames[0].splitlines():
            if line.startswith(('› ', '  ')): self.assertNotIn(session['updated'], line)

    def test_session_labels_preserve_picker_callback_and_discovery_scope(self):
        sessions = [{'title': 'Title | with separator', 'updated': 'date', 'cwd': '/fixture', 'id': str(n)}
                    for n in range(2)]
        from unittest.mock import Mock
        adapter = Mock()
        adapter.discover.return_value = sessions
        access = object()
        def pick(title, labels):
            self.assertEqual(str(labels[1]), 'Title | with separator | date | /fixture | 1')
            self.assertIsInstance(labels[1], str)
            self.assertEqual(labels[1].picker_title, sessions[1]['title'])
            self.assertEqual(labels[1].picker_details[-1], ('ID', '1'))
            return 1
        result = history.selected_session(adapter, access, '/fixture', pick, 'Title', None, False)
        self.assertIs(result, sessions[1])
        adapter.discover.assert_called_once_with(access, '/fixture', False, None, 'Title')

    def test_real_pty_long_list_and_fragmented_arrows(self):
        master, slave = pty.openpty()
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 8, 32, 0, 0))
        code = ('import switcher, termios; before = termios.tcgetattr(0); '
                'print("SELECTED=" + str(switcher.choose("Sessions", '
                '["session-%02d" % n for n in range(20)]))); '
                'mask = termios.ECHO | termios.ICANON | termios.ISIG; '
                'print("RESTORED=" + str(before[3] & mask == termios.tcgetattr(0)[3] & mask))')
        proc = subprocess.Popen([sys.executable, '-B', '-c', code], cwd=Path(__file__).parent,
                                stdin=slave, stdout=slave, stderr=slave)
        def frame():
            output = b''
            deadline = time.monotonic() + 3
            while time.monotonic() < deadline:
                if select.select([master], [], [], .1)[0]:
                    output += os.read(master, 8192)
                    if b'session-' in output: return output
            self.fail('Picker frame timed out: ' + repr(output))
        try:
            first = frame()
            self.assertIn(b'\x1b[H', first)
            self.assertNotIn(b'session-19', first)
            for index in range(1, 10):
                # Exercise reads of separate escape-sequence bytes on a real PTY.
                os.write(master, b'\x1b'); time.sleep(.01)
                os.write(master, b'['); time.sleep(.01)
                os.write(master, b'B')
                rendered = frame()
                self.assertIn(('› session-%02d' % index).encode(), rendered)
                self.assertLessEqual(rendered.count(b'\n'), 6)
            os.write(master, b'\x1b[A')
            self.assertIn('› session-08'.encode(), frame())
            os.write(master, b'\r')
            proc.wait(timeout=3)
            final = b''
            while select.select([master], [], [], .1)[0]: final += os.read(master, 8192)
            self.assertIn(b'SELECTED=8', final)
            self.assertIn(b'\x1b[?1049l', final)
            self.assertIn(b'RESTORED=True', final)
        finally:
            if proc.poll() is None: proc.kill(); proc.wait()
            os.close(master); os.close(slave)

    def test_real_pty_resize_without_input_and_while_navigating(self):
        master, slave = pty.openpty()
        def resize(columns, rows):
            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', rows, columns, 0, 0))
        resize(32, 8)
        code = ('import switcher, sessions, termios; before = termios.tcgetattr(0);\n'
                'try: print("SELECTED=" + str(switcher.choose("Sessions", '
                '[sessions.SessionLabel({"title": "session-%02d" % n, '
                '"updated": "2026-10-10", "cwd": "/fixture/" + "directory-" * 4, '
                '"id": "fixture-id-%02d" % n}) for n in range(20)])))\n'
                'except KeyboardInterrupt: print("CANCELLED")\n'
                'mask = termios.ECHO | termios.ICANON | termios.ISIG; '
                'print("RESTORED=" + str(before[3] & mask == termios.tcgetattr(0)[3] & mask))')
        proc = subprocess.Popen([sys.executable, '-B', '-c', code], cwd=Path(__file__).parent,
                                stdin=slave, stdout=slave, stderr=slave)
        def frame():
            output = b''
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                if select.select([master], [], [], .05)[0]:
                    output += os.read(master, 8192)
                    if b'session-' in output: return output
            self.fail('No redraw after terminal resize without a keypress: ' + repr(output))
        try:
            self.assertIn(b'\x1b[H', frame())
            for n in range(1, 10):
                os.write(master, b'\x1b[B')
                self.assertIn(('› session-%02d' % n).encode(), frame())
            resize(70, 18); os.kill(proc.pid, signal.SIGWINCH)
            larger = frame()
            self.assertIn('› session-09'.encode(), larger)
            self.assertIn(b'session-17', larger)
            self.assertIn(b'ID: fixture-id-09', larger)
            self.assertIn(b'Directory: /fixture/' + b'directory-' * 4, larger)
            resize(24, 6); os.kill(proc.pid, signal.SIGWINCH)
            smaller = frame()
            self.assertIn('› session-09'.encode(), smaller)
            self.assertLessEqual(smaller.count(b'\n'), 4)
            os.write(master, b'\x1b[A')
            self.assertIn('› session-08'.encode(), frame())
            resize(120, 30); os.kill(proc.pid, signal.SIGWINCH)
            os.write(master, b'\x1b[B')
            # A resize and input can produce separate frames; await the selection.
            larger = frame()
            if '› session-09'.encode() not in larger: larger += frame()
            self.assertIn('› session-09'.encode(), larger)
            self.assertIn(b'session-00', larger)
            self.assertIn(b'session-19', larger)
            self.assertIn(b'ID: fixture-id-09', larger)
            os.write(master, b'q'); proc.wait(timeout=3)
            final = b''
            while select.select([master], [], [], .05)[0]: final += os.read(master, 8192)
            self.assertIn(b'CANCELLED', final)
            self.assertIn(b'RESTORED=True', final)
            self.assertIn(b'\x1b[?1049l', final)
        finally:
            if proc.poll() is None: proc.kill(); proc.wait()
            os.close(master); os.close(slave)


if __name__ == '__main__': unittest.main()
