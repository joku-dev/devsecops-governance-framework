"""Original readonly personal GET and committed-action-request Git check profile."""
from pathlib import PurePosixPath
from lib.providers.personal_channel_protocol import LegacyPersonalProtocol,GIT_SAFETY
from lib.providers.personal_channel_transport import NativePersonalTransport
from lib.personal_channel_process import ReplayPersonalTransport
from lib.requirement_validation_budget import InputAdmissionError

DESCRIPTION='Prepare a bounded pilot update from protected main; publication remains a separate PR step.'
class LegacyPilotUpdateProtocol(LegacyPersonalProtocol):
    def request(self,kind,arguments,root,cwd):
        if kind=='get':return super().request(kind,arguments,root,cwd)
        if kind!='git-checked-run' or type(arguments) is not dict or set(arguments)!={'command','cwd','check','capture_output'}:raise InputAdmissionError('pilot_update_checked_read_options_required')
        command=arguments['command']
        if type(command) is not list or len(command)!=5 or command[:4]!=['git','ls-files','--error-unmatch','--']:raise InputAdmissionError('pilot_update_committed_request_check_required')
        path=command[4]
        if (type(path) is not str or not path.startswith('model/governance/lifecycle/action-requests/') or len(path)>8192
                or any(ord(c)<32 or 0xd800<=ord(c)<=0xdfff for c in path) or str(PurePosixPath(path))!=path or '..' in PurePosixPath(path).parts
                or arguments['cwd']!=root or arguments['check'] is not True or arguments['capture_output'] is not True):raise InputAdmissionError('pilot_update_committed_request_path_required')
        return {'kind':kind,'original_arguments':command,'source_root':root,'cwd':root,'timeout':90,'text':False}
    def actual_arguments(self,spec,selected):
        original=spec['original_arguments'];return [original[0] if selected is None else selected,*(GIT_SAFETY if spec['kind']=='git-checked-run' else []),*original[1:]]
class NativePilotUpdateTransport(NativePersonalTransport):
    def __init__(self,owner,root,*,emit_stderr,provider_executable='gh',environment=None):super().__init__(owner,root,LegacyPilotUpdateProtocol(),emit_stderr=emit_stderr,provider_executable=provider_executable,environment=environment)
    def run(self,command,*,cwd,check,capture_output):return self.request('git-checked-run',{'command':command,'cwd':str(cwd),'check':check,'capture_output':capture_output})
class ReplayPilotUpdateTransport(ReplayPersonalTransport):
    def __init__(self,owner,root,*,emit_stderr):super().__init__(owner,root,LegacyPilotUpdateProtocol(),emit_stderr=emit_stderr)
    def run(self,command,*,cwd,check,capture_output):return self.request('git-checked-run',{'command':command,'cwd':str(cwd),'check':check,'capture_output':capture_output})
