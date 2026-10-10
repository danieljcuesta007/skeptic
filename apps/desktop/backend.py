"""Private desktop server: stdin is a lifetime lease, never an always-on daemon."""
from pathlib import Path
import fcntl,json,os,sys,threading
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'local'))
from app import Registry,LocalServer,Denied

def serve(state, lease, output):
    registry=Registry(state)
    lock=None
    try:
        lock=os.open('desktop.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600,dir_fd=registry.statefd)
        import stat
        info=os.fstat(lock)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)!=0o600:raise Denied('Unsafe lock')
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        with LocalServer(registry,0) as server:
            worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
            output.write(json.dumps({'origin':server.origin})+'\n');output.flush()
            try:
                while lease.read(1):pass
            finally:
                server.shutdown();worker.join()
    finally:
        if lock is not None:os.close(lock)
        registry.close()

if __name__=='__main__':
    try:serve(Path.home()/'.skeptic-desktop',sys.stdin.buffer,sys.stdout)
    except (Denied,OSError,ValueError):
        print('Skeptic could not start safely. Another app may be open, or local access was denied.',file=sys.stderr);sys.exit(1)
