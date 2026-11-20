"""Owned renderer file ports reuse the established finite file observation wire."""
import errno
from pathlib import Path

from lib.providers.workbook_import_io import (Capture as FileCapture,Data as FileData,
    Output as FileOutput,admitted)
from lib.providers.sbom_export_storage import MAX_EVENTS
from lib.requirement_validation_budget import InputAdmissionError
from lib.validation_files import MAX_FILE,MAX_TOTAL
from lib.document_rendering_io import Gate,output_read_matches,known_read_failure,projected_mkdir_obstacle,projected_mkdir_failure


class BoundedCapture:
    def reserve(self):
        if self.record.sequence>=MAX_EVENTS-8:
            self.record.capture_incomplete=True
            raise InputAdmissionError('document_record_event_budget')
    def append(self,value):self.reserve();return FileCapture.append(self,value)
    def perform(self,*args,**kwargs):self.reserve();return FileCapture.perform(self,*args,**kwargs)


class Data(BoundedCapture,FileData):
    def __init__(self,record,output,private_state):
        super().__init__(record);self.output=output;self.private_state=Path(private_state);self.read_versions={}
    def read(self,path,label):
        spec={'path':path,'label':label};admitted(spec)
        if Path(path).is_relative_to(self.private_state):raise InputAdmissionError('document_private_input_forbidden')
        if self.output.mode=='private-candidate' and path in self.output.projected:
            value=self.output.projected[path]
            def effect():
                if value['kind']=='file':
                    raw=self.output.projected_raw[path];self.total+=len(raw)
                    if len(raw)>MAX_FILE or self.total>MAX_TOTAL:raise InputAdmissionError('document_projected_input_byte_budget')
                    return raw
                if value['kind']=='missing':raise FileNotFoundError(errno.ENOENT,'No such file or directory',label)
                raise IsADirectoryError(errno.EISDIR,'Is a directory',label)
            return self.perform('document-projected-read',{'selection':spec,'projection':value},effect,encoding='bytes')
        version=self.output.versions.get(path,0)
        if version>self.read_versions.get(path,0):self.observed.pop(path,None)
        self.selected=[spec]
        try:raw=super().read(path,label)
        except OSError as error:
            if not known_read_failure(error,self.output.observed.get(path)):raise InputAdmissionError('document_input_after_own_export_changed') from error
            raise
        if path in self.output.observed and not output_read_matches(raw,self.observed[path][1],self.output.observed[path]):raise InputAdmissionError('document_input_after_own_export_changed')
        self.read_versions[path]=version;return raw


class Output(BoundedCapture,FileOutput):
    def __init__(self,record,mode,source_root,private_state,product_root=None):
        super().__init__(record,mode);self.gate=Gate(source_root);self.source_root=Path(source_root)
        self.private_state=Path(private_state);self.product_root=None if product_root is None else Path(product_root)
        self.projected={};self.projected_raw={};self.versions={};self.tool_files={}
    def expected(self,kind,path,label):
        admitted({'path':path,'label':label})
        if Path(path).is_relative_to(self.private_state):raise InputAdmissionError('document_private_export_forbidden')
        if self.mode=='selected-files' and self.product_root is not None and Path(path).is_relative_to(self.product_root):raise InputAdmissionError('document_product_export_forbidden')
        self.gate.output(kind,path,label)
    def mkdir(self,path,mode,parents,exist_ok,label):
        obstacle=projected_mkdir_obstacle(self.projected,path) if self.mode=='private-candidate' else None
        if obstacle is None:return super().mkdir(path,mode,parents,exist_ok,label)
        self.expected('mkdir',path,label)
        if (mode,parents,exist_ok)!=(0o777,True,True):raise InputAdmissionError('document_original_mkdir_required')
        name,kind=obstacle;arguments={'path':path,'label':label,'mode':mode,'parents':parents,'exist_ok':exist_ok,'obstacle':{'path':name,'state':self.projected[name]}}
        def effect():raise projected_mkdir_failure(kind,label)
        return self.perform('document-projected-mkdir',arguments,effect)
    def write_text(self,path,data,encoding,label):
        try:
            value=super().write_text(path,data,encoding,label)
            self.projected[path]={'kind':'file','content':self.files[path]};self.projected_raw[path]=data.encode(encoding)
            return value
        finally:
            if path in self.observed:self.versions[path]=self.versions.get(path,0)+1
