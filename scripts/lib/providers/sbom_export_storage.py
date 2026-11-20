"""Stdlib-only private intent/outcome capture; no implicit resume or authority."""
from pathlib import Path
import hashlib,json,os,re,secrets,stat

MAX_METADATA=2*1024**2
MAX_BLOB=256*1024**2
MAX_TOTAL=1024**3
MAX_EVENTS=256
AUTHORITY={'official_acceptance':False,'production_approval':False,'authority_transferred':False,
 'independent_execution_authenticated':False,'evidence_trust':'unverified','published':False}


def encode(value):return (json.dumps(value,sort_keys=True,ensure_ascii=True,allow_nan=False,separators=(',',':'))+'\n').encode()


def document(raw):
 def unique(pairs):
  result={}
  for key,value in pairs:
   if key in result:raise ValueError('sbom_duplicate_metadata_key')
   result[key]=value
  return result
 def bad(_):raise ValueError('sbom_nonfinite_metadata')
 value=json.loads(raw,object_pairs_hook=unique,parse_constant=bad)
 if not isinstance(value,dict):raise ValueError('sbom_metadata_object_required')
 return value


def normalized(path):
 path=Path(path).expanduser().absolute()
 if any(p.is_symlink() for p in (path,*path.parents)):raise ValueError('sbom_path_symlink_forbidden')
 return Path(os.path.abspath(path))


def owned_directory(path,create=False):
 path=normalized(path)
 if create:path.mkdir(mode=0o700,parents=True,exist_ok=True)
 meta=path.stat()
 if not stat.S_ISDIR(meta.st_mode) or meta.st_uid!=os.geteuid() or meta.st_mode&0o077:
  raise ValueError('sbom_owned_private_directory_required')
 return path


def raw_new(path,raw,limit=MAX_METADATA):
 if not isinstance(raw,bytes) or len(raw)>limit:raise ValueError('sbom_record_byte_budget')
 fd=os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
 try:
  view=memoryview(raw)
  while view:
   count=os.write(fd,view)
   if count<=0:raise OSError('sbom_short_record_write')
   view=view[count:]
  os.fsync(fd)
 finally:os.close(fd)
 fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
 try:os.fsync(fd)
 finally:os.close(fd)


def read_private(path,limit=MAX_METADATA):
 path=normalized(path);fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
 try:
  before=os.fstat(fd)
  if (not stat.S_ISREG(before.st_mode) or before.st_nlink!=1 or before.st_uid!=os.geteuid()
   or before.st_mode&0o077 or before.st_size>limit):raise ValueError('sbom_private_regular_bounded_file_required')
  blocks=[];size=0
  while part:=os.read(fd,min(65536,limit+1-size)):
   blocks.append(part);size+=len(part)
   if size>limit:raise ValueError('sbom_record_byte_budget')
  after=os.fstat(fd);entry=os.stat(path,follow_symlinks=False)
  keys=('st_dev','st_ino','st_mode','st_nlink','st_size','st_mtime_ns','st_ctime_ns')
  if any(getattr(before,k)!=getattr(row,k) for row in (after,entry) for k in keys):raise ValueError('sbom_record_changed_during_read')
  return b''.join(blocks)
 finally:os.close(fd)


