"""Durable complete private release verification child with native starts and replay."""
from pathlib import Path
from contextlib import contextmanager,ExitStack
import os,stat
from lib.providers.operations_files import held_root,held_ancestor
from lib.release_validation_application import ReleaseValidationContext
from lib.providers.retained_security_files import capture
from lib.provider_observation_release import report,context_valid
from lib.requirement_validation_budget import InputAdmissionError


@contextmanager
def child_directory(anchor,target):
    anchor,target=Path(anchor),Path(target)
    if not target.is_relative_to(anchor) or target==anchor or '..' in target.parts:
        raise InputAdmissionError('provider_observation_private_release_child_required')
    parts=target.relative_to(anchor).parts
    if len(parts)>8:raise InputAdmissionError('provider_observation_release_child_depth')
    with ExitStack() as stack:
        parent=stack.enter_context(held_root(anchor))
        for name in (None,*parts):
            if name is not None:
                try:os.mkdir(name,mode=0o700,dir_fd=parent)
                except FileExistsError:pass
                parent=stack.enter_context(held_ancestor(parent,name))
            info=os.fstat(parent)
            if not stat.S_ISDIR(info.st_mode) or info.st_uid!=os.geteuid() or info.st_mode&0o077:
                raise InputAdmissionError('provider_observation_private_release_child_required')
        yield


class NativeObservationRelease:
    def __init__(self,owner,source,*,instance_root,node_context):
        context_valid(str(source),node_context)
        self.owner,self.source,self.instance_root=owner,str(source),Path(instance_root);self.node_context=dict(node_context);self.failure=None
    def report(self,revision,at):
        if self.failure is not None:raise self.failure
        if self.owner.record.capture_incomplete:self.stop()
        args={'source_root':self.source,'revision':revision,'observed_at':at,'node_context':self.node_context};cache={}
        def effect():
            if Path(self.source).resolve(strict=True)!=Path(self.source):self.stop()
            if self.instance_root.is_relative_to(self.owner.record.root):self.stop()
            with child_directory(self.owner.private_state,self.instance_root):
                context=ReleaseValidationContext(self.instance_root,{'node_id':self.node_context['node_id']},product_root=self.source)
                if context.binding!={**self.node_context,'source_revision':revision}:self.stop()
                operation,value=context.create(at,source_worktree=self.source)
                if value['execution']!='complete' or value['exception_type'] is not None or value['exit_code']!=0:self.stop()
                tree=capture(context.operations/operation);files={}
                for name,raw in sorted(tree.files.items()):
                    ref=self.owner.blob(raw);cache[ref['sha256']]=raw;files[name]=ref
                return {'schema_version':1,'binding':{**context.binding,'source_tree':context.tree},'operation':operation,'label':tree.label,'directories':sorted(tree.directories),'files':files}
        try:
            value=self.owner.perform('provider-observation-release-child',args,effect)
            return report(value,lambda ref:cache[ref['sha256']],source=self.source,revision=revision,at=at,node_context=self.node_context)
        except Exception:self.stop()
    def stop(self):
        self.owner.record.capture_incomplete=True;self.failure=InputAdmissionError('provider_observation_release_child_capture_incomplete');raise self.failure from None
