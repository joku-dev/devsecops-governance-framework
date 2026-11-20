"""Selected owned append using actual native Python buffered text streams.

No fsync, parent creation, truncation or separator is added. Resource release
after a capture failure is separate from retained original kernel behavior.
"""
import io,os,stat
from lib.requirement_validation_budget import InputAdmissionError
from lib.providers.workbook_import_io import original_error,failure_value
from lib.documentation_reconciliation_append import RetainedAppend

class NativeAppend(RetainedAppend):
    def __exit__(self,*exception):
        if self.owner.record.capture_incomplete:return False
        return super().__exit__(*exception)

    def __init__(self,owner,path,label):
        super().__init__(owner,path,label);self.stream=None;self.fd=None;self.fd_identity=None
        owner.documentation_append_sessions=getattr(owner,'documentation_append_sessions',[])
        owner.documentation_append_sessions.append(self)
        owner.output.admit(path,label);self.anchor=owner.output.anchor(path)
        self.before=self.anchor.snapshot(path);owner.output.prior(path,self.before)
        self.prior_raw=b''
        if self.before['kind']=='file':
            from lib.providers.sbom_export_storage import read_private
            self.prior_raw=read_private(owner.record.root/'blobs'/self.before['content']['sha256'],self.before['content']['bytes'])
        owner.append({'kind':'documentation-append-before','selection':self.spec,'anchor':self.anchor.frame,'snapshot':self.before})
        self.stage('open')

    def open_stream(self):
        parts=self.anchor.parts(self.path)
        def opener(label,flags):
            if not flags&os.O_APPEND or flags&os.O_TRUNC:raise InputAdmissionError('documentation_native_append_flags_changed')
            with self.anchor.root_fd() as root:
                with self.anchor.parent(root,parts[:-1]) as parent:
                    if self.before['kind']=='missing':flags|=os.O_EXCL
                    self.fd=os.open(parts[-1],flags|os.O_NOFOLLOW|os.O_NONBLOCK,0o666,dir_fd=parent)
            value=os.fstat(self.fd)
            self.fd_identity=(value.st_dev,value.st_ino)
            if not stat.S_ISREG(value.st_mode) or value.st_uid!=os.geteuid() or value.st_nlink!=1 or value.st_mode&0o7022:
                os.close(self.fd);self.fd=None;raise InputAdmissionError('documentation_native_owned_append_file_required')
            if self.before['kind']=='file' and (list(self.fd_identity)!=self.before['identity'] or stat.S_IMODE(value.st_mode)!=self.before['mode']):
                os.close(self.fd);self.fd=None;raise InputAdmissionError('documentation_native_append_replaced')
            self.opened={'mode':stat.S_IMODE(value.st_mode),'identity':list(self.fd_identity)}
            return self.fd
        return io.open(self.label,'a',encoding='utf-8',opener=opener)

    def stage(self,stage,text=None):
        payload=None if text is None else self.owner.blob(text.encode('utf-8'))
        def effect():
            result=error=None
            try:
                if stage=='open':self.stream=self.open_stream()
                elif stage=='write':result=self.stream.write(text)
                elif stage=='close':self.stream.close()
                else:raise InputAdmissionError('documentation_native_append_stage_required')
            except OSError as caught:
                if stage=='open':caught=original_error(caught,self.label)
                error=failure_value(caught)
            after=self.anchor.snapshot(self.path)
            return {'stage':stage,'snapshot':after,'opened_file':self.opened,
                    'closed':self.stream is None or self.stream.closed,'result':result,'failure':error}
        try:
            wire=self.owner.perform('documentation-native-append',self.arguments(stage,payload),effect)
            # Validation is pure, but NativeIO.blob stores rather than reads.
            from lib.providers.sbom_export_storage import read_private
            record_root=self.owner.record.root
            class View:
                def __init__(view,owner):view.__dict__.update(owner.__dict__);view.output=owner.output
                def blob(view,ref):return read_private(record_root/'blobs'/ref['sha256'],ref['bytes'])
            owner=self.owner;self.owner=View(owner)
            try:return self.validate(wire,stage,text)
            finally:self.owner=owner
        except (InputAdmissionError,ValueError):
            self.owner.record.capture_incomplete=True;raise

    def release(self):
        if self.stream is None or self.stream.closed:return {'released':False,'already_closed':True}
        self.owner.record.capture_incomplete=True
        value=os.fstat(self.stream.fileno())
        if (value.st_dev,value.st_ino)!=self.fd_identity:
            raise InputAdmissionError('documentation_native_release_descriptor_replaced')
        try:self.stream.close()
        except OSError as error:return {'released':self.stream.closed,'error_type':type(error).__name__,'message':str(error),'original_verdict':False}
        return {'released':True,'unobserved_close_may_flush':True,'original_verdict':False}
