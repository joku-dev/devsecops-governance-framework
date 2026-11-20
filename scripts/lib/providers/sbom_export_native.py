"""Finite native legacy SBOM protocol; temporary download credentials stay in RAM."""
from datetime import datetime,timezone
import hashlib,json,os,re,stat,time
from pathlib import Path
from urllib.error import HTTPError,URLError
from urllib.parse import quote,urlparse
from urllib.request import HTTPRedirectHandler,Request,build_opener

from lib.providers import sbom_export_profile as profile
from lib.providers.sbom_export_storage import MAX_BLOB,normalized

MAX_SBOM_BYTES=25*1024**2
DOWNLOAD_HOST_SUFFIXES=('.github.com','.githubusercontent.com','.amazonaws.com','.blob.core.windows.net')
DOWNLOAD_HOSTS={'github.com','githubusercontent.com','amazonaws.com'}


class NoRedirect(HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):return None


def request_headers(token):
 return {'Accept':'application/vnd.github+json',**({'Authorization':f'Bearer {token}'} if token else {}),
  'X-GitHub-Api-Version':profile.API_VERSION,'User-Agent':'governance-repository-sbom'}


def read_limited(response,limit=MAX_SBOM_BYTES):
 chunks=[];total=0
 while True:
  chunk=response.read(min(65536,limit+1-total))
  if not chunk:break
  total+=len(chunk)
  if total>limit:raise ValueError(f'SBOM response exceeds the {limit}-byte limit')
  chunks.append(chunk)
 return b''.join(chunks)


def validate_download_url(location):
 parsed=urlparse(location);host=(parsed.hostname or '').lower()
 if (parsed.scheme!='https' or not host or parsed.username is not None or parsed.password is not None
  or parsed.fragment or host not in DOWNLOAD_HOSTS and not any(host.endswith(suffix) for suffix in DOWNLOAD_HOST_SUFFIXES)):
  raise ValueError(f"GitHub returned an unexpected SBOM download host or URL: {host or '<missing>'}")


def locator_descriptor(location):
 # The private journal deliberately excludes path, query, userinfo and Location.
 value={'sha256':hashlib.sha256(location.encode()).hexdigest(),'characters':len(location)}
 try:
  parsed=urlparse(location)
  value.update(parseable=True,scheme=parsed.scheme,host=(parsed.hostname or '').lower(),
   username_present=parsed.username is not None,password_present=parsed.password is not None,
   fragment_present=bool(parsed.fragment))
 except ValueError:
  value.update(parseable=False,scheme=None,host=None,username_present=None,password_present=None,fragment_present=None)
 return value


def api_json(url,token):
 request=Request(url,headers=request_headers(token),method='GET')
 try:
  # API redirects never receive or forward the bearer credential.
  with build_opener(NoRedirect).open(request,timeout=20) as response:
   payload=json.loads(read_limited(response));return response.status,payload
 except HTTPError as error:
  try:
   if error.code==202:return error.code,{}
   raise RuntimeError(f'GitHub SBOM API returned HTTP {error.code}') from None
  finally:error.close()
 except (URLError,TimeoutError,json.JSONDecodeError) as error:
  # API URLs contain no temporary download credential.
  raise RuntimeError(f'GitHub SBOM API request failed: {error}') from None


def api_redirect(url,token):
 request=Request(url,headers=request_headers(token),method='GET')
 try:
  with build_opener(NoRedirect).open(request,timeout=20) as response:
   if response.status!=302:raise RuntimeError(f'Expected SBOM download redirect, got HTTP {response.status}')
 except HTTPError as error:
  try:
   if error.code!=302:raise RuntimeError(f'GitHub SBOM fetch returned HTTP {error.code}') from None
   location=error.headers.get('Location')
   if not location:raise RuntimeError('GitHub SBOM fetch response has no download location') from None
   return location
  finally:error.close()
 except (URLError,TimeoutError) as error:raise RuntimeError(f'GitHub SBOM fetch failed: {error}') from None
 raise RuntimeError('GitHub SBOM fetch did not return a download location')


