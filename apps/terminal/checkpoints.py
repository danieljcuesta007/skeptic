"""Explicit-scope checkpoint proposals. Hashes establish integrity, never correctness."""
from pathlib import Path
import datetime, hashlib, json, os, stat, subprocess, uuid

class Rejected(ValueError): pass
MAX_FILE=8*1024*1024

def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def digest(value): return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=True).encode()).hexdigest()
def git(root,*args,optional=False):
    p=subprocess.run(['git','-c','core.fsmonitor=false','-c','core.untrackedCache=false','-c','core.hooksPath=/dev/null','-C',str(root),*args],capture_output=True,env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'),timeout=15)
    if p.returncode and not optional: raise Rejected('Git inspection failed')
    return p.stdout if p.returncode==0 else None

def relative(value):
    p=Path(value)
    if not isinstance(value,str) or not value or p.is_absolute() or '..' in p.parts or value!=p.as_posix(): raise Rejected('Explicit normalized relative source required')
    if any(ord(c)<32 for c in value): raise Rejected('Control character in source')
    if any(c in ('.git','.ssh','.aws') or c.startswith('.env') or c.lower() in ('secrets.json','credentials.json','id_rsa','id_ed25519') for c in p.parts): raise Rejected('Protected source refused')
    return p

def fingerprint(root,value):
    p=relative(value); directory=None;fd=None
    try:
        directory=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        for part in p.parts[:-1]:
            child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=directory)
            os.close(directory);directory=child
        try:fd=os.open(p.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=directory)
        except FileNotFoundError:return {'state':'missing'}
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_size>MAX_FILE:raise Rejected('Source type/size refused')
        chunks=[];size=0
        while True:
            chunk=os.read(fd,65536)
            if not chunk:break
            size+=len(chunk)
            if size>MAX_FILE:raise Rejected('Source grew beyond bound')
            chunks.append(chunk)
        after=os.fstat(fd);final=os.stat(p.name,dir_fd=directory,follow_symlinks=False)
        sig=lambda v:(v.st_dev,v.st_ino,v.st_size,v.st_mtime_ns,v.st_ctime_ns)
        if sig(before)!=sig(after) or sig(after)!=sig(final):raise Rejected('Source changed during inspection')
        return {'state':'present','sha256':hashlib.sha256(b''.join(chunks)).hexdigest(),'size':size,'mode':stat.S_IMODE(after.st_mode)}
    except OSError as e:raise Rejected('Source unavailable or symlink refused') from e
    finally:
        if fd is not None:os.close(fd)
        if directory is not None:os.close(directory)

def _inspect(root,sources,project_id,canonical,canonical_root=None):
    root=Path(root)
    if root.is_symlink() or not root.is_absolute():raise Rejected('Explicit absolute checkout required')
    root=root.resolve(strict=True)
    top=git(root,'rev-parse','--show-toplevel').decode().strip()
    if Path(top)!=root:raise Rejected('Wrong checkout root')
    if not isinstance(project_id,str) or not project_id.strip():raise Rejected('Stable project ID required')
    sources=list(sources)
    if len(sources)>256 or len(set(sources))!=len(sources) :raise Rejected('Canonical source and distinct bounded scope required')
    record_root=Path(canonical_root) if canonical_root is not None else root
    if not record_root.is_absolute() or record_root.is_symlink():raise Rejected('Explicit canonical root required')
    record_root=record_root.resolve(strict=True);record_info=record_root.stat()
    record_fingerprint=fingerprint(record_root,canonical)
    if record_fingerprint['state']!='present':raise Rejected('Canonical record missing')
    info=root.stat();gitdir=git(root,'rev-parse','--absolute-git-dir').decode().strip();common=git(root,'rev-parse','--git-common-dir').decode().strip()
    common=str((root/common).resolve())
    status=git(root,'status','--porcelain=v1','-z','--untracked-files=all')
    # Preserve raw Git path bytes, including renamed/deleted/quoted paths, as hex.
    result={'version':1,'project_id':project_id,'root':str(root),'root_identity':[info.st_dev,info.st_ino],'gitdir':gitdir,'common_gitdir':common,'canonical':canonical,'canonical_root':str(record_root),'canonical_root_identity':[record_info.st_dev,record_info.st_ino],'canonical_fingerprint':record_fingerprint,'head':(git(root,'rev-parse','--verify','HEAD',optional=True) or b'').decode().strip() or None,'branch':(git(root,'symbolic-ref','--short','HEAD',optional=True) or b'').decode().strip() or None,'status_hex':status.hex(),'staged_diff_sha256':hashlib.sha256(git(root,'diff','--cached','--binary','--no-ext-diff','--no-textconv')).hexdigest(),'unstaged_diff_sha256':hashlib.sha256(git(root,'diff','--binary','--no-ext-diff','--no-textconv')).hexdigest(),'sources':{s:fingerprint(root,s) for s in sources}}
    result['fingerprint']=digest(result)
    return result

