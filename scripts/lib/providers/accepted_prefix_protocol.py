"""Explicit native/pure process composition; hashing requires a frozen private scope."""
from lib.accepted_prefix_protocol import LegacyAcceptedPrefixProtocol
from lib.providers.personal_channel_transport import NativePersonalTransport
from lib.personal_channel_process import ReplayPersonalTransport

class NativeAcceptedPrefixTransport(NativePersonalTransport):
    def __init__(self,owner,root,context,*,emit_stderr,environment=None,hash_scope=None):
        super().__init__(owner,root,LegacyAcceptedPrefixProtocol(context,hash_scope=hash_scope),emit_stderr=emit_stderr,environment=environment)
    def run(self,command,*,cwd,capture_output):return self.request('git-run',{'command':command,'cwd':str(cwd),'capture_output':capture_output})

class ReplayAcceptedPrefixTransport(ReplayPersonalTransport):
    def __init__(self,owner,root,context,*,emit_stderr,hash_scope=None):
        super().__init__(owner,root,LegacyAcceptedPrefixProtocol(context,hash_scope=hash_scope),emit_stderr=emit_stderr)
    def run(self,command,*,cwd,capture_output):return self.request('git-run',{'command':command,'cwd':str(cwd),'capture_output':capture_output})
