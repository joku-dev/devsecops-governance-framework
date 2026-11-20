"""Closed lifecycle input reconstruction; no selected filesystem or programs."""
from pathlib import PurePosixPath
import codecs,json,posixpath
from lib.workbook_import_io import ReplayIO as FileReplay,READ_ERRORS,error_wire
from lib.document_rendering_io import parse_tool_json
from lib.requirement_validation_replay import IntegrityError

PROBES=frozenset(('exists','is_file','is_dir','is_symlink'))
MAX_ENTRIES=10000
MAX_NAMES_BYTES=2*1024**2


def path_spec(path,label,cwd):
 if (type(path) is not str or not path.startswith('/') or path.startswith('//')
     or posixpath.normpath(path)!=path or str(PurePosixPath(path))!=path):raise IntegrityError('synthetic_lifecycle_absolute_path_changed')
 for value in (path,label):
  if type(value) is not str or not value or len(value)>8192 or '\\' in value or any(ord(c)<32 or 0xd800<=ord(c)<=0xdfff for c in value) or str(PurePosixPath(value))!=value:raise IntegrityError('synthetic_lifecycle_path_label_changed')
 raw=PurePosixPath(label);expected=posixpath.normpath(str(raw if raw.is_absolute() else PurePosixPath(cwd)/raw))
 if expected!=path:raise IntegrityError('synthetic_lifecycle_path_context_changed')
 return {'path':path,'label':label}


def metadata(value):
 if value=={'kind':'missing'}:return value
 keys={'kind','mode','identity','uid','nlink','bytes','mtime_ns','ctime_ns'}
 if (type(value) is not dict or set(value)!=keys or value['kind'] not in ('file','directory')
     or type(value['mode']) is not int or not 0<=value['mode']<=0o777 or value['mode']&0o022
     or type(value['identity']) is not list or len(value['identity'])!=2
     or any(type(n) is not int or n<0 for n in value['identity'])
     or any(type(value[k]) is not int for k in ('uid','nlink','bytes','mtime_ns','ctime_ns'))
     or value['uid']<0 or value['nlink']<1 or value['bytes']<0 or value['kind']=='file' and value['nlink']!=1):raise IntegrityError('synthetic_lifecycle_metadata_changed')
 return value


def probe_value(value,kind):
 metadata(value)
 if kind not in PROBES:raise IntegrityError('synthetic_lifecycle_probe_changed')
 return value['kind']!='missing' if kind=='exists' else value['kind']=='file' if kind=='is_file' else value['kind']=='directory' if kind=='is_dir' else False


