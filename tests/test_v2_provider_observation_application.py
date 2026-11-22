"""Registered whole observer, opaque credential cleanup and complete private replay."""
from pathlib import Path
from unittest.mock import patch
import copy,hashlib,json,os,shutil,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_provider_observation_context as whole
import test_v2_provider_observation as reference
from test_v2_provider_observation_reads import Response
from lib.provider_observation_application import generate,inspect,request_valid,PROFILE
from lib.provider_observation_ports import Record,read_record,NativeObservationBackend
from lib.portable.runtime import source_digest
from lib.functional_parity import git_read
from test_portable_runtime import OPA


class ObservationApplication(unittest.TestCase):
    def setUp(self):
        self.fixture=whole.WholeRecordedObservation();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups);self.base=self.fixture.world.base;self.node=self.base/'node';self.node.mkdir(mode=0o700);self.identity={'node_id':'a'*32,'source_revision':git_read(ROOT,'rev-parse','HEAD').decode().strip(),'runtime_source_digest':source_digest()};self.calls=[]
    def capture(self,provider='github',action='reviews',case='normal',*,reflection=False):
        config,argv=self.fixture.arguments(provider,action,case);rows,_=reference.routes(provider);calls=self.calls;test=self
        class Opener:
            def open(this,request,*,timeout):
                test.assertEqual(request.get_method(),'GET');test.assertEqual(request.get_header('Authorization'),'Bearer '+whole.TOKEN);path=request.full_url[len(config['api_url'].rstrip('/')):];calls.append(path)
                return Response(json.dumps({'reflected':whole.TOKEN} if reflection else copy.deepcopy(rows[path])).encode())
        with patch('lib.providers.transports.build_opener',return_value=Opener()):return generate({'legacy_arguments':argv,'working_directory':str(self.fixture.work)},self.node,self.identity,clock=lambda:reference.AT)
    def test_all_three_registered_review_providers_replay_after_profile_credential_and_output_removal(self):
        for provider in ('github','gitlab','bitbucket-dc'):
            with self.subTest(provider=provider):
                receipt,result=self.capture(provider);self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],0);self.assertTrue(result['kernel_result']['atomic_output_snapshot']['files']['candidate.json']['kind']=='file');checked=inspect(receipt['record_root'],node=self.identity)
                shutil.rmtree(self.fixture.work)
                with patch('subprocess.Popen',side_effect=AssertionError('No replay tool')),patch('lib.providers.transports.build_opener',side_effect=AssertionError('No replay HTTP')):self.assertEqual(inspect(receipt['record_root']),checked)
                with self.assertRaisesRegex(ValueError,'foreign_node'):inspect(receipt['record_root'],node={**self.identity,'node_id':'b'*32})
                for path in Path(receipt['record_root']).rglob('*'):
                    if path.is_file():self.assertNotIn(whole.TOKEN.encode(),path.read_bytes())
    def test_both_non_GitHub_security_branches_keep_all_sixteen_original_criteria(self):
        for provider in ('gitlab','bitbucket-dc'):
            with self.subTest(provider=provider):
                receipt,result=self.capture(provider,'security');self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],0);candidate=json.loads((self.fixture.work/'output/candidate.json').read_bytes());self.assertEqual(len(candidate['criteria']),16);self.assertFalse(candidate['official_acceptance']);self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
    def test_original_missing_change_exit_and_profile_failure_remain_distinct_from_technical_incomplete(self):
        for case,code in [('missing-change',2),('public-profile',1)]:
            with self.subTest(case=case):
                receipt,result=self.capture(case=case);self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],code);checked=inspect(receipt['record_root']);self.assertEqual(checked['original_exit_code'],code)
                if case=='missing-change':self.assertEqual(json.loads((self.fixture.work/'output/native-capture.json').read_bytes()),[])
                else:self.assertFalse((self.fixture.work/'output').exists())
    def test_lost_reader_intent_revokes_credentials_and_never_performs_the_first_GET(self):
        append=Record.append;release=NativeObservationBackend.release_resources;backends=[]
        def lose(record,row):
            if row.get('kind')=='provider-observation-read-intent':raise OSError('Controlled private intent loss')
            return append(record,row)
        def cleanup(backend):backends.append(backend);return release(backend)
        with patch.object(Record,'append',lose),patch.object(NativeObservationBackend,'release_resources',cleanup):receipt,_=self.capture()
        self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code']);self.assertEqual(self.calls,[]);self.assertEqual(len(backends),1);self.assertIsNone(backends[0].credentials.value);self.assertTrue(backends[0].reads.closed)
        self.assertFalse(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
    def test_selected_credential_reflection_and_request_authority_additions_are_rejected(self):
        receipt,_=self.capture(reflection=True);self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code']);request,*_=read_record(receipt['record_root'])
        for change in ({'schema_version':True},{'profile':'other'},{'argv':['secret\n']},{'official_acceptance':True}):
            with self.subTest(change=change),self.assertRaises(ValueError):request_valid({**request,**change})
        for path in Path(receipt['record_root']).rglob('*'):
            if path.is_file():self.assertNotIn(whole.TOKEN.encode(),path.read_bytes())
    def test_actual_registered_CLI_original_help_inspect_and_replay_leave_node_paused(self):
        node=self.base/'actual-observation-node';cli=[sys.executable,'-B',str(ROOT/'scripts/axiom_v2.py')]
        def call(arguments):
            value=subprocess.run([*cli,*map(str,arguments)],capture_output=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=120);self.assertEqual(value.returncode,0,(value.stdout[-3000:],value.stderr[-3000:]));return value
        call(['--instance',node,'init','--development','--opa',OPA]);receipt=json.loads(call(['--instance',node,'provider-observation','capture','--profile',PROFILE,'--','--help']).stdout);self.assertEqual(receipt['state'],'complete');self.assertEqual(receipt['original_exit_code'],0)
        checked=json.loads(call(['--instance',node,'provider-observation','inspect','--record',receipt['record_root']]).stdout);self.assertEqual(json.loads(call(['provider-observation','replay','--record',receipt['record_root']]).stdout),checked);self.assertEqual(json.loads((node/'consumer.json').read_bytes())['mode'],'paused')
