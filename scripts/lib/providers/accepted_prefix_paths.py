"""Original is_file/is_symlink calls, with stable lstat metadata and no file opens."""
import os,stat
from pathlib import Path
from lib.accepted_prefix_paths import probe_value
from lib.providers.accepted_prefix_protocol import LegacyAcceptedPrefixProtocol
from lib.providers.workbook_import_io import ordinary_ancestors,original_error,failure_value
from lib.requirement_validation_budget import InputAdmissionError

class NativePrefixPaths:
    def __init__(self,owner,root,context):self.owner,self.root,self.profile=owner,str(root),LegacyAcceptedPrefixProtocol(context)
    def state(self,path):
        try:
            ordinary_ancestors(path.parent);value=path.lstat()
        except (FileNotFoundError,NotADirectoryError):return {'kind':'missing'}
        except OSError as error:return {'kind':'unavailable','failure':failure_value(original_error(error,str(path)))}
        kind='symlink' if stat.S_ISLNK(value.st_mode) else 'file' if stat.S_ISREG(value.st_mode) else 'directory' if stat.S_ISDIR(value.st_mode) else 'other'
        return {'kind':kind,'identity':[value.st_dev,value.st_ino],'mode':stat.S_IMODE(value.st_mode),'uid':value.st_uid,
            'nlink':value.st_nlink,'bytes':value.st_size,'mtime_ns':value.st_mtime_ns,'ctime_ns':value.st_ctime_ns,
            'link':os.readlink(path) if kind=='symlink' else None}
    def probe(self,path,kind,label):
        self.profile.hashed_path(path,self.root)
        if kind not in ('is_file','is_symlink'):raise InputAdmissionError('accepted_prefix_path_probe_required')
        spec={'path':path,'probe':kind,'label':label};selected=Path(path)
        if selected.is_relative_to(self.owner.private_state):raise InputAdmissionError('accepted_prefix_private_path_forbidden')
        def effect():
            before=self.state(selected);result=failure=None
            try:result=getattr(selected,kind)()
            except OSError as error:failure=failure_value(original_error(error,label))
            after=self.state(selected)
            if before!=after:raise InputAdmissionError('accepted_prefix_path_changed')
            return {'schema_version':1,'specification':spec,'before':before,'after':after,'result':result,'failure':failure}
        try:return probe_value(self.owner.perform('accepted-prefix-path-probe',spec,effect),spec)
        except Exception as error:
            from lib.requirement_review_output import RetainedOutputError
            if isinstance(error,RetainedOutputError):raise
            self.owner.record.capture_incomplete=True;raise
