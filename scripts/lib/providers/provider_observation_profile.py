"""Profile bytes admitted by the complete private checker, independent of file UID."""
import errno,os,stat
from pathlib import Path
from lib.provider_observation_profile import read_intent,decoded,MAX_PROFILE
from lib.provider_observation_private_ports import STAT_FIELDS
from lib.providers.operations_files import held_root
from lib.providers.workbook_import_io import original_error
from lib.intake_atomic_effects import error_value
from lib.requirement_validation_budget import InputAdmissionError


class NativeCheckedProfile:
    def __init__(self,record,metadata,*,profile):self.record,self.metadata,self.profile=record,metadata,profile;self.fd=None;self.identity=None;self.closed=False
    def stop(self):
        self.record.capture_incomplete=True;raise InputAdmissionError('provider_observation_profile_capture_incomplete') from None
    def append(self,row):
        try:self.record.append(row)
        except Exception:self.stop()
    def snapshot(self,value):return {k:getattr(value,k) for k in STAT_FIELDS}
    def acquire(self,selection,expected):
        path=Path(selection['path'])
        with held_root(path.parent) as parent:
            before=os.stat(path.name,dir_fd=parent,follow_symlinks=False)
            if self.snapshot(before)!=expected or not stat.S_ISREG(before.st_mode) or before.st_size>MAX_PROFILE:self.stop()
            self.fd=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent);self.identity=(before.st_dev,before.st_ino)
            try:
                if self.snapshot(os.fstat(self.fd))!=expected:self.stop()
                parts=[];size=0
                while True:
                    raw=os.read(self.fd,min(65536,MAX_PROFILE+1-size))
                    if not raw:break
                    parts.append(raw);size+=len(raw)
                    if size>MAX_PROFILE:self.stop()
                if self.snapshot(os.fstat(self.fd))!=expected or self.snapshot(os.stat(path.name,dir_fd=parent,follow_symlinks=False))!=expected:self.stop()
                return b''.join(parts)
            finally:
                try:os.close(self.fd)
                except OSError:self.stop()
                else:self.fd=None
    def read(self,path,encoding,errors):
        if self.closed or self.record.capture_incomplete:self.stop()
        try:expected=read_intent(self.metadata,path,self.profile,self.record.sequence,encoding,errors)
        except ValueError:self.stop()
        self.append(expected);raw=None;error=None;content=None
        try:
            try:raw=self.acquire(expected['selection'],expected['private_stat'])
            except OSError as caught:
                if caught.errno in (errno.ELOOP,errno.ENOTDIR) or type(caught.errno) is not int:self.stop()
                error=original_error(caught,expected['selection']['label']) if caught.filename is not None else caught
            if error is None:content=self.record.blob(raw)
            self.append({'kind':'provider-profile-read-outcome','operation':expected['operation'],'content':content,'error':None if error is None else error_value(error)})
        except Exception:self.stop()
        if error is not None:raise error
        return decoded(raw,encoding,errors)
    def release_resources(self):
        required=self.fd is not None;state='no_extra_cleanup'
        if required:
            self.record.capture_incomplete=True
            try:
                info=os.fstat(self.fd)
                if (info.st_dev,info.st_ino)==self.identity:os.close(self.fd);state='closed'
                else:state='identity_changed_not_closed'
            except OSError as error:state='already_closed' if error.errno==errno.EBADF else 'cleanup_unavailable'
            self.fd=None
        self.closed=True;return {'required':required,'outside_original_cleanup':state}
