"""Reversible migration rehearsal for isolated, stopped synthetic registries only.

This module deliberately cannot access a production root or relocate a live PTY.
It copies an exited synthetic metadata snapshot and keeps the source intact.
"""
import hashlib,json,os,sqlite3,stat,uuid
from pathlib import Path
from managed_engine import Denied,Registry,fixture_path,private_file

RECEIPT='.skeptic-migration.json'
MARKER='.skeptic-migration-incomplete'
MAX_FILE=8*1024*1024

def _hash(path):
 fd=private_file(path,readonly=True)
 try:
  h=hashlib.sha256();total=0
  while True:
   chunk=os.read(fd,65536)
   if not chunk:break
   total+=len(chunk)
   if total>MAX_FILE:raise Denied('Migration fixture file exceeds limit')
   h.update(chunk)
  return h.hexdigest()
 finally:os.close(fd)

def inspect(source,destination):
 src=fixture_path(source);dst=fixture_path(destination)
 if src==dst or src in dst.parents or dst in src.parents:raise Denied('Migration roots must be separate')
 if not src.is_dir() or not (src/'registry.sqlite').exists():raise Denied('Source registry missing')
 if dst.exists():raise Denied('Destination must not exist; migration never overwrites')
 info=src.stat()
 if info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)!=0o700:raise Denied('Source state must be owner-only')
 registry=Registry(src,readonly=True)
 try:
  if registry.db.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise Denied('Source registry integrity check failed')
  sessions=registry.db.execute('SELECT id,status,supervisor,agent FROM sessions').fetchall()
  # A PID is never sufficient proof of process ownership or safe relocation.
  if any(row[1]!='exited' or row[2] is not None or row[3] is not None for row in sessions):
   raise Denied('Only archived synthetic sessions with no supervisor/agent identity may migrate')
  tables={row[0] for row in registry.db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
  if 'managed_schema' not in tables or [tuple(row) for row in registry.db.execute('SELECT version FROM managed_schema')]!=[(1,)]:
   raise Denied('Only the reviewed managed schema version can migrate')
  if 'switches' in tables:
   open_tx=registry.db.execute("SELECT id FROM switches WHERE stage NOT IN ('source_retained','failed','revoked') LIMIT 1").fetchone()
   if open_tx:raise Denied('Unresolved switch transaction prevents migration')
 finally:registry.close()
 files={}
 for path in sorted(src.iterdir()):
  if path.name=='registry.sqlite' or path.suffix in ('.handoff','.startup'):
   s=path.lstat()
   if not stat.S_ISREG(s.st_mode) or s.st_nlink!=1 or s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=0o600:
    raise Denied('Migration accepts owner-only regular metadata files only')
   files[path.name]=_hash(path)
 if 'registry.sqlite' not in files:raise Denied('Registry snapshot unavailable')
 body={'source':str(src),'destination':str(dst),'source_dev':info.st_dev,'source_ino':info.st_ino,'files':files}
 body['plan_hash']=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(',',':')).encode()).hexdigest()
 return body

def apply(source,destination,approved_plan_hash):
 plan=inspect(source,destination)
 if plan['plan_hash']!=approved_plan_hash:raise Denied('Migration plan changed; inspect and approve the new plan')
 dst=Path(plan['destination']);dst.mkdir(mode=0o700)
 try:
  marker=os.open(dst/MARKER,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
  os.close(marker)
  for name,digest in plan['files'].items():
   src=Path(plan['source'])/name;out=dst/name
   infd=private_file(src,readonly=True);outfd=os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
   try:
    while True:
     block=os.read(infd,65536)
     if not block:break
     offset=0
     while offset<len(block):offset+=os.write(outfd,block[offset:])
    os.fsync(outfd)
   finally:os.close(infd);os.close(outfd)
   if _hash(out)!=digest:raise Denied('Copied migration file did not match reviewed hash')
  manifest=dict(plan,format=1,migration_id=str(uuid.uuid4()))
  fd=os.open(dst/RECEIPT,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,'w') as stream:json.dump(manifest,stream,sort_keys=True);stream.flush();os.fsync(stream.fileno())
  os.unlink(dst/MARKER)
  dfd=os.open(dst,os.O_RDONLY|os.O_DIRECTORY);os.fsync(dfd);os.close(dfd)
 except BaseException:
  # Keep an inspectable marked partial destination; never delete a tree on error.
  raise
 return manifest

def rollback(destination,approved_migration_id):
 dst=fixture_path(destination);receipt=dst/RECEIPT
 info=dst.stat()
 if info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)!=0o700:raise Denied('Migration destination must remain owner-only')
 fd=private_file(receipt,readonly=True)
 try:manifest=json.loads(os.read(fd,65537))
 finally:os.close(fd)
 if manifest.get('format')!=1 or manifest.get('migration_id')!=approved_migration_id:raise Denied('Rollback identity mismatch')
 expected=set(manifest['files'])|{RECEIPT}
 actual={path.name for path in dst.iterdir()}
 if actual!=expected:raise Denied('Destination changed after migration; rollback will not move user data')
 for name,digest in manifest['files'].items():
  if _hash(dst/name)!=digest:raise Denied('Destination file changed after migration')
 backup=dst.with_name(dst.name+'.rollback-'+manifest['migration_id'])
 if backup.exists():raise Denied('Rollback archive already exists')
 os.rename(dst,backup)
 return str(backup)
