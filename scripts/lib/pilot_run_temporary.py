"""Closed original temporary-scope observations; pure reconstruction has no OS IO."""
from pathlib import PurePosixPath as P
from lib.requirement_review_output import snapshot, RetainedOutputError
from lib.requirement_validation_replay import IntegrityError
from lib.synthetic_lifecycle_io import path_spec
from lib.workbook_import_io import READ_ERRORS

MAX_NODES=2048
MAX_CAPTURE=25*1024**2

def require(value,reason):
    if not value:raise IntegrityError('pilot_run_temporary_'+reason)

def incoming(kind,error):
    if error is None:return {'type':None,'message':None}
    if isinstance(error,RetainedOutputError):return {'type':error.original_type,'message':error.original_message}
    return {'type':kind.__name__,'message':str(error)}

def failure(wire):
    if wire is None:return
    require(type(wire) is dict and set(wire)=={'type','message','errno','strerror','filename'},'failure_shape_changed')
    require(wire['type'] in READ_ERRORS and type(wire['message']) is str and len(wire['message'])<=65536,'failure_type_changed')
    require(type(wire['errno']) is int and type(wire['strerror']) is str and (wire['filename'] is None or type(wire['filename']) is str),'failure_fields_changed')
    error=READ_ERRORS[wire['type']](wire['errno'],wire['strerror'],wire['filename'])
    require(type(error).__name__==wire['type'] and str(error)==wire['message'],'failure_diagnostic_changed')

def creation(owner,parent,wire):
    require(type(wire) is dict and set(wire)=={'path','snapshot','failure'},'creation_shape_changed')
    failure(wire['failure'])
    if wire['failure'] is not None:
        require(wire['path'] is None and wire['snapshot'] is None,'failed_creation_path_changed')
        raise RetainedOutputError(wire['failure']['type'],wire['failure']['message'])
    path=wire['path'];path_spec(path,path,owner.cwd);path_spec(parent,parent,owner.cwd)
    require(P(path).parent==P(parent) and 4<=len(P(path).name)<=64 and P(path).name.startswith('tmp'),'creation_selection_changed')
    snapshot(wire['snapshot'],owner.blob)
    require(wire['snapshot']['kind']=='directory' and wire['snapshot']['mode']==0o700,'owned_creation_changed')
    owner.touched[path]=wire['snapshot']
    return path

def tree(owner,path,values):
    require(type(values) is dict and 1<=len(values)<=MAX_NODES and path in values,'inventory_shape_changed')
    total=0
    for name,value in values.items():
        path_spec(name,name,owner.cwd);require(P(name).is_relative_to(P(path)),'inventory_scope_changed')
        snapshot(value,owner.blob)
        if value['kind']=='file':total+=len(owner.blob(value['content']))
        require(value['kind'] in ('directory','file','missing'),'inventory_kind_changed')
        if name!=path:
            require(str(P(name).parent) in values,'inventory_parent_missing')
            parent_kind=values[str(P(name).parent)]['kind']
            require(parent_kind in ('directory','missing'),'file_parent_has_child')
            if parent_kind=='missing':require(value['kind']=='missing','missing_parent_has_child')
    require(total<=MAX_CAPTURE,'inventory_byte_budget')

def owned_before(owner,path,root,values):
    tree(owner,path,values);require(values[path]==root,'root_binding_changed')
    for name,value in values.items():
        require(value['kind']!='missing' and name in owner.touched and owner.touched[name]==value,'unowned_or_changed_child')

def cleanup(owner,path,root,before,wire):
    require(type(wire) is dict and set(wire)=={'states','failure','return_value'},'cleanup_shape_changed')
    failure(wire['failure']);after=wire['states'];owned_before(owner,path,root,before);tree(owner,path,after)
    require(set(after)==set(before),'cleanup_inventory_changed')
    require(wire['return_value'] is None,'cleanup_return_changed')
    for name,old in before.items():
        new=after[name]
        if new['kind']=='missing':continue
        require(wire['failure'] is not None,'successful_cleanup_left_entry')
        require(new['kind']==old['kind'] and new['identity']==old['identity'],'cleanup_replacement_changed')
        require(new['mode'] in (old['mode'],0o700),'cleanup_permission_change_unbound')
        if old['kind']=='file':require(new['content']==old['content'],'cleanup_file_bytes_changed')
    for name,state in after.items():
        owner.touched[name]=state
        if state['kind']=='missing':owner.files.pop(name,None)
    # Output history stays intact; only current ephemeral bindings disappear.
    for table in (getattr(owner,'metadata',{}),getattr(owner,'members',{}),getattr(owner,'reads',{}),getattr(getattr(owner,'data',None),'observed',{}),getattr(owner.output,'observed',{}),getattr(owner.output,'anchors',{})):
        for name in list(table):
            if P(name).is_relative_to(P(path)):table.pop(name,None)
    if wire['failure'] is not None:raise RetainedOutputError(wire['failure']['type'],wire['failure']['message'])
    return None

class ReplayTemporaryFactory:
    def __init__(self,owner,parent):self.owner,self.parent=owner,parent
    def TemporaryDirectory(self):return ReplayTemporary(self.owner,self.parent)

class ReplayTemporary:
    def __init__(self,owner,parent):
        require(owner.mode=='selected-files','native_replay_mode_changed');self.owner=owner;self.done=False
        ok,wire=owner.outcome('pilot-run-temporary-create',{'parent':parent},'json');require(ok,'unexpected_creation_failure_encoding')
        self.path=creation(owner,parent,wire);self.root=wire['snapshot']
        owner.pilot_temporary_sessions=getattr(owner,'pilot_temporary_sessions',[]);owner.pilot_temporary_sessions.append(self)
    def __enter__(self):
        ok,value=self.owner.outcome('pilot-run-temporary-enter',{'path':self.path},'json')
        require(ok and value==self.path,'enter_changed');return value
    def __exit__(self,kind,error,traceback):
        row=self.owner.row();require(type(row) is dict and set(row)=={'kind','path','states'} and row['kind']=='pilot-run-temporary-before' and row['path']==self.path,'cleanup_preimage_changed')
        owned_before(self.owner,self.path,self.root,row['states'])
        ok,wire=self.owner.outcome('pilot-run-temporary-cleanup',{'path':self.path,'incoming':incoming(kind,error)},'json');require(ok,'unexpected_cleanup_failure_encoding');self.done=True
        return cleanup(self.owner,self.path,self.root,row['states'],wire)
    def release(self):
        require(self.done,'unclosed_replay_scope');return {'original_cleanup_attempted':True}