def inspect(root,sources,project_id,canonical,canonical_root=None):
    sources=list(sources)
    first=_inspect(root,sources,project_id,canonical,canonical_root)
    second=_inspect(root,sources,project_id,canonical,canonical_root)
    if first!=second:raise Rejected('Source changed during snapshot inspection')
    return first

def validate_snapshot(s):
    if not isinstance(s,dict) or s.get('version')!=1 or s.get('fingerprint')!=digest({k:v for k,v in s.items() if k!='fingerprint'}):raise Rejected('Malformed snapshot')

def refresh(snapshot):
    validate_snapshot(snapshot)
    return inspect(snapshot['root'],snapshot['sources'],snapshot['project_id'],snapshot['canonical'],snapshot.get('canonical_root'))

def fresh(snapshot):return refresh(snapshot)['fingerprint']==snapshot['fingerprint']

def receipt(snapshot,command,exit_status,evidence):
    validate_snapshot(snapshot)
    if not isinstance(command,list) or not command or any(not isinstance(x,str) or '\x00' in x for x in command):raise Rejected('Explicit argv required')
    if type(exit_status)!=int:raise Rejected('Integer command exit status required')
    from sessions import sanitize
    if any(sanitize(v)!=v for v in command):raise Rejected('Sensitive command argv refused')
    if not fresh(snapshot):raise Rejected('Verification source changed')
    evidence=relative(evidence).as_posix();proof=fingerprint(snapshot['root'],evidence)
    if proof['state']!='present':raise Rejected('Evidence missing')
    r={'version':1,'id':str(uuid.uuid4()),'timestamp':now(),'command':command,'cwd':snapshot['root'],'source_fingerprint':snapshot['fingerprint'],'evidence':evidence,'evidence_fingerprint':proof,'exit_status':exit_status,'result':'command_passed' if exit_status==0 else 'command_failed','provenance':'caller_reported; execution not attested by Skeptic'}
    r['fingerprint']=digest(r);return r

def receipt_state(r,snapshot):
    if not isinstance(r,dict) or r.get('version')!=1 or r.get('fingerprint')!=digest({k:v for k,v in r.items() if k!='fingerprint'}):raise Rejected('Malformed verification receipt')
    required={'command','cwd','source_fingerprint','evidence','evidence_fingerprint','exit_status','result','provenance'}
    if not required<=r.keys() or type(r['exit_status'])!=int or r['result']!=('command_passed' if r['exit_status']==0 else 'command_failed'):raise Rejected('Conflicting verification fields')
    if r['cwd']!=snapshot['root'] or r['source_fingerprint']!=snapshot['fingerprint'] or not fresh(snapshot) or fingerprint(snapshot['root'],r['evidence'])!=r['evidence_fingerprint']:return 'stale'
    return r['result']

def proposal(snapshot,agent,session,objective,claims=(),pending=(),constraints=(),decisions=(),failures=(),uncertainty=(),receipts=(),writer='unknown'):
    validate_snapshot(snapshot)
    if not fresh(snapshot):raise Rejected('Stale proposal inputs')
    if writer not in ('unknown','clear','active','conflict'):raise Rejected('Invalid writer observation')
    from sessions import sanitize
    if any(len(v)>64 for v in (claims,pending,constraints,decisions,failures,uncertainty,receipts)):raise Rejected('Proposal list exceeds bound')
    def clean(v):
        if not isinstance(v,str) or len(v)>4000:raise Rejected('Invalid bounded text')
        return sanitize(v)
    data={'version':1,'id':str(uuid.uuid4()),'timestamp':now(),'snapshot':snapshot,'agent':clean(agent),'session':clean(session),'objective':clean(objective),'writer':writer,'claims':[clean(x) for x in claims],'pending':[clean(x) for x in pending],'constraints':[clean(x) for x in constraints],'decisions':[clean(x) for x in decisions],'failures':[clean(x) for x in failures],'uncertainty':[clean(x) for x in uncertainty],'receipts':list(receipts)}
    for r in data['receipts']:receipt_state(r,snapshot)
    data['fingerprint']=digest(data);return data

