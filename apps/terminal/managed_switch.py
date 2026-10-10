"""Durable managed switch journal in the existing temporary registry.

Recovery packets come from the existing switcher; terminal output is never promoted
into user instructions. Live sources are excluded because PTY detach is not quiescence.
"""
import hashlib,json,os,sqlite3,uuid
from pathlib import Path
import continuity
from managed_engine import Denied,Registry,fixture_path,observation,private_file,session_id

SCHEMA=1
STAGES=('locked','checkpoint_validated','target_launch_authorized','target_launching',
        'target_started','recovery_verifying','recovery_passed','target_active','source_retained')

def initialize(root):
 r=Registry(root)
 try:
  with r.db:
   r.db.execute('CREATE TABLE IF NOT EXISTS managed_schema (version INTEGER NOT NULL)')
   versions=r.db.execute('SELECT version FROM managed_schema').fetchall()
   if versions and versions!=[(SCHEMA,)]:raise Denied('Unsupported integration schema; no migration attempted')
   if not versions:r.db.execute('INSERT INTO managed_schema VALUES (?)',(SCHEMA,))
   r.db.execute('CREATE TABLE IF NOT EXISTS session_details (id TEXT PRIMARY KEY REFERENCES sessions(id), details TEXT NOT NULL)')
   r.db.execute('CREATE TABLE IF NOT EXISTS switches (id TEXT PRIMARY KEY, source TEXT NOT NULL, target TEXT NOT NULL UNIQUE, provider TEXT NOT NULL, stage TEXT NOT NULL, packet TEXT NOT NULL, hash TEXT NOT NULL, objective TEXT NOT NULL, project TEXT NOT NULL, authorized INTEGER NOT NULL, error TEXT)')
   r.db.execute('CREATE TABLE IF NOT EXISTS switch_events (transaction_id TEXT NOT NULL, sequence INTEGER NOT NULL, stage TEXT NOT NULL, PRIMARY KEY(transaction_id,sequence))')
   r.db.execute('CREATE TABLE IF NOT EXISTS project_locks (project TEXT PRIMARY KEY, transaction_id TEXT NOT NULL UNIQUE)')
 finally:r.close()


def overlaps(a,b):
 a,b=Path(a).resolve(),Path(b).resolve()
 return a==b or a in b.parents or b in a.parents

