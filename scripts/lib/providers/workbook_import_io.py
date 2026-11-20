"""Selected lazy workbook reads and exact ordered owned report file effects."""
from contextlib import contextmanager
import errno
import os
from pathlib import Path,PurePosixPath
import stat

from lib.providers.operations_files import held_root
from lib.providers.validation_worktree import signature
from lib.repository_capture import private_name
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_review_output import text_bytes
from lib.workbook_import_io import path_spec,selection_value,ancestor_paths,MODES
from lib.validation_files import MAX_FILE,MAX_TOTAL


class Capture:
    def __init__(self,record):self.record=record
    def failed(self,error):
        self.record.capture_incomplete=True
        raise InputAdmissionError('workbook_private_capture_failed') from error
    def blob(self,raw):
        try:return self.record.blob(raw)
        except Exception as error:self.failed(error)
    def append(self,value):
        try:return self.record.append(value)
        except Exception as error:self.failed(error)
    def perform(self,action,arguments,effect,*,encoding='json'):
        native=[]
        def operation():
            try:return effect()
            except Exception as error:native.append(error);raise
        try:return self.record.perform(action,arguments,operation,encoding=encoding)
        except Exception as error:
            if native and native[0] is error:
                if isinstance(error,InputAdmissionError):self.record.capture_incomplete=True
                raise
            self.failed(error)


def admitted(spec):
    try:path_spec(spec)
    except ValueError as error:raise InputAdmissionError(str(error)) from error
    if private_name(spec['path']):raise InputAdmissionError('workbook_private_path_not_admitted')


def ordinary_ancestors(path):
    current=Path('/')
    for part in Path(path).parts[1:]:
        current/=part
        value=os.stat(current,follow_symlinks=False)
        if stat.S_ISLNK(value.st_mode):raise InputAdmissionError('workbook_path_alias_forbidden')
        if not stat.S_ISDIR(value.st_mode):raise NotADirectoryError(errno.ENOTDIR,os.strerror(errno.ENOTDIR),str(current))


def original_error(error,label):
    if error.errno is None:return error
    return type(error)(error.errno,error.strerror,label)


def failure_value(error):
    return {'type':type(error).__name__,'message':str(error),'errno':error.errno,
            'strerror':error.strerror,'filename':error.filename}


