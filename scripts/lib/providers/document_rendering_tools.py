"""Explicit POSIX Pandoc observations; original argv, finite process, private projection."""
from contextlib import ExitStack
from pathlib import Path
from types import SimpleNamespace
import hashlib,io,math,os,selectors,stat,subprocess,tempfile,time

from lib.providers.document_rendering_io import BoundedCapture
from lib.providers.workbook_import_io import Capture,ordinary_ancestors
from lib.providers.sbom_export_storage import read_private,MAX_BLOB,owned_directory
from lib.providers.validation_worktree import signature
from lib.providers import process_groups
from lib.repository_capture import private_name
from lib.requirement_validation_budget import InputAdmissionError

MAX_BINARY=256*1024**2
MAX_STREAM=256*1024


def which_at(name,cwd,environment):
    """The original POSIX which selection, including empty/relative PATH entries."""
    if name!='pandoc':raise InputAdmissionError('document_fixed_tool_required')
    path=environment.get('PATH')
    if path is None:
        try:path=os.confstr('CS_PATH')
        except (AttributeError,ValueError):path=os.defpath
    if not path:return None
    seen=set()
    for directory in path.split(os.pathsep):
        normalized=os.path.normcase(directory)
        if normalized in seen:continue
        seen.add(normalized);label=os.path.join(directory,name)
        target=Path(label) if Path(label).is_absolute() else Path(cwd)/label
        if target.exists() and os.access(target,os.F_OK|os.X_OK) and not target.is_dir():return label
    return None


