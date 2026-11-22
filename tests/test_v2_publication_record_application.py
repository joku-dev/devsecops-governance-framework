"""Real private application/CLI records, foreign-node rejection and incomplete outcomes."""
from pathlib import Path
from unittest.mock import patch
import hashlib,json,os,shutil,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_operational_publisher_native as reference
from lib.operational_publication_application import generate,inspect,request_valid,PROFILE
from lib.operational_publication_ports import Record,read_record
from lib.providers.operational_publication_record import RecordingPublisherProcess
from lib.portable.runtime import source_digest
from lib.requirement_validation_budget import InputAdmissionError
class WholePublisherApplication(unittest.TestCase):
    def setUp(self):
        self.case=reference.WholeOperationalPublisherNative();self.case.setUp();self.addCleanup(self.case.doCleanups);self.root,self.origin,self.tools,self.output,self.summary,self.env=self.case.fixture('application')
        self.node=self.case.base/'publisher-node';self.node.mkdir(mode=0o700)
        self.settings={'node_id':'a'*32,'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT).decode().strip(),'runtime_source_digest':source_digest()}
        self.options={'source_worktree':str(self.root),'working_directory':str(ROOT),'scope':'portfolio','repository':reference.REPOSITORY,'run_id':reference.RUN,'attempt':reference.ATTEMPT,
            'workflow_ref':'refs/heads/main','profile':PROFILE,'transport_profile':'legacy-operational-publisher-local-test-v1','local_origin_root':str(self.case.base),'provider_executable':str(self.tools/'gh'),'output_file':str(self.output),'summary_file':str(self.summary)}
    def candidate(self):(self.root/'generated/reports/portfolio-onboarding-status.json').write_text('{"explicit":"application proposal"}\n')
    def generate(self,**extra):return generate({**self.options,**extra},self.node,self.settings,native_environment=self.env)
    def test_actual_native_proposal_and_inspection_bind_node_with_no_operating_authority(self):
        self.candidate();receipt,result=self.generate();self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],0,result);checked=inspect(receipt['record_root'],node=self.settings)
        self.assertTrue(checked['external_writes_may_have_occurred']);self.assertFalse(checked['authority_transferred']);self.assertFalse(checked['official_acceptance']);self.assertFalse(checked['external_completion_independently_proven']);self.assertFalse(checked['publisher_service_activated']);self.assertEqual(len(checked['pipeline_append_observations']),6)
        with self.assertRaisesRegex(ValueError,'foreign_node'):inspect(receipt['record_root'],node={**self.settings,'node_id':'b'*32})
    def test_no_change_does_not_claim_a_native_write(self):
        receipt,result=self.generate();self.assertEqual(receipt['state'],'complete',receipt);self.assertFalse(receipt['external_writes_may_have_occurred']);self.assertFalse(inspect(receipt['record_root'])['external_writes_may_have_occurred'])
    def test_original_PR_failure_is_complete_record_with_retained_original_failure(self):
        self.candidate();(self.tools/'mode').write_text('fail-pr');receipt,result=self.generate();self.assertEqual(receipt['state'],'complete');self.assertEqual(receipt['exit_code'],1);checked=inspect(receipt['record_root']);self.assertEqual(checked['kernel_exception']['type'],'CalledProcessError');self.assertTrue(checked['external_writes_may_have_occurred']);self.assertEqual(checked['pipeline_append_observations'],[])
    def test_source_tools_and_native_temporary_inputs_absent_during_complete_replay(self):
        self.candidate();receipt,_=self.generate();before=inspect(receipt['record_root']);shutil.rmtree(self.root);shutil.rmtree(self.tools);self.output.unlink();self.summary.unlink()
        with patch('lib.operational_publication_application.NativeIO',side_effect=AssertionError('No native owner')),patch('subprocess.Popen',side_effect=AssertionError('No Git/POST')),patch('tempfile.TemporaryDirectory',side_effect=AssertionError('No temporary')):
            self.assertEqual(inspect(receipt['record_root']),before)
    def test_closed_request_rejects_unknown_authority_profiles_environment_and_subject(self):
        receipt,_=self.generate();request,*_=read_record(receipt['record_root'])
        bads=({**request,'schema_version':True},{**request,'published':True},{**request,'transport_profile':'unselected'},
            {**request,'transport_profile':'legacy-operational-publisher-native-v1'},{**request,'subject':{**request['subject'],'repository':'other'}},
            {**request,'environment':{**request['environment'],'SECRET_TOKEN':'never-retained'}},{**request,'invocation':'shell'},
            {**request,'parser_context':{}},{**request,'provider_executable':'bad\0path'},{**request,'temporary_parent':'relative'})
        for bad in bads:
            with self.subTest(keys=list(bad)),self.assertRaises(ValueError):request_valid(bad)
    def test_unobserved_process_and_lost_completion_have_no_fabricated_original_exit_or_retry(self):
        self.candidate()
        with patch.object(RecordingPublisherProcess,'run',side_effect=InputAdmissionError('Unobserved native process')):receipt,_=self.generate()
        self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code']);self.assertFalse(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
        original=Record.append;lost=False;intents=[]
        def unavailable(record,row):
            nonlocal lost
            if row.get('kind')=='intent':intents.append(row)
            if row.get('kind')=='returned':lost=True
            if lost:raise OSError('Explicitly unavailable completion journal')
            return original(record,row)
        with patch.object(Record,'append',unavailable):receipt,_=self.generate()
        self.assertTrue(lost);self.assertEqual(len(intents),1);self.assertEqual(receipt['state'],'incomplete');self.assertFalse(receipt['journal_terminal_written']);self.assertIsNone(receipt['original_exit_code'])
    def test_actual_top_level_publish_inspect_and_source_free_replay_on_paused_node(self):
        from test_portable_runtime import OPA
        self.candidate();node=self.case.base/'actual-publisher-node';cli=[sys.executable,'-B',str(ROOT/'scripts/axiom_v2.py')]
        def call(args,expected=0):
            p=subprocess.run([*cli,*args],env=self.env,capture_output=True,timeout=120);self.assertEqual(p.returncode,expected,p.stderr[-4000:]);return p
        call(['--instance',str(node),'init','--development','--opa',str(OPA)])
        args=['--instance',str(node),'operational-publisher','publish','--profile',PROFILE,'--transport-profile','legacy-operational-publisher-local-test-v1','--local-origin-root',str(self.case.base),'--source-worktree',str(self.root),'--working-directory',str(ROOT),'--scope','portfolio','--repository',reference.REPOSITORY,'--run-id',reference.RUN,'--attempt',reference.ATTEMPT,'--workflow-ref','refs/heads/main','--provider-executable',str(self.tools/'gh'),'--output-file',str(self.output),'--summary-file',str(self.summary)]
        receipt=json.loads(call(args).stdout);self.assertEqual(receipt['state'],'complete');checked=json.loads(call(['--instance',str(node),'operational-publisher','inspect','--record',receipt['record_root']]).stdout)
        shutil.rmtree(self.root);shutil.rmtree(self.tools);self.output.unlink();self.summary.unlink()
        pure=json.loads(call(['operational-publisher','replay','--record',receipt['record_root']]).stdout);self.assertEqual(pure,checked);self.assertEqual(json.loads((node/'consumer.json').read_bytes())['mode'],'paused')
    def test_selected_private_state_program_is_not_executed_or_reported_as_an_original_verdict(self):
        self.candidate();marker=self.case.base/'private-program-must-not-run';tool=self.node/'unselected-provider';tool.write_text('#!'+sys.executable+'\nfrom pathlib import Path\nPath('+repr(str(marker))+').write_text("forbidden")\n');tool.chmod(0o700)
        receipt,result=self.generate(provider_executable=str(tool));self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code']);self.assertFalse(marker.exists())
    def test_product_source_node_and_selected_source_cannot_be_CI_append_targets(self):
        self.candidate()
        for output in (ROOT/'README.md',self.node/'instance.json',self.root/'README.md'):
            with self.subTest(output=output),patch.object(RecordingPublisherProcess,'run',side_effect=AssertionError('No native command before overlap rejection')):
                with self.assertRaisesRegex(ValueError,'pipeline_output_source_or_instance_overlap'):self.generate(output_file=str(output))
        self.assertFalse((self.tools/'calls.jsonl').exists());self.assertEqual(self.case.git(self.root,'branch','--show-current'),'main\n')
