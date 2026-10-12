"""Read-only, live-process-scoped conversation observation. Never a history crawler.

Answers one question per open agent: if it stopped now, could another engine
pick up? Each row carries a `verdict` (ready / wait / needs_project / unknown),
a one-line `headline`, the `next_step`, and for ready rows the exact
`continue_command` (an argv for the skeptic CLI, which still asks for every
approval it needs). Owned by Skeptic; the Vitals widget only displays it.
"""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import subprocess
import time

LIMIT = 256 * 1024
ID = re.compile(r'[A-Za-z0-9_.:-]{1,128}\Z')


def clean(value, limit=240):
    if not isinstance(value, str): return ''
    lines = []
    for line in value[:10000].splitlines():
        if re.search(r'(?i)(bearer\s+|password\s*[:=]|api[_ -]?key\s*[:=]|secret\s*[:=]|token\s*[:=]|-----BEGIN .*PRIVATE KEY|sk-[A-Za-z0-9_-]{15,}|gh[pousr]_[A-Za-z0-9]{15,}|AKIA[A-Z0-9]{16}|eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+|[a-z]+://[^\s/:]+:[^\s@]+@)', line):
            lines.append('[sensitive line withheld]')
        else:
            lines.append(''.join(c if c >= ' ' and c != '\x7f' else ' ' for c in line))
    return ' '.join(lines)[:limit]


def safe_file(path):
    path = Path(path).absolute()
    if '..' in path.parts or any(p.is_symlink() for p in (path, *path.parents)): raise ValueError('Aliased source')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1 or info.st_mode & 0o022:
        os.close(fd); raise ValueError('Unsafe source')
    return fd, info


def read_json(path):
    fd, info = safe_file(path)
    try:
        if info.st_size > LIMIT: raise ValueError('Oversized metadata')
        return json.loads(os.read(fd, LIMIT + 1))
    finally: os.close(fd)


def db_open(path):
    fd, _ = safe_file(path); os.close(fd)
    conn = sqlite3.connect(Path(path).absolute().as_uri() + '?mode=ro', uri=True, timeout=.2)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA query_only=ON')
    conn.execute('PRAGMA busy_timeout=200')
    return conn


def birth(pid):
    raw = subprocess.check_output(['/bin/ps', '-p', str(pid), '-o', 'lstart='], text=True, timeout=1).strip()
    return datetime.datetime.strptime(raw, '%a %b %d %H:%M:%S %Y').timestamp()


def base(agent):
    return {'id':f"process-{agent['pid']}", 'agent':agent['agent'], 'pid':agent['pid'], 'tty':agent['tty'],
            'title':'Conversation not linked', 'task':'Select the conversation in Sessions to link it.',
            'project':'unknown', 'cwd':'', 'model':'unknown', 'activity':'unknown', 'activity_evidence':'No provider turn evidence',
            'association':'unlinked', 'writer':'unknown', 'readiness':'blocked', 'blocked_reasons':['Conversation identity not linked'],
            'source':'', 'session_id':'', 'captured_epoch':time.time()}


def same_birth(expected, actual):
    # ps reports whole seconds (truncated) and agents record their own start a
    # beat after spawn (Claude ~1.2 s), so allow 2.5 s; PID reuse is minutes off.
    return type(expected) in (float, int) and abs(expected - actual) <= 2.5


def hermes_automation(conn, sid):
    try:
        states = conn.execute("SELECT CASE WHEN json_valid(value) THEN json_extract(value,'$.status') ELSE 'unknown' END status FROM state_meta WHERE key IN (?,?)",('goal:'+sid,'loop:'+sid)).fetchall()
        delegated = conn.execute("SELECT COUNT(*) FROM async_delegations WHERE (origin_session=? OR origin_ui_session_id=? OR parent_session_id=? OR origin_session_id=?) AND state IN ('running','finalizing','unknown')",(sid,sid,sid,sid)).fetchone()[0]
        pending = delegated > 0 or any(r['status'] not in ('done','cleared','completed') for r in states)
        return {'automation_pending':pending,'automation_evidence':'Active/paused goal, loop or delegated work' if pending else 'No recorded goal, loop or live delegation for this session'}
    except sqlite3.Error:
        return {'automation_pending':True,'automation_evidence':'Automatic continuation metadata unavailable; review it in the source'}


