"""Replay composition for the whole original observation program and final audit."""
from pathlib import PurePosixPath
from datetime import datetime,timedelta
import posixpath
from lib.provider_observation_private_ports import ReplayPrivateMetadata,require
from lib.provider_observation_credentials import ReplayCredentialCapability
from lib.provider_observation_profile import ReplayCheckedProfile
from lib.provider_observation_reads import ReplayObservationReads
from lib.intake_atomic_effects import AtomicScope,ReplayAtomicEffects
from lib.intake_atomic_json import IntakeAtomicJSON
from lib.requirement_validation_budget import InputAdmissionError


class ObservationScope:
    def __init__(self,owner,*,protected_roots):self.owner,self.protected_roots=owner,tuple(protected_roots);self.paths=None;self.roles_bound=False;self.atomic=None
    def bind_paths(self,paths):self.paths=paths
    def selections(self,profile,credential,output):
        if self.roles_bound:raise InputAdmissionError('provider_observation_roles_already_bound')
        values={k:PurePosixPath(self.paths.absolute(v.value)) for k,v in [('profile',profile),('credential',credential),('output',output)]}
        for key,path in values.items():
            for other in self.protected_roots:
                if other is not None and (path.is_relative_to(PurePosixPath(other)) or PurePosixPath(other).is_relative_to(path)):
                    raise InputAdmissionError('provider_observation_protected_role_overlap')
            for name,second in values.items():
                if name!=key and (path.is_relative_to(second) or second.is_relative_to(path)):raise InputAdmissionError('provider_observation_distinct_roles_required')
        self.selected={k:str(v) for k,v in values.items()};self.roles_bound=True;return self.selected
    def is_credential(self,path):return self.roles_bound and self.paths.absolute(path.value)==self.selected['credential']
    def is_profile(self,path):return self.roles_bound and self.paths.absolute(path.value)==self.selected['profile']
    def private_check(self,path):return self.metadata.check_private_file(self.metadata.path(str(path)))
    def secret_read(self,path):return self.credentials.read(self.metadata.path(str(path)))
    def profile_read(self,path,encoding,errors):return self.profile.read(self.metadata.path(str(path)),encoding,errors)
    def atomic_scope(self):return AtomicScope(self.selected['output'],['candidate.json','native-capture.json'],cwd=self.owner.cwd)


class ReplayObservationBackend(ObservationScope):
    def __init__(self,owner,*,protected_roots,reader_url):
        super().__init__(owner,protected_roots=protected_roots);self.reads=ReplayObservationReads(owner,owner.blob,reader_url=reader_url)
    def roles(self,profile,credential,output):
        selected=self.selections(profile,credential,output);self.metadata=ReplayPrivateMetadata(self.owner,self.owner.blob,cwd=self.owner.cwd,files=[selected['profile'],selected['credential']]);self.credentials=ReplayCredentialCapability(self.owner,self.metadata,credential=selected['credential']);self.profile=ReplayCheckedProfile(self.owner,self.metadata,self.owner.blob,profile=selected['profile'])
    def scalar(self,action,args):
        ok,value=self.owner.outcome(action,args,'json');require(ok,'unexpected_scalar_failure');return value
    def umask(self,value):
        require(type(value) is int and value==0o077,'umask_changed');old=self.scalar('provider-observation-umask',{'mask':value});require(type(old) is int and 0<=old<=0o777,'old_umask_changed');return old
    def clock(self):
        value=self.scalar('provider-observation-clock',{});require(type(value) is str,'clock_changed')
        try:observed=datetime.fromisoformat(value)
        except ValueError:require(False,'clock_changed')
        require(observed.tzinfo is not None and observed.utcoffset()==timedelta(0) and observed.isoformat()==value,'UTC_clock_changed');return value
    def atomic_json(self,path,value):
        if self.atomic is None:self.atomic=ReplayAtomicEffects(self.atomic_scope(),self.owner.events,self.owner.blob,position=self.owner.position)
        self.atomic.position=self.owner.position
        try:return IntakeAtomicJSON(path_factory=self.atomic.path,native=self.atomic,temporary=self.atomic).atomic_json(str(path),value)
        finally:self.owner.position=self.atomic.position
    def finish(self):
        require(not self.roles_bound or not self.metadata.descriptors,'private_metadata_descriptor_leak')
        if self.atomic is not None:
            require(self.atomic.failure is None and self.atomic.state.phase=='idle','atomic_scope_incomplete')
        self.owner.finish()
