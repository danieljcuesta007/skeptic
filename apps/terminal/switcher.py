"""Terminal switching engine. No HTTP dependency, document execution, or project writes."""
import argparse
import shlex
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import select
import shutil
import stat
import subprocess
import sys
import termios
import tty
import unicodedata
import urllib.request

LOCAL = Path(__file__).resolve().parents[1] / 'local'
sys.path.insert(0, str(LOCAL))
import app as host
from workspace import references

MAX_PACKET = 48000
RULES = ('PRINCIPLES.md', 'AGENTS.md', 'CLAUDE.md')


def clean(value):
    return ''.join(c if c >= ' ' and c != '\x7f' else ' ' for c in str(value))


def picker_line(value, columns):
    """Keep a row within the screen, including wide and combining characters."""
    result, width = [], 0
    for char in clean(value):
        cells = 0 if unicodedata.combining(char) else (2 if unicodedata.east_asian_width(char) in ('W', 'F') else 1)
        if width + cells > max(0, columns - 1): break
        result.append(char); width += cells
    return ''.join(result)


def picker_wrap(value, columns):
    """Wrap display text by terminal cells, preferring word boundaries."""
    remaining, lines = clean(value), []
    while remaining:
        line = picker_line(remaining, columns)
        if not line: break  # Even one character may not fit in a tiny terminal.
        if len(line) < len(remaining) and ' ' in line and line.rfind(' ') > 0:
            line = line[:line.rfind(' ')]
        lines.append(line)
        remaining = remaining[len(line):].lstrip()
    return lines


def choose(title, options, stream=None, output=None, on_enter=None):
    stream, output = stream or sys.stdin, output or sys.stdout
    if not options: raise host.Denied('No choices available')
    if not stream.isatty() or not output.isatty():
        raise host.Denied('Picker needs a terminal. Use continue --with codex or claude.')
    fd, old, index = stream.fileno(), termios.tcgetattr(stream.fileno()), 0
    top, rendered_size, redraw = 0, None, True
    try:
        tty.setcbreak(fd)
        output.write('\033[?1049h\033[?25l')
        while True:
            try: columns, rows = os.get_terminal_size(output.fileno())
            except OSError: columns, rows = 80, 24
            columns, rows = columns or 80, rows or 24
            if redraw or rendered_size != (columns, rows):
                help_line = ('Use ↑ ↓ to select, Enter to continue. Esc/q cancels.' if columns >= 51
                             else '↑/↓ select · Enter · Esc/q')
                header = [title, help_line, f'{index + 1}/{len(options)}'][:max(0, rows - 2)]
                selected = options[index]
                selected_title = getattr(selected, 'picker_title', str(selected))
                details = getattr(selected, 'picker_details', ())
                detail_lines = []
                if details or picker_line(selected_title, columns - 2) != clean(selected_title):
                    detail_lines = picker_wrap('Selected: ' + selected_title, columns)
                    for name, value in details:
                        detail_lines.extend(picker_wrap(name + ': ' + str(value), columns))
                available = max(1, rows - len(header) - 1)
                # Share space with details, but use spare space when the list is short.
                list_minimum = min(len(options), max(1, available // 2))
                detail_lines = detail_lines[:available - list_minimum]
                capacity = available - len(detail_lines)
                top = min(top, max(0, len(options) - capacity))
                if index < top: top = index
                elif index >= top + capacity: top = index - capacity + 1
                lines = header + [('› ' if n == index else '  ') +
                                  getattr(options[n], 'picker_title', str(options[n]))
                                  for n in range(top, min(len(options), top + capacity))] + detail_lines
                # Always anchor at the top after terminal reflow; never emit enough
                # rows/columns to scroll or wrap. No padding before selected details.
                output.write('\033[H\033[J' + '\r\n'.join(picker_line(line, columns) for line in lines))
                output.flush()
                rendered_size, redraw = (columns, rows), False
            # A bounded wait notices SIGWINCH-driven size changes without consuming a
            # key or replacing the caller's process-wide signal handlers.
            if not select.select([fd], [], [], .1)[0]: continue
            key = os.read(fd, 1)
            if key == b'\x1b':
                while len(key) < 3 and select.select([fd], [], [], .12)[0]:
                    key += os.read(fd, 3 - len(key))
                if key == b'\x1b': raise KeyboardInterrupt
            if key in (b'\x1b[A', b'\x1bOA', b'k'): index = (index - 1) % len(options)
            elif key in (b'\x1b[B', b'\x1bOB', b'j'): index = (index + 1) % len(options)
            elif key in (b'\r', b'\n'):
                # Multi-selection updates labels in this same terminal loop;
                # cursor, viewport and terminal mode survive each toggle.
                if on_enter is None or on_enter(index): return index
            elif key in (b'q', b'\x03', b'\x04', b''): raise KeyboardInterrupt
            redraw = True
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        output.write('\033[?25h\033[?1049l'); output.flush()


def providers(which=shutil.which, fetch=None):
    result = [{'id': p, 'label': label, 'executable': which(p), 'local': False,
               'availability': 'CLI installed; authentication/quota/model unknown' if which(p) else 'CLI missing'}
              for p, label in [('claude', 'Claude Code'), ('codex', 'Codex'), ('hermes', 'Hermes')]]
    # Only fixed loopback read-only endpoints. Never honor proxy/remote URL environment variables.
    def local_fetch(url):
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        with opener.open(url, timeout=.4) as response:
            body = response.read(65537)
            if len(body) > 65536: raise ValueError('Local model list too large')
            return json.loads(body)
    fetch = fetch or local_fetch
    if not result[1]['executable']: return result
    for provider, url, field in [('ollama', 'http://127.0.0.1:11434/api/tags', 'models'),
                                 ('lmstudio', 'http://127.0.0.1:1234/v1/models', 'data')]:
        try:
            data = fetch(url)
            if not isinstance(data, dict) or not isinstance(data.get(field, []), list): continue
            for model in data.get(field, [])[:30]:
                if not isinstance(model, dict): continue
                name = model.get('name' if provider == 'ollama' else 'id', '')
                if not isinstance(name, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,199}', name): continue
                result.append({'id': provider + ':' + name, 'label': provider + ' / ' + name,
                               'executable': result[1]['executable'], 'local': True, 'model': name,
                               'provider': provider, 'availability': 'Reported by running loopback provider; compatibility unverified'})
        except (OSError, ValueError, KeyError, TypeError): pass
    return result


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs): return None


class State:
    """Separate CLI consent; dashboard registrations never imply durable CLI permission."""
    def __init__(self, directory):
        self.registry = host.Registry(directory)
        self.fd = self.registry.statefd
        self.settings = self.read('settings.json', {'grants': {}, 'mappings': {}, 'recent': [], 'analytics': False})
        if not isinstance(self.settings, dict) or set(self.settings) != {'grants', 'mappings', 'recent', 'analytics'}:
            raise host.Denied('Invalid CLI configuration')
        if not isinstance(self.settings['grants'], dict) or not isinstance(self.settings['mappings'], dict) or not isinstance(self.settings['recent'], list) or not isinstance(self.settings['analytics'], bool):
            raise host.Denied('Invalid CLI configuration')
        for path, grant in self.settings['grants'].items():
            if not isinstance(path, str) or not isinstance(grant, dict) or set(grant) != {'kind', 'identity'} or grant['kind'] not in ('vault', 'repository') or not isinstance(grant['identity'], list) or len(grant['identity']) != 2 or any(not isinstance(n, int) for n in grant['identity']):
                raise host.Denied('Invalid saved grant')
        if any(not isinstance(k, str) or not isinstance(v, str) for k, v in self.settings['mappings'].items()) or any(not isinstance(v, str) for v in self.settings['recent']):
            raise host.Denied('Invalid saved mapping or provider')

    def read(self, name, default):
        try: fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=self.fd)
        except FileNotFoundError: return default
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600 or info.st_size > 65536:
                raise host.Denied('Unsafe CLI state')
            return json.loads(os.read(fd, 65537))
        finally: os.close(fd)

    def save(self):
        payload = json.dumps(self.settings).encode()
        if len(payload) > 65536: raise host.Denied('CLI configuration size limit')
        name = 'pending-' + os.urandom(16).hex()
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=self.fd)
        try:
            with os.fdopen(fd, 'wb') as out: out.write(payload); out.flush(); os.fsync(out.fileno())
            os.rename(name, 'settings.json', src_dir_fd=self.fd, dst_dir_fd=self.fd)
        finally:
            try: os.unlink(name, dir_fd=self.fd)
            except FileNotFoundError: pass

    def grant(self, path, kind, ask=input):
        path, fd = host.approve_root(str(path), vault=kind == 'vault')
        info = os.fstat(fd)
        signature = host.durable_identity(info)
        old = self.settings['grants'].get(path)
        if old and old.get('kind') == kind and host.identity_matches(old.get('identity'), info, legacy=True):
            if old['identity'] != signature:  # pre-durable grant: upgrade in place, no prompt
                self.settings['grants'][path] = {'kind': kind, 'identity': signature}
                self.save()
        else:
            if getattr(self, 'no_new_grants', False):
                os.close(fd); raise host.Denied('Approved scope changed/revoked; refresh checkpoint manually')
            if not sys.stdin.isatty():
                os.close(fd); raise host.Denied('Approval required. Run skeptic in your Terminal.')
            print('Approve persistent read-only access to ' + clean(path) + '?')
            print('Vault: project STATUS matching, governing files, confirmed project and exact linked notes only.\nRevoke with: skeptic permissions revoke PATH')
            if ask('Type approve: ').strip() != 'approve':
                os.close(fd); raise host.Denied('Read permission declined')
            self.settings['grants'][path] = {'kind': kind, 'identity': signature}
            self.save()
        return path, fd

    def event(self, event, provider, code=None):
        if not self.settings['analytics']: return
        try:
            fd = os.open('activity.jsonl', os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=self.fd)
            try:
                info = os.fstat(fd)
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600 or info.st_size > 1_000_000: return
                row = {'time': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'event': event, 'provider': provider, 'exit_code': code}
                os.write(fd, (json.dumps(row) + '\n').encode())
            finally: os.close(fd)
        except OSError: pass  # Optional analytics can never block continuation.

    def close(self): self.registry.close()


