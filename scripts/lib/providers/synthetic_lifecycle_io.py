"""Lazy stable owned lifecycle inputs and explicit finite filesystem observations."""
import errno,io,os,stat
from functools import wraps
from pathlib import Path
from lib.providers.operations_files import held_root
from lib.providers.validation_worktree import signature
from lib.providers.workbook_import_io import (Capture,Data as FileData,
    ordinary_ancestors,original_error,failure_value)
from lib.providers.synthetic_lifecycle_storage import MAX_EVENTS,encode
from lib.requirement_validation_budget import InputAdmissionError
from lib.synthetic_lifecycle_io import path_spec

MAX_ENTRIES=10000
MAX_NAMES_BYTES=2*1024**2
PROBES=frozenset(('exists','is_file','is_dir','is_symlink'))


def capture_port(method):
 """Keep failures of added observation guards out of original verdicts."""
 @wraps(method)
 def guarded(self,*args,**kwargs):
  try:return method(self,*args,**kwargs)
  except InputAdmissionError:
   self.record.capture_incomplete=True;raise
  except UnicodeError:raise
  except ValueError as error:
   self.record.capture_incomplete=True
   raise InputAdmissionError('synthetic_lifecycle_observation_failed') from error
 return guarded


class Budget(Capture):
 def reserve(self):
  if self.record.sequence>=MAX_EVENTS-16:
   self.record.capture_incomplete=True;raise InputAdmissionError('synthetic_lifecycle_event_budget')
 def append(self,value):self.reserve();return super().append(value)
 def perform(self,*args,**kwargs):self.reserve();return super().perform(*args,**kwargs)


class Inputs(Budget,FileData):pass


def metadata(value):
 kind='directory' if stat.S_ISDIR(value.st_mode) else 'file' if stat.S_ISREG(value.st_mode) else 'other'
 return {'kind':kind,'mode':stat.S_IMODE(value.st_mode),'identity':[value.st_dev,value.st_ino],
     'uid':value.st_uid,'nlink':value.st_nlink,'bytes':value.st_size,
     'mtime_ns':value.st_mtime_ns,'ctime_ns':value.st_ctime_ns}


def regular_entry(value):
 if stat.S_ISLNK(value.st_mode):raise InputAdmissionError('synthetic_lifecycle_alias_not_admitted')
 if value.st_uid!=os.geteuid() or value.st_mode&0o7022:raise InputAdmissionError('synthetic_lifecycle_owned_unshared_entry_required')
 if not (stat.S_ISREG(value.st_mode) or stat.S_ISDIR(value.st_mode)):raise InputAdmissionError('synthetic_lifecycle_ordinary_entry_required')
 if stat.S_ISREG(value.st_mode) and value.st_nlink!=1:raise InputAdmissionError('synthetic_lifecycle_input_alias_not_admitted')


