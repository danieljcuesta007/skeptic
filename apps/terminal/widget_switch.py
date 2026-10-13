"""One native confirmation for a reviewed widget handoff; no scope grants."""
import hashlib
import subprocess

SCRIPT = r'''on run argv
    set messageText to item 1 of argv
    set response to display dialog messageText with title "Skeptic — Switch window" buttons {"Cancel", "Switch"} default button "Switch" cancel button "Cancel"
    return button returned of response
end run'''


def confirm(summary, evidence, provider, packet, run=None):
    """The click approves this packet and attests to the original writer check.
    Text is passed as argv, never compiled into AppleScript or a shell command.
    Cancellation, errors and unavailable GUI all withhold approval.
    """
    run = run or subprocess.run
    document = (evidence.get('document') or {}).get('text', '')
    latest = document.split('\n[message ', 1)[0].split(':\n', 1)[-1].strip() if document.startswith('Latest recorded human request') else ''
    latest = ' '.join(latest.split())
    text = ("Switch this conversation to " + str(provider) + "?\n\n"
            + "Conversation: " + str(evidence.get('title') or 'Untitled') + " (" + str(evidence.get('id', '')) + ")\n"
            + ("Last request: " + (latest[:240] + '…' if len(latest) > 240 else latest) + "\n" if latest else '')
            + "Project: " + str(summary.get('cwd', '')) + "\n\n"
            + "Switch sends the filtered handoff shown in Terminal and confirms you have stopped any background tools or automatic work in the original window. The original window stays open.\n\n"
            + "Handoff SHA-256: " + hashlib.sha256(packet.encode()).hexdigest())
    try:
        result = run(['/usr/bin/osascript', '-e', SCRIPT, text], capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.SubprocessError): return False
    return result.returncode == 0 and result.stdout.strip() == 'Switch'


EXISTING_SCRIPT = r'''on run argv
    set targetTTY to item 1 of argv
    display dialog "A previous Skeptic switch is still open. Use that window, or exit its AI before starting another switch." with title "Skeptic — Already open" buttons {"Cancel", "Show existing window"} default button "Show existing window" cancel button "Cancel"
    tell application "Terminal"
        repeat with win in windows
            repeat with tabItem in tabs of win
                if tty of tabItem is targetTTY then
                    set selected tab of win to tabItem
                    set index of win to 1
                    activate
                    return
                end if
            end repeat
        end repeat
    end tell
end run'''


def show_existing(lock_path, run=None):
    """Offer the sole terminal attached to the live reservation; never stop it."""
    import re
    run = run or subprocess.run
    try:
        holders = run(['/usr/sbin/lsof', '-t', str(lock_path)], capture_output=True, text=True, timeout=5)
        pids = {p for p in holders.stdout.splitlines() if re.fullmatch(r'[0-9]{1,10}', p)}
        if holders.returncode or len(pids) != 1: return False
        descriptors = run(['/usr/sbin/lsof', '-a', '-p', next(iter(pids)), '-d', '0', '-Fn'], capture_output=True, text=True, timeout=5)
        terminals = {line[1:] for line in descriptors.stdout.splitlines() if re.fullmatch(r'n/dev/ttys[0-9]{3,6}', line)}
        if descriptors.returncode or len(terminals) != 1: return False
        result = run(['/usr/bin/osascript', '-e', EXISTING_SCRIPT, next(iter(terminals))], capture_output=True, text=True, timeout=300)
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError): return False
