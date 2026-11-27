"""Shared DB-API facade and pure exact-primitive replay, without SQLite or path IO."""
import hashlib,json
from functools import wraps
from lib.requirement_validation_budget import InputAdmissionError
from lib.private_intake_sql_protocol import (PROFILE,MAX_ROWS,atom,scalar,statement,require,Row,error,exception_value)
from lib.requirement_validation_replay import IntegrityError
from lib.requirement_review_output import RetainedOutputError
from lib.synthetic_lifecycle_context import LifecyclePaths,LifecyclePath
from lib.private_intake_sql_files import snapshot

def admitted(method):
    @wraps(method)
    def guarded(self,*args,**kwargs):
        backend=self.backend if hasattr(self,'backend') else self.port.backend
        try:return method(self,*args,**kwargs)
        except (IntegrityError,InputAdmissionError) as caught:return backend.invalidate(caught)
    return guarded

class Paths(LifecyclePaths):
    def __init__(self,root,cwd,owner,backend):super().__init__(root,cwd,owner);self.backend=backend
    def path(self,value):
        plain=super().path(value);return Path(self,plain.value)

class Path(LifecyclePath):
    def is_symlink(self):return self.namespace.backend.root_probe(self.namespace.absolute(self.value),str(self))
    def mkdir(self,mode=0o777,parents=False,exist_ok=False):return self.namespace.backend.root_mkdir(self.namespace.absolute(self.value),mode,parents,exist_ok,str(self))

class SQLite:
    Row=Row
    def __init__(self,backend):self.backend=backend;self.serial=0;self.connections={};self.cursors={};backend.facade=self
    @admitted
    def connect(self,database,timeout=5):
        value=self.backend.call('connect',{'database':str(database),'timeout':timeout});self.serial+=1
        require(type(value) is dict and set(value)=={'connection','sqlite_version'} and value['connection']=='connection-'+str(self.serial) and value['sqlite_version']==self.backend.context['sqlite_version'],'connection_changed')
        result=Connection(self,value['connection']);self.connections[result.name]=result;return result

class Connection:
    def __init__(self,port,name):self.port,self.name,self._row_factory=port,name,None;self.closed=False
    @property
    def row_factory(self):return self._row_factory
    @row_factory.setter
    @admitted
    def row_factory(self,value):
        require(value is self.port.Row,'original_row_factory_required');result=self.port.backend.call('row-factory',{'connection':self.name,'factory':'sqlite-row'});require(result is None,'row_factory_return_changed');self._row_factory=value
    def cursor_result(self,value):
        require(type(value) is dict and set(value)=={'cursor','names','row_mode'} and value['cursor']=='cursor-'+str(len(self.port.cursors)+1) and (value['names'] is None or type(value['names']) is list and all(type(n) is str for n in value['names'])) and value['row_mode']==('mapping' if self._row_factory is self.port.Row else 'tuple'),'cursor_changed')
        result=Cursor(self.port,value);self.port.cursors[result.name]=result;return result
    @admitted
    def execute(self,sql,parameters=()):
        statement(sql);require(type(parameters) in (tuple,list) and len(parameters)<=128,'parameters_changed');args={'connection':self.name,'sql':sql,'parameters':[atom(v,self.port.backend.store) for v in parameters]};return self.cursor_result(self.port.backend.call('execute',args))
    @admitted
    def executescript(self,sql):
        statement(sql,True);return self.cursor_result(self.port.backend.call('executescript',{'connection':self.name,'sql':sql}))
    @admitted
    def __enter__(self):
        value=self.port.backend.call('enter',{'connection':self.name});require(value=={'same_connection':True} and type(value['same_connection']) is bool,'context_enter_changed');return self
    @admitted
    def __exit__(self,kind,value,tb):
        result=self.port.backend.call('exit',{'connection':self.name,'exception':exception_value(kind,value)},exception=(kind,value,tb));require(type(result) is bool,'context_exit_changed');return result
    @admitted
    def close(self):
        result=self.port.backend.call('close',{'connection':self.name});require(result is None,'close_return_changed');self.closed=True;return result

class Cursor:
    def __init__(self,port,value):self.port,self.name,self.names,self.mode=port,value['cursor'],value['names'],value['row_mode']
    def row(self,value):
        if value is None:return None
        require(type(value) is list and self.names is not None and len(value)==len(self.names),'row_shape_changed');result=[scalar(v,self.port.backend.blob) for v in value];return Row(self.names,result) if self.mode=='mapping' else tuple(result)
    @admitted
    def fetchone(self):
        value=self.port.backend.call('fetchone',{'cursor':self.name});require(type(value) is dict and set(value)=={'row'},'fetchone_changed');return self.row(value['row'])
    @admitted
    def fetchall(self):
        value=self.port.backend.call('fetchall',{'cursor':self.name});require(type(value) is dict and set(value)=={'rows'} and type(value['rows']) is list and len(value['rows'])<=MAX_ROWS,'fetchall_changed');return [self.row(v) for v in value['rows']]
    @admitted
    def __iter__(self):
        value=self.port.backend.call('iter',{'cursor':self.name});require(value=={'same_cursor':True} and type(value['same_cursor']) is bool,'iteration_changed');return self
    @admitted
    def __next__(self):
        value=self.port.backend.call('next',{'cursor':self.name});require(type(value) is dict and set(value)=={'stopped','row'} and type(value['stopped']) is bool,'next_changed')
        if value['stopped']:require(value['row'] is None,'stopped_has_row');raise StopIteration
        require(value['row'] is not None,'next_missing_row');return self.row(value['row'])

