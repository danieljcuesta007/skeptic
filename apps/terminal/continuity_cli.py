"""Explicit local checkpoint proposal command; no writes, providers or discovery."""
import argparse,json,sys
from pathlib import Path
import checkpoints as c
import recovery_contract as recovery

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('command',choices=['propose','observe'])
 p.add_argument('--root',required=True);p.add_argument('--project-id',required=True);p.add_argument('--canonical',required=True)
 p.add_argument('--canonical-root',help='Separately approved canonical Markdown root');p.add_argument('--source',action='append',default=[]);p.add_argument('--agent',choices=['claude','hermes','codex'],required=True);p.add_argument('--session',required=True);p.add_argument('--objective',required=True)
 p.add_argument('--pending',action='append',default=[]);p.add_argument('--json',action='store_true')
 a=p.parse_args();scope=list(dict.fromkeys([a.canonical,*a.source]));snapshot=c.inspect(Path(a.root),scope,a.project_id,a.canonical,a.canonical_root)
 package=c.proposal(snapshot,a.agent,a.session,a.objective,pending=a.pending)
 if a.command=='observe':print(json.dumps(recovery.observation([package]),indent=2))
 elif a.json:print(json.dumps(package,indent=2))
 else:print(c.markdown(package))
if __name__=='__main__':
 try:main()
 except (c.Rejected,OSError,ValueError) as e:print('Checkpoint refused: '+str(e),file=sys.stderr);sys.exit(2)
