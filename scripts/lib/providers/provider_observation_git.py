"""Finite trusted Git process adapter; never select source programs or filters."""
from lib.provider_observation_git import CheckedGit,GitProfile
from lib.providers.personal_channel_transport import NativePersonalTransport


class NativeObservationGit(CheckedGit,NativePersonalTransport):
    def __init__(self,owner,root,*,emit_stderr,environment=None):
        super().__init__(owner,root,GitProfile(),emit_stderr=emit_stderr,environment=environment)
    def incomplete(self):self.record.capture_incomplete=True
