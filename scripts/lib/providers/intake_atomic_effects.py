"""Held private POSIX scope for original atomic JSON native-effect capture."""
import errno
import os
from pathlib import Path
import stat
import tempfile

from lib.intake_atomic_effects import (AtomicPorts,AtomicState,MAX_FILE,MAX_DESCRIPTORS,
    error_value,original_error)
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from lib.providers.operations_files import held_root


def signature(value):
    return tuple(getattr(value,k) for k in ('st_dev','st_ino','st_mode','st_uid','st_gid','st_nlink','st_size','st_mtime_ns','st_ctime_ns'))


def information(value,kind):
    return {'kind':kind,'mode':stat.S_IMODE(value.st_mode),'identity':[value.st_dev,value.st_ino],
        'stat':{'uid':value.st_uid,'gid':value.st_gid,'links':value.st_nlink,'bytes':value.st_size,
                'mtime_ns':value.st_mtime_ns,'ctime_ns':value.st_ctime_ns}}


class NativeAtomicEffects(AtomicPorts):
    def __init__(self,scope,record,*,forbidden_roots):
        if not forbidden_roots:raise InputAdmissionError('intake_atomic_explicit_product_exclusions_required')
        root=Path(scope.root)
        for value in (*forbidden_roots,record.root):
            other=Path(value).absolute()
            if root.is_relative_to(other) or other.is_relative_to(root):raise InputAdmissionError('intake_atomic_protected_root_overlap')
        if os.name!='posix':raise InputAdmissionError('intake_atomic_posix_profile_required')
        self.scope,self.record=scope,record;self.descriptors={};self.temps=set();self.cache={};self.sequence=0;self.closed=False
        self.anchor=held_root(root);opened=False
        try:
            self.fd=self.anchor.__enter__();opened=True;self.root_info=os.fstat(self.fd)
            if stat.S_IMODE(self.root_info.st_mode)!=0o700:raise InputAdmissionError('intake_atomic_writable_private_root_required')
            self.owned(self.root_info,directory=True)
            self.state=AtomicState(scope,self.retained_blob)
            self.snapshot()
        except BaseException as error:
            self.record.capture_incomplete=True
            try:
                if opened:self.anchor.__exit__(None,None,None)
            finally:self.closed=True
            if isinstance(error,OSError):raise InputAdmissionError('intake_atomic_initial_observation_failed') from None
            raise
    def retained_blob(self,ref):
        from lib.providers.sbom_export_storage import read_private
        return read_private(self.record.blobs/ref['sha256'],MAX_FILE)
    def owned(self,value,*,directory=False):
        valid=stat.S_ISDIR(value.st_mode) if directory else stat.S_ISREG(value.st_mode) and value.st_nlink==1
        if not valid or value.st_uid!=os.geteuid() or stat.S_IMODE(value.st_mode)&0o077:
            raise InputAdmissionError('intake_atomic_owned_private_ordinary_paths_required')
    def root_current(self):
        current=os.fstat(self.fd);self.owned(current,directory=True)
        if any(getattr(current,k)!=getattr(self.root_info,k) for k in ('st_dev','st_ino','st_mode','st_uid','st_gid')):
            raise InputAdmissionError('intake_atomic_root_binding_changed')
        return current
    def descriptor_open(self,row):
        # A closed stream no longer owns its old integer. A later temporary
        # file or journal write may legitimately reuse that producer fd.
        if row.get('stream') is not None and row['stream'].closed:return False
        try:value=os.fstat(row['fd'])
        except OSError as error:
            if error.errno==errno.EBADF:return False
            raise
        if ([value.st_dev,value.st_ino]!=row['identity'] or not stat.S_ISREG(value.st_mode)
                or value.st_uid!=os.geteuid() or stat.S_IMODE(value.st_mode)&0o077 or value.st_nlink not in (0,1)):
            raise InputAdmissionError('intake_atomic_descriptor_identity_changed')
        return True
    def file(self,name):
        try:before=os.stat(name,dir_fd=self.fd,follow_symlinks=False)
        except FileNotFoundError:self.cache.pop(name,None);return {'kind':'missing'}
        if stat.S_ISDIR(before.st_mode):
            self.owned(before,directory=True);part=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=self.fd)
            try:
                if signature(os.fstat(part))!=signature(before):raise InputAdmissionError('intake_atomic_directory_replaced')
                result=information(before,'directory');result['members']=sorted(os.listdir(part))
                if signature(os.fstat(part))!=signature(before):raise InputAdmissionError('intake_atomic_directory_changed')
                return result
            finally:os.close(part)
        self.owned(before)
        if before.st_size>MAX_FILE:raise InputAdmissionError('intake_atomic_file_byte_budget')
        key=signature(before)
        if name in self.cache and self.cache[name][0]==key:return self.cache[name][1]
        held=next((row['fd'] for row in self.descriptors.values() if row['name']==name and self.descriptor_open(row)),None)
        fd=held if held is not None else os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=self.fd)
        try:
            if signature(os.fstat(fd))!=key:raise InputAdmissionError('intake_atomic_file_replaced')
            parts=[];offset=0
            while True:
                raw=os.pread(fd,min(65536,MAX_FILE+1-offset),offset)
                if not raw:break
                parts.append(raw);offset+=len(raw)
                if offset>MAX_FILE:raise InputAdmissionError('intake_atomic_file_byte_budget')
            if signature(os.fstat(fd))!=key or signature(os.stat(name,dir_fd=self.fd,follow_symlinks=False))!=key:
                raise InputAdmissionError('intake_atomic_file_changed')
            result=information(before,'file');result['content']=self.record.blob(b''.join(parts));self.cache[name]=(key,result);return result
        finally:
            if held is None:os.close(fd)
    def snapshot(self):
        before=self.root_current();members=sorted(os.listdir(self.fd));names=set(self.scope.targets)|self.temps
        if not set(members)<=names:raise InputAdmissionError('intake_atomic_unselected_output_member')
        files={name:self.file(name) for name in sorted(names)};descriptors={}
        for token,row in self.descriptors.items():
            opened=self.descriptor_open(row);handle=row.get('stream');stream=None if handle is None else {'encoding':handle.encoding,'errors':handle.errors,'closed':handle.closed}
            descriptors[str(token)]={'name':row['name'],'open':opened,'stream':stream}
        after=self.root_current()
        if signature(after)!=signature(before) or sorted(os.listdir(self.fd))!=members:raise InputAdmissionError('intake_atomic_snapshot_root_changed')
        root=information(before,'directory');root['members']=members
        return {'root':root,'files':files,'descriptors':descriptors}
    def invoke(self,operation,args,effect):
        """Trusted native primitive boundary; no caller-supplied program is loaded."""
        return effect()
    def call(self,operation,args):
        if self.closed or self.record.capture_incomplete:raise InputAdmissionError('intake_atomic_capture_already_incomplete')
        try:before=self.snapshot();self.state.begin(operation,args,before)
        except BaseException as error:
            self.record.capture_incomplete=True
            if isinstance(error,OSError):raise InputAdmissionError('intake_atomic_before_observation_failed') from None
            raise
        intent={'kind':'intake-atomic-intent','sequence':self.sequence,'operation':operation,'arguments':args,'before':before}
        try:self.record.append(intent)
        except BaseException:self.record.capture_incomplete=True;raise
        result=error=None
        try:
            try:result=self.invoke(operation,args,lambda:self.native(operation,args))
            except OSError as caught:error=error_value(caught)
            after=self.snapshot();self.state.finish(operation,args,before,after,result,error)
            self.record.append({'kind':'intake-atomic-outcome','sequence':self.sequence,'result':result,'error':error,'after':after});self.sequence+=1
        except BaseException as caught:
            self.record.capture_incomplete=True
            if isinstance(caught,OSError):raise InputAdmissionError('intake_atomic_after_observation_or_journal_failed') from None
            raise
        if error is not None:raise original_error(error)
        return result
    def relabel(self,error,*labels):
        first=labels[0] if labels and error.filename is not None else error.filename
        second=labels[1] if len(labels)>1 and error.filename2 is not None else error.filename2
        cls=type(error)
        return cls(error.errno,error.strerror,first,None,second) if second is not None else cls(error.errno,error.strerror,first)
    def native(self,operation,args):
        if operation=='mkdir':
            try:return os.mkdir('.',args['mode'],dir_fd=self.fd)
            except FileExistsError:
                self.root_current();return None
            except OSError as error:raise self.relabel(error,args['path']) from None
        if operation=='mkstemp':
            if len(self.descriptors)>=MAX_DESCRIPTORS:raise InputAdmissionError('intake_atomic_descriptor_budget')
            for unused in range(256):
                name='tmp'+next(tempfile._get_candidate_names())
                if name in self.temps:continue
                try:fd=os.open(name,os.O_RDWR|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=self.fd)
                except FileExistsError:continue
                except OSError as error:raise self.relabel(error,self.scope.root+'/'+name) from None
                try:
                    value=os.fstat(fd);self.owned(value);token=len(self.descriptors)+1
                    self.descriptors[token]={'fd':fd,'name':name,'identity':[value.st_dev,value.st_ino]};self.temps.add(name)
                    return {'descriptor':token,'temporary':self.scope.root+'/'+name}
                except BaseException:os.close(fd);raise
            raise InputAdmissionError('intake_atomic_temporary_name_capture_budget')
        if operation in ('fdopen','enter','write','flush','fileno','fsync','close'):
            row=self.descriptors[args['descriptor']]
            if operation=='fdopen':
                stream=os.fdopen(row['fd'],'w');row['stream']=stream
                return {'encoding':stream.encoding,'errors':stream.errors}
            stream=row['stream']
            if operation=='enter':stream.__enter__();return None
            if operation=='write':return stream.write(args['text'])
            if operation=='flush':return stream.flush()
            if operation=='fileno':
                if stream.fileno()!=row['fd']:raise InputAdmissionError('intake_atomic_stream_descriptor_changed')
                return args['descriptor']
            if operation=='fsync':return os.fsync(row['fd'])
            return stream.close()
        if operation=='chmod':
            name=self.scope.name(args['path'])
            try:return os.chmod(name,args['mode'],dir_fd=self.fd,follow_symlinks=False)
            except OSError as error:raise self.relabel(error,args['path']) from None
        if operation=='replace':
            source,target=self.scope.name(args['source']),self.scope.name(args['target'])
            try:return os.replace(source,target,src_dir_fd=self.fd,dst_dir_fd=self.fd)
            except OSError as error:raise self.relabel(error,args['source'],args['target']) from None
        name=self.scope.name(args['path'])
        try:return os.unlink(name,dir_fd=self.fd)
        except FileNotFoundError:
            if args['missing_ok']:return None
            raise
        except OSError as error:raise self.relabel(error,args['path']) from None
    def release_resources(self):
        remaining=[];errors=[]
        if self.closed:return {'required':False,'unclosed_descriptors':[],'errors':[]}
        try:
            for token,row in self.descriptors.items():
                try:
                    if not self.descriptor_open(row):continue
                    remaining.append(token)
                    if row.get('stream') is not None:row['stream'].close()
                    else:os.close(row['fd'])
                except Exception as error:errors.append(type(error).__name__)
        finally:
            if remaining or errors:self.record.capture_incomplete=True
            self.anchor.__exit__(None,None,None);self.closed=True
        return {'required':bool(remaining or errors),'unclosed_descriptors':remaining,'errors':errors}
    def __enter__(self):return self
    def __exit__(self,kind,error,tb):self.release_resources()
