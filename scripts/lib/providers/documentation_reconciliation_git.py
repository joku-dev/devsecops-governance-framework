"""Explicit finite native Git read port; target repository programs never selected."""
from pathlib import Path
import os,stat,subprocess,re,sys,platform
from lib.providers.document_rendering_tools import NativeProcess,program_identity
from lib.providers.workbook_import_io import ordinary_ancestors
from lib.requirement_validation_budget import InputAdmissionError
from lib.documentation_reconciliation_git import request,actual_arguments,value

def lookup(cwd,environment):
    path=environment.get('PATH',os.defpath)
    for directory in path.split(os.pathsep):
        label=os.path.join(directory,'git');target=Path(label)
        if not target.is_absolute():target=Path(cwd)/target
        if target.exists() and os.access(target,os.F_OK|os.X_OK) and not target.is_dir():return label
    return None

class NativeGit:
    def __init__(self,owner,root,timeout=30):
        self.owner,self.root,self.calls=owner,root,0
        if type(timeout) not in (int,float) or not 0<timeout<=30:raise InputAdmissionError('documentation_git_timeout_required')
        self.timeout=timeout
    def error_type(self,error):
        if not isinstance(error,re.error):return type(error).__name__
        version=list(sys.version_info[:3]);name=type(error).__name__
        if sys.implementation.name!='cpython' or version[0]!=3 or version[1]<10 or name!=('PatternError' if version[1]>=13 else 'error'):
            raise InputAdmissionError('documentation_regex_runtime_not_admitted')
        self.owner.append({'kind':'documentation-original-regex-context','implementation':'cpython','version':version,'regex_error_type':name})
        return name
    def context(self):
        path=Path(str(self.root));ordinary_ancestors(path);info=path.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.geteuid() or info.st_mode&0o7022:
            raise InputAdmissionError('documentation_owned_source_required')
        return {'identity':[info.st_dev,info.st_ino],'mode':stat.S_IMODE(info.st_mode),'uid':info.st_uid}
    def run(self,command,**options):
        args=request(command,options,self.root);self.calls+=1
        if self.calls>32:raise InputAdmissionError('documentation_git_operation_budget')
        environment={k:v for k,v in os.environ.items() if not k.startswith(('GIT_','LD_','DYLD_'))}
        environment.update(GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_SYSTEM='/dev/null',GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_COUNT='0',GIT_OPTIONAL_LOCKS='0',GIT_NO_REPLACE_OBJECTS='1',GIT_NO_LAZY_FETCH='1',GIT_ALLOW_PROTOCOL='',GIT_TERMINAL_PROMPT='0',GIT_ASKPASS='/bin/false')
        cache={}
        def store(raw):
            ref=self.owner.blob(raw);cache[ref['sha256']]=raw;return ref
        def effect():
            before=self.context();selected=lookup(str(self.root),environment);identity=None if selected is None else program_identity(selected,str(self.root))
            if identity is not None and Path(identity['resolved']).is_relative_to(Path(str(self.root))):
                raise InputAdmissionError('documentation_source_program_not_admitted')
            actual=actual_arguments('git' if selected is None else selected,command);process=NativeProcess();error=None;code=None;out=err=b''
            try:code,out,err=process.run(actual,str(self.root),environment,self.timeout)
            except OSError as caught:error={'type':type(caught).__name__,'message':str(caught)}
            after=self.context()
            if before!=after or identity is not None and program_identity(selected,str(self.root))!=identity:
                raise InputAdmissionError('documentation_git_source_or_tool_changed')
            observe=process.observation
            if observe['timed_out'] or observe['stream_budget_exceeded']:
                raise InputAdmissionError('documentation_git_process_capture_incomplete')
            failure=None if code in (None,0) else {'type':'CalledProcessError','message':str(subprocess.CalledProcessError(code,command,output=out,stderr=err))}
            signal_context=None if code is None or code>=0 else {'implementation':sys.implementation.name,'version':list(sys.version_info[:3]),'system':platform.system()}
            return {'schema_version':1,'command':command,'cwd':str(self.root),'actual_arguments':actual,'program':identity,
                    'source_before':before,'source_after':after,'effective_encoding':subprocess._text_encoding(),
                    'returncode':code,'stdout':store(out),'stderr':store(err),'start_error':error,'return_error':failure,'signal_context':signal_context,
                    'observation':{k:observe[k] for k in ('started','terminal_observed','returncode','timed_out','stream_budget_exceeded','OS_network_or_process_tree_isolation_attested')}}
        wire=self.owner.perform('documentation-local-git',args,effect)
        return value(wire,args,lambda ref:cache[ref['sha256']])