def hermes(agent, home, started, now):
    row = base(agent)
    entries = read_json(home / '.hermes/runtime/active_sessions.json').get('entries', [])
    matches = [e for e in entries if isinstance(e, dict) and e.get('pid') == agent['pid'] and e.get('surface') == 'cli' and same_birth(e.get('process_start_time'), started)]
    if len(matches) != 1: return row
    lease = matches[0]; sid = lease.get('session_id')
    if not isinstance(sid, str) or not ID.fullmatch(sid): return row
    if (lease.get('metadata') or {}).get('live_session_id') != sid: return row
    # TTY breadcrumb tracks /new, /resume, and compression; lease alone may be an older session.
    crumb = read_json(home / '.hermes/terminal-sessions' / ('tty-dev-' + agent['tty']))
    if crumb.get('session_id') != sid or not isinstance(crumb.get('ts'), (int, float)) or crumb['ts'] < started: return row
    database = home / '.hermes/state.db'
    conn = db_open(database)
    try:
        meta = conn.execute('SELECT id,substr(title,1,500) title,substr(cwd,1,4096) cwd,substr(model,1,200) model,ended_at,last_activity_at,substr(last_activity_description,1,300) last_activity_description,last_activity_provenance FROM sessions WHERE id=?', (sid,)).fetchone()
        if not meta or meta['ended_at'] is not None: return row
        user = conn.execute("SELECT id,substr(content,1,1000) AS content FROM messages WHERE session_id=? AND role='user' AND active=1 ORDER BY id DESC LIMIT 1", (sid,)).fetchone()
        last = conn.execute("SELECT id,role,CASE WHEN tool_calls IS NOT NULL AND tool_calls NOT IN ('','[]','null') THEN 1 ELSE 0 END tool_calls,timestamp FROM messages WHERE session_id=? AND active=1 ORDER BY id DESC LIMIT 1", (sid,)).fetchone()
        automation = hermes_automation(conn,sid)
        desc = clean(meta['last_activity_description'])
        stamp = meta['last_activity_at']; fresh = isinstance(stamp, (int, float)) and 0 <= now - stamp <= 120
        activity = 'working' if desc and fresh else 'idle' if not desc and last and last['role'] == 'assistant' and not last['tool_calls'] else 'unknown'
        evidence = 'Hermes durable activity heartbeat' if activity == 'working' else 'Hermes cleared turn activity and last assistant reply' if activity == 'idle' else 'Missing, stale, or unfinished Hermes turn evidence'
        row.update(automation)
        row.update(id='hermes:'+sid+':'+str(agent['pid']), session_id=sid, title=clean(meta['title']) or 'Untitled Hermes conversation',
                   task=clean(user['content']) if user else 'No recorded user task', cwd=meta['cwd'] or crumb.get('cwd') or '',
                   model=clean(meta['model']) or 'unknown', activity=activity, activity_evidence=evidence,
                   association='native PID + start time + terminal record', source='hermes', source_path=str(database),
                   activity_detail=desc, turn_marker=last['id'] if last else None)
    finally: conn.close()
    return row


def jsonl_view(path, sid):
    fd, info = safe_file(path)
    try:
        head = os.pread(fd, min(info.st_size, 16384), 0)
        first = json.loads(head.split(b'\n')[0])
        if first.get('type') != 'session_meta' or first.get('payload', {}).get('id') != sid: raise ValueError('Session identity mismatch')
        start = max(0, info.st_size - LIMIT)
        tail = os.pread(fd, LIMIT, start).splitlines()
        if start: tail = tail[1:]
        records = []
        for line in tail:
            try: records.append(json.loads(line))
            except (ValueError, UnicodeError): continue
        task = ''; activity = 'unknown'; stamp = ''; turn = None
        for item in records:
            payload = item.get('payload')
            if not isinstance(payload, dict): continue
            if item.get('type') == 'event_msg':
                kind = payload.get('type')
                if kind == 'user_message': task = clean(payload.get('message'))
                if kind in ('task_started', 'turn_started'): activity = 'working'; stamp = item.get('timestamp', ''); turn = payload.get('turn_id')
                if kind in ('task_complete', 'task_completed', 'turn_complete', 'turn_aborted'): activity = 'idle'; stamp = item.get('timestamp', ''); turn = payload.get('turn_id')
        if activity == 'working':
            try:
                age = time.time() - datetime.datetime.fromisoformat(stamp.replace('Z', '+00:00')).timestamp()
                if not 0 <= age <= 120: activity = 'unknown'
            except (ValueError, TypeError): activity = 'unknown'
        return {'task':task or 'Task outside bounded tail; review conversation', 'activity':activity,
                'activity_evidence':'Codex explicit turn events' if activity != 'unknown' else 'No fresh explicit Codex turn marker',
                'turn_marker':turn, 'receipt':hashlib.sha256(head + b'\n'.join(tail)).hexdigest()}
    finally: os.close(fd)


