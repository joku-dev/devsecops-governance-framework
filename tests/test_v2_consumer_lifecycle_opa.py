"""Independent pinned OPA, opaque captured streams and complete inert replay."""
from pathlib import Path
import base64,copy,hashlib,io,json,os,shutil,subprocess,sys,tempfile,unittest,zipfile
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.providers.consumer_lifecycle_opa import NativeConsumerOPA,LegacyConsumerOPAProfile,QUERY,POLICY_SHA256
from lib.consumer_lifecycle_opa import ReplayConsumerOPA,result_value,frame_value,cleanup_value
from lib.providers.consumer_lifecycle_io import NativeConsumerIO
from lib.consumer_lifecycle_io import ReplayConsumerIO
from lib.lifecycle_preflight_context import PreflightPaths
from lib.personal_channel_ports import exclusive_factory
from lib.pilot_run_private_temporary import PrivateTemporaryFactory
from lib.providers.pilot_run_temporary import NativeTemporaryFactory
from lib.pilot_run_temporary import ReplayTemporaryFactory
from lib.providers.synthetic_lifecycle_storage import Record,read_record
from lib.requirement_review_output import RetainedOutputError
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
import test_v2_consumer_lifecycle_model as model
import test_v2_consumer_lifecycle_io as files
from test_portable_runtime import OPA

