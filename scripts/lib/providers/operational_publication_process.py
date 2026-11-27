"""Explicit finite Git/legacy POST writer; no shell or automatic rollback.

Only the whole publisher's operations are admitted. A timeout or incomplete
capture is technical failure after potentially visible native effects.
"""
from pathlib import Path,PurePosixPath
from types import SimpleNamespace
from urllib.parse import urlsplit
import hashlib,json,os,re,selectors,stat,subprocess,time
from lib.providers.workbook_import_io import failure_value
from lib.providers import process_groups
from lib.providers.document_rendering_tools import program_identity
from lib.providers.personal_channel_transport import lookup
from lib.requirement_validation_budget import InputAdmissionError

class NativePublisherPipes:
    def __init__(self):
        self.observation={'started':False,'terminal_observed':False,'returncode':None,'timed_out':False,'stream_budget_exceeded':False,'OS_network_or_process_tree_isolation_attested':False}
    def run(self,arguments,cwd,environment,timeout,stdin):
        process=None;buffers={'stdout':bytearray(),'stderr':bytearray()};offset=0;deadline=None
        try:
            process=subprocess.Popen(arguments,cwd=cwd,env=environment,stdin=subprocess.PIPE if stdin is not None else None,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True);started=time.monotonic();self.observation['started']=True
            with selectors.DefaultSelector() as selector:
                for name in buffers:
                    stream=getattr(process,name);os.set_blocking(stream.fileno(),False);selector.register(stream,selectors.EVENT_READ,name)
                if stdin is not None:
                    os.set_blocking(process.stdin.fileno(),False)
                    if stdin:selector.register(process.stdin,selectors.EVENT_WRITE,'stdin')
                    else:process.stdin.close()
                while selector.get_map() or process.poll() is None:
                    now=time.monotonic()
                    if deadline is None and now-started>=timeout:self.observation['timed_out']=True;process_groups.stop(process);deadline=time.monotonic()+2
                    if deadline is not None and now>=deadline:raise InputAdmissionError('operational_publication_pipe_drain_incomplete')
                    for selected,_ in selector.select(.02):
                        if selected.data=='stdin':
                            try:offset+=os.write(selected.fd,stdin[offset:offset+65536])
                            except BrokenPipeError:offset=len(stdin)
                            if offset==len(stdin):selector.unregister(selected.fileobj);selected.fileobj.close()
                            continue
                        raw=os.read(selected.fd,65536)
                        if not raw:selector.unregister(selected.fileobj);continue
                        name=selected.data;limit=16*1024**2 if name=='stdout' else 256*1024
                        if len(buffers[name])+len(raw)>limit:self.observation['stream_budget_exceeded']=True;raise InputAdmissionError('operational_publication_stream_budget')
                        buffers[name].extend(raw)
            code=process.wait(timeout=2);self.observation.update(terminal_observed=True,returncode=code)
            if self.observation['timed_out']:raise InputAdmissionError('operational_publication_native_deadline')
            return code,bytes(buffers['stdout']),bytes(buffers['stderr'])
        finally:
            try:
                if process is not None:process_groups.stop(process,graceful=process.poll() is None)
            finally:
                if process is not None:
                    for name in ('stdin','stdout','stderr'):
                        stream=getattr(process,name,None)
                        if stream is not None and not stream.closed:stream.close()
                self.observation.update(process_groups.observations(process))

GIT_SAFETY=['-c','core.hooksPath=/dev/null','-c','core.fsmonitor=false','-c','core.pager=cat','-c','core.sshCommand=/usr/bin/ssh -o BatchMode=yes -o StrictHostKeyChecking=yes','-c','credential.helper=','-c','remote.origin.receivepack=git-receive-pack','-c','remote.origin.uploadpack=git-upload-pack','-c','fetch.recurseSubmodules=false','-c','submodule.recurse=false','-c','maintenance.auto=false','-c','gc.auto=0']
def path_argument(value):
    return type(value) is str and bool(value) and len(value)<=8192 and '\0' not in value and not PurePosixPath(value).is_absolute() and '..' not in PurePosixPath(value).parts and str(PurePosixPath(value))==value

