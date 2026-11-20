"""Finite retained export replay. It performs no HTTP, wait, clock or file write."""
from datetime import datetime
from pathlib import Path
import hashlib,json,re

ERRORS={'ValueError':ValueError,'RuntimeError':RuntimeError,'OSError':OSError,
 'PermissionError':PermissionError,'FileExistsError':FileExistsError,'FileNotFoundError':FileNotFoundError,
 'IsADirectoryError':IsADirectoryError,'NotADirectoryError':NotADirectoryError,'TimeoutError':TimeoutError,
 'TypeError':TypeError,'AttributeError':AttributeError,'UnicodeError':UnicodeError,'RecursionError':RecursionError}


class Replay:
 def __init__(self,events,blob,profile,output_label):
  self.events=events;self.blob=blob;self.profile=profile;self.position=1;self.files={};self.locations={};self.output_label=output_label
 def peek(self):
  if self.position>=len(self.events):raise ValueError('sbom_replay_observation_missing')
  return self.events[self.position]
 def consume(self,action,arguments,*,encoding='json'):
  row=self.peek()
  if set(row)!={'kind','operation','action','arguments'} or row.get('kind')!='intent' or row['operation']!=self.position or row['action']!=action or row['arguments']!=arguments:
   raise ValueError('sbom_replay_operation_changed')
  operation=self.position;self.position+=1
  while self.peek().get('kind')=='download-redirect':
   if action!='download':raise ValueError('sbom_redirect_outside_download')
   redirect=self.peek()
   if set(redirect)!={'kind','locator','admitted'} or type(redirect['admitted']) is not bool:raise ValueError('sbom_redirect_observation_changed')
   self.location(redirect['locator']);self.position+=1
  value=self.peek();self.position+=1
  if value.get('operation')!=operation:raise ValueError('sbom_replay_result_changed')
  if value.get('kind')=='failed':
   if set(value)!={'kind','operation','exception','message'} or value['exception'] not in ERRORS or not isinstance(value['message'],str):raise ValueError('sbom_replay_error_changed')
   raise ERRORS[value['exception']](value['message'])
  if set(value)!={'kind','operation','encoding','value'} or value.get('kind')!='returned' or value['encoding']!=encoding:raise ValueError('sbom_replay_result_changed')
  raw=self.blob(value['value'])
  return raw if encoding=='bytes' else json.loads(raw)
 def location(self,value):
  fields={'sha256','characters','parseable','scheme','host','username_present','password_present','fragment_present'}
  if not isinstance(value,dict) or set(value)!=fields or not isinstance(value['sha256'],str) or not re.fullmatch('[a-f0-9]{64}',value['sha256']) or type(value['characters']) is not int or not 0<=value['characters']<=16384 or type(value['parseable']) is not bool:
   raise ValueError('sbom_download_locator_descriptor_changed')
  if value['parseable']:
   if any(type(value[key]) is not bool for key in ('username_present','password_present','fragment_present')) or not all(isinstance(value[key],str) for key in ('scheme','host')):raise ValueError('sbom_download_locator_descriptor_changed')
  elif any(value[k] is not None for k in fields-{'sha256','characters','parseable'}):raise ValueError('sbom_download_locator_descriptor_changed')
 def request_error(self,name):return self.profile.ERRORS[name]
 def source_label(self):return self.profile.SOURCE
 def generation_timeout_error(self):return self.profile.generation_timeout_error()
 def spdx_identity(self,repository):return self.profile.identity(repository)
 def report_locator(self,payload):return self.profile.report_locator(payload)
 def report_identifier(self,repository,locator):return self.profile.report_identifier(repository,locator)
 def repository_metadata(self,repository):return self.consume('repository_metadata',{'repository':repository})
 def branch_commit(self,repository,branch):return self.consume('branch_commit',{'repository':repository,'branch':branch})
 def generate_report(self,repository):return self.consume('generate_report',{'repository':repository,'provider_report_creation_requested':True})
 def poll_report(self,repository,identifier):
  result=self.consume('poll_report',{'repository':repository,'report_id':identifier})
  if not isinstance(result,dict) or set(result)!={'handle','locator'} or result['handle']!='download-'+str(len(self.locations)+1):raise ValueError('sbom_poll_handle_changed')
  self.location(result['locator']);self.locations[result['handle']]=result['locator'];return result['handle']
 def sleep(self,seconds):return self.consume('sleep',{'seconds':seconds})
 def download(self,handle):
  if handle not in self.locations:raise ValueError('sbom_replay_unknown_download_handle')
  return self.consume('download',{'handle':handle},encoding='bytes')
 def now(self):return datetime.fromisoformat(self.consume('clock',{}))
 def mkdir(self):return self.consume('output_mkdir',{})
 def snapshot(self,value):
  if not isinstance(value,dict) or type(value.get('exists')) is not bool:raise ValueError('sbom_export_snapshot_changed')
  if value['exists']:
   if set(value)!={'exists','content','mode'} or type(value['mode']) is not int or not 0<=value['mode']<=0o7777:raise ValueError('sbom_export_snapshot_changed')
   self.blob(value['content'])
  elif set(value)!={'exists'}:raise ValueError('sbom_export_snapshot_changed')
 def write(self,name,raw):
  if self.peek().get('action')=='output_prepare':return self.consume('output_prepare',{'name':name})
  before=self.peek();self.position+=1
  if set(before)!={'kind','name','snapshot','payload'} or before.get('kind')!='export-before' or before['name']!=name:raise ValueError('sbom_export_before_changed')
  self.snapshot(before['snapshot'])
  if self.blob(before['payload'])!=raw:raise ValueError('sbom_export_requested_bytes_changed')
  success=False
  try:
   result=self.consume('output_write',{'name':name,'payload':before['payload']})
   if result!=str(Path(self.output_label)/name):raise ValueError('sbom_export_result_path_changed')
   success=True
   return result
  finally:
   after=self.peek();self.position+=1
   if set(after)!={'kind','name','snapshot'} or after.get('kind')!='export-after' or after['name']!=name:raise ValueError('sbom_export_after_changed')
   self.snapshot(after['snapshot']);self.files[name]=after['snapshot']
   if success and (after['snapshot']['exists'] is not True or self.blob(after['snapshot']['content'])!=raw):raise ValueError('sbom_export_success_bytes_changed')
 def finish(self,result):
  if self.position!=len(self.events)-1 or self.peek()!={'kind':'terminal','state':'complete','exit_code':result['exit_code']}:
   raise ValueError('sbom_replay_terminal_changed')
