"""Behavioral fault injection in disposable copies, never in production sources."""
from pathlib import Path
import os,shutil,subprocess,sys,tempfile
HERE=Path(__file__).resolve().parent
faults=[('stale_sources_accepted','checkpoints.py',"def fresh(snapshot):return refresh(snapshot)['fingerprint']==snapshot['fingerprint']",'def fresh(snapshot):return True','test_checkpoints.Checkpoints.test_stale_proposal'),('launch_counts_as_ack', 'recovery_contract.py', " if not isinstance(acknowledgement,dict) or acknowledgement.get('package')!=reviewed_hash or acknowledgement.get('agent')!=assessment['destination'] or acknowledgement.get('source_fingerprint')!=package['snapshot']['fingerprint'] or acknowledgement.get('pending')!=package['pending']:raise c.Rejected('Destination has not reconciled')", " if False:raise c.Rejected('Destination has not reconciled')", 'test_recovery_contract.Recovery.test_false_success_blocked'),('writer_approval_bypassed','checkpoint_writer.py',"if Path(approved_destination).is_symlink() or destination!=Path(approved_destination).resolve(strict=True) or approved_digest!=review(proposal):",'if False:','test_checkpoints.Checkpoints.test_fixture_write_preserves_and_rejects')]
for name,file,old,new,test in faults:
 with tempfile.TemporaryDirectory(prefix='sk-fault-') as t:
  root=Path(t)
  for source in HERE.glob('*.py'):shutil.copy2(source,root/source.name)
  text=(root/file).read_text()
  if old not in text:raise SystemExit('Mutation anchor missing: '+name)
  mutated=text.replace(old,new,1)
  if name=='launch_counts_as_ack':
   mutated='\n'.join(line for line in mutated.split('\n') if "raise c.Rejected('Destination identity not reconciled')" not in line)
  (root/file).write_text(mutated)
  # sessions/app dependencies are original modules; mutation files remain first on sys.path.
  env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(HERE)+os.pathsep+str(HERE.parent/'local'))
  result=subprocess.run([sys.executable,'-B','-m','unittest',test],cwd=root,env=env,capture_output=True,text=True,timeout=45)
  if result.returncode==0 or 'FAIL:' not in result.stderr:raise SystemExit('Fault not caught by assertion: '+name+'\n'+result.stderr[-2000:])
  print('Caught planted fault: '+name)
print('3/3 checkpoint/recovery/writer faults caught')
