"""Local PTY engine for explicit temporary fixtures; no adoption or production migration."""
import base64
import ctypes
import fcntl
import json
import os
from pathlib import Path
import pty
import select
import signal
import socket
import sqlite3
import stat
import struct
import sys
import tempfile
import time
import uuid

VERSION = 1
FRAME_LIMIT = 32768
OUTPUT_LIMIT = 65536


class Denied(Exception):
    pass


def fixture_path(value):
    path = Path(value).absolute()
    if '..' in path.parts: raise Denied('Fixture traversal refused')
    allowed = [Path('/private/tmp'), Path('/tmp'), Path(tempfile.gettempdir()), Path(tempfile.gettempdir()).resolve()]
    if not any(path != root and root in path.parents for root in allowed):
        raise Denied('This slice requires an isolated temporary fixture directory')
    # Refuse aliases below the platform temp root (macOS /var itself is an alias).
    root = next(root for root in allowed if root in path.parents)
    current = root
    for part in path.relative_to(root).parts:
        current = current / part
        if current.is_symlink(): raise Denied('Fixture path contains a symlink')
    return path


def private_file(path, create=False, readonly=False):
    fd = os.open(path, (os.O_RDONLY if readonly else os.O_RDWR) | os.O_NOFOLLOW | (os.O_CREAT if create else 0), 0o600)
    info = os.fstat(fd)
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
        os.close(fd); raise Denied('Unsafe private state file')
    return fd


class Registry:
    def __init__(self, root, readonly=False):
        self.root = fixture_path(root)
        if readonly:
            info = self.root.stat()
            if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700: raise Denied('State must be owner-only')
            fd = private_file(self.root / 'registry.sqlite', readonly=True); os.close(fd)
            self.db = sqlite3.connect((self.root / 'registry.sqlite').as_uri() + '?mode=ro', uri=True, timeout=2)
            self.db.execute('PRAGMA query_only=ON')
            return
        self.root.mkdir(mode=0o700, exist_ok=True)
        info = self.root.stat()
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700: raise Denied('State must be owner-only')
        fd = private_file(self.root / 'registry.sqlite', True); os.close(fd)
        self.db = sqlite3.connect(self.root / 'registry.sqlite', timeout=2)
        self.db.execute('PRAGMA journal_mode=DELETE')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.execute('CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, project TEXT, cwd TEXT, dev INTEGER, ino INTEGER, provider TEXT, generation TEXT, supervisor INTEGER, agent INTEGER, status TEXT, exit_code INTEGER)')
        self.db.commit()

    def create(self, sid, cwd, generation):
        cwd = fixture_path(cwd)
        info = cwd.stat()
        if not stat.S_ISDIR(info.st_mode): raise Denied('Working directory unavailable')
        project = str(uuid.uuid5(uuid.NAMESPACE_URL, str(cwd) + ':' + str(info.st_dev) + ':' + str(info.st_ino)))
        with self.db:
            self.db.execute('INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?,?,?,?)', (sid, project, str(cwd), info.st_dev, info.st_ino, 'skeptic-fake-v1', generation, os.getpid(), None, 'starting', None))

    def update(self, sid, **values):
        if not values or set(values) - {'agent', 'status', 'exit_code'}: raise Denied('Invalid metadata update')
        with self.db:
            self.db.execute('UPDATE sessions SET ' + ','.join(k + '=?' for k in values) + ' WHERE id=?', (*values.values(), sid))

    def get(self, sid):
        self.db.row_factory = sqlite3.Row
        row = self.db.execute('SELECT * FROM sessions WHERE id=?', (sid,)).fetchone()
        if row is None: raise Denied('Unknown session')
        return dict(row)

    def close(self): self.db.close()


def session_id(value):
    if str(uuid.UUID(value)) != value: raise Denied('Invalid session ID')
    return value


def endpoint(root, sid):
    sid = session_id(sid)
    path = str(Path(root) / ('s-' + sid.replace('-', '')[:12] + '.sock'))
    if len(path.encode()) >= 104: raise Denied('Temporary state path too long for macOS socket')
    return path


def frame(value):
    body = json.dumps(value, separators=(',', ':')).encode()
    if len(body) > FRAME_LIMIT: raise Denied('Frame too large')
    return struct.pack('!I', len(body)) + body


def decode_request(raw):
    if len(raw) > FRAME_LIMIT: raise Denied('Frame too large')
    depth = 0; quoted = False; escaped = False
    for char in raw:
        if quoted:
            if escaped: escaped = False
            elif char == 92: escaped = True
            elif char == 34: quoted = False
        elif char == 34: quoted = True
        elif char in (91, 123):
            depth += 1
            if depth > 32: raise Denied('JSON nesting limit exceeded')
        elif char in (93, 125): depth -= 1
    try: request = json.loads(raw)
    except (ValueError, RecursionError) as error: raise Denied('Malformed JSON') from error
    if not isinstance(request, dict): raise Denied('Invalid request')
    return request


