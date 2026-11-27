"""Registered consumer records, strict node/tool scope and actual paused CLI."""
from pathlib import Path
import copy,hashlib,json,os,shutil,subprocess,sys,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_consumer_lifecycle_program as reference
from lib.consumer_lifecycle_application import generate,inspect,request_valid,PROFILE
from lib.consumer_lifecycle_ports import Record,read_record,NativeIO
from lib.portable.runtime import source_digest
from lib.functional_parity import git_read
from lib.requirement_validation_budget import InputAdmissionError
from test_portable_runtime import OPA


class ConsumerApplication(unittest.TestCase):
    def setUp(self):
        self.fixture=reference.WholeConsumerProgram();self.fixture.setUp();self.addCleanup(self.fixture.doCleanups);self.source=self.fixture.root;self.node=self.fixture.parent/'consumer-node';self.node.mkdir(mode=0o700);self.temporary=self.fixture.parent/'consumer-temporaries';self.temporary.mkdir(mode=0o700)
        self.identity={'node_id':'a'*32,'source_revision':git_read(ROOT,'rev-parse','HEAD').decode().strip(),'runtime_source_digest':source_digest()};self.settings={**self.identity,'opa':str(OPA),'opa_sha256':hashlib.sha256(OPA.read_bytes()).hexdigest()}
    def generate(self,args=(),**extra):
        return generate({'source_worktree':str(self.source),'legacy_arguments':list(args),'transport_profile':'legacy-consumer-readonly-v1','provider_executable':str(self.fixture.tools/'gh'),'temporary_parent':str(self.temporary),**extra},self.node,self.settings)
    def test_complete_validate_record_retains_source_history_without_transferring_operating_authority(self):
        before=reference.snapshot(self.source);receipt,result=self.generate(['--operation','validate']);self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],0,result);self.assertEqual(reference.snapshot(self.source),before);self.assertFalse(receipt['official_acceptance']);self.assertFalse(receipt['authority_transferred']);self.assertFalse(receipt['publication_included']);checked=inspect(receipt['record_root'],node=self.identity);self.assertTrue(checked['retained_declared_replay_consistent'])
        shutil.rmtree(self.source);shutil.rmtree(self.fixture.tools);shutil.rmtree(self.temporary)
        with patch('subprocess.Popen',side_effect=AssertionError('No process')),patch('lib.consumer_lifecycle_ports.NativeIO',side_effect=AssertionError('No source inputs')):self.assertEqual(inspect(receipt['record_root']),checked)
        with self.assertRaisesRegex(ValueError,'foreign_node'):inspect(receipt['record_root'],node={**self.identity,'node_id':'b'*32})
    def test_strict_tool_parser_resource_authority_and_invocation_requests_are_not_inferred(self):
        receipt,_=self.generate(['--help']);request,*_=read_record(receipt['record_root'])
        for change in ({'schema_version':True},{'argv':False},{'approved_opa_hashes':[['not-a-hash']]},{'approved_opa_hashes':['0'*64]},{'opa_tool':'relative/opa'},{'opa_workarea':'/a/../b'},{'official_acceptance':True},{'invocation':{'method':'arbitrary','arguments':{}}}):
            with self.subTest(change=change),self.assertRaises(ValueError):request_valid({**request,**change})
    def test_unobserved_input_and_journal_completion_loss_never_become_original_verdicts(self):
        with patch.object(NativeIO,'probe',side_effect=InputAdmissionError('unobserved consumer model')):receipt,_=self.generate(['--operation','validate'])
        self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code']);self.assertFalse(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
        append=Record.append;lost=False;intents=[]
        def lose(record,row):
            nonlocal lost
            if row.get('kind')=='intent':intents.append(row)
            if row.get('kind')=='returned':lost=True
            if lost:raise OSError('isolated journal completion loss')
            return append(record,row)
        with patch.object(Record,'append',lose):receipt,_=self.generate(['--operation','validate'])
        self.assertTrue(lost);self.assertEqual(len(intents),1);self.assertEqual(receipt['state'],'incomplete');self.assertFalse(receipt['journal_terminal_written']);self.assertIsNone(receipt['original_exit_code'])
    def test_real_cli_generates_inspects_and_replays_whole_validator_on_a_paused_node(self):
        node=self.fixture.parent/'actual-CLI-node';cli=[sys.executable,'-B',str(ROOT/'scripts/axiom_v2.py')]
        def call(args):
            p=subprocess.run([*cli,*args],capture_output=True,timeout=300,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'});self.assertEqual(p.returncode,0,(p.stdout[-3000:],p.stderr[-3000:]));return p
        call(['--instance',str(node),'init','--development','--opa',str(OPA)])
        receipt=json.loads(call(['--instance',str(node),'consumer-lifecycle','generate','--profile',PROFILE,'--transport-profile','legacy-consumer-readonly-v1','--source-worktree',str(self.source),'--temporary-parent',str(self.temporary),'--','--operation','validate']).stdout);self.assertEqual(receipt['state'],'complete');self.assertFalse(receipt['official_acceptance']);checked=json.loads(call(['--instance',str(node),'consumer-lifecycle','inspect','--record',receipt['record_root']]).stdout);shutil.rmtree(self.source);shutil.rmtree(self.fixture.tools);shutil.rmtree(self.temporary);pure=json.loads(call(['consumer-lifecycle','replay','--record',receipt['record_root']]).stdout);self.assertEqual(pure,checked);self.assertEqual(json.loads((node/'consumer.json').read_bytes())['mode'],'paused')
