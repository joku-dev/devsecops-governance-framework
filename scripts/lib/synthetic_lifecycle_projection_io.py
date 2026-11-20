"""Common deterministic private projection and closed retained-event replay."""
import codecs,hashlib,io
from lib.requirement_review_output import text_bytes
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from lib.synthetic_lifecycle_projection import Projection,PRIVATE_MASK,EMPTY
from lib.validation_files import MAX_FILE


class ProjectionPort:
 def __init__(self,owner,blob):
  self.io=owner;self.tree=Projection(blob);self.started=False;self.operations=0
 def selection(self,path,label):
  from lib.synthetic_lifecycle_io import path_spec
  return path_spec(path,label,self.io.cwd)
 def start(self):
  if self.started:return
  empty=self.store(b'')
  if empty!=EMPTY:raise IntegrityError('lifecycle_projection_empty_content_changed')
  self.emit({'kind':'lifecycle-private-context','creation_mask':PRIVATE_MASK,'identity_namespace':'private-projection','native_source_effects':False,'empty_content':empty})
  self.started=True
 def prepare(self,path,label):
  spec=self.selection(path,label);self.start();self.operations+=1
  if self.operations>256:raise InputAdmissionError('lifecycle_projection_output_operation_budget')
  frame,values=self.obtain(path,label)
  self.selection(frame['path'],frame['path'])
  self.emit({'kind':'lifecycle-private-preimages','selection':spec,'anchor':frame,'snapshots':values})
  return spec,self.tree.load(frame,values,path)
 def finish_output(self,spec,paths):
  states={name:self.tree.state(name) for name in paths}
  self.emit({'kind':'lifecycle-private-after','selection':spec,'states':states,'changed':list(self.tree.changed),'native_source_effects':False})
  self.io.projected_changes.update({name:self.tree.nodes[name] for name in self.tree.changed})
 def mkdir(self,path,mode,parents,exist_ok,label):
  if type(mode) is not int or not 0<=mode<=0o777 or type(parents) is not bool or type(exist_ok) is not bool:raise InputAdmissionError('lifecycle_projection_mkdir_options_not_admitted')
  spec,paths=self.prepare(path,label);self.tree.changed=[]
  args={'selection':spec,'mode':mode,'parents':parents,'exist_ok':exist_ok}
  try:return self.perform('lifecycle-private-mkdir',args,lambda:self.tree.mkdir(path,mode,parents,exist_ok,label))
  finally:self.finish_output(spec,paths)
 def write_bytes(self,path,raw,label):
  if type(raw) is not bytes:raise InputAdmissionError('lifecycle_projection_original_bytes_required')
  return self.write(path,label,raw,None,None,None)
 def write_text(self,path,value,encoding,errors,label):
  if type(value) is not str:raise TypeError('data must be str, not '+type(value).__name__)
  return self.write(path,label,None,value,encoding,errors)
 def write(self,path,label,raw,text,encoding,errors):
  spec,paths=self.prepare(path,label);text_ref=None;effective=None;encoding_error=None
  if text is not None:
   serial=text_bytes(text)
   if len(serial)>MAX_FILE*2:raise InputAdmissionError('lifecycle_projection_text_byte_budget')
   text_ref=self.store(serial);effective=self.effective_encoding(encoding,errors)
   try:raw=text.encode(effective,errors or 'strict')
   except UnicodeEncodeError as error:raw=None;encoding_error=error
  if raw is not None and len(raw)>MAX_FILE:raise InputAdmissionError('lifecycle_projection_output_byte_budget')
  payload=None if raw is None else self.store(raw);self.tree.changed=[]
  args={'selection':spec,'kind':'bytes' if text is None else 'text','text':text_ref,'payload':payload,'encoding':encoding,'errors':errors,'effective_encoding':effective}
  def effect():
   self.tree.write(path,raw,payload,label,encoding_error)
   return len(raw) if text is None else len(text)
  try:
   value=self.perform('lifecycle-private-write',args,effect)
   self.io.files[path]=payload;self.io.writes.append({'path':path,'label':label,'payload':payload});return value
  finally:self.finish_output(spec,paths)
 def read(self,path,label):
  spec=self.selection(path,label)
  return self.perform('lifecycle-private-read',{'selection':spec},lambda:self.tree.read(path,label),encoding='bytes')
 def probe(self,path,kind,label):
  spec=self.selection(path,label)
  return self.perform('lifecycle-private-probe',{'selection':spec,'probe':kind},lambda:self.tree.probe(path,kind))
 def iterdir(self,path,label,base=None):
  spec=self.selection(path,label)
  return self.perform('lifecycle-private-entries',{'selection':spec,'base_names':base},lambda:self.tree.entries(path,label,base))


class ReplayProjection(ProjectionPort):
 def __init__(self,owner):super().__init__(owner,owner.blob)
 def store(self,raw):
  ref={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}
  if self.io.blob(ref)!=raw:raise IntegrityError('lifecycle_projection_payload_changed')
  return ref
 def emit(self,value):
  if self.io.row()!=value:raise IntegrityError('lifecycle_projection_observation_changed')
 def obtain(self,path,label):
  if self.io.position>=self.io.limit:raise IntegrityError('lifecycle_projection_preimage_missing')
  row=self.io.events[self.io.position]
  if type(row) is not dict or set(row)!={'kind','selection','anchor','snapshots'} or type(row['anchor']) is not dict or set(row['anchor'])!={'path','snapshot'}:raise IntegrityError('lifecycle_projection_preimage_changed')
  return row['anchor'],row['snapshots']
 def effective_encoding(self,encoding,errors):
  if self.io.position>=self.io.limit:raise IntegrityError('lifecycle_projection_text_intent_missing')
  row=self.io.events[self.io.position]
  if type(row) is not dict or type(row.get('arguments')) is not dict:raise IntegrityError('lifecycle_projection_text_intent_changed')
  effective=row['arguments'].get('effective_encoding')
  if type(effective) is not str or not effective or len(effective)>128:raise IntegrityError('lifecycle_projection_effective_encoding_changed')
  try:
   with io.TextIOWrapper(io.BytesIO(),encoding=effective,errors=errors) as stream:resolved=stream.encoding
   if encoding is not None and codecs.lookup(encoding).name!=codecs.lookup(resolved).name:raise IntegrityError('lifecycle_projection_requested_encoding_changed')
  except (LookupError,TypeError,ValueError) as error:
   if isinstance(error,IntegrityError):raise
   raise IntegrityError('lifecycle_projection_text_codec_changed') from error
  return effective
 def perform(self,action,args,effect,*,encoding='json'):
  expected=error=None
  try:expected=effect()
  except (OSError,UnicodeError) as failure:error=failure
  ok,value=self.io.outcome(action,args,encoding)
  if error is not None:
   if ok or type(error).__name__!=value['exception'] or str(error)!=value['message']:raise IntegrityError('lifecycle_projection_failure_changed')
   raise error
  if not ok or type(expected) is not type(value) or expected!=value:raise IntegrityError('lifecycle_projection_result_changed')
  return value
