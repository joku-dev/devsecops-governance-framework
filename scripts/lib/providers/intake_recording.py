"""Explicit original native metadata/environment/route adapter; no dispatch writes."""
import json
import os
from urllib.error import HTTPError
from urllib.parse import quote,urlsplit
from urllib.request import Request

from lib.secure_http import open_https,read_limited,require_https

PROFILES=('legacy-intake-records-v1',)
DEFAULT_API_URL='https://api.github.com'
WARNING='warning: GitHub run metadata unavailable; recording the failed attempt with fallback identity\n'
ROUTES={
    ('governance_result','central-governance-intake','governance-control-evaluation'):'intake-governance-result.yml',
    ('governance_result','central-governance-intake','architecture-governance-evidence'):'intake-architecture-result.yml',
    ('vulnerability_scan','central-vulnerability-scan-collector','application-evidence'):'intake-evidence-trust.yml'}


def profile(name):
    if name not in PROFILES:raise ValueError('unsupported_intake_record_profile')
    return {'api_url':DEFAULT_API_URL,'routes':dict(ROUTES)}


def event_defaults(environment=None):
    env=os.environ if environment is None else environment
    return {'intake_repository_id':env.get('GITHUB_REPOSITORY',''),
        'intake_workflow_name':env.get('GITHUB_WORKFLOW',''),'intake_run_id':env.get('GITHUB_RUN_ID',''),
        'intake_run_attempt':int(env.get('GITHUB_RUN_ATTEMPT','1')),'trigger_event':env.get('GITHUB_EVENT_NAME','unknown')}


def token_value(explicit):
    if explicit:return explicit,'explicit'
    for key in ('GH_RESULT_INTAKE_TOKEN','GH_TOKEN','GITHUB_TOKEN'):
        if os.environ.get(key):return os.environ[key],'environment'
    return None,'none'


def endpoint(value):
    require_https(value);parts=urlsplit(value)
    if parts.query or parts.fragment or any(ord(c)<33 for c in value):raise ValueError('invalid_intake_record_api_endpoint')
    return value.rstrip('/')


def initial_observation():
    return {'client_invoked':False,'response_received':False,'http_status':None,'error_type':None,'body_retained':False}


def acquire(api_url,repository,run_id,token,on_attempt):
    observation=initial_observation();raw=None
    try:
        base=endpoint(api_url);owner,repo=repository.split('/',1)
        url=base+f'/repos/{quote(owner)}/{quote(repo)}/actions/runs/{run_id}'
        request=Request(url,headers={'Accept':'application/vnd.github+json','User-Agent':'devsecops-governance-result-intake',
            **({'Authorization':'Bearer '+token} if token else {})})
    except Exception as exc:
        observation['error_type']=type(exc).__name__
        return observation,raw
    # Journal failure is not a metadata lookup failure: it must abort before I/O.
    on_attempt()
    try:
        try:
            with open_https(request) as response:
                observation.update(response_received=True,http_status=getattr(response,'status',200))
                raw=read_limited(response,max_bytes=16*1024**2);observation['body_retained']=True
                json.loads(raw.decode('utf-8'))
        finally:observation['client_invoked']=True
    except Exception as exc:
        observation['error_type']=type(exc).__name__
        if isinstance(exc,HTTPError):
            observation.update(response_received=True,http_status=exc.code)
            exc.close()
    return observation,raw


def metadata_projection(observation,raw,repository,run_id):
    if observation['error_type'] is None:
        if not observation['client_invoked'] or not observation['body_retained'] or raw is None:
            raise ValueError('intake_metadata_observation_incomplete')
        run=json.loads(raw.decode('utf-8'));return run,[],b''
    return {'id':str(run_id),'run_attempt':None,'name':'metadata-unavailable','head_sha':'unknown',
        'html_url':f'https://github.com/{repository}/actions/runs/{run_id}'},[
        {'code':'source_metadata_unavailable',
         'message':'Authoritative GitHub Actions run metadata could not be retrieved during failure recording.',
         'retryable':True}],WARNING.encode()


def attempt_source(run,artifact):
    return {'provider':'github_actions','run_id':str(run.get('id','unknown')),'run_attempt':run.get('run_attempt'),
        'workflow_name':run.get('name','unknown'),'commit_id':run.get('head_sha','unknown'),
        'artifact_name':artifact,'source_uri':run.get('html_url','')}


def event_sources(request):
    repository=request['repository_id'];run=request['run_id'];intake_repository=request['intake_repository_id'];intake_run=request['intake_run_id']
    return ({'provider':'github_actions','run_id':str(run),'artifact_name':request['artifact_name'],
             'source_uri':f'https://github.com/{repository}/actions/runs/{run}'},
        {'provider':'github_actions','repository_id':intake_repository,'workflow_name':request['intake_workflow_name'],
         'run_id':str(intake_run),'run_attempt':request['intake_run_attempt'],'trigger_event':request['trigger_event'],
         'source_uri':f'https://github.com/{intake_repository}/actions/runs/{intake_run}'})
