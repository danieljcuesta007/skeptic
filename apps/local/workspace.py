"""Fresh, bounded inventory inside session-approved roots. No Git processes or writes."""
import hashlib
import os
import posixpath
from pathlib import Path
import re
import stat
from types import SimpleNamespace

POLICIES = ('FULL_BRAIN', 'PROJECT_SCOPED', 'ASK_TO_EXPAND')
RULES = ('PRINCIPLES.md', 'AGENTS.md', 'CLAUDE.md')


def identity(root, path):
    return hashlib.sha256((root + ':' + path).encode()).hexdigest()[:32]


def candidate_dirs(paths, kind):
    """A directory is a candidate, never an arbitrary ordinary note."""
    candidates = set()
    for path in paths:
        p = Path(path)
        if p.name == 'STATUS.md':
            candidates.add(str(p.parent))
        if kind == 'vault' and len(p.parts) >= 3 and p.parts[0] == '03 Projects':
            if not p.parts[1].startswith('_'):
                candidates.add(str(Path(*p.parts[:2])))
        if p.name in ('development-dashboard.md', 'dashboard.md', 'handoff.md'):
            candidates.add(str(p.parent))
    # Nested checkpoints within an Obsidian project do not create duplicates.
    canonical = {p for p in candidates if len(Path(p).parts) == 2 and Path(p).parts[0] == '03 Projects'}
    return sorted(p for p in candidates if not any(p != q and Path(q) in Path(p).parents for q in canonical))


def inside(path, folder):
    return Path(path).parent == Path(folder) or (folder != '.' and Path(folder) in Path(path).parents)


def references(text):
    """Only literal local paths in frontmatter paths or explicitly labelled repository lines."""
    values = []
    front = re.match(r'\A---\s*\n(.*?)\n---(?:\n|$)', text, re.S)
    if front:
        lines = front[1].splitlines()
        collecting = False
        for line in lines:
            if re.match(r'^paths:\s*', line):
                collecting = True
                tail = line.split(':', 1)[1].strip()
                values.extend(re.findall(r'(?:~/|/)[^\n,\]"\']+', tail))
            elif collecting and re.match(r'^\s+-\s+', line):
                values.append(re.sub(r'^\s+-\s+', '', line).strip(' \"\''))
            elif line and not line[0].isspace():
                collecting = False
    values.extend(re.findall(r'(?im)^\s*(?:[-*]\s*)?(?:repository|repo|work location|source repository)\s*:\s*`?((?:~/|/)[^`\n]+)', text))
    values.extend(re.findall(r'(?im)^\s*(?:[-*]\s*)?(?:\*\*)?(?:repository|repo|work location|source repository|product source|code repo)(?:\*\*)?\s*:\s*(?:\*\*)?\s*`((?:~/|/)[^`\n]+)`', text))
    return {os.path.expanduser(v.strip(' \"\'')) for v in values if '..' not in Path(v).parts}