class ReplayIO(FileReplay):
 def __init__(self,events,blob,mode,cwd):
  super().__init__(events,blob,mode,cwd);self.metadata={};self.members={};self.projected_changes={};self.projection=None
  from lib.synthetic_lifecycle_output import ReplayOutput
  self.output=ReplayOutput(self)
  if mode=='private-candidate':
   from lib.synthetic_lifecycle_projection_io import ReplayProjection
   self.projection=self.output=ReplayProjection(self)
 def remember(self,path,value):
  metadata(value)
  if path in self.metadata and self.metadata[path]!=value:raise IntegrityError('synthetic_lifecycle_observed_metadata_changed')
  self.metadata[path]=value
 def text_encoding(self,encoding,errors):
  if encoding is not None:return encoding
  row=self.row()
  if set(row)!={'kind','errors','effective_encoding'} or row['kind']!='lifecycle-default-read-encoding' or row['errors']!=errors or type(row['effective_encoding']) is not str or not row['effective_encoding'] or len(row['effective_encoding'])>128:raise IntegrityError('lifecycle_default_read_encoding_changed')
  try:codecs.lookup(row['effective_encoding'])
  except LookupError as error:raise IntegrityError('lifecycle_default_read_codec_unknown') from error
  return row['effective_encoding']
 def outcome(self,action,arguments,encoding):
  token=self.position;intent=self.row()
  if intent!={'kind':'intent','operation':token,'action':action,'arguments':arguments}:raise IntegrityError('synthetic_lifecycle_io_intent_changed')
  row=self.row()
  if row.get('operation')!=token:raise IntegrityError('synthetic_lifecycle_io_operation_changed')
  if row.get('kind')=='failed':
   if set(row)!={'kind','operation','exception','message'} or row['exception'] not in set(READ_ERRORS)|{'UnicodeEncodeError'} or type(row['message']) is not str or len(row['message'])>65536:raise IntegrityError('synthetic_lifecycle_io_failure_changed')
   return False,row
  if set(row)!={'kind','operation','encoding','value'} or row.get('kind')!='returned' or row['encoding']!=encoding:raise IntegrityError('synthetic_lifecycle_io_return_changed')
  raw=self.blob(row['value']);return True,raw if encoding=='bytes' else parse_tool_json(raw)
 def read(self,path,label):
  if self.projection is not None and self.projection.tree.affected(path):return self.projection.read(path,label)
  spec=path_spec(path,label,self.cwd)
  if self.row()!={'kind':'synthetic-lifecycle-read-binding','selection':spec}:raise IntegrityError('synthetic_lifecycle_read_binding_changed')
  self.selected={'inputs':[{'path':path,'label':path}]}
  try:raw=super().read(path,path)
  except OSError as error:raise type(error)(error.errno,error.strerror,label) from None
  after=self.row()
  if set(after)!={'kind','selection','snapshot'} or after['kind']!='synthetic-lifecycle-read-stability' or after['selection']!=spec:raise IntegrityError('synthetic_lifecycle_read_stability_changed')
  value=metadata(after['snapshot']);info=self.reads[path][1]
  if value['kind']!='file' or value['identity']!=info['identity'] or value['mode']!=info['mode'] or value['bytes']!=len(raw):raise IntegrityError('synthetic_lifecycle_read_metadata_changed')
  self.remember(path,value);return raw
 def probe(self,path,kind,label):
  if self.projection is not None and self.projection.tree.affected(path):return self.projection.probe(path,kind,label)
  spec=path_spec(path,label,self.cwd);ok,value=self.outcome('synthetic-lifecycle-probe',{'selection':spec,'probe':kind},'json');after=self.row()
  if set(after)!={'kind','selection','probe','snapshot','failure'} or after['kind']!='synthetic-lifecycle-probe-after' or after['selection']!=spec or after['probe']!=kind:raise IntegrityError('synthetic_lifecycle_probe_observation_changed')
  if ok:
   expected=probe_value(after['snapshot'],kind)
   if after['failure'] is not None or type(value) is not bool or value!=expected:raise IntegrityError('synthetic_lifecycle_probe_result_changed')
   self.remember(path,after['snapshot']);return value
  if after['snapshot'] is not None:raise IntegrityError('synthetic_lifecycle_failed_probe_snapshot_changed')
  error=error_wire(after['failure'],label)
  if type(error).__name__!=value['exception'] or str(error)!=value['message']:raise IntegrityError('synthetic_lifecycle_probe_failure_changed')
  raise error
 def iterdir(self,path,label):
  if self.projection is not None and self.projection.tree.affected(path):return self.projection.iterdir(path,label)
  names=self.native_iterdir(path,label)
  return self.projection.iterdir(path,label,names) if self.projection is not None and self.projection.tree.has_children(path) else names
 def native_iterdir(self,path,label):
  spec=path_spec(path,label,self.cwd);ok,value=self.outcome('synthetic-lifecycle-entries',{'selection':spec},'json');after=self.row()
  if set(after)!={'kind','selection','before','after','failure'} or after['kind']!='synthetic-lifecycle-entries-after' or after['selection']!=spec:raise IntegrityError('synthetic_lifecycle_entries_observation_changed')
  if ok:
   before=metadata(after['before']);metadata(after['after'])
   if (before['kind']!='directory' or before!=after['after'] or after['failure'] is not None or type(value) is not list or len(value)>MAX_ENTRIES
       or any(type(name) is not str for name in value) or len(value)!=len(set(value))
       or len((json.dumps({'names':value},sort_keys=True,ensure_ascii=True,allow_nan=False,separators=(',',':'))+'\n').encode())>MAX_NAMES_BYTES):raise IntegrityError('synthetic_lifecycle_membership_changed')
   for name in value:
    if type(name) is not str or not name or name in ('.','..') or '/' in name or '\0' in name:raise IntegrityError('synthetic_lifecycle_child_name_changed')
   if path in self.members and self.members[path]!=value:raise IntegrityError('synthetic_lifecycle_repeated_membership_changed')
   self.remember(path,before);self.members[path]=value;return value
  if after['before'] is not None or after['after'] is not None:raise IntegrityError('synthetic_lifecycle_failed_entries_snapshot_changed')
  error=error_wire(after['failure'],label)
  if type(error).__name__!=value['exception'] or str(error)!=value['message']:raise IntegrityError('synthetic_lifecycle_entries_failure_changed')
  raise error
 def mkdir(self,*args):return self.output.mkdir(*args)
 def write_bytes(self,*args):return self.output.write_bytes(*args)
 def write_text(self,*args):return self.output.write_text(*args)