class Data(Capture):
    def __init__(self,record):
        super().__init__(record);self.selected=None;self.observed={};self.total=0
    def select(self,value):self.selected=value['inputs']
    def read(self,path,label):
        spec={'path':path,'label':label};admitted(spec)
        if self.selected is None or spec not in self.selected:raise InputAdmissionError('workbook_input_not_selected')
        info=None;failure=None
        def effect():
            nonlocal info
            selected=Path(path)
            try:
                ordinary_ancestors(selected.parent)
                with held_root(selected.parent) as parent:
                    entry=os.stat(selected.name,dir_fd=parent,follow_symlinks=False)
                    if stat.S_ISDIR(entry.st_mode):raise IsADirectoryError(errno.EISDIR,os.strerror(errno.EISDIR),label)
                    if (not stat.S_ISREG(entry.st_mode) or entry.st_uid!=os.geteuid() or entry.st_nlink!=1
                            or entry.st_mode&0o7022 or entry.st_size>MAX_FILE):
                        raise InputAdmissionError('workbook_owned_regular_bounded_input_required')
                    fd=os.open(selected.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
                    try:
                        before=os.fstat(fd)
                        if signature(before)!=signature(entry):raise InputAdmissionError('workbook_input_replaced_before_read')
                        blocks=[];total=0
                        while block:=os.read(fd,min(65536,MAX_FILE+1-total)):
                            blocks.append(block);total+=len(block)
                            if total>MAX_FILE:raise InputAdmissionError('workbook_input_byte_budget')
                        after=os.fstat(fd);entry=os.stat(selected.name,dir_fd=parent,follow_symlinks=False)
                        if signature(before)!=signature(after) or signature(before)!=signature(entry):raise InputAdmissionError('workbook_input_changed_during_read')
                        raw=b''.join(blocks)
                        observed={'kind':'file','mode':stat.S_IMODE(before.st_mode),'identity':[before.st_dev,before.st_ino],'bytes':len(raw)}
                    finally:os.close(fd)
            except OSError as error:raise original_error(error,label) from None
            self.total+=len(raw)
            if self.total>MAX_TOTAL:raise InputAdmissionError('workbook_input_total_budget')
            if path in self.observed and self.observed[path]!=(raw,observed):raise InputAdmissionError('workbook_input_changed_between_reads')
            self.observed[path]=(raw,observed);info=observed;return raw
        try:return self.perform('workbook-input-read',spec,effect,encoding='bytes')
        except OSError as error:
            failure=failure_value(error)
            if path in self.observed:
                self.record.capture_incomplete=True
                raise InputAdmissionError('workbook_repeated_input_became_unavailable') from error
            raise
        finally:self.append({'kind':'workbook-input-after','selection':spec,'observation':info,'failure':failure})


class Anchor(Capture):
    def __init__(self,record,root):
        super().__init__(record);self.root=Path(root)
        try:
            ordinary_ancestors(self.root)
            with held_root(self.root) as fd:
                value=os.fstat(fd);self.admit(value);self.identity=(value.st_dev,value.st_ino,value.st_mode,value.st_uid)
                self.frame={'path':str(self.root),'snapshot':{'kind':'directory','mode':stat.S_IMODE(value.st_mode),'identity':[value.st_dev,value.st_ino]}}
        except OSError as error:raise InputAdmissionError('workbook_export_anchor_unavailable') from error
    @staticmethod
    def admit(value):
        if not stat.S_ISDIR(value.st_mode) or value.st_uid!=os.geteuid() or value.st_mode&0o7022:
            raise InputAdmissionError('workbook_owned_unshared_directory_required')
    @contextmanager
    def root_fd(self):
        with held_root(self.root) as fd:
            value=os.fstat(fd);self.admit(value)
            if (value.st_dev,value.st_ino,value.st_mode,value.st_uid)!=self.identity:raise InputAdmissionError('workbook_export_anchor_changed')
            yield fd
    @contextmanager
    def parent(self,fd,parts):
        if not parts:yield fd;return
        value=os.stat(parts[0],dir_fd=fd,follow_symlinks=False)
        if stat.S_ISLNK(value.st_mode):raise InputAdmissionError('workbook_export_alias_forbidden')
        if not stat.S_ISDIR(value.st_mode):raise NotADirectoryError(errno.ENOTDIR,os.strerror(errno.ENOTDIR),parts[0])
        self.admit(value);child=os.open(parts[0],os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
        try:
            actual=os.fstat(child)
            if (value.st_dev,value.st_ino,value.st_mode,value.st_uid)!=(actual.st_dev,actual.st_ino,actual.st_mode,actual.st_uid):raise InputAdmissionError('workbook_export_parent_changed')
            with self.parent(child,parts[1:]) as selected:yield selected
        finally:os.close(child)
    def parts(self,path):
        return PurePosixPath(path).relative_to(PurePosixPath(str(self.root))).parts
    def snapshot(self,path):
        parts=self.parts(path)
        try:
            with self.root_fd() as root:
                with self.parent(root,parts[:-1]) as parent:
                    try:value=os.stat(parts[-1],dir_fd=parent,follow_symlinks=False)
                    except FileNotFoundError:return {'kind':'missing'}
                    if value.st_uid!=os.geteuid() or value.st_mode&0o7022 or stat.S_ISLNK(value.st_mode):raise InputAdmissionError('workbook_owned_unshared_output_required')
                    result={'kind':'directory' if stat.S_ISDIR(value.st_mode) else 'file','mode':stat.S_IMODE(value.st_mode),'identity':[value.st_dev,value.st_ino]}
                    if stat.S_ISDIR(value.st_mode):return result
                    if not stat.S_ISREG(value.st_mode) or value.st_nlink!=1 or value.st_size>MAX_FILE:raise InputAdmissionError('workbook_regular_bounded_output_required')
                    fd=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
                    try:
                        before=os.fstat(fd)
                        if signature(before)!=signature(value):raise InputAdmissionError('workbook_export_replaced_before_capture')
                        chunks=[];total=0
                        while block:=os.read(fd,min(65536,MAX_FILE+1-total)):
                            chunks.append(block);total+=len(block)
                            if total>MAX_FILE:raise InputAdmissionError('workbook_output_preimage_budget')
                        after=os.fstat(fd);entry=os.stat(parts[-1],dir_fd=parent,follow_symlinks=False)
                        if signature(before)!=signature(after) or signature(before)!=signature(entry):raise InputAdmissionError('workbook_export_changed_during_capture')
                        result['content']=self.blob(b''.join(chunks));return result
                    finally:os.close(fd)
        except FileNotFoundError:return {'kind':'missing'}
        except NotADirectoryError:return {'kind':'unreachable','cause':'NotADirectoryError'}
        except OSError as error:raise InputAdmissionError('workbook_output_snapshot_unavailable') from error


class Output(Capture):
    def __init__(self,record,mode):
        super().__init__(record)
        if mode not in MODES:raise InputAdmissionError('workbook_export_mode_required')
        self.mode=mode;self.selected=None;self.mkdir_position=self.write_position=0
        self.files={};self.writes=[];self.touched={};self.observed={};self.anchors={}
    def select(self,value):self.selected=value['outputs']
    def expected(self,kind,path,label):
        if self.selected is None:raise InputAdmissionError('workbook_output_selection_required')
        admitted({'path':path,'label':label})
        if kind=='mkdir':
            if self.mkdir_position>=3 or self.write_position:raise InputAdmissionError('workbook_mkdir_order_changed')
            selected=self.selected[self.mkdir_position];self.mkdir_position+=1
            expected={'path':str(PurePosixPath(selected['path']).parent),'label':str(PurePosixPath(selected['label']).parent)}
        else:
            if self.mkdir_position!=3 or self.write_position>=3:raise InputAdmissionError('workbook_write_order_changed')
            expected=self.selected[self.write_position];self.write_position+=1
        if expected!={'path':path,'label':label}:raise InputAdmissionError('workbook_output_not_selected')
    def anchor(self,path,write=False):
        current=Path(path).parent
        for _ in range(101):
            try:value=current.lstat()
            except (FileNotFoundError,NotADirectoryError):pass
            except OSError as error:raise InputAdmissionError('workbook_export_anchor_unavailable') from error
            else:
                if stat.S_ISLNK(value.st_mode):raise InputAdmissionError('workbook_export_anchor_alias_forbidden')
                if stat.S_ISDIR(value.st_mode):break
            if current.parent==current:raise InputAdmissionError('workbook_export_anchor_missing')
            current=current.parent
        else:raise InputAdmissionError('workbook_export_anchor_depth_budget')
        if write and current!=Path(path).parent:raise InputAdmissionError('workbook_write_parent_missing_or_changed')
        anchor=Anchor(self.record,current);frame=anchor.frame
        if frame['path'] in self.anchors and self.anchors[frame['path']]!=frame['snapshot']:raise InputAdmissionError('workbook_export_anchor_replaced')
        if frame['path'] in self.observed and self.observed[frame['path']]!=frame['snapshot']:raise InputAdmissionError('workbook_observed_anchor_replaced')
        self.anchors[frame['path']]=frame['snapshot'];return anchor
    def prior(self,path,value):
        if path in self.observed and self.observed[path]!=value:raise InputAdmissionError('workbook_output_changed_between_operations')
    def mkdir(self,path,mode,parents,exist_ok,label):
        self.expected('mkdir',path,label)
        if (mode,parents,exist_ok)!=(0o777,True,True):raise InputAdmissionError('workbook_original_mkdir_required')
        anchor=None if self.mode=='private-candidate' else self.anchor(path)
        paths=[] if anchor is None else ancestor_paths(str(anchor.root),path)
        before=None if anchor is None else {name:anchor.snapshot(name) for name in paths}
        if before is not None:
            for name,value in before.items():self.prior(name,value)
        self.append({'kind':'workbook-mkdir-before','path':path,'label':label,'anchor':None if anchor is None else anchor.frame,'snapshots':before})
        created=[]
        def effect():
            if anchor is None:return None
            with anchor.root_fd() as root:
                current=os.dup(root)
                try:
                    parts=anchor.parts(path)
                    for index,part in enumerate(parts):
                        try:
                            if index==len(parts)-1:
                                try:os.mkdir(part,mode,dir_fd=current);created.append(paths[index])
                                except FileExistsError:
                                    value=os.stat(part,dir_fd=current,follow_symlinks=False)
                                    if stat.S_ISLNK(value.st_mode):raise InputAdmissionError('workbook_export_alias_forbidden')
                                    if not stat.S_ISDIR(value.st_mode):raise
                            else:
                                try:value=os.stat(part,dir_fd=current,follow_symlinks=False)
                                except FileNotFoundError:
                                    os.mkdir(part,0o777,dir_fd=current);created.append(paths[index]);value=os.stat(part,dir_fd=current,follow_symlinks=False)
                                if stat.S_ISLNK(value.st_mode):raise InputAdmissionError('workbook_export_alias_forbidden')
                            child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=current)
                            try:anchor.admit(os.fstat(child))
                            except Exception:os.close(child);raise
                        except OSError as error:raise original_error(error,label) from None
                        os.close(current);current=child
                finally:os.close(current)
        try:return self.perform('workbook-output-mkdir',{'path':path,'label':label,'mode':mode,'parents':parents,'exist_ok':exist_ok,'export_mode':self.mode},effect)
        finally:
            try:
                after=None if anchor is None else {name:anchor.snapshot(name) for name in paths}
                self.append({'kind':'workbook-mkdir-after','path':path,'label':label,'snapshots':after,'created':created})
                if after is not None:self.observed.update(after)
                for name in created:self.touched[name]=after[name]
            except Exception:
                self.record.capture_incomplete=True;raise
    def write_text(self,path,data,encoding,label):
        self.expected('write',path,label)
        if encoding!='utf-8':raise InputAdmissionError('workbook_original_utf8_required')
        text_ref=self.blob(text_bytes(data))
        try:raw=data.encode(encoding)
        except UnicodeEncodeError:raw=None
        payload=None if raw is None else self.blob(raw)
        anchor=None if self.mode=='private-candidate' else self.anchor(path,write=True)
        before=None if anchor is None else anchor.snapshot(path)
        if before is not None:self.prior(path,before)
        self.append({'kind':'workbook-write-before','path':path,'label':label,'anchor':None if anchor is None else anchor.frame,'snapshot':before,'text':text_ref,'payload':payload})
        progress={'opened':False,'truncated':False,'written_bytes':0}
        def effect():
            if anchor is None:
                if raw is None:data.encode(encoding)
                return len(data)
            parts=anchor.parts(path)
            try:
                with anchor.root_fd() as root:
                    with anchor.parent(root,parts[:-1]) as parent:
                        flags=os.O_WRONLY|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK
                        if before['kind']=='missing':flags|=os.O_EXCL
                        try:fd=os.open(parts[-1],flags,0o666,dir_fd=parent)
                        except FileExistsError as error:
                            if before['kind']=='missing':raise InputAdmissionError('workbook_output_appeared_before_write') from error
                            raise
                        progress['opened']=True
                        try:
                            value=os.fstat(fd)
                            if not stat.S_ISREG(value.st_mode) or value.st_uid!=os.geteuid() or value.st_nlink!=1:raise InputAdmissionError('workbook_owned_export_file_required')
                            if before['kind']=='file' and ([value.st_dev,value.st_ino]!=before['identity'] or stat.S_IMODE(value.st_mode)!=before['mode']):raise InputAdmissionError('workbook_output_replaced_before_write')
                            os.ftruncate(fd,0);progress['truncated']=True
                            if raw is None:data.encode(encoding)
                            view=memoryview(raw)
                            while view:
                                count=self.write_chunk(fd,view)
                                if count<=0:raise InputAdmissionError('workbook_unexpected_short_write')
                                progress['written_bytes']+=count;view=view[count:]
                        finally:os.close(fd)
            except OSError as error:
                if progress['opened']:raise
                raise original_error(error,label) from None
            return len(data)
        ok=False
        try:
            result=self.perform('workbook-output-write',{'path':path,'label':label,'text':text_ref,'payload':payload,'encoding':encoding,'export_mode':self.mode},effect)
            ok=True;self.files[path]=payload;self.writes.append({'path':path,'label':label,'payload':payload});return result
        finally:
            try:
                after=None if anchor is None else anchor.snapshot(path)
                self.append({'kind':'workbook-write-after','path':path,'label':label,'snapshot':after,'progress':progress})
                if after is not None:self.observed[path]=after
                if anchor is not None and progress['opened']:self.touched[path]=after
                if ok and anchor is not None and (after['kind']!='file' or after['content']!=payload):raise InputAdmissionError('workbook_export_changed_after_write')
            except Exception:
                self.record.capture_incomplete=True;raise
    def write_chunk(self,fd,view):return os.write(fd,view)


class Selection(Capture):
    def __init__(self,record,cwd,data,output,private_state,product_root=None):
        super().__init__(record);self.cwd,self.data,self.output,self.private_state=cwd,data,output,Path(private_state);self.value=None
        self.product_root=None if product_root is None else Path(product_root)
    def __call__(self,value):
        try:selection_value(value,self.cwd)
        except ValueError as error:raise InputAdmissionError(str(error)) from error
        if self.value is not None:raise InputAdmissionError('workbook_selection_repeated')
        for item in value['inputs']+value['outputs']:
            admitted(item)
            if Path(item['path']).is_relative_to(self.private_state):raise InputAdmissionError('workbook_source_private_state_overlap')
        if self.output.mode=='selected-files' and self.product_root is not None:
            if any(Path(item['path']).is_relative_to(self.product_root) for item in value['outputs']):
                raise InputAdmissionError('workbook_installed_product_export_forbidden')
        self.append({'kind':'workbook-selected','selection':value});self.value=value
        self.data.select(value);self.output.select(value)