class Environment:
 def __init__(self,record,token,*,anonymous_public=False):
  if not isinstance(token,str) or token and any(ord(c)<33 or ord(c)>126 for c in token):
   raise ValueError('sbom_invalid_read_credential')
  self.record=record;self.token=token;self.locations={};self.anonymous_public=anonymous_public
 def request_error(self,name):return profile.ERRORS[name]
 def source_label(self):return profile.SOURCE
 def generation_timeout_error(self):return profile.generation_timeout_error()
 def spdx_identity(self,repository):return profile.identity(repository)
 def report_locator(self,payload):return profile.report_locator(payload)
 def report_identifier(self,repository,locator):return profile.report_identifier(repository,locator)
 def repository_metadata(self,repository):
  def effect():
   status,metadata=api_json(profile.API_ROOT+'/repos/'+repository,self.token)
   if self.anonymous_public and status==200 and (not isinstance(metadata,dict) or metadata.get('visibility')!='public'):
    raise RuntimeError('Anonymous SBOM export requires a public repository')
   return status,metadata
  return self.record.perform('repository_metadata',{'repository':repository},effect)
 def branch_commit(self,repository,branch):
  return self.record.perform('branch_commit',{'repository':repository,'branch':branch},lambda:api_json(profile.API_ROOT+'/repos/'+repository+'/commits/'+quote(branch,safe=''),self.token))
 def generate_report(self,repository):
  def effect():
   status,payload=api_json(profile.API_ROOT+'/repos/'+repository+'/dependency-graph/sbom/generate-report',self.token)
   # Reject an unexpected locator before persisting its potential secret query.
   if status==201:profile.report_identifier(repository,profile.report_locator(payload))
   return status,payload
  return self.record.perform('generate_report',{'repository':repository,'provider_report_creation_requested':True},effect)
 def poll_report(self,repository,identifier):
  def effect():
   location=api_redirect(profile.API_ROOT+'/repos/'+repository+'/dependency-graph/sbom/fetch-report/'+identifier,self.token)
   if not isinstance(location,str) or len(location)>16384:raise ValueError('sbom_download_locator_budget')
   handle='download-'+str(len(self.locations)+1);self.locations[handle]=location
   return {'handle':handle,'locator':locator_descriptor(location)}
  value=self.record.perform('poll_report',{'repository':repository,'report_id':identifier},effect)
  return value['handle']
 def sleep(self,seconds):return self.record.perform('sleep',{'seconds':seconds},lambda:time.sleep(seconds))
 def download(self,handle):
  def effect():
   if handle not in self.locations:raise ValueError('sbom_download_handle_unavailable')
   location=self.locations[handle];validate_download_url(location)
   record=self.record
   class SafeDownloadRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
     descriptor=locator_descriptor(newurl)
     try:validate_download_url(newurl)
     except ValueError:
      record.append({'kind':'download-redirect','locator':descriptor,'admitted':False});raise
     record.append({'kind':'download-redirect','locator':descriptor,'admitted':True})
     return super().redirect_request(req,fp,code,msg,headers,newurl)
   request=Request(location,headers={'User-Agent':'governance-repository-sbom'})
   try:
    with build_opener(SafeDownloadRedirect).open(request,timeout=30) as response:return read_limited(response)
   except (HTTPError,URLError,TimeoutError) as error:
    if isinstance(error,HTTPError):error.close()
    raise RuntimeError('Could not download the generated SPDX SBOM') from None
   except ValueError as error:
    if str(error).startswith(('SBOM response exceeds the ','GitHub returned an unexpected SBOM download host or URL: ')):raise
    self.record.capture_incomplete=True
    raise RuntimeError('Could not download the generated SPDX SBOM') from None
   except Exception:
    self.record.capture_incomplete=True
    raise RuntimeError('Could not download the generated SPDX SBOM') from None
  return self.record.perform('download',{'handle':handle},effect,encoding='bytes')
 def now(self):
  value=self.record.perform('clock',{},lambda:datetime.now(timezone.utc).isoformat())
  return datetime.fromisoformat(value)


