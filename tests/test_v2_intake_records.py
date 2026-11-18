"""Whole original record/CLI/file effects and retained diagnostic boundaries."""
from contextlib import redirect_stderr,redirect_stdout
from copy import deepcopy
import importlib.util
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import ssl
import subprocess
import threading
import io
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(os.environ.get('AXIOM_TEST_PRODUCT_ROOT',Path(__file__).resolve().parents[1]));sys.path.insert(0,str(ROOT/'scripts'))
from lib import intake_recording as logic,intake_record_files as effects
from lib.intake_recording_application import IntakeRecordContext,run
from lib.providers import intake_recording as adapter
from lib.portable.contracts import canonical_digest
spec=importlib.util.spec_from_file_location('original_intake_records',Path(__file__).resolve().parent/'acceptance/v1_intake_recording_oracle.py')
oracle=importlib.util.module_from_spec(spec);spec.loader.exec_module(oracle)
FIXTURES=Path(os.environ.get('AXIOM_TEST_INTAKE_RECORD_FIXTURES',ROOT/'tests/fixtures/v2-intake-records'))
AT='2026-11-18T03:00:00Z';PROFILE='legacy-intake-records-v1'
RUN={'id':42,'run_attempt':2,'name':'Synthetic governance','head_sha':'a'*40,'html_url':'https://example.invalid/runs/42'}


class Response(io.BytesIO):
    status=200
    def __init__(self,raw):super().__init__(raw);self.headers={}


