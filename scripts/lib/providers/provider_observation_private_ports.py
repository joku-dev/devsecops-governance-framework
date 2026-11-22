"""Scoped actual OS metadata for the complete original private-file checker."""
import errno,os,stat,sys
from pathlib import Path
from lib.provider_observation_private_ports import MetadataProtocol,STAT_FIELDS,MOUNTINFO
from lib.intake_atomic_effects import error_value
from lib.requirement_validation_budget import InputAdmissionError
from lib.providers.workbook_import_io import ordinary_ancestors,original_error


class NativePrivateMetadata(MetadataProtocol):
    def __init__(self,record,*,cwd,files):
        self.record=record;self.raw_descriptors={};self.failed=False;self.closed=False
        context={'platform':sys.platform,'O_RDONLY':os.O_RDONLY,'O_NOFOLLOW':os.O_NOFOLLOW}
        self.initialize(context,cwd,files);self.append({'kind':'provider-private-context','context':context})
    def stop(self):
        self.failed=True;self.record.capture_incomplete=True;raise InputAdmissionError('provider_private_capture_incomplete') from None
    def append(self,value):
        try:self.record.append(value)
        except Exception:self.stop()
    def blob(self,value):
        from lib.providers.sbom_export_storage import read_private
        return read_private(self.record.blobs/value['sha256'],4096)
    def packet(self,operation,args):
        if self.closed:raise InputAdmissionError('provider_private_session_closed')
        if self.failed or self.record.capture_incomplete:self.stop()
        token=self.record.sequence;self.append({'kind':'provider-private-intent','operation':token,'action':operation,'arguments':args});value=error=post=None
        try:
            try:value=self.native(operation,args)
            except OSError as caught:
                label=args.get('selection',{}).get('label');caught=original_error(caught,label) if label is not None and caught.filename is not None else caught
                if type(caught.errno) is not int:self.stop()
                error=error_value(caught)
            if operation=='close':post={'open':args['descriptor'] in self.raw_descriptors}
            result={'value':value,'error':error,'post':post};self.append({'kind':'provider-private-outcome','operation':token,'packet':result});return result
        except Exception:self.stop()
    def selected(self,args):
        spec=args['selection'];path=Path(spec['path'])
        if str(path)!=spec['path']:self.stop()
        if path!=Path(MOUNTINFO):ordinary_ancestors(path.parent)
        return path
    def native(self,operation,args):
        if operation=='environment':return os.environ.get(args['key'])
        if operation=='geteuid':return os.geteuid()
        if operation=='open':
            path=self.selected(args);fd=os.open(path,args['flags']|os.O_NONBLOCK)
            token=self.last_descriptor+1;self.raw_descriptors[token]={'fd':fd,'identity':None,'close_attempted':False}
            try:info=os.fstat(fd)
            except OSError:self.stop()
            self.raw_descriptors[token]['identity']=(info.st_dev,info.st_ino)
            if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):self.stop()
            return token
        if operation=='fstat':
            info=os.fstat(self.raw_descriptors[args['descriptor']]['fd']);return {k:getattr(info,k) for k in STAT_FIELDS}
        if operation=='close':
            row=self.raw_descriptors[args['descriptor']]
            row['close_attempted']=True
            try:os.close(row['fd'])
            except OSError as error:
                if error.errno==errno.EBADF:self.raw_descriptors.pop(args['descriptor'])
                raise
            else:self.raw_descriptors.pop(args['descriptor']);return None
        if operation=='getxattr':
            selected=self.raw_descriptors[args['descriptor']]['fd'] if 'descriptor' in args else self.selected(args)
            raw=os.getxattr(selected,args['key'])
            if len(raw)>4096:self.stop()
            return self.record.blob(raw)
        path=self.selected(args)
        if operation=='is_symlink':return path.is_symlink()
        if operation=='stat':
            info=path.stat();return {k:getattr(info,k) for k in STAT_FIELDS}
        if operation=='resolve':return str(path.resolve())
        if operation=='mountinfo':
            if str(path)!=MOUNTINFO:self.stop()
            with path.open('r') as stream:text=stream.read(1024**2+1)
            if len(text)>1024**2:self.stop()
            return text
        self.stop()
    def release_resources(self):
        required=bool(self.raw_descriptors);results=[]
        if required:self.record.capture_incomplete=True
        for token,row in list(self.raw_descriptors.items()):
            state='closed'
            try:
                if not row['close_attempted']:os.close(row['fd'])
                else:
                    info=os.fstat(row['fd'])
                    if row['identity']==(info.st_dev,info.st_ino):os.close(row['fd'])
                    else:state='identity_changed_not_closed'
            except OSError as error:state='already_closed' if error.errno==errno.EBADF else 'cleanup_unavailable'
            results.append({'descriptor':token,'state':state});self.raw_descriptors.pop(token)
        self.closed=True;return {'required':required,'outside_original_cleanup':results}
