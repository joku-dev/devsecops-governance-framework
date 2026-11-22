"""Exact original two-ledger tree request; no publisher, push or provider POST port."""
from lib.providers.personal_channel_protocol import LegacyPersonalProtocol
from lib.providers.personal_channel_transport import NativePersonalTransport
from lib.personal_channel_process import ReplayPersonalTransport
from lib.providers.operating_verification_protocol import base
from lib.requirement_validation_budget import InputAdmissionError
LEDGERS=['governance/lifecycle/live-validation','governance/lifecycle/pilot-actions']
class LegacyPublicationValidationProtocol(LegacyPersonalProtocol):
    def request(self,kind,arguments,root,cwd):
        if kind!='git-tree' or type(arguments) is not dict or set(arguments)!={'command','cwd','text'}:
            raise InputAdmissionError('publication_validation_original_readonly_operation_required')
        command=arguments['command']
        if (type(command) is not list or len(command)!=8 or command[:4]!=['git','ls-tree','-r','--name-only']
                or not base(command[4]) or command[5:]!=['--',*LEDGERS]
                or arguments['cwd']!=root or arguments['text'] is not True):
            raise InputAdmissionError('publication_validation_original_two_ledger_tree_required')
        return {'kind':kind,'original_arguments':command,'source_root':root,'cwd':root,'timeout':90,'text':True}
class NativePublicationValidationTransport(NativePersonalTransport):
    def __init__(self,owner,root,*,emit_stderr):super().__init__(owner,root,LegacyPublicationValidationProtocol(),emit_stderr=emit_stderr)
class ReplayPublicationValidationTransport(ReplayPersonalTransport):
    def __init__(self,owner,root,*,emit_stderr):super().__init__(owner,root,LegacyPublicationValidationProtocol(),emit_stderr=emit_stderr)
