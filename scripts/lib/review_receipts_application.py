"""Actual explicit receipt export, idempotent usage, and private retained replay."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from lib import review_git, review_planning, review_receipts as logic, review_receipt_files as effects
from lib.candidate_workspace import private_directory
from lib.ci_bundle_storage import reserve
from lib.consumer_intake_store import atomic_json
from lib.portable.contracts import ROOT, canonical_digest
from lib.portable.runtime import read_json
from lib.provider_ports import REVIEW_PLAN_PROFILES, review_plan_profile
from lib.result_assessments import identity, operator_bytes
from lib.result_bytes import safe_bytes, strict_json
from lib.result_snapshot_store import explicit_time
from lib.review_metadata_application import FLAGS
from lib.review_planning_application import ReviewPlanningContext
from lib.supplement_application import write_lock

MAX_PLAN=8*1024**2; MAX_RESULTS=4*1024**2; MAX_JSON=2*1024**2; MAX_OUTPUT=8*1024**2
FILE_LIMITS={'plan.json':MAX_PLAN,'results.json':MAX_RESULTS,'target-status.bin':65536,
    'receipt-before.json':logic.MAX_RECEIPT,'receipt-after.json':logic.MAX_RECEIPT,
    'usage-before.jsonl':logic.MAX_LOG,'usage-after.jsonl':logic.MAX_LOG,'usage.jsonl':logic.MAX_LOG}


class ReviewReceiptContext:
    def __init__(self, instance_root, settings):
        self.instance=Path(instance_root).resolve();self.planning=ReviewPlanningContext(self.instance,settings)
        self.binding=self.planning.binding;self.clean=self.planning.clean
        self.root=private_directory(self.instance/'state/review-receipts');self.inputs=private_directory(self.root/'inputs')
        self.artifacts=private_directory(self.root/'artifacts');self.assessments=private_directory(self.root/'assessments')

    def schemas(self):return read_json(ROOT/'schemas/agent-review-receipt.schema.json'),read_json(ROOT/'schemas/axiom-v2-review-results.schema.json')

    def validate_input(self, manifest, files):
        if set(manifest)!={'schema_version','operation','profile','planning_input_id','plan_origin','node_plan_assessment_id','target','destinations','presence_before','files'} or type(manifest['schema_version']) is not int or manifest['schema_version']!=1:
            raise ValueError('invalid_review_receipt_manifest')
        operation=manifest['operation'];presence=manifest['presence_before']
        if operation=='summary':
            if any(manifest[k] is not None for k in ('profile','planning_input_id','plan_origin','node_plan_assessment_id','target','destinations')) or not isinstance(presence,dict) or set(presence)!={'usage'} or type(presence['usage']) is not bool or set(files)!={'usage.jsonl'}:
                raise ValueError('invalid_review_receipt_summary_inputs')
            if not presence['usage'] and files['usage.jsonl']:raise ValueError('fabricated_review_usage_file_presence')
            return
        if operation!='export':raise ValueError('invalid_review_receipt_operation')
        identity(manifest['planning_input_id']);review_plan_profile(manifest['profile'])
        if manifest['plan_origin'] not in ('operator_file','node_assessment') or (manifest['node_plan_assessment_id'] is None)!=(manifest['plan_origin']=='operator_file'):
            raise ValueError('invalid_review_receipt_plan_origin')
        if manifest['node_plan_assessment_id'] is not None:identity(manifest['node_plan_assessment_id'])
        target=manifest['target'];destinations=manifest['destinations']
        if not isinstance(target,str) or not Path(target).is_absolute() or '..' in Path(target).parts or str(Path(target))!=target:raise ValueError('invalid_retained_review_target')
        if not isinstance(destinations,dict) or set(destinations)!={'receipt','usage'} or not isinstance(destinations['receipt'],str):raise ValueError('invalid_retained_review_destinations')
        for path in destinations.values():
            if path is None:continue
            if not isinstance(path,str) or not Path(path).is_absolute() or '..' in Path(path).parts or str(Path(path))!=path or Path(path).is_relative_to(target) or Path(path).is_relative_to(ROOT):raise ValueError('invalid_retained_review_destinations')
        if not isinstance(presence,dict) or set(presence)!={'receipt','usage'} or type(presence['receipt']) is not bool:raise ValueError('invalid_review_receipt_presence')
        requested=destinations['usage'] is not None
        if (requested and type(presence['usage']) is not bool) or (not requested and presence['usage'] is not None):raise ValueError('invalid_review_receipt_presence')
        expected={'plan.json','results.json','target-status.bin','receipt-before.json','receipt-after.json'}|({'usage-before.jsonl','usage-after.jsonl'} if requested else set())
        if set(files)!=expected or files['target-status.bin'] or (not presence['receipt'] and files['receipt-before.json']) or (requested and not presence['usage'] and files['usage-before.jsonl']):raise ValueError('invalid_review_receipt_input_members_or_origin')

    def capture_input(self, metadata, files):
        if any(name not in FILE_LIMITS or not isinstance(raw,bytes) or len(raw)>FILE_LIMITS[name] for name,raw in files.items()):raise ValueError('review_receipt_input_budget')
        self.validate_input(metadata,files)
        manifest={**metadata,'files':{name:{'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)} for name,raw in files.items()}}
        if len(json.dumps(manifest).encode())>MAX_JSON:raise ValueError('review_receipt_manifest_budget')
        input_id=canonical_digest(manifest);reserve(self.root,sum(map(len,files.values()))+MAX_JSON)
        with tempfile.TemporaryDirectory(prefix='.incoming-',dir=self.inputs) as temporary:
            staged=Path(temporary)/'data';staged.mkdir(mode=0o700)
            for name,raw in files.items():path=staged/name;path.write_bytes(raw);path.chmod(0o600)
            atomic_json(staged/'manifest.json',manifest);self.planning.assert_current()
            with write_lock(self.root):
                target=self.inputs/input_id
                if target.is_symlink():raise ValueError('unsafe_review_receipt_input')
                if not target.exists():os.rename(staged,target)
                saved=self.input_data(input_id)
                if saved!=(manifest,files):raise ValueError('immutable_review_receipt_input_conflict')
        return input_id

    def input_data(self,input_id):
        root=self.inputs/identity(input_id)
        if root.is_symlink() or not root.is_dir() or root.stat().st_mode&0o077:raise ValueError('private_review_receipt_input_required')
        manifest=strict_json(safe_bytes(root/'manifest.json',limit=MAX_JSON))
        if canonical_digest(manifest)!=input_id or not isinstance(manifest.get('files'),dict) or len(manifest['files'])>7:raise ValueError('invalid_review_receipt_input_identity')
        if {p.name for p in root.iterdir()}!=set(manifest['files'])|{'manifest.json'}:raise ValueError('review_receipt_input_members_changed')
        files={}
        for name,row in manifest['files'].items():
            if name not in FILE_LIMITS or not isinstance(row,dict) or set(row)!={'sha256','bytes'} or type(row['bytes']) is not int or not 0<=row['bytes']<=FILE_LIMITS[name]:raise ValueError('invalid_review_receipt_input_length')
            raw=safe_bytes(root/name,limit=FILE_LIMITS[name])
            if len(raw)!=row['bytes'] or hashlib.sha256(raw).hexdigest()!=row['sha256']:raise ValueError('review_receipt_input_changed')
            files[name]=raw
        self.validate_input(manifest,files);return manifest,files

    def render(self,input_id,recorded_at):
        manifest,files=self.input_data(input_id);receipt_schema,results_schema=self.schemas()
        if manifest['operation']=='summary':
            report=logic.usage_summary(files['usage.jsonl'],receipt_schema)
            return {'review-usage-summary.json':(json.dumps(report,indent=2)+'\n').encode()},{'receipt_id':None,'receipt_created':False,'usage_appended':False,'declared_ready':False}
        stored,facts,raw,goal,_=self.planning.input_data(manifest['planning_input_id'])
        if stored['operation']!='prepare' or stored['profile']!=manifest['profile']:raise ValueError('receipt_requires_retained_current_plan_facts')
        expected,_=review_planning.plan(facts,raw,goal,review_plan_profile(manifest['profile']));plan=strict_json(files['plan.json'])
        if expected!=plan:raise ValueError('review_receipt_plan_does_not_match_retained_git')
        if manifest['node_plan_assessment_id'] is not None:
            old=self.planning.inspect(manifest['node_plan_assessment_id'])
            if old['operation']!='prepare':raise ValueError('receipt_requires_prepared_node_plan')
            _,previous,previous_raw,previous_goal,_=self.planning.input_data(old['input_id'])
            previous_plan,_=review_planning.plan(previous,previous_raw,previous_goal,review_plan_profile(old['profile']))
            if expected!=previous_plan or facts['files']!=previous['files'] or facts['role_paths']!=previous['role_paths']:raise ValueError('receipt_node_plan_contracts_stale')
        candidate=logic.build_receipt(plan,strict_json(files['results.json']),recorded_at,receipt_schema,results_schema)
        selected,after,created=logic.choose_receipt(candidate,files['receipt-before.json'] if manifest['presence_before']['receipt'] else None,receipt_schema)
        if after!=files['receipt-after.json']:raise ValueError('review_receipt_output_derivation_changed')
        appended=False
        if manifest['destinations']['usage'] is not None:
            expected_usage,appended=logic.usage_projection(files['usage-before.jsonl'] if manifest['presence_before']['usage'] else None,selected,receipt_schema)
            if expected_usage!=files['usage-after.jsonl']:raise ValueError('review_usage_output_derivation_changed')
        result=logic.export_result(selected,appended)
        return {'review-receipt.json':after,'review-export-result.json':(json.dumps(result)+'\n').encode()}, {'receipt_id':selected['receipt_id'],'receipt_created':created,'usage_appended':appended,'declared_ready':selected['eligible_for_human_review']}

    def create(self,metadata,files,at):
        explicit_time(at);input_id=self.capture_input(metadata,files);outputs,outcome=self.render(input_id,at)
        if any(len(raw)>MAX_OUTPUT for raw in outputs.values()):raise ValueError('review_receipt_output_budget')
        value={'schema_version':1,'kind':'explicit-review-receipt-export',**self.binding,'input_id':input_id,
            'operation':metadata['operation'],'assessed_at':at,'source_worktree_clean':self.clean,'assessment_time_source':'operator',
            'mode':'report-only','evidence_trust':'unverified','files':{name:{'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)} for name,raw in outputs.items()},**outcome,
            'receipt_file_exported':metadata['operation']=='export','target_observation':'local-git-at-command-execution' if metadata['operation']=='export' else 'not-applicable',**FLAGS}
        self.validate(value);assessment_id=canonical_digest(value);reserve(self.root,sum(map(len,outputs.values()))+MAX_JSON)
        with tempfile.TemporaryDirectory(prefix='.incoming-',dir=self.artifacts) as temporary:
            staged=Path(temporary)/'data';staged.mkdir(mode=0o700)
            for name,raw in outputs.items():path=staged/name;path.write_bytes(raw);path.chmod(0o600)
            self.planning.assert_current()
            with write_lock(self.root):
                target=self.artifacts/assessment_id;record=self.assessments/(assessment_id+'.json')
                if target.is_symlink() or record.is_symlink():raise ValueError('unsafe_review_receipt_assessment')
                if record.exists():
                    if strict_json(safe_bytes(record,limit=MAX_JSON))!=value:raise ValueError('immutable_review_receipt_assessment_conflict')
                else:
                    if target.exists():raise ValueError('unrecorded_review_receipt_artifact')
                    os.rename(staged,target);atomic_json(record,value)
        return self.inspect(assessment_id)

    def validate(self,value):
        try:Draft202012Validator(read_json(ROOT/'schemas/axiom-v2-review-receipt-export.schema.json'),format_checker=FormatChecker()).validate(value)
        except ValidationError:raise ValueError('invalid_review_receipt_assessment') from None
        if type(value['schema_version']) is not int or any(value[k]!=v for k,v in self.binding.items()):raise ValueError('review_receipt_binding_changed')
        explicit_time(value['assessed_at'])

    def inspect(self,assessment_id):
        assessment_id=identity(assessment_id);value=strict_json(safe_bytes(self.assessments/(assessment_id+'.json'),limit=MAX_JSON));self.validate(value)
        if canonical_digest(value)!=assessment_id:raise ValueError('review_receipt_assessment_identity_changed')
        outputs,outcome=self.render(value['input_id'],value['assessed_at']);manifest,_=self.input_data(value['input_id'])
        if value['operation']!=manifest['operation'] or value['receipt_file_exported']!=(manifest['operation']=='export') or value['target_observation']!=('local-git-at-command-execution' if manifest['operation']=='export' else 'not-applicable') or any(value[key]!=expected for key,expected in outcome.items()) or {name:{'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)} for name,raw in outputs.items()}!=value['files']:raise ValueError('review_receipt_output_manifest_changed')
        root=self.artifacts/assessment_id
        if root.is_symlink() or not root.is_dir() or root.stat().st_mode&0o077 or {p.name for p in root.iterdir()}!=set(outputs):raise ValueError('review_receipt_output_members_changed')
        for name,raw in outputs.items():
            if safe_bytes(root/name,limit=MAX_OUTPUT)!=raw:raise ValueError('review_receipt_output_changed')
        self.planning.assert_current()
        return {**value,'assessment_id':assessment_id,'data_directory':str(root),'retained_complete_outputs_reverified':True,'target_current_state_rechecked':False,'external_files_rechecked':False}

    def export(self,repo,plan_raw,results_raw,output,usage_log,at,profile,*,node_plan=None):
        if not isinstance(plan_raw,bytes) or len(plan_raw)>MAX_PLAN or not isinstance(results_raw,bytes) or len(results_raw)>MAX_RESULTS:raise ValueError('review_receipt_input_budget')
        if not isinstance(at,str) or len(at)>128:raise ValueError('review_receipt_assessment_time_budget')
        explicit_time(at);plan=strict_json(plan_raw);results=strict_json(results_raw);repo=Path(repo).resolve()
        if self.instance.is_relative_to(repo) or repo.is_relative_to(self.root):raise ValueError('review_private_state_must_be_outside_target')
        if plan.get('selection_mode')!='working_tree' or not plan.get('base_commit'):raise ValueError('receipt_full_branch_with_base_required')
        policy=review_plan_profile(profile);status=review_git.git(repo,'status','--porcelain','--untracked-files=normal','-z')
        if status:raise ValueError('receipt_clean_checkout_required')
        facts,raw=review_git.capture(repo,plan['base_commit'],[],policy);expected,_=review_planning.plan(facts,raw,plan['user_goal'],policy)
        if expected!=plan:raise ValueError('review_receipt_plan_stale')
        candidate=logic.build_receipt(plan,results,at,*self.schemas())
        if node_plan is not None:
            previous=self.planning.inspect(node_plan)
            if previous['operation']!='prepare':raise ValueError('receipt_requires_prepared_node_plan')
            _,old,old_raw,old_goal,_=self.planning.input_data(previous['input_id'])
            old_plan,_=review_planning.plan(old,old_raw,old_goal,review_plan_profile(previous['profile']))
            if old_plan!=plan or old['files']!=facts['files'] or old['role_paths']!=facts['role_paths']:raise ValueError('receipt_node_plan_contracts_stale')
        reserve(self.root,2*logic.MAX_LOG+2*logic.MAX_RECEIPT+MAX_PLAN+MAX_RESULTS+MAX_JSON)
        planning_id=self.planning.capture_input('prepare',profile,facts,raw,plan['user_goal'],None,None)
        def recheck():
            if review_git.observe(repo,plan['base_commit'],[],policy)!=(facts,raw) or review_git.git(repo,'status','--porcelain','--untracked-files=normal','-z'):raise ValueError('review_receipt_target_changed_during_export')
        recheck();selected,before,after,created,path=effects.write_receipt(output,candidate,self.schemas()[0],[repo,ROOT])
        files={'plan.json':plan_raw,'results.json':results_raw,'target-status.bin':status,'receipt-before.json':before if before is not None else b'','receipt-after.json':after}
        destinations={'receipt':str(path),'usage':None};presence={'receipt':before is not None,'usage':None}
        if usage_log is not None:
            old_usage,new_usage,appended,log_path=effects.append_usage(usage_log,selected,self.schemas()[0],[repo,ROOT])
            files.update({'usage-before.jsonl':old_usage if old_usage is not None else b'','usage-after.jsonl':new_usage});destinations['usage']=str(log_path);presence['usage']=old_usage is not None
        recheck()
        metadata={'schema_version':1,'operation':'export','profile':profile,'planning_input_id':planning_id,
            'plan_origin':'node_assessment' if node_plan is not None else 'operator_file','node_plan_assessment_id':node_plan,
            'target':str(repo),'destinations':destinations,'presence_before':presence,'files':{}}
        value=self.create(metadata,files,at);return {**value,'target_current_state_rechecked':True,'external_files_rechecked':True}

    def summary(self,path,at):
        path=Path(path).expanduser()
        if path.is_symlink():raise ValueError('review_usage_symlink_input_forbidden')
        present=path.exists();raw=operator_bytes(path,limit=logic.MAX_LOG) if present else b'';logic.usage_summary(raw,self.schemas()[0])
        metadata={'schema_version':1,'operation':'summary','profile':None,'planning_input_id':None,'plan_origin':None,'node_plan_assessment_id':None,'target':None,'destinations':None,'presence_before':{'usage':present},'files':{}}
        return self.create(metadata,{'usage.jsonl':raw},at)


def _run(arguments,instance_root,settings):
    parser=argparse.ArgumentParser(prog='axiom-v2 review-receipts',allow_abbrev=False);commands=parser.add_subparsers(dest='command',required=True)
    export=commands.add_parser('export');export.add_argument('--repo',type=Path,required=True);source=export.add_mutually_exclusive_group(required=True);source.add_argument('--plan-file',type=Path);source.add_argument('--plan');export.add_argument('--results',type=Path,required=True);export.add_argument('--output',type=Path,required=True);export.add_argument('--usage-log',type=Path);export.add_argument('--profile',choices=REVIEW_PLAN_PROFILES,required=True);export.add_argument('--at',required=True)
    summary=commands.add_parser('summary');summary.add_argument('--usage-log',type=Path,required=True);summary.add_argument('--at',required=True)
    inspect=commands.add_parser('inspect');inspect.add_argument('--assessment',required=True)
    args=parser.parse_args(arguments);app=ReviewReceiptContext(instance_root,settings)
    if args.command=='inspect':value=app.inspect(args.assessment)
    elif args.command=='summary':value=app.summary(args.usage_log,args.at)
    else:
        if args.plan is not None:
            prepared=app.planning.inspect(args.plan)
            if prepared['operation']!='prepare':raise ValueError('receipt_requires_prepared_node_plan')
            plan_raw=safe_bytes(Path(prepared['data_directory'])/'review-plan.json',limit=MAX_PLAN)
        else:plan_raw=operator_bytes(args.plan_file,limit=MAX_PLAN)
        value=app.export(args.repo,plan_raw,operator_bytes(args.results,limit=MAX_RESULTS),args.output,args.usage_log,args.at,args.profile,node_plan=args.plan)
    print(json.dumps(value,sort_keys=True));return 0


def run(arguments,instance_root,settings):
    try:return _run(arguments,instance_root,settings)
    except (ValidationError,UnicodeError,RecursionError,OverflowError):raise ValueError('invalid_review_receipt_input') from None
