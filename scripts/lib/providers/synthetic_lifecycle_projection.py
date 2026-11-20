"""Read-only native preimages for an explicitly logical private candidate."""
import hashlib,io,re
from lib.providers.sbom_export_storage import read_private,MAX_BLOB
from lib.providers.synthetic_lifecycle_output import NativeOutput
from lib.synthetic_lifecycle_projection_io import ProjectionPort
from lib.requirement_validation_budget import InputAdmissionError


class CaptureProjection(ProjectionPort):
 def __init__(self,owner):
  super().__init__(owner,self.resolve);self.observer=NativeOutput(owner)
 def resolve(self,ref):
  if (type(ref) is not dict or set(ref)!={'sha256','bytes'} or type(ref['sha256']) is not str
      or re.fullmatch('[a-f0-9]{64}',ref['sha256']) is None or type(ref['bytes']) is not int or not 0<=ref['bytes']<=MAX_BLOB):raise InputAdmissionError('lifecycle_projection_blob_reference_invalid')
  raw=read_private(self.io.record.root/'blobs'/ref['sha256'],MAX_BLOB)
  if len(raw)!=ref['bytes'] or hashlib.sha256(raw).hexdigest()!=ref['sha256']:raise InputAdmissionError('lifecycle_projection_blob_changed')
  return raw
 def store(self,raw):return self.io.blob(raw)
 def emit(self,value):return self.io.append(value)
 def obtain(self,path,label):
  self.io.check(path,label,write=True);anchor=self.observer.anchor(path)
  from lib.workbook_import_io import ancestor_paths
  paths=ancestor_paths(str(anchor.root),path)
  if len(paths)>100:raise InputAdmissionError('lifecycle_projection_output_depth_budget')
  values={name:anchor.snapshot(name) for name in paths}
  for name,value in values.items():self.observer.prior(name,value)
  return anchor.frame,values
 def effective_encoding(self,encoding,errors):
  with io.TextIOWrapper(io.BytesIO(),encoding=encoding,errors=errors) as stream:return stream.encoding
 def perform(self,action,args,effect,*,encoding='json'):return self.io.perform(action,args,effect,encoding=encoding)
