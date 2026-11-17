"""Private retained review metadata; no Git-scope inspection or review execution."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from lib import review_metadata as logic
from lib.candidate_workspace import private_directory
from lib.ci_bundle_storage import reserve
from lib.consumer_intake_store import atomic_json
from lib.functional_parity import git_read
from lib.portable.contracts import ROOT, canonical_digest
from lib.portable.runtime import read_json, source_digest
from lib.provider_ports import REVIEW_EVENT_PROFILES, review_event
from lib.result_assessments import identity, operator_bytes
from lib.result_bytes import safe_bytes, strict_json
from lib.result_snapshot_store import explicit_time
from lib.supplement_application import write_lock

MAX_JSON=2*1024**2;MAX_LOG=16*1024**2;MAX_OUTPUT=8*1024**2
INPUTS={'receipt':{'receipt.json'},'parse-body':{'description.txt'},'usage-summary':{'usage.jsonl'},'status':{'event.json','subject.json'}}
FLAGS={name:False for name in ('official_acceptance','production_approval','risk_acceptance','authority_transferred','operating_acceptance_inherited','published','provider_invoked','agent_execution_verified','human_approval_verified','current_revision_checked','private_review_outputs_verified')}


def render(operation,raw_files,event_profile):
    if operation not in INPUTS or set(raw_files)!=INPUTS[operation]:raise ValueError('unexpected_review_metadata_inputs')
    if any(len(v)>(MAX_LOG if n=='usage.jsonl' else MAX_JSON) for n,v in raw_files.items()):raise ValueError('review_metadata_input_budget')
    schema=read_json(ROOT/'schemas/agent-review-receipt.schema.json')
    if operation!='status' and event_profile is not None:raise ValueError('unexpected_review_event_profile')
    try:
        if operation=='receipt':
            value=strict_json(raw_files['receipt.json']);files={'review-receipt.md':logic.receipt_block(value,schema)+'\n'}
        elif operation=='parse-body':
            value=logic.parse_receipt(raw_files['description.txt'].decode('utf-8'),schema)
            files={'parsed-review-receipt.json':json.dumps(value,indent=2)+'\n'}
        elif operation=='usage-summary':
            rows=logic.parse_usage(raw_files['usage.jsonl'],schema)
            files={'review-usage-summary.json':json.dumps(logic.summarize_review_usage(rows,schema),indent=2)+'\n'}
        else:
            event=review_event(event_profile,strict_json(raw_files['event.json']));subject=strict_json(raw_files['subject.json'])
            Draft202012Validator(read_json(ROOT/'schemas/axiom-v2-review-subject.schema.json')).validate(subject)
            for side in ('target','proposed'):
                scope=subject[side]
                if subject['changed_paths']:
                    if 'repo-steward' not in scope['roles'] or not scope['validations']:raise ValueError('declared_review_scope_incomplete')
                elif scope['roles'] or scope['validations']:raise ValueError('declared_review_scope_has_no_paths')
            report=logic.status_from_subject(event,subject,schema)
            files={'review-status.json':json.dumps(report,indent=2)+'\n','review-status.md':logic.render_status(report)}
    except (ValidationError,UnicodeError,RecursionError,OverflowError):raise ValueError('invalid_review_metadata_input') from None
    result={name:text.encode('utf-8') for name,text in files.items()}
    if any(len(v)>MAX_OUTPUT for v in result.values()):raise ValueError('review_metadata_output_budget')
    return result


class ReviewMetadataContext:
    def __init__(self,instance_root,settings):
        instance_root=Path(instance_root).resolve()
        private_directory(Path(instance_root)/'state');self.root=private_directory(Path(instance_root)/'state/review-metadata')
        self.inputs=private_directory(self.root/'inputs');self.artifacts=private_directory(self.root/'artifacts');self.assessments=private_directory(self.root/'assessments')
        self.binding={'node_id':settings['node_id'],'runtime_source_digest':source_digest(),'source_revision':git_read(ROOT,'rev-parse','HEAD').decode().strip()}
        self.clean=not bool(git_read(ROOT,'status','--porcelain','--untracked-files=all').strip())

    def assert_current(self):
        if source_digest()!=self.binding['runtime_source_digest'] or git_read(ROOT,'rev-parse','HEAD').decode().strip()!=self.binding['source_revision']:raise ValueError('review_metadata_program_changed')

    def input_data(self,input_id):
        root=self.inputs/identity(input_id)
        if root.is_symlink() or not root.is_dir() or root.stat().st_mode&0o077:raise ValueError('private_review_metadata_input_required')
        manifest=strict_json(safe_bytes(root/'manifest.json',limit=MAX_JSON))
        if set(manifest)!={'schema_version','operation','files','origin'} or type(manifest['schema_version']) is not int or manifest['schema_version']!=1 or canonical_digest(manifest)!=input_id:raise ValueError('invalid_review_metadata_input_manifest')
        names=INPUTS.get(manifest['operation'])
        if names is None or set(manifest['files'])!=names or {p.name for p in root.iterdir()}!=names|{'manifest.json'}:raise ValueError('unexpected_review_metadata_input_members')
        origin=manifest['origin']
        if not isinstance(origin,dict) or set(origin)!={'kind','present'} or origin['kind']!='operator' or type(origin['present']) is not bool:raise ValueError('invalid_review_metadata_origin')
        if not origin['present'] and manifest['operation']!='usage-summary':raise ValueError('invalid_review_metadata_missing_source')
        raw_files={}
        for name,row in manifest['files'].items():
            limit=MAX_LOG if name=='usage.jsonl' else MAX_JSON
            if not isinstance(row,dict) or set(row)!={'bytes','sha256'} or type(row['bytes']) is not int or not 0<=row['bytes']<=limit:raise ValueError('invalid_review_metadata_input_length')
            raw=safe_bytes(root/name,limit=limit)
            if {'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}!=row:raise ValueError('review_metadata_input_changed')
            raw_files[name]=raw
        if not origin['present'] and any(raw_files.values()):raise ValueError('invalid_review_metadata_missing_source')
        return raw_files,manifest

    def capture(self,operation,raw_files,origin):
        if not isinstance(origin,dict) or set(origin)!={'kind','present'} or origin['kind']!='operator' or type(origin['present']) is not bool or (not origin['present'] and (operation!='usage-summary' or any(raw_files.values()))):raise ValueError('invalid_review_metadata_origin')
        if operation not in INPUTS or set(raw_files)!=INPUTS[operation] or any(not isinstance(v,bytes) or len(v)>(MAX_LOG if n=='usage.jsonl' else MAX_JSON) for n,v in raw_files.items()):raise ValueError('review_metadata_capture_budget_or_members')
        manifest={'schema_version':1,'operation':operation,'origin':origin,'files':{n:{'sha256':hashlib.sha256(v).hexdigest(),'bytes':len(v)} for n,v in raw_files.items()}}
        input_id=canonical_digest(manifest);reserve(self.root,sum(map(len,raw_files.values()))+MAX_JSON)
        with tempfile.TemporaryDirectory(prefix='.incoming-',dir=self.inputs) as temporary:
            staged=Path(temporary)/'data';staged.mkdir(mode=0o700)
            for name,raw in raw_files.items():
                path=staged/name;path.write_bytes(raw);path.chmod(0o600)
            atomic_json(staged/'manifest.json',manifest);self.assert_current()
            with write_lock(self.root):
                target=self.inputs/input_id
                if target.is_symlink():raise ValueError('unsafe_review_metadata_input')
                if not target.exists():os.rename(staged,target)
                saved,m=self.input_data(input_id)
                if saved!=raw_files or m!=manifest:raise ValueError('immutable_review_metadata_input_conflict')
        return input_id

    def validate(self,value):
        try:Draft202012Validator(read_json(ROOT/'schemas/axiom-v2-review-metadata.schema.json'),format_checker=FormatChecker()).validate(value)
        except ValidationError:raise ValueError('invalid_review_metadata_assessment') from None
        if type(value['schema_version']) is not int or any(value.get(k)!=v for k,v in self.binding.items()):raise ValueError('review_metadata_binding_changed')
        explicit_time(value['assessed_at'])
        if len(json.dumps(value).encode())>MAX_JSON:raise ValueError('review_metadata_record_budget')

    def create(self,operation,raw_files,at,event_profile=None,*,present=True):
        explicit_time(at);files=render(operation,raw_files,event_profile);input_id=self.capture(operation,raw_files,{'kind':'operator','present':present})
        value={'schema_version':1,'kind':'declared-review-metadata',**self.binding,'input_id':input_id,'operation':operation,'event_profile':event_profile,'assessed_at':at,'source_worktree_clean':self.clean,'files':{n:{'sha256':hashlib.sha256(v).hexdigest(),'bytes':len(v)} for n,v in files.items()},'mode':'report-only','evidence_trust':'unverified',**FLAGS}
        self.validate(value);assessment_id=canonical_digest(value);reserve(self.root,sum(map(len,files.values()))+MAX_JSON)
        with tempfile.TemporaryDirectory(prefix='.incoming-',dir=self.artifacts) as temporary:
            staged=Path(temporary)/'data';staged.mkdir(mode=0o700)
            for name,raw in files.items():
                path=staged/name;path.write_bytes(raw);path.chmod(0o600)
            self.assert_current();self.input_data(input_id)
            with write_lock(self.root):
                record=self.assessments/(assessment_id+'.json');target=self.artifacts/assessment_id
                if record.is_symlink() or target.is_symlink():raise ValueError('unsafe_review_metadata_assessment')
                if record.exists():
                    if strict_json(safe_bytes(record,limit=MAX_JSON))!=value:raise ValueError('immutable_review_metadata_assessment_conflict')
                else:
                    if target.exists():raise ValueError('unrecorded_review_metadata_artifact')
                    os.rename(staged,target);atomic_json(record,value)
        return assessment_id,self.inspect(assessment_id)

    def inspect(self,assessment_id):
        assessment_id=identity(assessment_id);value=strict_json(safe_bytes(self.assessments/(assessment_id+'.json'),limit=MAX_JSON));self.validate(value)
        if canonical_digest(value)!=assessment_id:raise ValueError('review_metadata_assessment_identity_changed')
        raw_files,manifest=self.input_data(value['input_id'])
        if value['operation']!=manifest['operation']:raise ValueError('review_metadata_operation_changed')
        files=render(value['operation'],raw_files,value['event_profile'])
        if {n:{'sha256':hashlib.sha256(v).hexdigest(),'bytes':len(v)} for n,v in files.items()}!=value['files']:raise ValueError('review_metadata_output_manifest_changed')
        root=self.artifacts/assessment_id
        if root.is_symlink() or not root.is_dir() or root.stat().st_mode&0o077 or {p.name for p in root.iterdir()}!=set(files):raise ValueError('unexpected_review_metadata_output_members')
        for name,raw in files.items():
            if safe_bytes(root/name,limit=MAX_OUTPUT)!=raw:raise ValueError('review_metadata_output_changed')
        self.assert_current();return {**value,'assessment_id':assessment_id,'data_directory':str(root),'retained_complete_outputs_reverified':True,'source_origin':manifest['origin']}


def run(arguments,instance_root,settings):
    parser=argparse.ArgumentParser(prog='axiom-v2 review-metadata',allow_abbrev=False);commands=parser.add_subparsers(dest='command',required=True)
    for operation,flag in [('receipt','--receipt'),('parse-body','--body'),('usage-summary','--usage-log'),('status','--event')]:
        command=commands.add_parser(operation);command.add_argument(flag,type=Path,required=True);command.add_argument('--at',required=True)
        if operation=='status':command.add_argument('--subject',type=Path,required=True);command.add_argument('--event-profile',choices=REVIEW_EVENT_PROFILES,required=True)
    inspect=commands.add_parser('inspect');inspect.add_argument('--assessment',required=True)
    args=parser.parse_args(arguments);app=ReviewMetadataContext(instance_root,settings)
    if args.command=='inspect':print(json.dumps(app.inspect(args.assessment),sort_keys=True));return 0
    present=True
    if args.command=='receipt':raw_files={'receipt.json':operator_bytes(args.receipt,limit=MAX_JSON)}
    elif args.command=='parse-body':raw_files={'description.txt':operator_bytes(args.body,limit=MAX_JSON)}
    elif args.command=='usage-summary':
        if args.usage_log.is_symlink():raise ValueError('unsafe_review_metadata_log')
        present=args.usage_log.exists();raw_files={'usage.jsonl':operator_bytes(args.usage_log,limit=MAX_LOG) if present else b''}
    else:raw_files={'event.json':operator_bytes(args.event,limit=MAX_JSON),'subject.json':operator_bytes(args.subject,limit=MAX_JSON)}
    _,value=app.create(args.command,raw_files,args.at,getattr(args,'event_profile',None),present=present);print(json.dumps(value,sort_keys=True));return 0
