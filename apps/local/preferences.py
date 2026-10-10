"""Owner-only appearance and welcome state; contains no knowledge or permissions."""
import json,os,secrets,stat
class Preferences:
    def __init__(self,fd):self.fd=fd
    def request(self,data):
        if data not in ({'action':'get'},) and not (set(data)=={'action','theme','welcomed'} and data['action']=='save' and data['theme'] in ('system','light','dark') and type(data['welcomed']) is bool):raise ValueError('Invalid preferences')
        if data['action']=='save':
            name='preferences-'+secrets.token_hex(8)+'.tmp'
            fd=os.open(name,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600,dir_fd=self.fd)
            try:os.write(fd,json.dumps({'theme':data['theme'],'welcomed':data['welcomed']}).encode());os.fsync(fd)
            finally:os.close(fd)
            os.rename(name,'preferences.json',src_dir_fd=self.fd,dst_dir_fd=self.fd)
        try:fd=os.open('preferences.json',os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=self.fd)
        except FileNotFoundError:return {'theme':'system','welcomed':False}
        try:
            info=os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or info.st_size>1024 or info.st_uid!=os.getuid() or stat.S_IMODE(info.st_mode)!=0o600:raise ValueError('Unsafe preferences')
            value=json.loads(os.read(fd,1025))
            if set(value)!= {'theme','welcomed'} or value['theme'] not in ('system','light','dark') or type(value['welcomed']) is not bool:raise ValueError('Invalid saved preferences')
            return value
        finally:os.close(fd)