def codex_candidates(home):
    conn = db_open(home / '.codex/state_5.sqlite')
    try:
        return [dict(r) for r in conn.execute('SELECT id,substr(title,1,500) title,substr(cwd,1,4096) cwd,substr(model,1,200) model,rollout_path,updated_at FROM threads WHERE archived=0 ORDER BY updated_at DESC LIMIT 64')]
    finally: conn.close()


def codex_turn(home, sid):
    conn = db_open(home / '.codex/thread_history_1.sqlite')
    try:
        turn = conn.execute('SELECT turn_id,status,first_user_item_id FROM thread_turns WHERE thread_id=? ORDER BY rollout_ordinal DESC LIMIT 1',(sid,)).fetchone()
        if not turn: return {}
        item = conn.execute("SELECT substr(item_json,1,8192) item_json FROM thread_items WHERE thread_id=? AND turn_id=? AND item_id=? AND item_type='userMessage'",(sid,turn['turn_id'],turn['first_user_item_id'])).fetchone()
        task = ''
        if item:
            try:
                data = json.loads(item['item_json'])
                if data.get('type') == 'userMessage':
                    task = clean(' '.join(clean(block.get('text'),1000) for block in data.get('content',[])[:20] if isinstance(block,dict) and block.get('type')=='text'))
            except (ValueError,TypeError): pass
        activity = 'working' if turn['status']=='inProgress' else 'idle' if turn['status'] in ('completed','interrupted','failed') else 'unknown'
        result = {'activity':activity,'activity_evidence':'Codex native turn status: '+clean(turn['status']), 'turn_marker':turn['turn_id']}
        if task: result['task'] = task
    finally: conn.close()
    try:
        queue = db_open(home / '.codex/queue_1.sqlite')
        try: result['queued_turns'] = queue.execute('SELECT COUNT(*) FROM queued_items WHERE thread_id=?',(sid,)).fetchone()[0]
        finally: queue.close()
    except (OSError,ValueError,sqlite3.Error): result['queued_turns'] = None
    return result


def codex(agent, home, started, links):
    row = base(agent)
    candidates = codex_candidates(home)
    link = links.get(str(agent['pid']), {})
    if not same_birth(link.get('birth'), started): return row
    matches = [c for c in candidates if c['id'] == link.get('session_id')]
    if len(matches) != 1: return row
    meta = matches[0]; path = Path(meta['rollout_path'])
    if home / '.codex/sessions' not in path.parents: return row
    view = jsonl_view(path, meta['id'])
    try: view.update(codex_turn(home,meta['id']))
    except (OSError,ValueError,sqlite3.Error): pass
    row.update(view); row.update(id='codex:'+meta['id']+':'+str(agent['pid']),session_id=meta['id'],title=clean(meta['title']),cwd=meta['cwd'] or '',
                                model=clean(meta['model']) or 'unknown',association='owner-confirmed (not automatically verified)',source='codex',source_path=str(path))
    # A manual link cannot prove this process stayed in the same conversation.
    row['activity_evidence'] += '; selected conversation only, live window association requires review'
    return row


