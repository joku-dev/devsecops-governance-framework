"""Owned auxiliary Git metadata lifecycle; no source program or Git execution.

Only captured index bytes and pure conversion-plan files enter this directory.
The coordinator must independently capture/recheck the selected source context.
Journal loss or namespace drift quarantines the directory; it is never retried or
removed by a destructor. Closing file descriptors does not remove evidence.
"""
import os,secrets,stat
from pathlib import Path
from lib.accepted_prefix_git_context import FrozenHashArguments
from lib.accepted_prefix_hash_scope import planned_files,specification,creation_value,removal_value
from lib.providers.sbom_export_storage import owned_directory
from lib.providers.workbook_import_io import ordinary_ancestors
from lib.requirement_validation_budget import InputAdmissionError


def fail(reason):raise InputAdmissionError('accepted_prefix_auxiliary_'+reason)
def identity(value):return [value.st_dev,value.st_ino]
def owned(value,kind):
    if value.st_uid!=os.geteuid() or value.st_mode&0o7022:fail('owned_unshared_entry_required')
    if kind=='directory' and not stat.S_ISDIR(value.st_mode):fail('directory_required')
    if kind=='file' and (not stat.S_ISREG(value.st_mode) or value.st_nlink!=1):fail('regular_file_required')

class NativeHashAuxiliary:
    def __init__(self,owner,root,path,attributes,configuration,*,index,shared,objects,filter_required=None):
        self.owner=owner;self.fd=self.parent_fd=None;self.dirfds={};self.closed=False
        self.root=str(root);self.path=path;self.files=planned_files(path,attributes,configuration,index,shared,filter_required)
        selected=Path(objects)
        if not selected.is_absolute() or str(selected)!=os.path.normpath(str(selected)) or selected.is_relative_to(owner.private_state):fail('objects_selection')
        self.objects=str(selected)
        self.parent=owner.private_state/'state/accepted-prefix-hash'
        refs={name:owner.blob(raw) for name,raw in self.files.items()}
        self.spec=specification(self.root,path,str(self.parent),self.objects,self.files)
        self.name='scope-'+secrets.token_hex(16);self.label=str(self.parent/self.name)
        self.arguments=FrozenHashArguments(self.root,self.label,self.path)
        self.expected={};self.directories={}
        def create():
            ordinary_ancestors(selected);objects_stat=selected.lstat();owned(objects_stat,'directory');self.objects_identity=identity(objects_stat)
            owned_directory(self.parent,True)
            self.parent_fd=os.open(self.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
            parent_stat=os.fstat(self.parent_fd);owned(parent_stat,'directory');self.parent_identity=identity(parent_stat)
            self.check_parent()
            os.mkdir(self.name,0o700,dir_fd=self.parent_fd)
            self.fd=os.open(self.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=self.parent_fd)
            self.scope_identity=identity(os.fstat(self.fd))
            for name in ('refs','refs/heads','info'):
                parent_fd,leaf=self.address(name);os.mkdir(leaf,0o700,dir_fd=parent_fd)
                child=os.open(leaf,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=parent_fd);self.dirfds[name]=child;self.directories[name]=identity(os.fstat(child))
            for name,raw in self.files.items():
                parent_fd,leaf=self.address(name)
                out=os.open(leaf,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=parent_fd)
                try:
                    offset=0
                    while offset<len(raw):
                        count=os.write(out,raw[offset:])
                        if count<=0:fail('short_write')
                        offset+=count
                    os.fsync(out);self.expected[name]=identity(os.fstat(out))
                finally:os.close(out)
            os.symlink(self.objects,'objects',dir_fd=self.fd)
            self.objects_link_identity=identity(os.stat('objects',dir_fd=self.fd,follow_symlinks=False))
            self.check_namespace()
            return {'schema_version':1,'scope_label':self.label,'scope_identity':self.scope_identity,
                'parent_identity':self.parent_identity,'files':refs,'directories':self.directories,
                'file_identities':self.expected,'objects_link_identity':self.objects_link_identity,
                'objects_identity':self.objects_identity,'native_created':True,'OS_isolation_attested':False}
        try:
            self.wire=owner.perform('accepted-prefix-hash-auxiliary-create',self.spec,create)
            cache={ref['sha256']:self.files[name] for name,ref in refs.items()}
            creation_value(self.wire,self.spec,self.files,lambda ref:cache[ref['sha256']])
        except Exception:
            owner.record.capture_incomplete=True;self.close_descriptors();raise
    @property
    def record(self):return self.owner.record
    def address(self,name):
        if '/' not in name:return self.fd,name
        parent,leaf=name.rsplit('/',1);return self.dirfds[parent],leaf
    def check_parent(self):
        ordinary_ancestors(self.parent)
        if identity(self.parent.lstat())!=self.parent_identity or identity(os.fstat(self.parent_fd))!=self.parent_identity:fail('parent_changed')
    def check_namespace(self):
        self.check_parent()
        current=os.stat(self.name,dir_fd=self.parent_fd,follow_symlinks=False)
        if identity(current)!=self.scope_identity or identity(os.fstat(self.fd))!=self.scope_identity:fail('scope_changed')
        owned(current,'directory')
        if stat.S_IMODE(current.st_mode)!=0o700:fail('scope_mode_changed')
        expected_top={name.split('/')[0] for name in self.files}|{'refs','info','objects'}
        if set(os.listdir(self.fd))!=expected_top:fail('unknown_scope_entry_quarantined')
        for name,expected in self.directories.items():
            parent_fd,leaf=self.address(name);current=os.stat(leaf,dir_fd=parent_fd,follow_symlinks=False);owned(current,'directory')
            child=self.dirfds[name]
            if stat.S_IMODE(current.st_mode)!=0o700:fail('directory_mode_changed')
            if identity(current)!=expected or identity(os.fstat(child))!=expected:fail('directory_changed')
            expected_children={'heads'} if name=='refs' else set() if name=='refs/heads' else {'attributes'}
            if set(os.listdir(child))!=expected_children:fail('unknown_child_quarantined')
        for name,raw in self.files.items():
            parent_fd,leaf=self.address(name);current=os.stat(leaf,dir_fd=parent_fd,follow_symlinks=False);owned(current,'file')
            if identity(current)!=self.expected[name] or stat.S_IMODE(current.st_mode)!=0o600 or current.st_size!=len(raw):fail('file_changed')
            source=os.open(leaf,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent_fd)
            try:
                if identity(os.fstat(source))!=self.expected[name]:fail('file_replaced')
                captured=bytearray()
                while block:=os.read(source,min(65536,len(raw)+1-len(captured))):
                    captured.extend(block)
                    if len(captured)>len(raw):fail('file_grew')
                if bytes(captured)!=raw:fail('file_bytes_changed')
            finally:os.close(source)
        link=os.stat('objects',dir_fd=self.fd,follow_symlinks=False)
        if not stat.S_ISLNK(link.st_mode) or identity(link)!=self.objects_link_identity or os.readlink('objects',dir_fd=self.fd)!=self.objects:fail('objects_link_changed')
        ordinary_ancestors(Path(self.objects));target=Path(self.objects).lstat();owned(target,'directory')
        if identity(target)!=self.objects_identity:fail('objects_directory_changed')
    def close_descriptors(self):
        for value in self.dirfds.values():os.close(value)
        self.dirfds={}
        for name in ('fd','parent_fd'):
            value=getattr(self,name,None)
            if value is not None:os.close(value);setattr(self,name,None)
    def finish(self):
        if self.closed:fail('already_closed')
        if self.owner.record.capture_incomplete:
            self.close_descriptors();self.closed=True;fail('journal_loss_quarantined')
        def remove():
            self.check_namespace()
            for name in self.files:
                parent_fd,leaf=self.address(name);os.unlink(leaf,dir_fd=parent_fd)
            os.unlink('objects',dir_fd=self.fd)
            for name in ('refs/heads','refs','info'):
                parent_fd,leaf=self.address(name);os.rmdir(leaf,dir_fd=parent_fd)
            if os.listdir(self.fd):fail('cleanup_unknown_entry_quarantined')
            os.rmdir(self.name,dir_fd=self.parent_fd)
            try:os.stat(self.name,dir_fd=self.parent_fd,follow_symlinks=False)
            except FileNotFoundError:pass
            else:fail('scope_reappeared')
            return {'schema_version':1,'scope_label':self.label,'scope_identity':self.scope_identity,
                'native_auxiliary_removed':True,'OS_isolation_attested':False}
        try:
            wire=self.owner.perform('accepted-prefix-hash-auxiliary-remove',{'scope_label':self.label,'scope_identity':self.scope_identity},remove)
            return removal_value(wire,self.wire)
        except Exception:self.owner.record.capture_incomplete=True;raise
        finally:self.closed=True;self.close_descriptors()
