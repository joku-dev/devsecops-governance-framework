"""Registered typed publisher records, full native path and actual paused CLI."""
from pathlib import Path
from unittest.mock import patch
import hashlib,json,os,shutil,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_typed_publication_native as reference
from lib.typed_publication_application import generate,inspect,request_valid,PROFILE
from lib.typed_publication_ports import Record,NativeIO,read_record
from lib.portable.runtime import source_digest
from lib.functional_parity import git_read
from lib.requirement_validation_budget import InputAdmissionError
from test_portable_runtime import OPA


class TypedPublisherApplication(unittest.TestCase):
    def setUp(self):
        self.typed=reference.WholeTypedPublisherNative();self.typed.setUp();self.addCleanup(self.typed.doCleanups);self.case=self.typed.case;self.source,self.origin,self.tools,self.output,self.summary,self.environment=self.case.fixture('candidate');self.typed.candidate(self.source);self.node=self.case.base/'typed-node';self.node.mkdir(mode=0o700);self.temporary=self.case.base/'temporaries';self.temporary.mkdir(mode=0o700);self.identity={'node_id':'a'*32,'source_revision':git_read(ROOT,'rev-parse','HEAD').decode().strip(),'runtime_source_digest':source_digest()};self.settings={**self.identity,'opa':str(OPA),'opa_sha256':hashlib.sha256(OPA.read_bytes()).hexdigest()}
    def options(self,**extra):return {'profile':PROFILE,'transport_profile':'legacy-typed-evidence-publisher-local-test-v1','source_worktree':str(self.source),'working_directory':str(ROOT),'local_origin_root':str(self.case.base),'scope':'typed-evidence','repository':'example/project','run_id':'42','attempt':'1','workflow_ref':'refs/heads/main','provider_executable':str(self.tools/'gh'),'output_file':str(self.output),'summary_file':str(self.summary),'temporary_parent':str(self.temporary),**extra}
    def generate(self,**extra):return generate(self.options(**extra),self.node,self.settings,native_environment=self.environment)
    def test_whole_registered_native_typed_publication_and_closed_replay_with_source_removed(self):
        receipt,result=self.generate();self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],0,result);self.assertFalse(receipt['official_acceptance']);self.assertFalse(receipt['authority_transferred']);self.assertTrue(receipt['external_writes_may_have_occurred']);self.assertNotEqual(self.case.git(self.source,'rev-parse','HEAD').strip(),self.case.initial);checked=inspect(receipt['record_root'],node=self.identity);self.assertEqual(checked['configured_publisher_scope_rules']['ledgers'][-3:],list(reference.ADDITIONAL_LEDGERS))
        shutil.rmtree(self.source);shutil.rmtree(self.tools);shutil.rmtree(self.temporary);self.output.unlink();self.summary.unlink()
        with patch('subprocess.Popen',side_effect=AssertionError('No native replay process')),patch('lib.typed_publication_ports.NativePublisherPaths',side_effect=AssertionError('No native output adapter')):self.assertEqual(inspect(receipt['record_root']),checked)
        with self.assertRaisesRegex(ValueError,'foreign_node'):inspect(receipt['record_root'],node={**self.identity,'node_id':'b'*32})
    def test_original_configure_helper_uses_an_owned_namespace_without_any_Git_or_POST(self):
        receipt,result=self.generate(invocation='configure');self.assertEqual(receipt['state'],'complete');self.assertEqual(result['kernel_result']['native_process_operation_count'],0);checked=inspect(receipt['record_root']);self.assertFalse(checked['external_writes_may_have_occurred']);self.assertEqual(self.case.git(self.source,'branch','--show-current'),'main\n')
        request,*_=read_record(receipt['record_root'])
        for change in ({'schema_version':True},{'transport_profile':'unknown'},{'invocation':'arbitrary'},{'local_origin_root':None},{'subject':{**request['subject'],'scope':'arbitrary'}},{'official_acceptance':True}):
            with self.subTest(change=change),self.assertRaises(ValueError):request_valid({**request,**change})
    def test_unobserved_process_and_lost_completion_never_become_success_or_automatic_retry(self):
        with patch.object(NativeIO,'perform',side_effect=InputAdmissionError('unobserved typed process')):receipt,_=self.generate()
        self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code']);self.assertFalse(inspect(receipt['record_root'])['retained_declared_replay_consistent']);append=Record.append;lost=False;intents=[]
        def lose(record,row):
            nonlocal lost
            if row.get('kind')=='intent':intents.append(row)
            if row.get('kind')=='returned':lost=True
            if lost:raise OSError('Isolated typed journal loss')
            return append(record,row)
        with patch.object(Record,'append',lose):receipt,_=self.generate()
        self.assertTrue(lost);self.assertEqual(len(intents),1);self.assertEqual(receipt['state'],'incomplete');self.assertFalse(receipt['journal_terminal_written']);self.assertIsNone(receipt['original_exit_code']);self.assertEqual(self.case.git(self.source,'branch','--show-current'),'main\n')
    def test_actual_CLI_native_publish_inspect_and_source_free_replay_leave_node_paused(self):
        node=self.case.base/'actual-typed-cli-node';cli=[sys.executable,'-B',str(ROOT/'scripts/axiom_v2.py')]
        def call(args):
            result=subprocess.run([*cli,*args],env={**self.environment,'PYTHONDONTWRITEBYTECODE':'1'},capture_output=True,timeout=120);self.assertEqual(result.returncode,0,(result.stdout[-3000:],result.stderr[-3000:]));return result
        call(['--instance',str(node),'init','--development','--opa',str(OPA)])
        receipt=json.loads(call(['--instance',str(node),'typed-publisher','publish','--profile',PROFILE,'--transport-profile','legacy-typed-evidence-publisher-local-test-v1','--local-origin-root',str(self.case.base),'--source-worktree',str(self.source),'--working-directory',str(ROOT),'--scope','typed-evidence','--repository','example/project','--run-id','42','--attempt','1','--workflow-ref','refs/heads/main','--provider-executable',str(self.tools/'gh'),'--output-file',str(self.output),'--summary-file',str(self.summary),'--temporary-parent',str(self.temporary)]).stdout);self.assertEqual(receipt['state'],'complete');checked=json.loads(call(['--instance',str(node),'typed-publisher','inspect','--record',receipt['record_root']]).stdout);shutil.rmtree(self.source);shutil.rmtree(self.tools);shutil.rmtree(self.temporary);self.output.unlink();self.summary.unlink();pure=json.loads(call(['typed-publisher','replay','--record',receipt['record_root']]).stdout);self.assertEqual(pure,checked);self.assertEqual(json.loads((node/'consumer.json').read_bytes())['mode'],'paused')
