"""Synthetic-only, on-demand discovery. No provider, shell or network integration."""
import argparse
import datetime
import fnmatch
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat


class Denied(ValueError):
    pass


class Reader:
    """Descriptor-relative no-follow access. Every successful body open is logged."""
    def __init__(self, roots, excluded):
        self.roots = {}
        self.excluded = excluded
        self.reads = []
        for alias, raw in roots.items():
            p = Path(raw)
            if not p.is_absolute() or p != p.resolve() or not p.is_dir():
                raise Denied('Allowed roots must be absolute, canonical directories')
            self.roots[alias] = p

    def parts(self, key):
        if not isinstance(key, str) or ':' not in key:
            raise Denied('Expected root:relative/path')
        alias, relative = key.split(':', 1)
        bits = relative.split('/')
        if alias not in self.roots or any(b in ('', '.', '..') for b in bits):
            raise Denied('Unauthorized or ambiguous path')
        if PurePosixPath(relative).is_absolute():
            raise Denied('Absolute source path rejected')
        if any(fnmatch.fnmatchcase(key, pat) or key.startswith(pat.rstrip('/') + '/')
               for pat in self.excluded):
            raise Denied('Excluded source')
        return alias, bits

    def inspect(self, key, previous=None):
        alias, bits = self.parts(key)  # policy BEFORE any filesystem content access
        handles = []
        try:
            fd = os.open(str(self.roots[alias]), os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            handles.append(fd)
            for part in bits[:-1]:
                fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                handles.append(fd)
            info = os.stat(bits[-1], dir_fd=fd, follow_symlinks=False)
            if not stat.S_ISREG(info.st_mode):
                raise Denied('Only regular files accepted; symlinks rejected')
            signature = [info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns]
            if previous and signature == previous.get('signature'):
                return dict(previous, validation='metadata-unchanged')
            bodyfd = os.open(bits[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            handles.append(bodyfd)
            opened = os.fstat(bodyfd)
            if not stat.S_ISREG(opened.st_mode) or opened != info:
                raise Denied('Source changed during open')
            self.reads.append(key)
            digest = hashlib.sha256()
            while True:
                block = os.read(bodyfd, 65536)
                if not block:
                    break
                digest.update(block)
            if tuple(os.fstat(bodyfd)[i] for i in (0, 1, 2, 6, 8, 9)) != tuple(opened[i] for i in (0, 1, 2, 6, 8, 9)):
                raise Denied('Source changed during read')
            return {'sha256': digest.hexdigest(), 'signature': signature, 'validation': 'hashed-now'}
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise Denied('Source inaccessible or symlink traversal rejected') from exc
        finally:
            for handle in reversed(handles):
                os.close(handle)


def discover(catalog, project, task, roots, explicit=(), previous=None):
    if not task.strip():
        raise Denied('Explicit nonempty task required')
    matches = [p for p in catalog['projects'] if p['id'] == project]
    if len(matches) != 1:
        raise Denied('Unknown or ambiguous project')
    project = matches[0]
    reader = Reader(roots, catalog.get('excluded', []))
    previous = previous or {}
    if previous.get('roots') != {k: str(v) for k, v in reader.roots.items()}:
        previous = {}  # never reuse freshness for a different authority/root
    sources = project['sources']
    keys = [s['path'] for s in sources]
    if len(keys) != len(set(keys)) or not set(explicit) <= set(keys):
        raise Denied('Duplicate source or selection outside approved catalog')
    # Explicit excluded selections fail; excluded catalog entries are silently omitted.
    for key in explicit:
        reader.parts(key)
    current, selected, missing, preferences = {}, [], [], {}
    words = set(re.findall(r'[a-z0-9]+', task.lower()))
    for source in sources:
        key = source['path']
        try:
            reader.parts(key)
        except Denied:
            if any(fnmatch.fnmatchcase(key, p) or key.startswith(p.rstrip('/') + '/')
                   for p in catalog.get('excluded', [])):
                continue
            raise
        record = reader.inspect(key, previous.get('files', {}).get(key))
        if record is None:
            missing.append(key)
            continue
        current[key] = record
        role = source['role']
        if role not in ('rule', 'status', 'note'):
            raise Denied('Unsupported source role')
        score = len(words & set(re.findall(r'[a-z0-9]+', ' '.join(source.get('tags', [])).lower())))
        priority = 0 if key in explicit else 1 if role == 'rule' else 2 if role == 'status' else 3
        if priority < 3 or score:
            selected.append({'path': key, 'role': role, 'sha256': record['sha256'],
                             'validation': record['validation'], 'priority': priority, 'score': score})
            # Host-approved structured declarations ONLY; ordinary note text is never interpreted.
            if role == 'rule':
                for name, value in source.get('preferences', {}).items():
                    preferences.setdefault(name, {}).setdefault(str(value), []).append(key)
    old = {}
    for key, value in previous.get('files', {}).items():
        try:
            reader.parts(key)
        except Denied:
            continue  # revoked paths must not leak through removed/rename output
        old[key] = value
    added = sorted(set(current) - set(old))
    removed = sorted(set(old) - set(current))
    changed = sorted(k for k in set(current) & set(old) if current[k]['sha256'] != old[k]['sha256'])
    renames = [{'from': a, 'to': b, 'confidence': 'hash-match candidate, not identity proof'}
               for a in removed for b in added if old[a]['sha256'] == current[b]['sha256']]
    conflicts = [{'preference': k, 'sources_by_value': v} for k, v in preferences.items() if len(v) > 1]
    checkpoint = project.get('handoff_hashes')
    stale = None if checkpoint is None else any(k not in current or current[k]['sha256'] != v
                                               for k, v in checkpoint.items())
    unknowns = ['No Git, worker concurrency or provider capability inspection',
                'Rule references require canonical reads by the receiving agent',
                'Conflicts detected only in host-approved structured declarations']
    if stale is None:
        unknowns.append('Handoff freshness unknown: no checkpoint hashes supplied')
    blocked = bool(conflicts or stale or missing)
    selected.sort(key=lambda s: (s['priority'], -s['score'], s['path']))
    receipt = {'project': project['id'], 'task': task,
               'rule_references': [s['path'] for s in selected if s['role'] == 'rule'],
               'sources': selected, 'handoff_location': project['status'] + '#handoff',
               'freshness': {'observed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                             'added': added, 'changed': changed, 'removed': removed,
                             'rename_candidates': renames, 'missing': missing, 'stale_handoff': stale},
               'conflicts': conflicts, 'unknowns': unknowns,
               'capabilities': {'local_file_hashing': True, 'network': False, 'execution': False,
                                'canonical_writes': False, 'provider_tools': 'unknown'},
               'next_permitted_action': 'Resolve missing sources, conflicts or stale checkpoint before acting'
                   if blocked else 'Read selected authorized references; no execution or external action authorized',
               'body_reads': reader.reads}
    if project['status'] not in current:
        raise Denied('Project status must be authorized and present')
    state = {'roots': {k: str(v) for k, v in reader.roots.items()}, 'files': current}
    return {'receipt': receipt, 'state': state}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--catalog', required=True, help='Trusted host-supplied synthetic policy JSON')
    parser.add_argument('--project', required=True)
    parser.add_argument('--task', required=True)
    parser.add_argument('--allow-root', action='append', required=True, help='alias=/absolute/path')
    parser.add_argument('--select', action='append', default=[])
    parser.add_argument('--previous', help='Previous JSON result; local cache is trusted input')
    args = parser.parse_args()
    roots = {}
    for raw in args.allow_root:
        alias, path = raw.split('=', 1)
        if alias in roots:
            parser.error('Duplicate root alias')
        roots[alias] = path
    catalog = json.loads(Path(args.catalog).read_text())
    previous = json.loads(Path(args.previous).read_text())['state'] if args.previous else None
    print(json.dumps(discover(catalog, args.project, args.task, roots, args.select, previous), indent=2))


if __name__ == '__main__':
    main()