class NativeOperationalPublicationProcess:
    def __init__(self,root,*,scope,repository,run_id,attempt,profile,environment=None,provider_executable='gh',local_origin_root=None,timeout=90):
        from lib.operational_publication import SCOPES
        self.root=Path(root).absolute();self.profile=profile;self.environment=dict(os.environ if environment is None else environment);self.cwd=str(Path.cwd());self.scope=scope;self.repository=repository
        if scope not in SCOPES or re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repository) is None or any(re.fullmatch(r'[1-9][0-9]*',v) is None for v in (run_id,attempt)):raise InputAdmissionError('operational_publication_bound_context_required')
        self.branch=f'automation/{scope}/{run_id}-{attempt}';self.provider_executable=provider_executable;self.local_origin_root=None if local_origin_root is None else Path(local_origin_root).resolve();self.timeout=timeout
        if type(timeout) not in (int,float) or not 0<timeout<=600:raise InputAdmissionError('operational_publication_deadline_required')
        self.observations=[];self.remote_pins=None;self.root_identity=self.context();self.git_identity=self.git_context()
    def context(self):
        p=self.root
        if p.is_symlink() or not p.is_dir() or p.resolve()!=p:raise InputAdmissionError('operational_publication_owned_source_required')
        s=p.stat()
        if s.st_uid!=os.geteuid() or s.st_mode&0o022:raise InputAdmissionError('operational_publication_owned_source_required')
        return (s.st_dev,s.st_ino,s.st_uid,stat.S_IMODE(s.st_mode))
    def git_context(self):
        # This writer profile accepts a standalone owned clone only. Linked
        # worktrees/shared Git dirs need their own explicit write scope.
        directory=self.root/'.git'
        if directory.is_symlink() or not directory.is_dir() or directory.resolve()!=directory:raise InputAdmissionError('operational_publication_standalone_Git_directory_required')
        value=directory.stat()
        if value.st_uid!=os.geteuid() or value.st_mode&0o022:raise InputAdmissionError('operational_publication_owned_Git_directory_required')
        for name in ('commondir','config.worktree','objects/info/alternates','objects/info/http-alternates'):
            item=directory/name
            if item.exists() or item.is_symlink():raise InputAdmissionError('operational_publication_shared_Git_profile_required')
        for name in ('config','HEAD','objects','refs'):
            item=directory/name
            if item.is_symlink() or item.resolve()!=item:raise InputAdmissionError('operational_publication_Git_alias_not_admitted')
            if item.exists():
                state=item.stat()
                if state.st_uid!=os.geteuid() or state.st_mode&0o022 or not (stat.S_ISDIR(state.st_mode) or stat.S_ISREG(state.st_mode)) or stat.S_ISREG(state.st_mode) and state.st_nlink!=1:raise InputAdmissionError('operational_publication_owned_Git_entry_required')
        return (value.st_dev,value.st_ino,value.st_uid,stat.S_IMODE(value.st_mode))
    def git_write_tree(self):
        # Check every native write directory, including nested ref/log/object
        # paths. This is a bounded observation, not an OS isolation claim.
        stack=[self.root/'.git'];count=0
        while stack:
            directory=stack.pop()
            for item in directory.iterdir():
                count+=1
                if count>100000:raise InputAdmissionError('operational_publication_Git_entry_budget')
                value=item.lstat()
                if value.st_uid!=os.geteuid() or value.st_mode&0o022 or not (stat.S_ISDIR(value.st_mode) or stat.S_ISREG(value.st_mode)):raise InputAdmissionError('operational_publication_Git_write_alias_not_admitted')
                if stat.S_ISDIR(value.st_mode):stack.append(item)
                elif value.st_nlink!=1 and ('objects' not in item.relative_to(self.root/'.git').parts):raise InputAdmissionError('operational_publication_shared_Git_write_entry_not_admitted')
    def git_environment(self):
        env={k:v for k,v in self.environment.items() if not k.startswith(('GIT_','LD_','DYLD_')) or k in ('GIT_AUTHOR_DATE','GIT_COMMITTER_DATE','GIT_AUTHOR_NAME','GIT_AUTHOR_EMAIL','GIT_COMMITTER_NAME','GIT_COMMITTER_EMAIL')}
        env.update(GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_SYSTEM='/dev/null',GIT_CONFIG_NOSYSTEM='1',GIT_CONFIG_COUNT='0',GIT_OPTIONAL_LOCKS='0',GIT_NO_REPLACE_OBJECTS='1',GIT_NO_LAZY_FETCH='1',GIT_TERMINAL_PROMPT='0',GIT_ASKPASS='/bin/false',GIT_ALLOW_PROTOCOL='file' if self.local_origin_root is not None else 'https:ssh')
        return env
    def valid_remote(self,url):
        if self.local_origin_root is not None:
            p=Path(url)
            return p.is_absolute() and p.resolve()==p and p.is_relative_to(self.local_origin_root) and p.is_dir() and not p.is_symlink() and p.stat().st_uid==os.geteuid() and not p.stat().st_mode&0o022
        value=url.removesuffix('.git');wanted=self.repository.lower()
        if value.startswith('git@github.com:'):return value.removeprefix('git@github.com:').lower()==wanted
        parts=urlsplit(value)
        return parts.hostname=='github.com' and parts.query==parts.fragment=='' and parts.path.removeprefix('/').lower()==wanted and ((parts.scheme=='https' and parts.username is None and parts.password is None and parts.port in (None,443)) or (parts.scheme=='ssh' and parts.username=='git' and parts.password is None and parts.port in (None,22)))
    def preflight_filter_profile(self,selected):
        # diff can invoke clean/process filters too. Check before every Git
        # operation, including the first read, without requiring an origin for
        # an original no-change result.
        process=NativePublisherPipes();code,out,err=process.run([selected,*GIT_SAFETY,'config','--get-regexp',r'^(filter\..*\.(clean|smudge|process)|include\.path|includeif\..*\.path|core\.worktree|extensions\.worktreeconfig)$'],str(self.root),self.git_environment(),self.timeout,None)
        if code not in (0,1) or code==0:raise InputAdmissionError('operational_publication_external_filter_profile_required')
    def preflight(self,selected):
        env=self.git_environment()
        def direct(arguments):
            process=NativePublisherPipes();code,out,err=process.run([selected,*GIT_SAFETY,*arguments],str(self.root),env,self.timeout,None)
            if code:raise InputAdmissionError('operational_publication_Git_preflight_unavailable')
            return out.decode(subprocess._text_encoding()).splitlines()
        pull=direct(['remote','get-url','--all','origin']);push=direct(['remote','get-url','--push','--all','origin'])
        if len(pull)!=1 or len(push)!=1 or not all(self.valid_remote(v) for v in (*pull,*push)):raise InputAdmissionError('operational_publication_remote_binding_required')
        pin={'pull_url':pull[0],'push_url':push[0],'local_test_origin':self.local_origin_root is not None}
        if self.remote_pins is not None and self.remote_pins!=pin:raise InputAdmissionError('operational_publication_remote_changed')
        self.remote_pins=pin
    def admit_git(self,command,options):
        from lib.operational_publication import SCOPES,LEDGERS
        if len(command)>20004 or any(type(v) is not str or '\0' in v or len(v)>8192 for v in command):raise InputAdmissionError('operational_publication_Git_arguments_required')
        args=command[1:];root=Path(options.get('cwd','')).absolute()
        if root!=self.root or options.get('capture_output') is not True:raise InputAdmissionError('operational_publication_Git_context_changed')
        exists=len(args)==3 and args[:2]==['cat-file','-e'] and args[2].startswith('HEAD:') and path_argument(args[2][5:]) and args[2][5:].startswith(LEDGERS)
        if exists:
            if set(options)!={'cwd','capture_output','check'} or options['check'] is not False:raise InputAdmissionError('operational_publication_original_exists_options_required')
            return False
        if set(options)!={'cwd','text','capture_output','check'} or options['text'] is not True or options['check'] is not True:raise InputAdmissionError('operational_publication_original_Git_options_required')
        fixed=[['diff','--name-only','--no-renames','-z','HEAD'],['ls-files','--others','--exclude-standard','-z'],['fetch','origin','main'],['merge-base','--is-ancestor','HEAD','refs/remotes/origin/main'],['rev-parse','refs/remotes/origin/main'],['switch','-c',self.branch],['reset','--mixed','HEAD'],['diff','--cached','--name-only','-z'],['rev-parse','HEAD'],['push','origin','HEAD:refs/heads/'+self.branch],['-c','user.name='+self.profile.author_name,'-c','user.email='+self.profile.author_email,'-c','commit.gpgsign=false','commit','-m','Propose '+self.scope+' operational update']]
        add=args[:2]==['add','--'] and len(args)>2 and all(path_argument(v) and any(v.startswith(p) if p.endswith('/') else v==p for p in SCOPES[self.scope]) for v in args[2:])
        if args not in fixed and not add:raise InputAdmissionError('operational_publication_fixed_Git_operation_required')
        return args[:1] in (['fetch'],['switch'],['reset'],['add'],['push'],['-c'])
    def run(self,command,**options):
        self.last_native=None;command=list(command)
        if not command or command[0] not in ('git','gh'):raise InputAdmissionError('operational_publication_fixed_program_required')
        mutation=False;data=None
        if command[0]=='git':
            mutation=self.admit_git(command,options);env=self.git_environment();cwd=str(self.root);name='git'
        else:
            if (set(options)!={'input','text','capture_output','check'} or options['text'] is not True or options['capture_output'] is not True or options['check'] is not True or type(options['input']) is not str or len(options['input'])>1024**2 or len(command)!=7 or command[:4]!=['gh','api','--method','POST'] or command[5:]!=['--input','-']):raise InputAdmissionError('operational_publication_original_POST_options_required')
            payload=json.loads(options['input']);endpoint=command[4]
            if endpoint==self.profile.pulls_endpoint(self.repository):
                if type(payload) is not dict or set(payload)!={'title','head','base','body'} or payload['head']!=self.branch or payload['base']!='main':raise InputAdmissionError('operational_publication_review_target_changed')
            elif endpoint in [self.profile.workflow_endpoint(self.repository,v) for v in self.profile.check_workflows]:
                if payload!={'ref':self.branch}:raise InputAdmissionError('operational_publication_dispatch_target_changed')
            else:raise InputAdmissionError('operational_publication_fixed_POST_endpoint_required')
            env=dict(self.environment)
            if env.get('GH_HOST','github.com')!='github.com':raise InputAdmissionError('operational_publication_explicit_host_profile_required')
            cwd=self.cwd;name=self.provider_executable;mutation=True
        selected=lookup(name,cwd,env);identity=None if selected is None else program_identity(selected,cwd)
        if identity is not None and any(Path(identity['resolved']).is_relative_to(root) for root in (self.root,*getattr(self,'forbidden_program_roots',()))):raise InputAdmissionError('operational_publication_source_or_private_program_forbidden')
        if self.context()!=self.root_identity or self.git_context()!=self.git_identity:raise InputAdmissionError('operational_publication_source_replaced')
        if command[0]=='git' and selected is not None:self.preflight_filter_profile(selected)
        if command[0]=='git' and mutation and selected is not None:self.git_write_tree();self.preflight(selected)
        actual=[selected or command[0],*(GIT_SAFETY if command[0]=='git' else []),*command[1:]];encoding=subprocess._text_encoding() if options.get('text',False) else None
        if 'input' in options:data=options['input'].encode(encoding)
        process=NativePublisherPipes();code=None;out=err=b'';start_error=None;row={'original_arguments':command,'actual_arguments':actual,'cwd':cwd,'write_operation':mutation,'remote':self.remote_pins,'program':identity,'input_sha256':None if data is None else hashlib.sha256(data).hexdigest(),'input_bytes':None if data is None else len(data)};self.observations.append(row)
        try:
            try:code,out,err=process.run(actual,cwd,env,self.timeout,data)
            except OSError as error:
                # Preserve the original executable label in the original leaf.
                if isinstance(error,FileNotFoundError):
                    error=FileNotFoundError(error.errno,error.strerror,command[0]);start_error=failure_value(error);raise error from None
                start_error=failure_value(error)
                raise
            if self.context()!=self.root_identity or self.git_context()!=self.git_identity or identity is not None and program_identity(selected,cwd)!=identity:raise InputAdmissionError('operational_publication_source_or_program_changed')
            stdout=out.decode(encoding).replace('\r\n','\n').replace('\r','\n') if encoding else out;stderr=err.decode(encoding).replace('\r\n','\n').replace('\r','\n') if encoding else err;row.update(returncode=code,stdout_sha256=hashlib.sha256(out).hexdigest(),stderr_sha256=hashlib.sha256(err).hexdigest())
            if code and options['check']:raise subprocess.CalledProcessError(code,command,output=stdout,stderr=stderr)
            return subprocess.CompletedProcess(command,code,stdout,stderr)
        finally:
            row['observation']=dict(process.observation)
            self.last_native={'row':row,'raw_stdout':out,'raw_stderr':err,'raw_stdin':data,'effective_encoding':encoding,'returncode':code,'start_error':start_error,'source_identity':list(self.root_identity),'Git_identity':list(self.git_identity)}
