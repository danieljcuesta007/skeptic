"""Run all synthetic regression suites from any working directory."""
from pathlib import Path
import os
import subprocess
import sys
root=Path(__file__).resolve().parents[1]
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
website=root/'apps/website';discovery=root/'packages/discovery'
commands=[(root/'apps/terminal',[sys.executable,'-B','mutation_managed.py']), (root/'apps/terminal',[sys.executable,'-B','-W','error::ResourceWarning','-m','unittest','-v','test_managed.py']),(root/'apps/terminal',[sys.executable,'-B','mutation_frozen.py']),(root/'apps/terminal',[sys.executable,'-B','mutation_recovery.py']),(root/'apps/desktop',[sys.executable,'-B','mutation_check.py']),(root/'apps/desktop',[sys.executable,'-W','error::ResourceWarning','-m','unittest','-v','test_desktop.py']),(root/'apps/terminal',[sys.executable,'-W','error::ResourceWarning','-m','unittest','-v','test_switcher.py','test_sessions.py','test_continuity.py','test_recovery.py','test_frozen.py','test_terminal_lifecycle.py']),
 (root/'apps/terminal',[sys.executable,'-B','mutation_check.py']),(root/'apps/terminal',[sys.executable,'-B','mutation_sessions.py']),(root/'apps/terminal',[sys.executable,'-B','mutation_continuity.py']),(root,[sys.executable,'-m','unittest','discover','-s','tests','-p','test_*.py']),(website,['npm','run','build']),(website,['npm','test']),(website,['node','mutation-check.mjs']),
 (root/'apps/local',[sys.executable,'build.py']),
 (root/'apps/local',[sys.executable,'-W','error::ResourceWarning','-m','unittest','-v','test_app.py','test_workspace.py','test_usage.py']),
 (root/'apps/local',[sys.executable,'mutation_usage.py']),
 (root/'apps/local',[sys.executable,'mutation_check.py']),
 (root/'apps/local',[sys.executable,'mutation_workspace.py']),
 (root/'apps/local',[sys.executable,'mutation_brand.py']),
 (root/'apps/local',['node','--check','app.js']),
 (root/'apps/local',['node','--test','test_usage_ui.mjs']),
 (root/'apps/local',['node','mutation_usage_ui.mjs']),
 (discovery,[sys.executable,'-W','error::ResourceWarning','-m','unittest','-v','test_engine.py','test_security.py']),
 (discovery,[sys.executable,'mutation_check_v2.py']),
 (discovery,[sys.executable,'mutation_check_security.py']),
 (discovery/'baseline-v1',[sys.executable,'-W','error::ResourceWarning','-m','unittest','-v','test_discovery.py']),
 (discovery/'baseline-v1',[sys.executable,'mutation_check.py'])]
for cwd,command in commands:
 print('Validate:',str(cwd.relative_to(root)), ' '.join(command),flush=True)
 subprocess.run(command,cwd=cwd,env=env,check=True)
print('All validation commands passed.')
