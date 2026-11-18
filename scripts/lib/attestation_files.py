"""Explicit original output-file replacement with bounded before/after observations.

Callers retain the previous bytes and durable intent before using this port.
One operating owner per external destination; node locks do not create a
distributed lease or overwrite authorization for another actor's changes.
"""
import os
from pathlib import Path
import stat

MAX_OUTPUT=1024**2


def destination(path,excluded):
    path=Path(path)
    if path.is_symlink():raise ValueError('attestation_output_symlink_forbidden')
    path=path.resolve()
    if not path.name or any(path.is_relative_to(Path(root).resolve()) for root in excluded):raise ValueError('attestation_output_outside_product_and_instance_required')
    if any(part.casefold()=='.git' for part in path.parts):raise ValueError('attestation_git_output_forbidden')
    return path


def parent(path,*,create=False):
    fd=os.open(path.anchor,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        for part in path.parent.parts[1:]:
            try:following=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
            except FileNotFoundError:
                if not create:os.close(fd);return None
                try:os.mkdir(part,0o700,dir_fd=fd)
                except FileExistsError:pass
                following=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd)
            os.close(fd);fd=following
        return fd
    except BaseException:os.close(fd);raise


def read_at(fd,name):
    try:file=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
    except FileNotFoundError:return None,None
    try:
        before=os.fstat(file)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_uid!=os.geteuid() or before.st_mode&0o022:
            raise ValueError('attestation_owned_regular_output_required')
        if before.st_size>MAX_OUTPUT:raise ValueError('attestation_output_byte_budget')
        raw=bytearray()
        while chunk:=os.read(file,min(65536,MAX_OUTPUT+1-len(raw))):
            raw.extend(chunk)
            if len(raw)>MAX_OUTPUT:raise ValueError('attestation_output_byte_budget')
        after=os.fstat(file)
        fields=('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns','st_mode','st_nlink')
        if any(getattr(before,key)!=getattr(after,key) for key in fields):raise ValueError('attestation_output_changed_during_read')
        metadata={key:getattr(before,key) for key in fields}
        return bytes(raw),metadata
    finally:os.close(file)


def observe(path):
    fd=parent(path)
    if fd is None:return None,None
    try:return read_at(fd,path.name)
    finally:os.close(fd)


def input_bytes(path,limit=MAX_OUTPUT):
    """Original readable-file aliases are permitted; inspect a bounded held regular file."""
    path=Path(path).resolve();fd=parent(path)
    if fd is None:raise FileNotFoundError('attestation_input_missing')
    try:file=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=fd)
    finally:os.close(fd)
    try:
        before=os.fstat(file)
        if not stat.S_ISREG(before.st_mode) or before.st_size>limit:raise ValueError('attestation_regular_bounded_input_required')
        with os.fdopen(file,'rb',closefd=False) as stream:raw=stream.read(limit+1)
        after=os.fstat(file)
        if len(raw)>limit or any(getattr(before,key)!=getattr(after,key) for key in ('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns','st_mode','st_nlink')):
            raise ValueError('attestation_input_changed_during_read')
        return raw
    finally:os.close(file)


def apply(path,raw,before,metadata):
    if not isinstance(raw,bytes) or len(raw)>MAX_OUTPUT:raise ValueError('attestation_output_byte_budget')
    fd=parent(path,create=True)
    try:
        held=os.fstat(fd);current=os.stat(path.parent,follow_symlinks=False)
        if (held.st_dev,held.st_ino)!=(current.st_dev,current.st_ino):raise ValueError('attestation_output_parent_changed')
        if read_at(fd,path.name)!=(before,metadata):raise ValueError('attestation_output_changed_before_write')
        flags=os.O_WRONLY|os.O_NOFOLLOW|os.O_NONBLOCK
        if before is None:flags|=os.O_CREAT|os.O_EXCL
        file=os.open(path.name,flags,0o600,dir_fd=fd)
        try:
            row=os.fstat(file)
            if not stat.S_ISREG(row.st_mode) or row.st_nlink!=1 or row.st_uid!=os.geteuid():raise ValueError('attestation_owned_regular_output_required')
            if metadata is not None and any(getattr(row,key)!=value for key,value in metadata.items()):raise ValueError('attestation_output_changed_before_write')
            os.ftruncate(file,0)
            with os.fdopen(file,'wb',closefd=False) as stream:stream.write(raw);stream.flush();os.fsync(file)
        finally:os.close(file)
        after,observed=read_at(fd,path.name)
        if after!=raw:raise ValueError('attestation_output_changed_after_write')
        return after,observed
    finally:os.close(fd)
