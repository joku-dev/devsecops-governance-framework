"""Owned selected Source writes and stable snapshots around admitted Git steps."""
from pathlib import Path
from lib.providers.pilot_run_intake_io import NativeRunIO
from lib.providers.operational_publication_paths import NativePublisherPaths
from lib.self_security_publication_io import FILES,selected
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError


class NativeSelfSecurityIO(NativeRunIO):
    def __init__(self,*args,source,**kwargs):self.source=source;super().__init__(*args,**kwargs)
    def check(self,path,label,*,write=False):
        value=super().check(path,label,write=write)
        try:selected(self.source,path,write)
        except IntegrityError as error:raise InputAdmissionError(str(error)) from None
        return value


class NativeWorktreeSnapshots:
    def __init__(self,owner,source):self.owner,self.source=owner,source;self.paths=NativePublisherPaths(owner,source=source,outputs=())
    def blob(self,ref):return self.paths.cache[ref['sha256']]
    def __call__(self):
        result={}
        for name in FILES:
            path=str(Path(self.source)/name);before=self.owner.entry(path);node=self.paths.observe(path);after=self.owner.entry(path)
            if before!=after:raise InputAdmissionError('self_security_worktree_snapshot_changed')
            result[name]={'metadata':before,'snapshot':node}
        return result
