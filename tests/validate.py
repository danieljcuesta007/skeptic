"""Run all synthetic regression suites from any working directory."""
from pathlib import Path
import os
import subprocess
import sys
root=Path(__file__).resolve().parents[1]
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
website=root/'apps/website';discovery=root/'packages/discovery'
commands=[(root,[sys.executable,'-m','unittest','discover','-s','tests','-p','test_*.py']),(website,['npm','run','build']),(website,['npm','test']),(website,['node','mutation-check.mjs']),
 (discovery,[sys.executable,'-W','error::ResourceWarning','-m','unittest','-v','test_engine.py','test_security.py']),
 (discovery,[sys.executable,'mutation_check_v2.py']),
 (discovery,[sys.executable,'mutation_check_security.py']),
 (discovery/'baseline-v1',[sys.executable,'-W','error::ResourceWarning','-m','unittest','-v','test_discovery.py']),
 (discovery/'baseline-v1',[sys.executable,'mutation_check.py'])]
for cwd,command in commands:
 print('Validate:',str(cwd.relative_to(root)), ' '.join(command),flush=True)
 subprocess.run(command,cwd=cwd,env=env,check=True)
print('All validation commands passed.')
