"""One-shot macOS Terminal metadata inventory; never terminal text or provider control."""
import json
import os
import stat
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = r'''const t = Application('/System/Applications/Utilities/Terminal.app');
if (!t.running()) JSON.stringify([]);
else { let rows = []; for (const w of t.windows()) {
const tabs=w.tabs(); for (let i=0; i<tabs.length; i++) { const tab=tabs[i];
rows.push({window:w.id(), tab:i+1, tty:tab.tty(), busy:tab.busy()});
if (rows.length > 128) throw Error('Tab limit exceeded');
}} JSON.stringify(rows); }'''
TTY = re.compile(r'^/dev/ttys[0-9]+$')
UUID = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')


def birth_epoch(pid, execute=None):
    """Normalize process birth to UTC epoch seconds.

    Claude's native session records store procStart in UTC while `ps -lstart`
    renders the same instant in the machine's local timezone, so the two
    strings can differ (e.g. UTC vs EDT) for the exact same process. Comparing
    the raw strings would treat one live process as two different ones and
    silently degrade window association. Parse both to an epoch and compare
    numbers. A record whose clock cannot be normalized never asserts identity.
    """
    execute = execute or command
    raw = execute(['/bin/ps', '-p', str(pid), '-o', 'lstart=']).strip()
    if not raw: raise ValueError('Process birth unavailable')
    return normalize_birth(raw)


def normalize_birth(raw, source='ps'):
    """Parse a process-birth string to UTC epoch seconds.

    The same instant appears in two encodings on this system: `ps -lstart`
    renders the machine's LOCAL time ('Tue Oct  6 14:14:54 2026', EDT) while
    Claude's native session records store procStart in UTC
    ('Tue Oct  6 18:14:54 2026'). These differ by the local offset for the
    identical process, so raw-string comparison treats one running Claude as
    two processes and silently degrades window association. Parse each to a
    single comparable number in the zone it is actually written in:

      source='ps'     no explicit zone -> the machine's local time
      source='record' no explicit zone -> UTC
    ISO inputs with an explicit Z/offset are honored as written regardless of
    source. Unparseable returns None so identity stays unasserted, not guessed.
    """
    if not isinstance(raw, str): return None
    text = raw.strip()
    if not text: return None
    if text.isdigit(): return int(text)
    # explicit offset or Z wins outright
    for form in ('%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M:%S.%f%z'):
        try: return int(datetime.strptime(text, form).timestamp())
        except ValueError: continue
    try: return int(datetime.strptime(text, '%Y-%m-%dT%H:%M:%SZ')
                    .replace(tzinfo=timezone.utc).timestamp())
    except ValueError: pass
    # ps-style wall clock, no zone
    try:
        moment = datetime.strptime(text, '%a %b %d %H:%M:%S %Y')
        if source == 'record': moment = moment.replace(tzinfo=timezone.utc)
        return int(moment.timestamp())
    except ValueError: return None


def command(argv):
    result = subprocess.run(argv, capture_output=True, text=True, timeout=8,
                            check=True)
    if len(result.stdout) > 131072:
        raise ValueError('Metadata output limit exceeded')
    return result.stdout


