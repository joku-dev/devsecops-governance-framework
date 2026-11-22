"""Captured source-Git context, isolated hashing and complete pure read replay."""
from pathlib import Path
from lib.providers.accepted_prefix_protocol import NativeAcceptedPrefixTransport,ReplayAcceptedPrefixTransport,LegacyAcceptedPrefixProtocol
from lib.providers.accepted_prefix_metadata_protocol import NativePrefixMetadataTransport,ReplayPrefixMetadataTransport
from lib.providers.accepted_prefix_metadata import NativeGitInputs
from lib.accepted_prefix_metadata import capture_context,file_selection,ReplayGitInputs
from lib.providers.accepted_prefix_hash_scope import NativeHashAuxiliary
from lib.accepted_prefix_hash_scope import ReplayHashAuxiliary
from lib.accepted_prefix_git_context import FrozenHashArguments,absolute_path
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError

class AcceptedPrefixTransport:
    """One ordered capture cursor; replay reconstructs it without any native IO."""
    def __init__(self,owner,root,context,*,emit_stderr,environment=None):
        self.owner,self.root,self.context,self.emit_stderr=owner,str(root),context,emit_stderr
        self.native=hasattr(owner,'record');self.environment=environment
        self.port=self.new_port()
    def new_port(self,scope=None):
        if self.native:return NativeAcceptedPrefixTransport(self.owner,self.root,self.context,emit_stderr=self.emit_stderr,environment=self.environment,hash_scope=scope)
        return ReplayAcceptedPrefixTransport(self.owner,self.root,self.context,emit_stderr=self.emit_stderr,hash_scope=scope)
    def metadata_port(self,path,driver):
        if self.native:return NativePrefixMetadataTransport(self.owner,self.root,path,driver=driver,environment=self.environment)
        return ReplayPrefixMetadataTransport(self.owner,self.root,path,driver=driver)
    def incomplete(self,reason):
        if self.native:self.owner.record.capture_incomplete=True
        raise InputAdmissionError('accepted_prefix_'+reason)
    def parent_binding(self,path):
        if self.native:
            parent=str(self.owner.private_state/'state/accepted-prefix-hash')
            self.owner.append({'kind':'accepted-prefix-private-parent','source_root':self.root,'path':path,'parent':parent})
        else:
            row=self.owner.row()
            if (type(row) is not dict or set(row)!={'kind','source_root','path','parent'} or row['kind']!='accepted-prefix-private-parent'
                    or row['source_root']!=self.root or row['path']!=path or not absolute_path(row['parent'])):raise IntegrityError('accepted_prefix_private_parent_changed')
            parent=row['parent']
        FrozenHashArguments(self.root,parent+'/scope-pending',path)
        return parent
    def check_output(self,command,*,cwd,text):
        # Validate the entire original request before observing new metadata.
        spec=self.port.profile.request('git-tree',{'command':command,'cwd':str(cwd),'text':text},self.root,self.owner.cwd)
        if command[1]!='hash-object':return self.port.check_output(command,cwd=cwd,text=text)
        path=self.port.profile.hashed_path(command[3],self.root)
        try:return self.hash_output(command,path,cwd,text)
        except (InputAdmissionError,IntegrityError):
            if self.native:self.owner.record.capture_incomplete=True
            raise
        except UnicodeError:raise
        except (OSError,ValueError) as error:
            if self.native:self.owner.record.capture_incomplete=True
            raise InputAdmissionError('accepted_prefix_context_capture_incomplete') from error
    def hash_output(self,command,path,cwd,text):
        before=capture_context(self.root,path,self.metadata_port);selected=file_selection(self.root,path,before)
        inputs=NativeGitInputs(self.owner,selected) if self.native else ReplayGitInputs(self.owner,selected)
        captured={role:inputs.read(role) for role in selected}
        shared={} if not before['shared'] else {Path(before['shared']).name:captured['shared'][0]}
        parent=self.parent_binding(path)
        options={'index':captured['index'][0],'shared':shared,'objects':before['objects'],'filter_required':before['filter_required']}
        if self.native:scope=NativeHashAuxiliary(self.owner,self.root,path,before['attributes'],before['configuration'],**options)
        else:scope=ReplayHashAuxiliary(self.owner,self.root,path,before['attributes'],before['configuration'],private_parent=parent,**options)
        try:
            return self.new_port(scope.arguments).check_output(command,cwd=cwd,text=text)
        finally:
            try:
                if self.native and self.owner.record.capture_incomplete:self.incomplete('hash_capture_incomplete')
                after=capture_context(self.root,path,self.metadata_port)
                if after!=before:self.incomplete('Git_context_changed')
                if {role:inputs.read(role) for role in selected}!=captured:self.incomplete('hash_inputs_changed')
            except Exception:
                if self.native:
                    self.owner.record.capture_incomplete=True
                    # The scope closes descriptors and refuses deletion once the
                    # capture is incomplete. Preserve the original technical cause.
                    try:scope.finish()
                    except Exception:pass
                raise
            else:scope.finish()
    def run(self,command,*,cwd,capture_output):return self.port.run(command,cwd=cwd,capture_output=capture_output)
