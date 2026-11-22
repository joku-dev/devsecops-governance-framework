"""Pure bindings for isolated Git metadata. Recorded observations grant no authority."""
import hashlib,posixpath,re
from lib.accepted_prefix_git_context import FrozenHashArguments,frozen_files,absolute_path
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError

MAX_INDEX=32*1024**2

def fail(reason):raise IntegrityError('accepted_prefix_auxiliary_'+reason)
def require(value,reason):
    if not value:fail(reason)
def file_ref(raw):return {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
def identity(value):return type(value) is list and len(value)==2 and all(type(n) is int and n>=0 for n in value)

def planned_files(path,attributes,configuration,index,shared,filter_required):
    files=frozen_files(path,attributes,configuration,filter_required=filter_required)
    if index is not None:
        if type(index) is not bytes or len(index)>MAX_INDEX:raise InputAdmissionError('accepted_prefix_auxiliary_index_budget')
        files['index']=index
    if type(shared) is not dict or len(shared)>1:raise InputAdmissionError('accepted_prefix_auxiliary_shared_index_shape')
    for name,raw in shared.items():
        if type(name) is not str or re.fullmatch(r'sharedindex\.[a-f0-9]{40}',name) is None or type(raw) is not bytes or len(raw)>MAX_INDEX:raise InputAdmissionError('accepted_prefix_auxiliary_shared_index_binding')
        if index is None:raise InputAdmissionError('accepted_prefix_auxiliary_shared_index_without_index')
        files[name]=raw
    return files

def specification(root,path,parent,objects,files):
    FrozenHashArguments(root,parent+'/scope-pending',path)
    if not absolute_path(objects) or not absolute_path(parent):raise InputAdmissionError('accepted_prefix_auxiliary_absolute_context_required')
    return {'schema_version':1,'source_root':root,'path':path,'private_parent':parent,
        'files':{name:file_ref(raw) for name,raw in files.items()},'objects':objects}

def creation_value(wire,spec,files,blob):
    keys={'schema_version','scope_label','scope_identity','parent_identity','files','directories','file_identities','objects_link_identity','objects_identity','native_created','OS_isolation_attested'}
    require(type(wire) is dict and set(wire)==keys,'creation_shape_changed')
    require(type(wire['schema_version']) is int and wire['schema_version']==1 and wire['native_created'] is True and wire['OS_isolation_attested'] is False,'creation_flags_changed')
    label=wire['scope_label'];parent=spec['private_parent']
    require(absolute_path(label) and posixpath.dirname(label)==parent and re.fullmatch('scope-[a-f0-9]{32}',posixpath.basename(label)) is not None,'creation_label_changed')
    require(wire['files']==spec['files'] and type(wire['file_identities']) is dict and set(wire['file_identities'])==set(files),'file_selection_changed')
    require(type(wire['directories']) is dict and set(wire['directories'])=={'refs','refs/heads','info'},'directory_selection_changed')
    ids=[wire[k] for k in ('scope_identity','parent_identity','objects_link_identity','objects_identity')]+list(wire['file_identities'].values())+list(wire['directories'].values())
    require(all(identity(v) for v in ids) and len({tuple(v) for v in ids})==len(ids),'identity_changed')
    for name,raw in files.items():
        ref=wire['files'][name]
        require(type(ref) is dict and set(ref)=={'sha256','bytes'} and type(ref['bytes']) is int and ref==file_ref(raw),'file_binding_changed')
        require(blob(ref)==raw,'file_bytes_changed')
    return FrozenHashArguments(spec['source_root'],label,spec['path'])

def removal_value(wire,created):
    expected={'schema_version':1,'scope_label':created['scope_label'],'scope_identity':created['scope_identity'],
        'native_auxiliary_removed':True,'OS_isolation_attested':False}
    require(type(wire) is dict and set(wire)==set(expected) and wire==expected and type(wire['schema_version']) is int
        and identity(wire['scope_identity']) and wire['native_auxiliary_removed'] is True and wire['OS_isolation_attested'] is False,'cleanup_changed')
    return wire

class ReplayHashAuxiliary:
    def __init__(self,owner,root,path,attributes,configuration,*,index,shared,objects,private_parent,filter_required=None):
        self.owner,self.closed=owner,False
        self.files=planned_files(path,attributes,configuration,index,shared,filter_required)
        spec=specification(str(root),path,private_parent,objects,self.files)
        ok,wire=owner.outcome('accepted-prefix-hash-auxiliary-create',spec,'json');require(ok,'creation_incomplete')
        self.arguments=creation_value(wire,spec,self.files,owner.blob);self.wire=wire
    def finish(self):
        require(not self.closed,'already_closed')
        spec={key:self.wire[key] for key in ('scope_label','scope_identity')}
        ok,wire=self.owner.outcome('accepted-prefix-hash-auxiliary-remove',spec,'json');require(ok,'cleanup_incomplete')
        self.closed=True;return removal_value(wire,self.wire)
