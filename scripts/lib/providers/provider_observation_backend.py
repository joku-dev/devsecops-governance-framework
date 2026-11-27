"""Native composition of checked credentials, actual GETs and whole atomic writes."""
from datetime import datetime,timezone
import os
from lib.provider_observation_backend import ObservationScope
from lib.providers.provider_observation_private_ports import NativePrivateMetadata
from lib.providers.provider_observation_credentials import NativeCredentialCapability
from lib.providers.provider_observation_profile import NativeCheckedProfile
from lib.providers.provider_observation_reads import NativeObservationReads
from lib.providers.intake_atomic_effects import NativeAtomicEffects
from lib.intake_atomic_ports import program
from lib.requirement_validation_budget import InputAdmissionError


class NativeObservationBackend(ObservationScope):
    def __init__(self,owner,*,protected_roots,clock=None):
        super().__init__(owner,protected_roots=protected_roots);self.record=owner.record;self.metadata=self.credentials=self.profile=None;self.native_clock=clock or (lambda:datetime.now(timezone.utc).isoformat());self.reads=NativeObservationReads(self.record,lambda reference:self.credentials.resolve(reference))
    def roles(self,profile,credential,output):
        values=self.selections(profile,credential,output);self.metadata=NativePrivateMetadata(self.record,cwd=self.owner.cwd,files=[values['profile'],values['credential']]);self.credentials=NativeCredentialCapability(self.record,self.metadata,credential=values['credential']);self.profile=NativeCheckedProfile(self.record,self.metadata,profile=values['profile'])
    def umask(self,value):
        if type(value) is not int or value!=0o077:raise InputAdmissionError('provider_observation_original_umask_required')
        return self.owner.perform('provider-observation-umask',{'mask':value},lambda:os.umask(value))
    def clock(self):return self.owner.perform('provider-observation-clock',{},self.native_clock)
    def atomic_json(self,path,value):
        if self.record.capture_incomplete:raise InputAdmissionError('provider_observation_capture_already_incomplete')
        if self.atomic is None:self.atomic=NativeAtomicEffects(self.atomic_scope(),self.record,forbidden_roots=self.protected_roots)
        return program(self.atomic).atomic_json(str(path),value)
    def release_resources(self):
        self.reads.release_credentials()
        return {'credential':None if self.credentials is None else self.credentials.release_resources(),
            'profile':None if self.profile is None else self.profile.release_resources(),
            'private_metadata':None if self.metadata is None else self.metadata.release_resources(),
            'atomic':None if self.atomic is None else self.atomic.release_resources()}
