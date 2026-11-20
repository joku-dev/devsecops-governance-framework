"""Explicit read protocol, raw private response capture and finite native worker.

The worker receives its selected bearer over stdin only. Its parent enforces
the original 60-second operation deadline across complete PR pagination.
"""
import base64,hashlib,json,math,os,re,subprocess,sys,time
from pathlib import Path
from urllib.parse import quote
from lib.operations_collection import AcquisitionFailure
from lib.providers import operations_report_profile as profile
from lib.providers.sbom_export_storage import read_private

MAX_RESPONSE=4*1024**2
MAX_WORKER_OUTPUT=6*1024**2


class NativeBackend:
    def __init__(self,record,token,*,wall_budget_seconds=60,request_budget=128):
        if type(wall_budget_seconds) not in (int,float) or not math.isfinite(wall_budget_seconds) or not 0<wall_budget_seconds<=60:
            raise ValueError('operations_native_deadline_invalid')
        if type(request_budget) is not int or not 1<=request_budget<=128:raise ValueError('operations_request_budget_invalid')
        profile.valid_request({'method':'GET','path':'/repos/fixture/repository/git/ref/heads/main','body':None,'token':token})
        self.record=record;self.token=token;self.wall_budget=wall_budget_seconds;self.budget=request_budget;self.calls=0;self.deadline=None
    def begin_group(self):self.deadline=time.monotonic()+self.wall_budget
    def end_group(self):self.deadline=None
    def body(self,reference):
        raw=read_private(self.record.blobs/reference['sha256'],MAX_RESPONSE)
        if len(raw)!=reference['bytes'] or hashlib.sha256(raw).hexdigest()!=reference['sha256']:raise ValueError('operations_http_body_changed')
        return raw
    def request(self,method,path,body=None):
        request={'method':method,'path':path,'body':body,'token':self.token};profile.valid_request(request)
        args={'method':method,'path':path,'body':body,'wall_budget_seconds':self.wall_budget}
        def effect():
            start=time.monotonic();remaining=self.wall_budget if self.deadline is None else self.deadline-start
            attempted=False;worker_exit=None;status=None;native_code=None;raw=None;exception=None
            if self.calls>=self.budget:native_code='request_budget_exhausted'
            elif remaining<=0:native_code='operation_deadline_exceeded'
            elif method=='POST' and not self.token:native_code='explicit_read_credential_required'
            else:
                self.calls+=1;attempted=True
                worker=Path(__file__).with_name('operations_http_worker.py')
                command=[sys.executable,'-I','-S','-B',str(worker)]
                # No inherited CLI authentication or caller executable lookup.
                environment={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','PYTHONDONTWRITEBYTECODE':'1'}
                process=None
                try:
                    process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=environment)
                    stdout,stderr=process.communicate(json.dumps(request,separators=(',',':')).encode(),timeout=max(0.001,remaining))
                    worker_exit=process.returncode
                    if worker_exit or len(stdout)>MAX_WORKER_OUTPUT or len(stderr)>65536:
                        raise RuntimeError('operations_http_worker_contract_failed')
                    value=json.loads(stdout)
                    if not isinstance(value,dict) or set(value) not in ({'native_code','status','body_b64'},{'native_code','status','body_b64','exception_type'}):
                        raise RuntimeError('operations_http_worker_contract_failed')
                    if 'exception_type' in value:raise RuntimeError('operations_http_worker_internal_error')
                    status=value['status'];native_code=value['native_code']
                    if value['body_b64'] is not None:
                        if not isinstance(value['body_b64'],str):raise RuntimeError('operations_http_worker_body_invalid')
                        raw=base64.b64decode(value['body_b64'],validate=True)
                        if len(raw)>MAX_RESPONSE:raise RuntimeError('operations_http_worker_body_invalid')
                    if status is not None and (type(status) is not int or not 100<=status<=599):raise RuntimeError('operations_http_worker_status_invalid')
                    allowed={'provider_read_failed','request_timeout','response_byte_budget'}
                    if native_code is not None and native_code not in allowed and not re.fullmatch(r'http_[1-5][0-9]{2}',str(native_code)):
                        raise RuntimeError('operations_http_worker_error_invalid')
                    if native_code is None and (status is None or not 200<=status<300 or raw is None):
                        raise RuntimeError('operations_http_worker_success_invalid')
                    if native_code is not None and str(native_code).startswith('http_'):
                        if native_code!='http_'+str(status) or raw is None:raise RuntimeError('operations_http_worker_status_invalid')
                    elif native_code is not None and (status is not None or raw is not None):
                        raise RuntimeError('operations_http_worker_error_invalid')
                except subprocess.TimeoutExpired:
                    process.kill();process.communicate(timeout=5)
                    worker_exit=process.returncode;native_code='operation_deadline_exceeded'
                except OSError:
                    # Keep the actual original OS error family; an absent own
                    # executable must not be relabelled as an API permission gap.
                    raise
                except Exception:
                    self.record.capture_incomplete=True
                    raise
                finally:
                    if process is not None and process.poll() is None:
                        process.kill();process.communicate(timeout=5)
            return {'schema_version':1,'status':status,'native_code':native_code,
                    'body':None if raw is None else self.record.blob(raw),'request_attempted':attempted,
                    'worker_exit':worker_exit,'elapsed_seconds':time.monotonic()-start}
        return self.record.perform('operations_http',args,effect)


