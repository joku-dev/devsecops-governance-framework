"""Explicit native intake telemetry, retained inputs and durable external effects."""
import argparse
from contextlib import contextmanager,ExitStack
import fcntl
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat
import tempfile

from jsonschema import Draft202012Validator,ValidationError
from lib import intake_recording as logic,intake_record_files as effects
from lib.candidate_workspace import private_directory
from lib.ci_bundle_storage import reserve
from lib.consumer_intake_store import atomic_json
from lib.functional_parity import git_read
from lib.portable.contracts import ROOT,canonical_digest
from lib.portable.runtime import read_json,source_digest
from lib.provider_ports import (INTAKE_RECORD_PROFILES,intake_record_profile,intake_record_event_defaults,
    intake_record_token,intake_record_endpoint,intake_record_api_selection,acquire_intake_record_metadata,intake_record_metadata,
    intake_attempt_source,intake_event_sources,intake_record_initial_observation)
from lib.result_assessments import identity
from lib.result_bytes import safe_bytes,strict_json
from lib.review_metadata_application import FLAGS
from lib.supplement_application import write_lock

MAX_JSON=4*1024**2
COMMON={'kind','profile','root','at','time_source','output','token_origin'}
BASE={'repository_id','run_id','evidence_type','collector_id','collector_version','artifact_name','status','error_code','message'}
REQUEST_KEYS={'attempt':COMMON|BASE|{'api_url','retryable'},
    'event':COMMON|BASE|{'intake_type','started_at','completed_at','intake_repository_id','intake_workflow_name',
        'intake_run_id','intake_run_attempt','trigger_event'},'retry':COMMON|{'attempt_path'}}



def sync_directory(path):
    descriptor=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(descriptor)
    finally:os.close(descriptor)


def durable_json(path,value):
    atomic_json(path,value);sync_directory(path.parent)


