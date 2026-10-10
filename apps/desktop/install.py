"""Install the local development bundle in your user Applications folder."""
from pathlib import Path
import plistlib,shutil
from build import build
source=build();destination=Path.home()/'Applications/Skeptic.app'
parent=destination.parent
if parent.is_symlink():raise SystemExit('Applications symlink refused')
parent.mkdir(exist_ok=True)
if destination.exists() or destination.is_symlink():
    if destination.is_symlink():raise SystemExit('App symlink refused')
    try:identity=plistlib.loads((destination/'Contents/Info.plist').read_bytes()).get('CFBundleIdentifier')
    except (OSError,ValueError):raise SystemExit('Unknown application preserved')
    if identity!='org.skeptic.local.development':raise SystemExit('Unknown application preserved')
    raise SystemExit('Skeptic is already installed. Quit it and remove that development bundle before installing this version.')
shutil.copytree(source,destination)
print(destination)