class Manager:
 def __init__(self,root,inspect=observation,readonly=False):
  self.root=fixture_path(root);self.registry=Registry(root,readonly=True if readonly else False)
  self.db=self.registry.db;self.inspect=inspect;self.synthetic=inspect is not observation
  try:
   versions=self.db.execute('SELECT version FROM managed_schema').fetchall()
   if [tuple(v) for v in versions]!=[(SCHEMA,)]:
    self.close();raise Denied('Unsupported integration schema')
  except sqlite3.DatabaseError as error:
   self.close();raise Denied('Run managed initialize explicitly; no automatic migration') from error
 def close(self):self.registry.close()
 def details(self,sid):
  row=self.db.execute('SELECT details FROM session_details WHERE id=?',(sid,)).fetchone()
  return json.loads(row[0]) if row else {'stable_id':sid,'name':sid,'task_state':'unknown','checkpoint':None,'last_verified_recovery':None}
 def register(self,sid,name):
  self.registry.get(sid)
  if not isinstance(name,str) or not name or len(name)>100 or any(ord(c)<32 for c in name):raise Denied('Invalid display name')
  data=self.details(sid);data['name']=name
  with self.db:self.db.execute('INSERT OR REPLACE INTO session_details VALUES (?,?)',(sid,json.dumps(data)))
 def preview(self,provider):
  if provider not in ('claude','codex','skeptic-fake-v1'):raise Denied('Unsupported destination provider')
  rows=[self.inspect(self.root,row[0]) for row in self.db.execute('SELECT id FROM sessions ORDER BY id').fetchall()]
  result=[]
  for row in rows:
   reason=None
   if row.get('reachability')!='reachable':reason='Supervisor unreachable; ownership/quiescence unknown'
   elif row['status']!='exited':reason='Source agent is still live/detached/suspended; no implicit pause or takeover'
   elif not row.get('agent_process_group_quiescent') or not row.get('output_complete'):reason='Source process group or PTY output drain is unresolved; project remains ineligible'
   elif row['provider']==provider:reason='Already uses destination provider'
   elif any(other['id']!=row['id'] and (other['status']!='exited' or not other.get('agent_process_group_quiescent') or not other.get('output_complete')) and overlaps(row['cwd'],other['cwd']) for other in rows):reason='Overlapping managed project writer or unresolved process group'
   details=self.details(row['id'])
   pending=self.db.execute("SELECT id FROM switches WHERE source=? AND stage NOT IN ('source_retained','failed','revoked')",(row['id'],)).fetchone()
   if pending:reason='Pending switch '+pending[0]
   if reason is None:
    for project,tid in self.db.execute('SELECT project,transaction_id FROM project_locks').fetchall():
     if overlaps(project,row['cwd']):reason='Project reserved by managed destination transaction '+tid;break
   result.append(dict(row,**details,destination=provider,eligible=reason is None,exclusion=reason,terminal='owned PTY; attachment observed by supervisor',checkpoint_ready=bool(details.get('checkpoint'))))
  return result
 def transaction(self,tid):
  self.db.row_factory=sqlite3.Row
  row=self.db.execute('SELECT * FROM switches WHERE id=?',(tid,)).fetchone()
  if not row:raise Denied('Unknown switch transaction')
  return dict(row)
 def event(self,tid,stage):
  count=self.db.execute('SELECT COUNT(*) FROM switch_events WHERE transaction_id=?',(tid,)).fetchone()[0]
  self.db.execute('INSERT INTO switch_events VALUES (?,?,?)',(tid,count+1,stage))
  self.db.execute('UPDATE switches SET stage=? WHERE id=?',(stage,tid))
 def prepare(self,sid,provider,packet,objective,tid=None):
  tid=session_id(tid) if tid else str(uuid.uuid4());session_id(sid)
  if not isinstance(packet,str) or not packet or len(packet.encode())>48000 or '\x00' in packet:raise Denied('Invalid bounded recovery packet')
  if not isinstance(objective,str) or not objective.strip() or len(objective.encode())>4000:raise Denied('Explicit latest user objective required')
  # Packet must come from switcher.assemble, which sanitizes source bodies before
  # framing. Re-sanitizing the JSON envelope misclassifies long approved paths
  # as tokens and destroys provenance. Independently screen the user objective.
  if continuity.history.sanitize(objective)!=objective:raise Denied('Recovery packet requires privacy review; protected content refused')
  digest=continuity.digest([sid,provider,packet,objective])
  prior=self.db.execute('SELECT id FROM switches WHERE id=?',(tid,)).fetchone()
  if prior:
   tx=self.transaction(tid)
   if tx['hash']!=digest:raise Denied('Transaction identity reused for changed evidence')
   return tx
  row=next((r for r in self.preview(provider) if r['id']==sid),None)
  if not row or not row['eligible']:raise Denied((row or {}).get('exclusion','Unknown managed session'))
  target=str(uuid.uuid4());path=self.root/(tid+'.handoff')
  # Owner-only immutable operational packet, produced by the existing recovery system.
  fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
  with os.fdopen(fd,'w') as out:out.write(packet);out.flush();os.fsync(out.fileno())
  try:
   with self.db:
    self.db.execute('BEGIN IMMEDIATE')
    if self.db.execute("SELECT 1 FROM switches WHERE source=? AND stage NOT IN ('source_retained','failed','revoked')",(sid,)).fetchone():raise Denied('Concurrent switch for this session')
    for locked in self.db.execute('SELECT project FROM project_locks').fetchall():
     if overlaps(locked[0],row['cwd']):raise Denied('Overlapping project switch lock')
    self.db.execute('INSERT INTO project_locks VALUES (?,?)',(row['cwd'],tid))
    self.db.execute('INSERT INTO switches VALUES (?,?,?,?,?,?,?,?,?,?,?)',(tid,sid,target,provider,'locked',str(path),digest,objective,row['project'],0,None))
    self.event(tid,'discovered');self.event(tid,'eligible');self.event(tid,'locked');self.event(tid,'checkpointing');self.event(tid,'checkpoint_validated')
    details=self.details(sid);details['checkpoint']=tid;details['pending_switch']=tid
    self.db.execute('INSERT OR REPLACE INTO session_details VALUES (?,?)',(sid,json.dumps(details)))
    destination=dict(details,task_state='switching')
    self.db.execute('INSERT OR REPLACE INTO session_details VALUES (?,?)',(target,json.dumps(destination)))
  except BaseException:
   # Keep the inspectable orphan packet after failed journal commit; never launch it.
   raise
  return self.transaction(tid)
 def validate(self,tid):
  tx=self.transaction(tid);fd=private_file(tx['packet'])
  try:
   raw=os.read(fd,48001)
   if len(raw)>48000:raise Denied('Checkpoint oversized')
   packet=raw.decode()
  finally:os.close(fd)
  if continuity.digest([tx['source'],tx['provider'],packet,tx['objective']])!=tx['hash']:raise Denied('Checkpoint evidence changed')
  source=self.inspect(self.root,tx['source'])
  if source['project']!=tx['project'] or source['status']!='exited' or source.get('reachability')!='reachable' or not source.get('agent_process_group_quiescent') or not source.get('output_complete'):raise Denied('Source project/quiescence/output drain changed')
  info=Path(source['cwd']).stat()
  if (info.st_dev,info.st_ino)!=(source['dev'],source['ino']):raise Denied('Project directory identity changed')
  for row in self.db.execute('SELECT id FROM sessions WHERE id NOT IN (?,?)',(tx['source'],tx['target'])).fetchall():
   other=self.inspect(self.root,row[0])
   if (other['status']!='exited' or not other.get('agent_process_group_quiescent') or not other.get('output_complete')) and overlaps(source['cwd'],other['cwd']):raise Denied('Conflicting project writer or unresolved process group')
  return tx,packet,source
 def authorize(self,tid,approved_hash):
  tx,packet,source=self.validate(tid)
  if tx['hash']!=approved_hash:raise Denied('Approval does not match inspected checkpoint')
  if tx['stage']!='checkpoint_validated':raise Denied('Transaction cannot be authorized at this stage')
  with self.db:
   self.db.execute('UPDATE switches SET authorized=1 WHERE id=?',(tid,));self.event(tid,'target_launch_authorized')
 def revoke(self,tid):
  tx=self.transaction(tid)
  with self.db:
   self.db.execute('UPDATE switches SET authorized=0 WHERE id=?',(tid,));self.event(tid,'revoked')
   # A launched target might still write. Its lock is deliberately retained.
   if tx['stage'] in ('checkpoint_validated','target_launch_authorized'):self.db.execute('DELETE FROM project_locks WHERE transaction_id=?',(tid,))
 def execute(self,tid,launcher):
  # Serialize the durable launch decision, then commit before external launch.
  # Concurrent workers see the launching marker and cannot both spawn.
  with self.db:
   self.db.execute('BEGIN IMMEDIATE')
   tx,packet,source=self.validate(tid)
   if not tx['authorized']:raise Denied('Launch approval missing or revoked')
   if tx['stage'] in ('target_started','recovery_verifying','source_retained'):return tx
   if tx['stage']=='target_launching':raise Denied('Interrupted launch; reconcile target identity; never blindly retry')
   if tx['stage']!='target_launch_authorized':raise Denied('Invalid launch stage')
   self.event(tid,'target_launching')
  try:
   launcher(self.root,source['cwd'],tx['target'],tx['provider'],packet)
  except Exception as error:
   with self.db:
    self.db.execute('UPDATE switches SET error=? WHERE id=?',('Target launch unresolved; inspect stable target identity',tid))
   raise Denied('Target launch unresolved; source retained; transaction '+tid) from error
  with self.db:self.event(tid,'target_started');self.event(tid,'recovery_verifying')
  return self.transaction(tid)
 def reconcile(self,tid):
  tx=self.transaction(tid)
  if tx['stage']!='target_launching':return tx
  target=self.inspect(self.root,tx['target'])
  if target.get('reachability')!='reachable' or target['provider']!=tx['provider'] or target['project']!=tx['project']:raise Denied('Target identity not verified; source retained')
  with self.db:self.event(tid,'target_started');self.event(tid,'recovery_verifying')
  return self.transaction(tid)
 def verify(self,tid,receipt):
  if not self.synthetic:raise Denied('Native recovery acknowledgement adapter unsupported; caller-supplied receipts cannot prove provider recovery')
  tx,packet,source=self.validate(tid)
  if not tx['authorized'] or tx['stage']!='recovery_verifying':raise Denied('Recovery is not authorized/ready')
  target=self.inspect(self.root,tx['target'])
  expected={'target':tx['target'],'project':tx['project'],'objective':tx['objective'],'checkpoint':tx['hash'],'provider':tx['provider']}
  if receipt!=expected or target['status'] not in ('live','detached') or target.get('reachability')!='reachable' or target['provider']!=tx['provider'] or target['project']!=tx['project']:raise Denied('Recovery receipt mismatch; launch is not recovery success')
  with self.db:
   self.event(tid,'recovery_passed');self.event(tid,'target_active');self.event(tid,'source_retained')
   details=self.details(tx['source']);details.update(last_verified_recovery=tid,pending_switch=None)
   self.db.execute('INSERT OR REPLACE INTO session_details VALUES (?,?)',(tx['source'],json.dumps(details)))
   details.update(task_state='recovered')
   self.db.execute('INSERT OR REPLACE INTO session_details VALUES (?,?)',(tx['target'],json.dumps(details)))
   # A verified target may still write, including while detached. Keep the
   # project lease for its lifetime; there is no automatic unlock on success.
  return self.transaction(tid)
 def acknowledge(self,tid,answers,output):
  """Record an operator's review of actual destination PTY output.

  This is an explicit human attestation, not a model-authored or cryptographic
  semantic proof. The caller must capture bounded output from the target PTY.
  """
  if self.synthetic:raise Denied('Synthetic sessions use the synthetic receipt test path')
  if not isinstance(output,bytes) or not output or len(output)>65536:raise Denied('Destination has no bounded recovery output to inspect')
  tx,packet,source=self.validate(tid)
  if not tx['authorized'] or tx['stage']!='recovery_verifying':raise Denied('Recovery is not authorized/ready')
  target=self.inspect(self.root,tx['target'])
  if target.get('reachability')!='reachable' or target['status'] not in ('live','detached') or target['provider']!=tx['provider'] or target['project']!=tx['project']:
   raise Denied('Destination identity/status changed; recovery remains unverified')
  required={'session':tx['target'],'project':tx['project'],'objective':tx['objective'],'checkpoint':tx['hash'],'provider':tx['provider']}
  if not isinstance(answers,dict) or any(answers.get(key)!=value for key,value in required.items()):
   raise Denied('Operator acknowledgement did not match session, project, objective, checkpoint and provider')
  pending=answers.get('pending')
  if not isinstance(pending,str) or len(pending.strip())<8 or len(pending.encode())>1000:
   raise Denied('Operator must inspect and record the next pending item')
  evidence={'method':'interactive-operator-review-v1','target':tx['target'],'provider':tx['provider'],
            'project':tx['project'],'objective_hash':hashlib.sha256(tx['objective'].encode()).hexdigest(),
            'checkpoint_hash':tx['hash'],'output_sha256':hashlib.sha256(output).hexdigest(),
            'output_bytes':len(output),'pending':pending,'operator_confirmed':True}
  with self.db:
   self.db.execute('CREATE TABLE IF NOT EXISTS recovery_acknowledgements (transaction_id TEXT PRIMARY KEY, evidence TEXT NOT NULL)')
   self.db.execute('INSERT INTO recovery_acknowledgements VALUES (?,?)',(tid,json.dumps(evidence,sort_keys=True)))
   self.event(tid,'recovery_passed');self.event(tid,'target_active');self.event(tid,'source_retained')
   details=self.details(tx['source']);details.update(last_verified_recovery=tid,pending_switch=None)
   self.db.execute('INSERT OR REPLACE INTO session_details VALUES (?,?)',(tx['source'],json.dumps(details)))
   details.update(task_state='operator_verified_recovered',recovery_acknowledgement=tid)
   self.db.execute('INSERT OR REPLACE INTO session_details VALUES (?,?)',(tx['target'],json.dumps(details)))
  return self.transaction(tid)
 def release_project(self,sid):
  """Explicitly release a managed writer reservation after observed quiescence."""
  session_id(sid);target=self.inspect(self.root,sid)
  if target.get('reachability')!='reachable' or target.get('status')!='exited' or not target.get('agent_process_group_quiescent') or not target.get('output_complete'):
   raise Denied('Project reservation retained: target has not exited with a drained PTY and absent owned process group')
  locks=self.db.execute('SELECT project,transaction_id FROM project_locks').fetchall();released=[]
  for project,tid in locks:
   if not overlaps(project,target['cwd']):continue
   tx=self.transaction(tid)
   if tx['target']!=sid:raise Denied('Project reservation belongs to a different session')
   released.append(tid)
  if not released:raise Denied('No project reservation belongs to this session')
  rows=[self.inspect(self.root,row[0]) for row in self.db.execute('SELECT id FROM sessions WHERE id<>?',(sid,)).fetchall()]
  if any((row.get('status')!='exited' or not row.get('agent_process_group_quiescent') or not row.get('output_complete')) and overlaps(target['cwd'],row['cwd']) for row in rows):
   raise Denied('Overlapping managed writer remains; project reservation retained')
  with self.db:
   for tid in released:self.db.execute('DELETE FROM project_locks WHERE transaction_id=?',(tid,))
  return {'session':sid,'released_transactions':released}
