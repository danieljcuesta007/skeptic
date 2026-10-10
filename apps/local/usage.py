"""Local quota snapshots and owner-local manual readings; no credential or cloud access."""
import datetime
import json
import hashlib
import math
import os
from pathlib import Path
import stat
import time

CATALOG = [
    {'id':'claude','name':'Claude Code','help':'Cached subscription quota from Claude Code activity.'},
    {'id':'codex','name':'Codex','help':'Cached subscription quota from Codex activity; separate from API spend.'},
    {'id':'hermes','name':'Hermes','help':'Record the underlying provider/model. Hermes usage is not a shared subscription quota.','url':'https://portal.nousresearch.com/manage-subscription'},
    {'id':'midjourney','name':'Midjourney','help':'Record Fast GPU hours and renewal date from Usage Details or Discord /info.','url':'https://www.midjourney.com/account'},
    {'id':'gemini','name':'Gemini','help':'Manual reading; account/plan and model limits can differ.'},
    {'id':'openrouter','name':'OpenRouter','help':'Manual account credit balance; credits are not a subscription percentage.','url':'https://openrouter.ai/settings/credits'},
    {'id':'ollama','name':'Ollama / local models','help':'No account quota inferred. Record the model and any resource budget you use.'},
    {'id':'other','name':'Other model / service','help':'Name the model or provider and its budget unit.'},
]
IDS = {item['id'] for item in CATALOG}


def numeric(n):
    return isinstance(n, (int,float)) and not isinstance(n,bool) and math.isfinite(n)


def read_json(path, limit=65536):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > limit:
            raise ValueError('Unsafe usage file')
        return json.loads(os.read(fd, limit+1))
    finally:
        os.close(fd)


def quota(raw, minutes, at):
    if not isinstance(raw,dict): return None
    used = raw.get('used_percentage',raw.get('used_percent',raw.get('usedPercent')))
    reset = raw.get('resets_at',raw.get('resetsAt'))
    if isinstance(reset,str):
        try: reset=datetime.datetime.fromisoformat(reset.replace('Z','+00:00')).timestamp()
        except (ValueError,OverflowError): return None
    if not all(numeric(x) for x in (used,reset,minutes,at)) or not 0<=used<=100 or not 0<reset<=253402300799 or not 0<at<=253402300799 or not 1<=minutes<=525600: return None
    return {'remaining':100-used,'limit':100,'unit':'%','window_minutes':minutes,'resets_at':reset,'observed_at':at,'source':'Last seen in local activity'}


