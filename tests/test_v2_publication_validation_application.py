"""Whole publication precondition records, actual CLI, closed replay and authority/tampering."""
from pathlib import Path
from unittest.mock import patch
import hashlib,json,os,shutil,subprocess,sys,unittest
from contextlib import nullcontext
from datetime import datetime as ActualDatetime
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_lifecycle_ledger_validation_execution as reference
from test_v2_personal_channel_programs import snapshot
from lib.operating_publication_validation_application import generate,inspect,request_valid,PROFILE
from lib.lifecycle_ledger_validation_ports import Record,read_record,encode
from lib.providers.pilot_run_intake_io import NativeRunIO
from lib.requirement_validation_budget import InputAdmissionError
from lib.portable.runtime import source_digest
from lib.functional_parity import git_read
class PublicationValidationApplication(unittest.TestCase):
    def setUp(self):
        case=reference.WholeLifecycleValidatorExecution();case.setUp();self.addCleanup(case.doCleanups);self.reference=case;self.source=case.source
        self.instance=self.source.parent/'publication-validation-instance';self.instance.mkdir(mode=0o700)
        self.settings={'node_id':'a'*32,'source_revision':git_read(ROOT,'rev-parse','HEAD').decode().strip(),'runtime_source_digest':source_digest()}
    def generate(self,base,native=False,**extra):
        chosen=self.reference.clock
        class Clock:
            @staticmethod
            def now(zone):return ActualDatetime.fromisoformat(chosen.replace('Z','+00:00')).astimezone(zone)
        with patch('lib.providers.personal_channel_transport.datetime',Clock) if chosen else nullcontext():
            return generate({'source_worktree':str(self.source),'base_ref':base,'transport_profile':'legacy-operating-publication-readonly-v1','provider_executable':self.reference.provider,'temporary_parent':str(self.reference.temporary),'native_temporaries':native,**extra},self.instance,self.settings)
    def reseal(self,root,events,value):
        previous='0'*64
        for i,event in enumerate(events):
            raw=encode({'sequence':i,'previous':previous,'value':event});(root/'events'/f'{i:08}.json').write_bytes(raw);previous=hashlib.sha256(raw).hexdigest()
        value['event_count'],value['event_tip']=len(events),previous;(root/'result.json').write_bytes(encode(value))

    def test_complete_active_original_index_is_data_and_does_not_transfer_publishing_authority(self):
        self.reference.tools();base=self.reference.base();before=snapshot(self.source);receipt,result=self.generate(base)
        self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],0,result);self.assertTrue(receipt['original_return_value']['live_activation_approved']);self.assertFalse(receipt['official_acceptance']);self.assertFalse(receipt['authority_transferred']);self.assertFalse(receipt['publisher_git_PR_or_dispatch_executed']);self.assertEqual(snapshot(self.source),before)
        checked=inspect(receipt['record_root'],node=self.settings);self.assertEqual(checked['successful_outputs'],{});self.assertEqual(checked['successful_writes'],[]);self.assertTrue(checked['retained_declared_replay_consistent'])
    def test_actual_new_receipt_both_temporary_modes_replay_after_all_inputs_removed(self):
        base=self.reference.fresh_case('receipt');before=snapshot(self.source);receipts=[]
        for native in (False,True):
            receipt,result=self.generate(base,native=native);self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],0,result);self.assertEqual(snapshot(self.source),before);self.assertFalse(list(self.reference.temporary.iterdir()));receipts.append(receipt)
        shutil.rmtree(self.source);shutil.rmtree(self.reference.provider_tools);shutil.rmtree(self.reference.temporary)
        with patch('lib.operating_publication_validation_application.NativeIO',side_effect=AssertionError('No native owner')),patch('subprocess.Popen',side_effect=AssertionError('No Git/provider')),patch('tempfile.TemporaryDirectory',side_effect=AssertionError('No temporary effect')),patch('lib.providers.personal_channel_transport.datetime',side_effect=AssertionError('No native clock')):
            for receipt in receipts:
                self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
                with self.assertRaisesRegex(ValueError,'foreign_node'):inspect(receipt['record_root'],node={**self.settings,'node_id':'b'*32})
    def test_original_bad_base_error_is_complete_but_not_a_fabricated_success(self):
        self.reference.tools();self.reference.base();receipt,result=self.generate('0'*40);self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],1);self.assertIsNotNone(result['kernel_result']['kernel_exception']);self.assertIsNone(receipt['original_return_value']);self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
    def test_request_has_no_implicit_base_or_publishing_action_and_rejects_forged_authority(self):
        self.reference.tools();base=self.reference.base();receipt,_=self.generate(base);request,*_=read_record(receipt['record_root'])
        for bad in ({**request,'schema_version':True},{**request,'argv':['publish']},{**request,'base_ref':None},{**request,'base_ref':False},{**request,'base_ref':''},{**request,'base_ref':'-c'},{**request,'base_ref':'bad\0ref'},{**request,'profile':'other'},{**request,'transport_profile':'other'},{**request,'temporary_parent':'relative'},{**request,'provider_executable':'bad\0path'},{**request,'parser_context':{}},{**request,'official_acceptance':True}):
            with self.assertRaises(ValueError):request_valid(bad)
    def test_resealed_result_authority_base_source_parser_and_orphan_blobs_rejected(self):
        self.reference.tools();base=self.reference.base()
        for attack in ('return','authority','base','source','parser','orphan'):
            with self.subTest(attack=attack):
                receipt,_=self.generate(base);self.assertEqual(receipt['state'],'complete',receipt);root=Path(receipt['record_root']);request,source,value,events,blob,_=read_record(root)
                if attack=='return':value['result']['kernel_result']['return_value']={};self.reseal(root,events,value)
                elif attack=='authority':value['official_acceptance']=0;self.reseal(root,events,value)
                elif attack=='base':request['base_ref']='0'*40;events[1]['request']=request;(root/'request.json').write_bytes(encode(request));self.reseal(root,events,value)
                elif attack=='source':source['source_digest']='0'*64;(root/'source.json').write_bytes(encode(source))
                elif attack=='parser':request['parser_context']={};events[1]['request']=request;(root/'request.json').write_bytes(encode(request));self.reseal(root,events,value)
                else:raw=b'orphan';(root/'blobs'/hashlib.sha256(raw).hexdigest()).write_bytes(raw)
                with self.assertRaises(ValueError,msg=attack):inspect(root)
    def test_unobserved_input_and_lost_completion_remain_incomplete_without_retry(self):
        self.reference.tools();base=self.reference.base()
        with patch.object(NativeRunIO,'read',side_effect=InputAdmissionError('Unobserved publication input')):receipt,_=self.generate(base)
        self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code']);self.assertFalse(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
        append=Record.append;lost=False;intents=[]
        def unavailable(record,row):
            nonlocal lost
            if row.get('kind')=='intent':intents.append(row)
            if row.get('kind')=='returned':lost=True
            if lost:raise OSError('Explicitly unavailable completion journal')
            return append(record,row)
        with patch.object(Record,'append',unavailable):receipt,_=self.generate(base)
        self.assertTrue(lost);self.assertEqual(len(intents),1);self.assertEqual(receipt['state'],'incomplete');self.assertFalse(receipt['journal_terminal_written']);self.assertIsNone(receipt['original_exit_code'])
    def test_actual_top_level_generate_inspect_and_source_free_replay_on_paused_node(self):
        from test_portable_runtime import OPA
        self.reference.tools();base=self.reference.base();node=self.source.parent/'actual-publication-node';cli=[sys.executable,'-B',str(ROOT/'scripts/axiom_v2.py')]
        def call(args):
            p=subprocess.run([*cli,*args],capture_output=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=300);self.assertEqual(p.returncode,0,p.stderr[-4000:]);return p
        call(['--instance',str(node),'init','--development','--opa',str(OPA)])
        receipt=json.loads(call(['--instance',str(node),'publication-validation','generate','--profile',PROFILE,'--transport-profile','legacy-operating-publication-readonly-v1','--source-worktree',str(self.source),'--provider-executable',self.reference.provider,'--base-ref',base]).stdout);self.assertEqual(receipt['state'],'complete');self.assertEqual(receipt['original_exit_code'],0);self.assertFalse(receipt['publisher_git_PR_or_dispatch_executed'])
        checked=json.loads(call(['--instance',str(node),'publication-validation','inspect','--record',receipt['record_root']]).stdout);shutil.rmtree(self.source);shutil.rmtree(self.reference.provider_tools)
        pure=json.loads(call(['publication-validation','replay','--record',receipt['record_root']]).stdout);self.assertEqual(pure,checked);self.assertEqual(json.loads((node/'consumer.json').read_bytes())['mode'],'paused')
if __name__=='__main__':unittest.main(verbosity=2)
