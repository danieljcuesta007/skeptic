"""Read-only current-user TTY inventory; launch identity only, no transcripts."""
import ast,ctypes,os,re,struct,subprocess,sys
from pathlib import Path

def python_agent(argv):
 if not argv or len(argv)>4096:return None
 args=argv[1:]
 if "--run-module" in args:return None
 if "-m" in args:
  i=args.index("-m")
  if i+1>=len(args) or args[i+1] not in ("hermes_cli","hermes_cli.main"):return None
  rest=args[i+2:]
 elif "-c" in args:
  i=args.index("-c")
  if i+1>=len(args) or len(args[i+1])>128*1024:return None
  try:tree=ast.parse(args[i+1])
  except (SyntaxError,ValueError,RecursionError):return None
  imported=any(isinstance(n,ast.ImportFrom) and n.module=="hermes_cli.main" and any(a.name=="main" and a.asname is None for a in n.names) for n in tree.body)
  if not imported or not tree.body:return None
  last=tree.body[-1]
  expected=ast.parse("sys.exit(main())").body[0]
  if ast.dump(last)!=ast.dump(expected):return None
  rest=args[i+2:]
 else:return None
 # Do not count gateway, update, tool module or other non-chat commands.
 if rest and not rest[0].startswith("-") and rest[0]!="chat":return None
 return "Hermes"

def process_argv(pid):
 """Darwin KERN_PROCARGS2: return argv only; never decode environment fields."""
 if sys.platform!="darwin":return []
 libc=ctypes.CDLL(None,use_errno=True)
 mib=(ctypes.c_int*3)(1,49,pid)
 size=ctypes.c_size_t(0)
 if libc.sysctl(mib,3,None,ctypes.byref(size),None,0)!=0 or not 4<size.value<=1024*1024:return []
 buf=ctypes.create_string_buffer(size.value)
 if libc.sysctl(mib,3,buf,ctypes.byref(size),None,0)!=0:return []
 raw=buf.raw[:size.value];argc=struct.unpack_from("i",raw)[0]
 if not 0<argc<=4096:return []
 pos=raw.find(b"\0",4)+1
 if pos<=4:return []
 while pos<len(raw) and raw[pos]==0:pos+=1
 argv=[]
 for _ in range(argc):
  end=raw.find(b"\0",pos)
  if end<0:return []
  argv.append(raw[pos:end].decode("utf-8","replace"));pos=end+1
 return argv

def parse(raw, uid, python_agents=None):
 terminals=set();agents=[];unidentified=0
 for line in raw.splitlines():
  parts=line.strip().split(None,3)
  if len(parts)!=4:continue
  owner,pid,tty,comm=parts
  if owner!=str(uid) or not pid.isdigit() or not tty.startswith("ttys") or not tty[4:].isdigit():continue
  terminals.add(tty);name=Path(comm).name
  agent={"claude":"Claude Code","claude-code":"Claude Code","codex":"Codex","hermes":"Hermes"}.get(name)
  if "/.local/share/claude/versions/" in comm:agent="Claude Code"
  if re.fullmatch(r"python(?:[0-9]+(?:\.[0-9]+)*)?",name):
   agent=(python_agents or {}).get(int(pid))
   if not agent:unidentified+=1
  if agent:agents.append({"agent":agent,"tty":tty,"pid":int(pid),"model":"unknown","activity":"unknown"})
 return {"terminals":len(terminals),"ttys":sorted(terminals),"agents":agents,"unidentified_python":unidentified,"scope":"TTYs with current-user processes; not Terminal window or saved conversation counts. Python launch entry points are checked locally; arguments are not retained. Model and activity unknown.","status":"observed"}

def collect():
 try:
  p=subprocess.run(["/bin/ps","-axo","uid=,pid=,tty=,comm="],capture_output=True,text=True,timeout=3,check=True)
  if len(p.stdout)>1024*1024:raise ValueError("Metadata too large")
  identified={}
  for line in p.stdout.splitlines():
   parts=line.strip().split(None,3)
   if len(parts)!=4:continue
   owner,pid,tty,comm=parts
   if owner!=str(os.getuid()) or not pid.isdigit() or not re.fullmatch(r"ttys[0-9]+",tty):continue
   if not re.fullmatch(r"python(?:[0-9]+(?:\.[0-9]+)*)?",Path(comm).name):continue
   argv=process_argv(int(pid))
   if argv and os.path.realpath(argv[0])==os.path.realpath(comm):
    agent=python_agent(argv)
    if agent:identified[int(pid)]=agent
  return parse(p.stdout,os.getuid(),identified)
 except (OSError,ValueError,subprocess.SubprocessError):return {"terminals":None,"agents":[],"unidentified_python":None,"status":"unknown","scope":"Process metadata unavailable"}
