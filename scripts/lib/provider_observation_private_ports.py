"""Whole credential-check metadata protocol; no credential payload is a read port."""
from pathlib import PurePosixPath
from types import SimpleNamespace
import errno,json,posixpath
from functools import wraps
from lib.intake_atomic_effects import original_error
from lib.provider_observation_private import PrivateCredentialCheck
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from lib.synthetic_lifecycle_io import path_spec

STAT_FIELDS=('st_mode','st_uid','st_gid','st_dev','st_ino','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
MOUNTINFO='/proc/self/mountinfo'


def require(value,reason):
    if not value:raise IntegrityError('provider_private_'+reason)


def stat_value(value):
    require(type(value) is dict and set(value)==set(STAT_FIELDS) and all(type(value[k]) is int for k in STAT_FIELDS)
        and all(value[k]>=0 for k in STAT_FIELDS if k not in ('st_mtime_ns','st_ctime_ns')),'stat_changed')
    return SimpleNamespace(**value)


def protocol_guard(method):
    @wraps(method)
    def guarded(self,*args,**kwargs):
        if self.failure is not None:raise self.failure
        try:return method(self,*args,**kwargs)
        except (IntegrityError,InputAdmissionError) as error:
            self.failure=error
            if hasattr(self,'record'):self.record.capture_incomplete=True
            raise
    return guarded


class MetadataPath:
    def __init__(self,port,value):self.port,self.value=port,PurePosixPath(value)
    def __str__(self):return str(self.value)
    def __eq__(self,other):return isinstance(other,MetadataPath) and self.port is other.port and self.value==other.value
    @property
    def name(self):return self.value.name
    @property
    def parent(self):return MetadataPath(self.port,self.value.parent)
    def is_symlink(self):return self.port.perform('is_symlink',{'selection':self.port.selection(self)})
    def stat(self):return stat_value(self.port.perform('stat',{'selection':self.port.selection(self)}))
    def resolve(self):
        value=self.port.perform('resolve',{'selection':self.port.selection(self)});require(type(value) is str and PurePosixPath(value).is_absolute(),'resolution_changed');return self.port.path(value)
    def read_text(self):
        selection=self.port.selection(self)
        if selection['path']!=MOUNTINFO:raise InputAdmissionError('provider_private_payload_read_forbidden')
        value=self.port.perform('mountinfo',{'selection':selection});require(type(value) is str and len(value)<=1024**2,'mountinfo_budget');return value


class MetadataProtocol:
    def initialize(self,context,cwd,files):
        require(type(context) is dict and set(context)=={'platform','O_RDONLY','O_NOFOLLOW'}
            and context['platform'] in ('linux','darwin') and type(context['O_RDONLY']) is int and context['O_RDONLY']==0
            and type(context['O_NOFOLLOW']) is int and context['O_NOFOLLOW']>0,'context_changed')
        self.context,self.cwd,self.targets=context,cwd,tuple(files);self.descriptors={};self.closed_snapshots={};self.successful_private_checks={};self.last_descriptor=0;self.failure=None
        self.O_RDONLY,self.O_NOFOLLOW=context['O_RDONLY'],context['O_NOFOLLOW'];self.system=SimpleNamespace(platform=context['platform']);self.environ=SimpleNamespace(get=self.environment)
        self.checker=PrivateCredentialCheck(path_factory=self.path,native=self,system=self.system)
    def path(self,value):
        if isinstance(value,MetadataPath):
            if value.port is not self:raise InputAdmissionError('provider_private_foreign_path')
            return value
        return MetadataPath(self,str(value))
    @protocol_guard
    def selection(self,value):
        label=str(value);path=posixpath.normpath(label if PurePosixPath(label).is_absolute() else self.cwd+'/'+label);spec=path_spec(path,label,self.cwd)
        if path not in {*self.targets,*(str(PurePosixPath(p).parent) for p in self.targets),MOUNTINFO}:
            raise InputAdmissionError('provider_private_metadata_scope_required')
        return spec
    @protocol_guard
    def perform(self,operation,args):
        packet=self.packet(operation,args)
        require(type(packet) is dict and set(packet)=={'value','error','post'},'packet_changed')
        if operation=='close':
            require(type(packet['post']) is dict and set(packet['post'])=={'open'} and type(packet['post']['open']) is bool,'close_observation_changed')
            if not packet['post']['open']:self.descriptors.pop(args['descriptor'],None)
        else:require(packet['post'] is None,'unexpected_post_observation')
        if packet['error'] is not None:
            require(packet['value'] is None,'failed_metadata_has_result');raise original_error(packet['error'])
        value=packet['value']
        if operation in ('is_symlink',):require(type(value) is bool,'probe_changed')
        elif operation=='geteuid':require(type(value) is int and value>=0,'euid_changed')
        elif operation=='environment':require(value is None or type(value) is str and len(value)<=8192,'credential_directory_changed')
        return value
    @protocol_guard
    def open(self,path,flags):
        spec=self.selection(path)
        require(spec['path'] in self.targets and type(flags) is int and flags==self.O_RDONLY|self.O_NOFOLLOW,'open_scope_or_flags_changed')
        token=self.perform('open',{'selection':spec,'flags':flags});require(type(token) is int and token==self.last_descriptor+1,'descriptor_token_changed');self.last_descriptor=token;self.descriptors[token]={'selection':spec,'stat':None};return token
    @protocol_guard
    def fstat(self,token):
        require(type(token) is int and token in self.descriptors,'descriptor_changed');value=self.perform('fstat',{'descriptor':token});info=stat_value(value);self.descriptors[token]['stat']=value;return info
    @protocol_guard
    def close(self,token):
        require(type(token) is int and token in self.descriptors,'descriptor_changed');row=self.descriptors[token];value=self.perform('close',{'descriptor':token});require(value is None and token not in self.descriptors,'descriptor_not_closed')
        if row['stat'] is not None:self.closed_snapshots[row['selection']['path']]=row['stat']
    def geteuid(self):return self.perform('geteuid',{})
    def environment(self,key):
        require(key=='CREDENTIALS_DIRECTORY','environment_key_changed');return self.perform('environment',{'key':key})
    @protocol_guard
    def getxattr(self,path,key):
        require(key=='system.posix_acl_access','xattr_key_changed')
        if type(path) is int:
            require(path in self.descriptors,'descriptor_changed');args={'descriptor':path,'key':key}
        else:args={'selection':self.selection(path),'key':key}
        value=self.perform('getxattr',args)
        try:raw=self.blob(value)
        except (ValueError,OSError,KeyError,TypeError):raise IntegrityError('provider_private_ACL_blob_changed') from None
        require(type(raw) is bytes and len(raw)<=4096,'ACL_byte_budget');return raw
    @protocol_guard
    def check_private_file(self,path):
        selected=self.path(path);spec=self.selection(selected)
        require(spec['path'] in self.targets,'private_check_target_changed')
        self.checker.check_private_file(selected)
        require(spec['path'] in self.closed_snapshots,'private_check_stat_missing')
        self.successful_private_checks[spec['path']]=self.closed_snapshots[spec['path']]


class ReplayPrivateMetadata(MetadataProtocol):
    def __init__(self,cursor,blob,*,cwd,files):
        self.cursor,self.blob,self.failure=cursor,blob,None;row=cursor.row();require(type(row) is dict and set(row)=={'kind','context'} and row['kind']=='provider-private-context','context_event_changed');self.initialize(row['context'],cwd,files)
    def packet(self,operation,args):
        if self.failure is not None:raise self.failure
        try:
            token=self.cursor.position;row=self.cursor.row();expected={'kind':'provider-private-intent','operation':token,'action':operation,'arguments':args}
            require(json.dumps(row,sort_keys=True,allow_nan=False)==json.dumps(expected,sort_keys=True,allow_nan=False),'intent_changed');row=self.cursor.row()
            require(type(row) is dict and set(row)=={'kind','operation','packet'} and row['kind']=='provider-private-outcome' and type(row['operation']) is int and row['operation']==token,'completion_changed');return row['packet']
        except (ValueError,TypeError) as error:
            self.failure=error if isinstance(error,IntegrityError) else IntegrityError('provider_private_event_changed');raise self.failure