class ConsumerOPA(unittest.TestCase):
    def setUp(self):
        old=os.umask(0o077);self.addCleanup(os.umask,old);t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.parent=Path(t.name).resolve();self.source=self.parent/'source';self.source.mkdir(mode=0o700);model.materialize(self.source);self.serial=0
        capture=self.source/'generated/reports/consumer-lifecycle-preflight/main-run-34778861076';self.policy=(capture/'producer/policies/opa/architecture_operation_readiness.rego').read_bytes();self.assertEqual(hashlib.sha256(self.policy).hexdigest(),POLICY_SHA256)
        with zipfile.ZipFile(io.BytesIO((capture/'artifact.zip').read_bytes())) as bundle:self.data=bundle.read('architecture-release-input.json')
    def execute(self,mode,*,tool=OPA,input_bytes=None):
        self.serial+=1;private=self.parent/f'private-{self.serial}';private.mkdir(mode=0o700);scratch=private/'opa-workarea';scratch.mkdir(mode=0o700);temporary=self.parent/f'temporary-{self.serial}';temporary.mkdir(mode=0o700);record=Record(private/'records',{'prototype':'whole independent consumer OPA','mode':mode},{'prototype':True});record.append({'kind':'execution-intent'});owner=NativeConsumerIO(record,mode=mode,cwd=str(self.source),private_state=private,product_root=ROOT,source=str(self.source),transaction_name=files.transaction_name);hashes=frozenset({hashlib.sha256(Path(tool).read_bytes()).hexdigest()});profile=LegacyConsumerOPAProfile();native=NativeConsumerOPA(owner,self.source,tool=str(tool),approved_hashes=hashes,workarea=scratch)
        def run(io,port,factory):
            paths=PreflightPaths(str(self.source),str(self.source),io,exclusive_factory)
            with factory.TemporaryDirectory() as name:
                path=paths.path(name);(path/'input.json').write_bytes(self.data if input_bytes is None else input_bytes);(path/'policy.rego').write_bytes(self.policy);command=['opa','eval','--format=json','--data',str(path/'policy.rego'),'--input',str(path/'input.json'),QUERY]
                try:
                    value=port.run(command,capture_output=True,check=True,timeout=30);result={'returncode':value.returncode,'stdout':value.stdout,'stderr':value.stderr,'error':None}
                except RetainedOutputError as caught:result={'returncode':None,'stdout':None,'stderr':None,'error':{'type':caught.original_type,'message':caught.original_message}}
            return result
        factory=PrivateTemporaryFactory(owner,str(temporary)) if mode=='private-candidate' else NativeTemporaryFactory(owner,str(temporary));actual=run(owner,native,factory);self.assertFalse(record.capture_incomplete);self.assertEqual(native.resources,{});self.assertEqual(list(scratch.iterdir()),[]);self.assertEqual(list(temporary.iterdir()),[])
        record.finish('complete',{'exit_code':1 if actual['error'] else 0},owner.touched);_,_,_,events,blob,closed=read_record(record.root);cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};wires=[]
        for row in events:
            if row.get('kind')=='returned':
                value=json.loads(cache[row['value']['sha256']]) if row['encoding']=='json' else None
                if isinstance(value,dict) and value.get('specification',{}).get('kind')=='opa-checked-run':wires.append(value)
        self.assertEqual(len(wires),1);wire=wires[0]
        # Compare the native mode to the exact original subprocess API while
        # retaining recorded stdout/stderr as raw bytes for failures as well.
        if mode=='selected-files':
            command=wire['specification']['original_arguments'];p=Path(command[4]).parent;p.mkdir(mode=0o700);(p/'policy.rego').write_bytes(self.policy);(p/'input.json').write_bytes(self.data if input_bytes is None else input_bytes)
            try:
                old=subprocess.run([str(tool),*command[1:]],capture_output=True,timeout=30)
                self.assertEqual(old.stdout,cache[wire['stdout']['sha256']]);self.assertEqual(old.stderr,cache[wire['stderr']['sha256']]);self.assertEqual(old.returncode,wire['returncode'])
            finally:shutil.rmtree(p)
        replay=ReplayConsumerIO(events,lambda ref:cache[ref['sha256']],mode,str(self.source),source=str(self.source),transaction_name=files.transaction_name);port=ReplayConsumerOPA(replay,self.source,profile=profile,tool=str(tool),approved_hashes=hashes,workarea=scratch);factory=PrivateTemporaryFactory(replay,str(temporary)) if mode=='private-candidate' else ReplayTemporaryFactory(replay,str(temporary))
        shutil.rmtree(self.source);shutil.rmtree(scratch);shutil.rmtree(temporary)
        with patch('subprocess.Popen',side_effect=AssertionError('No policy execution')),patch('os.open',side_effect=AssertionError('No selected/native files')),patch('lib.providers.consumer_lifecycle_tools.program_identity',side_effect=AssertionError('No tool lookup')):
            self.assertEqual(run(replay,port,factory),actual);replay.finish()
        for name,raw in cache.items():self.assertEqual(blob({'sha256':name,'bytes':len(raw)}),raw)
        self.assertTrue(closed());return actual,wire,cache
    def test_actual_pinned_independent_opa_matches_original_query_and_replays_all_effects(self):
        for mode in ('private-candidate','selected-files'):
            with self.subTest(mode=mode):
                if not self.source.exists():self.source.mkdir(mode=0o700);model.materialize(self.source)
                actual,wire,cache=self.execute(mode);self.assertIsNone(actual['error']);self.assertEqual(len(json.loads(actual['stdout'])['result'][0]['expressions'][0]['value']),2)
    def test_native_original_opa_error_and_all_raw_pipes_are_retained(self):
        actual,wire,cache=self.execute('selected-files',input_bytes=b'{"incomplete":');self.assertEqual(actual['error']['type'],'CalledProcessError');self.assertNotEqual(wire['returncode'],0)
    def test_resealed_materialization_and_tool_observations_fail_closed(self):
        actual,wire,cache=self.execute('private-candidate');profile=LegacyConsumerOPAProfile();spec=wire['specification'];hashes=frozenset({wire['program']['sha256']})
        for mutate in (lambda v:v['program'].update(sha256='0'*64),lambda v:v['actual_arguments'].append('--unsafe'),lambda v:v['observation'].update(OS_network_or_process_tree_isolation_attested=True),lambda v:v.update(returncode=7)):
            bad=copy.deepcopy(wire);mutate(bad)
            with self.assertRaises(IntegrityError):result_value(bad,spec,profile,lambda ref:cache[ref['sha256']],str(OPA),hashes)
        frame=spec['materialization'];args={'workarea':str(Path(frame['path']).parent),'files':frame['files']};bad=copy.deepcopy(frame);bad['path']=str(self.source/'tmpconsumer-opa-foreign')
        with self.assertRaises(IntegrityError):frame_value(bad,args)
        with self.assertRaises(IntegrityError):cleanup_value({'frame':frame,'owned_before':True,'absent_after':False},frame)
    def test_only_exact_original_policy_query_and_active_temporary_are_admitted(self):
        profile=LegacyConsumerOPAProfile()
        with patch('subprocess.Popen',side_effect=AssertionError('No process')):
            for command in (['opa','version'],['sh','-c','false'],['opa','eval','--format=json','--data','/tmp/policy.rego','--input','/tmp/input.json','data.other.deny']):
                with self.assertRaises(InputAdmissionError):profile.request(command,capture_output=True,check=True,timeout=30,source=str(self.source),cwd=str(self.source),owner=object())
            with self.assertRaises(InputAdmissionError):profile.admit_files({'policy.rego':self.policy+b'\n','input.json':self.data})
    def test_added_materialization_failure_is_incomplete_without_original_verdict_or_process(self):
        private=self.parent/'materialization-failure';private.mkdir(mode=0o700);scratch=private/'scratch';scratch.mkdir(mode=0o700);temporary=self.parent/'controlled-temporary';temporary.mkdir(mode=0o700);record=Record(private/'records',{'prototype':'added-materialization-failure'},{'prototype':True});record.append({'kind':'execution-intent'});owner=NativeConsumerIO(record,mode='private-candidate',cwd=str(self.source),private_state=private,product_root=ROOT,source=str(self.source),transaction_name=files.transaction_name);paths=PreflightPaths(str(self.source),str(self.source),owner,exclusive_factory);port=NativeConsumerOPA(owner,self.source,tool=str(OPA),approved_hashes=frozenset({hashlib.sha256(OPA.read_bytes()).hexdigest()}),workarea=scratch)
        with PrivateTemporaryFactory(owner,str(temporary)).TemporaryDirectory() as name:
            path=paths.path(name);(path/'policy.rego').write_bytes(self.policy);(path/'input.json').write_bytes(self.data);command=['opa','eval','--format=json','--data',str(path/'policy.rego'),'--input',str(path/'input.json'),QUERY]
            with patch.object(port,'create',side_effect=OSError(28,'isolated private workarea full')),patch('subprocess.Popen',side_effect=AssertionError('No original process')):
                with self.assertRaisesRegex(InputAdmissionError,'materialization_capture_incomplete'):port.run(command,capture_output=True,check=True,timeout=30)
        self.assertTrue(record.capture_incomplete)
        with self.assertRaisesRegex(ValueError,'incomplete_capture_cannot_complete'):record.finish('complete',{'exit_code':0},owner.touched)