def repository(cwd):
    """Filesystem primary signal; no Git execution until repository read approval."""
    cwd = Path(os.path.abspath(cwd))
    fd = host.open_directory(str(cwd)); os.close(fd)
    for parent in (cwd, *cwd.parents):
        if parent == Path.home(): break
        try:
            info = (parent / '.git').lstat()
            if stat.S_ISDIR(info.st_mode): return str(parent)
            if stat.S_ISREG(info.st_mode): raise host.Denied('Linked worktree/submodule Git pointers require separately approved metadata; unsupported today')
            raise host.Denied('Unsafe Git metadata')
        except FileNotFoundError: pass
    return str(cwd)


def git_metadata_safe(fd, budget=None, prefix=''):
    """Bounded metadata inspection; Git must not follow out-of-scope links/alternates."""
    if prefix.count('/') > 16: return False
    budget = budget if budget is not None else [20000]
    names = os.listdir(fd)
    budget[0] -= len(names)
    if budget[0] < 0: return False
    for name in names:
        rel = prefix + name
        if rel == 'objects/info/alternates': return False
        info = os.stat(name, dir_fd=fd, follow_symlinks=False)
        if stat.S_ISDIR(info.st_mode):
            child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            try:
                if not git_metadata_safe(child, budget, rel + '/'): return False
            finally: os.close(child)
        elif not stat.S_ISREG(info.st_mode) or info.st_nlink != 1: return False
    return True


