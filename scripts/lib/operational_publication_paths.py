"""Logical publisher selection and caller-selected CI append paths; no native effects."""
from pathlib import PurePosixPath
from lib.synthetic_lifecycle_context import LifecyclePaths,LifecyclePath
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from lib.requirement_review_output import RetainedOutputError,snapshot
from lib.workbook_import_io import READ_ERRORS
from lib.operational_publication_process import same,raw_blob

class PublisherPaths(LifecyclePaths):
    def __init__(self,source,cwd,io_port,publication_io):super().__init__(source,cwd,io_port);self.publication_io=publication_io
    def path(self,value):
        if isinstance(value,LifecyclePath):
            if value.namespace is not self:raise InputAdmissionError('publisher_foreign_path')
            value=value.value
        return PublisherPath(self,PurePosixPath(value))
class PublisherPath(LifecyclePath):
    def __truediv__(self,value):return self.namespace.path(super().__truediv__(value))
    @property
    def parent(self):return self.namespace.path(super().parent)
    @property
    def parents(self):return tuple(self.namespace.path(v) for v in super().parents)
    def is_symlink(self):return self.namespace.publication_io.is_symlink(self.namespace.absolute(self.value),str(self))
    def open(self,mode='r',encoding=None,errors=None):
        if mode=='a' and encoding=='utf-8' and errors is None:return self.namespace.publication_io.append(self.namespace.absolute(self.value),str(self))
        return super().open(mode,encoding,errors)

def failure(wire):
    if type(wire) is not dict or set(wire)!={'type','message','errno','strerror','filename'} or wire['type'] not in READ_ERRORS or type(wire['errno']) is not int or type(wire['strerror']) is not str or wire['filename'] is not None and type(wire['filename']) is not str:raise IntegrityError('publisher_append_error_changed')
    error=READ_ERRORS[wire['type']](wire['errno'],wire['strerror'],wire['filename'])
    if str(error)!=wire['message']:raise IntegrityError('publisher_append_error_diagnostic_changed')
    return RetainedOutputError(wire['type'],wire['message'])

def probe_value(wire,spec):
    if type(wire) is not dict or set(wire)!={'specification','before','after','result','error'} or not same(wire['specification'],spec) or not same(wire['before'],wire['after']):raise IntegrityError('publisher_symlink_observation_changed')
    info=wire['before']
    if type(info) is not dict or info.get('kind') not in ('missing','file','directory','symlink','other'):raise IntegrityError('publisher_symlink_state_changed')
    if info['kind']=='missing':
        if set(info)!={'kind'}:raise IntegrityError('publisher_missing_probe_changed')
    elif (set(info)!={'kind','identity','mode','uid','nlink','bytes','mtime_ns','ctime_ns','link'} or type(info['identity']) is not list or len(info['identity'])!=2 or any(type(v) is not int or v<0 for v in info['identity']) or any(type(info[k]) is not int for k in ('mode','uid','nlink','bytes','mtime_ns','ctime_ns')) or any(info[k]<0 for k in ('mode','uid','nlink','bytes')) or info['mode']>0o7777 or (type(info['link']) is not str if info['kind']=='symlink' else info['link'] is not None)):raise IntegrityError('publisher_symlink_metadata_changed')
    if wire['error'] is not None:raise failure(wire['error'])
    if type(wire['result']) is not bool or wire['result']!=(info['kind']=='symlink'):raise IntegrityError('publisher_symlink_result_changed')
    return wire['result']

class ReplayPublisherPaths:
    def __init__(self,owner,*,source,outputs):self.owner,self.source,self.outputs=owner,source,set(outputs);self.appends=[]
    def is_symlink(self,path,label):
        spec={'path':path,'label':label};ok,wire=self.owner.outcome('publisher-symlink-probe',spec,'json')
        if not ok:raise IntegrityError('publisher_probe_incomplete')
        return probe_value(wire,spec)
    def append(self,path,label):
        if path not in self.outputs:raise IntegrityError('publisher_output_not_selected')
        return ReplayAppend(self,path,label)

