"""Prove preference security regressions fail against planted faults."""
from pathlib import Path
import subprocess,sys
p=Path(__file__).parents[1]/'local/preferences.py';original=p.read_text()
faults=[("type(data['welcomed']) is bool","True"),("os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK","os.O_RDONLY|os.O_NONBLOCK")]
try:
 for before,after in faults:
  assert before in original;p.write_text(original.replace(before,after,1).replace("type(value['welcomed']) is not bool", "False"))
  result=subprocess.run([sys.executable,'-B','-m','unittest','test_desktop.py'],cwd=Path(__file__).parent,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  if result.returncode==0:raise SystemExit('Planted fault escaped')
finally:p.write_text(original)
print('2 planted desktop faults caught')
