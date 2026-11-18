"""Held-directory append-only effects at an explicitly selected external root.

Exclusive creation never replaces ledger history. Node-local coordination and
optimistic observations require one operating owner per shared destination.
"""
import os
from pathlib import Path,PurePosixPath
import stat

from lib import attestation_files
from lib.intake_recording import MAX_FILE,MAX_FILES,MAX_TOTAL

FIELDS=('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns','st_mode','st_nlink','st_uid')


def relative(value):
    path=PurePosixPath(value)
    if (not value or path.is_absolute() or path.as_posix()!=value or any(p.casefold() in ('.','..','.git') for p in path.parts)
            or '\\' in value or ':' in value or any(ord(c)<32 for c in value)):
        raise ValueError('unsafe_intake_record_path')
    return path


def within(path,root):
    """Include physical directory aliases on case-insensitive host filesystems."""
    path=Path(path);root=Path(root)
    if path.is_relative_to(root):return True
    try:base=os.stat(root,follow_symlinks=False)
    except FileNotFoundError:return False
    if not stat.S_ISDIR(base.st_mode):return False
    for ancestor in (path,*path.parents):
        try:row=os.stat(ancestor,follow_symlinks=False)
        except FileNotFoundError:continue
        if stat.S_ISDIR(row.st_mode) and (row.st_dev,row.st_ino)==(base.st_dev,base.st_ino):return True
    return False


def read_at(parent,name,*,output=False):
    try:fd=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
    except FileNotFoundError:return None,None
    try:
        before=os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_size>MAX_FILE:
            raise ValueError('bounded_regular_single_link_intake_record_required')
        if output and (before.st_uid!=os.geteuid() or before.st_mode&0o022):raise ValueError('owned_safe_native_output_required')
        with os.fdopen(fd,'rb',closefd=False) as stream:raw=stream.read(MAX_FILE+1)
        after=os.fstat(fd)
        if len(raw)>MAX_FILE or any(getattr(before,key)!=getattr(after,key) for key in FIELDS):
            raise ValueError('intake_record_changed_during_read')
        return raw,{key:getattr(before,key) for key in FIELDS}
    finally:os.close(fd)


def directory_names(fd):
    names=[];count=0
    with os.scandir(fd) as entries:
        for entry in entries:
            count+=1
            if count>MAX_FILES*4:raise ValueError('intake_record_directory_budget')
            if entry.name.endswith('.json'):names.append(entry.name)
    return sorted(names)