def program_identity(label,cwd):
    path=Path(label);path=path if path.is_absolute() else Path(cwd)/path
    if private_name(str(path)):raise InputAdmissionError('document_private_tool_path_forbidden')
    resolved=path.resolve(strict=True);ordinary_ancestors(resolved.parent)
    descriptor=os.open(resolved,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    try:
        before=os.fstat(descriptor)
        if (not stat.S_ISREG(before.st_mode) or before.st_uid not in (0,os.geteuid())
                or before.st_mode&0o7022 or not before.st_mode&0o111 or before.st_size>MAX_BINARY):
            raise InputAdmissionError('document_regular_stable_tool_required')
        digest=hashlib.sha256();size=0
        while part:=os.read(descriptor,65536):
            size+=len(part)
            if size>MAX_BINARY:raise InputAdmissionError('document_tool_byte_budget')
            digest.update(part)
        after=os.fstat(descriptor);entry=resolved.stat(follow_symlinks=False)
        if signature(before)!=signature(after) or signature(before)!=signature(entry) or path.resolve(strict=True)!=resolved:
            raise InputAdmissionError('document_tool_changed_during_capture')
        return {'label':label,'resolved':str(resolved),'sha256':digest.hexdigest(),'bytes':size,
            'mode':stat.S_IMODE(before.st_mode),'uid':before.st_uid,'identity':[before.st_dev,before.st_ino]}
    finally:os.close(descriptor)


class NativeProcess:
    """Finite binary pipe capture; standard text decoding is retained separately."""
    def __init__(self):
        self.observation={'started':False,'terminal_observed':False,'returncode':None,
            'stdout':b'','stderr':b'','start_error':None,'timed_out':False,'stream_budget_exceeded':False,
            'OS_network_or_process_tree_isolation_attested':False}
    def run(self,arguments,cwd,environment,timeout):
        process=None;buffers={'stdout':bytearray(),'stderr':bytearray()};started=time.monotonic()
        try:
            try:
                process=subprocess.Popen(arguments,cwd=cwd,env=environment,stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,start_new_session=True)
            except OSError as error:
                self.observation['start_error']={'type':type(error).__name__,'message':str(error)};raise
            self.observation['started']=True
            with selectors.DefaultSelector() as selector:
                for name in buffers:
                    stream=getattr(process,name);os.set_blocking(stream.fileno(),False)
                    selector.register(stream,selectors.EVENT_READ,name)
                while selector.get_map() or process.poll() is None:
                    if time.monotonic()-started>=timeout:
                        self.observation['timed_out']=True;raise InputAdmissionError('document_tool_timeout')
                    for selected,_ in selector.select(.05):
                        raw=os.read(selected.fd,65536)
                        if not raw:selector.unregister(selected.fileobj);continue
                        channel=selected.data
                        if len(buffers[channel])+len(raw)>MAX_STREAM:
                            self.observation['stream_budget_exceeded']=True;raise InputAdmissionError('document_tool_stream_budget')
                        buffers[channel].extend(raw)
            code=process.wait(timeout=max(.01,timeout-(time.monotonic()-started)))
            self.observation.update(terminal_observed=True,returncode=code)
            return code,bytes(buffers['stdout']),bytes(buffers['stderr'])
        finally:
            try:
                if process is not None:process_groups.stop(process,graceful=process.poll() is None)
            finally:
                if process is not None:process.stdout.close();process.stderr.close()
                self.observation.update({name:bytes(raw) for name,raw in buffers.items()})


def text(raw,encoding):return raw.decode(encoding).replace('\r\n','\n').replace('\r','\n')


class Tools(BoundedCapture,Capture):
    def __init__(self,record,output,scratch,*,cwd=None,environment=None,timeout=120):
        super().__init__(record);self.output=output;self.scratch=owned_directory(scratch,True)
        self.cwd=str(Path(cwd or Path.cwd()).absolute());ordinary_ancestors(self.cwd)
        self.environment=dict(os.environ if environment is None else environment)
        if any(type(k) is not str or type(v) is not str or '\0' in k or '\0' in v or '=' in k for k,v in self.environment.items()):raise InputAdmissionError('document_tool_environment_invalid')
        if type(timeout) not in (int,float) or not math.isfinite(timeout) or not 0<timeout<=600:raise InputAdmissionError('document_tool_timeout_invalid')
        self.timeout=timeout;self.identity=None;self.lookup_seen=False;self.lookup_value=None
        self.files={};self.process_factory=NativeProcess
    def checked_identity(self,label):
        try:value=program_identity(label,self.cwd)
        except OSError as error:raise InputAdmissionError('document_tool_identity_unavailable') from error
        from lib.document_rendering_io import program_value
        from lib.requirement_validation_replay import IntegrityError
        try:program_value(value,label)
        except IntegrityError as error:raise InputAdmissionError('document_tool_identity_invalid') from error
        if (Path(value['resolved']).is_relative_to(self.output.source_root)
                or Path(value['resolved']).is_relative_to(self.output.private_state)):
            raise InputAdmissionError('document_caller_or_private_program_forbidden')
        return value
    def which(self,name):
        self.output.gate.which(name)
        def effect():
            found=which_at(name,self.cwd,self.environment)
            identity=None if found is None else self.checked_identity(found)
            value={'path':found,'identity':identity,'context':{'cwd':self.cwd,'PATH':self.environment.get('PATH')}}
            if self.lookup_seen and value!=self.lookup_value:raise InputAdmissionError('document_tool_discovery_changed')
            self.lookup_seen=True;self.lookup_value=value;return value
        value=self.perform('document-tool-find',{'name':name},effect)
        self.identity=value['identity'];self.output.gate.found(value['path']);return value['path']
    def raw(self,reference):
        raw=read_private(self.record.blobs/reference['sha256'],MAX_BLOB)
        if len(raw)!=reference['bytes'] or hashlib.sha256(raw).hexdigest()!=reference['sha256']:raise InputAdmissionError('document_tool_blob_changed')
        return raw
    def source_snapshot(self,path):
        anchor=self.output.anchor(path);return anchor,anchor.snapshot(path)
    def run(self,arguments,**options):
        with ExitStack() as cleanup:return self.run_captured(arguments,options,cleanup)
    def run_captured(self,arguments,options,cleanup):
        gate=self.output.gate;gate.run(arguments,options)
        if self.checked_identity(arguments[0])!=self.identity:raise InputAdmissionError('document_tool_changed_before_run')
        original=list(arguments);mode=self.output.mode;temporary=None;process=self.process_factory()
        with io.TextIOWrapper(io.BytesIO()) as stream:encoding=stream.encoding
        frame={'original_arguments':original,'options':options,'export_mode':mode,'cwd':self.cwd,
            'SOURCE_DATE_EPOCH':self.environment.get('SOURCE_DATE_EPOCH'),'program':self.identity,
            'timeout_seconds':self.timeout,'stream_limit_bytes':MAX_STREAM,'encoding':encoding}
        anchor=None;logical_before=None
        if mode=='selected-files':
            anchor=self.output.anchor(gate.docx,write=True)
            before=anchor.snapshot(gate.docx);self.output.prior(gate.docx,before)
            inputs={name:anchor.snapshot(name) for name in (gate.md,gate.html)}
            for name,value in inputs.items():
                self.output.prior(name,value)
                if value.get('kind')!='file' or value['content']!=self.output.files[name]:raise InputAdmissionError('document_tool_input_changed')
            frame.update(anchor=anchor.frame,source_preimage=before,logical_before=None,inputs=inputs,workspace=None,effective_arguments=original)
            effective=original
        else:
            inputs={name:self.output.projected[name] for name in (gate.md,gate.html)}
            if gate.docx in self.output.projected:
                before=None;logical_before=self.output.projected[gate.docx]
            else:
                source_anchor,before=self.source_snapshot(gate.docx)
                logical_before={'kind':'file','content':before['content']} if before['kind']=='file' else {'kind':'directory'} if before['kind']=='directory' else {'kind':'missing'}
            temporary=tempfile.TemporaryDirectory(prefix='pandoc-',dir=self.scratch);cleanup.callback(temporary.cleanup);workspace=Path(temporary.name)
            for name in (gate.md,gate.html):
                target=workspace/Path(name).name;target.write_bytes(self.output.projected_raw[name])
            target=workspace/Path(gate.docx).name
            if logical_before['kind']=='file':target.write_bytes(self.raw(logical_before['content']))
            elif logical_before['kind']=='directory':target.mkdir()
            effective=[original[0],str(workspace/Path(gate.md).name),'-o',str(target)]
            frame.update(anchor=None,source_preimage=before,logical_before=logical_before,inputs=inputs,
                workspace=str(workspace),effective_arguments=effective)
        self.append({'kind':'document-tool-before',**frame})
        result=None
        def effect():
            code,stdout,stderr=process.run(effective,self.cwd,self.environment,self.timeout)
            return {'returncode':code,'stdout':text(stdout,encoding),'stderr':text(stderr,encoding)}
        try:
            result=self.perform('document-tool-run',{'arguments':original,'options':options,'export_mode':mode},effect)
            return SimpleNamespace(**result)
        finally:
            try:
                observed=dict(process.observation)
                for name in ('stdout','stderr'):observed[name]=self.blob(observed[name])
                if self.checked_identity(original[0])!=self.identity:raise InputAdmissionError('document_tool_changed_after_run')
                if mode=='selected-files':
                    after=anchor.snapshot(gate.docx)
                    for name,value in inputs.items():
                        if anchor.snapshot(name)!=value:raise InputAdmissionError('document_tool_modified_input')
                    self.output.observed[gate.docx]=after;self.output.touched[gate.docx]=after
                    self.output.versions[gate.docx]=self.output.versions.get(gate.docx,0)+1
                else:
                    from lib.providers.workbook_import_io import Anchor
                    capture=Anchor(self.record,Path(temporary.name));after=capture.snapshot(effective[3])
                    for name,value in inputs.items():
                        if (Path(temporary.name)/Path(name).name).read_bytes()!=self.output.projected_raw[name]:raise InputAdmissionError('document_tool_modified_private_input')
                if after['kind'] not in ('file','missing','directory'):raise InputAdmissionError('document_tool_output_unreachable')
                logical={'kind':'file','content':after['content']} if after['kind']=='file' else {'kind':after['kind']}
                self.output.projected[gate.docx]=logical
                if after['kind']=='file':self.output.projected_raw[gate.docx]=self.raw(after['content']);self.output.tool_files[gate.docx]=after['content']
                else:self.output.projected_raw.pop(gate.docx,None);self.output.tool_files.pop(gate.docx,None)
                self.append({'kind':'document-tool-after','output':gate.docx,'snapshot':after,'process':observed})
            except Exception:
                self.record.capture_incomplete=True;raise
            finally:
                if temporary is not None:temporary.cleanup()