class Usage:
    def __init__(self, statefd, home=None, clock=time.time):
        self.statefd=statefd; self.home=Path(home or Path.home()); self.clock=clock
        self.enabled=False; self.cached=[]; self.next_read=0
        self.manual={}
        try:
            fd=os.open('usage.json',os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=statefd)
            try:
                info=os.fstat(fd)
                if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1 or info.st_size>65536: raise ValueError()
                data=json.loads(os.read(fd,65537))
            finally: os.close(fd)
            if not isinstance(data,dict) or len(data)>100: raise ValueError()
            self.manual={k:self.validate(v) for k,v in data.items() if isinstance(k,str) and len(k)==64}
        except (OSError,ValueError,TypeError,KeyError): self.manual={}

    def validate(self, data):
        if not isinstance(data,dict) or set(data)!={'provider','model','remaining','limit','unit','resets_at','observed_at'}: raise ValueError('Invalid reading fields')
        if data['provider'] not in IDS: raise ValueError('Choose a provider')
        for field in ('model','unit'):
            if not isinstance(data[field],str) or len(data[field])>100 or any(ord(c)<32 for c in data[field]): raise ValueError('Invalid label')
        if not data['model'].strip(): raise ValueError('Model label required')
        if data['unit'] not in ('%','USD','credits','tokens','GPU hours','requests'): raise ValueError('Choose a supported unit')
        for field in ('remaining','limit'):
            if data[field] is not None and (not numeric(data[field]) or not 0<=data[field]<=1e15): raise ValueError('Invalid amount')
        if data['remaining'] is not None and data['limit'] is not None and data['remaining']>data['limit']: raise ValueError('Remaining exceeds limit')
        for field in ('resets_at','observed_at'):
            if data[field] is not None and (not numeric(data[field]) or not 0<data[field]<=253402300799): raise ValueError('Invalid date')
        if data['observed_at'] is None: raise ValueError('Reading date required')
        return dict(data)

    def save(self):
        name='usage.pending'
        fd=os.open(name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=self.statefd)
        try:
            with os.fdopen(fd,'w') as f: json.dump(self.manual,f,allow_nan=False); f.flush(); os.fsync(f.fileno())
            os.rename(name,'usage.json',src_dir_fd=self.statefd,dst_dir_fd=self.statefd)
        finally:
            try: os.unlink(name,dir_fd=self.statefd)
            except FileNotFoundError: pass

    def local(self):
        rows=[]
        try:
            raw=read_json(self.home/'.claude/state/rate-limits.json'); at=raw.get('at'); limits=raw.get('rate_limits',{})
            windows=[quota(limits.get(k),m,at) for k,m in [('five_hour',300),('seven_day',10080)]]
            rows.append({'provider':'claude','model':'Claude Code subscription','windows':[w for w in windows if w]})
        except (OSError,ValueError,TypeError,AttributeError): pass
        latest=None
        root=self.home/'.codex/sessions'
        # Fixed session location only. Bounded file count and tail bytes. No credential files.
        if not root.is_symlink():
            try:
                candidates=[]
                visited=0
                for directory,dirs,files in os.walk(root,followlinks=False):
                    visited+=1+len(dirs)+len(files)
                    if visited>10000: break
                    dirs[:]=[d for d in dirs if not (Path(directory)/d).is_symlink()]
                    for name in files:
                        if name.endswith('.jsonl'): candidates.append(Path(directory)/name)
                    if len(candidates)>10000: break
                paths=sorted(candidates,key=lambda p:p.lstat().st_mtime,reverse=True)[:12]
                for path in paths:
                    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
                    try:
                        info=os.fstat(fd)
                        if not stat.S_ISREG(info.st_mode) or info.st_nlink!=1: continue
                        offset=max(0,info.st_size-2*1024*1024); os.lseek(fd,offset,0)
                        lines=os.read(fd,2*1024*1024).splitlines()
                        if offset: lines=lines[1:]
                        for line in lines:
                            if b'"token_count"' not in line or b'"rate_limits"' not in line: continue
                            try:
                                e=json.loads(line); p=e.get('payload',{})
                                if e.get('type')!='event_msg' or p.get('type')!='token_count': continue
                                stamp=datetime.datetime.fromisoformat(e['timestamp'].replace('Z','+00:00'))
                                if stamp.tzinfo is None: continue
                                at=stamp.timestamp(); raw=p.get('rate_limits',{})
                                if raw.get('limit_id') not in (None,'codex'): continue
                                windows=[quota(raw.get(k),raw.get(k,{}).get('window_minutes'),at) for k in ('primary','secondary') if isinstance(raw.get(k),dict)]
                                windows=[w for w in windows if w]
                                if windows and (latest is None or at>latest['at']): latest={'at':at,'windows':windows}
                            except (ValueError,TypeError,KeyError,AttributeError): continue
                    finally: os.close(fd)
            except OSError: pass
        if latest: rows.append({'provider':'codex','model':'Codex subscription','windows':latest['windows']})
        return rows

    def request(self,data):
        if data=={'op':'enable'}:
            if not self.enabled: self.next_read=0
            self.enabled=True
        elif data=={'op':'disable'}: self.enabled=False; self.cached=[]
        elif set(data)=={'op','reading'} and data['op']=='save':
            reading=dict(data['reading']); reading['observed_at']=self.clock()
            reading=self.validate(reading); key=hashlib.sha256((reading['provider']+'\0'+reading['model']).encode()).hexdigest()
            if key not in self.manual and len(self.manual)>=100: raise ValueError('Maximum 100 saved models')
            before=dict(self.manual); self.manual[key]=reading
            try: self.save()
            except OSError:
                self.manual=before
                raise
        elif set(data)=={'op','id'} and data['op']=='delete' and data['id'] in self.manual:
            before=dict(self.manual); self.manual.pop(data['id'],None)
            try: self.save()
            except OSError:
                self.manual=before
                raise
        elif data!={'op':'read'}: raise ValueError('Unknown usage request')
        now=self.clock()
        if self.enabled and now>=self.next_read: self.cached=self.local(); self.next_read=now+60
        rows=list(self.cached)
        for key,reading in self.manual.items():
            rows.append({'id':key,'provider':reading['provider'],'model':reading['model'],'windows':[dict(reading,source='Manual reading')]})
        for row in rows:
            for w in row['windows']:
                expired=w.get('resets_at') is not None and w['resets_at']<=now
                w['expired']=expired; w['display_remaining']=None if expired or w['observed_at']>now+300 else w['remaining']
        return {'catalog':CATALOG,'rows':rows,'local_enabled':self.enabled,'checked_at':now}
