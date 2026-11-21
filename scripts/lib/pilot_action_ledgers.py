"""Two exact selected ledger scopes over one ordered capture/replay cursor."""
from pathlib import PurePosixPath as P
import posixpath
from lib.synthetic_ledger_io import ReplayIO as LedgerReplay,observation
from lib.synthetic_ledger_replay_effects import ReplayLedgerEffects
from lib.synthetic_ledger_private import PrivateLedgerPort,ReplayProjection
from lib.requirement_validation_replay import IntegrityError
from lib.requirement_validation_budget import InputAdmissionError

LEDGERS=('governance/lifecycle/live-validation','governance/lifecycle/pilot-actions')

def roots(source):return tuple(str(P(source)/name) for name in LEDGERS)

def select(path,ledgers):
    chosen=[name for name in ledgers if P(path).is_relative_to(name)]
    if len(chosen)!=1:raise InputAdmissionError('pilot_action_two_selected_ledgers_required')
    return chosen[0]

class StateGroup:
    def __init__(self):self.states={}
    def mkdir(self,created):
        for state in self.states.values():state.mkdir(created)

class LedgerOwner:
    def __init__(self,owner,ledger,files=None):
        object.__setattr__(self,'base',owner);object.__setattr__(self,'ledger',P(ledger))
        if files is not None:object.__setattr__(self,'ledger_files',files)
    def __getattr__(self,name):return getattr(self.base,name)
    def __setattr__(self,name,value):
        if name=='effect_state':self.base.effect_state.states[str(self.ledger)]=value
        else:setattr(self.base,name,value)

class NativeEffectRouter:
    """Pure logical descriptor routing; actual POSIX calls stay in injected ports."""
    def __init__(self,owner,ledgers,*,factory,transaction_name):
        self.owner,self.ledgers=owner,tuple(ledgers);owner.effect_state=StateGroup();self.parts={}
        for ledger in self.ledgers:
            files=getattr(owner,'ledger_files',None)
            if files is not None:files=files.parts[ledger]
            self.parts[ledger]=factory(LedgerOwner(owner,ledger,files),ledger,transaction_name=transaction_name)
        first=next(iter(self.parts.values()))
        for name in ('O_RDONLY','O_CREAT','O_RDWR','O_NOFOLLOW','O_DIRECTORY','LOCK_EX','LOCK_UN'):setattr(self,name,getattr(first,name))
        self.tokens={};self.serial=0
    def path(self,path):
        value=P(str(path));name=posixpath.normpath(str(value if value.is_absolute() else P(self.owner.cwd)/value))
        return self.parts[select(name,self.ledgers)]
    def bind(self,part,token):
        self.serial+=1;self.tokens[self.serial]=(part,token);return self.serial
    def token(self,token):
        if type(token) is not int or token not in self.tokens:raise IntegrityError('pilot_action_owned_descriptor_route_changed')
        return self.tokens[token]
    def open(self,path,flags,mode=0o777):
        part=self.path(path);return self.bind(part,part.open(path,flags,mode))
    def mkstemp(self,*,prefix,dir):
        part=self.path(dir);token,name=part.mkstemp(prefix=prefix,dir=dir);return self.bind(part,token),name
    def fdopen(self,descriptor,mode):
        part,token=self.token(descriptor);return RoutedStream(part.fdopen(token,mode),descriptor)
    def flock(self,descriptor,operation):
        part,token=self.token(descriptor);return part.flock(token,operation)
    def fsync(self,descriptor):
        part,token=self.token(descriptor);return part.fsync(token)
    def close(self,descriptor):
        part,token=self.token(descriptor);return part.close(token)
    def link(self,source,target):
        part=self.path(source)
        if self.path(target) is not part:raise IntegrityError('pilot_action_cross_ledger_publication_forbidden')
        return part.link(source,target)
    def unlink(self,path):return self.path(path).unlink(path)
    def release_resources(self):
        return [part.release_resources() for part in self.parts.values() if hasattr(part,'release_resources')]
    @property
    def descriptors(self):return {ledger:part.descriptors for ledger,part in self.parts.items()}

class RoutedStream:
    def __init__(self,stream,token):self.stream,self.token=stream,token
    def __enter__(self):self.stream.__enter__();return self
    def __exit__(self,*error):return self.stream.__exit__(*error)
    def write(self,raw):return self.stream.write(raw)
    def flush(self):return self.stream.flush()
    def fileno(self):self.stream.fileno();return self.token

class DualReplayProjection(ReplayProjection):
    def obtain(self,path,label):
        # Base alias admission uses io.ledger. Bind it only for the exact path
        # currently being checked; both admitted roots remain fixed.
        prior=self.io.ledger
        try:
            try:self.io.ledger=select(path,self.io.ledgers)
            except InputAdmissionError:pass
            return super().obtain(path,label)
        finally:self.io.ledger=prior

class ReplayActionIO(LedgerReplay):
    def __init__(self,*args,source,transaction_name,**kw):
        self.ledgers=roots(source)
        super().__init__(*args,ledger=self.ledgers[0],transaction_name=transaction_name,**kw)
        if self.mode=='private-candidate':self.projection=self.output=DualReplayProjection(self)
    def ledger_path(self,path):return any(P(path).parent==P(name)/'transactions' for name in self.ledgers)
    def remember_ledger(self,path,value):
        info=observation(value,self.blob,path=path,ledger=select(path,self.ledgers),transaction_name=self.transaction_name) or {'kind':'missing'}
        if path in self.metadata and self.metadata[path]!=info:raise IntegrityError('pilot_action_repeated_ledger_metadata_changed')
        self.metadata[path]=info

def replay_effects(owner,*,source,transaction_name):
    if owner.mode=='private-candidate':return PrivateLedgerPort(owner,str(P(source)/'governance/lifecycle'))
    return NativeEffectRouter(owner,roots(source),factory=ReplayLedgerEffects,transaction_name=transaction_name)
