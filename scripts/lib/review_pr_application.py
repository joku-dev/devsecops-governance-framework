"""Private actual committed PR-scope observation and retained status replay; no PR authority."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from lib import review_committed as committed,review_metadata as logic
from lib.candidate_workspace import private_directory
from lib.ci_bundle_storage import reserve
from lib.consumer_intake_store import atomic_json
from lib.functional_parity import git_read
from lib.portable.contracts import ROOT,canonical_digest
from lib.portable.runtime import source_digest,read_json
from lib.provider_ports import REVIEW_PLAN_PROFILES,REVIEW_EVENT_PROFILES,review_commit_profile,committed_review_event
from lib.result_assessments import identity,operator_bytes
from lib.result_bytes import safe_bytes,strict_json
from lib.result_snapshot_store import explicit_time
from lib.review_metadata_application import FLAGS
from lib.supplement_application import write_lock

MAX_JSON=8*1024**2;MAX_EVENT=8*1024**2;MAX_TOTAL=64*1024**2;MAX_OUTPUT=8*1024**2


def wire(value):return (json.dumps(value,sort_keys=True,indent=2,allow_nan=False)+'\n').encode()


class ReviewPRContext:
    def __init__(self,instance_root,settings):
        self.instance=Path(instance_root).resolve();private_directory(self.instance/'state');self.root=private_directory(self.instance/'state/review-pr')
        self.inputs=private_directory(self.root/'inputs');self.artifacts=private_directory(self.root/'artifacts');self.assessments=private_directory(self.root/'assessments')
        self.binding={'node_id':settings['node_id'],'source_revision':git_read(ROOT,'rev-parse','HEAD').decode().strip(),'runtime_source_digest':source_digest()}
        self.clean=not bool(git_read(ROOT,'status','--porcelain','--untracked-files=all').strip())

    def assert_current(self):
        if source_digest()!=self.binding['runtime_source_digest'] or git_read(ROOT,'rev-parse','HEAD').decode().strip()!=self.binding['source_revision']:raise ValueError('review_pr_program_changed')

    def input_data(self,input_id):
        root=self.inputs/identity(input_id)
        if root.is_symlink() or not root.is_dir() or root.stat().st_mode&0o077:raise ValueError('private_review_pr_input_required')
        manifest=strict_json(safe_bytes(root/'manifest.json',limit=MAX_JSON))
        if not isinstance(manifest,dict) or set(manifest)!={'schema_version','profile','event_profile','repository','raw_map','files'} or type(manifest['schema_version']) is not int or manifest['schema_version']!=1 or canonical_digest(manifest)!=input_id:raise ValueError('invalid_review_pr_manifest')
        policy=review_commit_profile(manifest['profile']);repository=manifest['repository']
        if not isinstance(repository,str) or not Path(repository).is_absolute() or str(Path(repository))!=repository or '..' in Path(repository).parts:raise ValueError('invalid_review_pr_repository_label')
        if manifest['event_profile'] not in REVIEW_EVENT_PROFILES or not isinstance(manifest['raw_map'],dict) or len(manifest['raw_map'])>403:raise ValueError('invalid_review_pr_source_map')
        for name,sha in manifest['raw_map'].items():
            if not isinstance(name,str) or not isinstance(sha,str) or not re.fullmatch('[a-f0-9]{64}',sha):raise ValueError('invalid_review_pr_source_map')
        fixed={'event.json','facts.json'};names=fixed|{'blobs/'+sha+'.bin' for sha in manifest['raw_map'].values()};blobs=root/'blobs'
        if blobs.is_symlink() or not blobs.is_dir() or blobs.stat().st_mode&0o077:raise ValueError('private_review_pr_blobs_required')
        if not isinstance(manifest['files'],dict) or set(manifest['files'])!=names or {p.name for p in root.iterdir()}!=fixed|{'manifest.json','blobs'} or {'blobs/'+p.name for p in blobs.iterdir()}!=names-fixed:raise ValueError('review_pr_input_members_changed')
        files={};total=0
        for name,row in manifest['files'].items():
            if name not in fixed and not re.fullmatch(r'blobs/[a-f0-9]{64}\.bin',name):raise ValueError('invalid_review_pr_blob_name')
            limit=MAX_EVENT if name=='event.json' else MAX_JSON
            if not isinstance(row,dict) or set(row)!={'sha256','bytes'} or type(row['bytes']) is not int or not 0<=row['bytes']<=limit:raise ValueError('invalid_review_pr_input_length')
            raw=safe_bytes(root/name,limit=limit);total+=len(raw)
            if {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}!=row or name not in fixed and name!='blobs/'+row['sha256']+'.bin':raise ValueError('review_pr_input_changed')
            if total>MAX_TOTAL:raise ValueError('review_pr_total_input_budget')
            files[name]=raw
        raw={name:files['blobs/'+sha+'.bin'] for name,sha in manifest['raw_map'].items()};facts=strict_json(files['facts.json'])
        subject=committed.subject(facts,raw,policy);event=committed_review_event(manifest['event_profile'],strict_json(files['event.json']))
        if event['head_commit']!=subject['head_commit'] or event['base_commit']!=subject['target_commit']:raise ValueError('review_pr_event_revision_changed')
        return manifest,facts,raw,event,subject

    def capture_input(self,repository,profile,event_profile,event_raw,facts,raw):
        if not isinstance(event_raw,bytes) or len(event_raw)>MAX_EVENT:raise ValueError('review_pr_event_budget')
        subject=committed.subject(facts,raw,review_commit_profile(profile));event=committed_review_event(event_profile,strict_json(event_raw))
        if event['head_commit']!=subject['head_commit'] or event['base_commit']!=subject['target_commit']:raise ValueError('review_pr_event_revision_changed')
        files={'event.json':event_raw,'facts.json':wire(facts)}
        files.update({'blobs/'+hashlib.sha256(data).hexdigest()+'.bin':data for data in raw.values()})
        if len(files['facts.json'])>MAX_JSON or any(not isinstance(data,bytes) or len(data)>MAX_JSON for data in files.values()) or sum(map(len,files.values()))>MAX_TOTAL:raise ValueError('review_pr_capture_budget')
        manifest={'schema_version':1,'profile':profile,'event_profile':event_profile,'repository':str(repository),
            'raw_map':{name:hashlib.sha256(data).hexdigest() for name,data in raw.items()},'files':{name:{'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)} for name,data in files.items()}}
        if len(wire(manifest))>MAX_JSON:raise ValueError('review_pr_manifest_budget')
        input_id=canonical_digest(manifest);reserve(self.root,sum(map(len,files.values()))+MAX_JSON)
        with tempfile.TemporaryDirectory(prefix='.incoming-',dir=self.inputs) as temporary:
            staged=Path(temporary)/'data';staged.mkdir(mode=0o700);(staged/'blobs').mkdir(mode=0o700)
            for name,data in files.items():path=staged/name;path.write_bytes(data);path.chmod(0o600)
            atomic_json(staged/'manifest.json',manifest);self.assert_current()
            with write_lock(self.root):
                target=self.inputs/input_id
                if target.is_symlink():raise ValueError('unsafe_review_pr_input')
                if not target.exists():os.rename(staged,target)
                saved,stored_facts,stored_raw,_,_=self.input_data(input_id)
                if saved!=manifest or stored_facts!=facts or stored_raw!=raw:raise ValueError('immutable_review_pr_input_conflict')
        return input_id

    def render(self,input_id):
        manifest,facts,raw,event,subject=self.input_data(input_id);report=logic.status_from_subject(event,subject,read_json(ROOT/'schemas/agent-review-receipt.schema.json'))
        outputs={'review-status.json':(json.dumps(report,indent=2)+'\n').encode(),'review-status.md':logic.render_status(report).encode()}
        if any(len(data)>MAX_OUTPUT for data in outputs.values()):raise ValueError('review_pr_output_budget')
        return outputs,report['status']

    def validate(self,value):
        try:Draft202012Validator(read_json(ROOT/'schemas/axiom-v2-review-pr.schema.json'),format_checker=FormatChecker()).validate(value)
        except ValidationError:raise ValueError('invalid_review_pr_assessment') from None
        if type(value['schema_version']) is not int or any(value[key]!=expected for key,expected in self.binding.items()):raise ValueError('review_pr_binding_changed')
        explicit_time(value['assessed_at'])

    def inspect(self,assessment_id):
        assessment_id=identity(assessment_id);value=strict_json(safe_bytes(self.assessments/(assessment_id+'.json'),limit=MAX_JSON));self.validate(value)
        if canonical_digest(value)!=assessment_id:raise ValueError('review_pr_assessment_identity_changed')
        manifest,_,_,_,_=self.input_data(value['input_id']);outputs,status=self.render(value['input_id'])
        if value['profile']!=manifest['profile'] or value['event_profile']!=manifest['event_profile'] or value['declared_status']!=status or value['files']!={name:{'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)} for name,data in outputs.items()}:raise ValueError('review_pr_output_manifest_changed')
        root=self.artifacts/assessment_id
        if root.is_symlink() or not root.is_dir() or root.stat().st_mode&0o077 or {p.name for p in root.iterdir()}!=set(outputs):raise ValueError('review_pr_output_members_changed')
        for name,data in outputs.items():
            if safe_bytes(root/name,limit=MAX_OUTPUT)!=data:raise ValueError('review_pr_output_changed')
        self.assert_current();return {**value,'assessment_id':assessment_id,'data_directory':str(root),'retained_complete_outputs_reverified':True,'local_committed_scope_rechecked':False}

    def create(self,repository,event_raw,at,profile,event_profile):
        if not isinstance(event_raw,bytes) or len(event_raw)>MAX_EVENT:raise ValueError('review_pr_event_budget')
        if not isinstance(at,str) or len(at)>128:raise ValueError('review_pr_time_budget')
        explicit_time(at);repository=Path(repository).resolve()
        if self.instance.is_relative_to(repository) or repository.is_relative_to(self.root):raise ValueError('review_private_state_must_be_outside_target')
        event=committed_review_event(event_profile,strict_json(event_raw));policy=review_commit_profile(profile)
        facts,raw=committed.capture(repository,event['base_commit'],event['head_commit'],policy)
        input_id=self.capture_input(repository,profile,event_profile,event_raw,facts,raw);outputs,status=self.render(input_id)
        value={'schema_version':1,'kind':'committed-git-review-status',**self.binding,'input_id':input_id,'operation':'status','profile':profile,'event_profile':event_profile,'assessed_at':at,'source_worktree_clean':self.clean,
            'target_observation':'local-committed-git-at-command-execution','assessment_time_source':'operator','mode':'report-only','evidence_trust':'unverified','declared_status':status,
            'files':{name:{'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)} for name,data in outputs.items()},**FLAGS}
        self.validate(value);assessment_id=canonical_digest(value);reserve(self.root,sum(map(len,outputs.values()))+MAX_JSON)
        def recheck():
            if committed.observe(repository,event['base_commit'],event['head_commit'],policy)!=(facts,raw):raise ValueError('review_pr_target_changed_during_operation')
        with tempfile.TemporaryDirectory(prefix='.incoming-',dir=self.artifacts) as temporary:
            staged=Path(temporary)/'data';staged.mkdir(mode=0o700)
            for name,data in outputs.items():path=staged/name;path.write_bytes(data);path.chmod(0o600)
            self.assert_current();recheck()
            with write_lock(self.root):
                record=self.assessments/(assessment_id+'.json');target=self.artifacts/assessment_id
                if record.is_symlink() or target.is_symlink():raise ValueError('unsafe_review_pr_assessment')
                if record.exists():
                    if strict_json(safe_bytes(record,limit=MAX_JSON))!=value:raise ValueError('immutable_review_pr_assessment_conflict')
                else:
                    if target.exists():raise ValueError('unrecorded_review_pr_artifact')
                    os.rename(staged,target);atomic_json(record,value)
        return {**self.inspect(assessment_id),'local_committed_scope_rechecked':True}


def _run(arguments,instance_root,settings):
    parser=argparse.ArgumentParser(prog='axiom-v2 review-pr',allow_abbrev=False);commands=parser.add_subparsers(dest='command',required=True)
    status=commands.add_parser('status');status.add_argument('--repo',type=Path,required=True);status.add_argument('--event',type=Path,required=True);status.add_argument('--profile',choices=REVIEW_PLAN_PROFILES,required=True);status.add_argument('--event-profile',choices=REVIEW_EVENT_PROFILES,required=True);status.add_argument('--at',required=True)
    inspect=commands.add_parser('inspect');inspect.add_argument('--assessment',required=True)
    args=parser.parse_args(arguments);app=ReviewPRContext(instance_root,settings)
    value=app.inspect(args.assessment) if args.command=='inspect' else app.create(args.repo,operator_bytes(args.event,limit=MAX_EVENT),args.at,args.profile,args.event_profile)
    print(json.dumps(value,sort_keys=True));return 0


def run(arguments,instance_root,settings):
    try:return _run(arguments,instance_root,settings)
    except (ValidationError,UnicodeError,RecursionError,OverflowError):raise ValueError('invalid_review_pr_input') from None
