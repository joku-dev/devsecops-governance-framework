"""Separate finite lifecycle journal budget; other profile budgets stay unchanged."""
import hashlib,re
from lib.providers.sbom_export_storage import (Record as BaseRecord,AUTHORITY,encode,
    document,owned_directory,raw_new,read_private,MAX_BLOB,MAX_TOTAL)

MAX_EVENTS=16384
MAX_JOURNAL_BYTES=32*1024**2


class Record(BaseRecord):
 def __init__(self,*args,**kwargs):
  self.journal_bytes=0;super().__init__(*args,**kwargs)
 def append(self,value):
  if self.sequence>=MAX_EVENTS:raise ValueError('synthetic_lifecycle_event_budget')
  owned_directory(self.root);owned_directory(self.events)
  raw=encode({'sequence':self.sequence,'previous':self.previous,'value':value})
  if self.journal_bytes+len(raw)>MAX_JOURNAL_BYTES:raise ValueError('synthetic_lifecycle_journal_byte_budget')
  raw_new(self.events/f'{self.sequence:08}.json',raw)
  self.previous=hashlib.sha256(raw).hexdigest();self.sequence+=1;self.journal_bytes+=len(raw)
 def finish(self,state,result,files,error=None):
  if state=='complete' and self.capture_incomplete:raise ValueError('synthetic_lifecycle_incomplete_capture_cannot_complete')
  return super().finish(state,result,files,error)


def read_record(root):
 root=owned_directory(root)
 if {p.name for p in root.iterdir()}!={'request.json','source.json','result.json','events','blobs'}:raise ValueError('synthetic_lifecycle_record_members_changed')
 request=document(read_private(root/'request.json'));source=document(read_private(root/'source.json'));result=document(read_private(root/'result.json'))
 for name in ('events','blobs'):owned_directory(root/name)
 names=sorted(p.name for p in (root/'events').iterdir())
 if not names or len(names)>MAX_EVENTS or names!=[f'{i:08}.json' for i in range(len(names))]:raise ValueError('synthetic_lifecycle_event_members_changed')
 previous='0'*64;events=[];seen=set();total=0;journal_bytes=0
 for index,name in enumerate(names):
  raw=read_private(root/'events'/name);journal_bytes+=len(raw)
  if journal_bytes>MAX_JOURNAL_BYTES:raise ValueError('synthetic_lifecycle_journal_byte_budget')
  row=document(raw)
  if set(row)!={'sequence','previous','value'} or type(row['sequence']) is not int or row['sequence']!=index or row['previous']!=previous:raise ValueError('synthetic_lifecycle_chain_changed')
  previous=hashlib.sha256(raw).hexdigest();events.append(row['value'])
 def blob(value):
  nonlocal total
  if (type(value) is not dict or set(value)!={'sha256','bytes'} or type(value['sha256']) is not str or re.fullmatch('[a-f0-9]{64}',value['sha256']) is None
      or type(value['bytes']) is not int or not 0<=value['bytes']<=MAX_BLOB):raise ValueError('synthetic_lifecycle_blob_reference_changed')
  raw=read_private(root/'blobs'/value['sha256'],MAX_BLOB)
  if len(raw)!=value['bytes'] or hashlib.sha256(raw).hexdigest()!=value['sha256']:raise ValueError('synthetic_lifecycle_blob_changed')
  if value['sha256'] not in seen:total+=len(raw);seen.add(value['sha256'])
  if total>MAX_TOTAL:raise ValueError('synthetic_lifecycle_blob_total_budget')
  return raw
 if type(result.get('event_count')) is not int or result['event_count']!=len(events) or result.get('event_tip')!=previous:raise ValueError('synthetic_lifecycle_terminal_chain_changed')
 return request,source,result,events,blob,lambda:{p.name for p in (root/'blobs').iterdir()}==seen
