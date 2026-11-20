"""Pure validation of retained ordered native lifecycle output observations."""
import io
from pathlib import PurePosixPath

from lib.requirement_review_output import snapshot,text_bytes,RetainedOutputError
from lib.requirement_validation_replay import IntegrityError
from lib.validation_files import MAX_FILE,MAX_TOTAL
from lib.workbook_import_io import ancestor_paths,READ_ERRORS


class ReplayOutput:
 def __init__(self,owner):self.io=owner;self.observed={};self.anchors={};self.total=0;self.operations=0
 def admit(self,path,label):
  from lib.synthetic_lifecycle_io import path_spec
  spec=path_spec(path,label,self.io.cwd)
  if self.io.mode!='selected-files':raise IntegrityError('synthetic_lifecycle_native_output_mode_changed')
  self.operations+=1
  if self.operations>256:raise IntegrityError('synthetic_lifecycle_output_operation_budget')
  return spec
 def anchor(self,frame,target):
  if type(frame) is not dict or set(frame)!={'path','snapshot'}:raise IntegrityError('synthetic_lifecycle_output_anchor_changed')
  from lib.synthetic_lifecycle_io import path_spec
  path_spec(frame['path'],frame['path'],self.io.cwd);snapshot(frame['snapshot'],self.io.blob)
  if frame['snapshot']['kind']!='directory':raise IntegrityError('synthetic_lifecycle_output_anchor_kind_changed')
  name=frame['path']
  if name in self.anchors and self.anchors[name]!=frame['snapshot']:raise IntegrityError('synthetic_lifecycle_output_anchor_replaced')
  if name in self.observed and self.observed[name]!=frame['snapshot']:raise IntegrityError('synthetic_lifecycle_output_anchor_metadata_changed')
  self.anchors[name]=frame['snapshot'];paths=ancestor_paths(name,target)
  if len(paths)>100:raise IntegrityError('synthetic_lifecycle_output_depth_budget')
  return paths
 def prior(self,path,value):
  snapshot(value,self.io.blob)
  if path in self.observed and self.observed[path]!=value:raise IntegrityError('synthetic_lifecycle_output_preimage_changed')
  if path in self.io.metadata:
   known=self.io.metadata[path]
   if known['kind']!=value['kind']:raise IntegrityError('synthetic_lifecycle_input_output_kind_changed')
   if known['kind']!='missing' and (known['identity']!=value['identity'] or known['mode']!=value['mode'] or known['kind']=='file' and known['bytes']!=value['content']['bytes']):raise IntegrityError('synthetic_lifecycle_input_output_metadata_changed')
   if path in self.io.reads and known['kind']=='file' and self.io.reads[path][0]!=self.io.blob(value['content']):raise IntegrityError('synthetic_lifecycle_input_output_bytes_changed')
  self.observed[path]=value
 def invalidate(self,paths,*,parents=False):
  names=set(paths)
  if parents:
   for path in paths:names.add(str(PurePosixPath(path).parent))
  for name in names:
   self.io.metadata.pop(name,None);self.io.members.pop(name,None);self.io.reads.pop(name,None)
 def failure(self,wire,value):
  if (type(wire) is not dict or set(wire)!={'type','message','errno','strerror','filename'}
      or wire['type'] not in READ_ERRORS or type(wire['errno']) is not int or type(wire['strerror']) is not str
      or wire['filename'] is not None and type(wire['filename']) is not str):raise IntegrityError('synthetic_lifecycle_output_error_wire_changed')
  error=READ_ERRORS[wire['type']](wire['errno'],wire['strerror'],wire['filename'])
  if str(error)!=wire['message'] or wire['type']!=value['exception'] or wire['message']!=value['message']:raise IntegrityError('synthetic_lifecycle_output_error_diagnostic_changed')
 def mkdir(self,path,mode,parents,exist_ok,label):
  spec=self.admit(path,label)
  if type(mode) is not int or not 0<=mode<=0o777 or type(parents) is not bool or type(exist_ok) is not bool:raise IntegrityError('synthetic_lifecycle_mkdir_options_changed')
  before=self.io.row()
  if set(before)!={'kind','selection','anchor','snapshots'} or before['kind']!='lifecycle-mkdir-before' or before['selection']!=spec:raise IntegrityError('synthetic_lifecycle_mkdir_before_changed')
  paths=self.anchor(before['anchor'],path)
  args={'selection':spec,'mode':mode,'parents':parents,'exist_ok':exist_ok,'export_mode':self.io.mode}
  ok,value=self.io.outcome('lifecycle-output-mkdir',args,'json');after=self.io.row()
  if set(after)!={'kind','selection','snapshots','created','failure'} or after['kind']!='lifecycle-mkdir-after' or after['selection']!=spec:raise IntegrityError('synthetic_lifecycle_mkdir_after_changed')
  if any(type(row) is not dict or set(row)!=set(paths) for row in (before['snapshots'],after['snapshots'])) or type(after['created']) is not list:raise IntegrityError('synthetic_lifecycle_mkdir_paths_changed')
  created=[]
  for name in paths:
   a,z=before['snapshots'][name],after['snapshots'][name];self.prior(name,a);snapshot(z,self.io.blob)
   if name!=path and a['kind']=='directory':raise IntegrityError('synthetic_lifecycle_mkdir_anchor_not_nearest')
   if a['kind']=='missing' and z['kind']=='directory':created.append(name);self.io.touched[name]=z
   elif a!=z:raise IntegrityError('synthetic_lifecycle_mkdir_unexpected_change')
   self.observed[name]=z
  if after['created']!=created or not parents and any(name!=path for name in created):raise IntegrityError('synthetic_lifecycle_mkdir_progress_changed')
  self.invalidate(created,parents=True)
  if ok:
   if value is not None or after['failure'] is not None or after['snapshots'][path]['kind']!='directory' or before['snapshots'][path]['kind']=='directory' and not exist_ok:raise IntegrityError('synthetic_lifecycle_mkdir_result_changed')
   return None
  self.failure(after['failure'],value);raise RetainedOutputError(value['exception'],value['message'])
 def write_bytes(self,path,raw,label):
  if type(raw) is not bytes:raise IntegrityError('synthetic_lifecycle_write_bytes_changed')
  return self.write(path,raw,label,'bytes',None,None,None)
 def write_text(self,path,value,encoding,errors,label):
  if type(value) is not str:raise IntegrityError('synthetic_lifecycle_write_text_changed')
  return self.write(path,None,label,'text',value,encoding,errors)
 def write(self,path,raw,label,kind,text,encoding,errors):
  spec=self.admit(path,label);before=self.io.row()
  if set(before)!={'kind','selection','anchor','snapshot','text','payload'} or before['kind']!='lifecycle-write-before' or before['selection']!=spec:raise IntegrityError('synthetic_lifecycle_write_before_changed')
  if kind=='bytes':
   if before['text'] is not None:raise IntegrityError('synthetic_lifecycle_bytes_text_claim_changed')
  elif self.io.blob(before['text'])!=text_bytes(text):raise IntegrityError('synthetic_lifecycle_write_original_text_changed')
  # Effective text encoding is an explicit retained adapter fact. Do not ask
  # the replay node's locale to resolve a captured None encoding again.
  intent=self.io.events[self.io.position] if self.io.position<self.io.limit else {}
  if type(intent) is not dict or type(intent.get('arguments')) is not dict:raise IntegrityError('synthetic_lifecycle_write_intent_changed')
  arguments=intent['arguments']
  effective=arguments.get('effective_encoding');encoding_error=None
  if kind=='bytes':
   if effective is not None:raise IntegrityError('synthetic_lifecycle_byte_encoding_claim_changed')
  else:
   if type(effective) is not str or not effective or len(effective)>128:raise IntegrityError('synthetic_lifecycle_text_encoding_changed')
   try:
    with io.TextIOWrapper(io.BytesIO(),encoding=effective,errors=errors) as stream:resolved=stream.encoding
    if encoding is not None:
     import codecs
     if codecs.lookup(encoding).name!=codecs.lookup(resolved).name:raise IntegrityError('synthetic_lifecycle_requested_text_encoding_changed')
    try:raw=text.encode(effective,errors or 'strict')
    except UnicodeEncodeError as error:raw=None;encoding_error=error
   except (LookupError,TypeError,ValueError) as error:
    if isinstance(error,IntegrityError):raise
    raise IntegrityError('synthetic_lifecycle_encoding_not_supported') from error
  if raw is None:
   if before['payload'] is not None:raise IntegrityError('synthetic_lifecycle_failed_encoding_payload_changed')
  elif len(raw)>MAX_FILE or self.io.blob(before['payload'])!=raw:raise IntegrityError('synthetic_lifecycle_write_payload_changed')
  if text is not None and len(text_bytes(text))>MAX_FILE*2:raise IntegrityError('synthetic_lifecycle_text_byte_budget')
  self.total+=0 if raw is None else len(raw)
  if self.total>MAX_TOTAL:raise IntegrityError('synthetic_lifecycle_output_total_budget')
  self.anchor(before['anchor'],path);a=before['snapshot'];self.prior(path,a)
  args={'selection':spec,'kind':kind,'text':before['text'],'payload':before['payload'],'encoding':encoding,'errors':errors,'effective_encoding':effective,'export_mode':self.io.mode}
  ok,value=self.io.outcome('lifecycle-output-write',args,'json');after=self.io.row()
  if set(after)!={'kind','selection','snapshot','progress','failure'} or after['kind']!='lifecycle-write-after' or after['selection']!=spec:raise IntegrityError('synthetic_lifecycle_write_after_changed')
  z=after['snapshot'];snapshot(z,self.io.blob);progress=after['progress']
  if (type(progress) is not dict or set(progress)!={'opened','opened_file','truncated','written_bytes'}
      or type(progress['opened']) is not bool or type(progress['truncated']) is not bool or type(progress['written_bytes']) is not int
      or not 0<=progress['written_bytes']<=(0 if raw is None else len(raw)) or progress['truncated'] and not progress['opened']
      or progress['written_bytes'] and not progress['truncated']):raise IntegrityError('synthetic_lifecycle_write_progress_changed')
  if progress['opened']:
   if a['kind'] not in ('missing','file') or z['kind']!='file':raise IntegrityError('synthetic_lifecycle_opened_file_changed')
   opened=progress['opened_file']
   if (type(opened) is not dict or set(opened)!={'mode','identity'} or type(opened['mode']) is not int or opened['mode']!=z['mode']
       or type(opened['identity']) is not list or len(opened['identity'])!=2 or any(type(n) is not int or n<0 for n in opened['identity'])
       or opened['identity']!=z['identity']):raise IntegrityError('synthetic_lifecycle_opened_descriptor_identity_changed')
   if a['kind']=='file' and (a['identity']!=z['identity'] or a['mode']!=z['mode']):raise IntegrityError('synthetic_lifecycle_overwrite_identity_changed')
   if progress['truncated']:
    expected=b'' if raw is None else raw[:progress['written_bytes']]
    if self.io.blob(z['content'])!=expected:raise IntegrityError('synthetic_lifecycle_partial_bytes_changed')
   elif a['kind']=='file' and a!=z or a['kind']=='missing' and self.io.blob(z['content'])!=b'':raise IntegrityError('synthetic_lifecycle_untruncated_bytes_changed')
   self.io.touched[path]=z;self.invalidate([path],parents=a['kind']=='missing')
  elif a!=z or progress['opened_file'] is not None:raise IntegrityError('synthetic_lifecycle_unopened_file_changed')
  self.observed[path]=z
  if ok:
   if (after['failure'] is not None or raw is None or not progress['truncated'] or progress['written_bytes']!=len(raw)
       or type(value) is not int or value!=(len(text) if kind=='text' else len(raw))):raise IntegrityError('synthetic_lifecycle_write_result_changed')
   self.io.files[path]=before['payload'];self.io.writes.append({'path':path,'label':label,'payload':before['payload']});return value
  if value['exception']=='UnicodeEncodeError':
   if encoding_error is None or str(encoding_error)!=value['message'] or not progress['truncated'] or after['failure'] is not None:raise IntegrityError('synthetic_lifecycle_encoding_failure_changed')
  else:self.failure(after['failure'],value)
  raise RetainedOutputError(value['exception'],value['message'])
