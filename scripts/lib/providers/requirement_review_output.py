"""Fixed owned report exports with durable preimages, intent and postimages."""
from contextlib import contextmanager
import errno
import os
from pathlib import Path
import stat

from lib.providers.operations_files import held_root
from lib.requirement_review_output import OUTPUTS, prefixes, text_bytes
from lib.requirement_validation_budget import InputAdmissionError
from lib.validation_files import MAX_FILE


class Output:
    def __init__(self, record, root, kind, mode):
        self.record,self.root,self.kind,self.mode=record,Path(root),kind,mode
        self.files={};self.touched={}
        self.identity=None
        if mode=='source-worktree':
            with held_root(self.root) as fd:
                value=os.fstat(fd);self.admit_directory(value)
                self.identity=(value.st_dev,value.st_ino,value.st_mode)

    @staticmethod
    def admit_directory(value):
        if (not stat.S_ISDIR(value.st_mode) or value.st_uid!=os.geteuid() or value.st_mode&0o7022):
            raise InputAdmissionError('requirement_review_owned_unshared_directory_required')

    @contextmanager
    def root_fd(self):
        with held_root(self.root) as fd:
            value=os.fstat(fd);self.admit_directory(value)
            if (value.st_dev,value.st_ino,value.st_mode)!=self.identity:
                raise InputAdmissionError('requirement_review_export_root_changed')
            yield fd

    @contextmanager
    def parent(self, fd, parts):
        if not parts:
            yield fd;return
        value=os.stat(parts[0],dir_fd=fd,follow_symlinks=False)
        if stat.S_ISLNK(value.st_mode):raise InputAdmissionError('requirement_review_export_alias_forbidden')
        if not stat.S_ISDIR(value.st_mode):raise NotADirectoryError(errno.ENOTDIR,'Not a directory',parts[0])
        self.admit_directory(value)
        child=os.open(parts[0],os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
        try:
            actual=os.fstat(child)
            if (value.st_dev,value.st_ino,value.st_mode)!=(actual.st_dev,actual.st_ino,actual.st_mode):
                raise InputAdmissionError('requirement_review_export_parent_changed')
            with self.parent(child,parts[1:]) as selected:yield selected
        finally:os.close(child)

    def blob(self,raw):
        try:return self.record.blob(raw)
        except Exception as error:
            self.record.capture_incomplete=True
            raise InputAdmissionError('requirement_review_private_capture_failed') from error

    def snapshot(self,name):
        parts=name.split('/')
        try:
            with self.root_fd() as root:
                with self.parent(root,parts[:-1]) as parent:
                    try:value=os.stat(parts[-1],dir_fd=parent,follow_symlinks=False)
                    except FileNotFoundError:return {'kind':'missing'}
                    if stat.S_ISLNK(value.st_mode):raise InputAdmissionError('requirement_review_export_alias_forbidden')
                    if value.st_uid!=os.geteuid() or value.st_mode&0o7022:
                        raise InputAdmissionError('requirement_review_owned_unshared_output_required')
                    result={'kind':'directory' if stat.S_ISDIR(value.st_mode) else 'file',
                            'mode':stat.S_IMODE(value.st_mode),'identity':[value.st_dev,value.st_ino]}
                    if stat.S_ISDIR(value.st_mode):return result
                    if not stat.S_ISREG(value.st_mode) or value.st_nlink!=1 or value.st_size>MAX_FILE:
                        raise InputAdmissionError('requirement_review_regular_bounded_output_required')
                    fd=os.open(parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
                    try:
                        before=os.fstat(fd)
                        if (before.st_dev,before.st_ino)!=(value.st_dev,value.st_ino):
                            raise InputAdmissionError('requirement_review_export_file_replaced')
                        chunks=[];total=0
                        while block:=os.read(fd,min(65536,MAX_FILE+1-total)):
                            chunks.append(block);total+=len(block)
                            if total>MAX_FILE:raise InputAdmissionError('requirement_review_output_preimage_budget')
                        after=os.fstat(fd);entry=os.stat(parts[-1],dir_fd=parent,follow_symlinks=False)
                        keys=('st_dev','st_ino','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
                        if any(getattr(before,k)!=getattr(row,k) for row in (after,entry) for k in keys):
                            raise InputAdmissionError('requirement_review_export_changed_during_capture')
                        result['content']=self.blob(b''.join(chunks));return result
                    finally:os.close(fd)
        except FileNotFoundError:return {'kind':'missing'}
        except NotADirectoryError:return {'kind':'unreachable','cause':'NotADirectoryError'}
        except OSError as error:
            raise InputAdmissionError('requirement_review_output_snapshot_unavailable') from error

    def mkdir(self,name,mode,parents,exist_ok):
        if (self.kind!='pra-platform' or name!='docs/governance/review-packets/PRA-2026-001'
                or (mode,parents,exist_ok)!=(0o777,True,True)):
            raise InputAdmissionError('requirement_review_fixed_mkdir_required')
        paths=prefixes(name)
        before=None if self.mode=='private-candidate' else {p:self.snapshot(p) for p in paths}
        self.record.append({'kind':'review-mkdir-before','name':name,'snapshots':before})
        created=[]
        def effect():
            if self.mode=='private-candidate':return None
            with self.root_fd() as root:
                current=os.dup(root)
                try:
                    for index,part in enumerate(name.split('/')):
                        last=index==len(paths)-1
                        try:
                            if last:
                                try:os.mkdir(part,mode,dir_fd=current);created.append(paths[index])
                                except FileExistsError:
                                    meta=os.stat(part,dir_fd=current,follow_symlinks=False)
                                    if stat.S_ISLNK(meta.st_mode):raise InputAdmissionError('requirement_review_export_alias_forbidden')
                                    if not stat.S_ISDIR(meta.st_mode):raise
                            else:
                                try:meta=os.stat(part,dir_fd=current,follow_symlinks=False)
                                except FileNotFoundError:
                                    os.mkdir(part,0o777,dir_fd=current);created.append(paths[index])
                                    meta=os.stat(part,dir_fd=current,follow_symlinks=False)
                                if stat.S_ISLNK(meta.st_mode):raise InputAdmissionError('requirement_review_export_alias_forbidden')
                            child=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=current)
                            try:self.admit_directory(os.fstat(child))
                            except Exception:os.close(child);raise
                        except OSError as error:
                            raise type(error)(error.errno,error.strerror,str(self.root/name)) from None
                        os.close(current);current=child
                finally:os.close(current)
        try:
            return self.record.perform('review-output-mkdir',{'name':name,'mode':mode,'parents':parents,'exist_ok':exist_ok,'export_mode':self.mode},effect)
        finally:
            try:
                after=None if self.mode=='private-candidate' else {p:self.snapshot(p) for p in paths}
                self.record.append({'kind':'review-mkdir-after','name':name,'snapshots':after,'created':created})
                for path in created:self.touched[path]=after[path]
            except Exception:
                self.record.capture_incomplete=True;raise

    def write_text(self,name,data,encoding):
        if name not in OUTPUTS[self.kind] or encoding!='utf-8':
            raise InputAdmissionError('requirement_review_fixed_utf8_output_required')
        text_ref=self.blob(text_bytes(data))
        try:raw=data.encode(encoding)
        except UnicodeEncodeError:raw=None
        payload=None if raw is None else self.blob(raw)
        before=None if self.mode=='private-candidate' else self.snapshot(name)
        self.record.append({'kind':'review-output-before','name':name,'text':text_ref,'payload':payload,'snapshot':before})
        progress={'opened':False,'truncated':False,'written_bytes':0}
        def effect():
            if self.mode=='private-candidate':
                if raw is None:data.encode(encoding)
                return len(data)
            parts=name.split('/')
            try:
                with self.root_fd() as root:
                    with self.parent(root,parts[:-1]) as parent:
                        flags=os.O_WRONLY|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK
                        if before['kind']=='missing':flags|=os.O_EXCL
                        try:fd=os.open(parts[-1],flags,0o666,dir_fd=parent)
                        except FileExistsError as error:
                            if before['kind']=='missing':raise InputAdmissionError('requirement_review_output_appeared_before_write') from error
                            raise
                        progress['opened']=True
                        try:
                            value=os.fstat(fd)
                            if not stat.S_ISREG(value.st_mode) or value.st_uid!=os.geteuid() or value.st_nlink!=1:
                                raise InputAdmissionError('requirement_review_owned_export_file_required')
                            if before['kind']=='file' and [value.st_dev,value.st_ino]!=before['identity']:
                                raise InputAdmissionError('requirement_review_output_replaced_before_write')
                            os.ftruncate(fd,0);progress['truncated']=True
                            if raw is None:data.encode(encoding)
                            view=memoryview(raw)
                            while view:
                                count=self.write_chunk(fd,view)
                                if count<=0:raise InputAdmissionError('requirement_review_unexpected_short_write')
                                progress['written_bytes']+=count;view=view[count:]
                        finally:os.close(fd)
            except OSError as error:
                if progress['opened'] or error.errno is None:raise
                raise type(error)(error.errno,error.strerror,str(self.root/name)) from None
            return len(data)
        ok=False
        try:
            value=self.record.perform('review-output-write',{'name':name,'text':text_ref,'payload':payload,'encoding':encoding,'export_mode':self.mode},effect)
            ok=True;self.files[name]=payload;return value
        finally:
            try:
                after=None if self.mode=='private-candidate' else self.snapshot(name)
                self.record.append({'kind':'review-output-after','name':name,'snapshot':after,'progress':progress})
                if self.mode=='source-worktree' and progress['opened']:self.touched[name]=after
                if ok and self.mode=='source-worktree' and (after['kind']!='file' or after['content']!=payload):
                    raise InputAdmissionError('requirement_review_export_changed_after_write')
            except Exception:
                self.record.capture_incomplete=True;raise

    def write_chunk(self,fd,view):
        return os.write(fd,view)
