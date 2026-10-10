"""Provider-neutral offline handoff assessment and destination reconciliation."""
import checkpoints as c
from continuity_adapters import AGENTS

def assess(package,destination,source_identity='unknown',writer='unknown',destination_available=False):
 c.markdown(package)  # Validate immutable proposal envelope.
 reasons=[]
 if destination not in AGENTS:reasons.append('Unsupported destination')
 if source_identity!='confirmed':reasons.append('Source identity uncertain')
 if writer!='clear':reasons.append('Writer safety not established')
 if not destination_available:reasons.append('Destination unavailable/unconfigured')
 if not c.fresh(package['snapshot']):reasons.append('Source changed after review')
 for receipt in package['receipts']:
  state=c.receipt_state(receipt,package['snapshot'])
  if state!='command_passed':reasons.append('Verification '+state)
 return {'version':1,'state':'handoff_blocked' if reasons else 'awaiting_approval','reasons':reasons,'destination':destination,'package':package['fingerprint']}

def reconcile(package,actual_root,project_id,session_id,destination,acknowledged_pending,approved=False):
 if not approved:raise c.Rejected('Explicit reconciliation approval required')
 if destination not in AGENTS or not session_id:raise c.Rejected('Destination identity required')
 s=package['snapshot'];c.markdown(package)
 if project_id!=s['project_id'] or str(__import__('pathlib').Path(actual_root).resolve())!=s['root']:raise c.Rejected('Wrong project or worktree')
 if not c.fresh(s):raise c.Rejected('Stale package')
 if acknowledged_pending!=package['pending']:raise c.Rejected('Pending work not reconciled')
 return {'version':1,'package':package['fingerprint'],'project_id':project_id,'checkout':s['root'],'session_id':session_id,'agent':destination,'source_fingerprint':s['fingerprint'],'pending':list(acknowledged_pending),'timestamp':c.now(),'provenance':'explicit caller acknowledgement; not provider-native semantic proof'}

def complete(package,assessment,acknowledgement,reviewed_hash):
 if assessment!=assess(package,assessment['destination'],'confirmed','clear',True):raise c.Rejected('Assessment invalid or blocked')
 if assessment['state']!='awaiting_approval' or reviewed_hash!=package['fingerprint']:raise c.Rejected('Exact package approval required')
 if not isinstance(acknowledgement,dict) or acknowledgement.get('package')!=reviewed_hash or acknowledgement.get('agent')!=assessment['destination'] or acknowledgement.get('source_fingerprint')!=package['snapshot']['fingerprint'] or acknowledgement.get('pending')!=package['pending']:raise c.Rejected('Destination has not reconciled')
 if not c.fresh(package['snapshot']):raise c.Rejected('Source changed before completion')
 return {'state':'handoff_complete','verification':'offline_contract_only','package':reviewed_hash,'acknowledgement':acknowledgement}

def batch(items,destination):
 """Independent outcomes; never launch, interrupt or bypass a per-session gate."""
 results=[]
 for item in items:
  result=assess(item['package'],destination,item.get('identity','unknown'),item.get('writer','unknown'),item.get('available',False))
  result['session']=item['package']['session'];results.append(result)
 return results

def observation(packages):
 sessions=[]
 for p in packages:
  c.markdown(p);s=p['snapshot'];is_fresh=c.fresh(s)
  receipts=[c.receipt_state(r,s) for r in p['receipts']]
  readiness=assess(p,'hermes','unknown',p['writer'],False)
  sessions.append({'id':p['session'],'agent':p['agent'],'project':s['project_id'],'objective':p['objective'],'cwd':s['root'],'activity':'unknown','last_activity':None,'checkpoint':p['timestamp'],'checkpoint_fresh':is_fresh,'verification':'stale' if 'stale' in receipts else 'failed' if 'command_failed' in receipts else 'command_passed' if receipts else 'unknown','dirty':bool(s['status_hex']),'pending':p['pending'],'failures':p['failures'],'writer':p['writer'],'readiness':readiness['state'],'blocked_reasons':readiness['reasons'],'uncertainty':p['uncertainty']})
 return {'version':1,'engine':'offline_fixture','monitoring':'disabled','sessions':sessions,'capabilities':{'live_switch':False,'pause_monitoring':False,'checkpoint_write':'fixture_only'}}