class Record:
 def __init__(self,state,request,source):
  state=owned_directory(state,True);self.root=state/secrets.token_hex(16);self.root.mkdir(mode=0o700)
  self.blobs=self.root/'blobs';self.blobs.mkdir(mode=0o700)
  self.events=self.root/'events';self.events.mkdir(mode=0o700)
  self.sequence=0;self.previous='0'*64;self.total=0;self.capture_incomplete=False
  raw_new(self.root/'request.json',encode(request));raw_new(self.root/'source.json',encode(source))
  self.append({'kind':'opened',**AUTHORITY})
 def append(self,value):
  if self.sequence>=MAX_EVENTS:raise ValueError('sbom_event_count_budget')
  owned_directory(self.root);owned_directory(self.events)
  row={'sequence':self.sequence,'previous':self.previous,'value':value}
  raw=encode(row);raw_new(self.events/f'{self.sequence:04}.json',raw)
  self.previous=hashlib.sha256(raw).hexdigest();self.sequence+=1
 def blob(self,raw):
  if not isinstance(raw,bytes) or len(raw)>MAX_BLOB or self.total+len(raw)>MAX_TOTAL:raise ValueError('sbom_blob_budget')
  digest=hashlib.sha256(raw).hexdigest();path=self.blobs/digest
  if path.exists():
   if read_private(path,MAX_BLOB)!=raw:raise ValueError('sbom_blob_collision')
  else:raw_new(path,raw,MAX_BLOB);self.total+=len(raw)
  return {'sha256':digest,'bytes':len(raw)}
 def perform(self,action,arguments,effect,*,encoding='json'):
  token=self.sequence;self.append({'kind':'intent','operation':token,'action':action,'arguments':arguments})
  try:
   value=effect()
  except Exception as error:
   detail=str(error)
   if len(detail)>65536:detail='sbom_native_error_message_budget'
   self.append({'kind':'failed','operation':token,'exception':type(error).__name__,'message':detail})
   raise
  try:
   if encoding=='bytes':raw=value
   else:raw=(json.dumps(value,ensure_ascii=True,allow_nan=True,separators=(',',':'))+'\n').encode()
   result=self.blob(raw)
  except Exception:
   self.capture_incomplete=True
   self.append({'kind':'capture-failed','operation':token})
   raise
  self.append({'kind':'returned','operation':token,'encoding':encoding,'value':result})
  return value
 def finish(self,state,result,files,error=None):
  value={'schema_version':1,'state':state,'result':result,'touched_files':files,
   'exception_type':None if error is None else type(error).__name__,**AUTHORITY}
  self.append({'kind':'terminal','state':state,'exit_code':None if result is None else result['exit_code']})
  value.update(event_count=self.sequence,event_tip=self.previous)
  raw_new(self.root/'result.json',encode(value))
  return value


def read_record(root):
 root=owned_directory(root)
 if {p.name for p in root.iterdir()}!={'request.json','source.json','result.json','events','blobs'}:
  raise ValueError('sbom_record_members_changed_or_pending')
 request=document(read_private(root/'request.json'));source=document(read_private(root/'source.json'));result=document(read_private(root/'result.json'))
 for directory in ('events','blobs'):owned_directory(root/directory)
 names=sorted(p.name for p in (root/'events').iterdir())
 if not names or len(names)>MAX_EVENTS or names!=[f'{i:04}.json' for i in range(len(names))]:raise ValueError('sbom_event_members_changed')
 previous='0'*64;events=[];referenced=set();total=0
 for index,name in enumerate(names):
  raw=read_private(root/'events'/name);row=document(raw)
  if set(row)!={'sequence','previous','value'} or type(row['sequence']) is not int or row['sequence']!=index or row['previous']!=previous:raise ValueError('sbom_event_chain_changed')
  previous=hashlib.sha256(raw).hexdigest();events.append(row['value'])
 def blob(value):
  nonlocal total
  if not isinstance(value,dict) or set(value)!={'sha256','bytes'} or not isinstance(value['sha256'],str) or not re.fullmatch('[a-f0-9]{64}',value['sha256']) or type(value['bytes']) is not int or not 0<=value['bytes']<=MAX_BLOB:
   raise ValueError('sbom_invalid_blob_reference')
  raw=read_private(root/'blobs'/value['sha256'],MAX_BLOB)
  if len(raw)!=value['bytes'] or hashlib.sha256(raw).hexdigest()!=value['sha256']:raise ValueError('sbom_blob_bytes_changed')
  if value['sha256'] not in referenced:total+=len(raw);referenced.add(value['sha256'])
  if total>MAX_TOTAL:raise ValueError('sbom_blob_total_budget')
  return raw
 if result.get('event_count')!=len(events) or result.get('event_tip')!=previous:raise ValueError('sbom_terminal_chain_changed')
 return request,source,result,events,blob,lambda: {p.name for p in (root/'blobs').iterdir()}==referenced
