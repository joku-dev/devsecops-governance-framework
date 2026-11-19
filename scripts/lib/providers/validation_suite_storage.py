"""Private finite suite intent, stream and result storage; standard library only."""
from pathlib import Path
import hashlib
import os
import re
import secrets

from lib.validation_suite import Observation,MAX_STREAM,replay
from lib.providers.environment_bootstrap_storage import (owned_directory,write_new,read_private,document,AUTHORITY)


def raw_new(path,raw):
    if type(raw) is not bytes or len(raw)>MAX_STREAM:raise ValueError('validation_suite_stream_budget')
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        remaining=memoryview(raw)
        while remaining:
            count=os.write(fd,remaining)
            if count<=0:raise OSError('validation_suite_stream_short_write')
            remaining=remaining[count:]
        os.fsync(fd)
    finally:os.close(fd)
    directory=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:os.fsync(directory)
    finally:os.close(directory)
    return {'path':path.name,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}


class SuiteJournal:
    def __init__(self,parent,request,source):
        owned_directory(parent);self.root=parent/secrets.token_hex(16);self.root.mkdir(mode=0o700)
        self.identity=self.root.stat();self.sequence=0;self.phase=None;self.rows=[];self.stream_bytes=0
        request_pin=write_new(self.root/'request.json',request);source_pin=write_new(self.root/'source.json',source)
        self.append({'kind':'opened','profile':'legacy-local-validation-v1','request':request_pin,'source':source_pin,**AUTHORITY})
    def append(self,row):
        owned_directory(self.root);current=self.root.stat()
        if (current.st_ino,current.st_dev)!=(self.identity.st_ino,self.identity.st_dev):raise ValueError('validation_suite_record_root_replaced')
        if self.sequence>=2048:raise ValueError('validation_suite_event_budget')
        write_new(self.root/f'event-{self.sequence:04d}.json',row);self.sequence+=1
    def begin_admission(self,action):
        if self.phase is not None:raise ValueError('validation_suite_phase_pending')
        self.phase=self.sequence
        self.append({'kind':'admission-intent','phase':self.phase,'action':action})
    def end_admission(self):
        if self.phase is None:raise ValueError('validation_suite_admission_missing')
        self.append({'kind':'admission-returned','phase':self.phase});self.phase=None
    def retain_component(self,kind,identifier,root):
        return retain_component(self,kind,identifier,root)
    def before(self,action):
        if self.phase is not None:raise ValueError('validation_suite_phase_pending')
        token=self.sequence;self.append({'kind':'phase-intent','phase':token,'action':action});self.phase=token;self.action=action;return token
    def after(self,token,wire):
        if type(token) is not int or token!=self.phase:raise ValueError('validation_suite_phase_changed')
        value=Observation.from_wire(wire)
        self.stream_bytes+=len(value.stdout)+len(value.stderr)
        if self.stream_bytes>32*1024**2:raise ValueError('validation_suite_total_stream_budget')
        descriptors={name:raw_new(self.root/f'phase-{token:04d}-{name}.bin',getattr(value,name)) for name in ('stdout','stderr')}
        self.append({'kind':'phase-returned','phase':token,'action':self.action,'returncode':value.returncode,'streams':descriptors})
        self.rows.append({'action':self.action,'observation':wire});self.phase=None
    def finish(self,report,streams):
        value={**report,'legacy_streams':{name:raw_new(self.root/('legacy-'+name+'.bin'),raw) for name,raw in streams.items()},**AUTHORITY}
        write_new(self.root/'result.json',value);self.append({'kind':'coordinator-finished','result_sha256':hashlib.sha256(read_private(self.root/'result.json')).hexdigest()})
        return {**value,'record_root':str(self.root)}


