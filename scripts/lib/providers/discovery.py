"""Provider-native discovery, artifact locators and endpoint policy."""
from datetime import datetime, timezone
from pathlib import Path
import re
from urllib.parse import urlencode,urlsplit
from lib.provider_errors import AccessFailure
from lib.portable.contracts import endpoint,valid_id
from lib.portable_intake.bundle import timestamp
from lib.providers.transports import encoded,bamboo_result_key


CI_PROVIDERS = ('github-actions','gitlab-ci','bamboo')


def instant(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat()


def validate_api_endpoint(api, origin):
    parsed=urlsplit(api)
    allowed={endpoint(origin)}
    if endpoint(origin)=='https://github.com':allowed.add('https://api.github.com')
    if (parsed.scheme!='https' or parsed.username or parsed.password or parsed.query or parsed.fragment
            or endpoint('https://'+parsed.netloc) not in allowed):
        raise ValueError('credential_endpoint_outside_profile_issuer')


def validate_discovery_profile(profile):
    policy=profile['policy'];provider=policy['ci']['provider'];transport=policy['transport'];discovery=profile['discovery']
    expected={'github-actions':('workflow_path','job_name','logical_job_id','upload_step_name','artifact_name'),
              'gitlab-ci':('job_name','configuration_path'),'bamboo':('artifact_name',)}
    if provider not in expected:raise ValueError('unsupported_discovery_provider')
    if any(not valid_id(transport.get(name)) for name in expected[provider]):
        raise ValueError('incomplete_discovery_profile')
    if provider=='bamboo' and not re.fullmatch(r'[A-Z0-9]+-[A-Z0-9]+',discovery['plan_key'] or ''):
        raise ValueError('native_bamboo_plan_required')
    validate_api_endpoint(transport['api_url'],policy['ci']['instance'])
    validate_api_endpoint(policy.get('scm_transport',transport)['api_url'],policy['scm']['instance'])


def physical_job_matches(provider, observed, expected):
    if provider not in ('github-actions','gitlab-ci','bamboo'):raise ValueError('unsupported_native_job_provider')
    return provider=='bamboo' or observed==expected


def producer_job_matches(provider, observed, expected):
    if provider not in ('github-actions','gitlab-ci','bamboo'):raise ValueError('unsupported_native_job_provider')
    return provider!='gitlab-ci' or observed==expected


def validate_candidate_composition(scm, ci):
    if (scm,ci) not in {('github','github-actions'),('gitlab','gitlab-ci'),('bitbucket-dc','bamboo')}:
        raise ValueError('candidate_provider_pair_mismatch')


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
