"""Persistent native execution queue on the existing private v2 SQLite store.

Native task identities are separate from immutable producer receipt identities.
The initial GitHub profile permits one exact job name per workflow run/attempt;
matrix names or collisions fail closed rather than collapsing physical jobs.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from pathlib import PurePosixPath
import re
import shutil
import subprocess
import tempfile
import zipfile
from urllib.parse import urlencode, urlsplit

from lib.consumer_github import AccessFailure
from lib.consumer_intake_store import atomic_json, file_digest
from lib.portable.contracts import canonical_digest, endpoint, execution_key, repository_key, valid_id
from lib.portable.runtime import read_json
from lib.private_credentials import check_private_file
from .bundle import MAX_TOTAL, safe_path, timestamp, unpack, validate_policy, verify_bundle, verifier_digest
from .transport import Reader, capture, encoded, BoundedAudit, bamboo_result_key


def instant(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat()


def profile_key(profile):
    return canonical_digest(profile)


def task_key(policy, locator):
    if (set(locator) != {'run_id','job_id','attempt'} or not all(valid_id(locator[k]) for k in ('run_id','job_id'))
            or type(locator['attempt']) is not int or locator['attempt'] < 1):
        raise ValueError('invalid_native_task_identity')
    return canonical_digest({'version':1,'repository':repository_key(policy['scm']),
        'ci_provider':policy['ci']['provider'],'ci_instance':endpoint(policy['ci']['instance']),
        'domain':'devsecops','scope':'pipeline-l1',**locator})


def validate_profiles(document):
    if set(document) != {'schema_version','profiles'} or document['schema_version'] != 1:
        raise ValueError('invalid_portable_registry')
    profiles=document['profiles']
    if not isinstance(profiles,list) or len(profiles)>2000:
        raise ValueError('portable_registry_capacity')
    seen=set()
    for profile in profiles:
        if set(profile) != {'id','policy','reader_credential','scm_reader_credential','discovery'}:
            raise ValueError('invalid_portable_profile')
        if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,63}',profile['id']) or profile['id'] in seen:
            raise ValueError('duplicate_or_invalid_profile')
        seen.add(profile['id'])
        for name in ('reader_credential','scm_reader_credential'):
            if not re.fullmatch(r'reader-[a-zA-Z0-9_-]{1,80}',profile[name]):
                raise ValueError('reader_credential_reference_required')
        policy=validate_policy(profile['policy'])
        if 'transport' not in policy or any('token_env' in policy.get(k,{}) for k in ('transport','scm_transport')):
            raise ValueError('service_uses_credential_files_only')
        transport=policy['transport'];provider=policy['ci']['provider']
        prefix=transport.get('bundle_prefix','')
        if prefix and (prefix.startswith('/') or '..' in prefix.split('/') or '\\' in prefix or ':' in prefix
                       or str(PurePosixPath(prefix))!=prefix or any(ord(c)<32 for c in prefix)):
            raise ValueError('unsafe_configured_bundle_prefix')
        expected=('workflow_path','job_name','logical_job_id','upload_step_name','artifact_name') if provider=='github-actions' else (
            'job_name','configuration_path') if provider=='gitlab-ci' else ('artifact_name',)
        if any(not valid_id(transport.get(name)) for name in expected):
            raise ValueError('incomplete_discovery_profile')
        discovery=profile['discovery']
        if set(discovery) != {'lookback_seconds','plan_key'} or type(discovery['lookback_seconds']) is not int or not 3600<=discovery['lookback_seconds']<=604800:
            raise ValueError('bounded_discovery_window_required')
        if provider=='bamboo' and not re.fullmatch(r'[A-Z0-9]+-[A-Z0-9]+',discovery['plan_key'] or ''):
            raise ValueError('native_bamboo_plan_required')
        # Credentials may use an API prefix, but never another origin than the declared issuer.
        for api,origin in [(transport['api_url'],policy['ci']['instance']),
                           (policy.get('scm_transport',transport)['api_url'],policy['scm']['instance'])]:
            parsed=urlsplit(api)
            actual=endpoint('https://'+parsed.netloc)
            allowed={endpoint(origin)}
            if endpoint(origin)=='https://github.com':allowed.add('https://api.github.com')
            if parsed.scheme!='https' or parsed.username or parsed.password or parsed.query or parsed.fragment or actual not in allowed:
                raise ValueError('credential_endpoint_outside_profile_issuer')
    return profiles


class Queue:
    """Additive service tables; old receipt bytes and migration mappings are unchanged."""
    def __init__(self,store):
        self.store,self.db=store,store.db
        self.db.executescript('''
          CREATE TABLE IF NOT EXISTS native_tasks (
            key TEXT PRIMARY KEY, profile TEXT NOT NULL, locator TEXT NOT NULL,
            state TEXT NOT NULL, discovered REAL NOT NULL, next_at REAL NOT NULL DEFAULT 0,
            retries INTEGER NOT NULL DEFAULT 0, error TEXT, receipt_key TEXT UNIQUE,
            raw_path TEXT, batch TEXT);
          CREATE INDEX IF NOT EXISTS native_ready ON native_tasks(state,next_at,discovered,key);
          CREATE TABLE IF NOT EXISTS portable_http_cache (
            key TEXT PRIMARY KEY, value TEXT NOT NULL, used_at REAL NOT NULL);
        ''')
        self.db.commit()

    def get(self,key,default=None):
        row=self.db.execute('SELECT value FROM meta WHERE key=?',('portable:'+key,)).fetchone()
        return json.loads(row[0]) if row else default

    def put(self,key,value):
        with self.db:
            self.db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',('portable:'+key,json.dumps(value,sort_keys=True)))

    def discover(self,profile,locator,*,at):
        key=task_key(profile['policy'],locator);digest=profile_key(profile)
        with self.store.transaction():
            old=self.db.execute('SELECT profile,locator FROM native_tasks WHERE key=?',(key,)).fetchone()
            encoded_locator=json.dumps(locator,sort_keys=True)
            if old and (old['profile']!=digest or old['locator']!=encoded_locator):
                raise ValueError('native_task_profile_conflict')
            self.db.execute('INSERT OR IGNORE INTO native_tasks(key,profile,locator,state,discovered) VALUES (?,?,?,?,?)',
                (key,digest,encoded_locator,'queued',at))
        return key

    def recover(self):
        # Caller holds worker.lock. Restart does not consume a retry or replace evidence.
        with self.db:self.db.execute("UPDATE native_tasks SET state='queued' WHERE state='working'")

    def claim(self,*,at):
        with self.store.transaction():
            row=self.db.execute("SELECT * FROM native_tasks WHERE state='queued' AND next_at<=? ORDER BY discovered,key LIMIT 1",(at,)).fetchone()
            if row:self.db.execute("UPDATE native_tasks SET state='working' WHERE key=?",(row['key'],))
            return dict(row) if row else None

    def fail(self,key,code,*,at,retryable=False,delay=60,defer=False):
        if not re.fullmatch('[a-z0-9_]{1,100}',code):code='portable_worker_failed'
        with self.store.transaction():
            row=self.db.execute('SELECT retries FROM native_tasks WHERE key=?',(key,)).fetchone()
            if not row:raise ValueError('unknown_native_task')
            retries=row['retries']+(0 if defer else 1)
            wait=max(1,min(delay,86400)) if defer else max(1,min(delay*2**min(retries-1,10),86400))
            self.db.execute('UPDATE native_tasks SET state=?,retries=?,error=?,next_at=? WHERE key=?',
                ('queued' if defer or retryable and retries<=3 else 'held',retries,code,at+wait,key))

    def finish(self,task,receipt,raw_path):
        locator=json.loads(task['locator']);ci=receipt['producer']['ci']
        if ci['run_id']!=locator['run_id'] or ci['attempt']!=locator['attempt']:
            raise ValueError('native_task_receipt_mismatch')
        raw=safe_path(self.store.root,raw_path+'/native-capture.json')
        metadata=read_json(raw);observation=metadata['observation']
        if ci['provider']!='bamboo' and observation.get('native_job_id')!=locator['job_id']:
            raise ValueError('native_job_receipt_mismatch')
        # Physical jobs cannot silently share one producer receipt identity.
        other=self.db.execute('SELECT key FROM native_tasks WHERE receipt_key=?',(receipt['execution_key'],)).fetchone()
        if other and other['key']!=task['key']:raise ValueError('producer_native_alias_conflict')
        saved,_=self.store.record(receipt)
        eligible=(saved['candidate_eligible'] and saved['verifier']==receipt['verifier']
                  and receipt['freshness']=='fresh' and receipt['execution']=='complete'
                  and all(passed for name,passed in receipt['checks'].items() if name!='replay_key_unique'))
        with self.store.transaction():
            self.db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',('portable:produced:'+task['key'],json.dumps(metadata['result_generated_at'])))
            self.db.execute('UPDATE native_tasks SET state=?,receipt_key=?,raw_path=?,error=NULL WHERE key=?',
                ('verified' if eligible else 'held',saved['execution_key'],raw_path,task['key']))

    def summary(self,*,at):
        counts=dict(self.db.execute('SELECT state,count(*) FROM native_tasks GROUP BY state'))
        oldest=self.db.execute("SELECT min(discovered) FROM native_tasks WHERE state IN ('queued','working')").fetchone()[0]
        return {'schema_version':1,'counts':counts,'queue_age_seconds':max(0,at-oldest) if oldest is not None else 0,
                'publisher_active':False,'official_acceptance':False}


class ReaderPool:
    """One finite request budget per issuer/credential realm and persisted throttle.

    Authentication is loaded only from named private files. No publisher credential is
    opened by discovery or collection. Separate operations acquire separate locks.
    """
    def __init__(self,queue,credentials,*,at,budget=300,factory=Reader):
        self.queue,self.credentials,self.at=queue,Path(credentials),at
        self.budget,self.factory,self.readers=budget,factory,{}

    def reader(self,transport,credential):
        realm=canonical_digest({'api':transport['api_url'].rstrip('/'),'subject':credential})
        throttle=self.queue.get('throttle:'+realm,0)
        if throttle>self.at:raise AccessFailure('rate_limited',True,throttle-self.at)
        if realm not in self.readers:
            path=self.credentials/credential
            check_private_file(path)
            token=path.read_text().strip()
            if not token or any(ord(c)<32 for c in token):raise ValueError('invalid_reader_credential')
            self.readers[realm]=self.factory(transport['api_url'],token,budget=self.budget)
            self.readers[realm].cache=ScopedCache(self.queue,realm,self.at)
        return GovernedReader(self,realm,self.readers[realm])

    @property
    def calls(self):return sum(reader.calls for reader in self.readers.values())


class ScopedCache:
    """Conditional-read optimization only; immutable native captures are never evicted."""
    def __init__(self,queue,realm,at):self.queue,self.realm,self.at=queue,realm,at
    def key(self,path):return canonical_digest({'realm':self.realm,'path':path})
    def get(self,path):
        row=self.queue.db.execute('SELECT value FROM portable_http_cache WHERE key=?',(self.key(path),)).fetchone()
        return json.loads(row[0]) if row else None
    def put(self,path,value):
        text=json.dumps(value,sort_keys=True)
        if len(text.encode())>256*1024:return
        with self.queue.db:
            self.queue.db.execute('INSERT OR REPLACE INTO portable_http_cache VALUES (?,?,?)',(self.key(path),text,self.at))
            self.queue.db.execute('DELETE FROM portable_http_cache WHERE key IN (SELECT key FROM portable_http_cache ORDER BY used_at DESC,key DESC LIMIT -1 OFFSET 512)')


class GovernedReader:
    def __init__(self,pool,realm,reader):self.pool,self.realm,self.reader=pool,realm,reader
    @property
    def base(self):return self.reader.base

    def invoke(self,method,*args):
        until=self.pool.queue.get('throttle:'+self.realm,0)
        if until>self.pool.at:raise AccessFailure('rate_limited',True,until-self.pool.at)
        if self.reader.calls>=self.reader.budget:raise AccessFailure('request_budget_exhausted',True)
        # Both poll and worker share a persisted hourly ceiling, including after restart.
        window=int(self.pool.at//3600);name='portable:quota:'+self.realm
        with self.pool.queue.store.transaction():
            row=self.pool.queue.db.execute('SELECT value FROM meta WHERE key=?',(name,)).fetchone()
            quota=json.loads(row[0]) if row else {'window':window,'used':0}
            if quota['window']!=window:quota={'window':window,'used':0}
            if quota['used']>=3000:raise AccessFailure('realm_budget_exhausted',True,(window+1)*3600-self.pool.at)
            quota['used']+=1
            self.pool.queue.db.execute('INSERT OR REPLACE INTO meta VALUES (?,?)',(name,json.dumps(quota,sort_keys=True)))
        try:return getattr(self.reader,method)(*args)
        except AccessFailure as error:
            if error.code in ('rate_limited','artifact_http_429'):
                self.pool.queue.put('throttle:'+self.realm,self.pool.at+min(86400,max(60,error.delay)))
            raise

    def get(self,path):return self.invoke('get',path)
    def download(self,path,destination):return self.invoke('download',path,destination)
    def pages(self,path,field=None,limit=25):
        # Delegate individual reads so the same persisted throttle/budget applies to pages.
        for page in range(1,limit+1):
            data=self.get(path+('&' if '?' in path else '?')+f'per_page=100&page={page}')
            rows=data[field] if field else data
            if not isinstance(rows,list):raise ValueError('invalid_provider_page')
            yield from rows
            if len(rows)<100:return
        raise AccessFailure('provider_pagination_limit')


def discover_page(profile,reader,*,page,start,end):
    """Bounded overlap windows; completion/failed runs included, never latest-success."""
    policy=profile['policy'];scm=policy['scm'];transport=policy['transport'];provider=policy['ci']['provider']
    found=[]
    if provider=='github-actions':
        route='/repos/'+'/'.join(encoded(p) for p in scm['path'].split('/'))
        query=urlencode({'per_page':25,'page':page,'created':instant(start)+'..'+instant(end)})
        document=reader.get(route+'/actions/workflows/'+encoded(Path(transport['workflow_path']).name)+'/runs?'+query)
        if document['total_count']>1000:raise AccessFailure('discovery_window_requires_narrower_profile')
        rows=document['workflow_runs']
        for run in rows:
            if run['status']!='completed':continue
            jobs=list(reader.pages(route+'/actions/runs/'+encoded(run['id'])+'/attempts/'+str(run['run_attempt'])+'/jobs','jobs'))
            matches=[j for j in jobs if j['name']==transport['job_name'] and j['status']=='completed']
            if len(matches)>1:raise ValueError('ambiguous_physical_github_job')
            if matches:found.append({'run_id':str(run['id']),'attempt':run['run_attempt'],'job_id':str(matches[0]['id'])})
        more=len(rows)==25
    elif provider=='gitlab-ci':
        route='/projects/'+encoded(scm['native_id'])
        query=urlencode({'per_page':25,'page':page,'updated_after':instant(start),'updated_before':instant(end),
                         'order_by':'id','sort':'asc'})
        rows=reader.get(route+'/pipelines?'+query)
        for run in rows:
            if run['status'] not in ('success','failed','canceled'):continue
            jobs=list(reader.pages(route+'/pipelines/'+encoded(run['id'])+'/jobs?include_retried=true'))
            for job in jobs:
                if job['name']==transport['job_name'] and job['status'] in ('success','failed'):
                    found.append({'run_id':str(run['id']),'attempt':1,'job_id':str(job['id'])})
        more=len(rows)==25
    else:
        plan=profile['discovery']['plan_key']
        query=urlencode({'max-results':25,'start-index':(page-1)*25,'expand':'results.result',
                         'includeAllStates':'true','lifeCycleState':'Finished'})
        rows=reader.get('/rest/api/latest/result/'+encoded(plan)+'.json?'+query)['results']['result']
        for run in rows:
            finished=timestamp(run['buildCompletedTime']).timestamp()
            if start<=finished<=end and run['lifeCycleState']=='Finished':
                native=bamboo_result_key(run)
                if not native.startswith(plan+'-'):raise ValueError('native_bamboo_plan_mismatch')
                found.append({'run_id':native,'attempt':1,'job_id':native})
        more=len(rows)==25 and any(timestamp(row['buildCompletedTime']).timestamp()>=start for row in rows)
    if len(found)>100:raise AccessFailure('discovery_job_page_limit')
    return found,more


def poll(queue,profiles,pool,*,at,limit=25):
    validate_profiles({'schema_version':1,'profiles':profiles})
    if not 1<=limit<=25:raise ValueError('invalid_poll_limit')
    if not profiles:return {'profiles':0,'discovered':0,'api_calls':0}
    verifier_version=verifier_digest()
    cursor=queue.get('profile_cursor',0)%len(profiles);visited=total=0
    for offset in range(min(limit,len(profiles))):
        profile=profiles[(cursor+offset)%len(profiles)];key=profile_key(profile)
        state=queue.get('discovery:'+key) or {'start':at-profile['discovery']['lookback_seconds'],'end':at,'page':1}
        try:
            reader=pool.reader(profile['policy']['transport'],profile['reader_credential'])
            locators,more=discover_page(profile,reader,page=state['page'],start=state['start'],end=state['end'])
            for locator in locators:queue.discover(profile,locator,at=at);total+=1
            if more:state['page']+=1
            else:state={'start':at-profile['discovery']['lookback_seconds'],'end':at,'page':1}
            if state['page']>400:raise AccessFailure('discovery_window_capacity_exceeded')
            queue.put('discovery:'+key,state)
            if queue.get('shadow_started:'+key) is None or queue.get('shadow_version:'+key)!=verifier_version:
                queue.put('shadow_started:'+key,at);queue.put('shadow_version:'+key,verifier_version)
                queue.put('shadow_match:'+key,None)
            queue.put('poll_error:'+key,None)
        except AccessFailure as error:
            queue.put('poll_error:'+key,error.code)
        except (ValueError,KeyError,TypeError):
            queue.put('poll_error:'+key,'native_discovery_invalid')
        visited+=1
    queue.put('profile_cursor',(cursor+visited)%len(profiles))
    return {'profiles':visited,'discovered':total,'api_calls':pool.calls}


def bootstrap_archive(profile,locator,reader,destination):
    """Get untrusted context bytes, then capture reacquires native bindings independently."""
    policy=profile['policy'];provider=policy['ci']['provider'];transport=policy['transport']
    if provider=='github-actions':
        route='/repos/'+'/'.join(encoded(p) for p in policy['scm']['path'].split('/'))
        run=reader.get(route+'/actions/runs/'+encoded(locator['run_id'])+'/attempts/'+str(locator['attempt']))
        jobs=list(reader.pages(route+'/actions/runs/'+encoded(locator['run_id'])+'/attempts/'+str(locator['attempt'])+'/jobs','jobs'))
        matches=[j for j in jobs if j['name']==transport['job_name'] and str(j['id'])==locator['job_id']]
        if len(matches)!=1:raise ValueError('native_task_job_disappeared')
        job=matches[0]
        artifacts=list(reader.pages(route+'/actions/runs/'+encoded(run['id'])+'/artifacts','artifacts'))
        found=[a for a in artifacts if a['name']==transport['artifact_name'] and not a['expired']
               and timestamp(job['started_at'])<=timestamp(a['created_at'])<=timestamp(job['completed_at'])]
        if len(found)!=1:raise ValueError('ambiguous_native_artifact')
        reader.download(route+'/actions/artifacts/'+encoded(found[0]['id'])+'/zip',destination)
    elif provider=='gitlab-ci':
        reader.download('/projects/'+encoded(policy['scm']['native_id'])+'/jobs/'+encoded(locator['job_id'])+'/artifacts',destination)
    else:
        result=reader.get('/rest/api/latest/result/'+encoded(locator['run_id'])+'.json?expand=artifacts')
        found=[a for a in result.get('artifacts',{}).get('artifact',[]) if a['name']==transport['artifact_name']]
        if len(found)!=1:raise ValueError('ambiguous_native_artifact')
        url=urlsplit(found[0]['link']['href']);base=urlsplit(reader.base)
        if (url.scheme,url.netloc)!=(base.scheme,base.netloc) or url.query or url.fragment or not url.path.startswith(base.path.rstrip('/')+'/'):
            raise ValueError('unsafe_native_artifact_url')
        reader.download(url.path[len(base.path.rstrip('/')):],destination)


class RawBudget:
    """One scan under worker lock per cycle; reserve full in-flight capture, never prune."""
    def __init__(self,root):
        self.root=Path(root)
        self.used=sum(p.stat().st_size for p in (self.root/'raw').rglob('*') if p.is_file())

    def require(self,policy):
        # bootstrap + exact native download + unpack + durable copy/audit, all bounded.
        if (self.used+2*MAX_TOTAL+64*1024**2>policy.get('storage_budget_bytes',2*1024**3)
                or shutil.disk_usage(self.root).free<policy.get('storage_reserve_bytes',8*1024**3)+6*MAX_TOTAL):
            raise AccessFailure('storage_budget_exhausted')


def durable_tree(path):
    for member in sorted(Path(path).rglob('*'),key=lambda p:len(p.parts),reverse=True):
        if member.is_symlink():raise ValueError('unsafe_durable_capture')
        descriptor=os.open(member,os.O_RDONLY)
        try:os.fsync(descriptor)
        finally:os.close(descriptor)
    descriptor=os.open(path,os.O_RDONLY)
    try:os.fsync(descriptor)
    finally:os.close(descriptor)


def collect_task(queue,task,profile,pool,budget,*,opa,at):
    policy=profile['policy'];locator=json.loads(task['locator']);budget.require(policy)
    reader=pool.reader(policy['transport'],profile['reader_credential'])
    scm=pool.reader(policy.get('scm_transport',policy['transport']),profile['scm_reader_credential'])
    raw=queue.store.root/'raw'/'native'/task['key']
    for relative in ('raw','raw/native','raw/native/'+task['key']):
        if (queue.store.root/relative).is_symlink():raise ValueError('unsafe_private_capture_path')
    raw.mkdir(parents=True,mode=0o700,exist_ok=True)
    # Each capture is append-only, including failed attempts and interrupted work.
    with tempfile.TemporaryDirectory(prefix='pending-',dir=raw) as temporary:
        temporary=Path(temporary);audit=BoundedAudit();receipt=None;observation=None;generated_at=None
        try:
            bootstrap_archive(profile,locator,reader,temporary/'bootstrap.zip')
            initial=unpack(temporary/'bootstrap.zip',temporary/'bootstrap')
            prefix=policy['transport'].get('bundle_prefix','')
            if prefix:initial=initial/prefix
            context_path=safe_path(initial,'context.json')
            if context_path.stat().st_size>65536:raise ValueError('native_context_size_limit')
            context=read_json(context_path)
            atomic_json(temporary/'bootstrap-digest.json',{'sha256':file_digest(temporary/'bootstrap.zip')})
            atomic_json(temporary/'bootstrap-context.json',context)
            (temporary/'bootstrap.zip').unlink();shutil.rmtree(temporary/'bootstrap')
            ci=context['ci']
            if (ci['run_id']!=locator['run_id'] or ci['attempt']!=locator['attempt']
                    or ci['provider']=='gitlab-ci' and ci['job_id']!=locator['job_id']):
                raise ValueError('bootstrap_context_task_mismatch')
            observation,audit=capture(context,policy,reader,temporary/'native-artifact.zip',at=instant(at),audit_sink=audit,scm_reader=scm)
            if ci['provider']!='bamboo' and observation.native_job_id!=locator['job_id']:
                raise ValueError('native_physical_job_changed')
            bundle=unpack(temporary/'native-artifact.zip',temporary/'bundle')
            if prefix:bundle=bundle/prefix
            receipt=verify_bundle(bundle,policy,opa=opa,at=instant(at),history=queue.store.history(),observation=observation)
            manifest=read_json(safe_path(bundle,'bundle.json'))
            result_path=next(member['path'] for member in manifest['files'] if member['role']=='result')
            generated_at=read_json(safe_path(bundle,result_path))['generated_at']
            atomic_json(temporary/'receipt.json',receipt)
        finally:
            atomic_json(temporary/'native-capture.json',{'observation':asdict(observation) if observation else None,'responses':audit,
                'result_generated_at':generated_at,
                'bundle_path':'bundle'+('/'+policy['transport']['bundle_prefix'] if policy['transport'].get('bundle_prefix') else '')})
            # Commit raw bytes before SQLite can consume the replay slot, even on failure.
            ready=temporary/'ready';ready.mkdir()
            for member in list(temporary.iterdir()):
                if member!=ready:member.rename(ready/member.name)
            durable_tree(ready)
            import uuid
            destination=raw/uuid.uuid4().hex;ready.rename(destination)
            durable_tree(raw)
            budget.used+=sum(p.stat().st_size for p in destination.rglob('*') if p.is_file())
        queue.finish(task,receipt,str(destination.relative_to(queue.store.root)))
        return receipt


def work(queue,profiles,pool,*,opa,at,limit=25):
    if not 1<=limit<=25:raise ValueError('invalid_work_limit')
    profiles=validate_profiles({'schema_version':1,'profiles':profiles});by_digest={profile_key(p):p for p in profiles}
    queue.recover();budget=RawBudget(queue.store.root);processed=0
    for _ in range(limit):
        task=queue.claim(at=at)
        if not task:break
        profile=by_digest.get(task['profile'])
        if profile is None:
            queue.fail(task['key'],'profile_changed_requires_review',at=at);continue
        try:
            collect_task(queue,task,profile,pool,budget,opa=opa,at=at)
        except AccessFailure as error:
            queue.fail(task['key'],error.code,at=at,retryable=error.retryable,delay=error.delay,
                       defer=error.code in ('rate_limited','request_budget_exhausted','realm_budget_exhausted','artifact_http_429','storage_budget_exhausted'))
        except (ValueError,OSError,KeyError,TypeError,zipfile.BadZipFile,subprocess.SubprocessError):
            queue.fail(task['key'],'native_evidence_invalid',at=at)
        processed+=1
    return {**queue.summary(at=at),'processed':processed,'api_calls':pool.calls}