class LedgerRoot:
    def __init__(self,path,excluded):
        requested=Path(path)
        if requested.is_symlink():raise ValueError('intake_record_root_symlink_forbidden')
        self.path=requested.resolve();self.excluded=[Path(p).resolve() for p in excluded]
        if any(within(self.path,p) for p in self.excluded):
            raise ValueError('external_intake_record_root_required')
        if any(p.casefold()=='.git' for p in self.path.parts):raise ValueError('intake_record_git_root_forbidden')
        parent=attestation_files.parent(self.path/'held-root')
        if parent is None:raise FileNotFoundError('intake_record_root_missing')
        self.fd=parent;row=os.fstat(parent);self.binding={'st_dev':row.st_dev,'st_ino':row.st_ino}
        self.check()

    def check(self):
        row=os.stat(self.path,follow_symlinks=False)
        if not stat.S_ISDIR(row.st_mode) or any(getattr(row,key)!=value for key,value in self.binding.items()):
            raise ValueError('intake_record_root_changed')

    def directory(self,name,*,create=False):
        self.check();parts=relative(name).parts
        target=self.path.joinpath(*parts)
        if any(within(target,p) or within(p,target) for p in self.excluded):raise ValueError('external_intake_record_scope_required')
        fd=os.dup(self.fd)
        try:
            for part in parts:
                try:following=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
                except FileNotFoundError:
                    if not create:os.close(fd);return None
                    try:os.mkdir(part,0o700,dir_fd=fd)
                    except FileExistsError:pass
                    following=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
                os.close(fd);fd=following
            return fd
        except BaseException:os.close(fd);raise

    def snapshot(self,scopes,filters=None):
        # A shared conflict directory can contain thousands of unrelated repos.
        # Read only the computed conflict leaf, never enumerate that directory.
        filters=filters or {}
        files={};metadata={};directories={};total=0
        for scope in scopes:
            if scope in filters and not filters[scope]:
                directories[scope]=None;continue
            fd=self.directory(scope)
            if fd is None:directories[scope]=None;continue
            try:
                row=os.fstat(fd);directories[scope]={key:getattr(row,key) for key in ('st_dev','st_ino')}
                names=directory_names(fd) if scope not in filters else list(filters[scope])
                if len(files)+len(names)>MAX_FILES:raise ValueError('intake_record_file_count_budget')
                for name in names:
                    full=scope+'/'+name;relative(full);raw,observed=read_at(fd,name)
                    if raw is None:
                        if scope in filters:continue
                        raise ValueError('intake_record_members_changed')
                    total+=len(raw)
                    if total>MAX_TOTAL:raise ValueError('intake_record_total_budget')
                    files[full]=raw;metadata[full]=observed
                if scope not in filters and names!=directory_names(fd):raise ValueError('intake_record_members_changed')
            finally:os.close(fd)
        self.check();return files,metadata,directories

    def one(self,name):
        path=relative(name);fd=self.directory(path.parent.as_posix())
        if fd is None:return None,None
        try:return read_at(fd,path.name)
        finally:os.close(fd)

    def apply(self,scopes,before,metadata,directories,writes,filters=None):
        if self.snapshot(scopes,filters)!=(before,metadata,directories):raise ValueError('intake_ledger_changed_before_write')
        if len(set(before)|set(writes))>MAX_FILES or sum(map(len,before.values()))+sum(map(len,writes.values()))>MAX_TOTAL:raise ValueError('intake_record_total_budget')
        expected=dict(before)
        for name,raw in writes.items():
            path=relative(name)
            if path.parent.as_posix() not in scopes or name in before or len(raw)>MAX_FILE:
                raise ValueError('invalid_append_only_intake_write')
            current,current_meta,current_dirs=self.snapshot(scopes,filters)
            if current!=expected or any(current_meta.get(k)!=v for k,v in metadata.items()):
                raise ValueError('intake_ledger_changed_before_write')
            if any(value is not None and current_dirs.get(k)!=value for k,value in directories.items()):raise ValueError('intake_ledger_directory_changed')
            fd=self.directory(path.parent.as_posix(),create=True)
            try:
                file=os.open(path.name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=fd)
                with os.fdopen(file,'wb') as stream:stream.write(raw);stream.flush();os.fsync(stream.fileno())
                os.fsync(fd)
            finally:os.close(fd)
            expected[name]=raw
        after,after_meta,after_dirs=self.snapshot(scopes,filters)
        if after!=expected or any(after_meta.get(k)!=v for k,v in metadata.items()):raise ValueError('intake_ledger_changed_after_write')
        return after,after_meta,after_dirs

    def close(self):os.close(self.fd)


def output_path(path,excluded,ledger):
    value=attestation_files.destination(path,excluded)
    if any(within(value,Path(root).resolve()) for root in excluded):raise ValueError('external_native_output_required')
    for scope in ('status/collection-attempts','status/intake-events','status/intake-conflicts'):
        if within(value,ledger/scope):raise ValueError('native_output_must_not_modify_ledger_history')
    return value


def output_observation(path):
    parent=attestation_files.parent(path)
    if parent is None:return None,None
    try:return read_at(parent,path.name,output=True)
    finally:os.close(parent)


def append_output(path,raw,before,metadata):
    if len(raw)+len(before or b'')>MAX_FILE:raise ValueError('native_output_byte_budget')
    parent=attestation_files.parent(path,create=True)
    try:
        held=os.fstat(parent);current=os.stat(path.parent,follow_symlinks=False)
        if (held.st_dev,held.st_ino)!=(current.st_dev,current.st_ino):raise ValueError('native_output_parent_changed')
        if read_at(parent,path.name,output=True)!=(before,metadata):raise ValueError('native_output_changed_before_append')
        flags=os.O_WRONLY|os.O_APPEND|os.O_NOFOLLOW|os.O_NONBLOCK
        if before is None:flags|=os.O_CREAT|os.O_EXCL
        file=os.open(path.name,flags,0o600,dir_fd=parent)
        try:
            row=os.fstat(file)
            if not stat.S_ISREG(row.st_mode) or row.st_nlink!=1 or row.st_uid!=os.geteuid() or row.st_mode&0o022:
                raise ValueError('owned_safe_native_output_required')
            if metadata is not None and any(getattr(row,k)!=v for k,v in metadata.items()):raise ValueError('native_output_changed_before_append')
            with os.fdopen(file,'wb',closefd=False) as stream:stream.write(raw);stream.flush();os.fsync(file)
        finally:os.close(file)
        after,observed=read_at(parent,path.name,output=True)
        if after!=(before or b'')+raw:raise ValueError('native_output_changed_after_append')
        return after,observed
    finally:os.close(parent)
