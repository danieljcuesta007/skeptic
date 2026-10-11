"""Build a local macOS AppKit/WebKit app; never packages private runtime state."""
from pathlib import Path
import plistlib,shutil,subprocess,sys
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
FILES=['apps/terminal/continuity_socket.py','apps/terminal/checkpoints.py','apps/terminal/checkpoint_writer.py','apps/terminal/recovery_contract.py','apps/terminal/continuity_adapters.py','apps/terminal/continuity_service.py','apps/desktop/backend.py','apps/local/app.py','apps/local/workspace.py','apps/local/usage.py','apps/local/preferences.py','apps/local/index.html','apps/local/app.js','apps/local/style.css','packages/discovery/engine.py']
def build(destination=None):
    target=Path(destination or HERE/'dist/Skeptic.app')
    if target.is_symlink():raise ValueError('Symlink output refused')
    if target.exists():shutil.rmtree(target)
    mac=target/'Contents/MacOS';resources=target/'Contents/Resources';mac.mkdir(parents=True);resources.mkdir()
    for name in FILES:
        source=ROOT/name
        if source.is_symlink():raise ValueError('Symlink source refused')
        out=resources/'runtime'/name;out.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,out)
    info={'CFBundleIdentifier':'org.skeptic.local.development','CFBundleName':'Skeptic','CFBundleExecutable':'Skeptic','CFBundlePackageType':'APPL','CFBundleShortVersionString':'0.43.7','NSHighResolutionCapable':True,'LSMinimumSystemVersion':'12.0','NSAppTransportSecurity':{'NSAllowsLocalNetworking':True}}
    (target/'Contents/Info.plist').write_bytes(plistlib.dumps(info))
    subprocess.run(['swiftc','-module-cache-path',str(HERE/'dist/module-cache'),str(HERE/'Skeptic.swift'),'-o',str(mac/'Skeptic'),'-framework','AppKit','-framework','WebKit'],check=True)
    return target
if __name__=='__main__':
    if sys.platform!='darwin':sys.exit('Build on macOS with Xcode Command Line Tools installed.')
    print(build())
