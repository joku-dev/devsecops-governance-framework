"""Private diagnostic attestation verification and explicit native output effects."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import tempfile

from jsonschema import Draft202012Validator,FormatChecker,ValidationError
from lib import attestation_assessment as logic,attestation_files as effects
from lib.candidate_workspace import private_directory
from lib.ci_bundle_storage import reserve
from lib.consumer_intake_store import atomic_json
from lib.functional_parity import git_read
from lib.portable.contracts import ROOT,canonical_digest
from lib.portable.runtime import read_json,source_digest
from lib.provider_ports import (ATTESTATION_PROFILES,attestation_profile,verify_attestation_signature,
    attestation_crypto_initial,attestation_crypto_outcome)
from lib.result_assessments import identity
from lib.result_bytes import safe_bytes,strict_json
from lib.result_snapshot_store import explicit_time
from lib.review_metadata_application import FLAGS
from lib.supplement_application import write_lock

MAX_JSON=4*1024**2
INPUT_NAMES={'attestation.json','registry.yaml','context.json','subject.json','output-before.bin'}


def hashes(files):return {name:{'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)} for name,raw in files.items()}


def derive(manifest,files,verify):
    value=logic.input_object(files['attestation.json']);registry=logic.registry(files['registry.yaml']);statement=value['statement']
    context=logic.input_object(files['context.json']) if manifest['context_origin']=='operator_file' else {key:statement[key] for key in logic.CONTEXT_FIELDS}
    subject=logic.input_object(files['subject.json']) if manifest['subject_origin']=='operator_file' else statement['subject']
    result=logic.assess(attestation=value,registry=registry,expected_context=context,expected_subject=subject,
        evaluated_at=manifest['evaluated_at'],attestation_ref=manifest['attestation_reference'],
        current_effective_level=manifest['declared_effective_level'],verify=verify)
    Draft202012Validator(read_json(ROOT/'schemas/evidence-attestation-assessment.schema.json'),format_checker=FormatChecker()).validate(result)
    return result


class AttestationContext:
    def __init__(self,instance_root,settings):
        self.instance=Path(instance_root).resolve();private_directory(self.instance/'state')
        self.root=private_directory(self.instance/'state/attestation-verification')
        self.inputs=private_directory(self.root/'inputs');self.artifacts=private_directory(self.root/'artifacts')
        self.assessments=private_directory(self.root/'assessments');self.intents=private_directory(self.root/'intents')
        self.scratch=private_directory(self.root/'scratch');self.locks=private_directory(self.root/'locks')
        self.binding={'node_id':settings['node_id'],'source_revision':git_read(ROOT,'rev-parse','HEAD').decode().strip(),'runtime_source_digest':source_digest()}
        self.clean=not bool(git_read(ROOT,'status','--porcelain','--untracked-files=all').strip())

    def current(self):
        if source_digest()!=self.binding['runtime_source_digest'] or git_read(ROOT,'rev-parse','HEAD').decode().strip()!=self.binding['source_revision']:
            raise ValueError('attestation_program_changed')

    def input_data(self,input_id):
        root=self.inputs/identity(input_id)
        if root.is_symlink() or not root.is_dir() or root.stat().st_mode&0o077:raise ValueError('private_attestation_inputs_required')
        value=strict_json(safe_bytes(root/'manifest.json',limit=MAX_JSON))
        keys={'schema_version','profile','attestation_reference','registry_origin','context_origin','subject_origin','declared_effective_level',
            'evaluated_at','assessment_time_source','output_destination','output_before_metadata','files'}
        if set(value)!=keys or type(value['schema_version']) is not int or value['schema_version']!=1 or canonical_digest(value)!=input_id:
            raise ValueError('attestation_input_identity_changed')
        attestation_profile(value['profile']);explicit_time(value['evaluated_at'])
        if value['registry_origin'] not in ('operator_file','product_default_diagnostic_data') or value['context_origin'] not in ('operator_file','statement_declaration') or value['subject_origin'] not in ('operator_file','statement_declaration'):
            raise ValueError('invalid_attestation_input_origin')
        if value['assessment_time_source'] not in ('operator','system_clock') or value['declared_effective_level'] not in ('unverified','integrity_verified','provenance_verified'):
            raise ValueError('invalid_attestation_input_declaration')
        if not isinstance(value['attestation_reference'],str) or not 1<=len(value['attestation_reference'].encode())<=4096:
            raise ValueError('invalid_attestation_input_reference')
        dest=value['output_destination']
        if not isinstance(dest,str) or not Path(dest).is_absolute() or str(Path(dest))!=dest or '..' in Path(dest).parts or '\0' in dest:
            raise ValueError('invalid_attestation_output_destination')
        if Path(dest).is_relative_to(ROOT) or Path(dest).is_relative_to(self.instance) or any(part.casefold()=='.git' for part in Path(dest).parts):raise ValueError('invalid_attestation_output_destination')
        expected={'attestation.json','registry.yaml'}|({'context.json'} if value['context_origin']=='operator_file' else set())|({'subject.json'} if value['subject_origin']=='operator_file' else set())
        metadata=value['output_before_metadata']
        if metadata is not None:
            if not isinstance(metadata,dict) or set(metadata)!={'st_dev','st_ino','st_size','st_mtime_ns','st_ctime_ns','st_mode','st_nlink'} or any(type(v) is not int for v in metadata.values()):raise ValueError('invalid_attestation_before_metadata')
            if any(metadata[key]<0 for key in ('st_dev','st_ino','st_size','st_mode','st_nlink')):raise ValueError('invalid_attestation_before_metadata')
            expected.add('output-before.bin')
        if not isinstance(value['files'],dict) or set(value['files'])!=expected or {p.name for p in root.iterdir()}!=expected|{'manifest.json'}:raise ValueError('attestation_input_members_changed')
        files={}
        for name,row in value['files'].items():
            if name not in INPUT_NAMES or not isinstance(row,dict) or set(row)!={'sha256','bytes'} or type(row['bytes']) is not int or not 0<=row['bytes']<=logic.MAX_INPUT:
                raise ValueError('invalid_attestation_input_file')
            raw=safe_bytes(root/name,limit=logic.MAX_INPUT)
            if hashes({name:raw})[name]!=row:raise ValueError('attestation_input_bytes_changed')
            files[name]=raw
        if metadata is not None and metadata['st_size']!=len(files['output-before.bin']):raise ValueError('attestation_before_length_changed')
        return value,files

    def capture(self,metadata,files):
        if not set(files)<=INPUT_NAMES or any(not isinstance(raw,bytes) or len(raw)>logic.MAX_INPUT for raw in files.values()):raise ValueError('attestation_input_budget')
        manifest={**metadata,'files':hashes(files)};input_id=canonical_digest(manifest);reserve(self.root,sum(map(len,files.values()))+MAX_JSON)
        with tempfile.TemporaryDirectory(prefix='.incoming-',dir=self.inputs) as temporary:
            staged=Path(temporary)/'data';staged.mkdir(mode=0o700)
            for name,raw in files.items():p=staged/name;p.write_bytes(raw);p.chmod(0o600)
            atomic_json(staged/'manifest.json',manifest);self.current()
            with write_lock(self.root):
                target=self.inputs/input_id
                if target.is_symlink():raise ValueError('unsafe_attestation_input')
                if not target.exists():os.rename(staged,target)
                if self.input_data(input_id)!=(manifest,files):raise ValueError('immutable_attestation_input_conflict')
        return input_id

    def intent(self,operation):
        value=strict_json(safe_bytes(self.intents/(identity(operation)+'.json'),limit=MAX_JSON))
        if set(value)!={'schema_version','operation_id','input_id','state','stage','process_started','assessment_id',*self.binding} or type(value['schema_version']) is not int or value['schema_version']!=1 or value['operation_id']!=operation or any(value[k]!=v for k,v in self.binding.items()):
            raise ValueError('attestation_intent_binding_changed')
        if value['state'] not in ('pending','completed') or type(value['process_started']) is not bool or value['stage'] not in ('inputs_retained','crypto_started','output_write_attempted','completed'):raise ValueError('invalid_attestation_intent')
        if (value['state']=='completed')!=(value['assessment_id'] is not None) or (value['state']=='completed')!=(value['stage']=='completed'):raise ValueError('invalid_attestation_intent_state')
        self.input_data(value['input_id'])
        if value['assessment_id'] is not None:identity(value['assessment_id'])
        return value

    def record(self,assessment_id):
        value=strict_json(safe_bytes(self.assessments/(identity(assessment_id)+'.json'),limit=MAX_JSON))
        try:Draft202012Validator(read_json(ROOT/'schemas/axiom-v2-attestation-verification.schema.json'),format_checker=FormatChecker()).validate(value)
        except ValidationError:raise ValueError('invalid_attestation_assessment') from None
        if type(value['schema_version']) is not int or canonical_digest(value)!=assessment_id or any(value[k]!=v for k,v in self.binding.items()):raise ValueError('attestation_assessment_binding_changed')
        intent=self.intent(value['operation_id'])
        if intent['input_id']!=value['input_id'] or intent['assessment_id']!=assessment_id or intent['state']!='completed' or intent['process_started']!=value['crypto']['process_started']:
            raise ValueError('attestation_intent_outcome_changed')
        return value

    def inspect(self,assessment_id):
        value=self.record(assessment_id);manifest,inputs=self.input_data(value['input_id']);root=self.artifacts/assessment_id
        if root.is_symlink() or not root.is_dir() or root.stat().st_mode&0o077 or {p.name for p in root.iterdir()}!=set(value['files']):raise ValueError('attestation_artifact_members_changed')
        files={}
        allowed={'native-assessment.json','native-stdout.txt','crypto-stdout.bin','crypto-stderr.bin','output-after.bin'}
        for name,row in value['files'].items():
            if name not in allowed:raise ValueError('invalid_attestation_artifact_name')
            raw=safe_bytes(root/name,limit=logic.MAX_INPUT)
            if hashes({name:raw})[name]!=row:raise ValueError('attestation_artifact_bytes_changed')
            files[name]=raw
        if not {'crypto-stdout.bin','crypto-stderr.bin'}<=files.keys():raise ValueError('attestation_crypto_streams_missing')
        crypto=value['crypto']
        if crypto['process_started']:
            if crypto['tool_path'] is None or crypto['tool_sha256'] is None or not crypto['attempted']:raise ValueError('attestation_started_tool_identity_missing')
        elif crypto['returncode'] is not None or files['crypto-stdout.bin'] or files['crypto-stderr.bin'] or crypto['timed_out']:
            raise ValueError('attestation_unstarted_process_outputs_changed')
        if crypto['timed_out'] and crypto['error_type'] is None:raise ValueError('attestation_timeout_error_missing')
        if value['output_write_attempted'] and not value['native_result_available']:raise ValueError('attestation_write_without_native_result')
        if 'output-after.bin' in files and not value['output_write_attempted']:raise ValueError('attestation_unattempted_output_capture')
        if value['native_result_available']!=({'native-assessment.json','native-stdout.txt'}<=files.keys()):raise ValueError('attestation_native_artifact_members_changed')
        attempted=False
        def verify(key,statement,signature):
            nonlocal attempted
            attempted=True;valid,reason=attestation_crypto_outcome(value['crypto'])
            if (valid,reason)!=(value['crypto']['signature_valid'],value['crypto']['reason']):raise ValueError('attestation_crypto_outcome_changed')
            return valid,reason
        error=None;result=None
        try:result=derive(manifest,inputs,verify)
        except Exception as exc:error=type(exc).__name__
        if attempted!=value['crypto']['attempted'] or (not attempted and value['crypto']!=attestation_crypto_initial()):raise ValueError('attestation_crypto_attempt_changed')
        if value['native_result_available']:
            if error is not None or result is None or files.get('native-assessment.json')!=logic.wire(result) or files.get('native-stdout.txt')!=logic.summary(result).encode():raise ValueError('attestation_native_output_changed')
        elif error!=value['error_type'] or {'native-assessment.json','native-stdout.txt'}&files.keys():raise ValueError('attestation_failure_outcome_changed')
        if value['evaluated_at']!=manifest['evaluated_at'] or value['assessment_time_source']!=manifest['assessment_time_source'] or value['profile']!=manifest['profile']:
            raise ValueError('attestation_declaration_changed')
        if value['exit_code']==0:
            if not value['native_result_available'] or value['error_type'] is not None or not value['output_write_attempted'] or value['output_capture_error'] is not None or files.get('output-after.bin')!=logic.wire(result):raise ValueError('attestation_completed_output_changed')
        elif value['error_type'] is None and value['output_capture_error'] is None:raise ValueError('attestation_error_required')
        self.current()
        return {**value,'assessment_id':assessment_id,'data_directory':str(root),'retained_artifacts_reverified':True,
            'retained_complete_outputs_reverified':value['exit_code']==0,'retained_native_result_rederived':value['native_result_available'],
            'external_output_capture_complete':value['output_capture_error'] is None,
            'current_input_or_destination_rechecked':False,'cryptographic_signature_reverified':False,'automatic_resume':False}

    def status(self,operation):
        value=self.intent(operation)
        checked=None
        if value['assessment_id'] is not None:checked=self.inspect(value['assessment_id'])
        elif value['state']!='pending':raise ValueError('invalid_attestation_pending_state')
        self.current();return {**value,'diagnostic_exit_code':None if checked is None else checked['exit_code'],
            'native_result_available':False if checked is None else checked['native_result_available'],
            'automatic_resume':False,'pending_may_have_external_effects':value['state']=='pending'}

    def verify(self,attestation,output,profile,*,trust_roots=None,evaluated_at=None,context=None,subject=None,level='integrity_verified'):
        if level not in ('unverified','integrity_verified','provenance_verified'):raise ValueError('invalid_attestation_declared_level')
        selected=attestation_profile(profile);at=evaluated_at or datetime.now(timezone.utc).isoformat().replace('+00:00','Z');explicit_time(at)
        files={'attestation.json':effects.input_bytes(attestation),'registry.yaml':effects.input_bytes(trust_roots if trust_roots is not None else ROOT/selected['registry'])}
        if context is not None:files['context.json']=effects.input_bytes(context)
        if subject is not None:files['subject.json']=effects.input_bytes(subject)
        output=effects.destination(output,[ROOT,self.instance]);lock_id=hashlib.sha256(str(output).encode()).hexdigest();lock_root=private_directory(self.locks/lock_id)
        # Same-node writers serialize. Independent nodes must have one operating
        # owner per destination; observed changes are never silently overwritten.
        with write_lock(lock_root):
            before,metadata=effects.observe(output)
            if before is not None:files['output-before.bin']=before
            metadata={'schema_version':1,'profile':profile,'attestation_reference':str(attestation),
                'registry_origin':'operator_file' if trust_roots is not None else 'product_default_diagnostic_data',
                'context_origin':'operator_file' if context is not None else 'statement_declaration',
                'subject_origin':'operator_file' if subject is not None else 'statement_declaration',
                'declared_effective_level':level,'evaluated_at':at,'assessment_time_source':'operator' if evaluated_at is not None else 'system_clock',
                'output_destination':str(output),'output_before_metadata':metadata}
            input_id=self.capture(metadata,files);operation=secrets.token_hex(32)
            intent={'schema_version':1,'operation_id':operation,'input_id':input_id,'state':'pending','stage':'inputs_retained','process_started':False,'assessment_id':None,**self.binding}
            self.current();atomic_json(self.intents/(operation+'.json'),intent)
            observation=attestation_crypto_initial();artifacts={'crypto-stdout.bin':b'','crypto-stderr.bin':b''};error=None;capture_error=None;result=None;write_attempted=False;exit_code=2
            def on_start(value):
                nonlocal observation
                observation=dict(value)
                intent.update(stage='crypto_started',process_started=value['process_started']);atomic_json(self.intents/(operation+'.json'),intent)
            def verify(key,statement,signature):
                nonlocal observation
                try:observation,out,err=verify_attestation_signature(key,statement,signature,self.scratch,profile,on_start)
                except Exception as exc:
                    observation.update(attempted=True,error_type=type(exc).__name__,failure_stage='adapter_failure',process_started=intent['process_started'])
                    out=err=b''
                artifacts.update({'crypto-stdout.bin':out,'crypto-stderr.bin':err});return attestation_crypto_outcome(observation)
            try:
                result=derive(metadata,files,verify);artifacts.update({'native-assessment.json':logic.wire(result),'native-stdout.txt':logic.summary(result).encode()})
                self.current();intent['stage']='output_write_attempted';atomic_json(self.intents/(operation+'.json'),intent);write_attempted=True
                effects.apply(output,artifacts['native-assessment.json'],before,metadata['output_before_metadata']);self.current();exit_code=0
            except Exception as exc:error=type(exc).__name__
            if write_attempted:
                try:
                    after,unused=effects.observe(output)
                    if after is not None:artifacts['output-after.bin']=after
                    if exit_code==0 and after!=artifacts['native-assessment.json']:
                        error='ValueError';exit_code=2
                except Exception as exc:capture_error=type(exc).__name__;exit_code=2
            value={'schema_version':1,'kind':'attestation-pilot-diagnostic',**self.binding,'input_id':input_id,'operation_id':operation,
                'evaluated_at':at,'assessment_time_source':metadata['assessment_time_source'],'source_worktree_clean':self.clean,
                'profile':profile,'crypto':observation,'native_result_available':result is not None and 'native-assessment.json' in artifacts,
                'output_write_attempted':write_attempted,'output_capture_error':capture_error,'error_type':error,'exit_code':exit_code,
                'files':hashes(artifacts),'mode':'report-only','evidence_trust':'unverified','registry_authority_activated':False,
                'declared_context_independently_verified':False,'key_algorithm_enforced':False,'registry_dates_enforced':False,**FLAGS}
            assessment_id=canonical_digest(value);reserve(self.root,sum(map(len,artifacts.values()))+MAX_JSON)
            with tempfile.TemporaryDirectory(prefix='.incoming-',dir=self.artifacts) as temporary:
                staged=Path(temporary)/'data';staged.mkdir(mode=0o700)
                for name,raw in artifacts.items():p=staged/name;p.write_bytes(raw);p.chmod(0o600)
                self.current()
                with write_lock(self.root):
                    os.rename(staged,self.artifacts/assessment_id);atomic_json(self.assessments/(assessment_id+'.json'),value)
                    intent.update(state='completed',stage='completed',assessment_id=assessment_id);atomic_json(self.intents/(operation+'.json'),intent)
            return self.inspect(assessment_id),result


def run(arguments,instance_root,settings):
    parser=argparse.ArgumentParser(prog='axiom-v2 attestation',allow_abbrev=False);commands=parser.add_subparsers(dest='command',required=True)
    verify=commands.add_parser('verify',allow_abbrev=False);verify.add_argument('attestation',type=Path)
    verify.add_argument('--output',type=Path,required=True);verify.add_argument('--trust-roots',type=Path)
    verify.add_argument('--evaluated-at');verify.add_argument('--expected-context',type=Path);verify.add_argument('--expected-subject',type=Path)
    verify.add_argument('--effective-level',choices=('unverified','integrity_verified','provenance_verified'),default='integrity_verified')
    verify.add_argument('--profile',choices=ATTESTATION_PROFILES,required=True);verify.add_argument('--format',choices=('legacy','receipt'),default='legacy')
    inspect=commands.add_parser('inspect');inspect.add_argument('--assessment',required=True)
    status=commands.add_parser('status');status.add_argument('--operation',required=True)
    args=parser.parse_args(arguments);app=AttestationContext(instance_root,settings)
    if args.command=='inspect':print(json.dumps(app.inspect(args.assessment),sort_keys=True));return 0
    if args.command=='status':print(json.dumps(app.status(args.operation),sort_keys=True));return 0
    value,result=app.verify(args.attestation,args.output,args.profile,trust_roots=args.trust_roots,evaluated_at=args.evaluated_at,
        context=args.expected_context,subject=args.expected_subject,level=args.effective_level)
    if args.format=='receipt':print(json.dumps(value,sort_keys=True))
    elif value['exit_code']==0:print(logic.summary(result),end='')
    else:
        import sys
        print('error: Attestation operation stopped; inspect private operation '+value['operation_id'],file=sys.stderr)
    return value['exit_code']
