"""Fixed operating-capture Git tree/show and original read-only personal GETs."""
from lib.providers.personal_channel_protocol import LegacyPersonalProtocol,GIT_SAFETY
from lib.providers.personal_channel_transport import NativePersonalTransport
from lib.personal_channel_process import ReplayPersonalTransport
from lib.requirement_validation_budget import InputAdmissionError

CAPTURES='generated/reports/lifecycle-operating-acceptance'
INDEX='status/governance-lifecycle-live.json'
def base(value):
    return type(value) is str and bool(value) and not value.startswith('-') and len(value)<=8192 and not any(ord(c)<32 or 0xd800<=ord(c)<=0xdfff for c in value)

class LegacyOperatingVerificationProtocol(LegacyPersonalProtocol):
    def request(self,kind,arguments,root,cwd):
        if kind=='get':return super().request(kind,arguments,root,cwd)
        if kind=='git-tree':
            if type(arguments) is not dict or set(arguments)!={'command','cwd','text'}:raise InputAdmissionError('operating_verification_original_git_options_required')
            command=arguments['command']
            if (type(command) is not list or len(command)!=7 or command[:4]!=['git','ls-tree','-r','--name-only']
                    or not base(command[4]) or command[5:]!=['--',CAPTURES] or arguments['cwd']!=root or arguments['text'] is not True):
                raise InputAdmissionError('operating_verification_original_git_tree_required')
            return {'kind':kind,'original_arguments':command,'source_root':root,'cwd':root,'timeout':90,'text':True}
        if kind=='git-run':
            if type(arguments) is not dict or set(arguments)!={'command','cwd','capture_output'}:raise InputAdmissionError('operating_verification_original_git_run_options_required')
            command=arguments['command'];suffix=':'+INDEX
            if (type(command) is not list or len(command)!=3 or command[:2]!=['git','show'] or type(command[2]) is not str
                    or not command[2].endswith(suffix) or not base(command[2][:-len(suffix)])
                    or arguments['cwd']!=root or arguments['capture_output'] is not True):
                raise InputAdmissionError('operating_verification_original_index_show_required')
            return {'kind':kind,'original_arguments':command,'source_root':root,'cwd':root,'timeout':90,'text':False}
        raise InputAdmissionError('operating_verification_readonly_operation_required')
    def actual_arguments(self,spec,selected):
        original=spec['original_arguments'];label=original[0] if selected is None else selected
        return [label,*(GIT_SAFETY if spec['kind'] in ('git-tree','git-run') else []),*original[1:]]

class NativeOperatingVerificationTransport(NativePersonalTransport):
    def __init__(self,owner,root,*,emit_stderr,environment=None,provider_executable='gh'):
        super().__init__(owner,root,LegacyOperatingVerificationProtocol(),emit_stderr=emit_stderr,environment=environment,provider_executable=provider_executable)
    def run(self,command,*,cwd,capture_output):
        return self.request('git-run',{'command':command,'cwd':str(cwd),'capture_output':capture_output})

class ReplayOperatingVerificationTransport(ReplayPersonalTransport):
    def __init__(self,owner,root,*,emit_stderr):
        super().__init__(owner,root,LegacyOperatingVerificationProtocol(),emit_stderr=emit_stderr)
    def run(self,command,*,cwd,capture_output):
        return self.request('git-run',{'command':command,'cwd':str(cwd),'capture_output':capture_output})
