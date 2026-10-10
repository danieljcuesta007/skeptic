"""Create only the public UI bundle. Project state and context are never build inputs."""
from pathlib import Path
from app import public_assets, ASSETS as ROUTES

ROOT = Path(__file__).resolve().parent
ASSETS = ('index.html', 'app.js', 'style.css')


def build():
    public = public_assets()  # Refuse symlinks, hard links and unsafe source assets.
    target = ROOT / 'dist'
    if target.is_symlink(): raise ValueError('Refuse linked build output')
    if target.exists():
        if set(p.name for p in target.iterdir()) - set(ASSETS):
            raise ValueError('Unexpected build output; inspect manually')
        for p in target.iterdir():
            if p.is_symlink() or not p.is_file(): raise ValueError('Unsafe build output')
            p.unlink()
    else:
        target.mkdir()
    for name in ASSETS:
        route = next(route for route, (filename, _) in ROUTES.items() if filename == name)
        (target / name).write_bytes(public[route][0])
    print('Local UI build: 3 public assets; no project data included.')


if __name__ == '__main__': build()