def native_record(pid, directory=None):
    """Exact PID only, no registry scan; undocumented metadata is a hint, never proof."""
    directory = Path(directory) if directory else Path.home() / '.claude/sessions'
    from sessions import safe_path, sanitize
    fd = rootfd = None
    try:
        import switcher
        rootfd = switcher.host.open_directory(str(directory))
        fd = os.open(str(pid) + '.json', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=rootfd)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1 or info.st_size > 16384:
            return None
        data = json.loads(os.read(fd, 16385))
        if not isinstance(data, dict) or type(data.get('pid')) is not int or data['pid'] != pid:
            return None
        sid = data.get('sessionId')
        if not isinstance(sid, str) or not UUID.fullmatch(sid): return None
        cwd = safe_path(data.get('cwd'))
        # procStart in Claude's record is a UTC wall-clock string
        # ('Tue Oct  6 18:14:54 2026'); parse it AS UTC so it matches a live
        # `ps -lstart` (which renders the same instant in local time). Falls
        # back to the ms epoch startedAt. None when absent/unparseable: the
        # identity stays unasserted, never guessed.
        epoch = normalize_birth(data.get('procStart', ''), source='record')
        if epoch is None:
            value = data.get('startedAt')
            if isinstance(value, (int, float)) and 10**11 < value < 10**14:
                epoch = int(value // 1000)
        return {'pid': pid, 'id': sid.lower(), 'cwd': cwd,
                'name': sanitize(data.get('name', ''))[:120] if isinstance(data.get('name'), str) else '',
                'busy': data.get('busy') if type(data.get('busy')) is bool else None,
                'epoch_hint': epoch}
    except (OSError, ValueError, __import__('switcher').host.Denied): return None
    finally:
        if fd is not None: os.close(fd)
        if rootfd is not None: os.close(rootfd)


def collect(execute=command, platform=None, records=None):
    if (platform or sys.platform) != 'darwin':
        raise ValueError('Open Terminal discovery requires macOS')
    rows = json.loads(execute(['/usr/bin/osascript', '-l', 'JavaScript', '-e', SCRIPT]))
    if not isinstance(rows, list) or len(rows) > 128:
        raise ValueError('Invalid Terminal metadata')
    found = []
    records = records or native_record
    for row in rows:
        if (not isinstance(row, dict) or type(row.get('window')) is not int
                or type(row.get('tab')) is not int or row['tab'] < 1
                or type(row.get('busy')) is not bool
                or not isinstance(row.get('tty'), str) or not TTY.fullmatch(row['tty'])):
            raise ValueError('Invalid Terminal tab metadata')
        item = dict(row, pids=[], process='unknown', identity='unmatched', candidates=[], process_identity={})
        try:
            output = execute(['/bin/ps', '-t', row['tty'][5:], '-o', 'pid=,comm=,stat='])
            for line in output.splitlines():
                parts = line.strip().split(None, 1)
                if len(parts) != 2 or not parts[0].isdigit():
                    continue
                executable, _, status = parts[1].rpartition(' ')
                name = Path(executable.strip()).name
                if (name in ('claude', 'claude-code') or '/.local/share/claude/versions/' in executable) and not status.startswith('Z'):
                    pid = int(parts[0]); item['pids'].append(pid)
                    # Birth is normalized to UTC epoch: Claude's records use UTC,
                    # ps reports local time, and raw-string comparison would split
                    # one live process into two identities. Never matches UUID by time.
                    item['process_identity'][pid] = birth_epoch(pid, execute)
                    record = records(pid)
                    if record: item['candidates'].append(record)
            item['process'] = 'Claude process present' if item['pids'] else 'no identifiable Claude process'
        except (OSError, ValueError, subprocess.SubprocessError):
            item['process'] = 'unknown (process metadata unavailable)'
            item['candidates'] = []
        if item['candidates']: item['identity'] = 'uncertain (native PID record; owner confirmation required)'
        # TTY/PID establish process association only. Native records can be stale.
        found.append(item)
    return found


def identify_candidates(rows, adapter, access, project):
    """Approved exact-UUID transcript hints; never a window identity assertion."""
    import sessions as history
    import switcher as host
    result = {}
    for row in rows:
        for candidate in row.get('candidates', []):
            sid = candidate['id']
            if sid in result: continue
            profile = {'availability': 'metadata unavailable', 'request': None, 'session': None}
            result[sid] = profile
            print('Identify CANDIDATE transcript ' + sid + ' — window association UNCONFIRMED.')
            try:
                items = adapter.discover(access, project, True, sid, None)
                if len(items) != 1:
                    profile['availability'] = 'exact UUID unavailable/ambiguous'; continue
                item = items[0]
                profile.update(session=item, availability='approved metadata; request extraction not approved')
                # Separate existing extraction consent even when native metadata was approved.
                snapshot = adapter.snapshot(access, item)
                if adapter.verify(access, snapshot)['appended_bytes']:
                    profile['availability'] = 'transcript changed; request hint withheld'; continue
                users = [r for r in snapshot['records'] if r.get('role') == 'user' or
                         r.get('role', '').startswith('historical-user-request')]
                users.sort(key=lambda r: (r.get('window_offset', 0), r.get('window_line', 0)))
                request = users[-1] if users else None
                profile.update(availability='approved transcript evidence; association unconfirmed',
                               request=' '.join(history.excerpt(request.get('untrusted_text', ''), 240).split()) if request else None,
                               request_origin=(request.get('message_id') or '?') if request else None,
                               gaps=bool(snapshot.get('chain_gap') or snapshot.get('partial') or snapshot.get('malformed_records')
                                         or (request and request.get('excerpt_truncated'))),
                               receipt={k: snapshot[k] for k in ('source', 'root', 'path', 'scope', 'scope_key', 'access_key', 'identity', 'snapshot_size', 'snapshot_sha256', 'byte_windows')})
            except (host.host.Denied, OSError, ValueError):
                # Declining one transcript is not permission to read the next one.
                # Every next exact candidate still passes existing gates independently.
                pass
    return result


def candidate_label(row, candidate, profiles):
    import sessions as history
    profile = profiles.get(candidate['id'], {}) if candidate else {}
    item = profile.get('session') or {}
    cwd = item.get('cwd') or (candidate.get('cwd') if candidate else None)
    project_name = Path(cwd).name if cwd else 'project unknown'
    if cwd and Path(cwd) == Path.home(): project_name += ' (home-started; actual project unconfirmed)'
    title = item.get('title') or (candidate.get('name') if candidate else None) or 'title unavailable'
    sid = candidate['id'] if candidate else 'unmatched'
    heading = title + f" | Window {row['window']} / Tab {row['tab']} | {row['tty']} | "
    heading += ('UNCONFIRMED' if candidate else 'UNMATCHED')
    label = str.__new__(history.SessionLabel, heading)
    label.picker_title = heading
    label.picker_details = (
        ('Last user request — CANDIDATE ONLY', profile.get('request') or profile.get('availability', 'not extracted')),
        ('Recorded directory (not verified project root)', cwd or 'unknown'),
        ('Project hint', project_name),
        ('Last activity', item.get('updated', 'unknown')),
        ('Candidate transcript title' if item else 'Native name hint only', title),
        ('Association', 'UNCONFIRMED native PID hint; transcript content is not verified as belonging to this window'),
        ('Evidence', profile.get('availability', 'native metadata only; transcript not read') +
                     ('; incomplete/truncated evidence' if profile.get('gaps') else '')),
        ('Window/tab/TTY', f"{row['window']}/{row['tab']} | {row['tty']}"),
        ('Process', row['process']), ('UUID', sid))
    return label


def run(args, state, adapter, access, project, picker=None, ask=None, collector=None):
    import switcher as host
    import session_review
    picker, ask = picker or host.choose, ask or input
    collector = collector or collect
    print('One-time metadata access: Terminal.app window/tab IDs, TTY and busy flag; '
          'PID/executable/status and Claude process birth metadata only for processes on those TTYs; bounded per-PID Claude '
          'session records (UUID, cwd, name, busy). These records are undocumented hints. No terminal text, '
          'arguments, environment, transcript bodies or window/process changes. '
          'macOS may request Terminal Automation permission; denial stops discovery.')
    if ask('Type discover to authorize this inventory (anything else cancels): ').strip() != 'discover':
        raise host.host.Denied('Open Terminal discovery declined')
    try:
        rows = collector()
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        raise host.host.Denied('Terminal metadata unavailable; no history fallback or permission changes') from error
    print('Confirmed automatic transcript matches: none. Native PID records are uncertain '
          'until owner-confirmed; other tabs are unmatched. Open/busy/process state '
          'does not establish unfinished work.')
    # Keep uncertain associations separate from unmatched tabs; no history read.
    rows.sort(key=lambda r: 0 if r.get('candidates') else 1)
    profiles = {}
    if any(r.get('candidates') for r in rows):
        print('Recognizable context can be read OFFLINE from these exact candidate UUIDs. '
              'This does not confirm the window association. Existing metadata and each transcript '
              'extraction approval apply; declining leaves that candidate context unavailable.')
        if ask('Type identify to request candidate titles/projects and last user-request hints (anything else skips): ').strip() == 'identify':
            profiles = identify_candidates(rows, adapter, access, project)
    entries = [(row, candidate) for row in rows for candidate in (row.get('candidates') or [None])]
    labels = [candidate_label(row, candidate, profiles) for row, candidate in entries]
    labels += ['Browse historical sessions (separate approval)', 'Cancel']
    selected = picker('Open Terminal sessions first — select the Claude work to continue', labels)
    if selected == len(entries) + 1: return 0
    if selected == len(entries):
        args.all_projects = True
        if getattr(args, 'continue_open', False):
            import sessions
            item = sessions.selected_session(adapter, access, project, picker, args.title, args.session_id, True)
            return session_review.continue_selected(args, state, adapter, access, item, ask=ask, picker=picker)
        return session_review.run(args, state, adapter, access, project, picker=picker, ask=ask)
    row, candidate = entries[selected]
    if candidate:
        session_id = candidate['id']
        print(str(candidate_label(row, candidate, profiles)))
        for name, value in candidate_label(row, candidate, profiles).picker_details: print(name + ': ' + str(value))
        print('Native PID record suggests this UUID for this tab. Record may be stale; '
              'confirm using the original work you recognize. Transcript hints alone do not prove the association.')
    else:
        print('No reliable UUID signal. Paste the exact session UUID or transcript path '
              'from original session information you can identify. No screen is read; '
              'do not guess by title/date. Blank cancels.')
        value = ask('Exact session UUID or transcript path: ').strip()
        if not value: return 0
        session_id = Path(value).stem if value.endswith('.jsonl') else value
        if not UUID.fullmatch(session_id): raise host.host.Denied('Invalid exact UUID')
    association = ask(f"Type confirm if {session_id} belongs to window {row['window']} tab {row['tab']}; "
                      "type transcript to select this conversation independently with window association UNCONFIRMED "
                      "(anything else cancels): ").strip()
    if association not in ('confirm', 'transcript'):
        raise host.host.Denied('Manual association not confirmed')
    def source_check():
        try: fresh = collector()
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            raise host.host.Denied('Open-source metadata unavailable during recheck; no provider launched') from error
        matches = [r for r in fresh if (r['window'], r['tab'], r['tty']) == (row['window'], row['tab'], row['tty'])]
        if (len(matches) != 1 or matches[0].get('pids') != row.get('pids')
                or matches[0].get('process_identity') != row.get('process_identity')):
            raise host.host.Denied('Selected tab/process changed; rediscover before proceeding')
        if candidate and candidate not in matches[0].get('candidates', []):
            raise host.host.Denied('Native session record changed; rediscover before proceeding')
        if getattr(args, 'continue_open', False) and candidate and candidate.get('busy') is True:
            raise host.host.Denied('Native source reports busy; writer safety prevents continuation. Original preserved.')
    if association == 'confirm': source_check()
    receipt = profiles.get(session_id, {}).get('receipt')
    if receipt and adapter.verify(access, receipt)['appended_bytes']:
        raise host.host.Denied('Candidate transcript changed since identification; rediscover before continuation')
    if getattr(args, 'continue_open', False):
        args.open_source_check = source_check if association == 'confirm' else None
    if association == 'confirm':
        print('Identity: owner-confirmed, not automatically verified. Existing transcript '
              'approvals and project/writer checks still apply.')
    else:
        print('Transcript selected independently. Window association remains UNCONFIRMED; '
              'actual source process and writer state are UNKNOWN. Existing transcript approvals, '
              'actual project confirmation and project-clear writer checks still apply.')
    if args is not None:
        args.session_association = ('Owner-confirmed window association; not automatically verified.' if association == 'confirm'
                                    else 'Transcript selected independently; window association UNCONFIRMED; source process and writer state UNKNOWN.')
    items = adapter.discover(access, project, True, session_id, None)
    if len(items) != 1:
        raise host.host.Denied('Exact UUID is unavailable or ambiguous in approved storage; no guessed match')
    if getattr(args, 'continue_open', False):
        return session_review.continue_selected(args, state, adapter, access, items[0], picker=picker, ask=ask)
    return session_review.run(args, state, adapter, access, project, picker=picker, ask=ask, chosen=items)