class Output:
 """Original ordered overwrites with private pre/post snapshots for touched files."""
 NAMES=frozenset(('sbom.spdx.json','sbom-metadata.json'))
 def __init__(self,record,path,*,source,credential=None,allow_workspace_output=False):
  self.record=record;self.label=str(Path(path));self.root=normalized(path);self.files={}
  self.source=normalized(source);self.credential=None if credential is None else normalized(credential)
  source_overlap=(self.root==self.source or self.root.is_relative_to(self.source) or self.source.is_relative_to(self.root))
  workspace_artifact=allow_workspace_output and self.root==self.source/'sbom-output'
  if (source_overlap and not workspace_artifact
   or self.root.is_relative_to(record.root.parent) or record.root.parent.is_relative_to(self.root)):
   raise ValueError('sbom_separate_export_source_state_required')
  if self.credential is not None and self.credential in {self.root/name for name in self.NAMES}:
   raise ValueError('sbom_export_overlaps_credential')
 def mkdir(self):
  def effect():
   normalized(self.root);self.root.mkdir(mode=0o700,parents=True,exist_ok=True)
   meta=self.root.stat()
   if not stat.S_ISDIR(meta.st_mode) or meta.st_uid!=os.geteuid() or meta.st_mode&0o022:raise ValueError('sbom_owned_export_directory_required')
  return self.record.perform('output_mkdir',{},effect)
 def snapshot(self,path):
  try:meta=path.lstat()
  except FileNotFoundError:return {'exists':False}
  if not stat.S_ISREG(meta.st_mode) or meta.st_nlink!=1 or meta.st_uid!=os.geteuid() or meta.st_size>MAX_BLOB:
   raise ValueError('sbom_export_regular_bounded_file_required')
  fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
  try:
   before=os.fstat(fd)
   if (before.st_dev,before.st_ino)!=(meta.st_dev,meta.st_ino):raise ValueError('sbom_export_file_replaced')
   chunks=[];size=0
   while part:=os.read(fd,min(65536,MAX_BLOB+1-size)):
    chunks.append(part);size+=len(part)
    if size>MAX_BLOB:raise ValueError('sbom_export_file_budget')
   after=os.fstat(fd);current=path.lstat()
   keys=('st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns','st_nlink')
   if any(getattr(before,k)!=getattr(row,k) for row in (after,current) for k in keys):raise ValueError('sbom_export_file_changed_during_read')
   return {'exists':True,'content':self.record.blob(b''.join(chunks)),'mode':stat.S_IMODE(meta.st_mode)}
  finally:os.close(fd)
 def write(self,name,raw):
  path=self.root/name
  try:
   if name not in self.NAMES or not isinstance(raw,bytes) or len(raw)>MAX_BLOB:raise ValueError('sbom_fixed_export_budget_required')
   normalized(self.root);normalized(path)
   before=self.snapshot(path);payload=self.record.blob(raw)
  except Exception as error:
   def rejected():raise error
   self.record.perform('output_prepare',{'name':name},rejected)
   raise
  self.record.append({'kind':'export-before','name':name,'snapshot':before,'payload':payload})
  after=None
  def effect():
   fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_NOFOLLOW|os.O_NONBLOCK,0o600)
   try:
    meta=os.fstat(fd)
    if not stat.S_ISREG(meta.st_mode) or meta.st_uid!=os.geteuid() or meta.st_nlink!=1:raise ValueError('sbom_owned_export_file_required')
    os.fchmod(fd,0o600);os.ftruncate(fd,0);view=memoryview(raw)
    while view:
     count=os.write(fd,view)
     if count<=0:raise OSError('sbom_export_short_write')
     view=view[count:]
    os.fsync(fd)
   finally:os.close(fd)
   return str(Path(self.label)/name)
  try:return self.record.perform('output_write',{'name':name,'payload':payload},effect)
  finally:
   try:after=self.snapshot(path)
   except Exception:
    self.record.capture_incomplete=True
    self.record.append({'kind':'export-capture-failed','name':name})
    raise
   self.files[name]=after
   self.record.append({'kind':'export-after','name':name,'snapshot':after})
