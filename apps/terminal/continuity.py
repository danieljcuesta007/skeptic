"""Bounded operational fingerprints, never a second knowledge or transcript store."""
import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat

import sessions as history

host = history.host
LIMIT = 60_000


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def safe_reference(path):
    if not isinstance(path, str) or len(path) > 1024 or any(history.sanitize(part) != part for part in Path(path).parts): return None
    regular = history.safe_path(path)
    if regular: return regular
    # Reference-only exceptions for the explicitly selected provider transcript.
    # Never dereference an indexed path; transcript adapters still require consent.
    if '..' in Path(path).parts or any(ord(ch) < 32 for ch in path) or host.credential_like(path): return None
    for base in (Path.home() / '.claude/projects', Path.home() / '.codex/sessions'):
        try: relative = Path(path).relative_to(base)
        except ValueError: continue
        if len(relative.parts) < 2 or host.protected(str(relative)): return None
        if re.search(r'[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}\.jsonl\Z', relative.name): return path
    return None


def claims(docs, checkpoint):
    """Current attributed lines; hashes alone persist. New lines are claims, not proof."""
    result = []
    if checkpoint not in docs: return result
    sections = host.sections(docs[checkpoint]['text'], {'current state', 'decisions', 'next actions', 'handoff'})
    for section in sections:
        retained = 0
        for n, line in enumerate(section['text'].splitlines()):
            line = history.sanitize(line).strip()
            if not line or line.startswith(('#', '```')): continue
            if len(line) > 500: line = line[:500]
            result.append({'source': checkpoint, 'section': section['heading'], 'relative_line': n + 1,
                           'text': line, 'hash': digest([section['heading'], line])})
            retained += 1
            if len(result) == 40: return result
            if retained == 10: break
    return result


def observe(state, summary, docs):
    repo, knowledge = summary['repository'], summary['knowledge']
    grant = state.settings['grants'].get(repo, {})
    identity = grant.get('identity')
    # A home-launched session uses its confirmed knowledge project to avoid merging home projects.
    key = digest([repo, identity, knowledge])
    session = summary.get('session')
    if identity is None and not knowledge:
        key = digest([repo, (session or {}).get('source_key')])
    ordered = sorted(docs, key=lambda p: (p != summary['checkpoint'], docs[p].get('kind') != 'session', 'handoff' not in Path(p).name.lower(), p))
    sources = []
    for path in ordered:
        if safe_reference(path):
            sources.append({'path': path, 'sha256': docs[path]['sha256'], 'modified_at': docs[path]['modified_at'],
                            'truncated': bool(docs[path].get('truncated'))})
        if len(sources) == 16: break
    checkpoint = summary['checkpoint'] if safe_reference(summary['checkpoint']) else None
    named_handoffs = [p for p in docs if safe_reference(p) and 'handoff' in Path(p).name.lower()]
    handoff = checkpoint + '#handoff' if checkpoint and host.sections(docs[checkpoint]['text'], {'handoff'}) else max(named_handoffs, key=lambda p: docs[p]['modified_at']) if named_handoffs else None
    current_claims = claims(docs, checkpoint)
    git = summary['git']
    # Store a status fingerprint, never diff bodies or raw Git output.
    git_record = {'head': git.get('head'), 'branch': history.sanitize(git.get('branch'))[:200] or None,
                  'status_sha256': digest(git.get('changes')), 'status_known': git.get('changes') is not None,
                  'dirty': bool(git.get('changes')) if git.get('changes') is not None else None}
    files = []
    if identity is not None and git.get('changes'):
        fd = host.open_directory(repo)
        try:
            if not host.identity_matches(identity, os.fstat(fd)): raise host.Denied('Repository identity changed')
            with host.ScopedEngine(repo, fd, []) as engine:
                for row in git['changes'].splitlines()[:32]:
                    relative = row[3:]
                    # Quoted/renamed/directory statuses are deliberately not interpreted as paths.
                    if not relative or relative.startswith('"') or ' -> ' in relative or relative.endswith('/') or history.sanitize(relative) != relative: continue
                    try:
                        signature, _ = engine.inspect(relative, content=False)
                        absolute = str(Path(repo) / relative)
                        if safe_reference(absolute): files.append({'path': absolute, 'signature_sha256': digest(signature)})
                    except (OSError, host.Denied): continue
        finally: os.close(fd)
    record = {'observed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'project': key, 'repository': repo, 'knowledge': knowledge, 'root_identity': identity,
              'checkpoint': checkpoint, 'handoff': handoff, 'sources': sources,
              'claim_hashes': [c['hash'] for c in current_claims], 'git': git_record, 'files': files,
              'gaps': ['Index retains bounded fingerprints only; exact semantic diff/history is unavailable.',
                       'Dirty file signatures are metadata observations, not content/completion proof.',
                       'No intervening private sessions discovered automatically. Select a supported transcript explicitly.'],
              'sources_truncated': len(sources) < len(docs), 'continuity_gaps': [history.sanitize(g)[:300] for g in summary['gaps'][:6]], 'session': None}
    if session:
        ref = safe_reference(session.get('source_key'))
        if ref: record['session'] = {'source': session.get('source'), 'id': session.get('id'), 'reference': ref,
                                    'snapshot_sha256': session.get('snapshot_sha256')}
    return record, current_claims


