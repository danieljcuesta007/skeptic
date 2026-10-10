"""Job-control acceptance with fake agents only; no real provider or session access."""
import os,pty,re,select,shlex,sys,tempfile,time,unittest
from pathlib import Path
class TerminalLifecycleTests(unittest.TestCase):
 @unittest.skipUnless(sys.platform=='darwin','Mac zsh job-control fixture')
 def test_suspend_switch_same_tty_resume_original(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp).resolve();original=root/'original.py';destination=root/'fake-codex'
   original.write_text('import os,sys\nprint("ORIGINAL_TTY="+os.ttyname(0),flush=True)\nprint("ORIGINAL_READY",flush=True)\ninput()\nprint("ORIGINAL_RESUMED",flush=True)\n')
   destination.write_text('#!'+sys.executable+'\nimport os\nprint("DESTINATION_TTY="+os.ttyname(0),flush=True)\nprint("DESTINATION_CWD="+os.getcwd(),flush=True)\n');destination.chmod(0o700)
   wrapper=root/'launch.py';wrapper.write_text('import sys\nsys.path.insert(0,'+repr(str(Path(__file__).parent))+')\nimport switcher\nswitcher.launch({"executable":'+repr(str(destination))+',"local":False},'+repr(str(root))+',"Synthetic approved handoff")\nprint("SWITCH_COMPLETE",flush=True)\n')
   before=original.read_bytes();pid,fd=pty.fork()
   if pid==0:os.execv('/bin/zsh',['zsh','-f','-i'])
   data=b''
   def until(marker):
    nonlocal data
    end=time.monotonic()+8
    while marker.encode() not in data and time.monotonic()<end:
     if select.select([fd],[],[],.1)[0]:
      try:data+=os.read(fd,65536)
      except OSError:break
    self.assertIn(marker.encode(),data)
   try:
    os.write(fd,(shlex.quote(sys.executable)+' -B '+shlex.quote(str(original))+'\n').encode());until('ORIGINAL_READY')
    os.write(fd,b'\x1a');os.write(fd,b'print SHELL_READY\n');until('SHELL_READY')
    os.write(fd,(shlex.quote(sys.executable)+' -B '+shlex.quote(str(wrapper))+'\n').encode());until('SWITCH_COMPLETE')
    text=data.decode(errors='replace');self.assertEqual(re.search(r'ORIGINAL_TTY=(\S+)',text)[1],re.search(r'DESTINATION_TTY=(\S+)',text)[1]);self.assertIn('DESTINATION_CWD='+str(root),text)
    self.assertEqual(original.read_bytes(),before)
    os.write(fd,b'fg\n');time.sleep(.1);os.write(fd,b'continue\n');until('ORIGINAL_RESUMED')
    os.write(fd,b'exit\n')
   finally:
    os.close(fd);os.waitpid(pid,0)
if __name__=='__main__':unittest.main()
