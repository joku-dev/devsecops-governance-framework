"""Private offline synthetic review packets and scores; no model/agent invocation."""
import argparse
from copy import deepcopy
import hashlib,json,os,re,tempfile
from pathlib import Path
import yaml
from jsonschema import Draft202012Validator,FormatChecker,ValidationError
from lib import review_quality as rubric
from lib.candidate_workspace import private_directory
from lib.ci_bundle_storage import reserve
from lib.consumer_intake_store import atomic_json
from lib.functional_parity import git_read
from lib.portable.contracts import ROOT,canonical_digest
from lib.portable.runtime import read_json,source_digest
from lib.result_assessments import identity,operator_bytes
from lib.result_bytes import safe_bytes,strict_json
from lib.result_snapshot_store import explicit_time
from lib.supplement_application import write_lock
from lib.v2_boundary import safe_source

DEFAULT_DATASET='.agents/evaluations/review-quality-v1.json'
MAX_JSON=4*1024**2;MAX_TRACE=1024**2;MAX_INPUT=256*1024**2;MAX_OUTPUT=8*1024**2;MAX_OUTPUT_TOTAL=128*1024**2;MAX_CASES=200
FLAGS={'official_acceptance':False,'production_approval':False,'risk_acceptance':False,'authority_transferred':False,'operating_acceptance_inherited':False,'published':False,'provider_invoked':False,'model_execution_verified':False,'trace_authenticity_verified':False,'independent_human_approval':False}

class ContractLoader(yaml.SafeLoader):pass

def unique_mapping(loader,node,deep=False):
    result={}
    for key,value in node.value:
        name=loader.construct_object(key,deep=deep)
        if name in result:raise ValueError('duplicate_review_role_key')
        result[name]=loader.construct_object(value,deep=deep)
    return result
ContractLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,unique_mapping)


