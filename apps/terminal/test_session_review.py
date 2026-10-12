import argparse
import contextlib
import io
import json
import os
from pathlib import Path
import pty
import select
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

import sessions as h
import session_review as r
import switcher as s
import test_sessions as fixture


def rows(cwd, sid=fixture.ID, count=3):
    result = [{'type': 'custom-title', 'customTitle': 'Review fixture', 'sessionId': sid}]
    parent = None
    for n in range(count):
        for role, text in [('user', 'Fix earlier export.' if n == 0 else 'Maybe later build themes.'),
                           ('assistant', 'The export is not done.' if n == 0 else 'Deferred.')]:
            uid = role + str(n)
            result.append({'type': role, 'uuid': uid, 'parentUuid': parent, 'sessionId': sid,
                           'cwd': cwd, 'timestamp': '2026-10-10T12:00:00Z', 'message': {'content': text}})
            parent = uid
    return result


class InventoryTests(unittest.TestCase):
    def conversation(self, messages, **flags):
        source = []
        parent = None
        for number, (role, text) in enumerate(messages):
            uid = 'message-' + str(number)
            source.append({'type': role, 'uuid': uid, 'parentUuid': parent, 'sessionId': fixture.ID,
                           'message': {'content': text}})
            parent = uid
        extracted = h.extract_claude([(0, n, row) for n, row in enumerate(source)], fixture.ID, inventory=True)
        return r.inventory(dict(extracted, **flags))

    def report(self, source):
        extracted = h.extract_claude([(0, n, row) for n, row in enumerate(source)], fixture.ID, inventory=True)
        return r.inventory(extracted)

    def test_earlier_requests_survive_recent_tail(self):
        source = rows('/synthetic', count=50)
        regular = h.extract_claude([(0, n, row) for n, row in enumerate(source)], fixture.ID)
        report = self.report(source)
        self.assertEqual(len(report['tasks']), 50)
        self.assertEqual(report['tasks'][0]['status'], 'unfinished')
        self.assertLess(len(regular['records']), 60)

    def test_completion_never_verified_by_assistant(self):
        source = rows('/synthetic', count=1)
        source[-1]['message']['content'] = 'Done, fixed and verified.'
        task = self.report(source)['tasks'][0]
        self.assertEqual(task['status'], 'completion claimed but unverified')
        self.assertIsNone(task['verification'])

    def test_later_unrelated_completion_does_not_close_earlier_task(self):
        source = rows('/synthetic', count=2)
        source[-1]['message']['content'] = 'Done.'
        report = self.report(source)
        self.assertEqual(report['tasks'][0]['status'], 'unfinished')
        self.assertEqual(report['tasks'][1]['status'], 'future idea')

    def test_supersession_and_negated_authorization_need_review(self):
        source = rows('/synthetic', count=1)
        source += [{'type': 'user', 'uuid': 'replace', 'parentUuid': source[-1]['uuid'],
                    'sessionId': fixture.ID, 'message': {'content': 'Instead, do not implement; investigate only.'}}]
        report = self.report(source)
        self.assertTrue(report['tasks'][0]['relations'])
        self.assertEqual([t['status'] for t in report['tasks']], ['unknown', 'unknown'])

    def test_blocked_future_unknown_and_cancel(self):
        source = rows('/synthetic', count=2)
        source[2]['message']['content'] = 'Blocked, waiting for access.'
        report = self.report(source)
        self.assertEqual([t['status'] for t in report['tasks']], ['blocked', 'future idea'])
        source += [{'type': 'user', 'uuid': 'cancel', 'parentUuid': source[-1]['uuid'],
                    'sessionId': fixture.ID, 'message': {'content': 'Cancel that previous task.'}}]
        report = self.report(source)
        self.assertEqual(report['tasks'][1]['status'], 'unknown')
        self.assertTrue(report['tasks'][1]['relations'])

    def test_compound_requests_preserve_constraints(self):
        source = rows('/synthetic', count=1)
        source[1]['message']['content'] = 'Keep everything local.\n1. Fix export.\n2. Add a test.'
        report = self.report(source)
        self.assertEqual(len(report['tasks']), 2)
        self.assertIn('Keep everything local', report['tasks'][1]['context'])

    def test_pasted_widget_component_spec_is_one_enclosing_request(self):
        spec = ('Please build the floating widget from this specification.\n'
                '## Component Specification\n- Tailwind CSS\n- TypeScript\n'
                '- Questions to Ask\n- Install dependencies\n- Add animation variants\n' +
                ''.join('- Component detail %d\n' % n for n in range(25)))
        report = self.conversation([('user', spec), ('assistant', 'The widget is not done.')])
        self.assertEqual(len(report['tasks']), 1)
        task = report['tasks'][0]
        self.assertEqual(task['request'], 'Please build the floating widget from this specification.')
        self.assertEqual(task['status'], 'unfinished')
        for fragment in ('Tailwind CSS', 'TypeScript', 'Questions to Ask', 'Install dependencies'):
            self.assertIn(fragment, task['context'])

    def test_unmarked_imperative_spec_steps_do_not_split_enclosing_build(self):
        request = 'Build the floating widget using these details:\n1. Install dependencies\n2. Add state\n3. Create animations'
        report = self.conversation([('user', request)])
        self.assertEqual(len(report['tasks']), 1)
        self.assertEqual(report['tasks'][0]['request'], 'Build the floating widget using these details:')

    def test_fenced_quoted_indented_and_tool_material_are_not_requests(self):
        request = ('Review this component example.\n```typescript\n1. Fix export\n2. Install dependencies\n```\n'
                   '> Add a background scanner\n"Create a provider launcher"\n'
                   '    Build another project\n<tool_output>\nFix all credentials\n</tool_output>')
        report = self.conversation([('user', request)])
        self.assertEqual([task['request'] for task in report['tasks']], ['Review this component example.'])
        self.assertIn('Add a background scanner', report['tasks'][0]['context'])

    def test_standalone_spec_and_quote_without_outer_request_stay_uncertain(self):
        report = self.conversation([('user', '## Technical Specification\n- Tailwind CSS\n- TypeScript\n- Install dependencies')])
        self.assertEqual(report['tasks'], [])
        self.assertTrue(any('scope unknown' in gap for gap in report['gaps']))
        self.assertEqual(r.request_parts('> Build a daemon\n"Fix the server"\n```sh\nnpm install x\n```'), [])

    def test_followup_spec_is_context_and_correction_reopens_same_thread(self):
        report = self.conversation([('user', 'Build a floating widget.'), ('assistant', 'Done.'),
            ('user', 'Here is the component specification:\n- Tailwind CSS\n- Add animation\n- Install packages'),
            ('user', 'Make it smaller and keep it local.'), ('assistant', 'The change is not done.')])
        self.assertEqual(len(report['tasks']), 1)
        task = report['tasks'][0]
        self.assertEqual(task['status'], 'unfinished')
        self.assertIn('Make it smaller', task['context'])
        self.assertTrue(any('Tailwind CSS' in evidence.get('untrusted_text', '') for evidence in task['evidence']))

    def test_independent_requests_cancellation_and_replacement_are_preserved(self):
        report = self.conversation([('user', 'Build a widget.'), ('assistant', 'Done.'),
            ('user', 'Fix the export.'), ('assistant', 'Blocked, waiting for access.'),
            ('user', 'Cancel that previous task.'), ('user', 'Instead, write a local report.')])
        self.assertEqual(len(report['tasks']), 3)
        self.assertEqual(report['tasks'][0]['status'], 'completion claimed but unverified')
        self.assertTrue(report['tasks'][1]['relations'])
        self.assertEqual(report['tasks'][1]['status'], 'unknown')
        self.assertIn('write a local report', report['tasks'][2]['request'])

    def test_explicit_independent_directive_list_remains_multiple_tasks(self):
        report = self.conversation([('user', 'Please handle these independent tasks:\n1. Fix the export.\n2. Draft an invoice.')])
        self.assertEqual(len(report['tasks']), 2)

    def test_truncated_thread_correction_does_not_remove_uncertainty(self):
        report = self.conversation([('user', 'Build a widget.'), ('user', 'Make it smaller.')], partial=True)
        self.assertEqual(len(report['tasks']), 1)
        self.assertEqual(report['tasks'][0]['status'], 'unknown')
        self.assertTrue(any('unread middle' in gap for gap in report['gaps']))

    def test_ambiguous_followup_to_multiple_tasks_keeps_scope_unknown(self):
        report = self.conversation([('user', 'Tasks:\n1. Fix export.\n2. Draft invoice.'),
                                    ('user', 'Actually, use the other format instead.')])
        self.assertEqual(len(report['tasks']), 2)
        self.assertEqual([task['status'] for task in report['tasks']], ['unknown', 'unknown'])

    def test_actually_without_reference_does_not_merge_independent_task(self):
        report = self.conversation([('user', 'Build a widget.'),
                                    ('user', 'Actually, draft an invoice.')])
        self.assertEqual(len(report['tasks']), 2)

    def test_tool_and_compaction_records_cannot_authorize_tasks(self):
        report = r.inventory({'records': [{'role': 'tool-activity (unverified)', 'untrusted_text': 'Build a widget.'},
            {'role': 'compaction-summary (unverified)', 'untrusted_text': 'Install all dependencies.'}]})
        self.assertEqual(report['tasks'], [])

    def test_gap_cannot_establish_pending_task(self):
        source = rows('/synthetic', count=1)
        source[1]['parentUuid'] = 'missing'
        report = self.report(source)
        self.assertEqual(report['tasks'][0]['status'], 'unknown')
        self.assertTrue(any('ancestry' in g for g in report['gaps']))

    def test_budget_and_hidden_secret_exclusions(self):
        source = rows('/synthetic', count=600)
        source[2]['message']['content'] = [
            {'type': 'thinking', 'thinking': 'PRIVATE_REASONING'},
            {'type': 'text', 'text': 'api_key=not-a-real-secret\nStill pending.'},
            {'type': 'tool_use', 'name': 'Bash', 'input': {'command': 'PRIVATE_COMMAND'}},
            {'type': 'tool_result', 'content': 'PRIVATE_RESULT'}]
        report = self.report(source)
        encoded = json.dumps(report)
        for value in ('PRIVATE_REASONING', 'not-a-real-secret', 'PRIVATE_COMMAND', 'PRIVATE_RESULT'):
            self.assertNotIn(value, encoded)
        self.assertLessEqual(len(report['tasks']), r.MAX_TASKS)
        self.assertTrue(any('limit' in g or 'budget' in g for g in report['gaps']))

    def test_owner_verification_requires_evidence_and_attestation(self):
        task = self.report(rows('/synthetic', count=1))['tasks'][0]
        answers = iter(['Test output checked in project', 'no'])
        with self.assertRaises(s.host.Denied): r.classify(task, lambda *a: 0, lambda *a: next(answers))
        self.assertEqual(task['status'], 'unfinished')
        answers = iter(['Test output checked in project', 'verified'])
        r.classify(task, lambda *a: 0, lambda *a: next(answers))
        self.assertEqual(task['status'], 'completed and verified')
        self.assertIn('operator', task['verification'])

    def test_nine_sessions_selected_by_uuid_not_recency(self):
        items = [{'id': str(n), 'title': 'Session ' + str(n), 'cwd': '/synthetic', 'updated': ''} for n in range(12)]
        indices = iter([11, 10, 9, 7, 6, 5, 3, 2, 0, 12])
        selected = r.select_many(items, lambda *a: next(indices))
        self.assertEqual({i['id'] for i in selected}, {'11','10','9','7','6','5','3','2','0'})

    def test_untitled_metadata_identifies_rows_without_transcript_reads(self):
        first = {'title': 'Untitled session', 'updated': '2026-10-10T12:00:00Z',
                 'cwd': '/fixture/project-one', 'id': 'aaaaaaaa-bbbb-cccc-dddd-000000000001'}
        second = dict(first, id='aaaaaaaa-bbbb-cccc-dddd-000000000002')
        with patch.object(h, 'open_file', side_effect=AssertionError('No new reads')):
            a, b = r.review_label(first), r.review_label(second)
        self.assertNotEqual(a.picker_title, b.picker_title)
        for value in ('2026-10-10', 'project-one', '000001'): self.assertIn(value, a.picker_title)
        self.assertIn(('ID', first['id']), a.picker_details)

    def test_conversation_hint_uses_only_approved_filtered_user_records(self):
        with patch.object(h, 'open_file', side_effect=AssertionError('No title reads')):
            self.assertEqual(r.conversation_label({'records': [{'role': 'user', 'untrusted_text': 'Fix the export for project Atlas.'}]}), 'Fix the export for project Atlas.')
            self.assertIsNone(r.conversation_label({'records': [{'role': 'assistant', 'untrusted_text': 'Done.'}]}))
            self.assertIsNone(r.conversation_label({'records': [{'role': 'user', 'untrusted_text': 'api_key=private-value'}]}))


