"""Closed original own-source Git reads and explicit adapter configuration admission."""
from lib.personal_channel_process import ReplayPersonalTransport
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError

HEAD=['git','rev-parse','HEAD']
STATUS=['git','status','--porcelain=v1','-z','--untracked-files=all','--','.github','scripts','model/controls','releases']
CONFIG=['git','config','--null','--name-only','--list','--no-includes']


class GitProfile:
    def request(self,kind,arguments,root,cwd):
        if (kind!='git-tree' or type(arguments) is not dict or set(arguments)!={'command','cwd','text'}
                or arguments['cwd']!=root or type(arguments['text']) is not bool
                or not any(arguments['command']==cmd and arguments['text'] is text
                    for cmd,text in ((HEAD,True),(STATUS,False),(CONFIG,False)))):
            raise InputAdmissionError('provider_observation_original_Git_read_required')
        return {'kind':kind,'source_root':root,'cwd':root,'text':arguments['text'],
            'original_arguments':arguments['command'],'timeout':30}
    def actual_arguments(self,spec,selected):
        return [selected or 'git','--no-optional-locks','--literal-pathspecs',
            '-c','safe.directory='+spec['source_root'],'-c','core.hooksPath=/dev/null',
            '-c','core.fsmonitor=false','-c','core.attributesFile=/dev/null',
            '-c','protocol.allow=never',*spec['original_arguments'][1:]]


def admit_config(raw):
    # Configuration listing is a Git builtin; --no-includes prevents reading
    # delegated files. Reject every include and filter definition before status
    # can invoke a source-configured clean/process helper. Global/system and
    # environment Git configuration are disabled by the native transport.
    if type(raw) is not bytes or len(raw)>8*1024**2:
        raise InputAdmissionError('provider_observation_Git_configuration_required')
    if raw and not raw.endswith(b'\0'):
        raise InputAdmissionError('provider_observation_Git_configuration_changed')
    for row in filter(None,raw.split(b'\0')):
        key=row
        if not key or any(c<32 or c>126 for c in key):
            raise InputAdmissionError('provider_observation_Git_configuration_changed')
        if key.lower().startswith((b'filter.',b'include.',b'includeif.')):
            raise InputAdmissionError('provider_observation_source_Git_program_or_include_forbidden')


class CheckedGit:
    def check_output(self,command,*,cwd,text=False):
        if getattr(self,'failure',None) is not None:raise self.failure
        try:return self.original_read(command,cwd=cwd,text=text)
        except (InputAdmissionError,IntegrityError) as error:
            self.failure=error;self.incomplete();raise
    def original_read(self,command,*,cwd,text):
        arguments={'command':command,'cwd':str(cwd),'text':text}
        self.profile.request('git-tree',arguments,self.root,self.owner.cwd)
        if command==CONFIG:raise InputAdmissionError('provider_observation_original_Git_read_required')
        try:admit_config(self.request('git-tree',{'command':CONFIG,'cwd':self.root,'text':False}))
        except Exception as error:
            self.incomplete()
            if isinstance(error,InputAdmissionError):raise
            raise InputAdmissionError('provider_observation_Git_configuration_capture_incomplete') from None
        return self.request('git-tree',arguments)


class ReplayObservationGit(CheckedGit,ReplayPersonalTransport):
    def __init__(self,owner,root,*,emit_stderr):
        super().__init__(owner,root,GitProfile(),emit_stderr=emit_stderr)
    def incomplete(self):pass
    def request(self,kind,args):
        try:return super().request(kind,args)
        except (InputAdmissionError,IntegrityError):raise
        except (KeyError,ValueError,OSError,TypeError):
            raise IntegrityError('provider_observation_Git_retained_data_changed') from None
