"""Owned native TemporaryDirectory creation and observed original cleanup.

The selected parent is canonical, explicit environment input. Ownership and
ordinary stable contents are additional technical capture conditions. They do
not claim isolation from a hostile process running with the same OS identity.
"""
import hashlib,os,stat,tempfile
from pathlib import Path
from lib.providers.operations_files import held_root
from lib.providers.validation_worktree import signature
from lib.providers.workbook_import_io import ordinary_ancestors,failure_value
from lib.providers.sbom_export_storage import read_private
from lib.requirement_validation_budget import InputAdmissionError
from lib.pilot_run_temporary import (MAX_NODES,MAX_CAPTURE,creation,cleanup,owned_before,incoming)
from lib.validation_files import MAX_FILE

_QUARANTINED_TEMPORARIES=[]

def directory(value):
    if not stat.S_ISDIR(value.st_mode) or value.st_uid!=os.geteuid() or value.st_mode&0o7022:
        raise InputAdmissionError('pilot_run_temporary_owned_directory_required')
    return {'kind':'directory','mode':stat.S_IMODE(value.st_mode),'identity':[value.st_dev,value.st_ino]}

class NativeTemporaryFactory:
    def __init__(self,owner,parent=None):
        self.owner=owner
        self.parent=str(Path(tempfile.gettempdir()).resolve()) if parent is None else str(parent)
    def TemporaryDirectory(self):return NativeTemporary(self.owner,self.parent)