class NativeIO(Budget):
 """Lazy inputs and explicit selected-file outputs; no native commands."""
 def __init__(self,record,*,mode,cwd,private_state,product_root=None):
  super().__init__(record)
  if mode not in ('private-candidate','selected-files'):raise InputAdmissionError('synthetic_lifecycle_export_mode_required')
  self.mode=mode;self.cwd=cwd;self.private_state=Path(private_state);self.product_root=None if product_root is None else Path(product_root)
  self.data=Inputs(record);self.metadata={};self.members={};self.files={};self.writes=[];self.touched={};self.projected_changes={};self.projection=None
  from lib.providers.synthetic_lifecycle_output import NativeOutput
  self.output=NativeOutput(self)
  if mode=='private-candidate':
   from lib.providers.synthetic_lifecycle_projection import CaptureProjection
   self.projection=self.output=CaptureProjection(self)
 def check(self,path,label,*,write=False):
  from lib.repository_capture import private_name
  try:spec=path_spec(path,label,self.cwd)
  except ValueError as error:raise InputAdmissionError(str(error)) from error
  if private_name(path):raise InputAdmissionError('synthetic_lifecycle_private_path_not_admitted')
  if Path(path).is_relative_to(self.private_state):raise InputAdmissionError('synthetic_lifecycle_private_state_overlap')
  if write and self.mode=='selected-files' and self.product_root is not None and Path(path).is_relative_to(self.product_root):raise InputAdmissionError('synthetic_lifecycle_product_export_forbidden')
  return spec
 def remember(self,path,value):
  if path in self.metadata and self.metadata[path]!=value:raise InputAdmissionError('synthetic_lifecycle_observed_entry_changed')
  self.metadata[path]=value
 @capture_port
 def text_encoding(self,encoding,errors):
  if encoding is not None:return encoding
  with io.TextIOWrapper(io.BytesIO(),encoding=None,errors=errors) as stream:effective=stream.encoding
  self.append({'kind':'lifecycle-default-read-encoding','errors':errors,'effective_encoding':effective})
  return effective
 @capture_port
 def read(self,path,label):
  if self.projection is not None and self.projection.tree.affected(path):
   self.check(path,label);return self.projection.read(path,label)
  spec=self.check(path,label);self.append({'kind':'synthetic-lifecycle-read-binding','selection':spec})
  self.data.selected=[{'path':path,'label':path}]
  try:raw=self.data.read(path,path)
  except OSError as error:
   if path in self.metadata and self.entry(path)!=self.metadata[path]:raise InputAdmissionError('synthetic_lifecycle_input_became_unavailable') from error
   raise original_error(error,label) from None
  value=self.entry(path);info=self.data.observed[path][1]
  if value['kind']!='file' or value['identity']!=info['identity'] or value['mode']!=info['mode'] or value['bytes']!=len(raw):raise InputAdmissionError('synthetic_lifecycle_input_changed_after_read')
  self.remember(path,value);self.append({'kind':'synthetic-lifecycle-read-stability','selection':spec,'snapshot':value});return raw
 @capture_port
 def entry(self,path):
  selected=Path(path)
  try:
   ordinary_ancestors(selected.parent)
   with held_root(selected.parent) as parent:
    value=os.fstat(parent) if selected==selected.parent else os.stat(selected.name,dir_fd=parent,follow_symlinks=False)
    regular_entry(value);return metadata(value)
  except (FileNotFoundError,NotADirectoryError):return {'kind':'missing'}
 @capture_port
 def probe(self,path,kind,label):
  if self.projection is not None and self.projection.tree.affected(path):
   self.check(path,label);return self.projection.probe(path,kind,label)
  spec=self.check(path,label)
  if kind not in PROBES:raise InputAdmissionError('synthetic_lifecycle_original_probe_required')
  observed=failure=None
  def effect():
   nonlocal observed
   try:observed=self.entry(path)
   except OSError as error:raise original_error(error,label) from None
   self.remember(path,observed)
   return observed['kind']!='missing' if kind=='exists' else observed['kind']=='file' if kind=='is_file' else observed['kind']=='directory' if kind=='is_dir' else False
  try:return self.perform('synthetic-lifecycle-probe',{'selection':spec,'probe':kind},effect)
  except OSError as error:failure=failure_value(error);raise
  finally:self.append({'kind':'synthetic-lifecycle-probe-after','selection':spec,'probe':kind,'snapshot':observed,'failure':failure})
 @capture_port
 def iterdir(self,path,label):
  if self.projection is not None and self.projection.tree.affected(path):
   self.check(path,label);return self.projection.iterdir(path,label)
  names=self.native_iterdir(path,label)
  return self.projection.iterdir(path,label,names) if self.projection is not None and self.projection.tree.has_children(path) else names
 @capture_port
 def native_iterdir(self,path,label):
  spec=self.check(path,label);before=after=failure=None
  def effect():
   nonlocal before,after
   try:
    selected=Path(path);ordinary_ancestors(selected.parent)
    with held_root(selected.parent) as parent:
     value=os.stat(selected.name,dir_fd=parent,follow_symlinks=False);regular_entry(value)
     if not stat.S_ISDIR(value.st_mode):raise NotADirectoryError(errno.ENOTDIR,'Not a directory',label)
     fd=os.open(selected.name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=parent)
     try:
      actual=os.fstat(fd)
      if signature(actual)!=signature(value):raise InputAdmissionError('synthetic_lifecycle_directory_replaced')
      before=metadata(actual);names=[]
      with os.scandir(fd) as scan:
       for row in scan:
        names.append(row.name)
        if len(names)>MAX_ENTRIES:raise InputAdmissionError('synthetic_lifecycle_directory_budget')
      actual=os.fstat(fd);current=os.stat(selected.name,dir_fd=parent,follow_symlinks=False);after=metadata(actual)
      if before!=after or signature(actual)!=signature(current):raise InputAdmissionError('synthetic_lifecycle_directory_changed_during_read')
     finally:os.close(fd)
   except OSError as error:raise original_error(error,label) from None
   if len(encode({'names':names}))>MAX_NAMES_BYTES:raise InputAdmissionError('synthetic_lifecycle_membership_byte_budget')
   for name in names:
    if name in ('.','..') or Path(name).name!=name:raise InputAdmissionError('synthetic_lifecycle_child_name_invalid')
   if path in self.members and self.members[path]!=names:raise InputAdmissionError('synthetic_lifecycle_membership_changed')
   self.remember(path,before);self.members[path]=names;return names
  try:return self.perform('synthetic-lifecycle-entries',{'selection':spec},effect)
  except OSError as error:failure=failure_value(error);raise
  finally:self.append({'kind':'synthetic-lifecycle-entries-after','selection':spec,'before':before,'after':after,'failure':failure})
 @capture_port
 def mkdir(self,*args):return self.output.mkdir(*args)
 @capture_port
 def write_bytes(self,*args):return self.output.write_bytes(*args)
 @capture_port
 def write_text(self,*args):return self.output.write_text(*args)