def program_data():
    revision=git_read(ROOT,'rev-parse','HEAD').decode().strip();entries={}
    raw=git_read(ROOT,'ls-tree','-r','-z',revision,'--','.agents/roles','.agents/skills',DEFAULT_DATASET)
    for item in filter(None,raw.split(b'\0')):
        metadata,name=item.split(b'\t',1);mode,kind,blob=metadata.decode().split();entries[name.decode()]={'mode':mode,'kind':kind,'git_blob':blob}
    files={}
    def read(name,limit=65536):
        row=entries.get(name)
        if not row or row['mode'] not in ('100644','100755') or row['kind']!='blob':raise ValueError('regular_review_program_input_required')
        if int(git_read(ROOT,'cat-file','-s',row['git_blob']))>limit:raise ValueError('review_program_input_budget')
        data=git_read(ROOT,'cat-file','blob',row['git_blob'])
        if data!=safe_bytes(ROOT/name,limit=limit):raise ValueError('review_program_committed_bytes_changed')
        if len(data)>limit:raise ValueError('review_program_input_budget')
        files[name]={**row,'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)};return data
    roles={};skills={};role_sha={};skill_sha={}
    paths=sorted(n for n in entries if re.fullmatch(r'\.agents/roles/[a-z0-9-]+\.yaml',n))
    if not 1<=len(paths)<=200:raise ValueError('review_program_role_budget')
    for name in paths:
        raw=read(name)
        try:role=yaml.load(raw.decode('utf-8'),Loader=ContractLoader)
        except (yaml.YAMLError,RecursionError,OverflowError):raise ValueError('invalid_review_program_role') from None
        if not isinstance(role,dict) or role.get('id')!=Path(name).stem:raise ValueError('invalid_review_program_role')
        if any(not isinstance(role.get(k),str) or not role[k].strip() for k in ('id','name','description','source_of_truth','skill')):raise ValueError('invalid_review_program_role')
        if not re.fullmatch('[a-z0-9]+(?:-[a-z0-9]+)*',role['skill']):raise ValueError('invalid_review_program_skill')
        for key in ('primary_files','responsibilities','validations','output_contract'):
            values=role.get(key)
            if not isinstance(values,list) or not values or any(not isinstance(v,str) or not v.strip() for v in values):raise ValueError('invalid_review_program_role')
        roles[role['id']]=role;role_sha[role['id']]=hashlib.sha256(raw).hexdigest()
        skill=read('.agents/skills/'+role['skill']+'/SKILL.md');skills[role['skill']]=skill.decode('utf-8').replace('\r\n','\n').replace('\r','\n');skill_sha[role['skill']]=hashlib.sha256(skill).hexdigest()
    if 'repo-steward' not in roles:raise ValueError('review_program_steward_required')
    default=read(DEFAULT_DATASET,MAX_JSON)
    if len(files)>401:raise ValueError('review_program_file_budget')
    return {'revision':revision,'roles':roles,'skills':skills,'role_sha':role_sha,'skill_sha':skill_sha,'default':default,'program_id':canonical_digest({'revision':revision,'files':files})}


def label(value):
    if not isinstance(value,str) or not 1<=len(value)<=4096 or any(ord(c)<32 or ord(c)==127 for c in value):raise ValueError('invalid_review_trace_label')
    return value


def _render(kind,program,raw_files,traces):
    dataset=strict_json(raw_files['dataset.json']);rubric.validate_dataset(dataset,program['roles'])
    if len(dataset['cases'])>MAX_CASES or any(len(c['id'].encode())+12>255 for c in dataset['cases']):raise ValueError('review_quality_case_budget')
    if kind=='prepare':
        if set(raw_files)!={'dataset.json'} or traces:raise ValueError('unexpected_review_prepare_input')
        values=rubric.prepare_files(dataset,program['roles'],program['skills'],program['role_sha'],program['skill_sha'],max_file_bytes=MAX_OUTPUT,max_total_bytes=MAX_OUTPUT_TOTAL)
    elif kind=='grade':
        if 'responses.json' not in raw_files:raise ValueError('review_responses_required')
        report=rubric.grade_evaluation(dataset,strict_json(raw_files['responses.json']),program['roles'],program['skills'],lambda name:raw_files[traces[name]] if name in traces else None)
        values={'evaluation-grade.json':rubric.wire(report)}
    else:raise ValueError('unsupported_review_quality_operation')
    result={name:value.encode('utf-8') for name,value in values.items()}
    if len(result)>401 or any(len(raw)>MAX_OUTPUT for raw in result.values()) or sum(map(len,result.values()))>MAX_OUTPUT_TOTAL:raise ValueError('review_quality_output_budget')
    for raw in result.values():strict_json(raw)
    return result

def render(kind,program,raw_files,traces):
    try:return _render(kind,program,raw_files,traces)
    except (RecursionError,OverflowError):raise ValueError('invalid_review_quality_json_depth_or_number') from None


class ReviewQualityContext:
    def __init__(self,instance_root,settings):
        self.instance=Path(instance_root).resolve();private_directory(self.instance/'state');self.root=private_directory(self.instance/'state/review-quality')
        self.inputs=private_directory(self.root/'inputs');self.artifacts=private_directory(self.root/'artifacts');self.assessments=private_directory(self.root/'assessments')
        self.binding={'node_id':settings['node_id'],'runtime_source_digest':source_digest(),'source_revision':git_read(ROOT,'rev-parse','HEAD').decode().strip()};self.program=program_data()
        self.clean=not bool(git_read(ROOT,'status','--porcelain','--untracked-files=all').strip())

    def assert_current(self):
        if source_digest()!=self.binding['runtime_source_digest'] or git_read(ROOT,'rev-parse','HEAD').decode().strip()!=self.binding['source_revision'] or program_data()['program_id']!=self.program['program_id']:raise ValueError('review_quality_program_changed')

    def input_data(self,input_id):
        root=self.inputs/identity(input_id)
        if root.is_symlink() or not root.is_dir() or root.stat().st_mode&0o077:raise ValueError('private_review_quality_input_required')
        manifest=strict_json(safe_bytes(root/'manifest.json',limit=MAX_JSON))
        if set(manifest)!={'schema_version','program_id','dataset_origin','files','traces'} or type(manifest['schema_version']) is not int or manifest['schema_version']!=1 or canonical_digest(manifest)!=input_id:raise ValueError('invalid_review_quality_input_manifest')
        if manifest['program_id']!=self.program['program_id'] or manifest['dataset_origin'] not in ('committed','operator'):raise ValueError('review_quality_input_program_changed')
        files=manifest['files'];traces=manifest['traces']
        if not isinstance(files,dict) or not isinstance(traces,dict) or len(traces)>MAX_CASES or len(files)>MAX_CASES+2:raise ValueError('review_quality_input_file_budget')
        expected={'dataset.json'}|({'responses.json'} if 'responses.json' in files else set())
        for name,path in traces.items():
            label(name)
            if not isinstance(path,str) or not re.fullmatch(r'traces/[0-9a-f]{64}\.json',path):raise ValueError('invalid_retained_review_trace')
            expected.add(path)
        if set(files)!=expected:raise ValueError('unexpected_review_quality_input_files')
        data=root/'data'
        if data.is_symlink() or not data.is_dir() or data.stat().st_mode&0o077 or {p.name for p in root.iterdir()}!={'manifest.json','data'}:raise ValueError('private_review_quality_input_required')
        actual_files=set();actual_dirs=set()
        for path in data.rglob('*'):
            if path.is_symlink():raise ValueError('unsafe_review_quality_input')
            name=path.relative_to(data).as_posix()
            if path.is_dir():actual_dirs.add(name)
            else:actual_files.add(name)
        expected_dirs={'traces'} if traces else set()
        if actual_files!=set(files) or actual_dirs!=expected_dirs:raise ValueError('unexpected_review_quality_input_members')
        raw_files={};total=0
        for name,row in files.items():
            limit=MAX_TRACE if name.startswith('traces/') else MAX_JSON
            if not isinstance(row,dict) or set(row)!={'sha256','bytes'} or type(row['bytes']) is not int or not 0<=row['bytes']<=limit:raise ValueError('invalid_review_quality_input_length')
            raw=safe_bytes(safe_source(data,name),limit=limit)
            if {'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)}!=row or (name.startswith('traces/') and name!='traces/'+row['sha256']+'.json'):raise ValueError('review_quality_input_bytes_changed')
            total+=len(raw);raw_files[name]=raw
        if total>MAX_INPUT:raise ValueError('review_quality_input_budget')
        if manifest['dataset_origin']=='committed' and raw_files['dataset.json']!=self.program['default']:raise ValueError('review_quality_committed_dataset_changed')
        return raw_files,manifest

    def capture(self,dataset_raw,response_raw,traces,dataset_origin):
        if len(dataset_raw)>MAX_JSON or (response_raw is not None and len(response_raw)>MAX_JSON) or len(traces)>MAX_CASES:raise ValueError('review_quality_input_budget')
        if dataset_origin not in ('committed','operator'):raise ValueError('invalid_review_dataset_origin')
        files={'dataset.json':dataset_raw};trace_map={}
        if response_raw is not None:files['responses.json']=response_raw
        for name,raw in traces.items():
            label(name)
            if len(raw)>MAX_TRACE:raise ValueError('review_trace_byte_budget')
            path='traces/'+hashlib.sha256(raw).hexdigest()+'.json';files[path]=raw;trace_map[name]=path
        if sum(map(len,files.values()))>MAX_INPUT:raise ValueError('review_quality_input_budget')
        manifest={'schema_version':1,'program_id':self.program['program_id'],'dataset_origin':dataset_origin,'files':{n:{'sha256':hashlib.sha256(v).hexdigest(),'bytes':len(v)} for n,v in files.items()},'traces':trace_map}
        if len((json.dumps(manifest,indent=2)+'\n').encode())>MAX_JSON:raise ValueError('review_quality_input_manifest_budget')
        input_id=canonical_digest(manifest);reserve(self.root,sum(map(len,files.values()))+MAX_JSON)
        with tempfile.TemporaryDirectory(prefix='.incoming-',dir=self.inputs) as temporary:
            staged=Path(temporary)/'snapshot';staged.mkdir(mode=0o700);data=staged/'data';data.mkdir(mode=0o700)
            for name,raw in files.items():
                path=safe_source(data,name);path.parent.mkdir(mode=0o700,parents=True,exist_ok=True);path.write_bytes(raw);path.chmod(0o600)
            atomic_json(staged/'manifest.json',manifest);self.assert_current()
            with write_lock(self.root):
                target=self.inputs/input_id
                if target.is_symlink():raise ValueError('unsafe_review_quality_input')
                if not target.exists():os.rename(staged,target)
                actual,saved=self.input_data(input_id)
                if actual!=files or saved!=manifest:raise ValueError('immutable_review_quality_input_conflict')
        return input_id

    def validate(self,value):
        try:Draft202012Validator(read_json(ROOT/'schemas/axiom-v2-review-quality.schema.json'),format_checker=FormatChecker()).validate(value)
        except ValidationError:raise ValueError('invalid_review_quality_assessment') from None
        if any(value.get(k)!=v for k,v in self.binding.items()) or value['program_id']!=self.program['program_id']:raise ValueError('review_quality_assessment_binding_changed')
        explicit_time(value['assessed_at'])
        if len((json.dumps(value,indent=2)+'\n').encode())>MAX_JSON:raise ValueError('review_quality_record_budget')

    def create(self,kind,dataset_raw,response_raw,traces,dataset_origin,at):
        explicit_time(at)
        input_id=self.capture(dataset_raw,response_raw,traces,dataset_origin);raw_files,manifest=self.input_data(input_id);files=render(kind,self.program,raw_files,manifest['traces'])
        value={'schema_version':1,'kind':'offline-review-quality',**self.binding,'program_id':self.program['program_id'],'input_id':input_id,'operation':kind,'assessed_at':at,'source_worktree_clean':self.clean,'files':{n:{'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)} for n,raw in files.items()},'mode':'report-only','evidence_trust':'unverified',**FLAGS}
        self.validate(value);assessment_id=canonical_digest(value);reserve(self.root,sum(map(len,files.values()))+MAX_JSON)
        with tempfile.TemporaryDirectory(prefix='.incoming-',dir=self.artifacts) as temporary:
            staged=Path(temporary)/'data';staged.mkdir(mode=0o700)
            for name,raw in files.items():
                if '/' in name or '\\' in name or len(name.encode())>255:raise ValueError('unsafe_review_quality_output_name')
                path=staged/name;path.write_bytes(raw);path.chmod(0o600)
            self.assert_current();self.input_data(input_id)
            with write_lock(self.root):
                target=self.artifacts/assessment_id;record=self.assessments/(assessment_id+'.json')
                if target.is_symlink() or record.is_symlink():raise ValueError('unsafe_review_quality_assessment')
                if record.exists():
                    if strict_json(safe_bytes(record,limit=MAX_JSON))!=value:raise ValueError('immutable_review_quality_assessment_conflict')
                else:
                    if target.exists():raise ValueError('unrecorded_review_quality_artifact')
                    os.rename(staged,target);atomic_json(record,value)
        return assessment_id,self.inspect(assessment_id)

    def inspect(self,assessment_id):
        assessment_id=identity(assessment_id);value=strict_json(safe_bytes(self.assessments/(assessment_id+'.json'),limit=MAX_JSON));self.validate(value)
        if canonical_digest(value)!=assessment_id:raise ValueError('review_quality_assessment_identity_changed')
        raw_files,manifest=self.input_data(value['input_id']);files=render(value['operation'],self.program,raw_files,manifest['traces'])
        if {n:{'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)} for n,raw in files.items()}!=value['files']:raise ValueError('review_quality_output_manifest_changed')
        root=self.artifacts/assessment_id
        if root.is_symlink() or not root.is_dir() or root.stat().st_mode&0o077 or {p.name for p in root.iterdir()}!=set(files):raise ValueError('unexpected_review_quality_output_members')
        for name,raw in files.items():
            if safe_bytes(safe_source(root,name),limit=MAX_OUTPUT)!=raw:raise ValueError('review_quality_output_changed')
        self.assert_current();return {**value,'assessment_id':assessment_id,'data_directory':str(root),'dataset_origin':manifest['dataset_origin']}


def run(arguments,instance_root,settings):
    parser=argparse.ArgumentParser(prog='axiom-v2 review-quality',allow_abbrev=False);commands=parser.add_subparsers(dest='command',required=True)
    for name in ('prepare','grade'):
        command=commands.add_parser(name);command.add_argument('--dataset',type=Path);command.add_argument('--at',required=True)
        if name=='grade':command.add_argument('--responses',type=Path,required=True);command.add_argument('--trace',nargs=2,action='append',default=[],metavar=('LABEL','FILE'))
    inspect=commands.add_parser('inspect');inspect.add_argument('--assessment',required=True)
    args=parser.parse_args(arguments);context=ReviewQualityContext(instance_root,settings)
    if args.command=='inspect':print(json.dumps(context.inspect(args.assessment),sort_keys=True));return 0
    dataset=operator_bytes(args.dataset,limit=MAX_JSON) if args.dataset else context.program['default'];responses=operator_bytes(args.responses,limit=MAX_JSON) if args.command=='grade' else None;traces={}
    for name,path in getattr(args,'trace',[]):
        label(name)
        if name in traces:raise ValueError('duplicate_review_trace_label')
        if len(traces)>=MAX_CASES:raise ValueError('review_trace_count_budget')
        traces[name]=operator_bytes(Path(path),limit=MAX_TRACE)
    _,value=context.create(args.command,dataset,responses,traces,'operator' if args.dataset else 'committed',args.at);print(json.dumps(value,sort_keys=True));return 0