class NativeTemporary:
    def __init__(self,owner,parent):
        if owner.mode!='selected-files':raise InputAdmissionError('pilot_run_temporary_native_mode_required')
        self.owner,self.resource,self.done=owner,None,False
        owner.pilot_temporary_sessions=getattr(owner,'pilot_temporary_sessions',[]);owner.pilot_temporary_sessions.append(self)
        self.path=self.root=None
        def effect():
            owner.check(parent,parent,write=True)
            try:ordinary_ancestors(Path(parent))
            except OSError as error:raise InputAdmissionError('pilot_run_temporary_parent_not_admitted') from error
            try:self.resource=self.create_resource(parent)
            except OSError as error:return {'path':None,'snapshot':None,'failure':failure_value(error)}
            self.path=str(self.resource.name);owner.check(self.path,self.path,write=True)
            with held_root(self.path) as descriptor:state=directory(os.fstat(descriptor))
            return {'path':self.path,'snapshot':state,'failure':None}
        try:
            wire=owner.perform('pilot-run-temporary-create',{'parent':parent},effect)
            self.path=creation(self.view(),parent,wire);self.root=wire['snapshot']
        except Exception:
            if self.resource is not None:self.quarantine()
            raise
    def create_resource(self,parent):return tempfile.TemporaryDirectory(dir=parent)
    def view(self):
        actual=self.owner
        class View:
            def __init__(self):self.__dict__.update(actual.__dict__)
            def blob(self,ref):
                raw=read_private(actual.record.blobs/ref['sha256'],MAX_FILE)
                if len(raw)!=ref['bytes'] or hashlib.sha256(raw).hexdigest()!=ref['sha256']:raise InputAdmissionError('pilot_run_temporary_blob_changed')
                return raw
        return View()
    def quarantine(self):
        if self.resource is not None:
            self.resource._finalizer.detach()
            if not any(value is self.resource for value in _QUARANTINED_TEMPORARIES):_QUARANTINED_TEMPORARIES.append(self.resource)
    def guard(self,descriptor):
        if directory(os.fstat(descriptor))!=self.root:raise InputAdmissionError('pilot_run_temporary_root_replaced')
    def observe(self,*,missing=False,known=None):
        values={};total=0
        if missing:
            try:os.lstat(self.path)
            except FileNotFoundError:return {name:{'kind':'missing'} for name in known}
        ordinary_ancestors(Path(self.path).parent)
        with held_root(self.path) as root:
            self.guard(root)
            def walk(descriptor,name):
                nonlocal total
                before=os.fstat(descriptor);values[name]=directory(before)
                names=[]
                with os.scandir(descriptor) as entries:
                    for entry in entries:
                        if len(values)+len(names)>=MAX_NODES:raise InputAdmissionError('pilot_run_temporary_inventory_budget')
                        names.append(entry.name)
                names.sort()
                for part in names:
                    if not part or part in ('.','..') or '/' in part or '\\' in part or any(ord(c)<32 or 0xd800<=ord(c)<=0xdfff for c in part):raise InputAdmissionError('pilot_run_temporary_member_not_admitted')
                    if len(values)>=MAX_NODES:raise InputAdmissionError('pilot_run_temporary_inventory_budget')
                    selected=str(Path(name)/part)
                    if selected not in self.owner.touched:
                        raise InputAdmissionError('pilot_run_temporary_unowned_or_changed_child')
                    entry=os.stat(part,dir_fd=descriptor,follow_symlinks=False)
                    if entry.st_uid!=os.geteuid() or entry.st_mode&0o7022:raise InputAdmissionError('pilot_run_temporary_owned_child_required')
                    is_dir=stat.S_ISDIR(entry.st_mode)
                    if not is_dir and (not stat.S_ISREG(entry.st_mode) or entry.st_nlink!=1 or entry.st_size>MAX_FILE):raise InputAdmissionError('pilot_run_temporary_ordinary_bounded_child_required')
                    child=os.open(part,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|(os.O_DIRECTORY if is_dir else 0),dir_fd=descriptor)
                    try:
                        first=os.fstat(child)
                        if signature(entry)!=signature(first):raise InputAdmissionError('pilot_run_temporary_child_replaced')
                        if is_dir:walk(child,selected)
                        else:
                            pieces=[];size=0
                            while block:=os.read(child,min(65536,MAX_FILE+1-size)):
                                pieces.append(block);size+=len(block)
                                if size>MAX_FILE:raise InputAdmissionError('pilot_run_temporary_file_budget')
                            total+=size
                            if total>MAX_CAPTURE:raise InputAdmissionError('pilot_run_temporary_capture_budget')
                            raw=b''.join(pieces)
                            values[selected]={'kind':'file','mode':stat.S_IMODE(first.st_mode),'identity':[first.st_dev,first.st_ino],'content':self.owner.blob(raw)}
                        if signature(first)!=signature(os.fstat(child)) or signature(first)!=signature(os.stat(part,dir_fd=descriptor,follow_symlinks=False)):raise InputAdmissionError('pilot_run_temporary_child_changed_during_observation')
                    finally:os.close(child)
                if signature(before)!=signature(os.fstat(descriptor)):raise InputAdmissionError('pilot_run_temporary_directory_changed_during_observation')
            walk(root,self.path)
        if known is not None:
            if not set(values)<=set(known):raise InputAdmissionError('pilot_run_temporary_new_child_after_cleanup')
            values={name:values.get(name,{'kind':'missing'}) for name in known}
        return values
    def __enter__(self):
        value=self.owner.perform('pilot-run-temporary-enter',{'path':self.path},self.resource.__enter__)
        if value!=self.path:raise InputAdmissionError('pilot_run_temporary_enter_changed')
        return value
    def __exit__(self,kind,error,traceback):
        try:
            before=self.observe();owned_before(self.view(),self.path,self.root,before)
            self.owner.append({'kind':'pilot-run-temporary-before','path':self.path,'states':before})
            def effect():
                # held_root forbids disappearance of its binding on context
                # exit. Retain a duplicate owned descriptor after that guard
                # closes, for this explicit original scope-removal operation.
                with held_root(self.path) as root:descriptor=os.dup(root)
                try:
                    self.guard(descriptor)
                    if directory(os.stat(self.path,follow_symlinks=False))!=self.root:
                        raise InputAdmissionError('pilot_run_temporary_root_replaced')
                    self.done=True
                    try:value=self.resource.__exit__(kind,error,traceback);failure=None
                    except OSError as caught:value=None;failure=failure_value(caught)
                finally:os.close(descriptor)
                return {'states':self.observe(missing=True,known=before),'return_value':value,'failure':failure}
            wire=self.owner.perform('pilot-run-temporary-cleanup',{'path':self.path,'incoming':incoming(kind,error)},effect)
            return cleanup(self.view(),self.path,self.root,before,wire)
        except Exception:
            if not self.done:self.quarantine()
            raise
    def release(self):
        if self.resource is None:return {'scope_created':False}
        if self.done:return {'original_cleanup_attempted':True}
        self.quarantine();self.owner.record.capture_incomplete=True
        return {'original_cleanup_attempted':False,'retained_for_diagnostics':True}
