"""End to end: the one-line installer, run against a fake home with a local archive."""
import hashlib
import os
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'apps/website/install.sh'


class InstallScriptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='skeptic-install-')).resolve()  # /var is a symlink on macOS
        self.home = self.tmp / 'home'; self.home.mkdir()
        self.archive = self.tmp / 'skeptic-0.1.0.tar.gz'
        # The same file set as scripts/release.sh (git archive): every tracked file,
        # read from the working tree so uncommitted changes are tested too.
        tracked = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, capture_output=True, check=True).stdout.decode().split('\0')
        with tarfile.open(self.archive, 'w:gz') as tar:
            for name in filter(None, tracked):
                if (ROOT / name).exists(): tar.add(ROOT / name, arcname='skeptic-0.1.0/' + name, recursive=False)
        self.sha = hashlib.sha256(self.archive.read_bytes()).hexdigest()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_installer(self, sha):
        script = self.tmp / 'install.sh'
        script.write_text(SCRIPT.read_text().replace('SHA256="UNRELEASED"', f'SHA256="{sha}"'))
        env = dict(os.environ, HOME=str(self.home), SKEPTIC_URL=self.archive.as_uri())
        return subprocess.run(['sh', str(script), '--no-profile'], env=env, capture_output=True, text=True, timeout=120)

    def test_verified_archive_installs_a_working_command_and_helpers(self):
        result = self.run_installer(self.sha)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('checksum verified', result.stdout)
        launcher = self.home / '.local/bin/skeptic'
        help_text = subprocess.run([str(launcher), '--help'], capture_output=True, text=True, env=dict(os.environ, HOME=str(self.home)))
        self.assertEqual(help_text.returncode, 0, help_text.stderr)
        self.assertIn('continue', help_text.stdout)
        self.assertTrue((self.home / '.claude/skills/skeptic/SKILL.md').exists())
        self.assertTrue((self.home / '.local/share/skeptic/0.1.0/apps/terminal/switcher.py').exists())
        self.assertFalse((self.home / '.zshrc').exists(), '--no-profile is passed through')

    def test_upgrade_prunes_old_versions_but_nothing_else(self):
        share = self.home / '.local/share/skeptic'
        (share / '0.0.9/apps/terminal').mkdir(parents=True)
        (share / '0.0.9/apps/terminal/install.py').write_text('# old')
        (share / '1.0-notes').mkdir()  # looks like a version but isn't Skeptic
        result = self.run_installer(self.sha)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((share / '0.0.9').exists())
        self.assertTrue((share / '1.0-notes').exists())
        self.assertTrue((share / '0.1.0').exists())

    def test_tampered_archive_installs_nothing(self):
        result = self.run_installer('0' * 64)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('checksum mismatch', result.stderr)
        self.assertFalse((self.home / '.local').exists())

    def test_unreleased_script_refuses_politely(self):
        result = self.run_installer('UNRELEASED')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('no release is published yet', result.stderr)
        self.assertFalse((self.home / '.local').exists())


if __name__ == '__main__':
    unittest.main()
