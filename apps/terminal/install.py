"""Install an owner-local launcher and native handoff integrations; preserve existing files."""
import argparse
import hashlib
import os
from pathlib import Path
import shlex
import stat
import time
import sys

HERE = Path(__file__).resolve().parent
MARKER = '# Skeptic terminal PATH'
LEGACY_SKILLS = {'3e6a5458e20095613b14efa59806fe7a14570facbf4daa62a1659d95103605b1', 'fa46d1a626d7ea7a49929e17ae78ca365e2a5be93ec781fe0b4eac41048b1ae0', '1295e0560d0dac183f10a636b726bc611dd9ff5bb3484c5275bf2eef958f5286', '5c585bb4a704f8b5ec5a5b37d5f879fbbeaf5baee247726d30e4d53bf3af9e1f', '36bc21f2ac7cccbbafed1728c44aceb1b6962982db334529a8bd927a35877222'}  # + 12 Oct 2026 shipped versions


def safe_parent(path):
    for item in (path, *path.parents):
        if item.is_symlink(): raise ValueError('Refusing symlinked install directory: ' + str(item))
    path.mkdir(parents=True, exist_ok=True)


def write_owned(path, text, mode=0o600, upgrade=False):
    if path.is_symlink(): raise ValueError('Refusing symlink: ' + str(path))
    if path.exists():
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid(): raise ValueError('Unsafe install target')
        if path.read_text() == text:
            path.chmod(mode); return
        if upgrade and hashlib.sha256(path.read_bytes()).hexdigest() in LEGACY_SKILLS:
            fd = os.open(str(path), os.O_WRONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                current = os.fstat(fd)
                if (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino): raise ValueError('Install target changed')
                os.ftruncate(fd, 0); os.write(fd, text.encode()); os.fchmod(fd, mode)
            finally: os.close(fd)
            return
        raise ValueError('Existing file differs; preserved: ' + str(path))
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    with os.fdopen(fd, 'w') as out: out.write(text)


def install(home, integrations=True, profile=True, upgrade=False, launcher_too=True):
    home = Path(home)
    bindir = home / '.local/bin'
    if not launcher_too:  # a package manager owns the command; only the helpers go in
        install_skills(home, integrations, upgrade)
        print('Installed the skeptic helpers for Claude Code and Codex. The command itself comes from your package manager.')
        return
    safe_parent(bindir)
    launcher = '#!/bin/sh\n# Skeptic launcher; rerun installer after moving repository.\nexec ' + shlex.quote(sys.executable) + ' -B ' + shlex.quote(str(HERE / 'switcher.py')) + ' "$@"\n'
    try: write_owned(bindir / 'skeptic', launcher, 0o700)
    except ValueError as error:
        # A launcher this installer generated for another checkout (the repo
        # moved, or an old work branch): retarget it with a rollback copy.
        # activate_launcher still preserves any customized script.
        if not str(error).startswith('Existing file differs'): raise
        activate_launcher(home, HERE)
        print('Retargeted existing Skeptic launcher to ' + str(HERE) + ' (previous copy kept beside it)')
    if profile:
        target = home / '.zshrc'
        if target.is_symlink(): raise ValueError('Symlinked .zshrc preserved; add ~/.local/bin to PATH manually')
        fd = os.open(str(target), os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid() or info.st_size > 1_000_000: raise ValueError('Unsafe shell profile')
            text = os.read(fd, 1_000_001).decode()
            if MARKER not in text:
                os.lseek(fd, 0, os.SEEK_END)
                os.write(fd, ('\n' + MARKER + '\nexport PATH="$HOME/.local/bin:$PATH"\n').encode())
        finally: os.close(fd)
    install_skills(home, integrations, upgrade)
    print('Installed: ' + str(bindir / 'skeptic'))
    print('Existing terminals: export PATH="$HOME/.local/bin:$PATH"; rehash')
    print('From Claude: Ctrl+Z returns to the same shell without closing it; run skeptic. Second Terminal is the fallback.')


def install_skills(home, integrations=True, upgrade=False):
    if not integrations: return
    for provider, base in [('claude', home / '.claude/skills'), ('codex', home / '.agents/skills')]:
        if integrations is not True and provider not in integrations: continue
        folder = base / 'skeptic'; safe_parent(folder)
        write_owned(folder / 'SKILL.md', (HERE / ('skeptic-' + provider + '.md')).read_text(), upgrade=upgrade)


def activate_launcher(home, source=HERE):
    """Only retarget a recognized Skeptic launcher, keeping an exact rollback copy."""
    home, source = Path(home), Path(source)
    target = home / '.local/bin/skeptic'
    safe_parent(target.parent)
    if target.is_symlink(): raise ValueError('Symlinked launcher preserved')
    info = target.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_nlink != 1:
        raise ValueError('Unsafe launcher preserved')
    original = target.read_text()
    prefix = '#!/bin/sh\n# Skeptic launcher; rerun installer after moving repository.\nexec '
    # Recognized one-command generated launcher only; preserve customized scripts.
    if not original.startswith(prefix) or len(original.splitlines()) != 3:
        raise ValueError('Unrecognized launcher preserved')
    words = shlex.split(original.splitlines()[2])
    if len(words) != 5 or words[0] != 'exec' or words[2] != '-B' or words[4] != '$@' or not words[3].endswith('/apps/terminal/switcher.py'):
        raise ValueError('Customized launcher preserved')
    try: path = '$HOME/' + str(source.relative_to(home) / 'switcher.py')
    except ValueError: path = str(source / 'switcher.py')  # checkout outside home: absolute path
    if '"' in path.replace('$HOME/', '', 1) or '$' in path.replace('$HOME/', '', 1) or '`' in path or '\n' in path:
        raise ValueError('Unsupported launcher path')
    replacement = prefix + 'python3 -B "' + path + '" "$@"\n'
    if original == replacement: return target
    backup = target.with_name('skeptic.before-integration')
    if backup.exists() and backup.read_text() != original:  # keep every earlier rollback copy
        stamp, n = time.strftime('%Y%m%d-%H%M%S'), 0
        backup = target.with_name('skeptic.before-' + stamp)
        while backup.exists() and backup.read_text() != original:  # same-second retargets
            n += 1; backup = target.with_name(f'skeptic.before-{stamp}-{n}')
    write_owned(backup, original, stat.S_IMODE(info.st_mode))
    # Check again before replacing the owned file. Shell configuration is untouched.
    fd = os.open(target, os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        current = os.fstat(fd)
        if (current.st_dev, current.st_ino) != (info.st_dev, info.st_ino) or os.read(fd, 65537).decode() != original:
            raise ValueError('Launcher changed during activation; preserved')
        os.lseek(fd, 0, os.SEEK_SET); os.write(fd, replacement.encode()); os.ftruncate(fd, len(replacement.encode())); os.fsync(fd)
    finally: os.close(fd)
    return target

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--upgrade-integrations', action='store_true', help='Upgrade only recognized Step 43D helper files; preserve all other content')
    p.add_argument('--no-integrations', action='store_true')
    p.add_argument('--no-profile', action='store_true')
    p.add_argument('--integration', choices=['all', 'claude', 'codex', 'none'], default='all')
    p.add_argument('--skills-only', action='store_true', help='Only install the Claude Code/Codex helpers (Homebrew provides the command)')
    a = p.parse_args()
    selected = False if a.no_integrations or a.integration == 'none' else True if a.integration == 'all' else [a.integration]
    try: install(Path.home(), selected, not a.no_profile and not a.skills_only, a.upgrade_integrations, not a.skills_only)
    except (OSError, ValueError) as exc: print('Installation: ' + str(exc), file=sys.stderr); sys.exit(1)
