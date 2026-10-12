"""Consent-gated local session adapter. Never mutates or resumes a provider session."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'local'))
import app as host

UUID = re.compile(r'[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}\Z')
META_WINDOW = 65536
SNAPSHOT_LIMIT = 8 * 1024 * 1024
SESSION_TEXT_LIMIT = 12000


def sanitize(text):
    """Conservative whole-line withholding before every display/context surface."""
    if not isinstance(text, str): return ''
    if re.search(r'-----BEGIN (?:[A-Z ]+)?PRIVATE KEY-----', text): return '[private key content withheld]'
    output = []
    for line in text.splitlines():
        secret = host.credential_like(line) or re.search(
            r'(?i)(?:authorization\s*[:=]|bearer\s+\S+|(?:password|passwd|api[_ -]?key|access[_ -]?token|refresh[_ -]?token|client[_ -]?secret|secret[_ -]?key)\s*["\x27]?\s*[:=]\s*\S+|AKIA[A-Z0-9]{16}|[a-z]+://[^\s/:]+:[^\s@]+@|eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+)', line)
        secret = secret or re.search(r'(?<!\w)[A-Za-z0-9+/=_-]{80,}(?!\w)', line)
        protected = re.search(r'(?i)(?:^|[\s/"\x27`])(?:\.env(?:\.[\w-]+)?|\.ssh|\.aws|credentials(?:\.json)?|secrets(?:\.json)?|id_rsa|id_ed25519)(?:$|[\s/"\x27`:])', line)
        if secret or protected: output.append('[sensitive/protected line withheld]')
        else: output.append(''.join(c if c >= ' ' and c != '\x7f' else ' ' for c in line))
    return '\n'.join(output)


def safe_path(value):
    if not isinstance(value, str) or not value or len(value) > 4096: return None
    value = os.path.expanduser(value)
    if not value.startswith('/') or '..' in Path(value).parts or any(ord(c) < 32 for c in value) or host.protected(value) or host.credential_like(value): return None
    return value.rstrip('/') or '/'


def encoded_project(project):
    encoded = re.sub(r'[^a-zA-Z0-9]', '-', project)
    if len(encoded) > 200: raise host.Denied('Long Claude storage names require --all-projects or explicit --id discovery')
    return encoded


def atomic_json(state, name, data):
    payload = json.dumps(data).encode()
    if len(payload) > 65536: raise host.Denied('Session consent state exceeds limit')
    temporary = 'pending-' + os.urandom(16).hex()
    fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=state.fd)
    try:
        with os.fdopen(fd, 'wb') as output:
            output.write(payload); output.flush(); os.fsync(output.fileno())
        os.rename(temporary, name, src_dir_fd=state.fd, dst_dir_fd=state.fd)
    finally:
        try: os.unlink(temporary, dir_fd=state.fd)
        except FileNotFoundError: pass


class Access:
    def __init__(self, state, ask=None, force_prompt=False):
        self.state, self.ask, self.force_prompt = state, ask or input, bool(force_prompt)
        self.data = state.read('sessions.json', {'grants': {}})
        if not isinstance(self.data, dict) or set(self.data) != {'grants'} or not isinstance(self.data['grants'], dict): raise host.Denied('Invalid session consent state')
        for key, value in self.data['grants'].items():
            if not isinstance(key, str) or not isinstance(value, list) or len(value) != 2 or any(not isinstance(n, int) for n in value): raise host.Denied('Invalid session consent')

    def consent(self, key, info, message):
        identity = [info.st_dev, info.st_ino]
        if self.force_prompt or self.data['grants'].get(key) != identity:
            if not sys.stdin.isatty(): raise host.Denied('Session approval required in a second Terminal; original Claude can stay open')
            print(sanitize(message))
            print('Persistent permission; revoke with: skeptic sessions revoke')
            if self.ask('Type approve: ').strip() != 'approve': raise host.Denied('Session access declined')
            self.data['grants'][key] = identity
            atomic_json(self.state, 'sessions.json', self.data)

    def revoke(self):
        self.data['grants'] = {}; atomic_json(self.state, 'sessions.json', self.data)

    def check(self, key, info):
        # Fresh read defeats revocation by another terminal between selection and launch.
        current = self.state.read('sessions.json', {'grants': {}})
        if current.get('grants', {}).get(key) != [info.st_dev, info.st_ino]: raise host.Denied('Session access revoked or source replaced')


def open_file(root, relative):
    """Exact ancestry and names; owner-only regular, single-link session files."""
    parts = Path(relative).parts
    if not parts or Path(relative).is_absolute() or any(p in ('.', '..') for p in parts): raise host.Denied('Invalid session locator')
    directory = host.open_directory(str(root))
    try:
        for part in parts[:-1]:
            if part not in os.listdir(directory): raise host.Denied('Session path alias or missing directory')
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory); directory = child
        if parts[-1] not in os.listdir(directory): raise host.Denied('Session file alias or missing file')
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid():
            os.close(fd); raise host.Denied('Unsafe session file')
        return fd, info
    finally: os.close(directory)


def rows_from_chunks(chunks):
    rows, malformed = [], 0
    for offset, body in chunks:
        lines = body.splitlines(keepends=True)
        if offset and lines: lines = lines[1:]  # Conservative: discard partial first record.
        for index, raw in enumerate(lines):
            if not raw.endswith(b'\n'): malformed += 1; continue  # Live unfinished append.
            try:
                row = json.loads(raw)
                if isinstance(row, dict): rows.append((offset, index + 1, row))
                else: malformed += 1
            except (ValueError, UnicodeError, RecursionError): malformed += 1
    return rows, malformed


def read_chunks(fd, info, limit):
    if info.st_size <= limit:
        return [(0, os.pread(fd, info.st_size, 0))]
    headsize = min(256 * 1024, limit // 2)
    tailstart = info.st_size - (limit - headsize)
    return [(0, os.pread(fd, headsize, 0)), (tailstart, os.pread(fd, info.st_size - tailstart, tailstart))]


class ClaudeAdapter:
    source = 'claude'

    def __init__(self, root):
        self.root = Path(os.path.abspath(os.path.expanduser(root)))
        default = Path.home() / '.claude/projects'
        if self.root != default:
            # Overrides are explicit user-selected synthetic/custom storage roots, never protected config roots.
            _, fd = host.approve_root(str(self.root)); os.close(fd)

    def discover(self, access, project, all_projects=False, session_id=None, title=None):
        if session_id and not UUID.fullmatch(session_id): raise host.Denied('Session ID must be a UUID')
        all_projects = all_projects or bool(session_id)
        try: rootfd = host.open_directory(str(self.root))
        except OSError: raise host.Denied("Session storage unavailable; check --session-root. Original session untouched.")
        try:
            scope = str(self.root) if all_projects else str(self.root / encoded_project(project))
            key = 'metadata:' + scope
            # No listing/read happens until scope consent. Pin root then scoped bucket separately.
            if all_projects:
                scopedfd = os.dup(rootfd)
            else:
                bucket = encoded_project(project)
                try: scopedfd = os.open(bucket, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=rootfd)
                except OSError: raise host.Denied("Session bucket unavailable. Use --project with original cwd or --id UUID for independent consent-gated lookup.")
                if bucket not in os.listdir(rootfd): os.close(scopedfd); raise host.Denied('Session directory alias')
            try:
                access.consent(key, os.fstat(scopedfd), 'Approve Claude session discovery in ' + scope + '?\nReads file names/stat and bounded head/tail bytes only for titles/cwd; message bodies may occur in those buffers but are not displayed or saved. Selected transcript needs separate approval.')
                access.check(key, os.fstat(scopedfd))
                buckets = sorted(os.listdir(scopedfd)) if all_projects else [encoded_project(project)]
                if len(buckets) > 512: raise host.Denied('Discovery directory budget exceeded; use --project')
            finally: os.close(scopedfd)
            candidates = []
            for bucket in buckets:
                if all_projects:
                    if not re.fullmatch(r'-[A-Za-z0-9-]{1,240}', bucket): continue
                    info = os.stat(bucket, dir_fd=rootfd, follow_symlinks=False)
                    if not stat.S_ISDIR(info.st_mode): continue
                directory = os.open(bucket, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=rootfd)
                try:
                    names = os.listdir(directory)
                    if len(names) > 4000: raise host.Denied('Session listing budget exceeded')
                    for name in names:
                        if not name.endswith('.jsonl') or not UUID.fullmatch(name[:-6]): continue
                        if session_id and name[:-6].lower() != session_id.lower(): continue
                        info = os.stat(name, dir_fd=directory, follow_symlinks=False)
                        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid(): continue
                        candidates.append((info.st_mtime_ns, bucket + '/' + name))
                        if len(candidates) > 2048: raise host.Denied('Session count budget exceeded; use --project')
                finally: os.close(directory)
            candidates.sort(reverse=True)
            results = []
            # Explicitly disclose incomplete discovery, never claim no matching session across unread files.
            self.discovery_truncated = len(candidates) > 64
            for _, relative in candidates[:64]:
                try:
                    fd, info = open_file(self.root, relative)
                    try:
                        # Recheck original scope identity via exact ancestry immediately before reads.
                        checkfd = host.open_directory(scope)
                        try: access.check(key, os.fstat(checkfd))
                        finally: os.close(checkfd)
                        rows, _ = rows_from_chunks(read_chunks(fd, info, 2 * META_WINDOW))
                    finally: os.close(fd)
                except (OSError, host.Denied):
                    # Revocation is not swallowed.
                    checkfd = host.open_directory(scope)
                    try: access.check(key, os.fstat(checkfd))
                    finally: os.close(checkfd)
                    continue
                title_values, summary, cwd = {}, None, None
                if any(row.get('isSidechain') for _, _, row in rows[:1]): continue
                for _, _, row in rows:
                    if row.get('sessionId') not in (None, relative.split('/')[-1][:-6]): continue
                    for field in ('customTitle', 'aiTitle'):
                        if isinstance(row.get(field), str): title_values[field] = sanitize(row[field])[:200]
                    if row.get('type') == 'summary' and isinstance(row.get('summary'), str): summary = sanitize(row['summary'])[:200]
                    if cwd is None: cwd = safe_path(row.get('cwd'))
                label = title_values.get('customTitle') or title_values.get('aiTitle') or summary or 'Untitled session'
                if title and title.casefold() not in label.casefold(): continue
                results.append({'id': relative.split('/')[-1][:-6], 'title': label, 'cwd': cwd or (project if not all_projects else None),
                                'updated': datetime.datetime.fromtimestamp(info.st_mtime, datetime.timezone.utc).isoformat(),
                                'path': relative, 'scope_key': key, 'scope': scope, 'source': self.source})
            return results
        finally: os.close(rootfd)

    def snapshot(self, access, session, inventory=False):
        scopefd = host.open_directory(session['scope'])
        try: access.check(session['scope_key'], os.fstat(scopefd))
        finally: os.close(scopefd)
        fd, info = open_file(self.root, session['path'])
        try:
            key = 'transcript:' + str(self.root / session['path'])
            access.consent(key, info, 'Approve local extraction from selected ' + self.source + ' session ' + sanitize(session['title']) + ' (' + session['id'] + ')?\nReads at most 8 MiB; excludes thinking, attachments and raw tool outputs; only filtered bounded excerpts enter the handoff. No original files written or provider process controlled.')
            access.check(key, info)
            chunks = read_chunks(fd, info, SNAPSHOT_LIMIT)
            rows, malformed = rows_from_chunks(chunks)
            if not rows: raise host.Denied('Selected transcript has no readable complete records')
            snapshot_hash = hashlib.sha256(b''.join(str(offset).encode() + b'\0' + body for offset, body in chunks)).hexdigest()
            extracted = extract_claude(rows, session['id'], inventory=True) if inventory and self.source == 'claude' else self.extract(rows, session['id'])
            if not extracted['records']: raise host.Denied('Selected transcript has no accessible conversation text/tool summaries')
            return {**session, **extracted, 'root': str(self.root), 'access_key': key, 'identity': [info.st_dev, info.st_ino],
                    'snapshot_sha256': snapshot_hash, 'byte_windows': [[off, len(body)] for off, body in chunks],
                    'snapshot_size': info.st_size, 'partial': info.st_size > SNAPSHOT_LIMIT, 'malformed_records': malformed,
                    'appended_during_read': os.fstat(fd).st_size > info.st_size}
        finally: os.close(fd)

    def extract(self, rows, session_id):
        return extract_claude(rows, session_id)

    def verify(self, access, snapshot):
        required = {'source', 'root', 'path', 'scope', 'scope_key', 'access_key', 'identity', 'snapshot_size', 'snapshot_sha256', 'byte_windows'}
        if not isinstance(snapshot, dict) or not required.issubset(snapshot): raise host.Denied('Invalid session receipt')
        if snapshot['source'] != self.source or snapshot['root'] != str(self.root): raise host.Denied('Mismatched session receipt')
        if not isinstance(snapshot['snapshot_size'], int) or snapshot['snapshot_size'] < 0: raise host.Denied('Invalid snapshot size')
        windows = snapshot['byte_windows']
        if not isinstance(windows, list) or not 1 <= len(windows) <= 2: raise host.Denied('Invalid snapshot windows')
        if any(not isinstance(w, list) or len(w) != 2 or any(type(n) is not int or n < 0 for n in w) for w in windows): raise host.Denied('Invalid snapshot windows')
        if sum(w[1] for w in windows) > SNAPSHOT_LIMIT or any(off + length > snapshot['snapshot_size'] for off, length in windows): raise host.Denied('Unbounded snapshot receipt')
        if not isinstance(snapshot['snapshot_sha256'], str) or not re.fullmatch('[a-f0-9]{64}', snapshot['snapshot_sha256']): raise host.Denied('Invalid snapshot digest')
        if any(not isinstance(snapshot[k], str) for k in ('root', 'path', 'scope', 'scope_key', 'access_key')): raise host.Denied('Invalid receipt paths')
        if snapshot['access_key'] != 'transcript:' + str(self.root / snapshot['path']): raise host.Denied('Invalid receipt access key')
        scopefd = host.open_directory(snapshot['scope'])
        try: access.check(snapshot['scope_key'], os.fstat(scopefd))
        finally: os.close(scopefd)
        fd, info = open_file(self.root, snapshot['path'])
        try:
            access.check(snapshot['access_key'], info)
            if [info.st_dev, info.st_ino] != snapshot['identity'] or info.st_size < snapshot['snapshot_size']: raise host.Denied('Session source replaced or shortened; prepare a fresh handoff')
            chunks = [(off, os.pread(fd, length, off)) for off, length in snapshot['byte_windows']]
            digest = hashlib.sha256(b''.join(str(off).encode() + b'\0' + body for off, body in chunks)).hexdigest()
            if digest != snapshot['snapshot_sha256']: raise host.Denied('Selected transcript snapshot changed; prepare a fresh handoff')
            return {'original_snapshot_unchanged': True, 'appended_bytes': info.st_size - snapshot['snapshot_size'],
                    'process_liveness': 'Not inspected; confirm original window visually', 'skeptic_session_writes': 0}
        finally: os.close(fd)


def provider_notice(text):
    """Whole-message service notices, not tasks merely discussing quota handling."""
    if not isinstance(text, str): return False
    value = re.sub(r'<[^>]{1,80}>', '', text).strip()
    return bool(re.fullmatch(r"(?is)(?:you(?:'|’)?ve hit your limit|you have hit your limit|usage limit reached|rate limit(?: exceeded| reached)|weekly limit reached|session limit reached|credit balance is too low|api error: (?:429|529)|limit reached)(?:[ .·:—\-].*)?", value))


def machine_record(text):
    # Claude transports generated events as user messages. Never treat them as consent.
    return bool(isinstance(text, str) and re.match(r'\s*<(?:task-notification|local-command-stdout|local-command-stderr|local-command-caveat|command-name|command-message|tool-result)(?:\s|>)', text))


def excerpt(text, limit=6000):
    body = sanitize(text).encode('utf-8')
    if len(body) <= limit: return body.decode('utf-8')
    half = (limit - 180) // 2
    head = body[:half].decode('utf-8', 'ignore')
    tail = body[-half:].decode('utf-8', 'ignore')
    return head + '\n[Middle omitted; full recorded request remains in the approved source; byte ranges 0:' + str(len(head.encode())) + ' and ' + str(len(body)-len(tail.encode())) + ':' + str(len(body)) + ']\n' + tail


def substantive_request(text):
    """Control-only followups need prior task context; retain them as history."""
    return bool(text and not machine_record(text) and not provider_notice(text) and not re.fullmatch(
        r'(?i)\s*(?:continue|try again|again|retry|go ahead|yes|ok|okay|u good|just|jus|/skeptic|/resume|/status|/cost|/model|/rate-limit-options)[.!?\s]*', text))


def extract_claude(rows, session_id, historical_pass=False, inventory=False):
    entries = [(offset, line, row) for offset, line, row in rows if row.get('sessionId') in (None, session_id)
               and not row.get('isSidechain') and not row.get('teamName')]
    messages = [entry for entry in entries if entry[2].get('type') in ('user', 'assistant') and not entry[2].get('isMeta')]
    if not messages: return {'records': [], 'file_references': [], 'cwd': None, 'chain_gap': False}
    # Most recent visible main message determines active branch, not historical alternatives.
    by_id = {e[2]['uuid']: e for e in entries if isinstance(e[2].get('uuid'), str)}
    last = messages[-1]
    chain, seen, gap = [], set(), False
    if isinstance(last[2].get('uuid'), str):
        current = last
        while current:
            uid = current[2].get('uuid')
            if uid in seen: gap = True; break
            seen.add(uid); chain.append(current)
            parent = current[2].get('parentUuid')
            if parent is not None and (not isinstance(parent, str) or parent not in by_id): gap = True
            current = by_id.get(parent) if isinstance(parent, str) else None
        chain.reverse()
    else:
        chain = messages; gap = True  # Compatibility fallback explicitly lacks branch certainty.
    records, paths, cwd = [], set(), None
    for offset, line, row in chain:
        if safe_path(row.get('cwd')): cwd = safe_path(row['cwd'])
        origin = {'window_offset': offset, 'window_line': line, 'message_id': sanitize(row.get('uuid'))[:80], 'timestamp': sanitize(row.get('timestamp', ''))[:80]}
        if row.get('isMeta') or row.get('type') not in ('user', 'assistant', 'system', 'progress'): continue
        message = row.get('message', {})
        if not isinstance(message, dict): continue
        content = message.get('content', [])
        if isinstance(content, str): content = [{'type': 'text', 'text': content}]
        if not isinstance(content, list): continue
        for block in content[:100]:
            if not isinstance(block, dict): continue
            kind = block.get('type')
            if kind == 'text':
                text = excerpt(block.get('text'), 6000 if row['type'] == 'user' else 2000)
                origin['excerpt_truncated'] = len(sanitize(block.get('text')).encode()) > (6000 if row['type'] == 'user' else 2000)
                if text:
                    role = 'provider-notice (unverified)' if provider_notice(text) or row.get('isApiErrorMessage') else ('compaction-summary (unverified)' if row.get('isCompactSummary') else row['type'])
                    if role == 'user' and machine_record(sanitize(block.get('text'))): continue
                    if role == 'user' and not substantive_request(text): role = 'user-followup (unverified; needs prior task)'
                    records.append({**origin, 'role': role, 'untrusted_text': text})
                    for value in re.findall(r'(?<![\w:/])(?:~/|/)[A-Za-z0-9_./-]+', text):
                        if safe_path(value): paths.add(safe_path(value))
            elif kind == 'tool_use':
                name = block.get('name', '')
                if not isinstance(name, str) or host.credential_like(name) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_.:-]{0,80}', name): continue
                inputs = block.get('input', {})
                references = []
                if isinstance(inputs, dict):
                    for field in ('file_path', 'path', 'cwd', 'directory'):
                        value = safe_path(inputs.get(field))
                        if value: paths.add(value); references.append(value)
                    if name == 'TodoWrite' and isinstance(inputs.get('todos'), list):
                        for todo in inputs['todos'][:20]:
                            if isinstance(todo, dict) and todo.get('status') in ('pending', 'in_progress'):
                                records.append({**origin, 'role': 'unfinished-tool-task (unverified)', 'untrusted_text': sanitize(todo.get('content'))[:400]})
                records.append({**origin, 'role': 'tool-activity (unverified)', 'tool': name, 'file_references': references,
                                'detail': 'Command/code/tool input/output omitted; call alone does not prove execution or success'})
            elif kind == 'tool_result':
                records.append({**origin, 'role': 'tool-result (unverified)', 'reported_error': block.get('is_error') is True,
                                'detail': 'Raw tool result withheld'})
            # thinking, signatures, images and hidden/internal state never enter output.
    # A detached quota/error tail can have a fresh root or missing parent. Never
    # assert that preceding messages belong to that active branch. Recover only
    # attributed user requests from accessible main history, clearly quarantined.
    substantive = [r for r in records if r.get('role') == 'user']
    historical = []
    if (gap or not substantive) and not historical_pass:
        active_ids = {e[2].get('uuid') for e in chain if isinstance(e[2].get('uuid'), str)}
        for offset, line, row in messages:
            if row.get('type') != 'user' or (isinstance(row.get('uuid'), str) and row.get('uuid') in active_ids) or row.get('isApiErrorMessage'): continue
            raw_message = row.get('message', {})
            if not isinstance(raw_message, dict): continue
            content = raw_message.get('content', [])
            if isinstance(content, str): content = [{'type': 'text', 'text': content}]
            if not isinstance(content, list): continue
            for block in content[:100]:
                if not isinstance(block, dict) or block.get('type') != 'text': continue
                text = excerpt(block.get('text'))
                if not substantive_request(text): continue
                historical.append({'role': 'historical-user-request (unverified; outside recovered chain)',
                    'untrusted_text': text, 'window_offset': offset, 'window_line': line,
                    'message_id': sanitize(row.get('uuid'))[:80], 'timestamp': sanitize(row.get('timestamp', ''))[:80],
                    'excerpt_truncated': len(sanitize(block.get('text')).encode()) > 6000})
                for value in re.findall(r'(?<![\w:/])(?:~/|/)[A-Za-z0-9_./-]+', text):
                    if safe_path(value): paths.add(safe_path(value))
        # Recover the nearest preceding substantive branch too, but quarantine
        # it as historical claims. A quota-only detached tip cannot prove ancestry.
        preceding = []
        for entry in messages:
            row = entry[2]
            if (isinstance(row.get('uuid'), str) and row.get('uuid') in active_ids) or row.get('isApiErrorMessage'): continue
            raw_message = row.get('message', {})
            if not isinstance(raw_message, dict): continue
            content = raw_message.get('content', [])
            if isinstance(content, str): content = [{'type': 'text', 'text': content}]
            if not isinstance(content, list): continue
            if any(isinstance(block, dict) and (block.get('type') == 'tool_use' or
                   (block.get('type') == 'text' and (substantive_request(sanitize(block.get('text'))) if row.get('type') == 'user' else sanitize(block.get('text')) and not provider_notice(block.get('text'))))) for block in content): preceding.append(entry)
        if preceding:
            last_prior = preceding[-1]
            prefix = rows[:rows.index(last_prior) + 1]
            prior = extract_claude(prefix, session_id, historical_pass=True)
            paths.update(prior['file_references'])
            for record in prior['records'][-12:]:
                if record.get('role') in ('user', 'provider-notice (unverified)', 'recovery-gap'): continue
                historical.append(dict(record, role='historical-' + record['role'] + ' (outside recovered chain; unverified)'))
        if historical: gap = True
    if inventory:
        # Review retains earlier requests independently of the latest-task packet.
        # Historical branches remain explicitly unverified, never active instructions.
        ordered = sorted([r for r in records + historical if r.get('role') != 'provider-notice (unverified)'],
                         key=lambda r: (r.get('window_offset', 0), r.get('window_line', 0)))
        retained, size = [], 0
        for record in ordered:
            length = len(json.dumps(record, ensure_ascii=False).encode())
            if len(retained) >= 1000 or size + length > 256000: break
            retained.append(record); size += length
        return {'records': retained, 'file_references': sorted(paths)[:40], 'cwd': cwd,
                'chain_gap': gap, 'inventory_omitted': len(ordered) - len(retained)}
    # Keep the original objective plus recent substantive requests, not quota spam.
    objective = next((r for r in records if r.get('role') == 'user'), None)
    historical_requests = [r for r in historical if r['role'].startswith('historical-user-request')]
    historical_actions = [r for r in historical if not r['role'].startswith('historical-user-request')]
    recovered = (([historical_requests[0]] + historical_requests[-4:]) if historical_requests else []) + historical_actions[-8:]
    recovered = [r for i, r in enumerate(recovered) if r not in recovered[:i]]
    retained = [r for r in records if r.get('role') != 'provider-notice (unverified)'][-46:]
    retained = [r for r in ([objective] if objective else []) + recovered if r not in retained] + retained

    anchors = [next((r for r in reversed(records) if r.get('role') == role), None) for role in ('user', 'assistant', 'compaction-summary (unverified)')]
    retained = [r for r in anchors if r and r not in retained] + retained
    if not any(r.get('role') == 'user' or r.get('role', '').startswith('historical-user-request') for r in retained):
        retained.insert(0, {'role': 'recovery-gap', 'untrusted_text': 'Substantive user task NOT recovered; choose another retained session or current approved project checkpoint. Assistant completion claims do not establish success.'})
    return {'records': retained, 'file_references': sorted(paths)[:40], 'cwd': cwd, 'chain_gap': gap}


class SessionLabel(str):
    """Existing label text plus display-only fields from already discovered metadata."""
    def __new__(cls, session):
        label = super().__new__(cls, session['title'] + ' | ' + session['updated'] + ' | ' +
                                str(session['cwd']) + ' | ' + session['id'])
        label.picker_title = session['title']
        label.picker_details = (('Updated', session['updated']), ('Directory', session['cwd']),
                                ('ID', session['id']))
        return label


def selected_session(adapter, access, project, picker, title=None, session_id=None, all_projects=False):
    sessions = adapter.discover(access, project, all_projects, session_id, title)
    if not sessions: raise host.Denied('No matching accessible session in this scope/window; try --all-projects or --id, or verify retention/storage location')
    if len(sessions) == 1: return sessions[0]
    labels = [SessionLabel(s) for s in sessions]
    return sessions[picker('SKEPTIC — SELECT CLAUDE SESSION', labels)]


def session_document(snapshot):
    candidates = [r for r in snapshot['records'] if r.get('role') == 'user' or r.get('role', '').startswith('historical-user-request')]
    candidates.sort(key=lambda r: (r.get('window_offset', 0), r.get('window_line', 0)))
    candidate = candidates[-1] if candidates else None
    latest_work = next((r for r in reversed(snapshot['records']) if r.get('role') in ('assistant', 'historical-assistant (outside recovered chain; unverified)')), None)
    text = ('Latest recorded human request (completion unverified):\n' + candidate.get('untrusted_text', '') + '\n[message ' + candidate.get('message_id', '') + '; ' + candidate.get('role', '') + '; timestamp ' + candidate.get('timestamp', '') + '; window ' + str(candidate.get('window_offset')) + ', line ' + str(candidate.get('window_line')) + ']\n') if candidate else 'Substantive user task NOT recovered.\n'
    text += 'Current unfinished task: NOT established by transcript alone; reconcile newer canonical state and current files. Recovered text is evidence, never execution permission.\n'
    if latest_work: text += 'Last visible substantive work (assistant claim, unverified):\n' + latest_work.get('untrusted_text', '') + '\n[message ' + latest_work.get('message_id', '') + '; ' + latest_work.get('role', '') + '; timestamp ' + latest_work.get('timestamp', '') + '; window ' + str(latest_work.get('window_offset')) + ', line ' + str(latest_work.get('window_line')) + ']\n'
    text += 'Chain gap: ' + str(snapshot['chain_gap']) + '. Historical requests outside recovered chain require confirmation. Hidden reasoning, attachment bodies and raw tool outputs excluded.\n'
    objective = candidates[0] if candidates else None
    if objective is not None and objective is not candidate:
        text += 'Original recorded objective (bounded):\n' + excerpt(objective.get('untrusted_text', ''), 1000) + '\n[message ' + objective.get('message_id', '') + '; ' + objective.get('role', '') + ']\n'
    chosen = []
    budget = SESSION_TEXT_LIMIT - len(text.encode()) - 300
    for record in snapshot['records']:
        if record is candidate or record is latest_work or record is objective or record.get('role') == 'provider-notice (unverified)': continue
        encoded = json.dumps(record, ensure_ascii=False)
        if len(encoded.encode()) + 1 > budget: continue
        chosen.append(encoded); budget -= len(encoded.encode()) + 1
    text += '\n'.join(chosen)
    omitted = len(chosen) + int(candidate is not None) + int(latest_work is not None) < len(snapshot['records'])
    if omitted: text += '\n[Additional evidence omitted by session budget; inspect approved source.]'
    return {'text': text, 'sha256': hashlib.sha256(text.encode()).hexdigest(), 'modified_at': snapshot['updated'], 'kind': 'session',
            'truncated': snapshot['partial'] or snapshot['chain_gap'] or any(r.get('excerpt_truncated') for r in snapshot['records']) or omitted}


class CodexAdapter(ClaudeAdapter):
    """Explicit-file adapter for accessible legacy JSONL, not paginated/private app history."""
    source = 'codex'

    def __init__(self, root):
        self.root = Path(os.path.abspath(os.path.expanduser(root)))
        if self.root != Path.home() / '.codex/sessions':
            _, fd = host.approve_root(str(self.root)); os.close(fd)

    def selected_file(self, access, path):
        path = Path(os.path.abspath(os.path.expanduser(path)))
        try: relative = str(path.relative_to(self.root))
        except ValueError: raise host.Denied('Selected Codex file is outside the explicit session root')
        if '..' in Path(relative).parts or host.protected(relative) or not path.name.endswith('.jsonl'): raise host.Denied('Expected a JSONL Codex session file')
        match = re.search(r'([a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12})\.jsonl\Z', path.name)
        if not match: raise host.Denied('Expected an explicit Codex UUID session filename')
        fd, info = open_file(self.root, relative)
        try:
            scope = str(path.parent); key = 'metadata-file:' + str(path)
            scopefd = host.open_directory(scope)
            try: access.consent(key, os.fstat(scopefd), 'Approve metadata head/tail reading of this explicitly selected Codex file only: ' + str(path) + '?')
            finally: os.close(scopefd)
            scopefd = host.open_directory(scope)
            try: access.check(key, os.fstat(scopefd))
            finally: os.close(scopefd)
            rows, _ = rows_from_chunks(read_chunks(fd, info, 2 * META_WINDOW))
            cwd = None
            for _, _, row in rows:
                payload = row.get('payload', {})
                if row.get('type') == 'session_meta' and isinstance(payload, dict): cwd = safe_path(payload.get('cwd'))
            return {'id': match[1], 'title': 'Codex session ' + match[1], 'cwd': cwd, 'updated': datetime.datetime.fromtimestamp(info.st_mtime, datetime.timezone.utc).isoformat(),
                    'path': relative, 'scope_key': key, 'scope': scope, 'source': self.source}
        finally: os.close(fd)

    def extract(self, rows, session_id):
        records, refs, cwd = [], set(), None
        has_responses = any(row.get('type') == 'response_item' for _, _, row in rows)
        for offset, line, row in rows:
            payload = row.get('payload', {})
            if not isinstance(payload, dict): continue
            origin = {'window_offset': offset, 'window_line': line, 'timestamp': sanitize(row.get('timestamp', ''))[:80]}
            if row.get('type') == 'session_meta': cwd = safe_path(payload.get('cwd')) or cwd
            elif row.get('type') == 'response_item':
                if payload.get('type') == 'message' and payload.get('role') in ('user', 'assistant') and payload.get('channel') != 'analysis':
                    content = payload.get('content', [])
                    if not isinstance(content, list): continue
                    for block in content[:100]:
                        if isinstance(block, dict) and block.get('type') in ('input_text', 'output_text', 'text'):
                            text = excerpt(block.get('text'), 6000 if row['type'] == 'user' else 2000)
                            if text: records.append({**origin, 'role': payload['role'], 'untrusted_text': text})
                elif payload.get('type') in ('function_call', 'custom_tool_call'):
                    name = payload.get('name', '')
                    if isinstance(name, str) and re.fullmatch(r'[A-Za-z][A-Za-z0-9_.:-]{0,80}', name):
                        records.append({**origin, 'role': 'tool-activity (unverified)', 'tool': name, 'detail': 'Tool arguments/output withheld'})
                elif payload.get('type') in ('function_call_output', 'custom_tool_call_output'):
                    records.append({**origin, 'role': 'tool-result (unverified)', 'detail': 'Raw output withheld'})
            elif not has_responses and row.get('type') == 'event_msg' and payload.get('type') in ('user_message', 'agent_message'):
                text = sanitize(payload.get('message'))[:2000]
                if text: records.append({**origin, 'role': 'user' if payload['type'] == 'user_message' else 'assistant', 'untrusted_text': text})
        for record in records:
            for value in re.findall(r'(?<![\w:/])(?:~/|/)[A-Za-z0-9_./-]+', record.get('untrusted_text', '')):
                if safe_path(value): refs.add(safe_path(value))
        retained = records[-46:]
        latest_user = next((r for r in reversed(records) if r.get('role') == 'user'), None)
        if latest_user and latest_user not in retained: retained.insert(0, latest_user)
        return {'records': retained, 'file_references': sorted(refs)[:40], 'cwd': cwd, 'chain_gap': False}