def markdown(p):
    if p.get('fingerprint')!=digest({k:v for k,v in p.items() if k!='fingerprint'}):raise Rejected('Changed proposal')
    s=p['snapshot'];lines=['# Skeptic checkpoint proposal','',f"Project: {s['project_id']}",f"Canonical record: {s['canonical_root']} / {s['canonical']}",f"Checkpoint: {p['id']}",f"Timestamp: {p['timestamp']}",f"Agent/session: {p['agent']} / {p['session']}",f"Objective: {p['objective']}",f"Writer observation: {p['writer']}",f"HEAD: {s['head'] or 'unborn'}",f"Branch: {s['branch'] or 'detached'}",f"Source fingerprint: {s['fingerprint']}",'','Hashes establish source integrity, not semantic correctness.','Git status: '+('dirty' if s['status_hex'] else 'clean'),'']
    for title,key in [('Unverified completion claims','claims'),('Outstanding tasks','pending'),('Constraints','constraints'),('Decisions','decisions'),('Known failures / interruptions','failures'),('Uncertainty','uncertainty')]:
        lines.extend(['## '+title,'']+(['- '+v for v in p[key]] or ['Unknown / none reported.'])+[''])
    lines+=['## Verification evidence','']
    for r in p['receipts']:lines+=['- '+receipt_state(r,s)+'; '+json.dumps(r['command'])+'; '+r['evidence']+'; '+r['provenance']]
    lines+=['','## Changed files (observed Git status)','']
    from sessions import sanitize
    rows=bytes.fromhex(s['status_hex']).split(b'\x00')
    lines += ['- '+sanitize(row.decode('utf-8','replace')) for row in rows if row]
    lines+=['','## Approved source fingerprints','']+['- '+path+': '+json.dumps(fp,sort_keys=True) for path,fp in s['sources'].items()]
    return '\n'.join(lines)+'\n'

def execute_fixture(snapshot,command,evidence,approved=False):
    """Observed offline command receipt; temporary projects only, no shell execution."""
    from checkpoint_writer import fixture
    from sessions import sanitize
    import resource,tempfile
    root=fixture(snapshot['root'])
    if not approved:raise Rejected('Explicit offline command approval required')
    if not isinstance(command,list) or not command or any(not isinstance(v,str) or '\x00' in v or sanitize(v)!=v for v in command):raise Rejected('Invalid/sensitive command argv')
    if Path(command[0]).name in ('claude','hermes','codex'):raise Rejected('Live providers prohibited')
    if not fresh(snapshot):raise Rejected('Stale command inputs')
    path=root/relative(evidence)
    if path.parent!=root:raise Rejected('Evidence must be in fixture root')
    started=now()
    def limits():resource.setrlimit(resource.RLIMIT_FSIZE,(256*1024,256*1024))
    with tempfile.TemporaryFile() as output:
        try:code=subprocess.run(command,cwd=root,stdout=output,stderr=subprocess.STDOUT,timeout=15,check=False,preexec_fn=limits).returncode
        except subprocess.TimeoutExpired:code=124
        output.seek(0);raw=output.read(256*1024+1)
    if len(raw)>256*1024:raise Rejected('Evidence limit exceeded')
    if not fresh(snapshot):raise Rejected('Command changed relevant sources; result is not a valid receipt')
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as out:out.write(sanitize(raw.decode('utf-8','replace')).encode());out.flush();os.fsync(out.fileno())
    r=receipt(snapshot,command,code,evidence);r['provenance']='Skeptic observed subprocess execution; fixture only; semantic correctness unverified';r['started_at']=started
    r['fingerprint']=digest({k:v for k,v in r.items() if k!='fingerprint'});return r