class ReplayAppend:
    def __init__(self,paths,path,label):self.paths,self.owner,self.path,self.label=paths,paths.owner,path,label;self.before=None;self.pending=b'';self.opened=False;self.closed=False;self.write_failed=False
    def operation(self,kind,text=None):
        args={'path':self.path,'label':self.label,'encoding':'utf-8','mode':'a','text':text}
        ok,wire=self.owner.outcome('publisher-append-'+kind,args,'json')
        if not ok:raise IntegrityError('publisher_append_capture_incomplete')
        return self.decode(kind,args,wire,text)
    def decode(self,kind,args,wire,text=None):
        if type(wire) is not dict or set(wire)!={'specification','before','after','return_value','error'} or not same(wire['specification'],args):raise IntegrityError('publisher_append_operation_changed')
        before,after=wire['before'],wire['after'];snapshot(before,self.owner.blob);snapshot(after,self.owner.blob)
        if self.before is not None and not same(before,self.before):raise IntegrityError('publisher_append_preimage_changed')
        def raw(info):return self.owner.blob(info['content']) if info['kind']=='file' else b''
        if kind=='open':
            if self.opened or self.closed or wire['return_value'] is not None:raise IntegrityError('publisher_append_open_changed')
            if wire['error'] is not None and not same(before,after):raise IntegrityError('publisher_failed_open_effect_changed')
            if wire['error'] is None:
                if after['kind']!='file' or before['kind'] not in ('missing','file') or before['kind']=='file' and not same(before,after) or before['kind']=='missing' and raw(after):raise IntegrityError('publisher_append_open_effect_changed')
                self.original=raw(after);self.opened=True
        else:
            if not self.opened or self.closed or before['kind']!='file' or after['kind']!='file' or before['identity']!=after['identity'] or before['mode']!=after['mode']:raise IntegrityError('publisher_append_file_replaced')
            if kind=='write':
                if type(text) is not str or len(text)>1024**2:raise IntegrityError('publisher_append_text_changed')
                try:encoded=text.encode('utf-8')
                except UnicodeEncodeError as error:
                    expected={'type':'UnicodeEncodeError','message':str(error),'encoding':error.encoding,'object':error.object,'start':error.start,'end':error.end,'reason':error.reason}
                    if not same(wire['error'],expected) or wire['return_value'] is not None or not same(before,after):raise IntegrityError('publisher_append_encoding_error_changed')
                    self.before=after;self.paths.appends.append({'operation':kind,'path':self.path,'before':before,'after':after,'return_value':None,'error':wire['error']});raise
                if len(encoded)>1024**2:raise IntegrityError('publisher_append_text_byte_budget')
                proposed=self.original+self.pending+encoded
                if wire['error'] is None:
                    if type(wire['return_value']) is not int or wire['return_value']!=len(text):raise IntegrityError('publisher_append_return_changed')
                    self.pending+=encoded
                elif wire['return_value'] is not None:raise IntegrityError('publisher_failed_append_return_changed')
                else:self.pending+=encoded;self.write_failed=True
                physical=raw(after)
                if not proposed.startswith(physical) or not physical.startswith(raw(before)):raise IntegrityError('publisher_append_write_prefix_changed')
            elif kind=='close':
                if wire['return_value'] is not None:raise IntegrityError('publisher_append_close_result_changed')
                proposed=self.original+self.pending;physical=raw(after)
                if wire['error'] is None and not self.write_failed and physical!=proposed or (wire['error'] is not None or self.write_failed) and (not proposed.startswith(physical) or not physical.startswith(raw(before))):raise IntegrityError('publisher_append_close_effect_changed')
                self.closed=True
            else:raise IntegrityError('publisher_append_kind_changed')
        self.before=after;self.paths.appends.append({'operation':kind,'path':self.path,'before':before,'after':after,'return_value':wire['return_value'],'error':wire['error']})
        if wire['error'] is not None:raise failure(wire['error'])
        return wire['return_value']
    def __enter__(self):self.operation('open');return self
    def write(self,text):return self.operation('write',text)
    def __exit__(self,*args):self.operation('close');return False