def response_json(value,backend):
    if not isinstance(value,dict) or set(value)!={'schema_version','status','native_code','body','request_attempted','worker_exit','elapsed_seconds'}:
        raise ValueError('operations_http_observation_invalid')
    if type(value['schema_version']) is not int or value['schema_version']!=1 or type(value['request_attempted']) is not bool:
        raise ValueError('operations_http_observation_invalid')
    if type(value['elapsed_seconds']) not in (int,float) or not math.isfinite(value['elapsed_seconds']) or value['elapsed_seconds']<0:
        raise ValueError('operations_http_observation_invalid')
    raw=None if value['body'] is None else backend.body(value['body'])
    code=value['native_code'];status=value['status']
    if code is not None:
        if not isinstance(code,str) or code not in {'provider_read_failed','request_timeout','response_byte_budget','request_budget_exhausted','operation_deadline_exceeded','explicit_read_credential_required','native_worker_unavailable'} and not re.fullmatch(r'http_[1-5][0-9]{2}',code):
            raise ValueError('operations_http_error_invalid')
        if code.startswith('http_') and (type(status) is not int or code!='http_'+str(status) or not value['request_attempted'] or raw is None):
            raise ValueError('operations_http_error_status_changed')
        raise AcquisitionFailure('TimeoutExpired' if code in ('request_timeout','operation_deadline_exceeded') else 'CalledProcessError')
    if type(status) is not int or not 200<=status<300 or raw is None or not value['request_attempted'] or value['worker_exit']!=0:
        raise ValueError('operations_http_success_invalid')
    # Match command_json's JSON-over-text decoding, including BOM failures.
    return json.loads(raw.decode('utf-8'))


class ProviderReads:
    def __init__(self,backend,repository,queries):
        profile.repository_parts(repository)
        if not isinstance(queries,dict) or len(queries)>69 or any(not isinstance(n,str) or len(n)>512 or e not in (None,'push','schedule') for n,e in queries.items()):
            raise ValueError('operations_workflow_query_budget')
        self.backend=backend;self.repository=repository;self.queries=queries
    def get(self,path):return response_json(self.backend.request('GET',path),self.backend)
    def main_reference(self,repository):
        if repository!=self.repository:raise ValueError('operations_repository_scope_changed')
        return self.get('/repos/'+repository+'/git/ref/heads/main')
    def workflow_runs(self,repository,name,event):
        if repository!=self.repository or name not in self.queries or self.queries[name]!=event:raise ValueError('operations_workflow_scope_changed')
        path='/repos/'+repository+'/actions/workflows/'+quote(name,safe='')+'/runs?branch=main&per_page=100'
        if event:path+='&event='+event
        return self.get(path)
    def pull_requests(self,repository):
        if repository!=self.repository:raise ValueError('operations_repository_scope_changed')
        owner,repo=profile.repository_parts(repository);cursor=None;seen_cursors=set();seen_numbers=set();result=[]
        self.backend.begin_group()
        try:
            for page in range(20):
                variables={'owner':owner,'repo':repo,'limit':min(100,1000-len(result)),'cursor':cursor}
                body={'query':profile.PR_QUERY,'variables':variables}
                response=response_json(self.backend.request('POST','/graphql',body),self.backend)
                if not isinstance(response,dict):raise ValueError('operations_graphql_object_required')
                if response.get('errors'):raise AcquisitionFailure('CalledProcessError')
                connection=response['data']['repository']['pullRequests'];rows=connection['nodes'];info=connection['pageInfo']
                if not isinstance(rows,list) or len(rows)>variables['limit'] or not isinstance(info,dict) or type(info.get('hasNextPage')) is not bool:
                    raise ValueError('operations_graphql_page_invalid')
                for value in rows:
                    item=profile.legacy_pull_request(value)
                    if item['number'] in seen_numbers:continue
                    seen_numbers.add(item['number']);result.append(item)
                    if len(result)==1000:return result
                if not info['hasNextPage']:return result
                cursor=info.get('endCursor')
                if not isinstance(cursor,str) or not cursor or len(cursor)>4096 or cursor in seen_cursors:
                    raise ValueError('operations_graphql_cursor_invalid')
                seen_cursors.add(cursor)
            raise AcquisitionFailure('CalledProcessError')
        except AcquisitionFailure:
            raise
        except (ValueError,KeyError,TypeError,UnicodeError):
            # gh pr list parses GraphQL inside the command. Its codec failures
            # are process failures; gh api's plain-output JSON failures differ.
            raise AcquisitionFailure('CalledProcessError') from None
        finally:self.backend.end_group()


class ReplayBackend:
    """Same provider decoding/pagination over retained calls; no worker or clock."""
    def __init__(self,calls,*,wall_budget_seconds=60):
        self.calls=calls;self.wall_budget=wall_budget_seconds
    def begin_group(self):pass
    def end_group(self):pass
    def body(self,reference):return self.calls.blob(reference)
    def request(self,method,path,body=None):
        profile.valid_request({'method':method,'path':path,'body':body,'token':''})
        return self.calls.call('operations_http',{'method':method,'path':path,'body':body,'wall_budget_seconds':self.wall_budget})