def claude_task(path, sid, with_cwd=False):
    """Latest real user request in the bounded tail; with_cwd also returns the
    working directory the newest record reports (where the work is now, which
    for a home-started session is usually a repository, not home)."""
    fd, info = safe_file(path)
    try:
        start = max(0, info.st_size - LIMIT)
        chunks = os.pread(fd,LIMIT,start).splitlines()
        if start: chunks = chunks[1:]
        task = ''; cwd = ''
        for raw in chunks:
            try: record = json.loads(raw)
            except (ValueError,UnicodeError): continue
            if not isinstance(record,dict) or record.get('sessionId') != sid: continue
            here = record.get('cwd')
            if isinstance(here,str) and here.startswith('/') and len(here) < 4096: cwd = here
            if record.get('type') != 'user': continue
            message = record.get('message') or {}
            content = message.get('content',[]) if isinstance(message,dict) else []
            if isinstance(content,str): content = [{'type':'text','text':content}]
            if isinstance(content,list):
                text = ' '.join(clean(block.get('text'),1000) for block in content[:20] if isinstance(block,dict) and block.get('type')=='text')
                if text and not text.startswith(('<local-command','<command-name','<system-reminder')): task = clean(text)
        task = task or 'Task outside bounded transcript tail; review conversation'
        return (task, cwd) if with_cwd else task
    finally: os.close(fd)


def claude_activity(meta):
    """Claude Code records 'status': 'busy' | 'idle' (older builds: 'busy': bool)."""
    status = meta.get('status')
    if status == 'busy' or meta.get('busy') is True: return 'working'
    if status == 'idle' or meta.get('busy') is False: return 'idle'
    return 'unknown'


def claude(agent, home, started):
    row = base(agent)
    meta = read_json(home / '.claude/sessions' / f"{agent['pid']}.json")
    expected = meta.get('startedAt')
    if not same_birth(expected / 1000 if isinstance(expected, (int,float)) else None, started): return row
    sid = meta.get('sessionId')
    if meta.get('pid') != agent['pid'] or not isinstance(sid, str) or not ID.fullmatch(sid): return row
    activity = claude_activity(meta)
    task = 'Task transcript unavailable; open recovery review'
    cwd = meta.get('cwd') or ''
    work = cwd
    if cwd and isinstance(cwd,str) and cwd.startswith('/'):
        bucket = re.sub(r'[^a-zA-Z0-9]', '-', cwd)
        try: task, work = claude_task(home / '.claude/projects' / bucket / (sid+'.jsonl'), sid, with_cwd=True)
        except (OSError,ValueError): pass
    row.update(id='claude:'+sid+':'+str(agent['pid']),session_id=sid,title=clean(meta.get('name')) or 'Untitled Claude conversation',
               task=task,cwd=cwd,work_cwd=work or cwd,activity=activity,
               activity_evidence='Claude native session status',association='native Claude session record (PID + start time)',source='claude')
    return row


def repo_root(path):
    """The enclosing Git working tree, found from the filesystem only (no Git
    execution: a repository's config must never run code here). Home is never
    a project."""
    if not path: return None
    home = os.path.realpath(Path.home())
    current = Path(os.path.realpath(path))
    for parent in (current, *current.parents):
        if str(parent) == home or str(parent) == '/': return None
        if (parent / '.git').exists(): return str(parent)
    return None


DESTINATION = {'claude': 'codex', 'codex': 'claude', 'hermes': 'codex'}
NAMES = {'claude': 'Claude', 'codex': 'Codex', 'hermes': 'Hermes'}


def continue_command(row, project):
    """argv for the skeptic CLI that continues this conversation elsewhere.
    The CLI re-checks the session and asks for any approval it needs."""
    dest = DESTINATION.get(row['source'])
    if not dest or not project: return None
    if row['source'] == 'claude' and row.get('session_id'):
        return ['skeptic', 'session', 'continue', '--project', row['cwd'], '--id', row['session_id'], '--cwd', project, '--with', dest]
    if row['source'] == 'codex' and row.get('source_path'):
        return ['skeptic', 'session', 'continue', '--source', 'codex', '--session-file', row['source_path'], '--cwd', project, '--with', dest]
    return ['skeptic', 'continue', '--with', dest]


