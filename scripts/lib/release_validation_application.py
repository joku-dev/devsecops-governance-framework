"""Private revision-bound release verification, durable starts and declared replay."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import secrets

from lib.candidate_workspace import private_directory
from lib.ci_bundle_storage import reserve
from lib.consumer_intake_store import atomic_json
from lib.functional_parity import git_read
from lib.portable.contracts import ROOT,canonical_digest
from lib.portable.runtime import source_digest
from lib.provider_ports import ReleaseSource,ReleaseVerificationEnvironment
from lib import release_reference_facts as reference_facts
from lib.release_inputs import collect
from lib.release_replay import ReplayReleaseEnvironment
from lib.release_verification import ReleaseVerification
from lib.result_assessments import identity
from lib.result_bytes import safe_bytes,strict_json
from lib.result_snapshot_store import explicit_time
from lib.validation_application import AUTHORITY,descriptors,retained_files,write_files

MAX_MANIFEST=4*1024**2
MAX_REFERENCES=48*1024**2
MAX_RECORD=64*1024**2
MAX_START=2*1024**2
KIND='explicit-product-release-verification'
PENDING_FIELDS={'schema_version','kind','node_id','runtime_source_digest','source_revision','source_tree',
    'assessed_at','input_id','source_root','operation_id',*AUTHORITY}
START_FIELDS={'request','tool','tool_path','tool_sha256','ssh_tool_path','ssh_tool_sha256','argv',
    'process_started','returncode','timed_out','output_truncated','error_type'}


def check_manifest(manifest,data,references,*,revision,tree):
    reference_facts.validate(references)
    if (not isinstance(manifest,dict) or set(manifest)!={'schema_version','scope','source_root','commit','tree','references_digest','files','absent'}
            or type(manifest['schema_version']) is not int or manifest['schema_version']!=1
            or manifest['scope']!='explicit-release-verification-data-v1' or manifest['commit']!=revision
            or manifest['tree']!=tree or references['source_head']!=revision or references['source_tree']!=tree
            or manifest['references_digest']!=canonical_digest(references)
            or not isinstance(manifest['source_root'],str) or not Path(manifest['source_root']).is_absolute()
            or str(Path(manifest['source_root']))!=manifest['source_root'] or '..' in Path(manifest['source_root']).parts
            or len(manifest['source_root'])>8192 or any(ord(c)<32 for c in manifest['source_root'])
            or not isinstance(manifest['files'],dict) or canonical_digest(manifest['files'])!=canonical_digest(descriptors(data))
            or not isinstance(manifest['absent'],list) or not all(isinstance(v,str) for v in manifest['absent'])
            or manifest['absent']!=sorted(set(manifest['absent'])) or set(data)&set(manifest['absent'])):
        raise ValueError('invalid_release_input_manifest')
    def read(name):
        if name in data:return data[name]
        if name in manifest['absent']:return None
        raise ValueError('release_retained_input_missing')
    if collect(read)!=set(data)|set(manifest['absent']):raise ValueError('release_retained_input_graph_changed')


class ReleaseValidationContext:
    def __init__(self,instance_root,settings,*,product_root=ROOT):
        self.product=Path(product_root).resolve();self.settings=settings
        instance_root=private_directory(Path(instance_root)).resolve()
        self.root=private_directory(private_directory(instance_root/'state')/'release-validation')
        self.operations=private_directory(self.root/'operations')
        self.binding={'node_id':settings['node_id'],'runtime_source_digest':source_digest(),
            'source_revision':git_read(self.product,'rev-parse','HEAD').decode().strip()}
        self.tree=git_read(self.product,'rev-parse','HEAD^{tree}').decode().strip()

    def assert_current(self):
        if (self.binding['runtime_source_digest']!=source_digest()
                or self.binding['source_revision']!=git_read(self.product,'rev-parse','HEAD').decode().strip()):
            raise ValueError('release_validation_product_changed')

    def create(self,at,*,source_worktree):
        explicit_time(at);acquisition=ReleaseSource(source_worktree,self.binding['source_revision'])
        data,manifest,references=acquisition.capture()
        check_manifest(manifest,data,references,revision=self.binding['source_revision'],tree=self.tree)
        reserve(self.root,384*1024**2);self.assert_current()
        operation=secrets.token_hex(32);target=self.operations/operation;target.mkdir(mode=0o700)
        value={'schema_version':1,'kind':KIND,**self.binding,'source_tree':self.tree,'assessed_at':at,
            'input_id':canonical_digest(manifest),'source_root':manifest['source_root'],'operation_id':operation,**AUTHORITY}
        write_files(target/'inputs',data);atomic_json(target/'input-manifest.json',manifest)
        atomic_json(target/'references.json',references);atomic_json(target/'pending.json',value)
        # Both the input journal and operation intent exist before any capsule
        # write or native signature invocation. Starts are separate private files.
        starts=private_directory(target/'starts');workarea=private_directory(target/'native-work');sequence=0
        def on_start(row):
            nonlocal sequence
            sequence+=1
            if sequence>16384 or set(row)!=START_FIELDS:raise ValueError('release_native_start_contract_changed')
            packet={'operation_id':operation,'input_id':value['input_id'],'sequence':sequence,'observation':row}
            if len(json.dumps(packet).encode())>MAX_START:raise ValueError('release_native_start_budget')
            atomic_json(starts/f'{sequence:05}.json',packet)
        with ReleaseVerificationEnvironment(target/'inputs',data,references,workarea,on_start=on_start) as native:
            try:
                report=ReleaseVerification(native).verify_release_integrity()
                # A legacy Python value can be non-finite even though it has no
                # valid JSON representation. Retain that actual codec failure
                # as incomplete; never admit a record strict replay cannot read.
                json.dumps(report,allow_nan=False)
                outcome={'execution':'complete','exception_type':None,'exit_code':0,'report':report}
            except Exception as error:
                outcome={'execution':'incomplete','exception_type':type(error).__name__,'exit_code':2,'report':None}
            value.update(outcome,native_context=deepcopy(native.metadata),native_observations=deepcopy(native.observations))
        if len(json.dumps(value,allow_nan=False).encode())>MAX_RECORD:raise ValueError('release_record_budget')
        atomic_json(target/'native-results.json',value)
        self.assert_current()
        latest_data,latest_manifest,latest_references=acquisition.capture()
        if (latest_data!=data or canonical_digest(latest_manifest)!=canonical_digest(manifest)
                or canonical_digest(latest_references)!=canonical_digest(references)):
            raise ValueError('release_inputs_changed_before_admission')
        atomic_json(target/'assessment.json',value)
        return operation,deepcopy(value)

    def inspect(self,operation,*,with_replayed_report=False):
        from lib.provider_ports import capture_retained_security_tree
        from lib.retained_security import release
        target=self.operations/identity(operation)
        if target.is_symlink() or not target.is_dir() or target.stat().st_mode&0o077:
            raise ValueError('unsafe_release_operation')
        if not (target/'assessment.json').exists():
            raise ValueError('release_operation_pending_requires_review')
        self.assert_current()
        value,report=release(capture_retained_security_tree(target),
            {**self.binding,'source_tree':self.tree},operation)
        self.assert_current()
        return (value,report) if with_replayed_report else value

    def status(self):
        rows=[]
        for path in sorted(self.operations.iterdir()):
            operation=identity(path.name)
            try:
                value=self.inspect(operation);state='retained_declared_replay_consistent'
            except (ValueError,OSError):state='pending_incomplete_or_invalid'
            rows.append({'operation_id':operation,'state':state})
        return rows


def run(arguments,instance_root,settings):
    parser=argparse.ArgumentParser(prog='axiom-v2 validation',allow_abbrev=False)
    sub=parser.add_subparsers(dest='operation',required=True)
    create=sub.add_parser('releases',allow_abbrev=False);create.add_argument('--at',required=True)
    create.add_argument('--source-worktree',type=Path,required=True);create.add_argument('--output',choices=('json','report'),default='json')
    inspect=sub.add_parser('release-inspect',allow_abbrev=False);inspect.add_argument('--assessment',required=True)
    sub.add_parser('release-status',allow_abbrev=False);args=parser.parse_args(arguments)
    context=ReleaseValidationContext(instance_root,settings)
    if args.operation=='release-status':print(json.dumps({'operations':context.status(),**AUTHORITY},indent=2));return 0
    if args.operation=='release-inspect':print(json.dumps(context.inspect(args.assessment),indent=2));return 0
    operation,value=context.create(args.at,source_worktree=args.source_worktree)
    print(json.dumps(value['report'] if args.output=='report' else {'assessment_id':operation,**value},indent=2))
    return value['exit_code']
