"""Explicit provider launch plans. No discovery of histories or existing processes."""
import os,re,shutil,stat,subprocess,uuid
from pathlib import Path
from managed_engine import Denied,fixture_path

VERSIONS={'claude':'2.1.296','codex':'0.162.0'}
CAPABILITIES={
 'fresh_launch':True,'conversation_resume':False,'documented_native_resume':True,'working_directory':True,
 'output_streaming':'owned PTY','exit_detection':'owned supervisor waitpid',
 'process_adoption':False,'safe_quiescence':False,'automatic_recovery_verification':False,
 'native_checkpoint':False,'authentication':'native CLI configuration; not inspected',
 'supervisor_restart_reattach':False,
}

def executable(provider,which=shutil.which):
 if provider not in VERSIONS:raise Denied('Unsupported provider')
 value=which(provider)
 if not value:raise Denied('Provider executable missing')
 path=Path(value).resolve(strict=True);info=path.stat()
 if not stat.S_ISREG(info.st_mode) or not os.access(path,os.X_OK):raise Denied('Provider executable unavailable')
 if info.st_mode & stat.S_IWOTH:raise Denied('World-writable provider executable refused')
 return str(path)

def probe(provider,run=subprocess.run,which=shutil.which):
 path=executable(provider,which)
 result=run([path,'--version'],capture_output=True,text=True,timeout=5,check=False)
 if result.returncode:raise Denied('Provider version probe failed')
 found=re.search(r'\b\d+\.\d+\.\d+\b',result.stdout)
 if not found or found[0]!=VERSIONS[provider]:raise Denied('Provider version not inspected; launch refused')
 return {'provider':provider,'executable':path,'version':found[0],
         'capabilities':dict(CAPABILITIES,native_session_identity='explicit UUID' if provider=='claude' else 'unavailable in interactive launch')}

def plan(provider,cwd,prompt='',native_id=None,approved=False,descriptor=None):
 if not approved:raise Denied('Explicit provider launch/context delivery approval required')
 cwd=fixture_path(cwd)
 if not cwd.is_dir():raise Denied('Temporary project required')
 if not isinstance(prompt,str) or len(prompt.encode())>48000 or '\x00' in prompt:raise Denied('Invalid or oversized handoff')
 info=descriptor or probe(provider)
 if info['provider']!=provider or info['version']!=VERSIONS.get(provider):raise Denied('Provider descriptor mismatch')
 # Revalidate the executable rather than accepting arbitrary commands from a descriptor.
 path=executable(provider,lambda _:info['executable'])
 argv=[path]
 if provider=='claude':
  native_id=str(uuid.UUID(native_id)) if native_id else str(uuid.uuid4())
  argv+=['--session-id',native_id]
 else:
  if native_id is not None:raise Denied('Codex fresh launch cannot assign a native session ID')
  # Never connect new tests to the shared server that may own user sessions.
  argv+=['--no-daemon','--cd',str(cwd)]
 if prompt:argv+=['--',prompt]
 return {'argv':argv,'cwd':str(cwd),'provider':provider,'native_id':native_id,'version':info['version']}
