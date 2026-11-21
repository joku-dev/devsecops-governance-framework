"""Owned atomic O_EXCL creation with actual original buffered binary write/close."""
import errno,io,os,stat
from lib.personal_channel_exclusive import RetainedExclusive,RetainedOutputError
from lib.providers.workbook_import_io import original_error,failure_value
from lib.providers.sbom_export_storage import read_private
from lib.requirement_validation_budget import InputAdmissionError

# A Python buffered object's finalizer closes its numeric fd. If another actor
# replaced that fd, keep the object inert until process teardown rather than
# let garbage collection close an unowned descriptor during another request.
_QUARANTINED_STREAMS=[]

class NativeExclusive(RetainedExclusive):
    def __init__(self,owner,path,label):
        super().__init__(owner,path,label)
        self.stream=self.resource=None;self.fd=self.fd_identity=None;self.last=None
        owner.personal_exclusive_sessions=getattr(owner,'personal_exclusive_sessions',[]);owner.personal_exclusive_sessions.append(self)
        owner.output.admit(path,label);self.anchor=owner.output.anchor(path)
        self.before=self.anchor.snapshot(path);owner.output.prior(path,self.before);self.last=self.before
        owner.append({'kind':'personal-exclusive-before','selection':self.spec,'anchor':self.anchor.frame,'snapshot':self.before})
        self.stage('open')

    def open_stream(self):
        parts=self.anchor.parts(self.path)
        def opener(label,flags):
            if not flags&os.O_EXCL or not flags&os.O_CREAT or flags&(os.O_TRUNC|os.O_APPEND):raise InputAdmissionError('personal_exclusive_native_flags_changed')
            with self.anchor.root_fd() as root:
                with self.anchor.parent(root,parts[:-1]) as parent:
                    self.fd=os.open(parts[-1],flags|os.O_NOFOLLOW|os.O_NONBLOCK,0o666,dir_fd=parent)
            value=os.fstat(self.fd);self.fd_identity=(value.st_dev,value.st_ino)
            if not stat.S_ISREG(value.st_mode) or value.st_uid!=os.geteuid() or value.st_nlink!=1 or value.st_mode&0o7022:
                os.close(self.fd);raise InputAdmissionError('personal_exclusive_owned_file_required')
            self.opened={'mode':stat.S_IMODE(value.st_mode),'identity':list(self.fd_identity)}
            return self.fd
        self.resource=io.open(self.label,'xb',opener=opener)
        return self.resource

    def descriptor_owned(self):
        if self.fd is None:return False
        try:value=os.fstat(self.fd)
        except OSError as error:
            if error.errno==errno.EBADF:return False
            raise
        if (value.st_dev,value.st_ino)!=self.fd_identity:raise InputAdmissionError('personal_exclusive_descriptor_replaced')
        return True

    def __exit__(self,*error):
        if self.owner.record.capture_incomplete:return False
        return super().__exit__(*error)

    def stage(self,stage,raw=None):
        payload=None if raw is None else self.owner.blob(raw)
        def effect():
            if self.anchor.snapshot(self.path)!=self.last:raise InputAdmissionError('personal_exclusive_changed_between_effects')
            result=error=None
            try:
                if stage=='open':self.stream=self.open_stream()
                elif stage=='write':
                    if not self.descriptor_owned():raise InputAdmissionError('personal_exclusive_descriptor_missing')
                    result=self.stream.write(raw)
                elif stage=='close':
                    if not self.descriptor_owned():raise InputAdmissionError('personal_exclusive_descriptor_missing')
                    self.stream.close()
                else:raise InputAdmissionError('personal_exclusive_stage_required')
            except OSError as caught:
                if stage=='open':caught=original_error(caught,self.label)
                error=failure_value(caught)
            after=self.anchor.snapshot(self.path);self.last=after
            closed=self.stream.closed if self.stream is not None else not self.descriptor_owned()
            return {'stage':stage,'snapshot':after,'opened_file':self.opened,'closed':closed,'result':result,'failure':error}
        try:
            wire=self.owner.perform('personal-exclusive-output',self.arguments(stage,payload),effect)
            actual=self.owner;root=actual.record.root
            class View:
                def __init__(view):view.__dict__.update(actual.__dict__);view.output=actual.output
                def blob(view,ref):return read_private(root/'blobs'/ref['sha256'],ref['bytes'])
            self.owner=View()
            try:return self.validate(wire,stage,raw)
            finally:self.owner=actual
        except RetainedOutputError:raise
        except Exception as error:
            self.owner.record.capture_incomplete=True
            if isinstance(error,InputAdmissionError):raise
            raise InputAdmissionError('personal_exclusive_capture_incomplete') from error

    def release(self):
        if self.resource is not None and self.resource.closed:return {'released':False,'already_closed':True}
        if self.resource is None and self.fd is None:return {'released':False,'already_closed':True}
        self.owner.record.capture_incomplete=True
        try:owned=self.descriptor_owned()
        except InputAdmissionError:
            self.quarantine();raise
        if not owned:
            self.quarantine()
            return {'released':False,'descriptor_ownership_lost':True,'resource_quarantined':True,'original_verdict':False}
        try:
            if self.resource is not None:self.resource.close()
            else:os.close(self.fd)
        except OSError as error:
            return {'released':self.resource.closed if self.resource is not None else not self.descriptor_owned(),
                    'error_type':type(error).__name__,'message':str(error),'original_verdict':False}
        return {'released':True,'unobserved_close_may_flush':True,'original_verdict':False}

    def quarantine(self):
        if self.resource is not None and not self.resource.closed and not any(stream is self.resource for stream in _QUARANTINED_STREAMS):
            _QUARANTINED_STREAMS.append(self.resource)