class SuiteSink:
    def __init__(self):self.streams={'stdout':bytearray(),'stderr':bytearray()}
    def write(self,name,raw):
        if name not in self.streams or type(raw) is not bytes:raise ValueError('validation_suite_output_required')
        if len(self.streams[name])+len(raw)>MAX_STREAM:raise ValueError('validation_suite_aggregate_stream_budget')
        self.streams[name].extend(raw)
    def bytes(self):return {name:bytes(raw) for name,raw in self.streams.items()}


def retained_stream(root,row):
    if type(row) is not dict or set(row)!={'path','bytes','sha256'} or type(row['path']) is not str or Path(row['path']).name!=row['path']:
        raise ValueError('validation_suite_retained_stream_shape')
    raw=read_private(root/row['path'],MAX_STREAM)
    if len(raw)!=row['bytes'] or hashlib.sha256(raw).hexdigest()!=row['sha256']:raise ValueError('validation_suite_retained_stream_changed')
    return raw


def inspect(root):
    root=owned_directory(Path(root));request=document(read_private(root/'request.json'));source=document(read_private(root/'source.json'))
    from lib.v2_source import active_fingerprints
    product=Path(__file__).resolve().parents[3]
    if (set(source)!={'source_root','active_fingerprints'} or source['source_root']!=str(product)
            or source['active_fingerprints']!=active_fingerprints(product)):
        raise ValueError('validation_suite_retained_source_changed')
    for name,original in (('requirements-validation.txt','requirements-validation.txt'),('validation-toolchain.env','scripts/validation-toolchain.env')):
        if hashlib.sha256(read_private(root/name)).hexdigest()!=source['active_fingerprints'][original]:
            raise ValueError('validation_suite_captured_input_changed')
    if request.get('profile')!='legacy-local-validation-v1' or type(request.get('check_tools')) is not bool:
        raise ValueError('validation_suite_request_profile_changed')
    if request['arguments']!=(['--check-tools'] if request['check_tools'] else []):raise ValueError('validation_suite_request_scope_changed')
    events=sorted(root.glob('event-*.json'));rows=[];pending=None;native={};terminal=None;components=[];phase_tokens={};component_rows={};unit_rows=[];provenance_rows=[]
    if len(events)>2048:raise ValueError('validation_suite_event_budget')
    for number,path in enumerate(events):
        if path.name!=f'event-{number:04d}.json':raise ValueError('validation_suite_event_sequence_changed')
        row=document(read_private(path));kind=row.get('kind')
        if number==0:
            if kind!='opened':raise ValueError('validation_suite_opening_event_missing')
            for name in ('request','source'):
                raw=read_private(root/(name+'.json'))
                if row[name]!={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}:raise ValueError('validation_suite_header_binding_changed')
        if terminal is not None:raise ValueError('validation_suite_trailing_events')
        if kind=='admission-intent':
            if pending is not None or type(row['phase']) is not int or row['phase']!=number:raise ValueError('validation_suite_admission_sequence_changed')
            pending=(row['phase'],'admission')
        elif kind=='admission-returned':
            if pending!=(row['phase'],'admission'):raise ValueError('validation_suite_admission_outcome_changed')
            pending=None
        elif kind=='phase-intent':
            if pending is not None or type(row['phase']) is not int or row['phase']!=number:raise ValueError('validation_suite_phase_sequence_changed')
            pending=(row['phase'],row['action']);phase_tokens[row['phase']]=row['action']
        elif kind=='phase-returned':
            if pending!=(row['phase'],row['action']) or set(row['streams'])!={'stdout','stderr'}:raise ValueError('validation_suite_phase_outcome_changed')
            raw={name:retained_stream(root,descriptor) for name,descriptor in row['streams'].items()}
            rows.append({'action':row['action'],'observation':Observation(row['returncode'],**raw).wire()});pending=None
        elif kind=='native-intent':
            if row['native_id'] in native:raise ValueError('validation_suite_duplicate_native')
            if pending is None or row['phase']!=pending[0]:raise ValueError('validation_suite_native_phase_changed')
            native[row['native_id']]={'intent':row,'started':None,'finished':None}
        elif kind in ('native-started','native-finished'):
            key='started' if kind=='native-started' else 'finished'
            if row['native_id'] not in native or native[row['native_id']][key] is not None:raise ValueError('validation_suite_native_order_changed')
            native[row['native_id']][key]=row
        elif kind=='retained-component':
            kind_name=row['component'];identifier=row['identifier']
            if kind_name not in ('runtime','repository') or not re.fullmatch('[a-f0-9]{64}',identifier):raise ValueError('validation_suite_component_identity_invalid')
            directory='validation' if kind_name=='runtime' else 'repository-validation'
            expected=Path(request['instance'])/'state'/directory/'operations'/identifier
            if row['root']!=str(expected) or component_files(expected)!=row['files']:raise ValueError('validation_suite_retained_component_changed')
            if pending is None or pending[1]!=kind_name+'_validation' or kind_name in component_rows:
                raise ValueError('validation_suite_component_phase_changed')
            component_rows[kind_name]=row
            components.append(kind_name)
        elif kind=='own-suite-provenance-inputs':
            if pending is None or pending[1]!='provenance_validation' or provenance_rows:
                raise ValueError('validation_suite_provenance_phase_changed')
            raw=read_private(root/'provenance-inputs/manifest.json')
            if row['manifest']!={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}:
                raise ValueError('validation_suite_provenance_manifest_changed')
            provenance_rows.append(document(raw))
        elif kind=='own-suite-unit-outcome':
            if pending is None or pending[1]!='unit_tests' or unit_rows:
                raise ValueError('validation_suite_unit_phase_changed')
            unit_rows.append(row)
        elif kind=='coordinator-finished':terminal=row
        elif kind not in ('opened','python-handoff-intent','own-suite-component','own-suite-source','own-suite-runtime-write','own-suite-runtime'):
            raise ValueError('validation_suite_unknown_event')
    for item in native.values():
        if item['finished'] is None:continue
        outcome=item['finished']['outcome']
        if (item['started'] is None or outcome['command']!=item['intent']['command']
                or item['started']['phase']!=item['intent']['phase'] or item['finished']['phase']!=item['intent']['phase']
                or outcome['cwd']!=item['intent']['cwd'] or outcome['timeout_seconds']!=item['intent']['timeout_seconds']
                or outcome['stream_limit_bytes']!=item['intent']['stream_limit_bytes']
                or type(outcome['exit_code']) is not int or not -127<=outcome['exit_code']<=255):
            raise ValueError('validation_suite_native_binding_changed')
        for name,descriptor in outcome['streams'].items():
            path=Path(descriptor['path'])
            if path.parts[0]!='native' or len(path.parts)!=2:raise ValueError('validation_suite_native_stream_scope')
            raw=read_private(root/path,MAX_STREAM)
            if len(raw)!=descriptor['bytes'] or hashlib.sha256(raw).hexdigest()!=descriptor['sha256']:raise ValueError('validation_suite_native_stream_changed')
    result=None
    if terminal is not None:
        raw=read_private(root/'result.json');result=document(raw)
        if hashlib.sha256(raw).hexdigest()!=terminal['result_sha256']:raise ValueError('validation_suite_result_changed')
        if any(result.get(k) is not v for k,v in AUTHORITY.items()):raise ValueError('validation_suite_authority_changed')
        if (result.get('profile')!='legacy-local-validation-v1' or type(result.get('full_default_requested')) is not bool
                or result['full_default_requested'] is request['check_tools']):raise ValueError('validation_suite_result_scope_changed')
        if result['state']=='complete':
            if pending is not None or any(n['finished'] is None for n in native.values()):raise ValueError('validation_suite_false_completion')
            expected_operations={'opa_version':['policy_version','policy_version_parser'],'dependency_versions':['dependency_versions'],'dependency_consistency':['dependency_consistency'],'opa_check':['policy_check']}
            for token,action in phase_tokens.items():
                operations=[n['intent']['operation'] for n in native.values() if n['intent']['phase']==token]
                if operations!=expected_operations.get(action,[]):raise ValueError('validation_suite_phase_native_membership_changed')
            for token,action in phase_tokens.items():
                if action not in expected_operations:continue
                captures=[n['finished']['outcome'] for n in native.values() if n['intent']['phase']==token]
                def output(capture,name):
                    return read_private(root/capture['streams'][name]['path'],MAX_STREAM)
                def shell(code):return 128-code if code<0 else code
                if action=='opa_version':
                    expected=Observation(shell(captures[1]['exit_code']) or shell(captures[0]['exit_code']),
                        output(captures[1],'stdout'),output(captures[0],'stderr')+output(captures[1],'stderr'))
                    if read_private(root/'policy-version-input.bin',MAX_STREAM)!=output(captures[0],'stdout'):
                        raise ValueError('validation_suite_version_input_changed')
                else:
                    capture=captures[0]
                    expected=Observation(shell(capture['exit_code']),output(capture,'stdout'),output(capture,'stderr'))
                actual=next(row['observation'] for row in rows if row['action']==action)
                if actual!=expected.wire():raise ValueError('validation_suite_phase_native_outcome_changed')
            completed_actions=[r['action'] for r in rows]
            if ('runtime_validation' in completed_actions)!=('runtime' in components) or ('repository_validation' in completed_actions)!=('repository' in components):
                raise ValueError('validation_suite_component_membership_changed')
            verify_component_observations(root,rows,component_rows,provenance_rows,unit_rows,result,environment=request['environment'])
            sink=SuiteSink();code=replay(request['arguments'],rows,sink,environment_label=request['environment'],expected_opa_version=request['expected_opa_version'])
            if code!=result['original_exit_code']:raise ValueError('validation_suite_replay_exit_changed')
            for name,descriptor in result['legacy_streams'].items():
                if retained_stream(root,descriptor)!=sink.bytes()[name]:raise ValueError('validation_suite_replay_streams_changed')
    return {'record_root':str(root),'declared_result':None if result is None else result['state'],
        'original_exit_code':None if result is None else result.get('original_exit_code'),
        'phase_count':len(rows),'pending_phase':pending,'retained_native_count':len(native),
        'retained_declared_replay_consistent':bool(result and result['state']=='complete'),
        'decision_replay_scope':'suite_order_status_final_streams_and_retained_component_bytes',
        'component_semantics_replayed_during_inspection':False,
        'native_execution_authenticated':False,'current_environment_rechecked':False,**AUTHORITY}


