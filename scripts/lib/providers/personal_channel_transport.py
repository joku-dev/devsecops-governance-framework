"""Explicit read-only provider/local-Git and clock observations; credentials stay in gh."""
from datetime import datetime,timezone
from pathlib import Path
import os,platform,stat,subprocess,sys
from lib.providers.document_rendering_tools import program_identity
from lib.providers.workbook_import_io import ordinary_ancestors,original_error,failure_value
from lib.providers.personal_channel_process import NativeReadProcess
from lib.providers.synthetic_lifecycle_io import capture_port
from lib.personal_channel_process import process_value,clock_value,MAX_CALLS,MAX_STDOUT,MAX_STDERR
from lib.requirement_validation_budget import InputAdmissionError

def lookup(name,cwd,environment):
    if os.path.dirname(name):return name
    for directory in environment.get('PATH',os.defpath).split(os.pathsep):
        label=os.path.join(directory,name);path=Path(label) if Path(label).is_absolute() else Path(cwd)/label
        if path.exists() and not path.is_dir() and os.access(path,os.F_OK|os.X_OK):return label
    return None

class NativePersonalTransport:
    def __init__(self,owner,root,profile,*,emit_stderr,environment=None,provider_executable='gh',stream_limits=(MAX_STDOUT,MAX_STDERR)):
        self.owner,self.root,self.profile,self.emit_stderr=owner,str(root),profile,emit_stderr
        self.environment=dict(os.environ if environment is None else environment);self.provider_executable=provider_executable
        if type(provider_executable) is not str or not provider_executable or '\0' in provider_executable or len(provider_executable)>8192:raise InputAdmissionError('personal_provider_executable_required')
        self.calls=0;self.stream_limits=stream_limits;self.process_factory=lambda:NativeReadProcess(stream_limits=stream_limits)

    @property
    def record(self):return self.owner.record

    def context(self):
        path=Path(self.root);ordinary_ancestors(path);value=path.lstat()
        if not stat.S_ISDIR(value.st_mode) or value.st_uid!=os.geteuid() or value.st_mode&0o7022:raise InputAdmissionError('personal_owned_source_required')
        return {'identity':[value.st_dev,value.st_ino],'mode':stat.S_IMODE(value.st_mode),'uid':value.st_uid}

    @capture_port
    def request(self,kind,arguments):
        self.calls+=1
        if self.calls>MAX_CALLS:raise InputAdmissionError('personal_transport_operation_budget')
        spec=self.profile.request(kind,arguments,self.root,self.owner.cwd);environment=dict(self.environment)
        if kind=='git-tree':
            environment={k:v for k,v in environment.items() if not k.startswith(('GIT_','LD_','DYLD_'))}
            environment.update(GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_SYSTEM='/dev/null',GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_COUNT='0',GIT_OPTIONAL_LOCKS='0',GIT_NO_REPLACE_OBJECTS='1',GIT_NO_LAZY_FETCH='1',GIT_ALLOW_PROTOCOL='',GIT_TERMINAL_PROMPT='0',GIT_ASKPASS='/bin/false')
        cache={}
        def store(raw):
            ref=self.owner.blob(raw);cache[ref['sha256']]=raw;return ref
        def effect():
            before=self.context();ordinary_ancestors(Path(spec['cwd']))
            name=self.provider_executable if kind=='get' else 'git';selected=lookup(name,spec['cwd'],environment)
            identity=None if selected is None else program_identity(selected,spec['cwd'])
            if identity is not None and (Path(identity['resolved']).is_relative_to(Path(self.root)) or Path(identity['resolved']).is_relative_to(self.owner.private_state)):
                raise InputAdmissionError('personal_source_or_private_program_forbidden')
            actual=self.profile.actual_arguments(spec,selected);process=self.process_factory();code=None;out=err=b'';start=None
            codec=subprocess._text_encoding() if spec['text'] else None
            try:code,out,err=process.run(actual,spec['cwd'],environment,spec['timeout'])
            except OSError as error:start=failure_value(original_error(error,spec['original_arguments'][0]))
            after=self.context()
            if before!=after or identity is not None and program_identity(selected,spec['cwd'])!=identity:raise InputAdmissionError('personal_source_or_program_changed')
            observe=process.observation
            if observe['stream_budget_exceeded']:raise InputAdmissionError('personal_process_capture_incomplete')
            # The original local Git call has no timeout. Our finite capture
            # deadline cannot be represented as an original TimeoutExpired.
            if observe['timed_out'] and kind=='git-tree':raise InputAdmissionError('personal_git_observation_deadline')
            signal_context=None;error=None
            if observe['timed_out']:error={'type':'TimeoutExpired','message':str(subprocess.TimeoutExpired(spec['original_arguments'],spec['timeout'],output=out))}
            elif code:
                error={'type':'CalledProcessError','message':str(subprocess.CalledProcessError(code,spec['original_arguments'],output=out))}
                if code<0:signal_context={'implementation':sys.implementation.name,'version':list(sys.version_info[:3]),'system':platform.system()}
            return {'schema_version':1,'specification':spec,'actual_arguments':actual,'program':identity,'source_before':before,'source_after':after,
                    'returncode':code,'stdout':store(out),'stderr':store(err),'start_error':start,'original_error':error,
                    'signal_context':signal_context,'effective_encoding':codec,'observation':observe}
        try:
            wire=self.owner.perform('personal-read-process',spec,effect)
            return process_value(wire,spec,self.profile,lambda ref:cache[ref['sha256']],emit_stderr=self.emit_stderr,stream_limits=self.stream_limits)
        except (UnicodeError,):raise
        except Exception as error:
            from lib.requirement_review_output import RetainedOutputError
            if isinstance(error,RetainedOutputError):raise
            self.owner.record.capture_incomplete=True
            if isinstance(error,InputAdmissionError):raise
            raise InputAdmissionError('personal_process_capture_incomplete') from error

    def fetch(self,endpoint):return self.request('get',{'endpoint':endpoint})
    def check_output(self,command,*,cwd,text):return self.request('git-tree',{'command':command,'cwd':str(cwd),'text':text})
    def clock(self):
        def effect():return {'schema_version':1,'clock':'UTC-seconds','value':datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')}
        try:return clock_value(self.owner.perform('personal-capture-clock',{'format':'UTC-seconds'},effect))
        except Exception as error:
            self.owner.record.capture_incomplete=True
            if isinstance(error,InputAdmissionError):raise
            raise InputAdmissionError('personal_clock_capture_incomplete') from error