class IntakeRecords(unittest.TestCase):
    def setUp(self):
        previous=os.umask(0o077);self.addCleanup(os.umask,previous)
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup);self.base=Path(temp.name).resolve()
        self.target=self.base/'target';self.target.mkdir(mode=0o700);self.instance=self.base/'instance';self.instance.mkdir(mode=0o700)
        self.settings={'node_id':'synthetic-intake-record-node'};self.app=IntakeRecordContext(self.instance,self.settings)
        self.old=oracle.Original(FIXTURES,self.target);self.old.schema_files();self.output=self.base/'native-output.txt'

    def request(self,kind='attempt',**changes):
        value={'kind':kind,'profile':PROFILE,'root':str(self.target),'at':AT,'time_source':'operator','output':None,'token_origin':'none'}
        if kind=='retry':value['attempt_path']=changes.pop('attempt_path')
        else:
            value.update(repository_id='owner/repo',run_id='42',evidence_type='governance_result',collector_id='central-governance-intake',
                collector_version='0.1.0',artifact_name='governance-control-evaluation',status='failed',error_code='intake_failed',message='Synthetic failed intake')
            if kind=='attempt':value.update(api_url='https://api.example.invalid',retryable=True)
            else:value.update(intake_type='devsecops_governance',started_at='2026-11-18T02:59:57Z',completed_at='',
                intake_repository_id='central/governance',intake_workflow_name='Synthetic intake',intake_run_id='84',intake_run_attempt=1,trigger_event='workflow_dispatch')
        value.update(changes);return value

    def execute(self,request,response=RUN,error=None):
        raw=json.dumps(response).encode()
        with patch.object(adapter,'open_https',side_effect=error if error is not None else lambda *a,**k:Response(raw)):
            return self.app.execute(request)

    def cli_args(self,request):
        args=[]
        names=sorted(set(request)-{'kind','profile','root','at','time_source','output','token_origin'})
        for name in names:
            value=request[name]
            if name=='retryable':
                if value:args+=['--retryable']
            elif value is not None and value!='':args+=['--'+name.replace('_','-'),str(value)]
        if request['output'] is not None:args+=['--github-output',request['output']]
        return args

    def compare(self,request,response=RUN,error=None):
        before=oracle.snapshot(self.target);previous=self.output.read_bytes() if self.output.exists() else None
        previous_mode=self.output.stat().st_mode&0o777 if self.output.exists() else None
        value,payload,stdout,stderr=self.execute(request,response,error);self.assertEqual(value['exit_code'],0)
        candidate=oracle.snapshot(self.target);after=self.output.read_bytes() if self.output.exists() else None
        after_mode=self.output.stat().st_mode&0o777 if self.output.exists() else None
        shutil.rmtree(self.target);self.target.mkdir(mode=0o700);self.old.schema_files()
        for name,raw in before.items():path=self.target/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        self.output.unlink(missing_ok=True)
        if previous is not None:self.output.write_bytes(previous);self.output.chmod(previous_mode)
        code,oldout,olderr=self.old.run(request['kind'],self.cli_args(request),at=request['at'],run=response,error=error)
        self.assertEqual((code,oldout,olderr),(0,stdout,stderr));self.assertEqual(oracle.snapshot(self.target),candidate)
        self.assertEqual(self.output.read_bytes() if self.output.exists() else None,after)
        if after_mode is not None:self.assertEqual(self.output.stat().st_mode&0o777,after_mode)
        self.assertTrue(self.app.inspect(value['assessment_id'])['retained_complete_outputs_rederived'])
        return value,payload

    def test_attempt_whole_original_cli_file_identity_and_declared_scope(self):
        value,payload=self.compare(self.request())
        self.assertTrue(value['provider_invoked']);self.assertTrue(value['lookup']['response_received'])
        self.assertFalse(value['native_outcome_authenticated']);self.assertEqual(value['evidence_trust'],'unverified')
        for key in ('official_index_updated','workflow_dispatched','authority_transferred','human_approval_verified','production_approval'):self.assertFalse(value[key])
        old=self.old.modules['attempt'];old['datetime']=type('Clock',(),{'now':staticmethod(lambda zone:__import__('datetime').datetime.fromisoformat(AT.replace('Z','+00:00')))})
        expected=old['build_attempt'](repository_id='owner/repo',run=RUN,evidence_type='governance_result',collector_id='central-governance-intake',collector_version='0.1.0',artifact_name='governance-control-evaluation',status='failed',code='intake_failed',message='Synthetic failed intake',retryable=True)
        self.assertEqual(payload,expected)

    def test_metadata_lookup_failure_keeps_original_fallback_warning_and_additional_error(self):
        for error in (OSError('synthetic private body must not escape'),ValueError('invalid metadata')):
            with self.subTest(error=type(error).__name__):
                value,payload=self.compare(self.request(run_id='43'),error=error)
                self.assertTrue(value['lookup']['client_invoked']);self.assertFalse(value['lookup']['response_received'])
                self.assertEqual([e['code'] for e in payload['errors']],['intake_failed','source_metadata_unavailable'])

    def test_metadata_declarations_preserve_original_unchecked_context_and_invalid_native_schema(self):
        for response in ({**RUN,'id':99,'head_sha':'declared-different'},{}):
            value,payload=self.compare(self.request(),response=response)
            self.assertEqual(payload['source']['run_id'],str(response.get('id','unknown')))
            self.assertFalse(value['native_outcome_authenticated'])
        self.assertFalse(value['native_schema_valid'])

    def test_attempt_first_identity_preserved_and_conflict_keeps_existing_requested_path_behavior(self):
        first,payload=self.compare(self.request());selected=first['selected']
        second,_=self.compare(self.request(at='2026-11-18T03:01:00Z',message='Changed detail'))
        self.assertEqual(second['selected'],selected);self.assertEqual(second['ledger_effect'],'conflict')
        self.assertNotEqual(second['selected'],second['requested']);self.assertFalse((self.target/second['requested']).exists())
        again,_=self.compare(self.request(at='2026-11-18T03:01:00Z',message='Changed detail'))
        self.assertEqual(again['ledger_effect'],'conflict')

    def test_identical_attempt_is_noop_even_if_existing_filename_differs(self):
        first,_=self.compare(self.request());path=self.target/first['selected'];renamed=path.with_name('earlier-retained-name.json');path.rename(renamed)
        value,_=self.compare(self.request());self.assertEqual(value['ledger_effect'],'existing');self.assertTrue(value['selected'].endswith('earlier-retained-name.json'))

    def test_filename_collisions_allocate_original_repeated_retry_suffixes(self):
        request=self.request();source=adapter.attempt_source(RUN,request['artifact_name']);payload=logic.attempt(request,source,[],AT);name,_=logic.record_paths('attempt',payload,'42')
        for suffix in ('','-retry','-retry-retry'):
            path=self.target/Path(name).with_name(Path(name).stem+suffix+'.json');path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps({'attempt_id':'other-'+suffix}))
        value,_=self.compare(request);self.assertTrue(value['selected'].endswith('-retry-retry-retry.json'))

    def test_events_success_partial_failure_and_subsecond_timezone_match_whole_original(self):
        for status in ('success','partial','failed'):
            request=self.request('event',status=status,error_code=None if status=='success' else 'intake_failed',message=None if status=='success' else 'Synthetic failure',intake_run_id='event-'+status,
                started_at='2026-11-18T04:00:00.100+01:00',completed_at='2026-11-18T03:00:01.350Z')
            value,payload=self.compare(request);self.assertEqual(payload['duration_ms'],1250);self.assertFalse(value['provider_invoked'])

    def test_event_identity_conflict_preserves_first_record_and_telemetry_declaration(self):
        first,_=self.compare(self.request('event'));second,_=self.compare(self.request('event',completed_at='2026-11-18T03:02:00Z'))
        self.assertEqual(first['selected'],second['selected']);self.assertEqual(second['ledger_effect'],'conflict');self.assertFalse(second['native_outcome_authenticated'])

    def test_event_original_error_conditions_have_no_external_effect(self):
        for change in ({'status':'success'},{'message':None},{'completed_at':'2026-11-17T00:00:00Z'},{'started_at':'2026-11-18T00:00:00'}):
            request=self.request('event',**change);before=oracle.snapshot(self.target);value,payload,*_=self.execute(request)
            self.assertEqual(value['exit_code'],2);self.assertIsNone(payload);self.assertFalse(value['effects_attempted']);self.assertEqual(oracle.snapshot(self.target),before)
            with self.assertRaises(ValueError):self.old.run('event',self.cli_args(request),at=AT)

    def test_retry_all_three_original_routes_and_append_bytes(self):
        for evidence,collector,artifact in (('governance_result','central-governance-intake','governance-control-evaluation'),('governance_result','central-governance-intake','architecture-governance-evidence'),('vulnerability_scan','central-vulnerability-scan-collector','application-evidence')):
            value,_=self.compare(self.request(evidence_type=evidence,collector_id=collector,artifact_name=artifact))
            self.output.write_bytes(b'previous output without newline');self.output.chmod(0o644)
            retry=self.request('retry',attempt_path=value['selected'],output=str(self.output));checked,plan=self.compare(retry)
            self.assertFalse(checked['workflow_dispatched']);self.assertEqual(self.output.stat().st_mode&0o777,0o644)
            self.assertTrue(self.output.read_bytes().startswith(b'previous output without newlineworkflow='))
            checked,_=self.compare(retry);self.assertEqual(self.output.read_bytes().count(b'workflow='),2)

    def test_retry_no_output_file_and_original_nonretryable_unknown_or_unsafe_rejection(self):
        value,_=self.compare(self.request());self.compare(self.request('retry',attempt_path=value['selected']))
        for index,change in enumerate(({'retryable':False},{'artifact_name':'unsupported'},{'run_id':'unsafe; run'})):
            record,_=self.compare(self.request(repository_id=f'owner/reject-{index}',**change),response={**RUN,'id':change.get('run_id',42)});retry=self.request('retry',attempt_path=record['selected'])
            before=oracle.snapshot(self.target);checked,_,*_=self.execute(retry);self.assertEqual(checked['exit_code'],2);self.assertFalse(checked['effects_attempted']);self.assertEqual(oracle.snapshot(self.target),before)
            with self.assertRaises(ValueError):self.old.run('retry',self.cli_args(retry),at=AT)

    def test_opaque_existing_conflict_and_malformed_json_keep_original_first_file(self):
        first,_=self.compare(self.request());changed=self.request(message='Changed')
        source=adapter.attempt_source(RUN,changed['artifact_name']);payload=logic.attempt(changed,source,[],AT);requested,conflicts=logic.record_paths('attempt',payload,'42')
        conflict=self.target/conflicts/(Path(requested).stem+'-conflict-'+logic.canonical_digest(payload)[:12]+'.json');conflict.parent.mkdir(parents=True,exist_ok=True);conflict.write_bytes(b'opaque retained conflict')
        junk=(self.target/first['selected']).parent/'000-malformed.json';junk.write_bytes(b'{invalid')
        self.compare(changed);self.assertEqual(conflict.read_bytes(),b'opaque retained conflict')

    def test_offline_replay_after_caller_ledger_and_native_output_disappear_does_no_provider_io(self):
        value,_=self.compare(self.request());shutil.rmtree(self.target)
        with patch('lib.intake_recording_application.acquire_intake_record_metadata',side_effect=AssertionError('offline replay queried provider')):
            checked=self.app.inspect(value['assessment_id'])
        self.assertTrue(checked['retained_complete_outputs_rederived']);self.assertFalse(checked['current_external_state_rechecked']);self.assertFalse(checked['native_api_requeried'])

    def test_foreign_node_tampered_blob_and_rehashed_authority_rejected(self):
        value,_=self.compare(self.request());identifier=value['assessment_id']
        with self.assertRaises(ValueError):IntakeRecordContext(self.instance,{'node_id':'foreign'}).inspect(identifier)
        meta,files=self.app.material(self.app.artifacts,value['artifact_id']);digest=meta['files']['native-payload.json']['sha256'];path=self.app.blobs/digest;raw=path.read_bytes();path.write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,'bytes_changed'):self.app.inspect(identifier)
        path.write_bytes(raw);record=json.loads((self.app.records/(identifier+'.json')).read_text());record['official_acceptance']=True;changed=canonical_digest(record);(self.app.records/(changed+'.json')).write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError,'invalid_intake_record_assessment'):self.app.inspect(changed)

    def test_pending_before_and_after_actual_ledger_write_never_retries(self):
        real=effects.LedgerRoot.apply
        for kind in ('before','after'):
            previous={p.stem for p in self.app.intents.glob('*.json')}
            def interrupt(ledger,*args):
                if kind=='after':real(ledger,*args)
                raise KeyboardInterrupt
            with patch.object(effects.LedgerRoot,'apply',interrupt):
                with self.assertRaises(KeyboardInterrupt):self.execute(self.request(run_id='interrupt-'+kind))
            operations=[p for p in self.app.intents.glob('*.json') if p.stem not in previous and json.loads(p.read_text())['state']=='pending'];self.assertEqual(len(operations),1);operation=operations[0].stem
            before=oracle.snapshot(self.target)
            with patch('lib.intake_recording_application.acquire_intake_record_metadata',side_effect=AssertionError('pending operation retried')):status=self.app.status(operation)
            self.assertEqual(status['state'],'pending');self.assertFalse(status['automatic_resume']);self.assertEqual(oracle.snapshot(self.target),before)

    def test_ledger_race_preserves_other_actor_and_records_partial_failure(self):
        real=effects.LedgerRoot.apply
        def race(ledger,scope,before,metadata,directories,writes,filters=None):
            target=ledger.path/scope[0]/'other.json';target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(b'{"other":"actor"}')
            return real(ledger,scope,before,metadata,directories,writes,filters)
        with patch.object(effects.LedgerRoot,'apply',race):value,_,*_=self.execute(self.request())
        self.assertEqual(value['exit_code'],2);self.assertTrue(value['native_result_available']);self.assertFalse(value['retained_complete_outputs_rederived'])
        self.assertEqual((self.target/'status/collection-attempts/owner__repo/other.json').read_bytes(),b'{"other":"actor"}')

    def test_symlink_hardlink_fifo_history_output_and_product_root_guards(self):
        secret=self.base/'secret';secret.write_bytes(b'controlled unrelated secret')
        bucket=self.target/'status/collection-attempts/owner__repo';bucket.mkdir(parents=True)
        for kind in ('symlink','hardlink','fifo'):
            path=bucket/(kind+'.json')
            if kind=='symlink':path.symlink_to(secret)
            elif kind=='hardlink':os.link(secret,path)
            else:os.mkfifo(path,0o600)
            with self.assertRaises((ValueError,OSError)):self.execute(self.request())
            self.assertEqual(secret.read_bytes(),b'controlled unrelated secret');path.unlink()
        for root in (ROOT,self.instance):
            with self.assertRaisesRegex(ValueError,'external_intake_record_root'):self.execute(self.request(root=str(root)))
        record,_=self.compare(self.request());retry=self.request('retry',attempt_path=record['selected'],output=str(self.target/record['selected']))
        with self.assertRaisesRegex(ValueError,'ledger_history'):self.execute(retry)

    def test_cli_native_event_stdout_and_provider_environment_defaults_match_original(self):
        args=['event','--repo',str(self.target),'--profile',PROFILE,'--at',AT,'--repository-id','owner/repo','--run-id','42','--evidence-type','governance_result','--collector-id','central-governance-intake','--artifact-name','governance-control-evaluation','--intake-type','devsecops_governance','--status','success','--started-at','2026-11-18T02:59:59Z']
        env={'GITHUB_REPOSITORY':'central/governance','GITHUB_WORKFLOW':'Synthetic native environment','GITHUB_RUN_ID':'84','GITHUB_RUN_ATTEMPT':'2','GITHUB_EVENT_NAME':'repository_dispatch'};out=io.StringIO();err=io.StringIO()
        with patch.dict(os.environ,env),redirect_stdout(out),redirect_stderr(err):code=run(args,self.instance,self.settings)
        expected=oracle.snapshot(self.target);shutil.rmtree(self.target);self.target.mkdir();self.old.schema_files()
        oldargs=[arg for arg in args[1:] if arg not in ()]
        for flag,value in [('--repo',str(self.target)),('--profile',PROFILE),('--at',AT)]:index=oldargs.index(flag);del oldargs[index:index+2]
        oldcode,oldout,olderr=self.old.run('event',oldargs,at=AT,environment=env)
        self.assertEqual((code,out.getvalue().encode(),err.getvalue().encode()),(oldcode,oldout,olderr));self.assertEqual(oracle.snapshot(self.target),expected)

    def test_unrelated_global_conflicts_are_never_enumerated_or_retained(self):
        first,_=self.compare(self.request());root=self.target/'status/intake-conflicts/collection-attempts';root.mkdir(parents=True,exist_ok=True)
        # Reading this unrelated leaf would fail the single-link guard.
        secret=self.base/'private-unrelated';secret.write_bytes(b'unrelated synthetic private bytes');(root/'other-repo.json').symlink_to(secret)
        native_scan=effects.directory_names
        def scan(fd):
            row=os.fstat(fd);other=root.stat()
            if (row.st_dev,row.st_ino)==(other.st_dev,other.st_ino):raise AssertionError('enumerated global conflict history')
            return native_scan(fd)
        with patch.object(effects,'directory_names',scan):value,_,*_=self.execute(self.request(message='Changed for selected conflict'))
        self.assertEqual(value['exit_code'],0)
        inputs,files=self.app.input_data(value['input_id']);self.assertEqual(len(inputs['conflict_filter']),1)
        self.assertIsNotNone(inputs['parent_input_id']);self.assertNotIn(b'unrelated synthetic private bytes',files.values())
        self.assertFalse(any(name.endswith('other-repo.json') for name in files));self.assertTrue((root/'other-repo.json').is_symlink())
        self.assertEqual(self.app.intent(value['operation_id'])['initial_input_id'],inputs['parent_input_id'])

    def test_different_repository_metadata_queries_can_overlap_under_shared_root(self):
        barrier=threading.Barrier(2,timeout=15)
        def transport(*args,**kwargs):barrier.wait();return Response(json.dumps(RUN).encode())
        with patch.object(adapter,'open_https',side_effect=transport),ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(self.app.execute,self.request(repository_id='owner/parallel-'+str(n))) for n in range(2)]
            values=[future.result(timeout=30)[0] for future in futures]
        self.assertEqual([v['exit_code'] for v in values],[0,0])
        for value in values:self.assertTrue(self.app.inspect(value['assessment_id'])['retained_complete_outputs_rederived'])
        # Common metadata and payload pieces are stored once across snapshots.
        manifests=[self.app.material(self.app.inputs,v['input_id'])[0] for v in values]
        referenced={row['sha256'] for value in values for row in self.app.material(self.app.artifacts,value['artifact_id'])[0]['files'].values()}
        self.assertLess(len(referenced),sum(len(self.app.material(self.app.artifacts,v['artifact_id'])[0]['files']) for v in values))
        self.assertEqual(len(manifests),2)

    def test_same_bucket_and_shared_native_output_are_exclusive_without_dispatch(self):
        first,_=self.compare(self.request());retry=self.request('retry',attempt_path=first['selected'],output=str(self.output))
        from lib.supplement_application import write_lock
        from lib.candidate_workspace import private_directory
        import hashlib
        key=hashlib.sha256(json.dumps(['native-output',str(self.output).casefold()]).encode()).hexdigest()
        with write_lock(private_directory(self.app.locks/key)):
            with self.assertRaisesRegex(ValueError,'writer_busy'):self.execute(retry)
        self.assertFalse(self.output.exists())

    def test_selected_conflict_capture_retains_original_input_before_provider_access(self):
        self.compare(self.request());initial=set(p.stem for p in self.app.inputs.iterdir())
        def transport(*args,**kwargs):
            pending=[json.loads(p.read_text()) for p in self.app.intents.glob('*.json') if json.loads(p.read_text())['state']=='pending']
            self.assertEqual(len(pending),1);intent=pending[0];self.assertEqual(intent['stage'],'metadata_requested')
            self.assertEqual(intent['input_id'],intent['initial_input_id']);self.assertNotIn(intent['input_id'],initial)
            inputs,unused=self.app.input_data(intent['input_id']);self.assertEqual(inputs['conflict_filter'],[])
            return Response(json.dumps(RUN).encode())
        with patch.object(adapter,'open_https',side_effect=transport):value,_,*_=self.app.execute(self.request(message='changed'))
        self.assertEqual(value['exit_code'],0);self.assertNotEqual(self.app.intent(value['operation_id'])['initial_input_id'],value['input_id'])

    def test_native_payload_budget_stops_before_effects_but_retains_metadata_response(self):
        # JSON escaping expands the native record beyond the bounded raw body.
        raw=json.dumps({**RUN,'name':'é'*100},ensure_ascii=False).encode()
        with patch.object(adapter,'open_https',return_value=Response(raw)),patch.object(logic,'MAX_FILE',len(raw)+100):
            value,payload,*_=self.app.execute(self.request())
        self.assertEqual(value['exit_code'],2);self.assertFalse(value['effects_attempted']);self.assertFalse(value['native_result_available'])
        meta,files=self.app.material(self.app.artifacts,value['artifact_id']);self.assertEqual(files['metadata-response.bin'],raw)
        self.assertEqual(oracle.snapshot(self.target),{})

    def test_original_partial_retry_helper_and_unicode_identity_are_preserved(self):
        minimum={'errors':[{'retryable':True}],'repository_id':'owner/repo','source':{'run_id':42,'artifact_name':'application-evidence'},'collector':{'id':'central-vulnerability-scan-collector'},'evidence_type':'vulnerability_scan','attempt_id':'original-helper'}
        self.assertEqual(logic.retry_plan(minimum,adapter.ROUTES),self.old.modules['retry']['build_retry_plan'](minimum))
        self.compare(self.request(message='Überprüfung der Größe'),response={**RUN,'name':'Überprüfung'})

    def test_first_status_path_component_and_sorted_first_identity_match_original_conflict(self):
        self.target=self.base/'status'/'nested-target';self.target.mkdir(parents=True,mode=0o700)
        self.old=oracle.Original(FIXTURES,self.target);self.old.schema_files()
        first,_=self.compare(self.request());path=self.target/first['selected'];raw=path.read_bytes();path.unlink()
        earlier=path.with_name('000-first.json');earlier.write_bytes(raw);path.with_name('999-second.json').write_bytes(raw)
        value,_=self.compare(self.request(message='different'))
        self.assertTrue(value['selected'].endswith('000-first.json'))
        conflicts=list((self.target/'status/intake-conflicts/collection-attempts').glob('*.json'))
        self.assertTrue(json.loads(conflicts[0].read_text())['target_path'].startswith('status/nested-target/status/'))

    def tls_servers(self):
        config=self.base/'tls.cnf';key=self.base/'tls-key.pem';cert=self.base/'tls-cert.pem'
        config.write_text('[req]\ndistinguished_name=dn\nx509_extensions=ext\nprompt=no\n[dn]\nCN=localhost\n[ext]\nsubjectAltName=DNS:localhost,IP:127.0.0.1\nbasicConstraints=critical,CA:TRUE\n')
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-days','1','-keyout',str(key),'-out',str(cert),'-config',str(config)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,timeout=30)
        key.chmod(0o600);cert.chmod(0o600);calls=[];routes={};hook=[None]
        class Handler(BaseHTTPRequestHandler):
            def do_GET(handler):
                calls.append((handler.server.server_port,handler.path,dict(handler.headers)))
                if hook[0] is not None:hook[0]()
                status,headers,body=routes.get((handler.server.server_port,handler.path),(200,{},json.dumps(RUN).encode()))
                handler.send_response(status)
                for name,value in headers.items():handler.send_header(name,value)
                handler.end_headers()
                try:handler.wfile.write(body)
                except (BrokenPipeError,ConnectionResetError):pass
            def log_message(*args):pass
        servers=[]
        for unused in range(2):
            server=ThreadingHTTPServer(('127.0.0.1',0),Handler);context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(cert,key)
            server.socket=context.wrap_socket(server.socket,server_side=True);worker=threading.Thread(target=server.serve_forever,daemon=True);worker.start()
            self.addCleanup(worker.join,5);self.addCleanup(server.server_close);self.addCleanup(server.shutdown);servers.append(server)
        return servers,calls,routes,hook,cert

    def test_real_https_native_cli_headers_journal_and_complete_wire_match_original(self):
        servers,calls,routes,hook,cert=self.tls_servers();port=servers[0].server_port;endpoint=f'https://127.0.0.1:{port}'
        request=self.request(api_url=endpoint,token_origin='explicit');token='synthetic-read-token-only'
        def check_journal():
            values=[json.loads(p.read_text()) for p in self.app.intents.glob('*.json') if json.loads(p.read_text())['state']=='pending']
            if values:self.assertEqual(values[-1]['stage'],'metadata_requested');self.app.input_data(values[-1]['input_id'])
        hook[0]=check_journal
        with patch.dict(os.environ,{'SSL_CERT_FILE':str(cert)}):value,payload,stdout,stderr=self.app.execute(request,token=token)
        self.assertEqual(value['exit_code'],0);candidate=oracle.snapshot(self.target);shutil.rmtree(self.target);self.target.mkdir();self.old.schema_files()
        code,out,err=self.old.run('attempt',self.cli_args(request)+['--token',token],at=AT,environment={'SSL_CERT_FILE':str(cert)},native_transport=True)
        self.assertEqual((code,out,err),(0,stdout,stderr));self.assertEqual(oracle.snapshot(self.target),candidate)
        self.assertEqual(len(calls),2);self.assertEqual(calls[0],calls[1])
        headers={name.casefold():value for name,value in calls[0][2].items()};self.assertEqual(headers['authorization'],'Bearer '+token)
        self.assertEqual(headers['accept'],'application/vnd.github+json');self.assertEqual(calls[0][1],'/repos/owner/repo/actions/runs/42')
        self.assertTrue(value['lookup']['response_received']);self.assertFalse(value['native_outcome_authenticated'])
        for directory in (self.app.inputs,self.app.artifacts):
            for manifest in directory.glob('*/manifest.json'):self.assertNotIn(token,manifest.read_text())
        for blob in self.app.blobs.iterdir():self.assertNotIn(token.encode(),blob.read_bytes())

    def test_real_https_redirects_errors_and_response_budget_follow_original_transport(self):
        servers,calls,routes,hook,cert=self.tls_servers();one,two=[s.server_port for s in servers];path='/repos/owner/repo/actions/runs/42'
        token='synthetic-redirect-token-only';endpoint=f'https://127.0.0.1:{one}'
        scenarios=[('same',302,{'Location':endpoint+'/same'},b'',None),
            ('cross',302,{'Location':f'https://127.0.0.1:{two}/cross'},b'',None),
            ('downgrade',302,{'Location':'http://127.0.0.1:1/forbidden'},b'','ValueError'),
            ('denied',403,{},b'private synthetic error body','HTTPError'),
            ('malformed',200,{},b'{broken','JSONDecodeError'),
            ('oversize',200,{'Content-Length':str(logic.MAX_FILE+1)},b'','ValueError')]
        for label,status,headers,body,error in scenarios:
            with self.subTest(label=label):
                routes[(one,path)]=(status,headers,body);calls.clear()
                with patch.dict(os.environ,{'SSL_CERT_FILE':str(cert)}):observation,raw=adapter.acquire(endpoint,'owner/repo','42',token,lambda:None)
                adapter_calls=list(calls);calls.clear()
                with patch.dict(os.environ,{'SSL_CERT_FILE':str(cert)}):
                    if error is None:original=self.old.modules['attempt']['github_get_json'](endpoint+path,token)
                    else:
                        with self.assertRaises(Exception) as raised:self.old.modules['attempt']['github_get_json'](endpoint+path,token)
                        self.assertEqual(type(raised.exception).__name__,error)
                        if hasattr(raised.exception,'close'):raised.exception.close()
                self.assertEqual(adapter_calls,calls);self.assertEqual(observation['error_type'],error)
                if label in ('same','cross'):
                    self.assertEqual(json.loads(raw),original)
                    redirected={k.casefold():v for k,v in calls[-1][2].items()}
                    self.assertEqual(redirected.get('authorization'),'Bearer '+token if label=='same' else None)
                if label=='malformed':self.assertTrue(observation['body_retained']);self.assertEqual(raw,body)
                if label=='oversize':self.assertFalse(observation['body_retained']);self.assertIsNone(raw)
                if label=='denied':self.assertEqual(observation['http_status'],403);self.assertIsNone(raw)
                if label=='downgrade':self.assertEqual(len(calls),1)

    def test_provider_environment_token_precedence_and_aborted_journal_prevent_io(self):
        environment={'GH_RESULT_INTAKE_TOKEN':'first-synthetic','GH_TOKEN':'second-synthetic','GITHUB_TOKEN':'third-synthetic'}
        with patch.dict(os.environ,environment,clear=True):
            self.assertEqual(adapter.token_value('explicit-synthetic'),('explicit-synthetic','explicit'))
            self.assertEqual(adapter.token_value(''),('first-synthetic','environment'))
            del os.environ['GH_RESULT_INTAKE_TOKEN'];self.assertEqual(adapter.token_value(''),('second-synthetic','environment'))
            del os.environ['GH_TOKEN'];self.assertEqual(adapter.token_value(''),('third-synthetic','environment'))
            del os.environ['GITHUB_TOKEN'];self.assertEqual(adapter.token_value(''),(None,'none'))
        with patch.object(adapter,'open_https',side_effect=AssertionError('I/O before durable journal')):
            with self.assertRaisesRegex(ValueError,'journal failed'):adapter.acquire('https://api.example.invalid','owner/repo','42','synthetic',lambda:(_ for _ in ()).throw(ValueError('journal failed')))

    def test_unrelated_conflict_directory_creation_during_lookup_does_not_abort_new_repo(self):
        def transport(*args,**kwargs):
            root=self.target/'status/intake-conflicts/collection-attempts';root.mkdir(parents=True,exist_ok=True)
            (root/'unrelated.json').write_bytes(b'unrelated retained bytes')
            return Response(json.dumps(RUN).encode())
        with patch.object(adapter,'open_https',side_effect=transport):value,_,*_=self.app.execute(self.request())
        self.assertEqual(value['exit_code'],0)
        unused,files=self.app.material(self.app.artifacts,value['artifact_id'])
        self.assertFalse(any(name.endswith('unrelated.json') for name in files))

    def test_cli_attempt_and_retry_absolute_input_and_receipt_inspection_match_original(self):
        request=self.request();args=['attempt','--repo',str(self.target),'--profile',PROFILE,'--at',AT,*self.cli_args(request)]
        out=io.StringIO();err=io.StringIO()
        with patch.object(adapter,'open_https',return_value=Response(json.dumps(RUN).encode())),redirect_stdout(out),redirect_stderr(err):code=run(args,self.instance,self.settings)
        candidate=oracle.snapshot(self.target);shutil.rmtree(self.target);self.target.mkdir();self.old.schema_files()
        original=self.old.run('attempt',self.cli_args(request),at=AT,run=RUN)
        self.assertEqual((code,out.getvalue().encode(),err.getvalue().encode()),original);self.assertEqual(oracle.snapshot(self.target),candidate)
        name=out.getvalue().strip();absolute=str(self.target/name)
        args=['retry','--repo',str(self.target),'--profile',PROFILE,'--at',AT,'--attempt-path',absolute,'--native-output',str(self.output)]
        out=io.StringIO();err=io.StringIO()
        with redirect_stdout(out),redirect_stderr(err):code=run(args,self.instance,self.settings)
        after=self.output.read_bytes();self.output.unlink()
        original=self.old.run('retry',['--attempt-path',absolute,'--github-output',str(self.output)],at=AT)
        self.assertEqual((code,out.getvalue().encode(),err.getvalue().encode()),original);self.assertEqual(self.output.read_bytes(),after)
        out=io.StringIO()
        with redirect_stdout(out):code=run(args+['--format','receipt'],self.instance,self.settings)
        receipt=json.loads(out.getvalue());self.assertEqual(code,0);self.assertFalse(receipt['workflow_dispatched'])
        out=io.StringIO()
        with redirect_stdout(out):self.assertEqual(run(['inspect','--assessment',receipt['assessment_id']],self.instance,self.settings),0)
        self.assertEqual(json.loads(out.getvalue())['assessment_id'],receipt['assessment_id'])

    def test_native_append_race_preserves_other_actor_and_captures_partial_error(self):
        value,_=self.compare(self.request());retry=self.request('retry',attempt_path=value['selected'],output=str(self.output))
        self.output.write_bytes(b'before');native=effects.append_output
        def race(path,raw,before,metadata):path.write_bytes(b'other actor');return native(path,raw,before,metadata)
        with patch.object(effects,'append_output',side_effect=race):checked,_,*_=self.app.execute(retry)
        self.assertEqual(checked['exit_code'],2);self.assertTrue(checked['effects_attempted']);self.assertEqual(self.output.read_bytes(),b'other actor')
        unused,files=self.app.material(self.app.artifacts,checked['artifact_id']);self.assertEqual(files['native-output-after.bin'],b'other actor')
        self.assertFalse(checked['retained_complete_outputs_rederived'])

    def test_source_change_guard_prevents_native_client_and_leaves_pending_operation(self):
        real_current=self.app.current;changed=[False];native_acquire=adapter.acquire
        def current():
            if changed[0]:raise ValueError('intake_record_program_changed')
            real_current()
        def acquire(*args):
            changed[0]=True
            return native_acquire(*args)
        with patch.object(self.app,'current',side_effect=current),patch('lib.intake_recording_application.acquire_intake_record_metadata',side_effect=acquire),patch.object(adapter,'open_https',side_effect=AssertionError('changed source queried provider')):
            with self.assertRaisesRegex(ValueError,'program_changed'):self.app.execute(self.request())
        operations=list(self.app.intents.glob('*.json'));self.assertEqual(len(operations),1)
        status=self.app.status(operations[0].stem);self.assertEqual(status['state'],'pending');self.assertFalse(status['automatic_resume'])
        self.assertEqual(oracle.snapshot(self.target),{})

    def test_bucket_file_and_byte_budgets_are_bounded_before_native_client(self):
        bucket=self.target/'status/collection-attempts/owner__repo';bucket.mkdir(parents=True)
        for n in range(3):(bucket/(str(n)+'.json')).write_bytes(b'{}')
        with patch.object(effects,'MAX_FILES',2),patch.object(adapter,'open_https',side_effect=AssertionError('over-budget bucket queried provider')):
            with self.assertRaisesRegex(ValueError,'file_count_budget'):self.app.execute(self.request())
        with patch.object(effects,'MAX_TOTAL',4),patch.object(adapter,'open_https',side_effect=AssertionError('over-budget bucket queried provider')):
            with self.assertRaisesRegex(ValueError,'total_budget'):self.app.execute(self.request())
        self.assertFalse(list(self.app.intents.iterdir()))
