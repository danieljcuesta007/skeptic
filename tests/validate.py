"""Run all synthetic regression suites from any working directory."""
from pathlib import Path
import os
import argparse
import subprocess
import sys
root=Path(__file__).resolve().parents[1]
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
website=root/'apps/website';discovery=root/'packages/discovery'
commands=[(root/'apps/terminal',[sys.executable,'-B','mutation_checkpoints.py']),(root/'apps/terminal',[sys.executable,'-B','-W','error::ResourceWarning','-m','unittest','-v','test_checkpoints','test_recovery_contract','test_continuity_service']),(root/'apps/terminal',[sys.executable,'-B','mutation_integration.py']),(root/'apps/terminal',[sys.executable,'-B','-W','error::ResourceWarning','-m','unittest','-v','test_managed_hardening','test_managed_providers','test_managed_switch','test_managed_switch_cli','test_managed_migration']),(root/'apps/terminal',[sys.executable,'-B','mutation_managed.py']), (root/'apps/terminal',[sys.executable,'-B','-W','error::ResourceWarning','-m','unittest','-v','test_managed.py']),(root/'apps/terminal',[sys.executable,'-B','mutation_frozen.py']),(root/'apps/terminal',[sys.executable,'-B','mutation_recovery.py']),(root/'apps/desktop',[sys.executable,'-B','mutation_check.py']),(root/'apps/desktop',[sys.executable,'-W','error::ResourceWarning','-m','unittest','-v','test_desktop.py']),(root/'apps/terminal',[sys.executable,'-W','error::ResourceWarning','-m','unittest','-v','test_switcher.py','test_picker.py','test_sessions.py','test_session_review.py','test_open_sessions.py','test_one_command.py','test_candidate_identification.py','test_continuity.py','test_recovery.py','test_frozen.py','test_terminal_lifecycle.py']),
 (root/'apps/terminal',[sys.executable,'-B','mutation_check.py']),(root/'apps/terminal',[sys.executable,'-B','mutation_sessions.py']),(root/'apps/terminal',[sys.executable,'-B','mutation_one_command.py']),(root/'apps/terminal',[sys.executable,'-B','mutation_continuity.py']),(root,[sys.executable,'-m','unittest','discover','-s','tests','-p','test_*.py']),(website,['npm','run','build']),(website,['npm','test']),(website,['node','mutation-check.mjs']),
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
parser=argparse.ArgumentParser(description='Full synthetic validation; native models are never invoked')
parser.add_argument('--without-managed-runtime',action='store_true',help='Explicit partial validation: excludes managed socket lifecycle and its mutations; cannot establish full acceptance')
args=parser.parse_args()
for cwd,command in commands:
 if args.without_managed_runtime and any(part in ('test_managed.py','mutation_managed.py') for part in command):
  print('NOT RUN (explicit partial scope): '+' '.join(command),flush=True)
  continue
 print('Validate:',str(cwd.relative_to(root)), ' '.join(command),flush=True)
 subprocess.run(command,cwd=cwd,env=env,check=True)
print('Selected socket-independent validation passed; managed runtime and its faults NOT VERIFIED.' if args.without_managed_runtime else 'All validation commands passed.')
