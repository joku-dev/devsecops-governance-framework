"""Ordered owned native lifecycle outputs with complete preimages and progress.

This adapter executes only explicit selected-files effects. Private projection
has its own contract and must never be represented by a successful native write.
"""
import errno,io,os,stat
from pathlib import Path,PurePosixPath

from lib.providers.workbook_import_io import Anchor,original_error,failure_value
from lib.requirement_review_output import text_bytes
from lib.requirement_validation_budget import InputAdmissionError
from lib.validation_files import MAX_FILE,MAX_TOTAL
from lib.workbook_import_io import ancestor_paths


class NativeOutput:
 def __init__(self,owner):
  self.io=owner;self.observed={};self.anchors={};self.total=0;self.operations=0
 def admit(self,path,label):
  spec=self.io.check(path,label,write=True)
  if self.io.mode!='selected-files':raise InputAdmissionError('synthetic_lifecycle_private_projection_not_implemented')
  self.operations+=1
  if self.operations>256:raise InputAdmissionError('synthetic_lifecycle_output_operation_budget')
  return spec
 def anchor(self,path):
  current=Path(path).parent
  for _ in range(101):
   try:value=current.lstat()
   except (FileNotFoundError,NotADirectoryError):pass
   except OSError as error:raise InputAdmissionError('synthetic_lifecycle_output_anchor_unavailable') from error
   else:
    if stat.S_ISLNK(value.st_mode):raise InputAdmissionError('synthetic_lifecycle_output_alias_forbidden')
    if stat.S_ISDIR(value.st_mode):break
   if current.parent==current:raise InputAdmissionError('synthetic_lifecycle_output_anchor_missing')
   current=current.parent
  else:raise InputAdmissionError('synthetic_lifecycle_output_depth_budget')
  anchor=Anchor(self.io.record,current);frame=anchor.frame;name=frame['path']
  if name in self.anchors and self.anchors[name]!=frame['snapshot']:raise InputAdmissionError('synthetic_lifecycle_output_anchor_replaced')
  if name in self.observed and self.observed[name]!=frame['snapshot']:raise InputAdmissionError('synthetic_lifecycle_output_anchor_changed')
  if name in self.io.metadata and self.io.entry(name)!=self.io.metadata[name]:raise InputAdmissionError('synthetic_lifecycle_input_anchor_changed_before_output')
  self.anchors[name]=frame['snapshot'];return anchor
 def prior(self,path,value):
  if path in self.observed and self.observed[path]!=value:raise InputAdmissionError('synthetic_lifecycle_output_changed_between_effects')
  if path in self.io.metadata and self.io.entry(path)!=self.io.metadata[path]:raise InputAdmissionError('synthetic_lifecycle_input_changed_before_output')
  self.observed[path]=value
 def invalidate(self,paths,*,parents=False):
  names=set(paths)
  if parents:
   for path in paths:names.add(str(PurePosixPath(path).parent))
  for name in names:
   self.io.metadata.pop(name,None);self.io.members.pop(name,None);self.io.data.observed.pop(name,None)
 def mkdir_one(self,anchor,parts,mode):
  with anchor.root_fd() as root:
   with anchor.parent(root,parts[:-1]) as parent:os.mkdir(parts[-1],mode,dir_fd=parent)
 def mkdir(self,path,mode,parents,exist_ok,label):
  spec=self.admit(path,label)
  if (type(mode) is not int or not 0<=mode<=0o777 or type(parents) is not bool or type(exist_ok) is not bool):raise InputAdmissionError('synthetic_lifecycle_mkdir_options_not_admitted')
  anchor=self.anchor(path);paths=ancestor_paths(str(anchor.root),path)
  if len(paths)>100:raise InputAdmissionError('synthetic_lifecycle_output_depth_budget')
  before={name:anchor.snapshot(name) for name in paths}
  for name,value in before.items():self.prior(name,value)
  self.io.append({'kind':'lifecycle-mkdir-before','selection':spec,'anchor':anchor.frame,'snapshots':before})
  created=[];failure=None
  def make(parts,local_mode,recurse,exists,display):
   try:self.mkdir_one(anchor,parts,local_mode);created.append(str(anchor.root.joinpath(*parts)))
   except FileNotFoundError as error:
    if not recurse or len(parts)<=1:raise original_error(error,display) from None
    make(parts[:-1],0o777,True,True,str(PurePosixPath(display).parent))
    make(parts,local_mode,False,exists,display)
   except OSError as error:
    if not exists or anchor.snapshot(str(anchor.root.joinpath(*parts)))['kind']!='directory':raise original_error(error,display) from None
  def effect():return make(anchor.parts(path),mode,parents,exist_ok,label)
  args={'selection':spec,'mode':mode,'parents':parents,'exist_ok':exist_ok,'export_mode':self.io.mode}
  try:return self.io.perform('lifecycle-output-mkdir',args,effect)
  except OSError as error:failure=failure_value(error);raise
  finally:
   try:
    after={name:anchor.snapshot(name) for name in paths}
    actual_created=[]
    for name in paths:
     a,z=before[name],after[name]
     if a['kind']=='missing' and z['kind']=='directory':actual_created.append(name)
     elif a!=z:raise InputAdmissionError('synthetic_lifecycle_unowned_mkdir_change')
    if actual_created!=created:raise InputAdmissionError('synthetic_lifecycle_created_directory_changed')
    self.io.append({'kind':'lifecycle-mkdir-after','selection':spec,'snapshots':after,'created':created,'failure':failure})
    self.observed.update(after);self.invalidate(created,parents=True)
    for name in created:self.io.touched[name]=after[name]
   except Exception:self.io.record.capture_incomplete=True;raise
 def write_bytes(self,path,raw,label):
  if type(raw) is not bytes:raise InputAdmissionError('synthetic_lifecycle_original_bytes_required')
  return self.write(path,raw,label,'bytes',None,None,None,None)
 def write_text(self,path,value,encoding,errors,label):
  if type(value) is not str:raise TypeError('data must be str, not '+type(value).__name__)
  # Preserve Python's resolved text encoding in the observation. The original
  # five generators use UTF-8; None retains the ordinary Python text default.
  with io.TextIOWrapper(io.BytesIO(),encoding=encoding,errors=errors) as stream:effective=stream.encoding
  try:raw=value.encode(effective,errors or 'strict');encoding_error=None
  except UnicodeEncodeError as error:raw=None;encoding_error=error
  return self.write(path,raw,label,'text',value,encoding,errors,(effective,encoding_error))
 def write_chunk(self,fd,view):return os.write(fd,view)
 def write(self,path,raw,label,kind,text,encoding,errors,text_context):
  spec=self.admit(path,label)
  text_raw=None if text is None else text_bytes(text)
  if raw is not None and len(raw)>MAX_FILE or text_raw is not None and len(text_raw)>MAX_FILE*2:raise InputAdmissionError('synthetic_lifecycle_output_byte_budget')
  text_ref=None if text_raw is None else self.io.blob(text_raw)
  self.total+=0 if raw is None else len(raw)
  if self.total>MAX_TOTAL:raise InputAdmissionError('synthetic_lifecycle_output_total_budget')
  payload=None if raw is None else self.io.blob(raw);anchor=self.anchor(path);before=anchor.snapshot(path);self.prior(path,before)
  effective=None if text_context is None else text_context[0]
  args={'selection':spec,'kind':kind,'text':text_ref,'payload':payload,'encoding':encoding,'errors':errors,'effective_encoding':effective,'export_mode':self.io.mode}
  self.io.append({'kind':'lifecycle-write-before','selection':spec,'anchor':anchor.frame,'snapshot':before,'text':text_ref,'payload':payload})
  progress={'opened':False,'opened_file':None,'truncated':False,'written_bytes':0};failure=None;ok=False
  def effect():
   parts=anchor.parts(path)
   try:
    with anchor.root_fd() as root:
     with anchor.parent(root,parts[:-1]) as parent:
      flags=os.O_WRONLY|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK
      if before['kind']=='missing':flags|=os.O_EXCL
      try:fd=os.open(parts[-1],flags,0o666,dir_fd=parent)
      except FileExistsError as error:
       if before['kind']=='missing':raise InputAdmissionError('synthetic_lifecycle_output_appeared_before_write') from error
       raise
      progress['opened']=True
      try:
       value=os.fstat(fd)
       if not stat.S_ISREG(value.st_mode) or value.st_uid!=os.geteuid() or value.st_nlink!=1 or value.st_mode&0o7022:raise InputAdmissionError('synthetic_lifecycle_owned_output_required')
       if before['kind']=='file' and ([value.st_dev,value.st_ino]!=before['identity'] or stat.S_IMODE(value.st_mode)!=before['mode']):raise InputAdmissionError('synthetic_lifecycle_output_replaced_before_write')
       progress['opened_file']={'mode':stat.S_IMODE(value.st_mode),'identity':[value.st_dev,value.st_ino]}
       os.ftruncate(fd,0);progress['truncated']=True
       if raw is None:raise text_context[1]
       view=memoryview(raw)
       while view:
        count=self.write_chunk(fd,view)
        if not 0<count<=len(view):raise InputAdmissionError('synthetic_lifecycle_invalid_native_write_count')
        progress['written_bytes']+=count;view=view[count:]
      finally:os.close(fd)
   except OSError as error:
    if progress['opened']:raise
    raise original_error(error,label) from None
   return len(text) if kind=='text' else len(raw)
  try:
   result=self.io.perform('lifecycle-output-write',args,effect);ok=True
   self.io.files[path]=payload;self.io.writes.append({'path':path,'label':label,'payload':payload});return result
  except OSError as error:failure=failure_value(error);raise
  finally:
   try:
    after=anchor.snapshot(path)
    opened=progress['opened_file']
    if opened is not None and (after['kind']!='file' or after['identity']!=opened['identity'] or after['mode']!=opened['mode']):raise InputAdmissionError('synthetic_lifecycle_open_file_changed_after_write')
    if not progress['opened'] and before!=after:raise InputAdmissionError('synthetic_lifecycle_unopened_output_changed')
    self.io.append({'kind':'lifecycle-write-after','selection':spec,'snapshot':after,'progress':progress,'failure':failure})
    self.observed[path]=after
    if progress['opened']:
     self.io.touched[path]=after;self.invalidate([path],parents=before['kind']=='missing')
    if ok and (after['kind']!='file' or after['content']!=payload):raise InputAdmissionError('synthetic_lifecycle_output_changed_after_write')
   except Exception:self.io.record.capture_incomplete=True;raise
