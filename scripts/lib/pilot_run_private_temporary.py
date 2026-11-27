"""Finite logical temporary scope; no native directory creation or deletion claim."""
from copy import deepcopy
from pathlib import PurePosixPath as P
from lib.pilot_run_temporary import tree,incoming,require
from lib.requirement_validation_budget import InputAdmissionError
from lib.synthetic_lifecycle_projection import PRIVATE_MASK

class PrivateTemporaryFactory:
    def __init__(self,owner,parent):self.owner,self.parent,self.serial=owner,parent,0
    def candidate(self):
        self.serial+=1
        return str(P(self.parent)/('tmpaxiom-private-'+str(self.serial).zfill(8)))
    def TemporaryDirectory(self):
        for _ in range(128):
            try:return PrivateTemporary(self.owner,self.candidate())
            except FileExistsError:continue
        raise InputAdmissionError('pilot_run_private_temporary_collision_budget')

class PrivateTemporary:
    def __init__(self,owner,path):
        if owner.mode!='private-candidate' or owner.projection is None:
            raise InputAdmissionError('pilot_run_private_temporary_mode_required')
        self.owner,self.path,self.port,self.done=owner,path,owner.projection,False
        selection,paths=self.port.prepare(path,path)
        try:self.port.perform('pilot-run-private-temporary-create',{'path':path,'mode':0o700,'creation_mask':PRIVATE_MASK},lambda:self.port.tree.mkdir(path,0o700,False,False,path))
        finally:self.port.finish_output(selection,paths)
        self.root=deepcopy(self.port.tree.state(path))
        require(self.root['kind']=='directory' and self.root['mode']==0o700,'private_creation_changed')
        owner.pilot_temporary_sessions=getattr(owner,'pilot_temporary_sessions',[]);owner.pilot_temporary_sessions.append(self)
    def __enter__(self):
        return self.port.perform('pilot-run-private-temporary-enter',{'path':self.path},lambda:self.path)
    def states(self):
        values={name:self.port.tree.state(name) for name in self.port.tree.nodes if P(name).is_relative_to(P(self.path))}
        class View:
            cwd=self.owner.cwd
            blob=staticmethod(self.port.tree.blob)
        tree(View(),self.path,values)
        return values
    def remove(self,path):self.port.tree.put(path,{'kind':'missing'})
    def __exit__(self,kind,error,traceback):
        before=self.states();require(before[self.path]==self.root,'private_owned_root_changed')
        self.port.emit({'kind':'pilot-run-private-temporary-before','path':self.path,'states':before,'native_effect':False})
        model=self.port.tree;model.changed=[]
        def effect():
            self.done=True
            for name in sorted(before,key=lambda name:(len(P(name).parts),name),reverse=True):self.remove(name)
        try:return self.port.perform('pilot-run-private-temporary-cleanup',{'path':self.path,'incoming':incoming(kind,error),'native_effect':False},effect)
        finally:
            after=self.states()
            self.port.emit({'kind':'pilot-run-private-temporary-after','path':self.path,'states':after,'changed':list(model.changed),'native_effect':False})
            self.owner.projected_changes.update({name:model.nodes[name] for name in model.changed})
            for name,value in after.items():
                if value['kind']=='missing':self.owner.files.pop(name,None)
    def release(self):
        require(self.done,'unclosed_private_scope')
        return {'original_cleanup_attempted':True,'native_scope_effects':False}