class Workspace:
    def __init__(self, registry, host):
        self.registry, self.h = registry, host
        self.confirmed, self.hidden = {}, set()

    def roots(self):
        return [{**r, 'kind': r.get('kind', 'projects'), 'policy': r.get('policy', 'PROJECT_SCOPED')}
                for r in self.registry.listing()]

    def check(self, record):
        key = record['id']
        if key not in self.registry.active:
            raise self.h.Denied('Approve this workspace root for this session first')
        fd = self.h.open_directory(record['path'])
        if self.h.Engine.sig(os.fstat(fd))[:2] != self.h.Engine.sig(os.fstat(self.registry.active[key]))[:2]:
            os.close(fd)
            raise self.h.Denied('Approved workspace root changed; reconnect it')
        return fd

    def knowledge(self, record, budget=16_000_000):
        fd = self.check(record)
        try:
            with self.h.ScopedEngine(record['path'], fd, record['excluded'],
                                     {'files': 2048, 'entries': 12000, 'bytes': min(16_000_000, budget)}) as engine:
                paths = list(engine.paths())
                candidates = candidate_dirs(paths, record['kind'])
                allowed = paths
                if record['policy'] != 'FULL_BRAIN':
                    allowed = [p for p in paths if Path(p).name in RULES or
                               (Path(p).name == 'STATUS.md' and any(str(Path(p).parent) == c for c in candidates)) or
                               (record['policy'] == 'PROJECT_SCOPED' and any(Path(c) in Path(p).parents or Path(p).parent == Path(c) for c in candidates))]
                engine.paths = lambda: iter(allowed)
                snapshot = self.h.summarize(engine)
                return snapshot, candidates
        finally:
            os.close(fd)

    def repositories(self, record):
        fd = self.check(record)
        repos, count = [], 0
        def walk(directory, rel='', depth=0):
            nonlocal count
            names = os.listdir(directory)
            count += len(names)
            if count > self.h.MAX_ENTRIES or depth > 8 or len(repos) >= 50:
                raise self.h.Denied('Repository scan budget exceeded; connect a smaller root')
            if '.git' in names:
                info = os.stat('.git', dir_fd=directory, follow_symlinks=False)
                if stat.S_ISDIR(info.st_mode):
                    gitfd = os.open('.git', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
                    try:
                        branch, commit = self.git_metadata(gitfd)
                    finally:
                        os.close(gitfd)
                    path = str(Path(record['path']) / rel)
                    repos.append({'id': identity(record['id'], rel), 'root': record['id'], 'path': path,
                                  'name': Path(path).name, 'branch': branch, 'commit': commit,
                                  'limitations': 'Read-only HEAD/ref inspection. Working-tree changes, hooks, remotes and GitHub freshness are not inspected.'})
                # Worktree/submodule .git pointer files are deliberately unsupported.
                return
            for name in sorted(names):
                sub = str(Path(rel) / name)
                if self.h.protected(sub, self.h.EXCLUSIONS + record['excluded']):
                    continue
                info = os.stat(name, dir_fd=directory, follow_symlinks=False)
                if stat.S_ISDIR(info.st_mode):
                    child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
                    try: walk(child, sub, depth + 1)
                    finally: os.close(child)
        try: walk(fd)
        finally: os.close(fd)
        return repos

    def git_metadata(self, gitfd):
        def read(path):
            parent = os.dup(gitfd)
            try:
                parts = path.split('/')
                if any(p in ('', '.', '..') for p in parts): return None
                for p in parts[:-1]:
                    if p not in os.listdir(parent): return None
                    child = os.open(p, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
                    os.close(parent); parent = child
                if parts[-1] not in os.listdir(parent): return None
                fd = os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
                try:
                    before = os.fstat(fd)
                    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > 128000: return None
                    data = os.read(fd, 128001)
                    if self.h.Engine.sig(before) != self.h.Engine.sig(os.fstat(fd)): return None
                    return data.decode('ascii').strip()
                finally: os.close(fd)
            except (OSError, UnicodeError): return None
            finally: os.close(parent)
        head = read('HEAD') or ''
        if re.fullmatch(r'[a-f0-9]{40}|[a-f0-9]{64}', head): return 'Detached HEAD', head
        match = re.fullmatch(r'ref: (refs/heads/[A-Za-z0-9_./-]{1,200})', head)
        if not match or '..' in match[1] or self.h.protected(match[1]): return None, None
        ref = match[1]
        commit = read(ref)
        if not commit:
            packed = read('packed-refs') or ''
            matches = re.findall(r'^([a-f0-9]{40}|[a-f0-9]{64}) ' + re.escape(ref) + r'$', packed, re.M)
            commit = matches[0] if len(matches) == 1 else None
        if not commit or not re.fullmatch(r'[a-f0-9]{40}|[a-f0-9]{64}', commit): commit = None
        return ref[len('refs/heads/'):], commit

    def inventory(self):
        projects, repos, snapshots, reads, excluded = [], [], {}, [], []
        roots = self.roots()
        # Operation-wide root and byte limits complement each engine's limits.
        active = [r for r in roots if r['approved']]
        if len(active) > 10: raise self.h.Denied('At most 10 active workspace roots')
        remaining = 20_000_000
        for root in active:
            if root['kind'] == 'repositories':
                repos.extend(self.repositories(root)); continue
            snapshot, candidates = self.knowledge(root, remaining)
            remaining -= sum(len(d['text'].encode('utf-8')) for d in snapshot['documents'].values())
            snapshots[root['id']] = snapshot
            reads.extend(str(Path(root['path']) / p) for p in snapshot['reads'])
            excluded.extend(snapshot['excluded'])
            for folder in candidates:
                if any(p.startswith('_') for p in Path(folder).parts): continue
                path = str(Path(root['path']) / folder)
                key = identity(root['id'], folder)
                if key in self.hidden or any(p['path'] == path for p in projects): continue
                local = {p: d for p, d in snapshot['documents'].items() if inside(p, folder)}
                status = str(Path(folder) / 'STATUS.md')
                checkpoint = local.get(status)
                sections = self.h.sections(checkpoint['text'], {'current state', 'next actions', 'handoff'}) if checkpoint else []
                for section in sections: section['path'] = status
                def excerpt(heading):
                    s = next((s for s in sections if self.h.path_key(s['heading']) == heading), None)
                    return {'text': s['text'][:700], 'source': str(Path(root['path']) / s['path']), 'line': s['line'],
                            'truncated': s['truncated'] or len(s['text']) > 700} if s else None
                projects.append({'id': key, 'root': root['id'], 'folder': folder, 'path': path,
                                 'name': Path(path).name, 'knowledge': root['path'], 'policy': root['policy'],
                                 'checkpoint': str(Path(root['path']) / status) if checkpoint else None,
                                 'current': excerpt('current state'), 'pending': excerpt('next actions'),
                                 'handoff': excerpt('handoff'), 'repository': None, 'suggestions': [],
                                 'readiness': 'NEEDS REVIEW' if checkpoint else 'MISSING CHECKPOINT'})
        if len(projects) > 100 or len(reads) > 4096 or sum(len(d['text']) for s in snapshots.values() for d in s['documents'].values()) > 20_000_000:
            raise self.h.Denied('Workspace exceeds operation budget; approve smaller roots')
        for project in projects:
            snapshot = snapshots[project['root']]
            documents = {p: d for p, d in snapshot['documents'].items() if str(Path(p).parent) == project['folder']}
            evidence = set().union(*(references(d['text']) for d in documents.values())) if documents else set()
            exact = [r for r in repos if r['path'] in evidence]
            confirmed = [r for r in repos if r['id'] == self.confirmed.get(project['id'])]
            if len(exact) == 1:
                root = self.registry.projects[project['root']]
                project['repository'] = {**exact[0], 'evidence': 'Explicit repository path in project source',
                    'evidence_sources': [{'path': str(Path(root['path']) / p), 'sha256': d['sha256']} for p, d in documents.items() if exact[0]['path'] in references(d['text'])]}
            elif confirmed:
                project['repository'] = {**confirmed[0], 'evidence': 'User-confirmed association this session'}
            else:
                project['suggestions'] = exact or [r for r in repos if self.h.path_key(r['name']) == self.h.path_key(project['name'])]
            if project['checkpoint'] and project['current'] and project['pending'] and project['handoff'] and not project['suggestions']:
                project['readiness'] = 'READY TO RESUME'
        # Repositories without knowledge are real candidates, with explicit unknowns.
        for repo in repos:
            if any(p['repository'] and p['repository']['id'] == repo['id'] for p in projects): continue
            if repo['id'] in self.hidden: continue
            projects.append({'id': repo['id'], 'root': repo['root'], 'folder': None, 'path': repo['path'],
                             'name': repo['name'], 'knowledge': None, 'policy': next(r['policy'] for r in roots if r['id'] == repo['root']),
                             'checkpoint': None, 'current': None, 'pending': None, 'handoff': None,
                             'repository': repo, 'suggestions': [], 'readiness': 'NOT CONNECTED'})
        return {'projects': projects, 'repositories': repos, 'roots': roots, 'reads': reads,
                'excluded': excluded, '_snapshots': snapshots}

    def detail(self, key):
        inventory = self.inventory()
        project = next((p for p in inventory['projects'] if p['id'] == key), None)
        if not project: raise self.h.Denied('Unknown or revoked project')
        if project['folder'] is None:
            return project, {'documents': {}, 'sources': [], 'instructions': [], 'sections': [], 'handoffs': [],
                             'checkpoints': [], 'default_selection': [], 'reads': [], 'excluded': [],
                             'missing': ['No connected knowledge checkpoint. Git HEAD is not evidence of project progress.']}
        root = self.registry.projects[project['root']]
        full = inventory['_snapshots'][project['root']]
        folder = Path(project['folder'])
        wanted = {p for p in full['documents'] if inside(p, project['folder']) or
                  (Path(p).name in RULES and Path(p).parent in (folder, *folder.parents))}
        linked, external = set(), {}
        approved_lookup = {str(Path(self.registry.projects[root_id]['path']) / source): (source, approved)
                           for root_id, approved in inventory['_snapshots'].items() for source in approved['documents']}
        # Follow only exact Markdown links already read inside approved roots.
        # No basename guessing, URL fetch, symlink or approval expansion.
        for p in list(wanted):
            text = full['documents'][p]['text']
            targets = re.findall(r'\[[^\]]*\]\(([^)]+\.md)(?:#[^)]*)?\)', text) + re.findall(r'\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]', text)
            for target in targets[:30]:
                if '://' in target: continue
                if target.startswith(('/', '~')):
                    exact = os.path.expanduser(target)
                    if '..' in Path(exact).parts: continue
                    if not exact.endswith('.md'): exact += '.md'
                    if exact in approved_lookup: external[exact] = approved_lookup[exact]
                    continue
                for candidate in (str(Path(p).parent / target), target):
                    candidate = posixpath.normpath(candidate)
                    candidate = candidate if candidate.endswith('.md') else candidate + '.md'
                    if '..' not in Path(candidate).parts and candidate in full['documents']:
                        wanted.add(candidate); linked.add(candidate)
        def absolute(p): return str(Path(root['path']) / p)
        full = self.h.summarize(SimpleNamespace(budget_exhausted=False, audit=full['excluded'], body_reads=sorted(wanted)),
                                {p: full['documents'][p] for p in wanted})
        snapshot = {'documents': {absolute(p): d for p, d in full['documents'].items() if p in wanted}}
        for field in ('sources', 'sections', 'handoffs'):
            snapshot[field] = [{**s, 'path': absolute(s['path'])} for s in full[field] if s['path'] in wanted]
        dates = {s['path']: s['modified_at'] for s in snapshot['sources']}
        snapshot['handoffs'].sort(key=lambda s: dates.get(s['path'], ''), reverse=True)
        snapshot['handoffs'].sort(key=lambda s: s['path'] != project['checkpoint'])
        for field in ('instructions', 'checkpoints', 'default_selection', 'reads'):
            snapshot[field] = [absolute(p) for p in full[field] if p in wanted]
        snapshot['default_selection'] = sorted(set(snapshot['default_selection']) | {absolute(p) for p in linked})
        if len(external) > 30: raise self.h.Denied('Too many linked canonical sources')
        for exact, (source, approved) in external.items():
            if exact in snapshot['documents']: continue
            snapshot['documents'][exact] = approved['documents'][source]
            snapshot['sources'].append({**next(s for s in approved['sources'] if s['path'] == source),
                                        'path': exact, 'reason': 'Explicit canonical link inside an approved boundary'})
            snapshot['reads'].append(exact); snapshot['default_selection'].append(exact)
            if Path(source).name in RULES: snapshot['instructions'].append(exact)
            for section in self.h.sections(approved['documents'][source]['text'], {'objective', 'summary', 'current state', 'next actions', 'handoff', 'decisions'}):
                section.update(path=exact, sha256=approved['documents'][source]['sha256'])
                snapshot['sections'].append(section)
                if self.h.path_key(section['heading']) == 'handoff': snapshot['handoffs'].append(section)
        snapshot['excluded'] = full['excluded']
        repo = project['repository']
        if repo:
            repo_root = self.registry.projects[repo['root']]
            repo_fd = self.check(repo_root)
            try:
                with self.h.ScopedEngine(repo_root['path'], repo_fd, repo_root['excluded']) as engine:
                    repo_folder = Path(repo['path']).relative_to(repo_root['path'])
                    eligible = [str(parent / name) for parent in (repo_folder, *repo_folder.parents) for name in RULES]
                    eligible.append(str(repo_folder / 'STATUS.md'))
                    if repo_root['policy'] != 'ASK_TO_EXPAND': eligible.append(str(repo_folder / 'README.md'))
                    engine.paths = lambda: iter(eligible)
                    repo_snapshot = self.h.summarize(engine)
                for p, d in repo_snapshot['documents'].items():
                    snapshot['documents'][str(Path(repo_root['path']) / p)] = d
                for field in ('sources', 'sections', 'handoffs'):
                    snapshot[field].extend({**s, 'path': str(Path(repo_root['path']) / s['path'])} for s in repo_snapshot[field])
                for field in ('instructions', 'default_selection', 'reads'):
                    snapshot[field].extend(str(Path(repo_root['path']) / p) for p in repo_snapshot[field])
                snapshot['excluded'].extend(repo_snapshot['excluded'])
            finally:
                os.close(repo_fd)
        snapshot['missing'] = []
        for field, text in [('checkpoint', 'No STATUS.md checkpoint; progress unknown.'), ('current', 'Current state unknown.'),
                            ('pending', 'Unfinished work unknown.'), ('handoff', 'No canonical STATUS Handoff section; other handoff files require review.')]:
            if not project[field]: snapshot['missing'].append(text)
        snapshot['missing'].extend(['Source statements are unverified; file modification dates and Git commits do not prove progress.',
                                    'Sources outside approved roots and unresolved links were not read. Parent instructions above the root are unavailable.',
                                    'Milestones/completed work are literal source excerpts, not inferred completion. Conflicting source claims require review.'])
        if project['suggestions']: snapshot['missing'].append('Repository association is ambiguous; confirm a suggested match.')
        return project, snapshot

    def request(self, route, data):
        if route == 'roots' and data == {}: return {'roots': self.roots()}
        if route == 'connect' and set(data) == {'path', 'kind', 'policy', 'excluded', 'approval'}:
            if data['approval'] is not True: raise self.h.Denied('Explicit workspace read approval required')
            if data['kind'] not in ('vault', 'repositories', 'projects') or data['policy'] not in POLICIES:
                raise self.h.Denied('Invalid workspace policy')
            key = self.registry.approve(data['path'], data['excluded'], data['kind'], data['policy'])
            self.confirmed.clear(); self.hidden.clear()
            return {'id': key, 'activity': 'Saved root approval settings only; no knowledge files written.'}
        if route == 'disconnect' and set(data) == {'id'}:
            if data['id'] not in {r['id'] for r in self.roots()}: raise self.h.Denied('Unknown root')
            self.registry.remove(data['id']); self.confirmed.clear(); self.hidden.clear()
            return {'activity': 'Root permission revoked; source files untouched.'}
        if route == 'inventory' and data == {}:
            result = self.inventory(); del result['_snapshots']; return result
        if route == 'detail' and set(data) == {'id'}:
            project, snapshot = self.detail(data['id']); del snapshot['documents']
            return {'project': project, **snapshot}
        if route == 'confirm' and set(data) == {'id', 'repository', 'approval'}:
            if data['approval'] is not True: raise self.h.Denied('Explicit association approval required')
            project, _ = self.detail(data['id'])
            if data['repository'] not in {r['id'] for r in project['suggestions']}: raise self.h.Denied('Not an approved suggested repository')
            self.confirmed[project['id']] = data['repository']
            return {'activity': 'Repository association confirmed for this session.'}
        if route == 'remove' and set(data) == {'id'}:
            self.detail(data['id']); self.hidden.add(data['id']); self.confirmed.pop(data['id'], None)
            return {'activity': 'Project hidden for this session. Disconnect its root to revoke all root access.'}
        if route == 'resume' and set(data) == {'id', 'selected', 'provider', 'task'}:
            project, snapshot = self.detail(data['id'])
            prompt = self.h.continuation(project['path'], snapshot, data['selected'], data['provider'], data['task'])
            preface = [f"Project: {project['name']}\nKnowledge folder: {project['path']}\nAccess policy: {project['policy']}",
                       'Preserve unrelated staged, unstaged and untracked work. No provider is launched. Review source conflicts before continuing.']
            for field in ('checkpoint', 'current', 'pending', 'handoff'):
                preface.append(f'{field}: {project[field] or "Unknown; inspect canonical sources."}')
            preface.append(f"Repository observation (HEAD is not progress): {project['repository'] or 'Not connected'}")
            preface.append('Next recommended action: read the canonical checkpoint and attributed unfinished work; reconcile actual Git state before changing files. Excerpts may be truncated; read full source paths.')
            return {'prompt': '\n'.join(preface) + '\n' + prompt, 'selected': data['selected'],
                    'reads': snapshot['reads'], 'excluded': snapshot['excluded']}
        raise self.h.Denied('Unknown workspace request or fields')
