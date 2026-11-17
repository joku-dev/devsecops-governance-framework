"""Private immutable snapshots of declared role-selection metadata; no agent runs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

from jsonschema import Draft202012Validator, FormatChecker, ValidationError
from lib import agent_usage
from lib.candidate_workspace import private_directory
from lib.ci_bundle_storage import reserve
from lib.consumer_intake_store import atomic_json
from lib.functional_parity import git_read
from lib.portable.contracts import ROOT, canonical_digest
from lib.portable.runtime import read_json, source_digest
from lib.result_assessments import identity, operator_bytes
from lib.result_bytes import safe_bytes, strict_json
from lib.result_snapshot_store import explicit_time
from lib.supplement_application import write_lock
from lib.v2_boundary import safe_source

LOG='generated/agent-usage/agent-usage.jsonl'
OUTPUTS={'result.json':'generated/agent-usage/agent-usage-summary.json','result.md':'docs/operations/agent-usage-snapshot-latest.md'}
MAX_LOG=16*1024**2;MAX_EVENTS=100000;MAX_RECORD=4*1024**2;MAX_OUTPUT=64*1024**2
FLAGS={'official_acceptance':False,'production_approval':False,'risk_acceptance':False,'authority_transferred':False,'operating_acceptance_inherited':False,'published':False,'agent_execution_verified':False,'human_approval_verified':False}

def finite_jsonl_constant(value):
    raise ValueError('invalid_agent_usage_jsonl')


def events(raw):
    if len(raw)>MAX_LOG:raise ValueError('agent_usage_log_byte_budget')
    result=[]
    try:
        for line in raw.decode('utf-8').splitlines():
            if not line.strip():continue
            if len(result)>=MAX_EVENTS:raise ValueError('agent_usage_event_budget')
            value=json.loads(line,parse_constant=finite_jsonl_constant)
            if not isinstance(value,dict):raise ValueError('agent_usage_event_object_required')
            result.append(value)
    except (UnicodeError,json.JSONDecodeError,RecursionError):raise ValueError('invalid_agent_usage_jsonl') from None
    return result


def render(raw,label,at,latest_count):
    if type(latest_count) is not int:raise ValueError('invalid_agent_usage_latest_count')
    if not isinstance(label,str) or not 1<=len(label)<=4096 or any(ord(c)<32 or ord(c)==127 for c in label):raise ValueError('invalid_agent_usage_log_label')
    explicit_time(at)
    try:files=agent_usage.files(events(raw),label,at,latest_count)
    except (TypeError,AttributeError):raise ValueError('invalid_agent_usage_event_metadata') from None
    result={OUTPUTS[name]:value.encode('utf-8') for name,value in files.items()}
    if any(len(v)>MAX_OUTPUT for v in result.values()) or sum(map(len,result.values()))>128*1024**2:raise ValueError('agent_usage_output_budget')
    return result


class AgentUsageContext:
    def __init__(self,instance_root,settings):
        self.instance=Path(instance_root).resolve();private_directory(self.instance/'state')
        self.root=private_directory(self.instance/'state/agent-usage');self.inputs=private_directory(self.root/'inputs');self.artifacts=private_directory(self.root/'artifacts');self.assessments=private_directory(self.root/'assessments')
        self.binding={'node_id':settings['node_id'],'runtime_source_digest':source_digest(),'source_revision':git_read(ROOT,'rev-parse','HEAD').decode().strip()}
        self.clean=not bool(git_read(ROOT,'status','--porcelain','--untracked-files=all').strip())

    def assert_current(self):
        if source_digest()!=self.binding['runtime_source_digest'] or git_read(ROOT,'rev-parse','HEAD').decode().strip()!=self.binding['source_revision']:raise ValueError('agent_usage_product_changed')

    def input_data(self,input_id):
        root=self.inputs/identity(input_id)
        if root.is_symlink() or not root.is_dir() or root.stat().st_mode&0o077:raise ValueError('private_agent_usage_input_required')
        if {p.name for p in root.iterdir()}!={'manifest.json','events.jsonl'}:raise ValueError('unexpected_agent_usage_input_members')
        manifest=strict_json(safe_bytes(root/'manifest.json',limit=MAX_RECORD));raw=safe_bytes(root/'events.jsonl',limit=MAX_LOG)
        if canonical_digest(manifest)!=input_id or set(manifest)!={'schema_version','sha256','bytes','origin'} or manifest['schema_version']!=1:raise ValueError('invalid_agent_usage_input_manifest')
        if type(manifest['bytes']) is not int or not 0<=manifest['bytes']<=MAX_LOG:raise ValueError('invalid_agent_usage_input_length')
        if manifest['bytes']!=len(raw) or manifest['sha256']!=hashlib.sha256(raw).hexdigest():raise ValueError('agent_usage_input_changed')
        origin=manifest['origin']
        if isinstance(origin,dict) and set(origin)=={'kind','present'} and origin['kind']=='operator':
            if type(origin['present']) is not bool or (not origin['present'] and raw):raise ValueError('invalid_agent_usage_input_presence')
        elif isinstance(origin,dict) and set(origin)=={'kind','revision','path','git_blob'} and origin['kind']=='committed' and origin['revision']==self.binding['source_revision'] and origin['path']==LOG:
            expected=git_read(ROOT,'rev-parse',origin['revision']+':'+LOG).decode().strip()
            if expected!=origin['git_blob'] or git_read(ROOT,'cat-file','blob',expected)!=raw:raise ValueError('agent_usage_committed_source_changed')
        else:raise ValueError('invalid_agent_usage_input_origin')
        events(raw);return raw,manifest

    def capture(self,raw,origin):
        events(raw);manifest={'schema_version':1,'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'origin':origin};input_id=canonical_digest(manifest);reserve(self.root,len(raw)+MAX_RECORD)
        with tempfile.TemporaryDirectory(prefix='.incoming-',dir=self.inputs) as temporary:
            staged=Path(temporary)/'data';staged.mkdir(mode=0o700);path=staged/'events.jsonl';path.write_bytes(raw);path.chmod(0o600);atomic_json(staged/'manifest.json',manifest);self.assert_current()
            with write_lock(self.root):
                target=self.inputs/input_id
                if target.is_symlink():raise ValueError('unsafe_agent_usage_input')
                if not target.exists():os.rename(staged,target)
                saved,record=self.input_data(input_id)
                if saved!=raw or record!=manifest:raise ValueError('immutable_agent_usage_input_conflict')
        return input_id

    def validate(self,value):
        try:Draft202012Validator(read_json(ROOT/'schemas/axiom-v2-agent-usage.schema.json'),format_checker=FormatChecker()).validate(value)
        except ValidationError:raise ValueError('invalid_agent_usage_assessment') from None
        if any(value.get(k)!=v for k,v in self.binding.items()):raise ValueError('agent_usage_binding_changed')
        if len((json.dumps(value,sort_keys=True,indent=2)+'\n').encode())>MAX_RECORD:raise ValueError('agent_usage_assessment_budget')
        explicit_time(value['assessed_at'])

    def create(self,raw,origin,label,at,latest_count):
        files=render(raw,label,at,latest_count);input_id=self.capture(raw,origin)
        value={'schema_version':1,'kind':'declared-agent-selection-snapshot',**self.binding,'input_id':input_id,'source_log_label':label,'assessed_at':at,'latest_count_requested':latest_count,'latest_count_effective':max(latest_count,0),'source_worktree_clean':self.clean,'files':{n:{'sha256':hashlib.sha256(v).hexdigest(),'bytes':len(v)} for n,v in files.items()},'evidence_trust':'unverified','mode':'report-only',**FLAGS}
        self.validate(value);assessment_id=canonical_digest(value);reserve(self.root,sum(map(len,files.values()))+MAX_RECORD)
        with tempfile.TemporaryDirectory(prefix='.incoming-',dir=self.artifacts) as temporary:
            staged=Path(temporary)/'data';staged.mkdir(mode=0o700)
            for name,raw in files.items():
                path=safe_source(staged,name);path.parent.mkdir(parents=True,mode=0o700,exist_ok=True);path.write_bytes(raw);path.chmod(0o600)
            self.input_data(input_id);self.assert_current()
            with write_lock(self.root):
                record=self.assessments/(assessment_id+'.json');target=self.artifacts/assessment_id
                if record.is_symlink() or target.is_symlink():raise ValueError('unsafe_agent_usage_assessment')
                if record.exists():
                    if strict_json(safe_bytes(record,limit=MAX_RECORD))!=value:raise ValueError('immutable_agent_usage_assessment_conflict')
                else:
                    if target.exists():raise ValueError('unrecorded_agent_usage_artifact')
                    os.rename(staged,target);atomic_json(record,value)
        return assessment_id,self.inspect(assessment_id)

    def inspect(self,assessment_id):
        assessment_id=identity(assessment_id);value=strict_json(safe_bytes(self.assessments/(assessment_id+'.json'),limit=MAX_RECORD));self.validate(value)
        if canonical_digest(value)!=assessment_id:raise ValueError('agent_usage_assessment_identity_changed')
        if value['latest_count_effective']!=max(value['latest_count_requested'],0):raise ValueError('agent_usage_count_changed')
        raw,manifest=self.input_data(value['input_id']);files=render(raw,value['source_log_label'],value['assessed_at'],value['latest_count_requested']);descriptors={n:{'sha256':hashlib.sha256(v).hexdigest(),'bytes':len(v)} for n,v in files.items()}
        if descriptors!=value['files']:raise ValueError('agent_usage_output_manifest_changed')
        root=self.artifacts/assessment_id
        if root.is_symlink() or not root.is_dir() or root.stat().st_mode&0o077:raise ValueError('private_agent_usage_artifact_required')
        expected_dirs={str(p) for n in files for p in Path(n).parents if str(p)!='.'};actual_dirs=set();actual_files=set()
        for path in root.rglob('*'):
            if path.is_symlink():raise ValueError('unsafe_agent_usage_artifact')
            name=path.relative_to(root).as_posix()
            if path.is_dir():actual_dirs.add(name)
            else:actual_files.add(name)
        if actual_dirs!=expected_dirs or actual_files!=set(files):raise ValueError('unexpected_agent_usage_artifact_members')
        for name,raw in files.items():
            if safe_bytes(safe_source(root,name),limit=MAX_OUTPUT)!=raw:raise ValueError('agent_usage_output_changed')
        self.assert_current();return {**value,'assessment_id':assessment_id,'data_directory':str(root),'source_origin':manifest['origin']}


def run(arguments,instance_root,settings):
    parser=argparse.ArgumentParser(prog='axiom-v2 agent-usage',allow_abbrev=False);commands=parser.add_subparsers(dest='command',required=True)
    create=commands.add_parser('create');create.add_argument('--usage-log',type=Path);create.add_argument('--source-log-label');create.add_argument('--latest-count',type=int,default=10);create.add_argument('--at',required=True)
    inspect=commands.add_parser('inspect');inspect.add_argument('--assessment',required=True)
    args=parser.parse_args(arguments);app=AgentUsageContext(instance_root,settings)
    if args.command=='inspect':print(json.dumps(app.inspect(args.assessment),sort_keys=True));return 0
    if args.usage_log:
        if args.usage_log.is_symlink():raise ValueError('unsafe_agent_usage_log')
        present=args.usage_log.exists()
        raw=operator_bytes(args.usage_log,limit=MAX_LOG) if present else b'';origin={'kind':'operator','present':present};label=args.source_log_label or str(args.usage_log.resolve())
    else:
        revision=app.binding['source_revision'];blob=git_read(ROOT,'rev-parse',revision+':'+LOG).decode().strip();raw=git_read(ROOT,'cat-file','blob',blob);origin={'kind':'committed','revision':revision,'path':LOG,'git_blob':blob};label=args.source_log_label or LOG
    _,value=app.create(raw,origin,label,args.at,args.latest_count);print(json.dumps(value,sort_keys=True));return 0
