"""Exact bounded Source report selection and explicit Git transition epochs."""
from pathlib import PurePosixPath as P
from lib.self_security_publication import ALLOWED_PATHS,REPORT_JSON,VIEWER_DATA
from lib.synthetic_lifecycle_io import metadata
from lib.requirement_review_output import snapshot,RetainedOutputError
from lib.requirement_validation_replay import IntegrityError
from lib.pilot_run_intake_io import ReplayRunIO

FILES=tuple(sorted((*ALLOWED_PATHS,VIEWER_DATA)))


def selected(source,path,write=False):
    root=P(source);target=P(path)
    if not target.is_relative_to(root):raise IntegrityError('self_security_file_outside_source')
    name=target.relative_to(root).as_posix();directories={str(P(n).parent) for n in ALLOWED_PATHS}|{'generated','.'}
    if name not in (ALLOWED_PATHS|directories if write else set(FILES)|directories):raise IntegrityError('self_security_file_outside_closed_scope')
    return path


def changes_worktree(command):
    return command[:2] in (['git','reset'],['git','clean'],['git','switch']) or command[:1]==['git'] and 'merge' in command[1:]


class WorktreeEpochs:
    def __init__(self,owner,source,observe=None,blob=None):
        self.owner,self.source,self.observe=owner,source,observe;self.blob=owner.blob if blob is None else blob;self.epoch=0;self.observations=[]
    def capture(self,phase,command):
        spec={'source':self.source,'epoch':self.epoch,'phase':phase,'original_arguments':list(command)}
        if self.observe is not None:value=self.owner.perform('self-security-worktree-'+phase,spec,self.observe)
        else:
            ok,value=self.owner.outcome('self-security-worktree-'+phase,spec,'json')
            if not ok:raise IntegrityError('self_security_worktree_capture_incomplete')
        if type(value) is not dict or set(value)!=set(FILES):raise IntegrityError('self_security_worktree_file_set_changed')
        for name,row in value.items():
            if type(row) is not dict or set(row)!={'metadata','snapshot'}:raise IntegrityError('self_security_worktree_snapshot_fields_changed')
            info=metadata(row['metadata']);node=row['snapshot'];snapshot(node,self.blob,max_file=8*1024**2)
            if info['kind']!=node['kind'] and not (info['kind']=='missing' and node['kind']=='unreachable'):raise IntegrityError('self_security_worktree_kind_changed')
            if info['kind']!='missing' and (info['mode']!=node['mode'] or info['identity']!=node['identity']):raise IntegrityError('self_security_worktree_identity_changed')
            if info['kind']=='file' and info['bytes']!=node['content']['bytes']:raise IntegrityError('self_security_worktree_content_size_changed')
        self.observations.append({'specification':spec,'snapshots':value});return value
    def before(self,command):
        values=self.capture('before',command)
        for name,row in values.items():
            path=str(P(self.source)/name)
            if path in self.owner.metadata and self.owner.metadata[path]!=row['metadata']:raise IntegrityError('self_security_input_changed_before_native_git')
    def after(self,command):
        values=self.capture('after',command);self.epoch+=1
        # Only this closed three-file IO namespace uses these caches. A new
        # epoch follows an explicitly admitted native Git worktree operation.
        self.owner.metadata.clear();self.owner.members.clear()
        if hasattr(self.owner,'data'):self.owner.data.observed.clear()
        if hasattr(self.owner,'reads'):self.owner.reads.clear()
        self.owner.output.observed.clear();self.owner.output.anchors.clear()
        for name,row in values.items():self.owner.metadata[str(P(self.source)/name)]=row['metadata']


class EpochPublisherProcess:
    def __init__(self,process,epochs):self.process,self.epochs=process,epochs
    @property
    def calls(self):return self.process.calls
    @property
    def observations(self):return self.process.observations
    def run(self,command,**options):
        transition=changes_worktree(list(command))
        if transition:self.epochs.before(list(command))
        try:value=self.process.run(command,**options)
        except (RetainedOutputError,UnicodeError):
            if transition:self.epochs.after(list(command))
            raise
        if transition:self.epochs.after(list(command))
        return value


class ReplaySelfSecurityIO(ReplayRunIO):
    def __init__(self,*args,source,**kwargs):self.source=source;super().__init__(*args,**kwargs)
    def read(self,path,label):selected(self.source,path);return super().read(path,label)
    def mkdir(self,path,mode,parents,exist_ok,label):selected(self.source,path,True);return super().mkdir(path,mode,parents,exist_ok,label)
    def write_bytes(self,path,raw,label):selected(self.source,path,True);return super().write_bytes(path,raw,label)
