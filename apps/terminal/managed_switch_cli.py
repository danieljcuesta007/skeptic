"""CLI review and confirmation around the shared managed switch journal."""
import argparse,json,os,sqlite3,sys
from pathlib import Path
from managed_engine import Denied
from managed_switch import Manager

def main(argv=None):
 parser=argparse.ArgumentParser(description='Managed switching; active sources excluded; temporary projects only')
 parser.add_argument('provider',choices=['claude','codex','skeptic-fake-v1'])
 scope=parser.add_mutually_exclusive_group();scope.add_argument('--select',action='store_true');scope.add_argument('--all',action='store_true')
 parser.add_argument('--state',default=os.environ.get('SKEPTIC_MANAGED_STATE'));parser.add_argument('--id',default=os.environ.get('SKEPTIC_SESSION_ID'))
 parser.add_argument('--task',help='Explicit current user objective; required for recovery')
 parser.add_argument('--vault',default=str(Path.home()/'brain'));parser.add_argument('--permissions-state',default=str(Path.home()/'.skeptic-cli'))
 args=parser.parse_args(argv)
 if not args.state:raise Denied('Managed state required; existing unmanaged sessions are never adopted')
 manager=Manager(args.state,readonly=True)
 try:rows=manager.preview(args.provider)
 finally:manager.close()
 for index,row in enumerate(rows,1):
  print(str(index)+'. '+row['name']+' | '+row['cwd']+' | '+row['provider']+' -> '+row['destination']+' | '+row['terminal']+' | '+row['status']+' | '+('eligible' if row['eligible'] else row['exclusion'])+' | checkpoint '+('ready' if row['checkpoint_ready'] else 'needs preparation'))
 if args.all:selected=[r for r in rows if r['eligible']]
 elif args.select:
  value=input('Select session numbers, comma separated: ')
  try:numbers=list(dict.fromkeys(int(part.strip()) for part in value.split(',')))
  except ValueError:raise Denied('Invalid session selection')
  if any(n<1 or n>len(rows) for n in numbers):raise Denied('Unknown selection')
  selected=[rows[n-1] for n in numbers]
 else:selected=[r for r in rows if r['id']==args.id]
 if not selected:raise Denied('No eligible/current managed session selected')
 if any(not row['eligible'] for row in selected):raise Denied('Selection includes an excluded session')
 if not args.task:raise Denied('--task must state the latest genuine user objective; terminal output is not instruction evidence')
 # Each batch needs independently supplied objectives. Do not duplicate one task
 # across unrelated sessions. Read these explicitly from the user.
 objectives={row['id']:args.task if len(selected)==1 else input('Latest objective for '+row['name']+': ') for row in selected}
 print('Destination providers may consume quota and store the reviewed project context. Native config/hooks and permissions apply. Sources are retained. Cooperative locks do not control unmanaged agents; confirm those cannot write these projects.')
 if input('Type preflight to prepare reviewed packets for these projects: ')!='preflight':return 1
 from switcher import State,assemble
 import continuity
 import managed_cli
 manager=Manager(args.state)
 try:state=State(args.permissions_state)
 except BaseException:manager.close();raise
 results=[]
 try:
  for row in selected:
   try:
    summary,packet=assemble(state,Path(row['cwd']),Path(args.vault),task=objectives[row['id']])
    reviewed=continuity.digest({k:v for k,v in state.observation.items() if k!='observed_at'})
    tx=manager.prepare(row['id'],args.provider,packet,objectives[row['id']])
    print(packet);print('Checkpoint '+tx['id']+' hash '+tx['hash'])
    if input('Type send to approve this exact packet and launch: ')!='send':
     manager.revoke(tx['id']);results.append({'source':row['id'],'result':'revoked'});continue
    manager.authorize(tx['id'],tx['hash'])
    def launch(root,cwd,sid,provider,packet):
     # Refresh grants and exact bounded evidence using the existing engine.
     state.settings=state.read('settings.json',{'grants':{},'mappings':{},'recent':[],'analytics':False})
     state.no_new_grants=True
     fresh_summary,fresh_packet=assemble(state,Path(cwd),Path(args.vault),task=objectives[row['id']])
     fresh=continuity.digest({k:v for k,v in state.observation.items() if k!='observed_at'})
     if fresh!=reviewed or fresh_packet!=packet:raise Denied('Reviewed evidence/Git/grants changed; prepare a new checkpoint')
     # No fake context-recovery claim: the echo fixture has no recovery protocol.
     if provider=='skeptic-fake-v1':raise Denied('Fake echo agent has no recovery adapter; synthetic journal tests only')
     managed_cli.start(root,cwd,sid,provider=provider,approved=True,packet=packet)
    result=manager.execute(tx['id'],launch)
    results.append({'source':row['id'],'target':result['target'],'transaction':result['id'],'result':result['stage']})
    print('Target launched; recovery remains unverified. Attach using managed attach --state STATE --id '+result['target']+'. Source retained.')
   except (Denied,OSError,ValueError,sqlite3.DatabaseError,continuity.host.Denied) as error:results.append({'source':row['id'],'result':'failed','reason':str(error)})
 finally:manager.close();state.close()
 print(json.dumps(results,indent=2));return 0 if all(r['result']=='source_retained' for r in results) else 2
