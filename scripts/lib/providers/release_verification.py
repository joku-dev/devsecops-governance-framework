"""Finite bounded Git/SSH verification in an isolated retained-reference capsule."""
import base64
from copy import deepcopy
import os
from pathlib import Path
import selectors
import shutil
import subprocess
import tempfile
import time
from types import SimpleNamespace

from lib.providers import process_groups
from lib.providers.attestation_verification import executable
from lib import release_reference_facts as facts
from lib.release_requests import ReleaseRequests,git_prefix

MAX_STREAM=65536


class ReleaseVerificationEnvironment(ReleaseRequests):
    def __init__(self,root,files,references,workarea,*,git_tool=None,ssh_tool=None,on_start=None,on_intent=None,on_finish=None,timeout=30):
        super().__init__(root,files);facts.validate(references)
        if type(timeout) not in (int,float) or not 0<timeout<=30:raise ValueError('invalid_release_native_timeout')
        workarea=Path(workarea)
        if workarea.is_symlink() or not workarea.is_dir() or workarea.stat().st_mode&0o077:
            raise ValueError('private_release_workarea_required')
        if any(callback is not None and not callable(callback) for callback in (on_start,on_intent,on_finish)):
            raise ValueError('release_native_journal_callback_required')
        self.timeout=timeout;self.references=deepcopy(references);self.observations=[];self.on_start=on_start
        self.on_intent=on_intent;self.on_finish=on_finish
        self.tools={}
        for name,selected in [('git',git_tool),('ssh-keygen',ssh_tool)]:
            found=selected if selected is not None else shutil.which(name)
            if found is None:raise FileNotFoundError('release_native_tool_missing')
            self.tools[name]=executable(found)
            if Path(self.tools[name][0]).is_relative_to(self.root):
                raise ValueError('release_native_tool_inside_inspected_source')
        self.context=tempfile.TemporaryDirectory(prefix='release-git-',dir=workarea)
        self.capsule=Path(self.context.name);self.staged=self.capsule/'inputs';self.staged.mkdir(mode=0o700)
        self.staged_count=0
        self.environment={'LANG':'C.UTF-8','PATH':'','GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_SYSTEM':'/dev/null',
            'GIT_CONFIG_NOSYSTEM':'1','GIT_CONFIG_COUNT':'0','GIT_TERMINAL_PROMPT':'0','GIT_ASKPASS':'/bin/false',
            'GIT_NO_REPLACE_OBJECTS':'1','GIT_NO_LAZY_FETCH':'1','GIT_ALLOW_PROTOCOL':'','GIT_OPTIONAL_LOCKS':'0'}
        self.git_prefix=git_prefix(self.tools,self.capsule)
        self.metadata={'schema_version':1,'capsule_root':str(self.capsule),'tools':{name:list(value) for name,value in self.tools.items()}}
        try:self.prepare()
        except BaseException:self.close();raise

    def __enter__(self):return self
    def __exit__(self,*args):self.close()
    def close(self):self.context.cleanup()

    def prepare(self):
        requests=[({'stage':'capsule-init','object_format':self.references['object_format']},
            ['init','--bare','--template=','-b','release-capsule','--object-format='+self.references['object_format']],None,None)]
        for oid,row in sorted(self.references['objects'].items()):
            requests.append(({'stage':'capsule-object','oid':oid,'kind':row['kind']},
                ['hash-object','-w','--stdin','-t',row['kind']],base64.b64decode(row['base64'],validate=True),oid))
        for name,oid in sorted(self.references['refs'].items()):
            requests.append(({'stage':'capsule-ref','name':name,'oid':oid},['update-ref','refs/tags/'+name,oid],None,None))
        for request,arguments,stdin,expected in requests:
            result=self.observe('git',self.git_prefix+arguments,request,stdin)
            if result.returncode or expected is not None and result.stdout.decode('ascii').strip()!=expected:
                raise ValueError('release_capsule_preparation_failed')

    def stage(self,raw):
        self.staged_count+=1
        if self.staged_count>4096:raise ValueError('release_native_staging_budget')
        path=self.staged/str(self.staged_count);fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        with os.fdopen(fd,'wb') as stream:stream.write(raw)
        return str(path)

    def run(self,command,**kwargs):
        request=self.request(command,**kwargs);operation=request['operation']
        stdin=None if request['stdin_base64'] is None else base64.b64decode(request['stdin_base64'],validate=True)
        if command[0]=='git':
            arguments=command[1:]
            if operation=='verify-tag':
                original=command[2].split('=',1)[1];allowed=self.stage(self.temporary_bytes(original))
                arguments=['-c','gpg.ssh.allowedSignersFile='+allowed,*command[3:]]
            argv=self.git_prefix+arguments
        else:
            argv=[self.tools['ssh-keygen'][0],*command[1:]]
            if operation=='signer-fingerprint':argv[2]=self.stage(self.temporary_bytes(command[2]))
            else:
                argv[4]=self.stage(self.temporary_bytes(command[4]))
                argv[10]=self.stage(self.source_bytes(command[10]))
        result=self.observe(command[0],argv,{'stage':'decision','request':request},stdin)
        if not request['text']:return result
        return SimpleNamespace(returncode=result.returncode,
            stdout=result.stdout.decode('utf-8').replace('\r\n','\n').replace('\r','\n'),
            stderr=result.stderr.decode('utf-8').replace('\r\n','\n').replace('\r','\n'))

    def observe(self,tool,argv,request,stdin):
        for name,selected in self.tools.items():
            if executable(selected[0])!=selected:raise ValueError('release_native_tool_changed')
        row={'request':request,'tool':tool,'tool_path':self.tools[tool][0],'tool_sha256':self.tools[tool][1],
            'ssh_tool_path':self.tools['ssh-keygen'][0],'ssh_tool_sha256':self.tools['ssh-keygen'][1],
            'argv':argv,'process_started':False,'returncode':None,'timed_out':False,'output_truncated':False,'error_type':None}
        if self.on_intent is not None:self.on_intent(deepcopy(row))
        self.observations.append(row);process=None;streams={'stdout':bytearray(),'stderr':bytearray()}
        try:
            process=subprocess.Popen(argv,cwd=self.capsule,env=self.environment,stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
                stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,umask=0o077)
            row['process_started']=True
            if self.on_start is not None:self.on_start(deepcopy(row))
            deadline=time.monotonic()+self.timeout
            with selectors.DefaultSelector() as selector:
                for name in streams:
                    stream=getattr(process,name);os.set_blocking(stream.fileno(),False);selector.register(stream,selectors.EVENT_READ,name)
                remaining=memoryview(stdin) if stdin is not None else None
                if remaining is not None:
                    os.set_blocking(process.stdin.fileno(),False);selector.register(process.stdin,selectors.EVENT_WRITE,'stdin')
                while selector.get_map():
                    if time.monotonic()>=deadline:row['timed_out']=True;raise TimeoutError('release_native_timeout')
                    for key,_ in selector.select(min(.1,max(0,deadline-time.monotonic()))):
                        if key.data=='stdin':
                            try:written=os.write(key.fd,remaining[:65536]);remaining=remaining[written:]
                            except BrokenPipeError:remaining=remaining[:0]
                            if not remaining:selector.unregister(key.fileobj);process.stdin.close()
                            continue
                        raw=os.read(key.fd,65536)
                        if not raw:selector.unregister(key.fileobj);continue
                        available=MAX_STREAM-len(streams[key.data]);streams[key.data].extend(raw[:available])
                        if len(raw)>available:row['output_truncated']=True;raise ValueError('release_native_output_budget')
            process.wait(timeout=max(.001,deadline-time.monotonic()));row['returncode']=process.returncode
            for name,selected in self.tools.items():
                if executable(selected[0])!=selected:raise ValueError('release_native_tool_changed')
        except BaseException as error:
            row['error_type']=type(error).__name__;raise
        finally:
            try:
                if process is not None:
                    try:process_groups.stop(process)
                    finally:
                        for name in ('stdin','stdout','stderr'):
                            stream=getattr(process,name)
                            if stream is not None:stream.close()
            except BaseException as error:row['error_type']=type(error).__name__;raise
            finally:
                row.update(process_groups.observations(process))
                row.update({name+'_base64':base64.b64encode(bytes(raw)).decode('ascii') for name,raw in streams.items()})
                if self.on_finish is not None:self.on_finish(deepcopy(row))
        return SimpleNamespace(returncode=row['returncode'],**{name:bytes(raw) for name,raw in streams.items()})
