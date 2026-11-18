"""Private optional role execution, retained raw artifacts and offline reconstruction.

The external directory preserves the original native artifacts. Node-local intent
and provenance remain separate; inspecting an interrupted operation never retries it.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import tempfile
import threading
import time
import uuid

from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from lib import review_execution as logic, review_git, review_planning
from lib.candidate_workspace import private_directory
from lib.ci_bundle_storage import reserve
from lib.consumer_intake_store import atomic_json
from lib.portable.contracts import ROOT, canonical_digest
from lib.portable.runtime import read_json
from lib.provider_ports import (REVIEW_EXECUTION_PROFILES, review_execution_profile,
    review_execution_adapter, review_execution_command, review_execution_observations,
    ReviewExecutionOutput, execute_review_process, review_plan_profile, native_cleanup_observation_valid)
from lib.result_assessments import identity, operator_bytes
from lib.result_bytes import safe_bytes, strict_json
from lib.result_snapshot_store import explicit_time
from lib.review_metadata_application import FLAGS
from lib.review_planning_application import ReviewPlanningContext, external_selection, MAX_JSON, MAX_RESULTS, wire
from lib.supplement_application import write_lock


def hashes(files):
    return {name:{'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()} for name,raw in files.items()}


def result_schema():
    return read_json(ROOT/'schemas/axiom-v2-review-results.schema.json')


def selected_plan(planner, input_id):
    manifest,facts,raw,goal,_=planner.input_data(input_id)
    if manifest['operation']!='check-file':raise ValueError('review_execution_external_plan_required')
    supplied= strict_json(safe_bytes(planner.inputs/input_id/'plan.json',limit=MAX_JSON))
    plan,_=review_planning.plan(facts,raw,goal,review_plan_profile(manifest['profile']))
    if supplied!=plan or plan['selection_mode']!='working_tree' or not plan['base_commit']:
        raise ValueError('review_execution_current_full_branch_plan_required')
    review_planning.check_results(plan,review_planning.results_template(plan),result_schema())
    return plan,facts,raw


def role_material(plan,task,raw,validations,profile,repository,output):
    projection=review_execution_profile(profile)
    adapter_path=projection['adapter_template'].format(role=task['role_id'])
    configuration=review_execution_adapter(raw[adapter_path],profile)
    schema=logic.response_schema(task,[t['role_id'] for t in plan['reviews'][:-1]],result_schema())
    prompt=logic.prompt(plan,task,raw,configuration['instructions'],validations)
    command=review_execution_command(repository,configuration,Path(output)/task['role_id'],profile)
    return configuration,schema,prompt,command,hashlib.sha256(raw[adapter_path]).hexdigest()


def response_outcome(observation,files,role,schema,task,profile):
    error=observation['process_error_type'];value=None;metadata={'model':None,'usage':None};response_digest=None
    if error is None:
        try:
            if observation['timed_out'] or observation['exit_code']!=0:raise ValueError('review_execution_process_failed')
            raw=files.get(role+'/response.json')
            if raw is None:raise FileNotFoundError('review_execution_response_missing')
            value=logic.response(raw,schema,task)
            metadata=review_execution_observations(files.get(role+'/events.jsonl'),profile)
            response_digest=hashlib.sha256(raw).hexdigest()
        except Exception as exc:error=type(exc).__name__
    return {**observation,'error_type':error,'response_digest':response_digest},value,metadata


class ReviewExecutionContext:
    def __init__(self,instance_root,settings):
        self.planner=ReviewPlanningContext(instance_root,settings);self.instance=self.planner.instance
        self.root=private_directory(self.instance/'state/review-execution')
        self.inputs=private_directory(self.root/'inputs');self.intents=private_directory(self.root/'intents')
        self.progress=private_directory(self.root/'progress');self.artifacts=private_directory(self.root/'artifacts')
        self.assessments=private_directory(self.root/'assessments');self.binding=self.planner.binding

    def input_data(self,input_id):
        value=strict_json(safe_bytes(self.inputs/(identity(input_id)+'.json'),limit=MAX_JSON))
        required={'schema_version','planning_input_id','profile','repository','output_directory','execute_requested',
            'parallel_specialists','timeout_seconds','validation_results'}
        if set(value)!=required or type(value['schema_version']) is not int or value['schema_version']!=1 or canonical_digest(value)!=input_id:
            raise ValueError('review_execution_input_changed')
        if type(value['execute_requested']) is not bool:raise ValueError('review_execution_input_changed')
        review_execution_profile(value['profile']);plan,facts,raw=selected_plan(self.planner,identity(value['planning_input_id']))
        logic.policy(raw['.agents/execution-contract.yaml'],value['parallel_specialists'],value['timeout_seconds'])
        for key in ('repository','output_directory'):
            path=value[key]
            if not isinstance(path,str) or not Path(path).is_absolute() or str(Path(path))!=path or '\0' in path:
                raise ValueError('invalid_review_execution_path')
        # Exact operator validation bytes are retained as a bounded encoded string.
        validation=value['validation_results']
        if validation is not None and (not isinstance(validation,str) or len(validation.encode())>MAX_RESULTS):
            raise ValueError('review_execution_validation_budget')
        return value,plan,facts,raw

    def intent(self,operation):
        value=strict_json(safe_bytes(self.intents/(identity(operation)+'.json'),limit=MAX_JSON))
        keys={'schema_version','operation_id','input_id','assessed_at',*self.binding}
        if set(value)!=keys or type(value['schema_version']) is not int or value['schema_version']!=1 or value['operation_id']!=operation or any(value[k]!=v for k,v in self.binding.items()):
            raise ValueError('review_execution_intent_binding_changed')
        explicit_time(value['assessed_at']);self.input_data(value['input_id']);return value

    def status(self,operation):
        intent=self.intent(operation)
        progress=strict_json(safe_bytes(self.progress/(operation+'.json'),limit=MAX_JSON))
        if set(progress)!={'operation_id','state','stage','started_roles','observations','assessment_id'} or progress['operation_id']!=operation or progress['state'] not in ('in_progress','completed'):
            raise ValueError('invalid_review_execution_progress')
        if progress['assessment_id'] is not None:
            checked=self.inspect(progress['assessment_id'])
            if checked['operation_id']!=operation or progress['state']!='completed':raise ValueError('review_execution_progress_changed')
            if any(progress[key]!=checked[key] for key in ('started_roles','observations','stage')):raise ValueError('review_execution_progress_changed')
        elif progress['state']!='in_progress':raise ValueError('review_execution_progress_changed')
        _,plan,_,_=self.input_data(intent['input_id']);roles={task['role_id'] for task in plan['reviews']}
        if not isinstance(progress['started_roles'],list) or any(not isinstance(role,str) for role in progress['started_roles']) or len(progress['started_roles'])!=len(set(progress['started_roles'])) or not set(progress['started_roles'])<=roles:
            raise ValueError('review_execution_progress_roles_changed')
        if not isinstance(progress['observations'],dict) or not set(progress['observations'])<=roles:
            raise ValueError('review_execution_progress_roles_changed')
        self.planner.assert_current()
        return {**intent,**progress,'automatic_resume':False,'incomplete_is_not_retry_authorization':True}

    def record(self,assessment_id):
        value=strict_json(safe_bytes(self.assessments/(identity(assessment_id)+'.json'),limit=MAX_JSON))
        try:Draft202012Validator(read_json(ROOT/'schemas/axiom-v2-review-execution.schema.json'),format_checker=FormatChecker()).validate(value)
        except ValidationError:raise ValueError('invalid_review_execution_assessment') from None
        if type(value['schema_version']) is not int or canonical_digest(value)!=assessment_id or any(value[k]!=v for k,v in self.binding.items()):raise ValueError('review_execution_binding_changed')
        intent=self.intent(value['operation_id'])
        if intent['input_id']!=value['input_id'] or intent['assessed_at']!=value['assessed_at']:raise ValueError('review_execution_intent_changed')
        return value

    def retained(self,assessment_id,value):
        root=self.artifacts/assessment_id
        if root.is_symlink() or not root.is_dir() or root.stat().st_mode&0o077:raise ValueError('private_review_execution_artifacts_required')
        if {p.name for p in root.iterdir()}!={row['sha256']+'.bin' for row in value['files'].values()}:raise ValueError('review_execution_artifact_members_changed')
        files={};total=0
        for name,row in value['files'].items():
            parts=name.split('/')
            if not 1<=len(parts)<=2 or any(not p or p in ('.','..') or '\\' in p or '\0' in p for p in parts):raise ValueError('invalid_review_execution_artifact_name')
            raw=safe_bytes(root/(row['sha256']+'.bin'),limit=logic.MAX_FILE);total+=len(raw)
            if hashes({name:raw})[name]!=row:raise ValueError('review_execution_artifact_changed')
            if total>logic.MAX_TOTAL:raise ValueError('review_execution_artifact_budget')
            files[name]=raw
        return files

    def rederive(self,value,files):
        input,plan,_,raw=self.input_data(value['input_id']);results=review_planning.results_template(plan)
        if input['validation_results'] is not None:results['validations']=strict_json(input['validation_results'].encode())['validations']
        review_planning.check_results(plan,results,result_schema())
        expected={};materials={}
        for task in plan['reviews']:
            role=task['role_id'];config,schema,prompt,command,adapter_digest=role_material(plan,task,raw,results['validations'],input['profile'],input['repository'],input['output_directory'])
            materials[role]=(schema,prompt,adapter_digest)
            expected[role+'/response.schema.json']=logic.json_bytes(schema);expected[role+'/command.json']=logic.json_bytes(command)
            expected[role+'/prompt.json']=logic.json_bytes(prompt)
        manifest=logic.manifest(plan,value['native_run_id'],raw['.agents/execution-contract.yaml'],input['execute_requested'],input['parallel_specialists'],input['timeout_seconds'])
        reviews=[];traces=[];specialists=[]
        for task in plan['reviews']:
            role=task['role_id'];schema,prompt,adapter_digest=materials[role]
            if role not in value['observations']:continue
            observation=value['observations'][role];prior=specialists if role=='repo-steward' else []
            if not native_cleanup_observation_valid(observation):raise ValueError('review_execution_cleanup_observation_changed')
            config=review_execution_adapter(raw[review_execution_profile(input['profile'])['adapter_template'].format(role=role)],input['profile'])
            if observation['requested_model']!=config['requested_model'] or (not observation['process_started'] and observation['process_error_type'] is None):
                raise ValueError('review_execution_process_observation_changed')
            if role=='repo-steward':expected[role+'/execution-prompt.json']=logic.json_bytes({**prompt,'specialist_results':prior})
            observed,response,metadata=response_outcome(observation,files,role,schema,task,input['profile'])
            initial=next(r for r in results['reviews'] if r['role_id']==role)
            review,trace=logic.finish_role(task,initial,observed,response,metadata,provider=review_execution_profile(input['profile'])['provider'],adapter_digest=adapter_digest,specialists=prior)
            reviews.append(review);traces.append(trace)
            if role!='repo-steward':specialists.append(review)
            expected[role+'/trace.json']=logic.json_bytes(trace)
        if input['execute_requested']:
            results,report=logic.final_results(plan,results,reviews,traces,result_schema(),completed=True)
            manifest.update(roles=traces,provider_invoked=any(o['process_started'] for o in value['observations'].values()),completion=report)
        expected['results.json']=logic.json_bytes(results);expected['execution.json']=logic.json_bytes(manifest)
        if any(files.get(name)!=raw for name,raw in expected.items()):raise ValueError('review_execution_control_outputs_changed')
        allowed=set(expected)
        for role in value['observations']:allowed.update(role+'/'+n for n in ('response.json','events.jsonl','stderr.log'))
        # Additional provider-created bytes are opaque retained data, never executable inputs.
        return expected,set(files)-allowed

    def inspect(self,assessment_id):
        value=self.record(assessment_id);files=self.retained(assessment_id,value)
        input,plan,_,_=self.input_data(value['input_id'])
        roles=[t['role_id'] for t in plan['reviews']]
        if not set(value['observations'])<=set(roles) or len(set(value['started_roles']))!=len(value['started_roles']) or not set(value['started_roles'])<=set(roles):raise ValueError('review_execution_role_changed')
        observed_starts={role for role,o in value['observations'].items() if o['process_started']}
        if not observed_starts<=set(value['started_roles']) or value['provider_invoked']!=bool(value['started_roles']) or value['execute_requested']!=input['execute_requested']:
            raise ValueError('review_execution_process_observation_changed')
        if not input['execute_requested'] and (value['observations'] or value['started_roles']):raise ValueError('review_execution_preparation_cannot_invoke')
        if value['exit_code']!=2:
            if value['capture_error'] is not None or value['error_type'] is not None or value['native_run_id'] is None:raise ValueError('review_execution_completion_changed')
            self.rederive(value,files)
            manifest=json.loads(files['execution.json']);ready=manifest.get('completion',{}).get('eligible_for_human_review',False)
            if value['declared_ready']!=ready or value['exit_code']!=(0 if not input['execute_requested'] or ready else 1):raise ValueError('review_execution_outcome_changed')
            if input['execute_requested']:
                specialists=roles[:-1]
                if not set(specialists)<=value['observations'].keys():raise ValueError('review_execution_missing_specialists')
                responses=json.loads(files['results.json'])['reviews']
                steward_expected=all(r['status']=='completed' for r in responses[:-1])
                if (roles[-1] in value['observations'])!=steward_expected:raise ValueError('review_execution_steward_order_changed')
        self.planner.assert_current()
        return {**value,'assessment_id':assessment_id,'data_directory':str(self.artifacts/assessment_id),
            'retained_raw_artifacts_reverified':True,'native_control_outputs_rederived':value['exit_code']!=2,
            'native_artifact_capture_complete':value['capture_error'] is None,
            'target_current_state_rechecked':False,'provider_model_identity_verified':False,'automatic_resume':False}

    def create(self,repository,plan_bytes,output,profile,at,*,execute=False,parallel=1,timeout=180,validation_bytes=None):
        explicit_time(at);projection=review_execution_profile(profile)
        supplied,goal,base,paths=external_selection(plan_bytes)
        if paths or supplied['selection_mode']!='working_tree' or not base:raise ValueError('review_execution_full_branch_plan_required')
        repository=Path(repository).resolve()
        if self.instance.is_relative_to(repository) or repository.is_relative_to(self.root):raise ValueError('review_private_state_must_be_outside_target')
        policy=review_plan_profile('legacy-role-review-v1');facts,raw=review_git.capture(repository,base,[],policy)
        if review_git.git(repository,'status','--porcelain','--untracked-files=normal').strip():raise ValueError('review_execution_clean_committed_target_required')
        expected,_=review_planning.plan(facts,raw,goal,policy)
        if expected!=supplied:raise ValueError('review_execution_stale_plan')
        logic.policy(raw['.agents/execution-contract.yaml'],parallel,timeout)
        if execute and os.environ.get('CI'):raise ValueError('review_execution_forbidden_in_ci')
        if validation_bytes is not None and (not isinstance(validation_bytes,bytes) or len(validation_bytes)>MAX_RESULTS):raise ValueError('review_execution_validation_budget')
        template=review_planning.results_template(expected)
        planning_id=self.planner.capture_input('check-file','legacy-role-review-v1',facts,raw,goal,wire(template),None,plan_bytes)
        input={'schema_version':1,'planning_input_id':planning_id,'profile':profile,'repository':str(repository),
            'output_directory':str(Path(output).expanduser().resolve()),'execute_requested':execute,
            'parallel_specialists':parallel,'timeout_seconds':timeout,
            'validation_results':None if validation_bytes is None else validation_bytes.decode('utf-8')}
        input_id=canonical_digest(input);operation=secrets.token_hex(32)
        intent={'schema_version':1,'operation_id':operation,'input_id':input_id,'assessed_at':at,**self.binding}
        progress={'operation_id':operation,'state':'in_progress','stage':'intent_recorded','started_roles':[],'observations':{},'assessment_id':None}
        reserve(self.root,logic.MAX_TOTAL+MAX_JSON)
        self.planner.assert_current()
        with write_lock(self.root):
            target=self.inputs/(input_id+'.json')
            if target.is_symlink():raise ValueError('unsafe_review_execution_input')
            if target.exists():
                if strict_json(safe_bytes(target,limit=MAX_JSON))!=input:raise ValueError('immutable_review_execution_input_conflict')
            else:atomic_json(target,input)
            atomic_json(self.intents/(operation+'.json'),intent);atomic_json(self.progress/(operation+'.json'),progress)
        lock=threading.Lock();observations={};traces={};prepared=[];native=None;directory=None
        results=deepcopy(template);error=None;capture_error=None;files={};stage='create_output';code=2
        def update(stage_name):
            with lock:
                progress.update(stage=stage_name,observations=deepcopy(observations))
                atomic_json(self.progress/(operation+'.json'),progress)
        def current():
            self.planner.assert_current()
            if review_git.observe(repository,base,[],policy)!=(facts,raw):raise ValueError('review_execution_target_changed')
            if review_git.git(repository,'status','--porcelain','--untracked-files=normal').strip():raise ValueError('review_execution_target_changed')
        try:
            current();directory=ReviewExecutionOutput(output,[repository,ROOT,self.instance]);update(stage)
            stage='validate_recorded_validations'
            if validation_bytes is not None:results['validations']=strict_json(validation_bytes)['validations']
            review_planning.check_results(expected,results,result_schema())
            for task in expected['reviews']:
                stage='prepare_role';config,schema,prompt,command,adapter_digest=role_material(expected,task,raw,results['validations'],profile,repository,directory.path)
                role=task['role_id'];directory.mkdir(role)
                directory.write(role+'/response.schema.json',schema);directory.write(role+'/command.json',command)
                prepared.append((task,config,schema,prompt,command,adapter_digest))
            native=logic.manifest(expected,uuid.uuid4().hex,raw['.agents/execution-contract.yaml'],execute,parallel,timeout)
            stage='write_prompts'
            for task,_,_,prompt,_,_ in prepared:directory.write(task['role_id']+'/prompt.json',prompt)
            if execute:
                stage='execute_reviews';update(stage)
                def invoke(item,specialists=None):
                    task,config,schema,prompt,command,adapter_digest=item;role=task['role_id'];current()
                    if specialists is not None:
                        prompt={**prompt,'specialist_results':specialists};directory.write(role+'/execution-prompt.json',prompt)
                    observed={'run_id':uuid.uuid4().hex,'started_at':datetime.now(timezone.utc).isoformat(),
                        'requested_model':config['requested_model']};begin=time.monotonic()
                    def on_start():
                        with lock:
                            progress['started_roles'].append(role);atomic_json(self.progress/(operation+'.json'),progress)
                    process=execute_review_process(command,json.dumps(prompt),directory,role,timeout,profile,on_start)
                    observed.update(process);observed['process_error_type']=observed.pop('error_type')
                    raw_outputs={}
                    try:
                        for name in ('response.json','events.jsonl'):
                            data=directory.read(role+'/'+name,logic.MAX_RESPONSE if name=='response.json' else 10*1024**2)
                            if data is not None:raw_outputs[role+'/'+name]=data
                    except Exception as exc:
                        observed['process_error_type']=observed['process_error_type'] or type(exc).__name__
                    outcome,response,metadata=response_outcome(observed,raw_outputs,role,schema,task,profile)
                    observed.update(completed_at=datetime.now(timezone.utc).isoformat(),elapsed_seconds=time.monotonic()-begin)
                    outcome.update(completed_at=observed['completed_at'],elapsed_seconds=observed['elapsed_seconds'])
                    initial=next(r for r in results['reviews'] if r['role_id']==role)
                    review,trace=logic.finish_role(task,initial,outcome,response,metadata,provider=projection['provider'],adapter_digest=adapter_digest,specialists=specialists or [])
                    directory.write(role+'/trace.json',trace)
                    with lock:observations[role]=observed;traces[role]=trace
                    update('role_completed');current();return review,trace
                try:
                    with ThreadPoolExecutor(max_workers=parallel) as pool:completed=list(pool.map(invoke,prepared[:-1]))
                    for review,_ in completed:results['reviews'][next(i for i,r in enumerate(results['reviews']) if r['role_id']==review['role_id'])]=review
                    if all(r['status']=='completed' for r in results['reviews'][:-1]):
                        review,_=invoke(prepared[-1],deepcopy(results['reviews'][:-1]));results['reviews'][-1]=review
                    else:results['reviews'][-1].update(status='skipped',summary='Required specialists did not complete; final synthesis was not executed')
                    current();native['completion']=review_planning.check_results(expected,results,result_schema())
                finally:
                    native.update(roles=[traces[t['role_id']] for t in expected['reviews'] if t['role_id'] in traces],provider_invoked=bool(progress['started_roles']))
                    directory.write('results.json',results);directory.write('execution.json',native)
            else:
                directory.write('results.json',results);directory.write('execution.json',native)
            stage='final_source_check';current();code=0 if not execute or native.get('completion',{}).get('eligible_for_human_review') else 1
        except Exception as exc:error=type(exc).__name__
        finally:
            if directory is not None:
                try:files=directory.snapshot()
                except Exception as exc:capture_error=type(exc).__name__;code=2
                finally:directory.close()
        value={'schema_version':1,'kind':'local-review-execution',**self.binding,'operation_id':operation,'input_id':input_id,
            'assessed_at':at,'source_worktree_clean':self.planner.clean,'profile':profile,'execute_requested':execute,
            'native_run_id':None if native is None else native['run_id'],'observations':observations,
            'started_roles':progress['started_roles'],'exit_code':code,'error_type':error,'capture_error':capture_error,
            'stage':stage,'files':hashes(files),'declared_ready':code!=2 and native.get('completion',{}).get('eligible_for_human_review',False),
            'mode':'report-only','evidence_trust':'unverified',**FLAGS}
        value['provider_invoked']=bool(progress['started_roles']);assessment_id=canonical_digest(value)
        # Retention failure leaves the durable operation pending; it never retries providers.
        with tempfile.TemporaryDirectory(prefix='.incoming-',dir=self.artifacts) as temporary:
            staged=Path(temporary)/'data';staged.mkdir(mode=0o700)
            for raw in files.values():path=staged/(hashlib.sha256(raw).hexdigest()+'.bin');path.write_bytes(raw);path.chmod(0o600)
            self.planner.assert_current()
            with write_lock(self.root):
                os.rename(staged,self.artifacts/assessment_id);atomic_json(self.assessments/(assessment_id+'.json'),value)
                progress.update(state='completed',stage=stage,observations=deepcopy(observations),assessment_id=assessment_id)
                atomic_json(self.progress/(operation+'.json'),progress)
        return self.inspect(assessment_id),native


def run(arguments,instance_root,settings):
    parser=argparse.ArgumentParser(prog='axiom-v2 review-run',allow_abbrev=False)
    commands=parser.add_subparsers(dest='command',required=True)
    start=commands.add_parser('run',allow_abbrev=False)
    start.add_argument('--repo',type=Path,required=True);start.add_argument('--plan-file','--plan',dest='plan_file',type=Path,required=True)
    start.add_argument('--output-dir',type=Path,required=True);start.add_argument('--profile',choices=REVIEW_EXECUTION_PROFILES,required=True)
    start.add_argument('--execute',action='store_true',help='Explicitly start provider processes; may consume credits, forbidden in CI.')
    start.add_argument('--parallel-specialists',type=int,default=1);start.add_argument('--timeout-seconds',type=int,default=180)
    start.add_argument('--validation-results',type=Path);start.add_argument('--at',required=True)
    start.add_argument('--format',choices=('legacy','receipt'),default='legacy')
    inspect=commands.add_parser('inspect');inspect.add_argument('--assessment',required=True)
    status=commands.add_parser('status');status.add_argument('--operation',required=True)
    args=parser.parse_args(arguments);app=ReviewExecutionContext(instance_root,settings)
    if args.command=='inspect':print(json.dumps(app.inspect(args.assessment),sort_keys=True));return 0
    if args.command=='status':print(json.dumps(app.status(args.operation),sort_keys=True));return 0
    value,native=app.create(args.repo,operator_bytes(args.plan_file,limit=MAX_JSON),args.output_dir,args.profile,args.at,
        execute=args.execute,parallel=args.parallel_specialists,timeout=args.timeout_seconds,
        validation_bytes=None if args.validation_results is None else operator_bytes(args.validation_results,limit=MAX_RESULTS))
    if args.format=='receipt':print(json.dumps(value,sort_keys=True))
    elif value['exit_code']!=2:print(json.dumps(logic.summary(native)))
    else:
        import sys
        print('error: Review execution stopped; inspect private operation '+value['operation_id'],file=sys.stderr)
    return value['exit_code']
