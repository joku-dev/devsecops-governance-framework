"""Registered whole self-security publisher with Source restore epochs and real CLI."""
from pathlib import Path
from unittest.mock import patch
import hashlib,json,os,shutil,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_self_security_publication_native as reference
from lib.self_security_publication_application import generate,inspect,request_valid,PROFILE
from lib.self_security_publication_ports import Record,NativeIO,read_record
from lib.portable.runtime import source_digest
from lib.functional_parity import git_read
from lib.requirement_validation_budget import InputAdmissionError
from test_portable_runtime import OPA


class SelfSecurityPublisherApplication(unittest.TestCase):
    def setUp(self):
        self.case=reference.SelfSecurityNativeFixture();self.case.setUp();self.addCleanup(self.case.doCleanups);self.source,self.origin,self.tools,self.output,self.summary,self.environment=self.case.fixture('candidate');self.node=self.case.base/'node';self.node.mkdir(mode=0o700);self.identity={'node_id':'a'*32,'source_revision':git_read(ROOT,'rev-parse','HEAD').decode().strip(),'runtime_source_digest':source_digest()};self.settings={**self.identity,'opa':str(OPA),'opa_sha256':hashlib.sha256(OPA.read_bytes()).hexdigest()}
    def options(self,**extra):return {'source_worktree':str(self.source),'working_directory':str(ROOT),'profile':PROFILE,'transport_profile':'legacy-self-security-publisher-local-test-v1','local_origin_root':str(self.case.base),'repository':'owner/repo','run_id':'123','attempt':'2','workflow_ref':'refs/heads/main','provider_executable':str(self.tools/'gh'),'output_file':str(self.output),'summary_file':str(self.summary),**extra}
    def generate(self,**extra):return generate(self.options(**extra),self.node,self.settings,native_environment=self.environment)
    def test_whole_native_Source_restore_record_and_replay_after_source_tools_and_outputs_are_removed(self):
        receipt,result=self.generate();self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],0,result);self.assertFalse(receipt['official_acceptance']);self.assertFalse(receipt['authority_transferred']);self.assertTrue(receipt['external_writes_may_have_occurred']);checked=inspect(receipt['record_root'],node=self.identity);self.assertEqual(len(checked['known_source_worktree_transitions']),6);self.assertEqual(len(checked['successful_source_writes']),2)
        shutil.rmtree(self.source);shutil.rmtree(self.tools);self.output.unlink();self.summary.unlink();real_open=os.open;record=Path(receipt['record_root'])
        def private_reads(path,flags,*args,**kwargs):
            self.assertTrue(Path(path).is_absolute() and Path(path).is_relative_to(record),path);self.assertFalse(flags&(os.O_WRONLY|os.O_RDWR|os.O_CREAT|os.O_TRUNC|os.O_APPEND));return real_open(path,flags,*args,**kwargs)
        with patch('subprocess.Popen',side_effect=AssertionError('No native replay')),patch('os.open',side_effect=private_reads),patch('lib.self_security_publication_ports.NativePublisherPaths',side_effect=AssertionError('No native append adapter')):self.assertEqual(inspect(receipt['record_root']),checked)
        with self.assertRaisesRegex(ValueError,'foreign_node'):inspect(receipt['record_root'],node={**self.identity,'node_id':'b'*32})
    def test_original_protected_ref_failure_and_strict_request_authority_mode_and_origin(self):
        receipt,result=self.generate(workflow_ref='refs/heads/feature');self.assertEqual(receipt['state'],'complete');self.assertEqual(receipt['original_exit_code'],1);self.assertEqual(result['kernel_result']['native_process_operation_count'],0);request,*_=read_record(receipt['record_root'])
        for change in ({'schema_version':True},{'export_mode':'private-candidate'},{'invocation':'arbitrary'},{'local_origin_root':None},{'subject':{**request['subject'],'repository':'a/b/c'}},{'official_acceptance':True}):
            with self.subTest(change=change),self.assertRaises(ValueError):request_valid({**request,**change})
    def test_unobserved_inputs_and_lost_completion_are_incomplete_without_retry_or_native_push(self):
        with patch.object(NativeIO,'read',side_effect=InputAdmissionError('Unobserved self-security input')):receipt,_=self.generate()
        self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code']);self.assertFalse(inspect(receipt['record_root'])['retained_declared_replay_consistent']);append=Record.append;lost=False;intents=[]
        def lose(record,row):
            nonlocal lost
            if row.get('kind')=='intent':intents.append(row)
            if row.get('kind')=='returned':lost=True
            if lost:raise OSError('Isolated self-security completion loss')
            return append(record,row)
        with patch.object(Record,'append',lose):receipt,_=self.generate()
        self.assertTrue(lost);self.assertEqual(len(intents),1);self.assertEqual(receipt['state'],'incomplete');self.assertFalse(receipt['journal_terminal_written']);self.assertIsNone(receipt['original_exit_code']);self.assertEqual(self.case.git(self.source,'branch','--show-current'),'main\n');self.assertFalse((self.tools/'calls.jsonl').exists())
    def test_actual_registered_native_CLI_inspect_and_replay_leave_node_paused(self):
        node=self.case.base/'actual-self-security-cli-node';cli=[sys.executable,'-B',str(ROOT/'scripts/axiom_v2.py')]
        def call(args):
            result=subprocess.run([*cli,*args],env={**self.environment,'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,timeout=120);self.assertEqual(result.returncode,0,(result.stdout[-3000:],result.stderr[-3000:]));return result
        call(['--instance',str(node),'init','--development','--opa',str(OPA)]);receipt=json.loads(call(['--instance',str(node),'self-security-publisher','publish','--profile',PROFILE,'--transport-profile','legacy-self-security-publisher-local-test-v1','--source-worktree',str(self.source),'--working-directory',str(ROOT),'--local-origin-root',str(self.case.base),'--repository','owner/repo','--run-id','123','--attempt','2','--workflow-ref','refs/heads/main','--provider-executable',str(self.tools/'gh'),'--output-file',str(self.output),'--summary-file',str(self.summary)]).stdout);self.assertEqual(receipt['state'],'complete');checked=json.loads(call(['--instance',str(node),'self-security-publisher','inspect','--record',receipt['record_root']]).stdout);shutil.rmtree(self.source);shutil.rmtree(self.tools);self.output.unlink();self.summary.unlink();pure=json.loads(call(['self-security-publisher','replay','--record',receipt['record_root']]).stdout);self.assertEqual(pure,checked);self.assertEqual(json.loads((node/'consumer.json').read_bytes())['mode'],'paused')
