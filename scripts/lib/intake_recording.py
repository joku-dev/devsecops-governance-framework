"""Original report-only collection/event records and append-only decisions.

Native source projections, environment names and retry routes are supplied by
explicit ports. Recording a declared outcome does not verify its occurrence.
"""
from datetime import datetime,timezone
import json
from pathlib import Path
import re

from jsonschema import Draft202012Validator
from lib.identifiers import sanitize_timestamp,slugify_repository
from lib.result_ledger import canonical_digest

MAX_FILE=16*1024**2
MAX_FILES=4096
MAX_TOTAL=128*1024**2
KINDS=('attempt','event','retry')


def parse_timestamp(value):
    parsed=datetime.fromisoformat(value.replace('Z','+00:00'))
    if parsed.tzinfo is None:raise ValueError('Intake timestamps must include a timezone')
    return parsed.astimezone(timezone.utc)


def utc_timestamp(value):
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')


def wire(value):return (json.dumps(value,indent=2)+'\n').encode('utf-8')


def attempt(request,source,additional_errors,at):
    collector={'id':request['collector_id'],'version':request['collector_version']}
    identity={'repository_id':request['repository_id'],'evidence_type':request['evidence_type'],
        'collector':collector,'source':source}
    return {'schema_version':'1.0.0','record_type':'evidence-collection-attempt',
        'attempt_id':canonical_digest(identity),'enforcement':'report_only','status':request['status'],
        'repository_id':request['repository_id'],'evidence_type':request['evidence_type'],
        'collector':collector,'attempted_at':utc_timestamp(parse_timestamp(at)),'source':source,
        'errors':[{'code':request['error_code'],'message':request['message'],'retryable':request['retryable']},*(additional_errors or [])]}


def event(request,source,intake,completed_at):
    started=parse_timestamp(request['started_at']);completed=parse_timestamp(completed_at)
    if completed<started:raise ValueError('completed_at must not be earlier than started_at')
    status=request['status'];code=request['error_code'];message=request['message']
    if status=='success' and (code or message):raise ValueError('successful intake events must not contain an error')
    if status!='success' and not (code and message):raise ValueError('partial and failed intake events require an error code and message')
    collector={'id':request['collector_id'],'version':request['collector_version']}
    identity={'repository_id':request['repository_id'],'intake_type':request['intake_type'],
        'evidence_type':request['evidence_type'],'collector':collector,
        'source':{key:source[key] for key in ('run_id','artifact_name')},
        'intake':{key:intake[key] for key in ('repository_id','workflow_name','run_id','run_attempt')}}
    return {'schema_version':'1.0.0','record_type':'intake-operation-event','event_id':canonical_digest(identity),
        'enforcement':'report_only','status':status,'intake_type':request['intake_type'],
        'repository_id':request['repository_id'],'evidence_type':request['evidence_type'],'collector':collector,
        'started_at':utc_timestamp(started),'completed_at':utc_timestamp(completed),
        'duration_ms':int((completed-started).total_seconds()*1000),'source':source,'intake':intake,
        'errors':[] if status=='success' else [{'code':code,'message':message}]}


def record_paths(kind,payload,run_id=None):
    bucket='status/'+('collection-attempts' if kind=='attempt' else 'intake-events')
    conflict='status/intake-conflicts/'+('collection-attempts' if kind=='attempt' else 'intake-events')
    if kind=='attempt':name=f"{sanitize_timestamp(payload['attempted_at'])}-run-{run_id}-{payload['evidence_type']}.json"
    else:name=f"{sanitize_timestamp(payload['started_at'])}-intake-{payload['event_id'][:12]}-{payload['evidence_type']}.json"
    return bucket+'/'+slugify_repository(payload['repository_id'])+'/'+name,conflict


def ledger_projection(kind,files,target,payload,root):
    """Whole original first-identity/conflict/retry behavior over retained bytes."""
    identity='attempt_id' if kind=='attempt' else 'event_id'
    conflict_root='status/intake-conflicts/'+('collection-attempts' if kind=='attempt' else 'intake-events')
    parent=Path(target).parent.as_posix()
    for name in sorted(n for n in files if Path(n).parent.as_posix()==parent and n.endswith('.json')):
        try:existing=json.loads(files[name].decode('utf-8'))
        except json.JSONDecodeError:continue
        if existing.get(identity)!=payload.get(identity):continue
        if canonical_digest(existing)==canonical_digest(payload):
            return {'selected':name,'writes':{},'effect':'existing','conflict_path':None}
        digest=canonical_digest(payload);conflict=conflict_root+'/'+Path(target).stem+'-conflict-'+digest[:12]+'.json'
        # Original conflicts retain their first file without replacement.
        writes={}
        if conflict not in files:
            path=Path(root)/name;parts=path.parts
            portable=str(Path(*parts[parts.index('status'):])) if 'status' in parts else str(path)
            value={'schema_version':'1.0.0','conflict_type':'append_only_snapshot_conflict',
                'enforcement':'report_only','detected_at':payload.get('attempted_at' if kind=='attempt' else 'completed_at','unknown'),
                'target_path':portable,'existing_payload_sha256':canonical_digest(existing),
                'incoming_payload_sha256':digest,'existing_evidence_identity':{identity:payload.get(identity)},
                'incoming_evidence_identity':{identity:payload.get(identity)}}
            writes[conflict]=wire(value)
        return {'selected':name,'writes':writes,'effect':'conflict','conflict_path':conflict}
    while target in files:
        path=Path(target);target=str(path.with_name(path.stem+'-retry'+path.suffix))
    return {'selected':target,'writes':{target:wire(payload)},'effect':'created','conflict_path':None}


def retry_plan(payload,routes,schema=None):
    if schema is not None:Draft202012Validator(schema).validate(payload)
    errors=payload.get('errors',[])
    if not errors or not all(error.get('retryable') is True for error in errors):
        raise ValueError('collection attempt contains a non-retryable error')
    repository=payload['repository_id'];run=str(payload['source']['run_id']);artifact=payload['source']['artifact_name']
    route=routes.get((payload['evidence_type'],payload['collector']['id'],artifact))
    if route is None:raise ValueError('collection attempt does not match a supported retry route')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repository):raise ValueError('repository_id is not safe for workflow dispatch')
    if not re.fullmatch(r'[0-9]+',run):raise ValueError('run_id is not safe for workflow dispatch')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+',artifact):raise ValueError('artifact_name is not safe for workflow dispatch')
    return {'workflow':route,'repository_id':repository,'run_id':run,'artifact_name':artifact,'attempt_id':payload['attempt_id']}


def output_lines(plan):return ''.join(f'{key}={value}\n' for key,value in plan.items()).encode('utf-8')