class WorkflowTests(unittest.TestCase):
    setUp = fixture.SessionTests.setUp
    tearDown = fixture.SessionTests.tearDown
    rows = fixture.SessionTests.rows
    write_session = fixture.SessionTests.write_session
    approved = fixture.SessionTests.approved
    discover = fixture.SessionTests.discover
    snapshot = fixture.SessionTests.snapshot

    def args(self):
        return argparse.Namespace(all_projects=False, session_id=None, title=None,
            conversation_only=True, repo=[], vault=str(self.vault), cwd=None)

    def test_no_transcript_read_if_discovery_declined(self):
        with patch('sys.stdin.isatty', return_value=True), patch.object(h, 'read_chunks', side_effect=AssertionError('Private read')):
            access = h.Access(self.state, ask=lambda *a: 'decline')
            with self.assertRaises(s.host.Denied): r.run(self.args(), self.state, self.adapter, access, self.origin)

    def test_extraction_declined_leaves_other_selected_sessions_reviewable(self):
        self.write_session(self.origin, rows(self.origin, fixture.OTHER, 1), fixture.OTHER)
        self.approved(lambda: self.adapter.discover(self.access, self.origin))
        choices = iter([0, 1, 2, 1])
        access = h.Access(self.state, ask=lambda *a: 'decline')
        output = io.StringIO()
        with patch('sys.stdin.isatty', return_value=True), contextlib.redirect_stdout(output), patch.object(s, 'launch', side_effect=AssertionError('launch')):
            self.assertEqual(r.run(self.args(), self.state, self.adapter, access, self.origin,
                                   picker=lambda *a: next(choices)), 0)
        self.assertIn('unknown', output.getvalue())

    def test_earlier_task_packet_uses_confirmed_scope_and_never_launches(self):
        self.write_session(self.origin, rows(self.origin, count=30))
        snapshot = self.approved(lambda: self.adapter.snapshot(self.access, self.discover()[0], inventory=True))
        report = r.inventory(snapshot); task = report['tasks'][0]
        before = self.file.read_bytes()
        output = io.StringIO()
        with patch.object(s, 'session_destination', return_value=str(self.repo)) as destination, patch.object(s, 'launch', side_effect=AssertionError('launch')), contextlib.redirect_stdout(output):
            r.prepare(self.args(), self.state, self.adapter, self.access, report, task, lambda *a: 'Finish earlier export; preserve other work.')
        self.assertTrue(destination.call_args.kwargs['confirm'])
        self.assertIn('SELECTED EARLIER TASK', output.getvalue())
        self.assertIn('Fix earlier export', output.getvalue())
        self.assertIn('PROPOSED CODEX HANDOFF', output.getvalue())
        self.assertEqual(before, self.file.read_bytes())

    def test_appends_and_revocation_refuse_stale_preparation(self):
        self.write_session(self.origin, rows(self.origin, count=1))
        snapshot = self.approved(lambda: self.adapter.snapshot(self.access, self.discover()[0], inventory=True))
        report = r.inventory(snapshot)
        with self.file.open('a') as stream: stream.write('\n')
        with self.assertRaisesRegex(s.host.Denied, 'appended'):
            r.prepare(self.args(), self.state, self.adapter, self.access, report, report['tasks'][0], input)
        self.access.revoke()
        with self.assertRaises(s.host.Denied):
            r.prepare(self.args(), self.state, self.adapter, self.access, report, report['tasks'][0], input)

    def test_project_inspection_reuses_approved_reads_without_completion_claim(self):
        snapshot = self.snapshot(); report = r.inventory(snapshot); task = report['tasks'][0]
        args = self.args(); args.conversation_only = False
        output = io.StringIO()
        with patch.object(s, 'session_destination', return_value=str(self.repo)) as destination, contextlib.redirect_stdout(output), patch.object(s, 'launch', side_effect=AssertionError('launch')):
            r.inspect_project(args, self.state, report, task)
        self.assertTrue(destination.call_args.kwargs['confirm'])
        self.assertIn('GOVERNING_SOURCE', output.getvalue())
        self.assertIn('CANONICAL_NEXT', output.getvalue())
        self.assertNotEqual(task['status'], 'completed and verified')

    def test_actual_cli_nine_session_review_and_earlier_task_preview_on_pty(self):
        source = rows(self.origin, count=2); source[0]['customTitle'] = 'Untitled session'
        self.write_session(self.origin, source)
        files = [self.file]
        for number in range(8):
            sid = 'aaaaaaaa-bbbb-cccc-dddd-' + str(number).zfill(12)
            source = rows(self.origin, sid, 2); source[0]['customTitle'] = 'Untitled session'
            files.append(self.write_session(self.origin, source, sid))
        before = [file.read_bytes() for file in files]
        master, slave = pty.openpty()
        process = subprocess.Popen([sys.executable, '-B', str(Path(s.__file__)), 'sessions', 'review',
            '--project', self.origin, '--session-root', str(self.storage), '--state-dir', str(self.root / 'pty-state'),
            '--conversation-only', '--vault', str(self.vault)], stdin=slave, stdout=slave, stderr=slave,
            cwd=str(self.repo), env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        os.close(slave)
        seen = bytearray()
        cursor = 0
        def expect(text, send=b''):
            nonlocal cursor
            deadline = time.monotonic() + 12
            while text.encode() not in seen[cursor:]:
                if time.monotonic() > deadline: self.fail('PTY timeout: ' + text + '\n' + bytes(seen).decode(errors='replace')[-4000:])
                if select.select([master], [], [], .1)[0]:
                    try: chunk = os.read(master, 65536)
                    except OSError: chunk = b''
                    if not chunk: self.fail('CLI exited before ' + text)
                    seen.extend(chunk)
            cursor = seen.index(text.encode(), cursor) + len(text.encode())
            if send: os.write(master, send)
        try:
            expect('Type approve:', b'approve\n')
            expect('Select sessions:', b'\r')
            for number in range(1, 9):
                expect('Review selected sessions (' + str(number) + ')', b'\x1b[B\r')
            expect('Review selected sessions (9)', b'\x1b[B\r')
            for number in range(9): expect('Type approve:', b'approve\n')
            expect('Inspect a task;', b'\r')
            expect('Selected task', b'\x1b[B\x1b[B\r')
            expect('Confirm project destination', b'\r')
            expect('Confirm the exact remaining task', b'Finish earlier export only.\n')
            expect('PROPOSED CODEX HANDOFF')
            # Each synthetic session has two requests; finish after all 18 tasks.
            expect('Inspect a task;', b'\x1b[B' * 18 + b'\r')
            expect('Review finished.')
            self.assertEqual(process.wait(timeout=5), 0)
            self.assertIn(b'SELECTED EARLIER TASK', seen)
            self.assertIn(b'Conversation hint from approved transcript', seen)
            self.assertIn(b'Fix earlier export.', seen)
            self.assertEqual(before, [file.read_bytes() for file in files])
        finally:
            if process.poll() is None: process.terminate(); process.wait(timeout=5)
            os.close(master)


if __name__ == '__main__': unittest.main()