class Clock:
    def __init__(self,backend):self.backend=backend
    @admitted
    def time(self):
        result=scalar(self.backend.call('clock',{}),self.backend.blob);require(type(result) is float,'clock_type_changed');return result

def replay_admitted(method):
    @wraps(method)
    def guarded(self,*args,**kwargs):
        if self.failure is not None:raise self.failure
        try:return method(self,*args,**kwargs)
        except (IntegrityError,InputAdmissionError) as caught:return self.invalidate(caught)
    return guarded


class ReplaySQLite:
    def __init__(self,owner,*,root,cwd):
        self.owner,self.blob,self.failure=owner,owner.blob,None;self.facade=None;self.saw_connect=False;self.initial_snapshot=None;self.final_snapshot=None;self.context=owner.row();require(type(self.context) is dict and set(self.context)=={'kind','profile','root','cwd','sqlite_version'} and self.context['kind']=='private-intake-sql-context' and self.context['profile']==PROFILE and self.context['root']==root and self.context['cwd']==cwd and type(self.context['sqlite_version']) is str and 1<=len(self.context['sqlite_version'])<=128,'context_changed')
    def invalidate(self,error):
        self.failure=error;raise error
    def store(self,raw):
        if self.failure is not None:raise self.failure
        ref={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
        try:value=self.blob(ref)
        except (ValueError,KeyError,OSError,TypeError):raise IntegrityError('private_intake_sql_input_blob_unavailable') from None
        require(value==raw,'input_blob_changed');return ref
    @replay_admitted
    def root_probe(self,path,label):
        if self.failure is not None:raise self.failure
        ok,value=self.owner.outcome('private-intake-root-is-symlink',{'path':path,'label':label},'json')
        if not ok:raise RetainedOutputError(value['exception'],value['message'])
        require(type(value) is bool,'root_probe_changed');return value
    @replay_admitted
    def root_mkdir(self,path,mode,parents,exist_ok,label):
        if self.failure is not None:raise self.failure
        require(path==self.context['root'] and (mode,parents,exist_ok)==(0o700,True,True),'root_mkdir_changed')
        value=self.owner.row();require(type(value) is dict and set(value)=={'kind','direct_existing'} and value['kind']=='private-intake-root-mkdir-strategy' and type(value['direct_existing']) is bool,'root_mkdir_strategy_changed')
        if not value['direct_existing']:return self.owner.mkdir(path,mode,parents,exist_ok,label)
        ok,result=self.owner.outcome('private-intake-root-mkdir-existing',{'path':path,'label':label,'mode':mode,'parents':parents,'exist_ok':exist_ok},'json')
        if not ok:raise RetainedOutputError(result['exception'],result['message'])
        require(result is None,'root_mkdir_return_changed');return result
    def call(self,action,args,*,exception=None):
        if self.failure is not None:raise self.failure
        try:
            if action=='connect' and not self.saw_connect:
                row=self.owner.row();require(type(row) is dict and set(row)=={'kind','snapshot'} and row['kind']=='private-intake-sql-database-start','database_start_changed');self.initial_snapshot=snapshot(row['snapshot'],self.blob)
            token=self.owner.position;row=self.owner.row();expected={'kind':'private-intake-sql-intent','operation':token,'action':action,'arguments':args};require(json.dumps(row,sort_keys=True,allow_nan=False)==json.dumps(expected,sort_keys=True,allow_nan=False),'intent_changed');self.saw_connect=self.saw_connect or action=='connect';row=self.owner.row();require(type(row) is dict and set(row)=={'kind','operation','result','error'} and row['kind']=='private-intake-sql-outcome' and type(row['operation']) is int and row['operation']==token,'outcome_changed')
            if row['error'] is not None:
                require(row['result'] is None,'failed_call_has_result');raise error(row['error'])
            return row['result']
        except IntegrityError as caught:self.failure=caught;raise
    @replay_admitted
    def release_resources(self):
        if self.failure is not None:raise self.failure
        extras=[name for name,value in self.facade.connections.items() if not value.closed]
        value=self.owner.row();require(type(value) is dict and set(value)=={'kind','original_unclosed_connections','outside_original_connection_cleanup','directory_lease_released','database_snapshot'},'resource_release_fields_changed')
        expected={'kind':'private-intake-sql-released','original_unclosed_connections':extras,'outside_original_connection_cleanup':extras,'directory_lease_released':self.saw_connect,'database_snapshot':value['database_snapshot']};require(value==expected and type(value['directory_lease_released']) is bool,'resource_release_changed')
        if self.saw_connect:
            self.final_snapshot=snapshot(value['database_snapshot'],self.blob);require(self.initial_snapshot['root']==self.final_snapshot['root'],'database_root_generation_changed')
        else:require(value['database_snapshot'] is None,'unexpected_database_snapshot')
        return {k:v for k,v in expected.items() if k!='kind'}
