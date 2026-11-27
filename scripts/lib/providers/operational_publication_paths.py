"""Owned selected append targets and exact publisher symlink observations."""
from pathlib import Path
from types import SimpleNamespace
import errno,os,stat
from lib.operational_publication_paths import probe_value,ReplayAppend
from lib.providers.workbook_import_io import ordinary_ancestors,failure_value,original_error
from lib.providers.operations_files import held_root
from lib.providers.validation_worktree import signature
from lib.requirement_validation_budget import InputAdmissionError
MAX_OUTPUT=8*1024**2

class NativePublisherPaths:
    def __init__(self,owner,*,source,outputs):self.owner,self.source,self.outputs=owner,Path(source),set(outputs);self.appends=[];self.cache={}
    def state(self,path):
        try:value=Path(path).lstat()
        except (FileNotFoundError,NotADirectoryError):return {'kind':'missing'}
        return {'kind':'symlink' if stat.S_ISLNK(value.st_mode) else 'file' if stat.S_ISREG(value.st_mode) else 'directory' if stat.S_ISDIR(value.st_mode) else 'other','identity':[value.st_dev,value.st_ino],'mode':stat.S_IMODE(value.st_mode),'uid':value.st_uid,'nlink':value.st_nlink,'bytes':value.st_size,'mtime_ns':value.st_mtime_ns,'ctime_ns':value.st_ctime_ns,'link':os.readlink(path) if stat.S_ISLNK(value.st_mode) else None}
    def is_symlink(self,path,label):
        if not Path(path).is_relative_to(self.source):raise InputAdmissionError('publisher_probe_outside_selected_source')
        spec={'path':path,'label':label}
        def effect():
            before=self.state(path);result=error=None
            try:result=Path(path).is_symlink()
            except OSError as caught:error=failure_value(original_error(caught,label))
            after=self.state(path)
            if before!=after:raise InputAdmissionError('publisher_probe_changed')
            return {'specification':spec,'before':before,'after':after,'result':result,'error':error}
        return probe_value(self.owner.perform('publisher-symlink-probe',spec,effect),spec)
    def append(self,path,label):
        if path not in self.outputs or Path(path).is_relative_to(self.source) or Path(path).is_relative_to(self.owner.private_state) or getattr(self.owner,'product_root',None) is not None and Path(path).is_relative_to(self.owner.product_root):raise InputAdmissionError('publisher_owned_external_output_selection_required')
        return NativeAppend(self,path,label)
    def observe(self,path):
        p=Path(path)
        try:ordinary_ancestors(p.parent)
        except FileNotFoundError:return {'kind':'missing'}
        except NotADirectoryError:return {'kind':'unreachable','cause':'NotADirectoryError'}
        with held_root(p.parent) as parent:
            try:value=os.stat(p.name,dir_fd=parent,follow_symlinks=False)
            except FileNotFoundError:return {'kind':'missing'}
            if stat.S_ISDIR(value.st_mode):return {'kind':'directory','identity':[value.st_dev,value.st_ino],'mode':stat.S_IMODE(value.st_mode)}
            if not stat.S_ISREG(value.st_mode) or value.st_nlink!=1 or value.st_uid!=os.geteuid() or value.st_mode&0o7022 or value.st_size>MAX_OUTPUT:raise InputAdmissionError('publisher_owned_bounded_append_file_required')
            fd=os.open(p.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
            try:
                if signature(os.fstat(fd))!=signature(value):raise InputAdmissionError('publisher_append_preimage_replaced')
                raw=b''
                while part:=os.read(fd,min(65536,MAX_OUTPUT+1-len(raw))):
                    raw+=part
                    if len(raw)>MAX_OUTPUT:raise InputAdmissionError('publisher_append_byte_budget')
                if signature(value)!=signature(os.fstat(fd)) or signature(value)!=signature(os.stat(p.name,dir_fd=parent,follow_symlinks=False)):raise InputAdmissionError('publisher_append_preimage_changed')
            finally:os.close(fd)
            ref=self.owner.blob(raw);self.cache[ref['sha256']]=raw
            return {'kind':'file','identity':[value.st_dev,value.st_ino],'mode':stat.S_IMODE(value.st_mode),'content':ref}

class NativeAppend:
    def __init__(self,paths,path,label):
        self.paths,self.owner,self.path,self.label=paths,paths.owner,path,label;self.stream=None
        self.decoder=ReplayAppend(SimpleNamespace(owner=SimpleNamespace(blob=lambda ref:paths.cache[ref['sha256']]),appends=paths.appends),path,label)
    def operation(self,kind,text=None):
        args={'path':self.path,'label':self.label,'encoding':'utf-8','mode':'a','text':text}
        def effect():
            before=self.paths.observe(self.path);error=result=None
            try:
                if kind=='open':
                    ordinary_ancestors(Path(self.path).parent)
                    fd=os.open(self.path,os.O_WRONLY|os.O_APPEND|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,0o666)
                    try:self.stream=os.fdopen(fd,'a',encoding='utf-8')
                    except BaseException:os.close(fd);raise
                elif kind=='write':result=self.stream.write(text)
                elif kind=='close':self.stream.close()
                else:raise InputAdmissionError('publisher_append_operation_required')
            except OSError as caught:error=failure_value(original_error(caught,self.label) if kind=='open' else caught)
            except UnicodeEncodeError as caught:error={'type':'UnicodeEncodeError','message':str(caught),'encoding':caught.encoding,'object':caught.object,'start':caught.start,'end':caught.end,'reason':caught.reason}
            after=self.paths.observe(self.path)
            return {'specification':args,'before':before,'after':after,'return_value':result,'error':error}
        wire=self.owner.perform('publisher-append-'+kind,args,effect)
        return self.decoder.decode(kind,args,wire,text)
    def __enter__(self):self.operation('open');return self
    def write(self,text):return self.operation('write',text)
    def __exit__(self,*args):
        try:self.operation('close')
        finally:
            if self.stream is not None and not self.stream.closed:self.stream.close()
        return False
