"""Finite logical private candidate filesystem; never a native write claim.

Stable owned source preimages are explicit inputs. Creation mode uses the
declared private-candidate mask, not an assumed future host umask or ACL.
"""
import errno,hashlib
from pathlib import PurePosixPath
from lib.requirement_review_output import snapshot
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from lib.validation_files import MAX_FILE,MAX_TOTAL
from lib.workbook_import_io import ancestor_paths

PRIVATE_MASK=0o077
MAX_NODES=2048
MAX_PATH_BYTES=1024**2
EMPTY={'sha256':hashlib.sha256(b'').hexdigest(),'bytes':0}


class Projection:
 def __init__(self,blob,*,max_file=MAX_FILE,max_total=MAX_TOTAL):
  self.max_file,self.max_total=max_file,max_total
  self.blob=blob;self.base={};self.nodes={};self.serial=0;self.total=0;self.read_total=0;self.changed=[]
 def load(self,frame,values,path):
  if type(frame) is not dict or set(frame)!={'path','snapshot'}:raise IntegrityError('lifecycle_projection_anchor_changed')
  root=frame['path'];snapshot(frame['snapshot'],self.blob,max_file=self.max_file)
  if frame['snapshot']['kind']!='directory':raise IntegrityError('lifecycle_projection_directory_anchor_required')
  paths=ancestor_paths(root,path)
  if len(paths)>100 or type(values) is not dict or set(values)!=set(paths):raise IntegrityError('lifecycle_projection_preimage_paths_changed')
  self.load_one(root,frame['snapshot'])
  for name in paths:self.load_one(name,values[name])
  return paths
 def load_one(self,path,value):
  snapshot(value,self.blob,max_file=self.max_file)
  if path in self.base and self.base[path]!=value:raise IntegrityError('lifecycle_projection_source_preimage_changed')
  self.base[path]=value
 def state(self,path):
  if path in self.nodes:return self.nodes[path]
  for parent in PurePosixPath(path).parents:
   name=str(parent)
   if name in self.nodes:
    return {'kind':'missing'} if self.nodes[name]['kind']=='directory' else {'kind':'unreachable','cause':'NotADirectoryError'}
  if path in self.base:return self.base[path]
  raise IntegrityError('lifecycle_projection_unobserved_path')
 def affected(self,path):return path in self.nodes or any(str(parent) in self.nodes for parent in PurePosixPath(path).parents)
 def has_children(self,path):return any(str(PurePosixPath(name).parent)==path for name in self.nodes)
 def put(self,path,value):
  if path not in self.nodes:
   if len(self.nodes)>=MAX_NODES or sum(len(n.encode()) for n in self.nodes)+len(path.encode())>MAX_PATH_BYTES:raise InputAdmissionError('lifecycle_projection_namespace_budget')
  self.nodes[path]=value
  if path not in self.changed:self.changed.append(path)
 def fresh(self,kind,mode,content=None):
  self.serial+=1;value={'kind':kind,'mode':mode,'identity':[0,self.serial]}
  if kind=='file':value['content']=content
  return value
 @staticmethod
 def fail(code,label):raise OSError(code,{errno.ENOENT:'No such file or directory',errno.ENOTDIR:'Not a directory',errno.EISDIR:'Is a directory',errno.EEXIST:'File exists',errno.EACCES:'Permission denied'}[code],label)
 def parent(self,path,label,*,write=False):
  parent=self.state(str(PurePosixPath(path).parent));kind=parent['kind']
  if kind=='unreachable' or kind=='file':self.fail(errno.ENOTDIR,label)
  if kind=='missing':self.fail(errno.ENOENT,label)
  if not parent['mode']&0o100 or write and not parent['mode']&0o200:self.fail(errno.EACCES,label)
 def mkdir(self,path,mode,parents,exist_ok,label):
  self.changed=[]
  def make(name,bits,recurse,exists,display):
   try:
    value=self.state(name);self.parent(name,display)
    if value['kind']!='missing':self.fail(errno.EEXIST,display)
    self.parent(name,display,write=True);self.put(name,self.fresh('directory',bits&~PRIVATE_MASK))
   except FileNotFoundError:
    if not recurse:raise
    parent=str(PurePosixPath(name).parent)
    if parent==name:raise
    make(parent,0o777,True,True,str(PurePosixPath(display).parent));make(name,bits,False,exists,display)
   except OSError:
    if not exists or self.state(name)['kind']!='directory':raise
  return make(path,mode,parents,exist_ok,label)
 def write(self,path,raw,payload,label,encoding_error=None):
  self.changed=[];self.parent(path,label);before=self.state(path)
  if before['kind']=='unreachable':self.fail(errno.ENOTDIR,label)
  if before['kind']=='directory':self.fail(errno.EISDIR,label)
  if before['kind']=='missing':
   self.parent(path,label,write=True);value=self.fresh('file',0o666&~PRIVATE_MASK,EMPTY)
  else:
   if not before['mode']&0o200:self.fail(errno.EACCES,label)
   value={**before,'content':EMPTY}
  self.put(path,value)
  if encoding_error is not None:raise encoding_error
  if type(raw) is not bytes or len(raw)>self.max_file:raise InputAdmissionError('lifecycle_projection_output_byte_budget')
  self.total+=len(raw)
  if self.total>self.max_total:raise InputAdmissionError('lifecycle_projection_output_total_budget')
  self.put(path,{**value,'content':payload})
 def read(self,path,label):
  self.parent(path,label);value=self.state(path)
  if value['kind']=='missing':self.fail(errno.ENOENT,label)
  if value['kind']=='unreachable':self.fail(errno.ENOTDIR,label)
  if value['kind']=='directory':self.fail(errno.EISDIR,label)
  if not value['mode']&0o400:self.fail(errno.EACCES,label)
  raw=self.blob(value['content']);self.read_total+=len(raw)
  if len(raw)>self.max_file or self.read_total>self.max_total:raise InputAdmissionError('lifecycle_projection_read_byte_budget')
  return raw
 def probe(self,path,kind):
  value=self.state(path)
  if kind not in ('exists','is_file','is_dir','is_symlink'):raise IntegrityError('lifecycle_projection_probe_changed')
  return value['kind'] in ('file','directory') if kind=='exists' else value['kind']=='file' if kind=='is_file' else value['kind']=='directory' if kind=='is_dir' else False
 def entries(self,path,label,base=None):
  value=self.state(path)
  if value['kind']=='missing':self.fail(errno.ENOENT,label)
  if value['kind']!='directory':self.fail(errno.ENOTDIR,label)
  if value['mode']&0o500!=0o500:self.fail(errno.EACCES,label)
  names=[] if base is None else list(base)
  for name in self.nodes:
   if str(PurePosixPath(name).parent)==path and PurePosixPath(name).name not in names:names.append(PurePosixPath(name).name)
  if len(names)>10000:raise InputAdmissionError('lifecycle_projection_membership_budget')
  return names