def git_state(root, run=subprocess.run):
    # Refuse Git configurations capable of loading extra files or running filters.
    # Read exact local config without following links before invoking Git.
    if not (Path(root) / '.git').is_dir():
        return {'branch': None, 'head': None, 'changes': None}
    gitfd = host.open_directory(str(Path(root) / '.git'))
    try:
        if not git_metadata_safe(gitfd):
            return {'branch': None, 'head': None, 'changes': None, 'limitation': 'Git metadata links, alternates or budget limit; process inspection withheld'}
        for config_name in ('config', 'config.worktree'):
            try: configfd = os.open(config_name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=gitfd)
            except FileNotFoundError: configfd = None
            if configfd is not None:
                try:
                    info = os.fstat(configfd)
                    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > 64000: raise host.Denied('Unsafe Git config')
                    config = os.read(configfd, 64001).decode('utf-8')
                    if re.search(r'(?im)^\s*\[\s*(?:filter|include|includeIf)\b', config):
                        return {'branch': None, 'head': None, 'changes': None, 'limitation': 'Git filter/include config present; process observation withheld to avoid commands or out-of-scope reads'}
                finally: os.close(configfd)
    finally: os.close(gitfd)
    # Isolate global/system config, disable fsmonitor, optional locks and external helpers.
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull, GIT_OPTIONAL_LOCKS='0', GIT_TERMINAL_PROMPT='0')
    def git(args):
        p = run(['git', '-c', 'core.worktree=' + root, '-c', 'core.bare=false', '-c', 'core.fsmonitor=false', '-c', 'core.untrackedCache=false', '-c', 'core.hooksPath=/dev/null', *args],
                cwd=root, env=env, capture_output=True, text=True, timeout=10, check=False)
        if p.returncode: return None
        if len(p.stdout.encode()) > 64000: return 'Output withheld: Git observation exceeds limit'
        return p.stdout.rstrip()
    changes = git(['status', '--porcelain=v1', '--untracked-files=all'])
    if changes:
        changes = '\n'.join(line if not line[3:].startswith(chr(34)) and ' -> ' not in line[3:] and not host.protected(line[3:]) else line[:2] + ' [protected filename withheld; quoted/renamed names also withheld]' for line in changes.splitlines())
    return {'branch': git(['symbolic-ref', '--short', 'HEAD']), 'head': git(['rev-parse', '--verify', 'HEAD']), 'changes': changes}


def safe_docs(root, fd, paths):
    with host.ScopedEngine(root, fd, [], {'files': 2048, 'entries': 12000, 'bytes': 2_000_000}) as engine:
        engine.paths = lambda: iter(sorted(set(paths)))
        return host.summarize(engine)


