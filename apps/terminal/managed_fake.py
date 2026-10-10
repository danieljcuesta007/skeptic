"""Controlled synthetic terminal agent; never loads provider configuration or writes files."""
import os
import signal
import sys
import termios
import fcntl
import struct

def resized(*_):
    rows, cols, _, _ = struct.unpack('HHHH', fcntl.ioctl(0, termios.TIOCGWINSZ, b'\0' * 8))
    print('SIZE=' + str(rows) + 'x' + str(cols), flush=True)

signal.signal(signal.SIGWINCH, resized)
signal.signal(signal.SIGINT, lambda *_: print('INTERRUPT', flush=True))
print('FAKE_READY PID=' + str(os.getpid()) + ' CWD=' + os.getcwd() + ' TTY=' + str(os.isatty(0)), flush=True)
for line in sys.stdin:
    line = line.rstrip('\r\n')
    if line == 'exit': print('FAKE_EXIT', flush=True); sys.exit(0)
    if line == 'fail': sys.exit(7)
    if line == 'stop': os.kill(os.getpid(), signal.SIGSTOP); print('CONTINUED', flush=True)
    elif line == 'burst': print('x' * 80000, flush=True)
    else: print('ECHO=' + line, flush=True)
