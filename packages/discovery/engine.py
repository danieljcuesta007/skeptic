"""Provider-independent local Markdown index. Synthetic validation only; no live adapter."""
import argparse
import copy
import datetime
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
import unicodedata

MODES = {'FULL_BRAIN', 'PROJECT_SCOPED', 'ASK_TO_EXPAND'}
BUILTIN_EXCLUSIONS = ['.git', '.obsidian', '.ai', '.health', '.trash', 'node_modules',
                      '.env*', '*credentials*', '*secrets*', '*private-key*']

MAX_CACHE_BYTES = 32 * 1024 * 1024

def credential_like(text):
    return bool(re.search(r'-----BEGIN .*PRIVATE KEY-----|gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}', text))

def path_key(text):
    # Conservative matching also protects case/normalization aliases on POSIX hosts.
    return unicodedata.normalize('NFKC', text).casefold()

class Denied(ValueError):
    pass


def tokens(text):
    return set(re.findall(r'[^\W_]+', text.casefold(), re.UNICODE))


class Engine:
    def __init__(self, config):
        config = copy.deepcopy(config)  # host policy cannot be changed through caller aliases
        self.config = config
        self.root = Path(config['root'])
        if not self.root.is_absolute() or self.root != self.root.resolve() or not self.root.is_dir():
            raise Denied('Root must be an absolute canonical directory')
        if config['mode'] not in MODES:
            raise Denied('Explicit valid mode required; no public-user default')
        self.mode = config['mode']
        self.rules = list(config.get('rules', []))
        self.exclusions = BUILTIN_EXCLUSIONS + config.get('excluded', [])
        self.body_reads = []
        for path in self.rules:
            self.validate(path)
        self.rootfd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        self.root_identity = self.sig(os.fstat(self.rootfd))[:2]

    def close(self):
        os.close(self.rootfd)

    def __enter__(self): return self
    def __exit__(self, *args): self.close()

    @staticmethod
    def sig(s):
        return [s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns]

    def validate(self, path):
        if not isinstance(path, str) or len(path)>4096 or '\x00' in path or path.startswith('/') or any(p in ('', '.', '..') for p in path.split('/')):
            raise Denied('Unsafe relative path')
        return path.split('/')

    def excluded(self, path):
        bits = [path_key(bit) for bit in self.validate(path)]
        path = path_key(path)
        patterns = [path_key(pattern) for pattern in self.exclusions]
        return any(fnmatch.fnmatchcase(path, pattern) or path.startswith(pattern.rstrip('/') + '/')
                   or any(fnmatch.fnmatchcase(bit, pattern) for bit in bits)
                   for pattern in patterns)

    def scoped(self, path, project):
        if self.excluded(path): return False
        if path in self.rules: return True
        if self.mode == 'FULL_BRAIN': return True
        if not project: return False
        if path == project['status']: return True
        if self.mode == 'ASK_TO_EXPAND': return False
        return any(path == prefix or path.startswith(prefix.rstrip('/') + '/') for prefix in project['paths'])

    def project(self, name):
        if name is None:
            if self.mode != 'FULL_BRAIN': raise Denied('Project required for scoped modes')
            return None
        hits = [p for p in self.config.get('projects', []) if p['id'] == name]
        if len(hits) != 1: raise Denied('Unknown or ambiguous project')
        p = hits[0]
        for path in [p['status'], *p['paths']]: self.validate(path)
        return p

    def inspect(self, path, content=False):
        if self.excluded(path): raise Denied('Protected source')
        bits = self.validate(path)
        handles = []
        fd = self.rootfd
        try:
            for part in bits[:-1]:
                if part not in os.listdir(fd): raise Denied('Noncanonical source alias')
                fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                handles.append(fd)
            if bits[-1] not in os.listdir(fd): raise Denied('Noncanonical source alias')
            info = os.stat(bits[-1], dir_fd=fd, follow_symlinks=False)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                raise Denied('Symlinks, special files and hard-linked files rejected')
            if not content: return self.sig(info), None
            if info.st_size > self.config.get('max_file_bytes', 1_000_000):
                raise Denied('Source exceeds size limit')
            bodyfd = os.open(bits[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            handles.append(bodyfd)
            if self.sig(os.fstat(bodyfd)) != self.sig(info): raise Denied('Source raced during open')
            self.body_reads.append(path)
            blocks = []
            total = 0
            while True:
                data = os.read(bodyfd, 65536)
                if not data: break
                total += len(data)
                if total > self.config.get('max_file_bytes', 1_000_000): raise Denied('Source exceeds size limit')
                blocks.append(data)
            if self.sig(os.fstat(bodyfd)) != self.sig(info): raise Denied('Source raced during read')
            return self.sig(info), b''.join(blocks)
        finally:
            for handle in reversed(handles): os.close(handle)

    def paths(self, project=None):
        """Descriptor-relative enumeration; exclusions and symlinks pruned before body reads."""
        def walk(fd, prefix=''):
            for name in sorted(os.listdir(fd)):
                relative = prefix + name
                if self.excluded(relative): continue
                info = os.stat(name, dir_fd=fd, follow_symlinks=False)
                if stat.S_ISLNK(info.st_mode): continue
                if stat.S_ISDIR(info.st_mode):
                    if self.mode != 'FULL_BRAIN':
                        targets = self.rules + ([project['status']] if project else [])
                        if self.mode == 'PROJECT_SCOPED' and project:
                            targets += project['paths']
                        if not any(t == relative or t.startswith(relative + '/') or relative.startswith(t.rstrip('/') + '/') for t in targets):
                            continue
                    child = os.open(name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                    try: yield from walk(child, relative + '/')
                    finally: os.close(child)
                elif stat.S_ISREG(info.st_mode) and name.lower().endswith('.md'):
                    yield relative
        return walk(self.rootfd)

    def index(self, project=None, previous=None):
        p = self.project(project)
        previous = self.validate_cache(previous, project) if previous is not None else {}
        policy_hash = hashlib.sha256(json.dumps(self.config, sort_keys=True).encode()).hexdigest()
        reusable = previous.get('root_identity') == self.root_identity and previous.get('root') == str(self.root)
        old = previous.get('documents', {}) if reusable else {}
        docs, errors, quarantined = {}, [], set()
        for path in self.paths(p):
            if not self.scoped(path, p): continue
            try:
                signature, _ = self.inspect(path)
                if path in old and old[path]['signature'] == signature:
                    docs[path] = old[path]
                    continue
                signature, data = self.inspect(path, content=True)
                text = data.decode('utf-8')
                # A secondary heuristic can quarantine unexpected secret-like material.
                # It cannot prevent the local read or replace path exclusions.
                if credential_like(text):
                    quarantined.add(path)
                    errors.append({'reason': 'quarantined credential-like content; filename withheld'})
                    continue
                chunks = [{'line': i + 1, 'text': text[start:start+600]} for i, start in enumerate(range(0,len(text),600))]
                docs[path] = {'signature': signature, 'sha256': hashlib.sha256(data).hexdigest(), 'chunks': chunks}
            except (Denied, OSError, UnicodeError):
                errors.append({'reason': 'unreadable, unsafe or oversized source; filename withheld'})
        # Do not expose revoked paths through a diff after a policy or project change.
        visible_old = {k:v for k,v in old.items() if self.scoped(k,p) and k not in quarantined}
        added = sorted(set(docs)-set(visible_old))
        removed = sorted(set(visible_old)-set(docs))
        changed = sorted(k for k in set(docs)&set(visible_old) if docs[k]['sha256']!=visible_old[k]['sha256'])
        renames = [{'from':a,'to':b} for a in removed for b in added if visible_old[a]['sha256']==docs[b]['sha256']]
        return {'schema':2,'root':str(self.root),'root_identity':self.root_identity,'policy_hash':policy_hash,
                'mode':self.mode,'project':project,'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
                'documents':docs,'changes':{'added':added,'removed':removed,'changed':changed,'rename_candidates':renames},
                'errors':errors}

    def validate_cache(self, index, project=None):
        """Cache is data, never authority. Reject malformed scoped records before reads."""
        p = self.project(project)
        try:
            if not isinstance(index, dict) or index.get('schema') != 2:
                raise Denied('Invalid cache; rebuild explicitly')
            if index.get('root') != str(self.root) or index.get('root_identity') != self.root_identity:
                raise Denied('Invalid cache; rebuild explicitly')
            if index.get('mode') not in MODES or not isinstance(index.get('policy_hash'), str):
                raise Denied('Invalid cache; rebuild explicitly')
            if not re.fullmatch(r'[0-9a-f]{64}', index['policy_hash']):
                raise Denied('Invalid cache; rebuild explicitly')
            if index.get('project') is not None and not isinstance(index['project'], str):
                raise Denied('Invalid cache; rebuild explicitly')
            if not isinstance(index.get('observed_at'), str) or len(index['observed_at'])>100:
                raise Denied('Invalid cache; rebuild explicitly')
            documents = index.get('documents')
            if not isinstance(documents, dict) or len(documents)>10000:
                raise Denied('Invalid cache; rebuild explicitly')
            safe, total_chunks, total_chars = {}, 0, 0
            for path, doc in documents.items():
                # Revoked/protected records cannot trigger body reads or reach output.
                if not self.scoped(path, p): continue
                if path not in self.rules and not (p and path==p['status']) and not path.lower().endswith('.md'):
                    continue
                if not isinstance(doc, dict): raise Denied('Invalid cache; rebuild explicitly')
                signature = doc.get('signature')
                if not isinstance(signature, list) or len(signature)!=5 or any(type(n) is not int or n<0 for n in signature):
                    raise Denied('Invalid cache; rebuild explicitly')
                digest, chunks = doc.get('sha256'), doc.get('chunks')
                if not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest):
                    raise Denied('Invalid cache; rebuild explicitly')
                if not isinstance(chunks, list) or len(chunks)>10000:
                    raise Denied('Invalid cache; rebuild explicitly')
                cleaned = []
                for chunk in chunks:
                    if not isinstance(chunk, dict): raise Denied('Invalid cache; rebuild explicitly')
                    line, text = chunk.get('line'), chunk.get('text')
                    if type(line) is not int or not 1<=line<=10000 or not isinstance(text, str) or len(text)>600:
                        raise Denied('Invalid cache; rebuild explicitly')
                    total_chunks += 1; total_chars += len(text)
                    if total_chunks>100000 or total_chars>MAX_CACHE_BYTES:
                        raise Denied('Invalid cache; rebuild explicitly')
                    cleaned.append({'line':line, 'text':text})
                safe[path] = {'signature':signature[:], 'sha256':digest, 'chunks':cleaned}
            return {**{key:index[key] for key in ('schema','root','root_identity','policy_hash','mode','project','observed_at')},
                    'documents':safe}
        except (KeyError, TypeError, AttributeError, RecursionError):
            raise Denied('Invalid cache; rebuild explicitly') from None

    def validate_catalog(self, catalog, project=None):
        """Untrusted catalogs may request scoped sources, never set roots, roles or policy."""
        if not isinstance(catalog, dict) or set(catalog) != {'sources'} or not isinstance(catalog['sources'], list):
            raise Denied('Catalog can contain source requests only')
        p = self.project(project)
        for path in catalog['sources']:
            if not self.scoped(path, p):
                raise Denied('Catalog request outside host authority')
        return catalog['sources']

    def revalidate_governing(self, index, project=None):
        """Call immediately before consequential actions; query calls this regardless of budget."""
        p = self.project(project)
        index = self.validate_cache(index, project)
        policy_hash=hashlib.sha256(json.dumps(self.config,sort_keys=True).encode()).hexdigest()
        if index['policy_hash']!=policy_hash or index['project']!=project or index['root_identity']!=self.root_identity: raise Denied('Reindex after policy/project changes')
        references, missing, stale, preferences = [], [], [], {}
        handoff = None
        required = self.rules + ([p['status']] if p else [])
        for path in required:
            if not self.scoped(path, p): raise Denied('Required source outside policy')
            try:
                _, data = self.inspect(path, True)
                text = data.decode('utf-8')
                digest = hashlib.sha256(data).hexdigest()
                record = index['documents'].get(path)
                if not record:
                    missing.append(path)
                    continue
                if digest != record['sha256']: stale.append(path)
                if credential_like(text):
                    missing.append(path)
                    continue
                references.append({'path':path, 'sha256':digest, 'requires_full_read':path in self.rules})
                if digest != record['sha256']:
                    continue  # Never emit stale handoff/preference contents.
                if path in self.rules:
                    # Deliberately explicit fixture syntax; ordinary notes never supply preferences.
                    for key,value in re.findall(r'^Preference: ([A-Za-z0-9 _.-]+) = (.+)$', text, re.MULTILINE):
                        preferences.setdefault(key,{}).setdefault(value,[]).append(path)
                elif p:
                    match = re.search(r'^## Handoff\s*\n(.*?)(?=^## |\Z)',text,re.MULTILINE|re.DOTALL)
                    handoff = {'location':path+'#handoff','excerpt':match.group(1).strip()[:600] if match else None,
                               'complete':bool(match and len(match.group(1).strip())<=600)}
            except (OSError, Denied, UnicodeError):
                missing.append(path)
        conflicts = [{'preference':key,'sources':sorted({p for paths in values.values() for p in paths})}
                     for key,values in preferences.items() if len(values)>1]
        return {'references':references,'missing':missing,'stale':stale,'conflicts':conflicts,
                'handoff':handoff,'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}

    def query(self, index, task, project=None, limit=5, max_chars=1800, explicit=(), catalog=None):
        if not task.strip() or not 1<=limit<=20 or not 100<=max_chars<=10000: raise Denied('Invalid query or bounds')
        p = self.project(project)
        index = self.validate_cache(index, project)
        policy_hash=hashlib.sha256(json.dumps(self.config,sort_keys=True).encode()).hexdigest()
        if index['policy_hash']!=policy_hash or index['project']!=project or index['root_identity']!=self.root_identity: raise Denied('Reindex after policy/project changes')
        for path in explicit:
            if not self.scoped(path,p) or path not in index['documents']: raise Denied('Selection outside scope')
        if catalog is not None:
            explicit = tuple(explicit) + tuple(self.validate_catalog(catalog, project))
            for path in explicit:
                if path not in index['documents']: raise Denied('Requested source not indexed')
        governing = self.revalidate_governing(index, project)
        candidates=[]
        words=tokens(task)
        for path,doc in index['documents'].items():
            if not self.scoped(path,p): continue
            role='rule' if path in self.rules else 'status' if p and path==p['status'] else 'data'
            for chunk in doc['chunks']:
                score=len(words&tokens(path+' '+chunk['text']))
                priority=0 if path in explicit else 1 if role=='rule' else 2 if role=='status' else 3
                if score or priority<3: candidates.append((priority,-score,path,chunk,role))
        candidates.sort(key=lambda c:(c[0],c[1],c[2],c[3]['line']))
        passages=[]; used=0; checked={}; live_text={}; stale=[]
        for _,score,path,chunk,role in candidates:
            if len(passages)>=limit or used>=max_chars: break
            if path not in checked:
                try:
                    _,data=self.inspect(path,True)
                    checked[path]=hashlib.sha256(data).hexdigest()==index['documents'][path]['sha256']
                    live_text[path]=data.decode('utf-8')
                    if credential_like(live_text[path]): checked[path]=False
                except (OSError,Denied,UnicodeError): checked[path]=False
            if not checked[path]:
                if path not in stale: stale.append(path)
                continue
            start=(chunk['line']-1)*600
            if start < 0 or start >= len(live_text[path]): continue
            text=live_text[path][start:start+min(600,max_chars-used)];used+=len(text)
            passages.append({'path':path,'sha256':index['documents'][path]['sha256'],'chunk':chunk['line'],
                             'role':role,'text':text})
        missing=governing['missing']
        stale=sorted(set(stale+governing['stale']))
        return {'mode':self.mode,'project':project,'task':task,'passages':passages,'characters':used,
                'rules':self.rules,'handoff':p['status']+'#handoff' if p else None,'stale':stale,
                'missing_required':missing,'indexed_at':index['observed_at'],
                'governing':governing, 'current_handoff':governing['handoff'],
                'conflicting_preferences':governing['conflicts'],
                'capabilities':{'file_references':True,'provider_tools':'unknown','execution':False},
                'unknowns':['Provider capabilities and Git/concurrency unverified','Host policy is trusted; untrusted cache can affect ranking/omissions but cannot grant access',
                            'Natural-language preference conflicts are not automatically resolved'],
                'next':'Reindex/resolve required sources before acting' if stale or missing or governing['conflicts'] else
                    'Read selected context; ask before expanding scope' if self.mode=='ASK_TO_EXPAND' else
                    'Use relevant context; no write or external-action permission granted',
                'limitations':{'network':False,'provider_integration':False,'writes_to_notes':False}}


def save_index(path, index):
    path=Path(path)
    if path.is_symlink(): raise Denied('Symlink cache destination rejected')
    if path.parent != path.parent.resolve() or not path.parent.is_dir(): raise Denied('Canonical existing cache directory required')
    # Persist only outside indexed knowledge root.
    root=Path(index['root'])
    if path.resolve()==root or root in path.resolve().parents: raise Denied('Index must live outside notes')
    if any((parent/'.git').exists() for parent in [path.parent,*path.parent.parents]):
        raise Denied('Index destination inside a Git working tree')
    fd,tmp=tempfile.mkstemp(prefix='.skeptic-index-',dir=path.parent)
    try:
        os.fchmod(fd,0o600)
        with os.fdopen(fd,'w') as f: json.dump(index,f,ensure_ascii=False)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def load_index(path):
    """Bounded, no-follow cache input; reject ambiguous JSON and unsafe files."""
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result: raise Denied('Invalid cache; rebuild explicitly')
            result[key] = value
        return result
    fd = None
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or info.st_size>MAX_CACHE_BYTES:
            raise Denied('Invalid cache; rebuild explicitly')
        with os.fdopen(fd, 'rb') as stream:
            fd = None
            data = stream.read(MAX_CACHE_BYTES+1)
        if len(data)>MAX_CACHE_BYTES: raise Denied('Invalid cache; rebuild explicitly')
        result = json.loads(data, object_pairs_hook=unique_pairs,
                            parse_constant=lambda _: (_ for _ in ()).throw(Denied('Invalid cache; rebuild explicitly')))
        if not isinstance(result, dict): raise Denied('Invalid cache; rebuild explicitly')
        return result
    except (OSError, ValueError, UnicodeError, RecursionError):
        raise Denied('Invalid cache; rebuild explicitly') from None
    finally:
        if fd is not None: os.close(fd)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy',required=True);parser.add_argument('--index',required=True)
    parser.add_argument('--project');parser.add_argument('--task',required=True)
    args=parser.parse_args()
    config=json.loads(Path(args.policy).read_text())
    path=Path(args.index)
    previous=load_index(path) if path.exists() or path.is_symlink() else None
    with Engine(config) as engine:
        index=engine.index(args.project,previous)
        receipt=engine.query(index,args.task,args.project)
        save_index(path,index)
    print(json.dumps(receipt,indent=2,ensure_ascii=False))

if __name__=='__main__':
    try: main()
    except Denied:
        raise SystemExit('Invalid or unauthorized input; review policy/cache and rebuild explicitly') from None