def assess(rows):
    for row in rows:
        work = row.get('work_cwd') or row['cwd']
        project = repo_root(work)
        row['project_root'] = project
        row['project'] = Path(project).name if project else ('Home; no repository yet' if work and os.path.realpath(work) == os.path.realpath(Path.home()) else 'Project unknown')
        blockers = []
        if row['association'] == 'unlinked': blockers.append('Conversation identity not linked')
        # A Codex link is owner-made but pinned to PID + start time, and its turn
        # state is read from Codex's own store; it may be ready, with a note.
        if row['activity'] == 'working': blockers.append('Source is working; do not start a competing writer')
        if row['activity'] == 'unknown': blockers.append('Turn state is not established')
        if row.get('queued_turns'): blockers.append('Codex has queued continuation; resolve it before handoff')
        if row.get('automation_pending'): blockers.append(row.get('automation_evidence','Automatic continuation needs review'))
        if not project: blockers.append('No repository in the session\'s current directory')
        peers = [r for r in rows if r is not row and project and repo_root(r.get('work_cwd') or r['cwd']) == project]
        busy_peers = [r for r in peers if r['activity'] == 'working']
        if busy_peers: blockers.append('Another agent is working in this repository; wait or pick one writer')
        row['writer'] = 'active' if row['activity'] == 'working' else 'conflict' if busy_peers else 'none' if row['activity'] == 'idle' else 'unknown'
        name = NAMES.get(row['source'], row['agent'])
        dest = NAMES.get(DESTINATION.get(row['source'], ''), 'another engine')
        if not blockers:
            row.update(readiness='ready', verdict='ready', headline=f'{dest} can pick up {row["project"]}',
                       next_step=f'Continue in {dest}', continue_command=continue_command(row, project))
        elif row['activity'] == 'working':
            row.update(readiness='blocked', verdict='wait', headline=f'{name} is mid-turn', next_step='Wait for this turn to finish', continue_command=None)
        elif row['association'] == 'unlinked' or row['activity'] == 'unknown':
            row.update(readiness='blocked', verdict='unknown', headline=f'Can\'t read this {name} session', next_step=blockers[0], continue_command=None)
        elif not project:
            row.update(readiness='needs review', verdict='needs_project', headline=f'{name} isn\'t in a repository', next_step='Open the work in a repository, or continue from your notes', continue_command=None)
        else:
            row.update(readiness='blocked', verdict='wait', headline=blockers[0], next_step=blockers[0], continue_command=None)
        row['continue_cwd'] = project if row.get('continue_command') else None
        notes = []
        if row['source'] == 'codex' and row['association'] != 'unlinked': notes.append('Codex conversation was linked by you in Sessions')
        if row['source'] == 'hermes': notes.append('Continues the project from notes and Git; the Hermes chat itself is not carried')
        if peers and not busy_peers: notes.append(f'{len(peers)} other idle agent(s) in this repository')
        if notes: row['note'] = '; '.join(notes)
        row['blocked_reasons'] = blockers
    return rows


def summary(rows):
    """The single answer a glance needs: the best row, ready first."""
    order = {'ready': 0, 'wait': 1, 'needs_project': 2, 'unknown': 3}
    best = sorted(rows, key=lambda r: (order.get(r.get('verdict'), 9), r['source'] != 'claude'))
    return best[0] if best else None


def collect(inventory, home=None, clock=time.time, births=birth):
    home = Path(home) if home else Path.home()
    try: links = read_json(home / '.skeptic-widget/session-links.json')
    except (OSError, ValueError, TypeError): links = {}
    rows = []
    for agent in inventory.get('agents', [])[:32]:
        row = base(agent)
        started = None
        try:
            started = births(agent['pid'])
            if agent['agent'] == 'Hermes': row = hermes(agent, home, started, clock())
            elif agent['agent'] == 'Codex': row = codex(agent, home, started, links)
            elif agent['agent'] == 'Claude Code': row = claude(agent, home, started)
        except (OSError, ValueError, TypeError, KeyError, sqlite3.Error, subprocess.SubprocessError): pass
        if started is not None: row['process_birth'] = started
        rows.append(row)
    return assess(rows)


if __name__ == '__main__':
    import importlib.util
    spec = importlib.util.spec_from_file_location('inventory', Path(__file__).with_name('live_inventory.py'))
    inventory = importlib.util.module_from_spec(spec); spec.loader.exec_module(inventory)
    print(json.dumps(collect(inventory.collect())))