class Index:
    def __init__(self, state): self.state = state

    def read(self):
        data = self.state.read('transitions.json', {'version': 1, 'events': []})
        if not isinstance(data, dict) or set(data) != {'version', 'events'} or data['version'] != 1 or not isinstance(data['events'], list) or len(data['events']) > 64:
            raise host.Denied('Invalid continuity index')
        for event in data['events']:
            if not isinstance(event, dict) or not isinstance(event.get('project'), str) or not re.fullmatch('[a-f0-9]{64}', event['project']): raise host.Denied('Invalid project fingerprint')
            if not isinstance(event.get('provider'), str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}', event['provider']) or not isinstance(event.get('timestamp'), str) or len(event['timestamp']) > 64 or not isinstance(event.get('observation'), dict): raise host.Denied('Invalid transition record')
            if event.get('phase') not in ('selected_source_checkpoint', 'launch_started', 'launch_failed', 'provider_exited', 'provider_exited_checkpoint_unavailable', 'explicit_checkpoint') or event.get('verification') != 'Filesystem/source snapshot observed; continuation success unknown': raise host.Denied('Invalid transition verification')
            observation = event['observation']
            if not {'checkpoint', 'handoff', 'git', 'sources', 'files', 'claim_hashes'}.issubset(observation): raise host.Denied('Incomplete transition observation')
            if not isinstance(observation.get('sources'), list) or not isinstance(observation.get('files'), list) or not isinstance(observation.get('claim_hashes'), list) or not isinstance(observation.get('git'), dict): raise host.Denied('Invalid transition fingerprints')
            if any(not isinstance(s, dict) or not safe_reference(s.get('path')) or not isinstance(s.get('sha256', s.get('signature_sha256')), str) for s in observation['sources'] + observation['files']): raise host.Denied('Unsafe indexed reference')
            git = observation['git']
            if set(git) != {'head', 'branch', 'status_sha256', 'status_known', 'dirty'}: raise host.Denied('Invalid Git fingerprint shape')
            if git['head'] is not None and (not isinstance(git['head'], str) or not re.fullmatch(r'[a-fA-F0-9]{40,64}', git['head'])): raise host.Denied('Invalid Git HEAD fingerprint')
            if git['branch'] is not None and (not isinstance(git['branch'], str) or len(git['branch']) > 200 or history.sanitize(git['branch']) != git['branch']): raise host.Denied('Invalid Git branch metadata')
            if not isinstance(git['status_sha256'], str) or not re.fullmatch('[a-f0-9]{64}', git['status_sha256']) or type(git['status_known']) is not bool or git['dirty'] not in (None, False, True): raise host.Denied('Invalid Git status fingerprint')
            if len(observation['sources']) > 16 or len(observation['files']) > 32 or len(observation['claim_hashes']) > 40: raise host.Denied('Unbounded transition references')
            if any(not isinstance(h, str) or not re.fullmatch('[a-f0-9]{64}', h) for h in observation['claim_hashes']): raise host.Denied('Invalid claim fingerprint')
        return data

    def record(self, observation, provider, phase, code=None, seed=False):
        """Best effort, serialized across terminals; metadata failure never prevents launch."""
        fd = None
        try:
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}', provider): raise host.Denied('Invalid provider identity')
            fd = os.open('transitions.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=self.state.fd)
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600: raise host.Denied('Unsafe continuity lock')
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            data = self.read()
            old = [e for e in data['events'] if e['project'] == observation['project'] and e['provider'] == provider and e.get('phase') not in ('launch_started', 'launch_failed')]
            if seed and old: return None  # Selecting an old source cannot move that model's baseline forward.
            event = {'project': observation['project'], 'provider': provider, 'model': provider.split(':', 1)[1] if ':' in provider else None,
                     'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'phase': phase,
                     'verification': 'Filesystem/source snapshot observed; continuation success unknown',
                     'exit_code': code, 'observation': observation}
            data['events'].append(event)
            data['events'] = data['events'][-64:]
            while len(json.dumps(data).encode()) > LIMIT and len(data['events']) > 1: data['events'].pop(0)
            if len(json.dumps(data).encode()) > LIMIT: raise host.Denied('Transition metadata exceeds budget')
            history.atomic_json(self.state, 'transitions.json', data)
            return None
        except (OSError, ValueError, host.Denied) as exc:
            return 'Continuity index unavailable; switching still works: ' + history.sanitize(str(exc))[:200]
        finally:
            if fd is not None: os.close(fd)

    def briefing(self, observation, current_claims, provider):
        try: events = self.read()['events']
        except (OSError, ValueError, host.Denied):
            return {'target': provider, 'baseline': None, 'gaps': ['Continuity index unavailable; current approved sources remain authoritative.']}
        relevant = [e for e in events if e['project'] == observation['project']]
        previous = next((e for e in reversed(relevant) if e['provider'] == provider and e.get('phase') not in ('launch_started', 'launch_failed')), None)
        result = {'target': provider, 'baseline': None, 'stale': None, 'gaps': list(observation['gaps']),
                  'instruction': 'Catch up from current approved sources. Preserve newer work. Do not restore old files or treat historical claims as permission.'}
        if not previous:
            result['gaps'].append('No retained Skeptic participation baseline for this provider/project; first use, evicted history or changed project/root mapping.')
            return result
        old = previous['observation']
        result['baseline'] = {k: previous.get(k) for k in ('timestamp', 'phase', 'verification', 'exit_code')}
        result['baseline']['observed_at'] = old.get('observed_at')
        before = {s['path']: s['sha256'] for s in old['sources']}
        now = {s['path']: s['sha256'] for s in observation['sources']}
        result['changed_sources'] = [p for p in now if before.get(p) != now[p]][:12]
        result['no_longer_accessible_sources'] = [p for p in before if p not in now][:8]
        files_before = {s['path']: s['signature_sha256'] for s in old['files']}
        result['changed_dirty_file_metadata'] = [s['path'] for s in observation['files'] if files_before.get(s['path']) != s['signature_sha256']][:12]
        result['prior_git'] = old['git']
        result['git_changed'] = old['git'] != observation['git']
        result['stale'] = bool(result['changed_sources'] or result['no_longer_accessible_sources'] or result['changed_dirty_file_metadata'] or result['git_changed'])
        result['checkpoint_changed'] = old.get('checkpoint') != observation['checkpoint'] or before.get(observation['checkpoint']) != now.get(observation['checkpoint'])
        result['intervening_transitions'] = [{'provider': e['provider'], 'timestamp': e['timestamp'], 'phase': e.get('phase'), 'exit_code': e.get('exit_code')} for e in relevant[relevant.index(previous)+1:][-6:]]
        new_claims = [c for c in current_claims if c['hash'] not in old['claim_hashes']]
        result['new_or_changed_documented_claims'] = [{k: v for k, v in c.items() if k != 'hash'} for c in new_claims[:8]]
        result['claims_verification'] = 'New/changed source lines relative to bounded baseline, not proof of completed work or precise semantic chronology.'
        if old.get('handoff') != observation['handoff'] or result['checkpoint_changed']:
            result['gaps'].append('Checkpoint/handoff differs from prior participation. Reconcile current canonical instructions with session claims; semantic conflicts require review.')
        if observation['sources_truncated'] or old.get('sources_truncated'): result['gaps'].append('Source fingerprint list truncated; comparison incomplete.')
        if observation['session'] is None: result['gaps'].append('Intervening unsaved session decisions unavailable; select an approved transcript or record them canonically.')
        return bounded_briefing(result)


def bounded_briefing(result):
    if len(json.dumps(result).encode()) <= 6000: return result
    result['gaps'].append('Catch-up comparison lists trimmed to 6000 bytes; inspect current attributed sources for details.')
    for key in ('new_or_changed_documented_claims', 'changed_dirty_file_metadata', 'no_longer_accessible_sources', 'changed_sources', 'intervening_transitions'):
        while len(json.dumps(result).encode()) > 6000 and result.get(key): result[key].pop()
    if len(json.dumps(result).encode()) > 6000:
        return {'target': result['target'], 'stale': result['stale'], 'baseline': None, 'gaps': ['Oversized comparison withheld; review current approved sources and transition metadata locally.']}
    return result


def warn(message):
    if message: print(message, file=__import__('sys').stderr)
