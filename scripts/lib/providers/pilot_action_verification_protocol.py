"""Fixed legacy personal GET and action-ledger Git path selection; read-only."""
from lib.providers.personal_channel_protocol import LegacyPersonalProtocol
from lib.providers.personal_channel_transport import NativePersonalTransport
from lib.personal_channel_process import ReplayPersonalTransport
from lib.requirement_validation_budget import InputAdmissionError

LEDGER='governance/lifecycle/pilot-actions'
class LegacyActionVerificationProtocol(LegacyPersonalProtocol):
    def request(self,kind,arguments,root,cwd):
        if kind=='get':return super().request(kind,arguments,root,cwd)
        if kind!='git-tree' or type(arguments) is not dict or set(arguments)!={'command','cwd','text'}:
            raise InputAdmissionError('pilot_action_verification_readonly_operation_required')
        command=arguments['command']
        if (type(command) is not list or len(command)!=7 or command[:4]!=['git','ls-tree','-r','--name-only']
                or command[5:]!=['--',LEDGER] or type(command[4]) is not str or not command[4]
                or command[4].startswith('-') or len(command[4])>8192 or any(ord(c)<32 for c in command[4])
                or arguments['cwd']!=root or arguments['text'] is not True):
            raise InputAdmissionError('pilot_action_verification_original_git_tree_required')
        return {'kind':kind,'original_arguments':command,'source_root':root,'cwd':root,'timeout':90,'text':True}

class NativeActionVerificationTransport(NativePersonalTransport):
    def __init__(self,owner,root,*,emit_stderr,environment=None,provider_executable='gh'):
        super().__init__(owner,root,LegacyActionVerificationProtocol(),emit_stderr=emit_stderr,environment=environment,provider_executable=provider_executable)

class ReplayActionVerificationTransport(ReplayPersonalTransport):
    def __init__(self,owner,root,*,emit_stderr):
        super().__init__(owner,root,LegacyActionVerificationProtocol(),emit_stderr=emit_stderr)
