#!/usr/bin/env python3
"""Synthetic multi-repository intake using real OPA/files and two real worker processes.

Fixture providers never open a socket. The common collector, verifier, store,
budgets and recovery execute unchanged. All producer contexts are synthetic.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import resource
import shutil
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.consumer_github import AccessFailure
from lib.consumer_intake_store import atomic_json,file_digest,lock
from lib.portable.contracts import canonical_digest,repository_key
from lib.portable.runtime import evaluate,prepare_evidence,source_digest
from lib.portable_intake.bundle import export_bundle,timestamp,verifier_digest
from lib.portable_intake.controller import Queue,ReaderPool,profile_key,work
from lib.portable_intake.store import Store
import test_portable_intake as fixtures
from test_portable_runtime import context,OPA

START=timestamp('2026-11-15T14:00:00Z').timestamp()


def usage():
    own=resource.getrusage(resource.RUSAGE_SELF);children=resource.getrusage(resource.RUSAGE_CHILDREN)
    scale=1024**2 if sys.platform=='darwin' else 1024
    return {'self_cpu_seconds':own.ru_utime+own.ru_stime,'child_cpu_seconds':children.ru_utime+children.ru_stime,
            'self_peak_rss_mib':own.ru_maxrss/scale,'largest_child_peak_rss_mib':children.ru_maxrss/scale}


def disk_bytes(root):return sum(p.stat().st_size for p in Path(root).rglob('*') if p.is_file())


def emit(event,**values):print(json.dumps({'event':event,**values},sort_keys=True),flush=True)


def transform(value,native,job_id):
    if isinstance(value,dict):return {transform(k,native,job_id):transform(v,native,job_id) for k,v in value.items()}
    if isinstance(value,list):return [transform(v,native,job_id) for v in value]
    if type(value) is int and value==42:return native
    if isinstance(value,str):
        if value=='42':return str(native)
        value=value.replace('PROJ-PLAN-42','PROJ-PLAN-'+str(native)).replace('job-42',job_id)
        return re.sub(r'(?<=/)42(?=/|\?|$)',str(native),value)
    return value


def prepare(destination,count,load):
    """Actual producer evaluation/export once per distinct execution; no fan-out receipt."""
    begin=time.perf_counter();before=usage();fixture=fixtures.BundleTests('runTest');fixture.setUp()
    responses={};downloads={};profiles=[];tasks=[];artifacts={}
    archives=destination/'fixtures/archives';archives.mkdir(parents=True)
    credentials=destination/'credentials';credentials.mkdir(mode=0o700)
    try:
        for index in range(count):
            provider=load['providers'][index%3];instance_index=(index//3)%2+1
            native=1000+index//6;origin='https://fixture-'+str(instance_index)+'.example'
            realm=provider+'-'+str(instance_index);token='synthetic:'+realm
            responses.setdefault(token,{});downloads.setdefault(token,{})
            name='reader-'+realm
            if not (credentials/name).exists():(credentials/name).write_text(token);(credentials/name).chmod(0o600)
            ctx=context(provider);ctx['synthetic']=True
            path=('capacity/subgroup/' if provider=='gitlab-ci' else 'CAPACITY/' if provider=='bamboo' else 'capacity/')+'repo-'+str(native)
            ctx['scm'].update(instance=origin,native_id=str(native),path=path,url=origin+'/'+path)
            ctx['ci'].update(instance=origin,run_id='PROJ-PLAN-'+str(native) if provider=='bamboo' else str(native),job_id='job-'+str(native))
            policy=deepcopy(fixture.policy);policy['scm']=deepcopy(ctx['scm'])
            policy['ci']={k:ctx['ci'][k] for k in ('provider','instance')}
            policy['transport'].update(instance=origin,api_url=origin,logical_job_id=ctx['ci']['job_id'] if provider=='github-actions' else 'portable')
            profile={'id':'capacity-'+str(index),'policy':policy,'reader_credential':name,
                'scm_reader_credential':name,'discovery':{'lookback_seconds':86400,'plan_key':'PROJ-PLAN' if provider=='bamboo' else None}}
            profiles.append(profile)
            repetitions=2 if index<int(count*load['rerun_fraction']) else 1
            for repetition in range(repetitions):
                execution=deepcopy(ctx)
                if provider=='github-actions':execution['ci']['attempt']=1+repetition
                if provider=='gitlab-ci' and repetition:execution['ci']['job_id']+='-retry'
                if provider=='bamboo' and repetition:execution['ci']['run_id']='PROJ-PLAN-'+str(native+100000)
                produced='2026-11-15T'+('13' if repetition else '12')+':00:00Z'
                fixture.ctx=execution;fixture.policy=policy
                payload=(hashlib.sha256((str(index)+':'+str(repetition)).encode()).digest()*128)[:load['artifact_bytes']]
                (fixture.checkout/'artifact.bin').write_bytes(payload);digest=file_digest(fixture.checkout/'artifact.bin')
                atomic_json(fixture.checkout/'sbom.json',{'bomFormat':'CycloneDX','specVersion':'1.5','components':[],
                    'metadata':{'component':{'type':'application','name':'synthetic-capacity',
                    'hashes':[{'alg':'SHA-256','content':digest}]}}})
                negative=index%10==0
                atomic_json(fixture.checkout/'scan.json',{'scanner':'synthetic-capacity-scanner','artifact_sha256':digest,
                    'max_severity':'critical' if negative else 'none',
                    'findings':[{'id':'synthetic-finding','severity':'critical'}] if negative else []})
                data,subjects=prepare_evidence(execution,fixture.checkout,'artifact.bin','sbom.json','scan.json')
                result=evaluate(execution,data,subjects,opa=OPA,at=produced)
                for filename,value in [('context.json',execution),('result.json',result),('evaluation-input.json',data)]:
                    atomic_json(fixture.assessment/filename,value)
                shutil.rmtree(fixture.bundle);export_bundle(fixture.assessment,fixture.checkout,fixture.bundle)
                reader,native_rows,job,artifact=fixture.native(provider)
                blob=(fixture.root/'native.zip').read_bytes()
                archive_name=hashlib.sha256(blob).hexdigest()+'.zip';(archives/archive_name).write_bytes(blob)
                native_rows=transform(native_rows,native,execution['ci']['job_id'])
                # The raw fixtures model independent native resources, not a copied run.
                if provider=='github-actions':
                    route='/repos/'+path;attempt=execution['ci']['attempt'];physical=str(1000000+2*index+repetition)
                    old=route+'/actions/runs/'+str(native)+'/attempts/1'
                    run=native_rows.pop(old);run['run_attempt']=attempt
                    native_rows[route+'/actions/runs/'+str(native)+'/attempts/'+str(attempt)]=run
                    job=transform(job,native,execution['ci']['job_id']);job['id']=physical
                    job.update(started_at='2026-11-15T'+('12' if repetition else '11')+':59:00Z',
                        completed_at='2026-11-15T'+('13' if repetition else '12')+':05:00Z')
                    artifact=transform(artifact,native,execution['ci']['job_id']);artifact['id']=2000000+2*index+repetition
                    artifact['created_at']='2026-11-15T'+('13' if repetition else '12')+':01:00Z'
                    native_rows[route+'/actions/runs/'+str(native)+'/attempts/'+str(attempt)+'/jobs?per_page=100&page=1']={'jobs':[job]}
                    artifact_path=route+'/actions/runs/'+str(native)+'/artifacts?per_page=100&page=1'
                    artifacts.setdefault((token,artifact_path),[]).append(artifact)
                    native_rows[artifact_path]={'artifacts':artifacts[token,artifact_path]}
                    download=route+'/actions/artifacts/'+str(artifact['id'])+'/zip'
                elif provider=='gitlab-ci':
                    physical=execution['ci']['job_id'];download='/projects/'+str(native)+'/jobs/'+physical+'/artifacts'
                    job_row=native_rows['/projects/'+str(native)+'/jobs/'+physical]
                    job_row.update(started_at='2026-11-15T'+('12' if repetition else '11')+':59:00Z',
                                   finished_at='2026-11-15T'+('13' if repetition else '12')+':05:00Z')
                else:
                    run_key=execution['ci']['run_id'];physical=run_key
                    row=native_rows.pop('/rest/api/latest/result/PROJ-PLAN-'+str(native)+'.json?expand=artifacts')
                    row['key']=run_key;row.pop('vcsRevisionKey',None)
                    download='/artifact/'+run_key+'.zip';row['artifacts']['artifact'][0]['link']['href']=origin+download
                    native_rows['/rest/api/latest/result/'+run_key+'.json?expand=artifacts']=row
                responses[token].update(native_rows);downloads[token][download]=archive_name
                tasks.append({'profile_index':index,'locator':{'run_id':execution['ci']['run_id'],'job_id':physical,
                    'attempt':execution['ci']['attempt']},'expected_decision':result['decision']})
            if (index+1)%100==0:emit('prepared',repositories=index+1,total=count)
    finally:fixture.doCleanups()
    atomic_json(destination/'fixtures/profiles.json',profiles)
    atomic_json(destination/'fixtures/tasks.json',tasks)
    atomic_json(destination/'fixtures/native.json',{'responses':responses,'downloads':downloads})
    atomic_json(destination/'profile.json',load)
    preparation={'wall_seconds':time.perf_counter()-begin,'usage_before':before,'usage_after':usage(),
        'repositories':count,'executions':len(tasks),'fixture_disk_bytes':disk_bytes(destination/'fixtures')}
    atomic_json(destination/'preparation.json',preparation)
    store=Store(destination/'private')
    try:
        queue=Queue(store)
        for task in tasks:queue.discover(profiles[task['profile_index']],task['locator'],at=START)
        assert len({repository_key(p['policy']['scm']) for p in profiles})==count
        assert store.db.execute('SELECT count(*) FROM native_tasks').fetchone()[0]==len(tasks)
    finally:store.close()
    return preparation


class FixtureProvider:
    def __init__(self,directory,queue,profile):
        self.root,self.queue,self.profile=directory,queue,profile
        self.catalog=json.loads((directory/'fixtures/native.json').read_text())
        self.reads=queue.get('benchmark_native_reads',0);self.rate_events=queue.get('benchmark_rate_events',0)
    def factory(self,base,token,*,budget):
        provider=self
        class FixtureReader:
            def __init__(inner):inner.base,inner.budget,inner.calls=base,budget,0
            def get(inner,path):
                inner.calls+=1;provider.reads+=1
                if provider.reads%provider.profile['injected_rate_limit_every_reads']==0:
                    provider.rate_events+=1
                    raise AccessFailure('rate_limited',True,provider.profile['injected_retry_after_seconds'])
                if path not in provider.catalog['responses'][token]:raise AccessFailure('http_404')
                return deepcopy(provider.catalog['responses'][token][path])
            def download(inner,path,destination):
                inner.calls+=1
                filename=provider.catalog['downloads'][token][path]
                if not re.fullmatch(r'[a-f0-9]{64}\.zip',filename):raise ValueError('invalid_fixture_archive')
                shutil.copyfile(provider.root/'fixtures/archives'/filename,destination)
        return FixtureReader()


def worker(directory,phase):
    load=json.loads((directory/'profile.json').read_text());profiles=json.loads((directory/'fixtures/profiles.json').read_text())
    assert all(p['id'].startswith('capacity-') and p['policy']['scm']['instance'].endswith('.example') for p in profiles)
    begin=time.perf_counter();before=usage();recovery_begin=time.perf_counter()
    with lock(directory/'private/worker.lock'):
        store=Store(directory/'private');queue=Queue(store)
        try:
            before_receipts=store.db.execute('SELECT count(*) FROM receipts').fetchone()[0]
            prior_working=store.db.execute("SELECT count(*) FROM native_tasks WHERE state='working'").fetchone()[0]
            queue.recover();recovery_seconds=time.perf_counter()-recovery_begin
            if phase==2:assert prior_working==1 and before_receipts==queue.get('benchmark_restart_receipts')
            emit('worker_started',phase=phase,recovery_seconds=recovery_seconds,recovered_tasks=prior_working)
            provider=FixtureProvider(directory,queue,load)
            at=queue.get('benchmark_clock',START);cycles=0;api_calls=0;max_depth=0;max_age=0
            total=store.db.execute('SELECT count(*) FROM native_tasks').fetchone()[0]
            while True:
                remaining=store.db.execute("SELECT count(*) FROM native_tasks WHERE state IN ('queued','working')").fetchone()[0]
                if not remaining:break
                pool=ReaderPool(queue,directory/'credentials',at=at,budget=load['cycle_request_budget_per_realm'],factory=provider.factory)
                receipts_before_cycle=store.db.execute('SELECT count(*) FROM receipts').fetchone()[0]
                phase_limit=min(load['worker_limit'],max(1,int(total*load['restart_after_fraction'])-receipts_before_cycle)) if phase==1 else load['worker_limit']
                result=work(queue,profiles,pool,opa=OPA,at=at,limit=phase_limit)
                assert result['processed']<=load['worker_limit']
                cycles+=1;api_calls+=pool.calls;max_depth=max(max_depth,remaining);max_age=max(max_age,result['queue_age_seconds'])
                receipts=store.db.execute('SELECT count(*) FROM receipts').fetchone()[0]
                if cycles%10==0:emit('processing',phase=phase,receipts=receipts,total=total,cycles=cycles)
                at+=60
                if not result['processed']:
                    next_at=store.db.execute("SELECT min(next_at) FROM native_tasks WHERE state='queued'").fetchone()[0]
                    if next_at is not None:at=max(at,next_at)
                if time.perf_counter()-begin>load['synthetic_acceptance']['processing_wall_seconds_upper_bound']:
                    raise ValueError('synthetic_wall_limit_exceeded')
                if phase==1 and receipts>=total*load['restart_after_fraction']:
                    abandoned=queue.claim(at=at)
                    if abandoned is None:
                        next_at=store.db.execute("SELECT min(next_at) FROM native_tasks WHERE state='queued'").fetchone()[0]
                        if next_at is not None:at=max(at,next_at);abandoned=queue.claim(at=at)
                    if abandoned is None:raise ValueError('restart_requires_pending_task')
                    queue.put('benchmark_restart_receipts',receipts)
                    break
            queue.put('benchmark_clock',at);queue.put('benchmark_native_reads',provider.reads);queue.put('benchmark_rate_events',provider.rate_events)
            value={'phase':phase,'wall_seconds':time.perf_counter()-begin,'usage_before':before,'usage_after':usage(),
                'recovery_seconds':recovery_seconds,'recovered_tasks':prior_working,'cycles':cycles,'api_calls':api_calls,
                'maximum_queue_depth':max_depth,'maximum_simulated_queue_age_seconds':max_age,
                'simulated_clock_elapsed_seconds':at-START,'rate_limit_events_total':provider.rate_events,
                'counts':queue.summary(at=at)['counts'],'receipts':store.db.execute('SELECT count(*) FROM receipts').fetchone()[0],
                'operations_disk_bytes':disk_bytes(store.root)}
            atomic_json(directory/('worker-'+str(phase)+'.json'),value)
            if phase==2:
                assert value['receipts']==total
                assert value['counts']=={'held':total}  # synthetic => no native candidate eligibility
                assert not store.db.execute('SELECT 1 FROM portable_batches').fetchone()
            return 75 if phase==1 else 0
        finally:store.close()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-root',type=Path,required=True)
    parser.add_argument('--repositories',type=int,choices=[6,1000,2000])
    parser.add_argument('--worker-phase',type=int,choices=[1,2])
    args=parser.parse_args();os.umask(0o077);directory=args.output_root.resolve()
    if args.worker_phase:return worker(directory,args.worker_phase)
    if not args.repositories:parser.error('--repositories is required')
    directory.mkdir(mode=0o700,parents=True,exist_ok=False)
    load=json.loads((ROOT/'tests/capacity/portable-intake-v1.json').read_text())
    preparation=prepare(directory,args.repositories,load)
    parent_begin=time.perf_counter()
    for phase in (1,2):
        process=subprocess.run([sys.executable,str(Path(__file__).resolve()),'--output-root',str(directory),'--worker-phase',str(phase)],check=False)
        assert process.returncode==(75 if phase==1 else 0),f'worker_phase_{phase}_failed'
    parts=[json.loads((directory/('worker-'+str(p)+'.json')).read_text()) for p in (1,2)]
    wall=sum(p['wall_seconds'] for p in parts);last=parts[-1];expected=preparation['executions']
    peak=max(p['usage_after']['self_peak_rss_mib'] for p in parts)
    assert last['recovered_tasks']==1 and last['recovery_seconds']<=load['synthetic_acceptance']['recovery_seconds_upper_bound']
    assert last['rate_limit_events_total']>0 or args.repositories==6
    assert peak<=load['synthetic_acceptance']['worker_peak_rss_mib_upper_bound']
    report={'schema_version':1,'load_profile_id':load['id'],'synthetic':True,'production_capacity_approved':False,
        'scope':load['measurement_scope'],'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'benchmark_sha256':file_digest(Path(__file__)),'profile_sha256':file_digest(ROOT/'tests/capacity/portable-intake-v1.json'),
        'runtime_source_digest':source_digest(),'verifier_source_digest':verifier_digest(),
        'hardware':{'system':platform.system(),'release':platform.release(),'machine':platform.machine(),
                    'cpu_count':os.cpu_count(),'python':platform.python_version()},
        'repository_count':args.repositories,'execution_count':expected,'preparation':preparation,'worker_phases':parts,
        'processing_wall_seconds':wall,'parent_processing_wall_seconds':time.perf_counter()-parent_begin,
        'executions_per_second':expected/wall,'native_api_calls':sum(p['api_calls'] for p in parts),
        'worker_self_peak_rss_mib':peak,'final_operations_disk_bytes':last['operations_disk_bytes'],
        'maximum_queue_depth':max(p['maximum_queue_depth'] for p in parts),
        'maximum_simulated_queue_age_seconds':max(p['maximum_simulated_queue_age_seconds'] for p in parts),
        'real_remote_publications':0,'identity_collisions':0,'missing_receipts':expected-last['receipts']}
    atomic_json(directory/'report.json',report);emit('completed',report=str(directory/'report.json'),repositories=args.repositories,
        executions=expected,processing_seconds=wall,api_calls=report['native_api_calls'],rss_mib=peak)
    return 0


if __name__=='__main__':raise SystemExit(main())
