import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

class MigrationTests(unittest.TestCase):
    def test_demo_works_inside_git_project_without_creating_index_in_repository(self):
        root=Path(__file__).resolve().parents[1]
        result=subprocess.run([sys.executable,str(root/'packages/discovery/run_demo.py')],
                              cwd=root,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),
                              check=True,capture_output=True,text=True)
        receipt=json.loads(result.stdout)
        self.assertEqual(receipt['project'],'atlas')
        self.assertFalse(receipt['limitations']['network'])
        self.assertFalse((root/'packages/discovery/sample-index.json').exists())