def vault_candidates(root, fd, repo):
    # Enumerate only canonical project directory entries; no recursive vault scan.
    statuses = []
    try:
        projectfd = os.open('03 Projects', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
    except FileNotFoundError: return [], {}
    try:
        names = os.listdir(projectfd)
        if len(names) > 256: raise host.Denied('Too many canonical projects; approve a project folder instead')
        for name in sorted(names):
            if name.startswith('.') or name.startswith('_') or host.protected(name): continue
            info = os.stat(name, dir_fd=projectfd, follow_symlinks=False)
            if stat.S_ISDIR(info.st_mode): statuses.append('03 Projects/' + name + '/STATUS.md')
    finally: os.close(projectfd)
    snapshot = safe_docs(root, fd, statuses)
    matches = [str(Path(p).parent) for p, doc in snapshot['documents'].items() if repo in references(doc['text'])]
    return matches, snapshot['documents']


def assemble(state, cwd, vault, task='', picker=choose, session=None, target=None):
    conversation_only = bool(session and session.get("conversation_only"))
    home_session = session is not None and (Path(cwd) == Path.home() or conversation_only)
    project_gap = None
    try: repo = str(cwd) if home_session else repository(cwd)
    except (host.Denied, OSError):
        if session is None: raise
        repo = str(cwd); home_session = True
        project_gap = "Project could not be safely verified; conversation-based recovery only. Project/Git reads withheld. Choose --cwd PATH or --conversation-only."
    rfd = None
    if not home_session: repo, rfd = state.grant(repo, 'repository')
    vfd = None
    try:
        try: git = {'branch': None, 'head': None, 'changes': None, 'limitation': project_gap or ('Conversation-only recovery: project/Git reads withheld' if conversation_only else 'Home-started session: home files/Git not scanned')} if home_session else git_state(repo)
        except (OSError, ValueError, subprocess.TimeoutExpired, host.Denied):
            git = {'branch': None, 'head': None, 'changes': None, 'limitation': 'Git observation unavailable; inspect local state before acting'}
        if git.get('changes') and len(git['changes']) > 4000:
            git['changes'] = git['changes'][:4000] + '\n[Git listing truncated; inspect full status locally]'
        instructions = list(RULES) + ['README.md', 'STATUS.md']
        # Subdirectory-specific instructions, bounded to current repository.
        relative = Path(cwd).relative_to(repo)
        for parent in (relative, *relative.parents):
            instructions.extend(str(parent / name) for name in RULES)
        snapshot = {'documents': {}} if home_session else safe_docs(repo, rfd, instructions)
        docs = {str(Path(repo) / p): d for p, d in snapshot['documents'].items()}
        knowledge, checkpoint = None, None
        gaps = ['Unsaved conversation/current request and hidden reasoning were not recovered. No transcript scraping.',
                'Git facts are observed; documented progress is unverified. No remote freshness check.',
                'Ancestor instructions above the repository approval and unresolved/out-of-scope links were not read.']
        vault = os.path.expanduser(vault)
        if not conversation_only and Path(vault).is_dir():
            vault, vfd = state.grant(vault, 'vault')
            matches, candidates = vault_candidates(vault, vfd, repo)
            mapping_key = ('session-knowledge:' + session['source_key'] + ':' + repo) if session else repo
            mapped = state.settings['mappings'].get(mapping_key)
            eligible = [str(Path(p).parent) for p in candidates]
            if mapped in eligible: matches = [mapped]
            if len(matches) > 1 and getattr(state, 'no_new_grants', False): matches = []
            if len(matches) > 1:
                matches = [matches[picker('Confirm project knowledge', matches)]]
            if not matches:
                # No guessed association. Offer explicit confirmation of an existing checkpoint.
                if eligible and sys.stdin.isatty() and not getattr(state, 'no_new_grants', False):
                    options = ['Continue with session only' if home_session else 'Continue with repository only'] + sorted(eligible)
                    selected = picker('No exact repository reference. Confirm a mapping or continue without knowledge.', options)
                    if selected: matches = [options[selected]]
                if not matches: gaps.append('No confirmed vault association; project knowledge missing.')
            if matches:
                folder = matches[0]
                state.settings['mappings'][mapping_key] = folder; state.save()
                knowledge = str(Path(vault) / folder)
                # Enumerate only the confirmed project; retain safe descriptor reads.
                host_fd = host.open_directory(knowledge)
                try:
                    with host.ScopedEngine(knowledge, host_fd, []) as project_engine:
                        paths = [str(Path(folder) / p) for p in project_engine.paths()]
                finally: os.close(host_fd)
                paths += list(RULES) + ['USER.md', 'SOUL.md', 'IDENTITY.md', 'BRAIN-WORKFLOW.md']
                for parent in (Path(folder), *Path(folder).parents): paths.extend(str(parent / name) for name in RULES)
                selected = safe_docs(vault, vfd, paths)
                # One hop, exact links only. No basename search or outside-root expansion.
                linked = []
                for p, doc in selected['documents'].items():
                    targets = re.findall(r'\[[^\]]*\]\(([^)]+\.md)(?:#[^)]*)?\)', doc['text']) + re.findall(r'\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]', doc['text'])
                    for target in targets[:20]:
                        if target.startswith(('/', '~')) or '://' in target: continue
                        for candidate in (str(Path(p).parent / target), target):
                            candidate = os.path.normpath(candidate)
                            if '..' in Path(candidate).parts: continue
                            if not candidate.endswith('.md'): candidate += '.md'
                            linked.append(candidate)
                if linked:
                    extras = safe_docs(vault, vfd, linked[:60])
                    selected['documents'].update(extras['documents'])
                docs.update({str(Path(vault) / p): d for p, d in selected['documents'].items()})
                status = str(Path(knowledge) / 'STATUS.md')
                checkpoint = status if status in docs else None
        else: gaps.append('Knowledge retrieval skipped: conversation-only recovery.' if conversation_only else 'Vault directory unavailable; repository-only context.')
        if project_gap: gaps.append(project_gap)
        if not checkpoint:
            candidates = [p for p in docs if Path(p).name == 'STATUS.md']
            checkpoint = max(candidates, key=lambda p: docs[p]['modified_at']) if candidates else None
        handoffs = []
        if checkpoint:
            handoffs = host.sections(docs[checkpoint]['text'], {'handoff'})
        if not handoffs: gaps.append('No canonical Handoff section; accessible handoff-named sources included when present.')
        summary = {'project': Path(repo).name, 'cwd': str(cwd), 'repository': repo, 'knowledge': knowledge,
                   'checkpoint': checkpoint, 'git': git, 'gaps': gaps}
        if session and not conversation_only:
            extras = session.get('repositories', [])
            if len(extras) > 4: raise host.Denied('At most four additional repositories')
            summary['additional_repositories'] = []
            for candidate in extras:
                import sessions as history
                exact = history.safe_path(candidate)
                if not exact: raise host.Denied('Invalid/protected additional repository')
                try: additional = repository(exact)
                except (host.Denied, OSError):
                    summary['gaps'].append('Additional repository could not be verified; reads withheld: ' + exact)
                    continue
                additional, extra_fd = state.grant(additional, 'repository')
                try:
                    extra = safe_docs(additional, extra_fd, list(RULES) + ['README.md', 'STATUS.md'])
                    docs.update({str(Path(additional) / p): d for p, d in extra['documents'].items()})
                    try: observed = git_state(additional)
                    except (OSError, ValueError, host.Denied, subprocess.TimeoutExpired): observed = {'head': None, 'limitation': 'Git unavailable'}
                    if observed.get('changes'): observed['changes'] = history.sanitize(observed['changes'][:4000])
                    summary['additional_repositories'].append({'root': additional, 'git': observed})
                finally: os.close(extra_fd)
        if session:
            summary['session'] = {k: v for k, v in session.items() if k not in ('document', 'records')}
            summary['gaps'][0] = 'Only approved accessible transcript excerpts recovered; unsaved/in-flight history and hidden reasoning remain inaccessible.'
            docs[session['source_key']] = session['document']
        import continuity
        if len(task) > 2000: raise host.Denied('Task exceeds 2000 characters')
        filtered_task = continuity.history.sanitize(task)
        if filtered_task != task: summary['gaps'].append('Sensitive request text withheld; review the filtered handoff before proceeding.')
        task = filtered_task
        if git.get('changes'): git['changes'] = continuity.history.sanitize(git['changes'])
        filtered = 0
        for path, doc in list(docs.items()):
            safe = continuity.history.sanitize(doc['text'])
            if safe != doc['text']:
                docs[path] = dict(doc, text=safe, truncated=True)
                filtered += 1
        if filtered: summary['gaps'].append('Sensitive/protected lines omitted from outgoing context; review the filtered handoff. Source hashes refer to original accessible files.')
        state.observation, state.current_claims = continuity.observe(state, summary, docs)
        if target: summary['catchup'] = continuity.Index(state).briefing(state.observation, state.current_claims, target)
        packet = context_packet(summary, docs, task)
        return summary, packet
    finally:
        if rfd is not None: os.close(rfd)
        if vfd is not None: os.close(vfd)


context_packet = host.grounded_packet


def select_provider(state, requested=None):
    models = providers()
    if requested:
        model = next((m for m in models if m['id'] == requested), None)
        if not model or not model['executable']: raise host.Denied('Provider unavailable; run skeptic models')
        return model
    models.sort(key=lambda m: state.settings['recent'].index(m['id']) if m['id'] in state.settings['recent'] else 100)
    model = models[choose('SKEPTIC — SWITCH MODEL', [m['label'] + ' — ' + m['availability'] for m in models])]
    if not model['executable']: raise host.Denied('Provider CLI missing; install it separately')
    return model


def review_summary(summary, evidence):
    """Human view of the same immutable packet inputs, never a separate handoff."""
    import sessions as history
    git = summary.get('git', {})
    rows = (git.get('changes') or '').splitlines()
    print('Project: ' + str(summary.get('cwd', summary.get('repository'))) + '\nKnowledge: ' + str(summary.get('knowledge')))
    print('Git: ' + str(git.get('branch')) + ' / ' + str(git.get('head'))[:12] + '; ' + str(len(rows)) + ' listed local changes (listing may be bounded). Preserve all work.')
    print(history.excerpt(evidence['document']['text'].split('Chain gap:')[0], 1800))
    print('Chain gap: ' + str(evidence['chain_gap']) + '; snapshot partial: ' + str(evidence['partial']) + '; excerpt truncated: ' + str(evidence['document']['truncated']))
    print('Source: ' + evidence['source_key'] + '\nCurrent unfinished status requires reconciliation. Detailed evidence includes permissions, sources and omissions.')


def session_destination(state, snapshot, explicit=None, confirm=False):
    import sessions as history
    if explicit:
        path = history.safe_path(explicit)
        if not path: raise host.Denied('Invalid/protected destination directory')
        return path
    mapping_key = 'session-destination:' + snapshot['root'] + '/' + snapshot['path'] + ':' + str(snapshot['identity'])
    mapped = state.settings['mappings'].get(mapping_key)
    if mapped and history.safe_path(mapped) and not confirm: return mapped
    cwd = history.safe_path(snapshot.get('cwd'))
    if cwd is None:
        if not confirm: raise host.Denied('Session working directory is unavailable; use --cwd with the approved destination')
        cwd = history.safe_path(input('Recorded directory unavailable. Confirm actual project/worktree folder: ').strip())
        if not cwd: raise host.Denied('Invalid/protected project folder')
    candidates = [cwd]
    if confirm:
        for value in (mapped, os.getcwd()):
            if history.safe_path(value) and value not in candidates: candidates.append(value)
    if Path(cwd) == Path.home() or confirm:
        developer = Path.home() / 'Developer'
        for ref in snapshot['file_references']:
            value = Path(ref)
            try:
                parts = value.relative_to(developer).parts
                candidate = str(developer / parts[0]) if parts else str(value.parent)
            except ValueError: candidate = str(value.parent)
            if history.safe_path(candidate) and candidate not in candidates and Path(candidate) != Path('/'):
                candidates.append(candidate)
        if len(candidates) > 1 or confirm:
            candidates = candidates[:12]
            labels = [p + (' — session cwd' if p == cwd else ' — candidate; not verified') for p in candidates]
            if confirm: labels.append('Choose another project folder…')
            choice = choose('Confirm project destination (references are unverified hints)', labels)
            if choice == len(candidates):
                cwd = history.safe_path(input('Project folder: ').strip())
                if not cwd: raise host.Denied('Invalid/protected project folder')
            else: cwd = candidates[choice]
    state.settings['mappings'][mapping_key] = cwd; state.save()
    return cwd


def session_cli(args, state):
    import sessions as history
    access = history.Access(state, force_prompt=getattr(args, 'fresh_session_approval', False))
    if args.command == 'sessions' and args.action == 'revoke':
        access.revoke(); print('Session discovery/extraction approvals revoked. Original sessions untouched.'); return 0
    if args.command == 'sessions' and args.action == 'permissions':
        print(json.dumps(access.data['grants'], indent=2)); return 0
    action = args.action or ('list' if args.command == 'sessions' else 'continue')
    if args.command == 'session' and action == 'verify':
        receipt = state.read('session-receipt.json', None)
        if not receipt: raise host.Denied('No selected-session receipt; preview or launch a session first')
        if not isinstance(receipt, dict) or receipt.get('source') not in ('claude', 'codex') or not isinstance(receipt.get('root'), str): raise host.Denied('Invalid session receipt')
        adapter_class = history.ClaudeAdapter if receipt['source'] == 'claude' else history.CodexAdapter
        print(json.dumps(adapter_class(receipt['root']).verify(access, receipt), indent=2)); return 0
    root = args.session_root or str(Path.home() / ('.claude/projects' if args.source == 'claude' else '.codex/sessions'))
    adapter = history.ClaudeAdapter(root) if args.source == 'claude' else history.CodexAdapter(root)
    project = history.safe_path(args.project)
    if not project: raise host.Denied('Invalid/protected session project scope')
    if args.command == 'sessions' and action == 'review':
        if args.source != 'claude': raise host.Denied('Multi-session review supports Claude only')
        import session_review
        return session_review.run(args, state, adapter, access, project)
    if args.command == 'sessions' and action == 'open':
        if args.source != 'claude': raise host.Denied('Open Terminal recovery supports Claude only')
        import open_sessions
        return open_sessions.run(args, state, adapter, access, project)
    if args.source == 'codex':
        if not args.session_file: raise host.Denied('Codex reverse adapter needs --session-file PATH (accessible legacy JSONL only); no private-history scan')
        session = adapter.selected_file(access, args.session_file)
        if args.command == 'sessions': print(json.dumps([session], indent=2)); return 0
    elif args.command == 'sessions':
        if action not in ('list', 'pick'): raise host.Denied('Use sessions [list|pick|permissions|revoke]')
        if action == 'pick':
            session = history.selected_session(adapter, access, project, choose, args.title, args.session_id, args.all_projects)
            print(json.dumps(session, indent=2))
        else:
            items = adapter.discover(access, project, args.all_projects, args.session_id, args.title)
            print(json.dumps(items, indent=2, ensure_ascii=False))
        if getattr(adapter, 'discovery_truncated', False): print('Discovery limited to 64 most recent files; older sessions were not inspected. Narrow scope or use --id.')
        return 0
    else:
        session = history.selected_session(adapter, access, project, choose, args.title, args.session_id, args.all_projects)
        if getattr(adapter, 'discovery_truncated', False): print('Discovery inspected only the 64 most recent candidate files.')
    if action not in ('handoff', 'preview', 'continue'): raise host.Denied('Use session handoff|preview|continue|verify')
    snapshot = adapter.snapshot(access, session)
    cwd = session_destination(state, snapshot, args.cwd, getattr(args, "interactive_switch", False))
    source_key = str(Path(snapshot['root']) / snapshot['path'])
    evidence = {k: snapshot[k] for k in ('id', 'title', 'source', 'snapshot_sha256', 'byte_windows', 'partial', 'malformed_records', 'chain_gap', 'appended_during_read')}
    evidence.update(source_key=source_key, document=history.session_document(snapshot), conversation_only=getattr(args, "conversation_only", False), original_cwd=snapshot.get("cwd"), storage_path=source_key, repositories=getattr(args, "repo", []))
    task = history.sanitize(args.task) or 'Continue the selected session’s latest unfinished user request using the accessible evidence; reconcile canonical instructions, current files and permissions before acting. Keep the original provider session intact.'
    summary, packet = assemble(state, cwd, args.vault, task, session=evidence, target=args.provider)
    import continuity
    continuity.warn(continuity.Index(state).record(state.observation, args.source, 'selected_source_checkpoint', seed=True))
    summary['original_session'] = 'Left open and unmodified by Skeptic; no signals, resume, fork or deletion'
    # Receipt contains source hashes/offsets/identity only, never conversation text.
    receipt_fields = ('source', 'root', 'path', 'scope', 'scope_key', 'access_key', 'identity', 'snapshot_size', 'snapshot_sha256', 'byte_windows')
    receipt = {k: snapshot[k] for k in receipt_fields}
    history.atomic_json(state, 'session-receipt.json', receipt)
    if action in ('handoff', 'preview'):
        print('PROPOSED SESSION HANDOFF — selected original remains open; no cloud launch.\n' + packet)
        return 0
    return launch_recovery(args, state, adapter, access, snapshot, cwd, task, evidence, summary, packet)


def launch_recovery(args, state, adapter, access, snapshot, cwd, task, evidence, summary, packet):
    if not sys.stdin.isatty() or not sys.stdout.isatty(): raise host.Denied('Launch requires a second interactive Terminal; original session stays open')
    model = requested_model(select_provider(state, args.provider), getattr(args, 'model', None))
    print('Selected provider: ' + clean(model['label']) + '. Original session remains open. Host approvals still apply.', flush=True)
    state.settings = state.read('settings.json', {})
    # Re-read granted knowledge and recheck transcript consent/snapshot immediately before launch.
    summary, packet = assemble(state, cwd, args.vault, task, session=evidence, target=model['id'])
    if adapter.verify(access, snapshot)['appended_bytes']: raise host.Denied('Source appended; refresh the review before launch')
    state.settings['recent'] = [model['id']] + [p for p in state.settings['recent'] if p != model['id']][:9]
    print('REVIEW SELECTED SESSION HANDOFF — no provider has launched yet.', flush=True)
    review_summary(summary, evidence)
    print('COMPLETE FILTERED RECOVERY PACKET\n' + packet, flush=True)
    print('Outgoing evidence SHA-256: ' + hashlib.sha256(packet.encode()).hexdigest())
    print('A detached or quota-limited source may still have a tool process writing or automatically resume when availability returns. Check background tools AND queued/automatic continuation. Skeptic cannot prove unmanaged process quiescence. If any agent may write this project, cancel and choose an existing isolated worktree with --cwd, or prepare a handoff only.')
    if input('After checking the original Claude window and other project writers, type project-clear to continue: ').strip() != 'project-clear':
        raise host.Denied('Project writer check declined; no provider launched')
    while True:
        answer = input('Type send to approve this exact outgoing packet, evidence to inspect it, or anything else to cancel: ').strip()
        if answer == 'evidence': print(packet, flush=True); continue
        if answer != 'send': raise host.Denied('Handoff sending declined')
        break
    if adapter.verify(access, snapshot)['appended_bytes']: raise host.Denied('Source appended; refresh the review before launch')
    state.settings = state.read('settings.json', {})
    state.no_new_grants = True
    try: _, refreshed = assemble(state, cwd, args.vault, task, session=evidence, target=model['id'])
    finally: state.no_new_grants = False
    if refreshed != packet: raise host.Denied('Approved context changed during review; prepare/review a fresh handoff')
    state.settings['recent'] = [model['id']] + [p for p in state.settings['recent'] if p != model['id']][:9]
    state.save(); state.event('launch_started', model['id'])
    # Conversation-only previews do not grant project reads, but launch still
    # requires an exact, non-symlink directory; never follow a saved alias.
    if getattr(args, 'open_source_check', None): args.open_source_check()
    destination_fd = host.open_directory(str(cwd)); os.close(destination_fd)
    code = tracked_launch(state, model, cwd, packet, args.vault, task)
    if code: print(f'Provider exited {code}; original session untouched by Skeptic.', file=sys.stderr)
    return code


def tracked_launch(state, model, cwd, packet, vault, task):
    # Serialize CLI writers sharing the consent state; unmanaged writers still
    # require the explicit project-clear attestation, never inferred from quota.
    import fcntl
    fd = os.open('continuation-writer.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600, dir_fd=state.fd)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600:
            raise host.Denied('Unsafe continuation writer reservation')
        try: fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError: raise host.Denied('Another Skeptic CLI writer is active; no provider launched')
        return _tracked_launch(state, model, cwd, packet, vault, task)
    finally: os.close(fd)


def _tracked_launch(state, model, cwd, packet, vault, task):
    import continuity
    index = continuity.Index(state)
    start = dict(state.observation, session=None, incoming_session=state.observation.get('session'))
    continuity.warn(index.record(start, model['id'], 'launch_started'))
    try: code = launch(model, cwd, packet)
    except OSError:
        continuity.warn(index.record(start, model['id'], 'launch_failed'))
        state.event('launch_failed', model['id']); raise
    try:
        state.settings = state.read('settings.json', {})
        state.no_new_grants = True
        if Path(cwd) == Path.home(): raise host.Denied('Home-started context requires an explicit selected session; home never scanned')
        assemble(state, cwd, vault, task)
        continuity.warn(index.record(state.observation, model['id'], 'provider_exited', code))
    except (OSError, ValueError, host.Denied, subprocess.TimeoutExpired):
        continuity.warn(index.record(start, model['id'], 'provider_exited_checkpoint_unavailable', code))
        print('Post-session checkpoint unavailable; next switch will re-read approved sources.', file=sys.stderr)
    finally: state.no_new_grants = False
    state.event('provider_exited', model['id'], code)
    return code


def requested_model(provider, model):
    if model is None: return provider
    if not isinstance(model, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._:/-]{0,99}', model) or host.credential_like(model):
        raise host.Denied('Invalid model identifier; use the provider-native model picker instead')
    if provider.get('local') and model != provider.get('model'):
        raise host.Denied('Select a detected local model; Skeptic never downloads models')
    return dict(provider, model=model, model_verification='User selected; provider will validate availability')


def launch(provider, cwd, packet, run=subprocess.run, scratch=None):
    if not provider['executable']: raise host.Denied('Selected provider CLI is missing')
    if provider.get('id') == 'hermes':
        # Hermes seeds an interactive chat from a file (`chat --query-file`); a
        # private 0600 file in Skeptic's state dir, removed when Hermes exits.
        folder = Path(scratch or (Path.home() / '.skeptic-cli' / 'handoffs'))
        folder.mkdir(mode=0o700, parents=True, exist_ok=True)
        path = folder / ('hermes-' + os.urandom(8).hex() + '.md')
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        try:
            with os.fdopen(fd, 'w') as out: out.write(packet)
            argv = [provider['executable'], '--in', str(cwd)]
            if provider.get('model'): argv += ['-m', provider['model']]
            return run(argv + ['chat', '--query-file', str(path)], cwd=cwd, check=False).returncode
        finally:
            try: path.unlink()
            except FileNotFoundError: pass
    argv = [provider['executable']]
    if provider['local']: argv += ['--oss', '--local-provider', provider['provider'], '--model', provider['model']]
    elif provider.get('model'): argv += ['--model', provider['model']]
    # Explicit -- ends options; prompt is one argv entry, never shell text.
    argv += ['--', packet]
    return run(argv, cwd=cwd, check=False).returncode


def live_rows():
    """Open agents with a verdict each. Reads native session metadata only
    (the same scope as the Vitals tile); no approvals, history or Git."""
    import importlib.util
    def load(name):
        spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module
    inventory, sessions = load('live_inventory'), load('live_sessions')
    rows = sessions.collect(inventory.collect())
    return rows, sessions.summary(rows)


MARKS = {'ready': 'Ready', 'wait': 'Wait ', 'needs_project': 'Needs', 'unknown': '  ?  '}


def ready_cli(args, rows=None, run=None):
    """skeptic ready: if this agent stopped now, could another pick up?"""
    rows, best = rows if rows is not None else live_rows()
    if args.json:
        print(json.dumps({'summary': best, 'rows': rows}, indent=2)); return 0
    if not rows:
        print('No open Claude, Codex or Hermes sessions.'); return 0
    print('SKEPTIC — could another engine pick up?')
    for row in rows:
        print(f"{MARKS.get(row.get('verdict'), '  ?  ')}  {row['agent']} ({row['tty']}) · {clean(row['project'])} — {clean(row['headline'])}")
        if row.get('continue_command'): print('        ' + ' '.join(shlex.quote(a) for a in row['continue_command']))
        elif row.get('next_step'): print('        ' + clean(row['next_step']))
    if args.go:
        if not best or not best.get('continue_command'):
            print('Nothing is ready to continue yet.', file=sys.stderr); return 2
        # Repository continuations read the current directory: run it in the
        # session's project, not wherever this terminal happens to be.
        if best.get('continue_cwd'): os.chdir(best['continue_cwd'])
        return (run or main)(best['continue_command'][1:])
    return 0


def main(argv=None):
    selected_argv = sys.argv[1:] if argv is None else argv
    if not selected_argv:
        selected_argv = ['sessions', 'open', '--continue', '--with', 'codex', '--project', str(Path.home())]
    if selected_argv[:1] == ['managed']:
        from managed_cli import main as managed_main
        return managed_main(selected_argv[1:])
    if selected_argv[:1] == ['switch'] and '--with' not in selected_argv and (('--select' in selected_argv or '--all' in selected_argv) or os.environ.get('SKEPTIC_SESSION_ID') or any(p in selected_argv for p in ('claude','codex','skeptic-fake-v1'))):
        from managed_switch_cli import main as switch_main
        try: return switch_main(selected_argv[1:])
        except (host.Denied, __import__('managed_engine').Denied, OSError, ValueError) as error:
            print('Managed switch refused: '+str(error),file=sys.stderr);return 2
    parser = argparse.ArgumentParser(prog='skeptic')
    parser.add_argument('command', nargs='?', default='switch', choices=['switch', 'continue', 'status', 'doctor', 'models', 'handoff', 'permissions', 'analytics', 'sessions', 'session', 'catchup', 'checkpoint', 'transitions', 'ready'])
    parser.add_argument('action', nargs='?', help='sessions: open|list|pick|review|permissions|revoke; session: handoff|preview|continue|verify')
    parser.add_argument('path', nargs='?')
    parser.add_argument('--with', dest='provider')
    parser.add_argument('--model', help='Explicit provider-native model name; catalog/auth/quota not inferred')
    parser.add_argument('--vault', default=str(Path.home() / 'brain'))
    parser.add_argument('--task', default='')
    parser.add_argument('--state-dir', default=str(Path.home() / '.skeptic-cli'))
    parser.add_argument('--project', default=os.getcwd(), help='Claude session storage project scope; use --project ~ for home-started sessions')
    parser.add_argument('--all-projects', action='store_true', help='Explicitly request discovery across Claude project buckets; approval still required')
    parser.add_argument('--title', help='Session title substring; ambiguous matches use picker')
    parser.add_argument('--id', dest='session_id')
    parser.add_argument('--cwd', help='Explicit destination working directory for a home/multi-project session')
    parser.add_argument('--source', choices=['claude', 'codex'], default='claude')
    parser.add_argument('--repo', action='append', default=[], help='Additional explicitly selected repository (repeat, maximum four)')
    parser.add_argument('--conversation-only', action='store_true', help='Approved transcript recovery without project/Git/vault reads')
    parser.add_argument('--session-root', help='Explicit custom session storage directory')
    parser.add_argument('--session-file', help='Explicit Codex legacy JSONL transcript/export; no automatic Codex scan')
    parser.add_argument('--continue', dest='continue_open', action='store_true', help='Open-session task confirmation then approved Codex launch; default for bare skeptic')
    parser.add_argument('--json', action='store_true', help='ready: machine-readable rows')
    parser.add_argument('--go', action='store_true', help='ready: run the best ready continuation now')
    parser.add_argument('--fresh-session-approval', action='store_true', help='Ask again for metadata and selected-transcript consent even when a matching persistent grant exists')
    args = parser.parse_args(selected_argv)
    if args.command == 'ready': return ready_cli(args)
    state = None
    try:
        state = State(args.state_dir)
        if args.command == 'switch':
            args.interactive_switch = True
            print('SKEPTIC — Your work. Your memory. Any AI.')
            workflow = choose('Continue your work', ['Recover a Claude session (local, consent required)', 'Continue this project from approved notes and Git'])
            if workflow == 0:
                args.command = 'session'; args.action = 'continue'; args.source = 'claude'
                # Explicit menu choice requests discovery; scope consent still precedes reads.
                args.all_projects = not bool(args.session_id)
            else: args.command = 'continue'
        if args.command in ('sessions', 'session'):
            return session_cli(args, state)
        if args.command == 'transitions':
            import continuity
            print(json.dumps(continuity.Index(state).read(), indent=2)); return 0
        if args.command == 'permissions':
            if args.action == 'revoke' and args.path:
                path = os.path.expanduser(args.path)
                state.settings['grants'].pop(path, None)
                state.settings['mappings'] = {}  # Associations grant no access; discard on revocation.
                state.save(); print('Permission revoked.'); return 0
            print(json.dumps(state.settings['grants'], indent=2)); return 0
        if args.command == 'analytics':
            if args.action not in ('on', 'off'): raise host.Denied('Use analytics on|off')
            state.settings['analytics'] = args.action == 'on'; state.save(); return 0
        models = providers()
        if args.command in ('models', 'doctor'):
            for model in models: print(clean(model['id'] + ': ' + model['availability']))
            if args.command == 'doctor':
                print('Python: ' + sys.version.split()[0] + '; Git: ' + str(bool(shutil.which('git'))))
                print('Authentication, quotas and cloud model catalog: unknown (not queried).')
                print('CLI approved roots: ' + json.dumps(list(state.settings['grants'])))
                print('Current repository: ' + clean(repository(os.getcwd())))
                for path, grant in state.settings['grants'].items():
                    try:
                        _, fd = host.approve_root(path, vault=grant['kind'] == 'vault')
                        try:
                            info = os.fstat(fd)
                            valid = host.identity_matches(grant['identity'], info)
                            legacy = not valid and host.identity_matches(grant['identity'], info, legacy=True)
                        finally: os.close(fd)
                        print(clean(path) + ': ' + ('valid' if valid else 'valid; record upgrades on next skeptic run' if legacy else 'changed; fresh approval needed'))
                    except (OSError, host.Denied): print(clean(path) + ': inaccessible')
            return 0
        model = None
        if args.command == 'continue':
            model = requested_model(select_provider(state, args.provider), args.model)
        target = model['id'] if model else args.provider
        if args.command in ('catchup', 'checkpoint') and not target: raise host.Denied('Use --with PROVIDER to identify the catch-up/checkpoint participant')
        summary, packet = assemble(state, os.getcwd(), args.vault, args.task, target=target)
        if args.command == 'checkpoint':
            import continuity
            continuity.warn(continuity.Index(state).record(state.observation, target, 'explicit_checkpoint'))
            print(json.dumps(summary, indent=2)); return 0
        if args.command in ('handoff', 'catchup'):
            print('PROPOSED HANDOFF — review before updating canonical STATUS; no source files written.\n' + packet)
            return 0
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        if args.command == 'status': return 0
        print('Selected provider: ' + clean(model['label']) + '\nLaunching interactive CLI; host trust/tool approvals still apply.', flush=True)
        if not sys.stdin.isatty() or not sys.stdout.isatty(): raise host.Denied('Interactive launch requires Terminal')
        # Recheck consent/root identity immediately before launch by fresh assembly.
        state.settings = state.read('settings.json', {})
        summary, packet = assemble(state, os.getcwd(), args.vault, args.task, target=model['id'])
        state.settings['recent'] = [model['id']] + [p for p in state.settings['recent'] if p != model['id']][:9]
        state.save(); state.event('launch_started', model['id'])
        code = tracked_launch(state, model, os.getcwd(), packet, args.vault, args.task)
        if code: print(f'Provider exited {code}; project files preserved by Skeptic.', file=sys.stderr)
        return code
    except KeyboardInterrupt:
        print('Switch cancelled.', file=sys.stderr); return 130
    except (host.Denied, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        detail = clean(exc) if isinstance(exc, host.Denied) else 'Local source missing, inaccessible or invalid. Check --project (original cwd), --id UUID and --cwd (destination). Use --conversation-only for approved transcript recovery. Original session untouched.'
        print('Skeptic: ' + detail, file=sys.stderr); return 1
    finally:
        if state is not None: state.close()


if __name__ == '__main__': sys.exit(main())