def verify_component_observations(root,rows,components,provenance,units,result,*,environment=None):
    """Bind final streams to retained components, without rerunning native work.

    Runtime/repository engines already replay at creation; inspection checks their
    complete byte closure and wires. Provenance is pure and replayed here. Unit
    completion requires its actual captured discovery streams and parsed summary.
    This is declared evidence, never independent execution authentication.
    """
    import base64
    by_action={row['action']:row['observation'] for row in rows}
    def expected(action,code,stdout,stderr):
        if by_action[action]!=Observation(code,stdout,stderr).wire():
            raise ValueError('validation_suite_component_outcome_changed')
    if 'runtime' in components:
        value=document(read_private(Path(components['runtime']['root'])/'assessment.json',48*1024**2))
        if value['execution']!='complete':raise ValueError('validation_suite_runtime_incomplete')
        expected('runtime_validation',value['exit_code'],base64.b64decode(value['stdout_base64'],validate=True),base64.b64decode(value['stderr_base64'],validate=True))
    if 'repository' in components:
        # Native repository storage has its own strict loader and replay contract.
        from lib.provider_ports import load_repository_operation,repository_operation_header
        from lib import repository_operation as contract
        target=Path(components['repository']['root'])
        header=contract.binding(repository_operation_header(target))
        value=load_repository_operation(target,header)
        if value['outcome']['execution']!='complete':raise ValueError('validation_suite_repository_incomplete')
        outcome=value['outcome'];expected('repository_validation',outcome['exit_code'],outcome['stdout'].encode(),outcome['stderr'].encode())
    if ('provenance_validation' in by_action)!=bool(provenance):raise ValueError('validation_suite_provenance_membership_changed')
    if provenance:
        from lib.provenance_validation import ProvenanceValidation
        from lib.validation_files import ValidationFiles
        manifest=provenance[0]
        files={name:retained_stream(root/'provenance-inputs',descriptor) for name,descriptor in manifest['files'].items()}
        value=ProvenanceValidation(ValidationFiles(files,manifest['membership'],label=manifest['label'])).run()
        expected('provenance_validation',value['returncode'],value['stdout'].encode(),value['stderr'].encode())
    if ('unit_tests' in by_action)!=bool(units):raise ValueError('validation_suite_unit_membership_changed')
    if bool(result.get('full_unit_discovery_observed',False))!=bool(units):raise ValueError('validation_suite_unit_claim_changed')
    if units:
        row=units[0];native=root/'work/native'
        if row['native_root']!=str(native):raise ValueError('validation_suite_unit_capture_scope_changed')
        outcome=row['native_outcome']
        command=outcome['command']
        if (type(command) is not list or len(command)!=7 or any(type(s) is not str for s in command)
                or command[1:]!=['-B','-m','unittest','discover','-s','tests']
                or environment is not None and Path(command[0]).parent!=Path(environment)/'bin'):
            raise ValueError('validation_suite_whole_unit_command_required')
        if set(outcome['outputs'])!={'stdout','stderr'}:raise ValueError('validation_suite_unit_capture_shape')
        raw={name:retained_stream(native,descriptor) for name,descriptor in outcome['outputs'].items()}
        if any(outcome['outputs'][name]['path']!='unit-tests-'+name+'.bin' for name in raw):raise ValueError('validation_suite_unit_capture_scope_changed')
        code=outcome['returncode'];code=128-code if code<0 else code
        expected('unit_tests',code,raw['stdout'],raw['stderr'])
        matches=list(re.finditer(rb'^Ran ([0-9]+) tests? in ([0-9.]+)s\s*$',raw['stderr'],re.M))
        if not matches:raise ValueError('validation_suite_whole_unit_summary_required')
        summary=re.search(rb'^(OK(?: \(skipped=([0-9]+)\))?|FAILED \([^\n]+\))$',raw['stderr'][matches[-1].end():],re.M)
        if summary is None or code not in (0,1) or (code==0)!=summary[1].startswith(b'OK'):
            raise ValueError('validation_suite_whole_unit_summary_changed')
        skipped=re.search(rb'skipped=([0-9]+)',summary[1])
        statistics={'tests_run':int(matches[-1][1]),'seconds':float(matches[-1][2]),'skipped':int(skipped[1]) if skipped else 0}
        if statistics['tests_run']<=0 or statistics!=row['statistics'] or statistics!=result.get('unit_statistics'):
            raise ValueError('validation_suite_unit_statistics_changed')


def component_files(root):
    root=owned_directory(root);files={};total=0
    for path in sorted(root.rglob('*')):
        if path.is_symlink():raise ValueError('validation_suite_component_symlink')
        if path.is_dir():continue
        if len(files)>=20000:raise ValueError('validation_suite_component_file_budget')
        raw=read_private(path,64*1024**2);total+=len(raw)
        if total>512*1024**2:raise ValueError('validation_suite_component_byte_budget')
        files[path.relative_to(root).as_posix()]={'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
    return files


def retain_component(self,kind,identifier,root):
    if kind not in ('runtime','repository') or not re.fullmatch('[a-f0-9]{64}',identifier):
        raise ValueError('validation_suite_component_identity_invalid')
    self.append({'kind':'retained-component','component':kind,'identifier':identifier,
        'root':str(root),'files':component_files(root),
        'semantic_replay_performed_at_creation':True,'independent_execution_authenticated':False})