def sequence(state, message):
    number = message.get('id')
    if type(number) is not int or number <= state['last_id'] or number > 9007199254740991: raise Denied('Request IDs must increase')
    state['last_id'] = number
    if message.get('op') == 'hello':
        if state['hello']: raise Denied('Already authenticated')
        state['hello'] = True
    elif not state['hello']: raise Denied('hello required')


def peer_uid(connection):
    if sys.platform == 'darwin':
        uid, gid = ctypes.c_uint(), ctypes.c_uint()
        if ctypes.CDLL(None).getpeereid(connection.fileno(), ctypes.byref(uid), ctypes.byref(gid)) != 0: raise Denied('Cannot authenticate peer')
        return uid.value
    if hasattr(socket, 'SO_PEERCRED'):
        return struct.unpack('3i', connection.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))[1]
    raise Denied('Peer authentication unsupported')


def process_group_clear(pgid):
    """True only when the explicitly owned PTY process group is absent.

    Detached and SIGSTOPped agents still exist and therefore remain writers from
    the project's point of view. Errors and permission ambiguity fail closed.
    """
    if type(pgid) is not int or pgid <= 1: return False
    try:
        os.killpg(pgid, 0)
        return False
    except ProcessLookupError:
        return True
    except (PermissionError, OSError):
        return False


class Client:
    def __init__(self, root, sid):
        self.root, self.sid = Path(root), session_id(sid)
        registry = Registry(root, readonly=True)
        try: self.metadata = registry.get(sid)
        finally: registry.close()
        fd = private_file(self.root / (sid + '.key'))
        try: self.key = os.read(fd, 128).decode()
        finally: os.close(fd)
        path = endpoint(root, sid)
        info = os.lstat(path)
        if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600: raise Denied('Unsafe engine endpoint')
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.settimeout(2)
        try:
            self.socket.connect(path)
            if peer_uid(self.socket) != os.getuid(): raise Denied('Wrong engine owner')
            self.request('hello')
        except BaseException:
            self.socket.close(); raise

    def request(self, op, **values):
        number = getattr(self, 'number', 0) + 1; self.number = number
        self.socket.sendall(frame(dict(v=VERSION, id=number, op=op, key=self.key, generation=self.metadata['generation'], **values)))
        def receive(size):
            body = b''
            while len(body) < size:
                chunk = self.socket.recv(size - len(body))
                if not chunk: raise Denied('Supervisor disconnected; terminal state unavailable')
                body += chunk
            return body
        size = struct.unpack('!I', receive(4))[0]
        if size > FRAME_LIMIT: raise Denied('Oversized engine response')
        result = json.loads(receive(size))
        if result.get('id') != number or result.get('v') != VERSION: raise Denied('Protocol mismatch')
        if not result.get('ok'): raise Denied(result.get('error', 'Request denied'))
        return result['result']

    def close(self): self.socket.close()


def observation(root, sid):
    registry = Registry(root, readonly=True)
    try: row = registry.get(sid)
    finally: registry.close()
    try:
        fd = private_file(Path(root) / (sid + '.startup'), readonly=True)
        try: receipt = json.loads(os.read(fd,300001))
        finally: os.close(fd)
        if receipt.get('session') != sid or receipt.get('cwd') != row['cwd']: raise Denied('Startup receipt identity mismatch')
        row['requested_native_id'] = receipt.get('native_id')
        row['provider_version'] = receipt.get('version')
    except FileNotFoundError: pass
    try:
        client = Client(root, sid)
        try: return client.request('status')
        finally: client.close()
    except (OSError, Denied, ValueError):
        # A PID in a database never proves ownership or permission to signal it.
        row['recorded_status'] = row['status']
        row['status'] = 'stale' if row['status'] in ('starting', 'live', 'detached', 'suspended') else row['status']
        row['reachability'] = 'unreachable'
        row['screen'] = 'Unavailable; no supervisor reconnection or agent relaunch attempted'
        return row


