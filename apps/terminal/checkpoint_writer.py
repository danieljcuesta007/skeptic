"""Fixture-only reviewed append writer. Never enabled for live canonical records."""
from pathlib import Path
import fcntl,hashlib,os,tempfile,uuid
import checkpoints as c

def fixture(root):
 root=Path(root).resolve(strict=True)
 if Path(tempfile.gettempdir()).resolve() not in root.parents and Path('/private/tmp') not in root.parents:raise c.Rejected('Checkpoint writer is restricted to temporary fixtures')
 return root

def review(proposal):
 return c.digest({'proposal':proposal['fingerprint'],'markdown':c.markdown(proposal)})

def write(proposal,approved_digest,approved_destination,before_replace=None):
 s=proposal['snapshot'];fixture(s['root']);root=fixture(s['canonical_root']);destination=root/c.relative(s['canonical'])
 if Path(approved_destination).is_symlink() or destination!=Path(approved_destination).resolve(strict=True) or approved_digest!=review(proposal):raise c.Rejected('Exact destination and reviewed content approval required')
 if not c.fresh(s):raise c.Rejected('Checkpoint inputs changed')
 # Canonical parent must be real and stable; cross-provider locks are cooperative.
 for part in c.relative(s['canonical']).parts[:-1]:
  root=root/part
  if root.is_symlink():raise c.Rejected('Symlink destination parent')
 lock=root/('.skeptic-checkpoint-'+hashlib.sha256(destination.name.encode()).hexdigest()[:16]+'.lock')
 fd=os.open(lock,os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
 temporary=root/('.skeptic-pending-'+uuid.uuid4().hex)
 try:
  fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
  # Writer bookkeeping must be ignored by fixture Git configuration.
  if not c.fresh(s):raise c.Rejected('Writer bookkeeping changed source scope; ignore .skeptic-* in fixture')
  old=destination.read_bytes();new=old+b'\n\n'+c.markdown(proposal).encode()
  outfd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
  with os.fdopen(outfd,'wb') as out:out.write(new);out.flush();os.fsync(out.fileno())
  if before_replace:before_replace()
  if not c.fresh(s) or destination.read_bytes()!=old:raise c.Rejected('Concurrent checkpoint change')
  os.replace(temporary,destination)
  dirfd=os.open(root,os.O_RDONLY)
  try:os.fsync(dirfd)
  finally:os.close(dirfd)
  return {'version':1,'timestamp':c.now(),'destination':str(destination),'review':approved_digest,'before_sha256':hashlib.sha256(old).hexdigest(),'after_sha256':hashlib.sha256(new).hexdigest(),'operation':'reviewed append; fixture only'}
 finally:
  if temporary.exists():temporary.unlink()
  os.close(fd)