@contextmanager
def material_lock(root):
    # This lock covers short content-addressed publication, never provider I/O.
    descriptor=os.open(root/'material.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    try:
        row=os.fstat(descriptor)
        if not stat.S_ISREG(row.st_mode) or row.st_mode&0o077 or row.st_uid!=os.geteuid() or row.st_nlink!=1:
            raise ValueError('private_intake_material_lock_required')
        fcntl.flock(descriptor,fcntl.LOCK_EX)
        yield
    finally:os.close(descriptor)


def descriptors(files):return {key:{'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)} for key,raw in files.items()}


def scopes(request):
    if request['kind']=='retry':return []
    kind='collection-attempts' if request['kind']=='attempt' else 'intake-events'
    return ['status/'+kind+'/'+logic.slugify_repository(request['repository_id']),'status/intake-conflicts/'+kind]


def checked_request(value):
    if not isinstance(value,dict) or value.get('kind') not in REQUEST_KEYS or set(value)!=REQUEST_KEYS[value['kind']]:raise ValueError('invalid_intake_record_request')
    intake_record_profile(value['profile']);logic.parse_timestamp(value['at'])
    if value['time_source'] not in ('operator','system_clock') or value['token_origin'] not in ('explicit','environment','none'):raise ValueError('invalid_intake_record_origin')
    if not isinstance(value['root'],str) or not Path(value['root']).is_absolute() or '..' in Path(value['root']).parts:raise ValueError('invalid_intake_record_root')
    if value['output'] is not None and (not isinstance(value['output'],str) or not Path(value['output']).is_absolute() or '..' in Path(value['output']).parts):raise ValueError('invalid_native_output_path')
    if value['kind']!='retry' and value['output'] is not None:raise ValueError('native_output_requires_retry')
    if value['kind']!='attempt' and value['token_origin']!='none':raise ValueError('unexpected_intake_record_credential_origin')
    if value['kind']=='attempt':
        if type(value['retryable']) is not bool or value['status'] not in ('partial','failed'):raise ValueError('invalid_collection_attempt_status')
        if value['api_url'] is not None and intake_record_endpoint(value['api_url'])!=value['api_url']:raise ValueError('invalid_intake_record_endpoint')
    elif value['kind']=='event':
        if value['status'] not in ('success','partial','failed') or value['intake_type'] not in ('devsecops_governance','architecture_governance','typed_evidence') or type(value['intake_run_attempt']) is not int:
            raise ValueError('invalid_intake_event_request')
    else:
        path=effects.relative(value['attempt_path'])
        if not str(path).startswith('status/collection-attempts/') or path.suffix!='.json':raise ValueError('attempt_path_below_collection_attempts_required')
    for name in scopes(value):effects.relative(name)
    if len(json.dumps(value).encode())>1024**2:raise ValueError('intake_record_request_budget')
    return value


def derive(request,before,lookup,response,native_time):
    profile=intake_record_profile(request['profile']);kind=request['kind'];stderr=b'';native_output=b''
    clock=logic.checked_native_time(request,native_time,required=True)
    if kind=='retry':
        value=json.loads(before[request['attempt_path']].decode('utf-8'))
        payload=logic.retry_plan(value,profile['routes'],read_json(ROOT/'schemas/evidence-collection-attempt.schema.json'))
        projection={'selected':request['attempt_path'],'writes':{},'effect':'none','conflict_path':None};requested=None
        native_output=logic.output_lines(payload);stdout=logic.wire(payload);valid=True
    else:
        if kind=='attempt':
            run,errors,stderr=intake_record_metadata(lookup,response,request['repository_id'],request['run_id'])
            payload=logic.attempt(request,intake_attempt_source(run,request['artifact_name']),errors,clock['value'])
            schema='evidence-collection-attempt.schema.json'
        else:
            source,intake=intake_event_sources(request)
            completed=request['completed_at'] or logic.utc_timestamp(logic.parse_timestamp(clock['value']))
            payload=logic.event(request,source,intake,completed);schema='intake-operation-event.schema.json'
        requested,_=logic.record_paths(kind,payload,request['run_id']);effects.relative(requested)
        projection=logic.ledger_projection(kind,before,requested,payload,request['root'])
        stdout=(requested+'\n').encode();valid=Draft202012Validator(read_json(ROOT/'schemas'/schema)).is_valid(payload)
    return payload,projection,requested,stdout,stderr,native_output,valid


class IntakeRecordContext:
    def __init__(self,instance,settings):
        self.instance=Path(instance).resolve();private_directory(self.instance/'state')
        self.root=private_directory(self.instance/'state/intake-records')
        self.inputs=private_directory(self.root/'inputs');self.artifacts=private_directory(self.root/'artifacts');self.blobs=private_directory(self.root/'blobs')
        self.records=private_directory(self.root/'assessments');self.intents=private_directory(self.root/'intents');self.locks=private_directory(self.root/'locks')
        self.binding={'node_id':settings['node_id'],'source_revision':git_read(ROOT,'rev-parse','HEAD').decode().strip(),'runtime_source_digest':source_digest()}
        self.clean=not bool(git_read(ROOT,'status','--porcelain','--untracked-files=all').strip())

    def current(self):
        if source_digest()!=self.binding['runtime_source_digest'] or git_read(ROOT,'rev-parse','HEAD').decode().strip()!=self.binding['source_revision']:raise ValueError('intake_record_program_changed')

    def save(self,parent,metadata,files):
        if len(files)>logic.MAX_FILES+10 or sum(map(len,files.values()))>2*logic.MAX_TOTAL or any(len(raw)>logic.MAX_FILE for raw in files.values()):raise ValueError('intake_record_material_budget')
        manifest={**metadata,'files':descriptors(files)};raw=(json.dumps(manifest,sort_keys=True,indent=2)+'\n').encode()
        if len(raw)>MAX_JSON:raise ValueError('intake_record_manifest_budget')
        identifier=canonical_digest(manifest)
        # Share unchanged immutable content across successive bucket snapshots.
        # No hardlinks and no automatic deletion of retained history.
        with material_lock(self.root):
            missing={hashlib.sha256(content).hexdigest():content for content in files.values() if not (self.blobs/hashlib.sha256(content).hexdigest()).exists()}
            reserve(self.root,sum(map(len,missing.values()))+MAX_JSON)
            for digest,content in missing.items():
                descriptor,temporary=tempfile.mkstemp(prefix='.incoming-',dir=self.blobs)
                try:
                    with os.fdopen(descriptor,'wb') as stream:stream.write(content);stream.flush();os.fsync(stream.fileno())
                    os.replace(temporary,self.blobs/digest)
                finally:Path(temporary).unlink(missing_ok=True)
            sync_directory(self.blobs);self.current()
            target=parent/identifier
            if target.is_symlink():raise ValueError('unsafe_intake_record_material')
            if not target.exists():
                with tempfile.TemporaryDirectory(prefix='.incoming-',dir=parent) as temporary:
                    staged=Path(temporary)/'data';staged.mkdir(mode=0o700)
                    durable_json(staged/'manifest.json',manifest);os.rename(staged,target);sync_directory(parent)
            stored,actual=self.material(parent,identifier)
            if stored!=manifest or actual!=files:raise ValueError('immutable_intake_record_material_conflict')
        return identifier

    def material(self,parent,identifier):
        root=parent/identity(identifier);blobs=self.blobs
        if root.is_symlink() or not root.is_dir() or root.stat().st_mode&0o077 or blobs.is_symlink() or not blobs.is_dir() or blobs.stat().st_mode&0o077:
            raise ValueError('private_intake_record_material_required')
        if {p.name for p in root.iterdir()}!={'manifest.json'}:raise ValueError('intake_record_material_members_changed')
        value=strict_json(safe_bytes(root/'manifest.json',limit=MAX_JSON))
        if canonical_digest(value)!=identifier or any(value.get(k)!=v for k,v in self.binding.items()):raise ValueError('intake_record_material_binding_changed')
        rows=value.get('files')
        if not isinstance(rows,dict) or len(rows)>logic.MAX_FILES+10:raise ValueError('invalid_intake_record_material')
        files={};total=0
        descriptor=os.open(blobs,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:
            for name,row in rows.items():
                effects.relative(name)
                if not isinstance(row,dict) or set(row)!={'sha256','bytes'} or type(row['bytes']) is not int or not 0<=row['bytes']<=logic.MAX_FILE:raise ValueError('invalid_intake_record_blob')
                digest=identity(row['sha256']);content,observed=effects.read_at(descriptor,digest,output=True)
                if content is None or observed['st_mode']&0o077:raise ValueError('private_intake_record_blob_required')
                total+=len(content)
                if total>2*logic.MAX_TOTAL or descriptors({name:content})[name]!=row:raise ValueError('intake_record_material_bytes_changed')
                files[name]=content
        finally:os.close(descriptor)
        return value,files

    def input_data(self,identifier,*,parent_allowed=True):
        value,files=self.material(self.inputs,identifier)
        if set(value)!={'schema_version',*self.binding,'request','root_binding','before_metadata','before_directories','output_before_metadata','conflict_filter','parent_input_id','files'} or type(value['schema_version']) is not int or value['schema_version']!=1:
            raise ValueError('invalid_intake_record_inputs')
        request=checked_request(value['request']);metadata=value['before_metadata'];directories=value['before_directories']
        selected=scopes(request);filtered=value['conflict_filter'];parent_id=value['parent_input_id']
        if not isinstance(filtered,list) or len(filtered)>1 or any(not isinstance(n,str) or len(selected)!=2 or Path(n).parent.as_posix()!=selected[1] or effects.relative(n).suffix!='.json' for n in filtered):raise ValueError('invalid_intake_record_conflict_filter')
        if not isinstance(metadata,dict) or not isinstance(directories,dict) or not isinstance(value['root_binding'],dict) or set(value['root_binding'])!={'st_dev','st_ino'} or any(type(n) is not int for n in value['root_binding'].values()):raise ValueError('invalid_intake_record_directory_binding')
        for row in directories.values():
            if row is not None and (not isinstance(row,dict) or set(row)!={'st_dev','st_ino'} or any(type(n) is not int for n in row.values())):raise ValueError('invalid_intake_record_directory_binding')
        if parent_id is not None:
            if not parent_allowed or not filtered:raise ValueError('invalid_intake_record_input_lineage')
            initial,initial_files=self.input_data(identity(parent_id),parent_allowed=False)
            if initial['parent_input_id'] is not None or initial['conflict_filter'] or any(initial[k]!=value[k] for k in ('request','root_binding','output_before_metadata')):raise ValueError('intake_record_initial_input_changed')
            if any(files.get(k)!=raw for k,raw in initial_files.items()) or any(metadata.get(k)!=row for k,row in initial['before_metadata'].items()):raise ValueError('intake_record_initial_input_changed')
            if set(metadata)-set(initial['before_metadata'])-set(filtered) or any(row is not None and directories.get(k)!=row for k,row in initial['before_directories'].items()) or directories.get(selected[0])!=initial['before_directories'].get(selected[0]):raise ValueError('intake_record_initial_input_changed')
        elif filtered:raise ValueError('intake_record_initial_input_required')
        expected={'ledger/'+name for name in metadata}
        if value['output_before_metadata'] is not None:expected.add('native-output-before.bin')
        if set(files)!=expected or set(directories)!=set(scopes(request)):raise ValueError('intake_record_input_members_changed')
        for name,row in metadata.items():
            effects.relative(name)
            if not isinstance(row,dict) or set(row)!=set(effects.FIELDS) or any(type(n) is not int for n in row.values()) or row['st_size']!=len(files['ledger/'+name]):raise ValueError('invalid_intake_record_file_observation')
        if request['kind']=='retry' and set(metadata)!={request['attempt_path']}:raise ValueError('invalid_retry_input_members')
        if request['kind']!='retry' and any(Path(name).parent.as_posix()!=selected[0] and name not in filtered for name in metadata):raise ValueError('invalid_ledger_input_scope')
        return value,files

    def intent(self,operation):
        value=strict_json(safe_bytes(self.intents/(identity(operation)+'.json'),limit=MAX_JSON))
        if set(value)!={'schema_version',*self.binding,'operation_id','input_id','initial_input_id','state','stage','assessment_id'} or type(value['schema_version']) is not int or value['schema_version']!=1 or value['operation_id']!=operation or any(value[k]!=v for k,v in self.binding.items()):raise ValueError('intake_record_intent_binding_changed')
        if value['state'] not in ('pending','completed') or value['stage'] not in ('inputs_retained','metadata_requested','effects_attempted','completed') or (value['state']=='completed')!=(value['assessment_id'] is not None) or (value['state']=='completed')!=(value['stage']=='completed'):raise ValueError('invalid_intake_record_intent')
        inputs,unused=self.input_data(value['input_id'])
        if value['initial_input_id']!=(inputs['parent_input_id'] or value['input_id']):raise ValueError('intake_record_intent_input_lineage_changed')
        return value

    def inspect(self,identifier):
        record=strict_json(safe_bytes(self.records/(identity(identifier)+'.json'),limit=MAX_JSON))
        try:Draft202012Validator(read_json(ROOT/'schemas/axiom-v2-intake-records.schema.json')).validate(record)
        except ValidationError:raise ValueError('invalid_intake_record_assessment') from None
        if canonical_digest(record)!=identifier or any(record[k]!=v for k,v in self.binding.items()):raise ValueError('intake_record_assessment_binding_changed')
        intent=self.intent(record['operation_id'])
        if intent['input_id']!=record['input_id'] or intent['assessment_id']!=identifier:raise ValueError('intake_record_outcome_pointer_changed')
        inputs,files=self.input_data(record['input_id']);request=inputs['request'];artifact,outputs=self.material(self.artifacts,record['artifact_id'])
        if set(artifact)!={'schema_version',*self.binding,'files'} or type(artifact['schema_version']) is not int or artifact['schema_version']!=1:raise ValueError('invalid_intake_record_artifacts')
        if record['kind']!=request['kind'] or record['profile']!=request['profile'] or record['assessed_at']!=request['at'] or record['provider_invoked']!=record['lookup']['client_invoked']:raise ValueError('intake_record_request_or_client_changed')
        allowed={'native-payload.json','native-stdout.bin','native-stderr.bin','metadata-response.bin','native-output-after.bin'}
        if any(name not in allowed and not name.startswith('ledger-after/') for name in outputs):raise ValueError('invalid_intake_record_artifact_name')
        response=outputs.get('metadata-response.bin')
        if record['lookup']['body_retained']!=(response is not None):raise ValueError('intake_record_response_members_changed')
        if record['native_result_available']!=('native-payload.json' in outputs):raise ValueError('intake_record_native_result_members_changed')
        logic.checked_native_time(request,record['native_time'],required=record['native_result_available'])
        if request['kind']!='attempt' and record['lookup']!=intake_record_initial_observation():raise ValueError('unexpected_intake_record_provider_access')
        if record['exit_code']==0:
            before={k.removeprefix('ledger/'):raw for k,raw in files.items() if k.startswith('ledger/')}
            payload,projection,requested,stdout,stderr,append,valid=derive(request,before,record['lookup'],response,record['native_time'])
            if inputs['conflict_filter']!=([projection['conflict_path']] if projection['conflict_path'] else []):raise ValueError('intake_record_conflict_selection_changed')
            if outputs.get('native-payload.json')!=logic.wire(payload) or outputs.get('native-stdout.bin')!=stdout or outputs.get('native-stderr.bin')!=stderr:raise ValueError('intake_record_native_output_changed')
            after={k.removeprefix('ledger-after/'):raw for k,raw in outputs.items() if k.startswith('ledger-after/')}
            if after!={**before,**projection['writes']} or (record['selected'],record['requested'],record['ledger_effect'],record['native_schema_valid'])!=(projection['selected'],requested,projection['effect'],valid):raise ValueError('intake_record_ledger_output_changed')
            if request['output'] is not None:
                if outputs.get('native-output-after.bin')!=files.get('native-output-before.bin',b'')+append:raise ValueError('intake_record_native_append_changed')
            elif 'native-output-after.bin' in outputs:raise ValueError('unexpected_intake_record_native_output')
            if not record['native_result_available'] or not record['effects_attempted'] or record['error_type'] is not None or record['capture_error'] is not None:raise ValueError('invalid_completed_intake_record')
        elif record['error_type'] is None and record['capture_error'] is None:raise ValueError('intake_record_error_required')
        self.current();return {**record,'assessment_id':identifier,'data_directory':str(self.artifacts/record['artifact_id']),
            'retained_artifacts_reverified':True,'retained_complete_outputs_rederived':record['exit_code']==0,
            'current_external_state_rechecked':False,'native_api_requeried':False,'automatic_resume':False}

    def status(self,operation):
        value=self.intent(operation)
        checked=self.inspect(value['assessment_id']) if value['assessment_id'] is not None else None
        self.current();return {**value,'diagnostic_exit_code':None if checked is None else checked['exit_code'],
            'pending_may_have_external_effects':value['state']=='pending','automatic_resume':False}

    def execute(self,request,*,token=None):
        request=checked_request(dict(request));ledger=effects.LedgerRoot(request['root'],[ROOT,self.instance])
        try:
            request['root']=str(ledger.path)
            keys=[['ledger',ledger.binding,scopes(request)[0].casefold() if request['kind']!='retry' else request['attempt_path'].casefold()]]
            if request['output'] is not None:
                request['output']=str(effects.output_path(request['output'],[ROOT,self.instance],ledger.path))
                keys.append(['native-output',request['output'].casefold()])
            with ExitStack() as stack:
                for key in sorted(hashlib.sha256(json.dumps(key).encode()).hexdigest() for key in keys):
                    stack.enter_context(write_lock(private_directory(self.locks/key)))
                return self._execute(request,token,ledger)
        finally:ledger.close()

    def _execute(self,request,token,ledger):
        selected_scopes=scopes(request);kind=request['kind'];output=None;output_before=output_metadata=None;conflict_filter=[]
        native_time=logic.native_record_time(request)
        if kind=='event' and not request['completed_at'] and request['time_source']=='system_clock':
            native_time=logic.native_record_time(request,datetime.now(timezone.utc).isoformat().replace('+00:00','Z'))
        filters={} if kind=='retry' else {selected_scopes[1]:[]}
        if kind=='retry':
            raw,row=ledger.one(request['attempt_path'])
            if raw is None:raise FileNotFoundError('collection_attempt_missing')
            before={request['attempt_path']:raw};metadata={request['attempt_path']:row};directories={}
        else:before,metadata,directories=ledger.snapshot(selected_scopes,filters)
        if request['output'] is not None:
            output=effects.output_path(request['output'],[ROOT,self.instance],ledger.path);request['output']=str(output)
            output_before,output_metadata=effects.output_observation(output)
        files={'ledger/'+key:raw for key,raw in before.items()}
        if output_before is not None:files['native-output-before.bin']=output_before
        input_id=self.save(self.inputs,{'schema_version':1,**self.binding,'request':request,'root_binding':ledger.binding,
            'before_metadata':metadata,'before_directories':directories,'output_before_metadata':output_metadata,
            'conflict_filter':[],'parent_input_id':None},files)
        operation=secrets.token_hex(32);intent={'schema_version':1,**self.binding,'operation_id':operation,'input_id':input_id,'initial_input_id':input_id,
            'state':'pending','stage':'inputs_retained','assessment_id':None}
        self.current();durable_json(self.intents/(operation+'.json'),intent)
        lookup=intake_record_initial_observation();outputs={};error=capture_error=None;payload=None;projection=None;requested=None;valid=None;effects_attempted=False;exit_code=2;stdout=stderr=b''
        def progress(stage):
            intent['stage']=stage;durable_json(self.intents/(operation+'.json'),intent)
        try:
            response=None
            if kind=='attempt':
                def lookup_start():self.current();progress('metadata_requested')
                lookup,response=acquire_intake_record_metadata(request['api_url'],request['repository_id'],request['run_id'],token,lookup_start)
                if response is not None:outputs['metadata-response.bin']=response
                if request['time_source']=='system_clock':
                    native_time=logic.native_record_time(request,datetime.now(timezone.utc).isoformat().replace('+00:00','Z'))
            payload,projection,requested,stdout,stderr,append,valid=derive(request,before,lookup,response,native_time)
            if projection['conflict_path'] is not None:
                conflict_filter=[projection['conflict_path']];filters={selected_scopes[1]:[Path(conflict_filter[0]).name]}
                final_before,final_meta,final_dirs=ledger.snapshot(selected_scopes,filters)
                if any(final_before.get(k)!=raw for k,raw in before.items()) or set(final_before)-set(before)-set(conflict_filter) or any(final_meta.get(k)!=row for k,row in metadata.items()) or final_dirs[selected_scopes[0]]!=directories[selected_scopes[0]] or any(row is not None and final_dirs.get(k)!=row for k,row in directories.items()):raise ValueError('intake_ledger_changed_during_metadata_lookup')
                final_files={'ledger/'+key:raw for key,raw in final_before.items()}
                if output_before is not None:final_files['native-output-before.bin']=output_before
                input_id=self.save(self.inputs,{'schema_version':1,**self.binding,'request':request,'root_binding':ledger.binding,
                    'before_metadata':final_meta,'before_directories':final_dirs,'output_before_metadata':output_metadata,
                    'conflict_filter':conflict_filter,'parent_input_id':intent['initial_input_id']},final_files)
                intent['input_id']=input_id;durable_json(self.intents/(operation+'.json'),intent)
                before,metadata,directories=final_before,final_meta,final_dirs
                payload,projection,requested,stdout,stderr,append,valid=derive(request,before,lookup,response,native_time)
            native=logic.wire(payload)
            if any(len(raw)>logic.MAX_FILE for raw in (native,stdout,stderr,append)):raise ValueError('intake_record_native_output_budget')
            if any(len(raw)>logic.MAX_FILE for raw in projection['writes'].values()):raise ValueError('intake_record_native_output_budget')
            outputs.update({'native-payload.json':native,'native-stdout.bin':stdout,'native-stderr.bin':stderr})
            self.current();progress('effects_attempted');effects_attempted=True
            if kind=='retry':
                if ledger.one(request['attempt_path'])!=(before[request['attempt_path']],metadata[request['attempt_path']]):raise ValueError('retry_source_changed_before_append')
                if output is not None:effects.append_output(output,append,output_before,output_metadata)
            else:ledger.apply(selected_scopes,before,metadata,directories,projection['writes'],filters)
            self.current();exit_code=0
        except Exception as exc:error=type(exc).__name__
        if effects_attempted:
            try:
                if kind=='retry':
                    after,unused=ledger.one(request['attempt_path']);observed={} if after is None else {request['attempt_path']:after}
                else:observed,unused,unused_dirs=ledger.snapshot(selected_scopes,filters)
                outputs.update({'ledger-after/'+key:raw for key,raw in observed.items()})
                if exit_code==0 and observed!={**before,**projection['writes']}:error='ValueError';exit_code=2
                if output is not None:
                    after,unused=effects.output_observation(output)
                    if after is not None:outputs['native-output-after.bin']=after
                    if exit_code==0 and after!=(output_before or b'')+append:error='ValueError';exit_code=2
            except Exception as exc:capture_error=type(exc).__name__;exit_code=2
        artifact_id=self.save(self.artifacts,{'schema_version':1,**self.binding},outputs)
        record={'schema_version':1,**self.binding,'operation_id':operation,'input_id':input_id,'artifact_id':artifact_id,
            'kind':kind,'profile':request['profile'],'assessed_at':request['at'],'source_worktree_clean':self.clean,
            'native_time':native_time,
            'lookup':lookup,'native_result_available':'native-payload.json' in outputs,'effects_attempted':effects_attempted,
            'selected':None if projection is None else projection['selected'],'requested':requested,
            'ledger_effect':None if projection is None else projection['effect'],'native_schema_valid':valid,
            'exit_code':exit_code,'error_type':error,'capture_error':capture_error,
            'mode':'report-only','evidence_trust':'unverified',**FLAGS,
            'native_outcome_authenticated':False,'workflow_dispatched':False,'official_index_updated':False,
            'request_delivery_independently_verified':False}
        record['provider_invoked']=lookup['client_invoked']
        Draft202012Validator(read_json(ROOT/'schemas/axiom-v2-intake-records.schema.json')).validate(record)
        identifier=canonical_digest(record);self.current();durable_json(self.records/(identifier+'.json'),record)
        intent.update(state='completed',stage='completed',assessment_id=identifier);durable_json(self.intents/(operation+'.json'),intent)
        return self.inspect(identifier),payload,stdout,stderr


def run(arguments,instance,settings):
    parser=argparse.ArgumentParser(prog='axiom-v2 intake-records',allow_abbrev=False);commands=parser.add_subparsers(dest='kind',required=True)
    for kind in ('attempt','event','retry'):
        sub=commands.add_parser(kind,allow_abbrev=False);sub.add_argument('--repo',type=Path,required=True)
        sub.add_argument('--profile',choices=INTAKE_RECORD_PROFILES,required=True);sub.add_argument('--at');sub.add_argument('--format',choices=('legacy','receipt'),default='legacy')
        if kind=='retry':
            sub.add_argument('--attempt-path',required=True);sub.add_argument('--native-output','--github-output',dest='output',type=Path)
            continue
        for name in ('repository-id','run-id','evidence-type','collector-id','artifact-name'):sub.add_argument('--'+name,required=True)
        sub.add_argument('--collector-version',default='0.1.0');sub.add_argument('--error-code',required=kind=='attempt');sub.add_argument('--message',required=kind=='attempt')
        if kind=='attempt':
            sub.add_argument('--status',choices=('partial','failed'),default='failed');sub.add_argument('--retryable',action='store_true')
            sub.add_argument('--api-url');sub.add_argument('--token',default='')
        else:
            sub.add_argument('--intake-type',choices=('devsecops_governance','architecture_governance','typed_evidence'),required=True)
            sub.add_argument('--status',choices=('success','partial','failed'),required=True);sub.add_argument('--started-at',required=True);sub.add_argument('--completed-at',default='')
            for name in ('intake-repository-id','intake-workflow-name','intake-run-id','trigger-event'):sub.add_argument('--'+name)
            sub.add_argument('--intake-run-attempt',type=int)
    inspect=commands.add_parser('inspect');inspect.add_argument('--assessment',required=True)
    status=commands.add_parser('status');status.add_argument('--operation',required=True)
    args=parser.parse_args(arguments);app=IntakeRecordContext(instance,settings)
    if args.kind=='inspect':print(json.dumps(app.inspect(args.assessment),sort_keys=True));return 0
    if args.kind=='status':print(json.dumps(app.status(args.operation),sort_keys=True));return 0
    request=vars(args).copy();kind=request['kind'];raw_root=Path(request.pop('repo'))
    if raw_root.is_symlink():raise ValueError('intake_record_root_symlink_forbidden')
    root=raw_root.resolve();format=request.pop('format');at=request['at'];token=None
    request.update(root=str(root),at=at or datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),time_source='operator' if at is not None else 'system_clock',token_origin='none')
    if kind=='attempt':
        token,origin=intake_record_token(request.pop('token'));request['token_origin']=origin
        raw_api=request['api_url'] if request['api_url'] is not None else intake_record_profile(request['profile'])['api_url']
        request['api_url']=intake_record_api_selection(raw_api);request['output']=None
    elif kind=='event':
        for name,value in intake_record_event_defaults().items():
            if request[name] is None:request[name]=value
        for name in ('intake_repository_id','intake_workflow_name','intake_run_id'):
            if not request[name]:parser.error('--'+name.replace('_','-')+' or its native environment value is required')
        request['output']=None
    else:
        raw=Path(request['attempt_path']);path=raw.resolve() if raw.is_absolute() else (root/raw).resolve()
        if not path.is_relative_to(root/'status/collection-attempts') or path.suffix!='.json':raise ValueError('attempt_path_below_collection_attempts_required')
        request['attempt_path']=str(path.relative_to(root));request['output']=str(request['output']) if request['output'] is not None else None
        if request['output'] is not None:
            if Path(request['output']).is_symlink():raise ValueError('native_output_symlink_forbidden')
            request['output']=str(Path(request['output']).resolve())
    value,payload,stdout,stderr=app.execute(request,token=token)
    import sys
    if format=='receipt':print(json.dumps(value,sort_keys=True))
    elif value['exit_code']==0:sys.stderr.write(stderr.decode('utf-8'));sys.stdout.write(stdout.decode('utf-8'))
    else:print('error: Intake recording stopped; inspect private operation '+value['operation_id'],file=sys.stderr)
    return value['exit_code']
