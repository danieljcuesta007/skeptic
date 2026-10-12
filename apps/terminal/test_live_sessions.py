import importlib.util, json, os, sqlite3, tempfile, unittest
from pathlib import Path
from unittest.mock import patch

def load(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
live = load('live_sessions')


class ClaudeFixture(unittest.TestCase):
    """A fake home with Claude's native session record and transcript."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name).resolve()
        (self.home / '.claude/sessions').mkdir(parents=True, mode=0o700)
        self.repo = self.home / 'code' / 'atlas'; (self.repo / '.git').mkdir(parents=True)
        self.sid = 'sess-1'; self.started = 1000.0
        self.write_meta(status='idle')
        self.write_transcript(cwd=str(self.repo))
        patcher = patch.object(live.Path, 'home', return_value=self.home); patcher.start(); self.addCleanup(patcher.stop)

    def write_meta(self, **extra):
        meta = {'pid': 42, 'sessionId': self.sid, 'cwd': str(self.home), 'startedAt': (self.started + 1.25) * 1000, 'name': 'atlas-work', **extra}
        path = self.home / '.claude/sessions/42.json'; path.write_text(json.dumps(meta)); path.chmod(0o600)

    def write_transcript(self, cwd, blocks=None, age=0):
        bucket = self.home / '.claude/projects' / ''.join(c if c.isalnum() else '-' for c in str(self.home))
        bucket.mkdir(parents=True, exist_ok=True)
        rows = [{'sessionId': self.sid, 'type': 'user', 'cwd': str(self.home), 'message': {'content': 'Ship Atlas'}},
                {'sessionId': self.sid, 'type': 'assistant', 'cwd': cwd, 'message': {'content': blocks or []}}]
        path = bucket / (self.sid + '.jsonl'); path.write_text(''.join(json.dumps(r) + '\n' for r in rows)); path.chmod(0o600)
        if age: t = os.stat(path).st_mtime - age; os.utime(path, (t, t))

    def collect(self, agents=None):
        agents = agents or [{'pid': 42, 'tty': 'ttys001', 'agent': 'Claude Code'}]
        return live.collect({'agents': agents}, self.home, births=lambda pid: self.started, titles=getattr(self, 'titles', {}))


class VerdictTests(ClaudeFixture):
    def test_idle_session_in_a_repository_is_ready_with_command(self):
        row = self.collect()[0]
        self.assertEqual(row['activity'], 'idle'); self.assertEqual(row['verdict'], 'ready')
        self.assertEqual(row['project'], 'atlas'); self.assertEqual(row['task'], 'Ship Atlas')
        self.assertEqual(row['continue_command'], ['skeptic', 'session', 'continue', '--project', str(self.home), '--id', self.sid, '--cwd', str(self.repo), '--with', 'codex'])

    def test_status_busy_means_wait(self):
        self.write_meta(status='busy')
        row = self.collect()[0]
        self.assertEqual(row['activity'], 'working'); self.assertEqual(row['verdict'], 'wait'); self.assertIsNone(row['continue_command'])

    def test_legacy_busy_flag_still_read(self):
        self.write_meta(busy=False)
        self.assertEqual(self.collect()[0]['activity'], 'idle')

    def test_home_without_repository_needs_project(self):
        # Even a home folder that is itself a Git repo (dotfiles) is not a project.
        (self.home / '.git').mkdir()
        self.write_transcript(cwd=str(self.home))
        row = self.collect()[0]
        self.assertEqual(row['verdict'], 'needs_project'); self.assertIsNone(row['continue_command'])

    def test_start_time_within_tolerance_but_pid_reuse_refused(self):
        self.started = 1000.0; self.assertEqual(self.collect()[0]['association'], 'native Claude session record (PID + start time)')
        self.started = 1060.0; self.assertEqual(self.collect()[0]['verdict'], 'unknown')

    def test_busy_peer_in_same_repository_blocks(self):
        row = self.collect()[0]
        peer = dict(row, id='peer', pid=43, activity='working')
        assessed = live.assess([dict(row), peer])
        self.assertNotEqual(assessed[0]['verdict'], 'ready')
        idle_peer = dict(row, id='peer', pid=43, activity='idle')
        self.assertEqual(live.assess([dict(row), idle_peer])[0]['verdict'], 'ready')

    def test_linked_idle_codex_can_be_ready_and_carries_note(self):
        row = {'id': 'c', 'agent': 'Codex', 'pid': 7, 'tty': 't', 'source': 'codex', 'association': 'owner-confirmed (not automatically verified)',
               'activity': 'idle', 'cwd': str(self.repo), 'source_path': '/x/rollout.jsonl', 'session_id': 'c1'}
        out = live.assess([row])[0]
        self.assertEqual(out['verdict'], 'ready'); self.assertIn('linked by you', out['note'])
        self.assertEqual(out['continue_command'][:5], ['skeptic', 'session', 'continue', '--source', 'codex'])
        self.assertEqual(out['continue_cwd'], str(self.repo))

    def test_idle_with_automatic_or_queued_work_waits(self):
        base = {'id': 'h', 'agent': 'Hermes', 'pid': 9, 'tty': 't', 'source': 'hermes', 'association': 'native', 'activity': 'idle', 'cwd': '/nowhere'}
        for extra in ({'automation_pending': True, 'automation_evidence': 'Active goal'}, {'queued_turns': 2}):
            out = live.assess([dict(base, **extra)])[0]
            self.assertEqual(out['verdict'], 'wait'); self.assertEqual(out['readiness'], 'blocked')

    def test_frozen_busy_session_is_switchable_with_warning(self):
        self.write_meta(status='busy'); self.write_transcript(cwd=str(self.repo), age=live.STALL_SECONDS + 60)
        row = self.collect()[0]
        self.assertEqual(row['verdict'], 'ready'); self.assertIn('looks frozen', row['headline']); self.assertEqual(row['writer'], 'frozen')
        self.write_transcript(cwd=str(self.repo))  # fresh output: really working
        self.assertEqual(self.collect()[0]['verdict'], 'wait')

    def test_usage_limit_message_counts_as_frozen(self):
        self.write_meta(status='busy')
        self.write_transcript(cwd=str(self.repo), blocks=[{'type': 'text', 'text': "You've hit your limit · resets 3pm"}])
        row = self.collect()[0]
        self.assertEqual(row['verdict'], 'ready'); self.assertIn('usage limit', row['headline'])

    def test_resumed_after_limit_is_working_again(self):
        bucket = self.home / '.claude/projects' / ''.join(c if c.isalnum() else '-' for c in str(self.home))
        self.write_meta(status='busy')
        self.write_transcript(cwd=str(self.repo), blocks=[{'type': 'text', 'text': "You've hit your limit"}])
        path = bucket / (self.sid + '.jsonl')
        with open(path, 'a') as f:  # the user resumed; Claude is calling tools again
            f.write(json.dumps({'sessionId': self.sid, 'type': 'user', 'cwd': str(self.repo), 'message': {'content': 'continue'}}) + '\n')
            f.write(json.dumps({'sessionId': self.sid, 'type': 'assistant', 'cwd': str(self.repo), 'message': {'content': [{'type': 'tool_use', 'input': {'command': 'ls'}}]}}) + '\n')
        row = self.collect()[0]
        self.assertEqual(row['verdict'], 'wait'); self.assertNotIn('frozen', row)

    def test_home_session_project_from_touched_files(self):
        self.write_transcript(cwd=str(self.home), blocks=[{'type': 'tool_use', 'name': 'Edit', 'input': {'file_path': str(self.repo / 'src' / 'app.py')}}])
        (self.repo / 'src').mkdir()
        row = self.collect()[0]
        self.assertEqual(row['project'], 'atlas'); self.assertEqual(row['verdict'], 'ready')

    def test_ready_rows_offer_every_other_engine(self):
        self.assertEqual(self.collect()[0]['destinations'], ['codex', 'hermes'])

    def test_session_named_by_its_terminal_tab(self):
        self.titles = {'ttys001': 'Atlas importer'}
        self.assertEqual(self.collect()[0]['label'], 'Atlas importer')
        self.titles = {}
        self.assertEqual(self.collect()[0]['label'], 'atlas-work')  # Claude's own session name

    def test_tab_titles_parsed_from_terminal(self):
        out = '/dev/ttys003\x1f\u25d0 Widget spacing fixes\n/dev/ttys005\x1f\u2733 Claude Code\nbad line\n/dev/../x\x1fnope\n'
        run = lambda *a, **k: type('R', (), {'stdout': out})()
        with patch.object(live.sys, 'platform', 'darwin'), patch.dict(os.environ, {'SKEPTIC_TAB_TITLES': '1'}):
            self.assertEqual(live.terminal_titles(run=run), {'ttys003': 'Widget spacing fixes', 'ttys005': ''})
        def boom(*a, **k): raise live.subprocess.TimeoutExpired('osascript', 2)
        with patch.object(live.sys, 'platform', 'darwin'), patch.dict(os.environ, {'SKEPTIC_TAB_TITLES': '1'}):
            self.assertEqual(live.terminal_titles(run=boom), {})
        with patch.dict(os.environ, {'SKEPTIC_TAB_TITLES': '0'}):
            self.assertEqual(live.terminal_titles(run=run), {})

    def test_last_active_from_transcript_or_session_record(self):
        row = self.collect()[0]
        path = next((self.home / '.claude/projects').rglob('*.jsonl'))
        self.assertGreaterEqual(row['last_active'], os.stat(path).st_mtime - 1)
        self.write_meta(status='idle', updatedAt=(os.stat(path).st_mtime + 600) * 1000)  # Claude's own record is newer
        self.assertAlmostEqual(self.collect()[0]['last_active'], os.stat(path).st_mtime + 600, delta=1)

    def test_summary_prefers_ready(self):
        rows = [{'verdict': 'wait', 'source': 'claude'}, {'verdict': 'ready', 'source': 'codex'}]
        self.assertEqual(live.summary(rows)['verdict'], 'ready'); self.assertIsNone(live.summary([]))

    def test_repo_root_never_home_and_never_runs_git(self):
        self.assertIsNone(live.repo_root(str(self.home)))
        self.assertEqual(live.repo_root(str(self.repo / 'src')), str(self.repo))
        with patch.object(live.subprocess, 'run', side_effect=AssertionError('git executed')): live.repo_root(str(self.repo))


class HermesTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.home = Path(self.tmp.name).resolve()
        for n in ('.hermes/runtime', '.hermes/terminal-sessions'): (self.home / n).mkdir(parents=True, mode=0o700)
        reg = self.home / '.hermes/runtime/active_sessions.json'
        reg.write_text(json.dumps({'entries': [{'pid': 42, 'surface': 'cli', 'process_start_time': 1000., 'session_id': 's1', 'metadata': {'live_session_id': 's1'}}]})); reg.chmod(0o600)
        crumb = self.home / '.hermes/terminal-sessions/tty-dev-ttys009'; crumb.write_text(json.dumps({'session_id': 's1', 'cwd': '/project', 'ts': 1010.})); crumb.chmod(0o600)
        conn = sqlite3.connect(self.home / '.hermes/state.db')
        conn.executescript('CREATE TABLE state_meta (key TEXT,value TEXT); CREATE TABLE async_delegations (origin_session TEXT,origin_ui_session_id TEXT,parent_session_id TEXT,origin_session_id TEXT,state TEXT); CREATE TABLE sessions (id TEXT,title TEXT,cwd TEXT,model TEXT,ended_at REAL,last_activity_at REAL,last_activity_description TEXT,last_activity_provenance TEXT); CREATE TABLE messages (id INTEGER,session_id TEXT,role TEXT,content TEXT,active INTEGER,tool_calls TEXT,timestamp REAL,reasoning TEXT);')
        conn.execute('INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?)', ('s1', 'Build', '/project', 'model', None, 1090., '', 'unknown'))
        conn.execute('INSERT INTO messages VALUES (?,?,?,?,?,?,?,?)', (1, 's1', 'user', 'Fix spacing', 1, None, 1080., 'HIDDEN'))
        conn.execute('INSERT INTO messages VALUES (?,?,?,?,?,?,?,?)', (2, 's1', 'assistant', 'Done', 1, None, 1090., 'HIDDEN'))
        conn.commit(); conn.close(); (self.home / '.hermes/state.db').chmod(0o600)

    def test_idle_hermes_task_and_no_reasoning(self):
        row = live.collect({'agents': [{'pid': 42, 'tty': 'ttys009', 'agent': 'Hermes'}]}, self.home, clock=lambda: 1100., births=lambda pid: 1000., titles={})[0]
        self.assertEqual(row['activity'], 'idle'); self.assertEqual(row['task'], 'Fix spacing'); self.assertNotIn('HIDDEN', json.dumps(row))


if __name__ == '__main__': unittest.main()
