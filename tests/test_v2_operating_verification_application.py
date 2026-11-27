"""Closed action-verification records, original diagnostics and registered CLI."""
from pathlib import Path
from datetime import datetime as ActualDatetime
from unittest.mock import patch
import hashlib,json,os,shutil,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_operating_verification as reference
from test_v2_personal_channel_programs import snapshot
from lib.operating_verification_application import generate,inspect,request_valid,PROFILE
from lib.operating_verification_ports import Record,read_record,encode
from lib.providers.pilot_run_intake_io import NativeRunIO
from lib.requirement_validation_budget import InputAdmissionError
from lib.portable.runtime import source_digest
from lib.functional_parity import git_read

class OperatingVerificationApplication(unittest.TestCase):
    def setUp(self):
        case=reference.WholeOperatingVerification();case.setUp();self.addCleanup(case.doCleanups);self.reference=case
        self.source,self.tools,self.base=case.selected();self.instance=self.source.parent/'action-check-instance';self.instance.mkdir(mode=0o700)
        self.settings={'node_id':'a'*32,'source_revision':git_read(ROOT,'rev-parse','HEAD').decode().strip(),'runtime_source_digest':source_digest()}

    def generate(self,native=False,**extra):
        class Clock:
            @staticmethod
            def now(zone):return ActualDatetime.fromisoformat(reference.AT.replace('Z','+00:00')).astimezone(zone)
        options={'source_worktree':str(self.source),'base_ref':self.base,'transport_profile':'legacy-personal-operating-git-v1','provider_executable':str(self.tools/'gh'),'native_capture':native,**extra}
        with patch('lib.providers.personal_channel_transport.datetime',Clock):return generate(options,self.instance,self.settings)

    def reseal(self,root,events,value):
        previous='0'*64
        for i,event in enumerate(events):
            raw=encode({'sequence':i,'previous':previous,'value':event});(root/'events'/f'{i:08}.json').write_bytes(raw);previous=hashlib.sha256(raw).hexdigest()
        value['event_count'],value['event_tip']=len(events),previous;(root/'result.json').write_bytes(encode(value))

    def test_whole_original_API_return_raw_GET_order_and_source_unchanged_both_modes(self):
        before=snapshot(self.source);calls=self.tools/'calls.jsonl'
        env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(self.source/'scripts'),'PATH':str(self.tools)+os.pathsep+os.environ['PATH']}
        old=subprocess.run([sys.executable,'-B','-c',reference.WRAPPER,self.base,reference.AT,'null','verify-new-captures'],cwd=self.source,env=env,capture_output=True,timeout=180);self.assertEqual(old.returncode,0,old.stderr[-3000:]);queries=calls.read_bytes()
        for native in (False,True):
            with self.subTest(native=native):
                calls.unlink();receipt,result=self.generate(native);self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_return_value'],json.loads(old.stdout));self.assertEqual(receipt['original_return_value'],1)
                self.assertFalse(receipt['source_export_requested']);self.assertFalse(receipt['official_acceptance']);self.assertFalse(receipt['structural_ledger_validation_included']);self.assertEqual(receipt['verification_scope'],'whole_original_operating_verify-new-captures_helper')
                self.assertEqual(snapshot(self.source),before);self.assertEqual(calls.read_bytes(),queries)
                _,_,_,_,blob,_=read_record(receipt['record_root']);kernel=result['kernel_result'];raw=b''.join(blob(p['blob']) if 'blob' in p else p['text'].encode() for p in kernel['stderr_parts']);self.assertEqual(raw,old.stderr)
                self.assertTrue(inspect(receipt['record_root'],node=self.settings)['retained_declared_replay_consistent'])

    def test_source_provider_and_Git_removed_pure_replay_both_modes_foreign_node_rejected(self):
        receipts=[]
        for native in (False,True):
            receipt,_=self.generate(native);self.assertEqual(receipt['state'],'complete',receipt);receipts.append(receipt)
        shutil.rmtree(self.source);shutil.rmtree(self.tools)
        with patch('lib.operating_verification_ports.NativeIO',side_effect=AssertionError('No selected source')),patch('subprocess.Popen',side_effect=AssertionError('No Git/provider')),patch('lib.providers.personal_channel_transport.datetime',side_effect=AssertionError('No clock')):
            for receipt in receipts:
                value=inspect(receipt['record_root']);self.assertTrue(value['retained_declared_replay_consistent']);self.assertFalse(value['native_source_or_exports_repeated'])
                with self.assertRaisesRegex(ValueError,'foreign_node'):inspect(receipt['record_root'],node={**self.settings,'node_id':'b'*32})

    def test_strict_request_shape_base_checked_time_provider_and_profile(self):
        receipt,_=self.generate();request,*_=read_record(receipt['record_root'])
        for bad in ({**request,'schema_version':True},{**request,'base_ref':True},{**request,'base_ref':'-other'},{**request,'base_ref':''},{**request,'checked_at':True},{**request,'checked_at':'bad\0time'},{**request,'transport_profile':'other'},{**request,'provider_executable':'bad\0path'},{**request,'argv':[]},{**request,'temporary_parent':'extra'},{**request,'operation':'unknown'}):
            with self.assertRaises(ValueError):request_valid(bad)
        request_valid({**request,'checked_at':''})
        with self.assertRaises(ValueError):request_valid({**request,'operation':'collect'})
        with self.assertRaises(ValueError):request_valid({**request,'operation':'verify-provider','base_ref':None,'checked_at':reference.AT})

    def test_resealed_count_authority_base_source_clock_and_extra_blob_rejected(self):
        for attack in ('return','authority','base','source','clock','orphan'):
            with self.subTest(attack=attack):
                receipt,_=self.generate();self.assertEqual(receipt['state'],'complete',receipt);root=Path(receipt['record_root']);request,source,value,events,blob,_=read_record(root)
                if attack=='return':value['result']['kernel_result']['return_value']=99;self.reseal(root,events,value)
                elif attack=='authority':value['official_acceptance']=0;self.reseal(root,events,value)
                elif attack=='base':request['base_ref']='different';events[1]['request']=request;(root/'request.json').write_bytes(encode(request));self.reseal(root,events,value)
                elif attack=='source':source['source_digest']='0'*64;(root/'source.json').write_bytes(encode(source))
                elif attack=='clock':
                    i=next(i for i,e in enumerate(events) if e.get('kind')=='intent' and e.get('action')=='personal-capture-clock');row=events[i+1];wire=json.loads(blob(row['value']));wire['value']='2099-01-01T00:00:00Z';raw=encode(wire);sha=hashlib.sha256(raw).hexdigest();(root/'blobs'/sha).write_bytes(raw);row['value']={'sha256':sha,'bytes':len(raw)};self.reseal(root,events,value)
                else:raw=b'orphan';(root/'blobs'/hashlib.sha256(raw).hexdigest()).write_bytes(raw)
                with self.assertRaises(ValueError,msg=attack):inspect(root)

    def test_original_missing_base_complete_diagnostic_preserves_no_count(self):
        receipt,result=self.generate(base_ref='missing-original-base');self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],1);self.assertIsNone(receipt['original_return_value']);self.assertEqual(result['kernel_result']['kernel_exception']['type'],'CalledProcessError');self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])

    def test_unobserved_input_is_incomplete_without_original_count_or_exit(self):
        with patch.object(NativeRunIO,'read',side_effect=InputAdmissionError('Unobserved selected input')):receipt,_=self.generate()
        self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code']);self.assertIsNone(receipt['original_return_value']);self.assertFalse(inspect(receipt['record_root'])['retained_declared_replay_consistent'])

    def test_journal_loss_after_actual_provider_request_stops_without_verdict_or_retry(self):
        before=snapshot(self.source);calls=self.tools/'calls.jsonl';append=Record.append;blocked=False
        def lost(record,row):
            nonlocal blocked
            if calls.exists() and row.get('kind')=='returned':blocked=True
            if blocked:raise OSError('Chosen journal unavailable')
            return append(record,row)
        with patch.object(Record,'append',lost):receipt,_=self.generate(True)
        self.assertTrue(blocked);self.assertEqual(len(calls.read_text().splitlines()),1);self.assertEqual(snapshot(self.source),before);self.assertEqual(receipt['state'],'incomplete');self.assertFalse(receipt['journal_terminal_written']);self.assertIsNone(receipt['original_exit_code']);self.assertIsNone(receipt['original_return_value'])

    def test_actual_top_level_accepted_base_CLI_inspect_and_source_free_replay(self):
        from test_portable_runtime import OPA
        base=reference.commit(self.source);node=self.source.parent/'actual-action-check-node';cli=[sys.executable,'-B',str(ROOT/'scripts/axiom_v2.py')]
        def call(args):
            p=subprocess.run([*cli,*args],capture_output=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=180);self.assertEqual(p.returncode,0,p.stderr[-4000:]);return p
        call(['--instance',str(node),'init','--development','--opa',str(OPA)])
        receipt=json.loads(call(['--instance',str(node),'operating-verification','generate','--profile',PROFILE,'--transport-profile','legacy-personal-operating-git-v1','--source-worktree',str(self.source),'--base-ref',base,'--provider-executable','never-called-for-accepted-base']).stdout);self.assertEqual(receipt['state'],'complete');self.assertEqual(receipt['original_return_value'],0)
        checked=json.loads(call(['--instance',str(node),'operating-verification','inspect','--record',receipt['record_root']]).stdout);shutil.rmtree(self.source);shutil.rmtree(self.tools)
        pure=json.loads(call(['operating-verification','replay','--record',receipt['record_root']]).stdout);self.assertEqual(pure,checked);self.assertEqual(json.loads((node/'consumer.json').read_bytes())['mode'],'paused')

    def test_whole_collect_and_verify_provider_records_have_original_snapshot_but_no_node_authority(self):
        for operation in ('collect','verify-provider'):
            for native in (False,True):
                with self.subTest(operation=operation,native=native):
                    receipt,result=self.generate(native,operation=operation,base_ref=None)
                    self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],0)
                    self.assertIsInstance(receipt['original_return_value'],dict)
                    self.assertEqual(receipt['original_return_value']['result']['status'],'confirmed')
                    self.assertFalse(receipt['official_acceptance']);self.assertFalse(receipt['authority_transferred']);self.assertFalse(receipt['source_export_requested'])
                    self.assertEqual(receipt['verification_scope'],'whole_original_operating_'+operation+'_helper')
                    checked=inspect(receipt['record_root'],node=self.settings);self.assertEqual(checked['original_return_value'],receipt['original_return_value']);self.assertTrue(checked['retained_declared_replay_consistent'])
