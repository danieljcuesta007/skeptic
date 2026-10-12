"""Offline host contract adapters; no installation, credentials or provider execution."""
from pathlib import Path
import json,shutil
from checkpoints import Rejected
AGENTS=('claude','hermes','codex')

def event(agent,payload):
 if agent not in AGENTS or not isinstance(payload,dict):raise Rejected('Unsupported event')
 raw=json.dumps(payload)
 if len(raw.encode())>16384:raise Rejected('Event exceeds bound')
 if agent=='claude':
  kind=payload.get('hook_event_name');sid=payload.get('session_id');cwd=payload.get('cwd')
  if kind not in ('SessionStart','Stop','SessionEnd'):raise Rejected('Unsupported Claude event')
 else:kind=payload.get('event');sid=payload.get('session_id');cwd=payload.get('cwd')
 if not all(isinstance(v,str) and v and len(v)<4096 and not any(ord(c)<32 for c in v) for v in (kind,sid,cwd)):raise Rejected('Invalid event identity')
 return {'version':1,'agent':agent,'session_id':sid,'cwd':cwd,'event':kind,'provenance':'host_reported' if agent=='claude' else 'caller_reported','association':'unconfirmed','activity':'unknown','writer':'unknown','automatic_actions':[]}

def package_skill(source,destination,agent):
 if agent not in AGENTS:raise Rejected('Unsupported host')
 source=Path(source);destination=Path(destination)
 if destination.exists():raise Rejected('Existing configuration preserved')
 if not (source/'SKILL.md').is_file():raise Rejected('Skill missing')
 # Caller provides an isolated directory; this helper never chooses a host home.
 import tempfile
 resolved=destination.parent.resolve(strict=True)
 if Path(tempfile.gettempdir()).resolve() not in [resolved,*resolved.parents] and Path('/private/tmp') not in [resolved,*resolved.parents]:raise Rejected('Only disposable skill roots supported')
 shutil.copytree(source,destination,symlinks=False)
 return {'agent':agent,'path':str(destination),'status':'packaged_offline','runtime_loaded':False}

if __name__=='__main__':
 import sys
 try:
  data=sys.stdin.buffer.read(16385)
  if len(data)>16384:raise Rejected('Input exceeds bound')
  print(json.dumps(event('claude',json.loads(data))))
 except (Rejected,ValueError):sys.exit(2)
