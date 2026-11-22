"""Bounded held-fd credential text reads; payload and digest stay unrecorded."""
import errno,os,stat
from pathlib import Path
from lib.provider_observation_credentials import intent
from lib.provider_observation_context import SecretText
from lib.provider_observation_private_ports import STAT_FIELDS
from lib.provider_observation_reads import capability
from lib.intake_atomic_effects import error_value
from lib.providers.operations_files import held_root
from lib.providers.workbook_import_io import original_error
from lib.requirement_validation_budget import InputAdmissionError

MAX_CREDENTIAL=65536


class NativeCredentialCapability:
    def __init__(self,record,metadata,*,credential):
        self.record,self.metadata,self.credential=record,metadata,credential;self.value=None;self.used=False;self.closed=False;self.fd=None;self.identity=None
    def stop(self):
        self.record.capture_incomplete=True;raise InputAdmissionError('provider_observation_credential_capture_incomplete') from None
    def append(self,value):
        try:self.record.append(value)
        except Exception:self.stop()
    def snapshot(self,info):return {k:getattr(info,k) for k in STAT_FIELDS}
    def read_native(self,selected,expected):
        path=Path(selected['path'])
        with held_root(path.parent) as parent:
            before=os.stat(path.name,dir_fd=parent,follow_symlinks=False)
            if self.snapshot(before)!=expected or not stat.S_ISREG(before.st_mode) or before.st_size>MAX_CREDENTIAL:self.stop()
            self.fd=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent);self.identity=(before.st_dev,before.st_ino)
            try:
                if self.snapshot(os.fstat(self.fd))!=expected:self.stop()
                # Native default codec and newline translation are the original
                # Path.read_text contract; no raw bytes enter the journal.
                with os.fdopen(self.fd,'r',closefd=False) as stream:
                    text=stream.read(MAX_CREDENTIAL+1);encoding=stream.encoding
                if len(text)>MAX_CREDENTIAL or self.snapshot(os.fstat(self.fd))!=expected or self.snapshot(os.stat(path.name,dir_fd=parent,follow_symlinks=False))!=expected:self.stop()
                return text,encoding
            finally:
                try:os.close(self.fd)
                except OSError:self.stop()
                else:self.fd=None
    def read(self,path):
        if self.closed or self.used or self.record.capture_incomplete:self.stop()
        try:expected=intent(self.metadata,path,self.credential,self.record.sequence)
        except (ValueError,InputAdmissionError):self.stop()
        self.append(expected);self.used=True;encoding=error=None;value=None
        try:
            try:value,encoding=self.read_native(expected['selection'],expected['private_stat'])
            except (UnicodeError,ValueError):self.stop()
            except OSError as caught:
                # ELOOP/ENOTDIR can be produced by the additional no-alias
                # acquisition guard. They cannot become an original verdict.
                if caught.errno in (errno.ELOOP,errno.ENOTDIR) or type(caught.errno) is not int:self.stop()
                caught=original_error(caught,expected['selection']['label']);error=caught
            self.append({'kind':'provider-credential-read-outcome','operation':expected['operation'],'encoding':encoding,
                'error':None if error is None else error_value(error)})
        except Exception:self.stop()
        if error is not None:raise error
        self.value=value;return SecretText('credential-1')
    def resolve(self,reference):
        cap=capability(reference)
        if self.closed or cap['identifier']!='credential-1' or self.value is None or self.record.capture_incomplete:self.stop()
        return self.value
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
        self.value=None;self.closed=True;return {'required':required,'outside_original_cleanup':state}