def supervise(root, sid, cwd, provider="skeptic-fake-v1", approved=False):
    os.umask(0o077)
    registry = Registry(root)
    generation = str(uuid.uuid4())
    key_path = registry.root / (sid + '.key')
    fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    key = os.urandom(32).hex()
    with os.fdopen(fd, 'w') as out: out.write(key); out.flush(); os.fsync(out.fileno())
    registry.create(sid, cwd, generation)
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listener.bind(endpoint(root, sid)); os.chmod(endpoint(root, sid), 0o600)
    listener.listen(8); listener.setblocking(False)
    # This executable is fresh, single-threaded and does not load HTTP/framework APIs.
    cwd_fd = os.open(cwd, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    cwd_info = os.fstat(cwd_fd)
    recorded = registry.get(sid)
    if (cwd_info.st_dev, cwd_info.st_ino) != (recorded['dev'], recorded['ino']): raise Denied('Working directory identity changed before launch')
    fake_argv = [sys.executable, '-B', str(Path(__file__).with_name('managed_fake.py'))]
    child_env = {'PATH': os.defpath, 'PYTHONUNBUFFERED': '1', 'SKEPTIC_SESSION_ID': sid, 'SKEPTIC_MANAGED_STATE': str(root)}
    if provider != 'skeptic-fake-v1':
        from managed_providers import plan
        fd = private_file(registry.root / (sid + '.startup'))
        try: receipt = json.loads(os.read(fd,300001))
        finally: os.close(fd)
        if receipt.get('session') != sid or receipt.get('provider') != provider or receipt.get('cwd') != str(cwd): raise Denied('Launch receipt mismatch')
        launch = plan(provider, cwd, prompt=receipt.get('packet',''), native_id=receipt.get('native_id'), approved=approved)
        fake_argv = launch['argv']
        child_env = dict(os.environ, SKEPTIC_SESSION_ID=sid, SKEPTIC_MANAGED_STATE=str(root))
        with registry.db:
            registry.db.execute('UPDATE sessions SET provider=? WHERE id=?', (provider, sid))
    pid, master = pty.fork()
    if pid == 0:
        try:
            os.fchdir(cwd_fd)
            os.closerange(3, 256)
            os.execve(fake_argv[0], fake_argv, child_env)
        except BaseException as error:
            os.write(2, ('Agent launch failed: ' + type(error).__name__ + ': ' + str(error) + '\n').encode())
            os._exit(2)
    os.close(cwd_fd)
    registry.update(sid, agent=pid, status='detached')
    os.set_blocking(master, False)
    clients, writer, output, start, end = {}, None, bytearray(), 0, 0
    live, suspended, code, draining = True, False, None, True
    native_id = launch['native_id'] if provider != 'skeptic-fake-v1' else None
    def update_status():
        registry.update(sid, status='suspended' if suspended else ('live' if writer is not None else 'detached') if live else 'exited', exit_code=code)
    def disconnect(connection):
        nonlocal writer
        if connection is writer: writer = None; update_status()
        clients.pop(connection, None); connection.close()
    def dispatch(connection, message):
        nonlocal writer, live
        if message.get('v') != VERSION or message.get('key') != key or message.get('generation') != generation: raise Denied('Authentication/generation mismatch')
        sequence(clients[connection], message)
        op = message.get('op')
        if op == 'hello': return {'generation': generation}
        if op == 'status': return dict(registry.get(sid), reachability='reachable', output_complete=not draining, final_cursor=end, agent_process_group_quiescent=(not live and process_group_clear(pid)), requested_native_id=native_id, provider_native_id=None, writer_attached=writer is not None, observer_connections=sum(1 for state in clients.values() if state['mode']=='observe'), screen='Bounded byte replay only; exact screen restoration unavailable')
        if op in ('attach', 'claim'):
            if op == 'attach' and message.get('mode') == 'observe':
                if writer is connection: raise Denied('Detach writer before observing')
                clients[connection]['mode'] = 'observe'; return {'writer': False}
            if not live: raise Denied('Agent exited; input unavailable')
            if writer is not None and writer is not connection: raise Denied('Writer already attached')
            writer = connection; clients[connection]['mode'] = 'write'; update_status(); return {'writer': True}
        if op == 'detach':
            clients[connection]['mode'] = 'unattached'
            if writer is connection: writer = None; update_status()
            return {'detached': True}
        if op == 'output':
            cursor = message.get('cursor', 0)
            if type(cursor) is not int or cursor < 0 or cursor > end: raise Denied('Invalid output cursor')
            offset = max(cursor, start); size = min(end - offset, 16000)
            return {'data': base64.b64encode(output[offset-start:offset-start+size]).decode(), 'cursor': offset+size, 'gap': cursor < start, 'start': start, 'end': end}
        if op in ('input', 'resize', 'continue'):
            if writer is not connection: raise Denied('Writer lease required')
            if not live: raise Denied('Agent exited')
            if op == 'input':
                body = base64.b64decode(message.get('data', ''), validate=True)
                if len(body) > 4096: raise Denied('Input too large')
                # Nonblocking partial write is acknowledged explicitly; client retries remaining bytes.
                try: count = os.write(master, body)
                except BlockingIOError: count = 0
                return {'written': count}
            if op == 'resize':
                rows, cols = message.get('rows'), message.get('cols')
                if any(type(n) is not int or not 1 <= n <= 1000 for n in (rows, cols)): raise Denied('Invalid size')
                fcntl.ioctl(master, __import__('termios').TIOCSWINSZ, struct.pack('HHHH', rows, cols, 0, 0))
                return {'resized': True}
            os.killpg(pid, signal.SIGCONT); return {'continued': True}
        if op == 'shutdown':
            if live: raise Denied('Detach preserves live agent; shutdown requires agent exit')
            return {'shutdown': True}
        raise Denied('Unknown operation')
    try:
        running = True
        while running:
            if live:
                waited, status = os.waitpid(pid, os.WNOHANG | os.WUNTRACED | os.WCONTINUED)
                if waited:
                    if os.WIFSTOPPED(status): suspended = True
                    elif os.WIFCONTINUED(status): suspended = False
                    else: live = False; suspended = False; code = os.waitstatus_to_exitcode(status)
                    update_status()
            reads = [listener, *clients] + ([master] if draining else [])
            writes = [c for c, state in clients.items() if state['out']]
            ready, writable, _ = select.select(reads, writes, [], .03)
            for obj in ready:
                if obj is listener:
                    conn, _ = listener.accept(); conn.setblocking(False)
                    if len(clients) >= 16 or peer_uid(conn) != os.getuid(): conn.close(); continue
                    clients[conn] = {'in': bytearray(), 'out': bytearray(), 'seen': time.monotonic(), 'last_id': 0, 'hello': False, 'mode': 'unattached'}
                elif obj == master:
                    try: data = os.read(master, 8192)
                    except BlockingIOError: continue
                    except OSError: data = b''
                    if not data: draining = False; continue
                    output.extend(data); end += len(data)
                    if len(output) > OUTPUT_LIMIT:
                        drop = len(output) - OUTPUT_LIMIT; del output[:drop]; start += drop
                else:
                    state = clients[obj]
                    try: data = obj.recv(FRAME_LIMIT + 4)
                    except BlockingIOError: continue
                    except OSError: disconnect(obj); continue
                    if not data: disconnect(obj); continue
                    state['in'].extend(data); state['seen'] = time.monotonic()
                    if len(state['in']) > FRAME_LIMIT + 4: disconnect(obj); continue
                    if len(state['in']) < 4: continue
                    size = struct.unpack('!I', state['in'][:4])[0]
                    if size > FRAME_LIMIT: disconnect(obj); continue
                    if len(state['in']) < size + 4: continue
                    raw = bytes(state['in'][4:4+size]); del state['in'][:4+size]
                    request = {}
                    try:
                        request = decode_request(raw)
                        if not isinstance(request, dict): raise Denied('Invalid request')
                        result = dispatch(obj, request)
                        response = {'v': VERSION, 'id': request.get('id'), 'ok': True, 'result': result}
                        if request.get('op') == 'shutdown': running = False
                    except (Denied, ValueError, TypeError, OSError, RecursionError) as error:
                        response = {'v': VERSION, 'id': request.get('id') if isinstance(request, dict) and type(request.get('id')) is int and 0 < request['id'] <= 9007199254740991 else None, 'ok': False, 'error': str(error)}
                    state['out'].extend(frame(response))
                    if len(state['out']) > FRAME_LIMIT * 2: disconnect(obj)
            for conn in writable:
                if conn not in clients: continue
                try: count = conn.send(clients[conn]['out']); del clients[conn]['out'][:count]
                except BlockingIOError: pass
                except OSError: disconnect(conn)
            for conn, state in list(clients.items()):
                if (state['in'] or state['out']) and time.monotonic() - state['seen'] > 5: disconnect(conn)
            # Flush shutdown response before closing; no live agent can be shut down here.
            if not running:
                for conn, state in clients.items():
                    if state['out']:
                        try: conn.settimeout(.2); conn.sendall(state['out'])
                        except OSError: pass
    finally:
        for conn in list(clients): conn.close()
        os.close(master); listener.close(); registry.close()
        # Preserve registry/socket receipts; never adopt or relaunch from stale metadata.


if __name__ == '__main__':
    try: supervise(sys.argv[1], session_id(sys.argv[2]), sys.argv[3], sys.argv[4] if len(sys.argv)>4 else "skeptic-fake-v1", len(sys.argv)>5 and sys.argv[5]=="approved")
    except (Denied, OSError, ValueError): sys.exit(2)
