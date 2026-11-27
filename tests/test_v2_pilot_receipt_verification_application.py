"""Closed API recordings for independently refetched original receipt verification."""
from pathlib import Path
from datetime import datetime as ActualDatetime
from unittest.mock import patch
import hashlib,json,os,shutil,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_pilot_receipt_verification as reference
from test_v2_personal_channel_programs import snapshot
from lib.pilot_receipt_verification_application import generate,inspect,request_valid,PROFILE
from lib.pilot_receipt_verification_ports import Record,read_record,encode
from lib.providers.pilot_run_temporary import NativeTemporary
from lib.providers.pilot_run_intake_io import NativeRunIO
from lib.requirement_validation_budget import InputAdmissionError
from lib.portable.runtime import source_digest
from lib.functional_parity import git_read

class ReceiptVerificationApplication(unittest.TestCase):
 def setUp(self):
  case=reference.WholePilotReceiptVerification();case.setUp();self.addCleanup(case.doCleanups);self.reference=case;self.fixture=case.fixture
  self.base,self.at,self.now=case.prepare('normal');self.source=self.fixture.source;self.tools=self.fixture.tools;self.parent=self.fixture.parent;self.instance=self.source.parent/'verification-instance';self.instance.mkdir(mode=0o700)
  self.settings={'node_id':'a'*32,'source_revision':git_read(ROOT,'rev-parse','HEAD').decode().strip(),'runtime_source_digest':source_digest()}
 def generate(self,native=False,**extra):
  samples=iter([self.at,self.now])
  class Clock:
   @staticmethod
   def now(zone):return ActualDatetime.fromisoformat(next(samples).replace('Z','+00:00')).astimezone(zone)
  opts={'source_worktree':str(self.source),'base_ref':self.base,'transport_profile':'legacy-preflight-receipt-git-v1','provider_executable':str(self.tools/'gh'),'temporary_parent':str(self.parent),'native_capture':native,**extra}
  with patch('lib.providers.personal_channel_transport.datetime',Clock):return generate(opts,self.instance,self.settings)
 def reseal(self,root,events,value):
  previous='0'*64
  for i,event in enumerate(events):
   raw=encode({'sequence':i,'previous':previous,'value':event});(root/'events'/f'{i:08}.json').write_bytes(raw);previous=hashlib.sha256(raw).hexdigest()
  value['event_count'],value['event_tip']=len(events),previous;(root/'result.json').write_bytes(encode(value))
 def test_whole_original_API_return_GET_order_unchanged_source_and_closed_both_modes(self):
  before=snapshot(self.source);old=subprocess.run([sys.executable,'-B','-c',reference.WRAPPER,self.at,self.now,self.base],cwd=self.source,capture_output=True,env={**os.environ,'PYTHONPATH':str(self.source/'scripts'),'PATH':str(self.tools)+os.pathsep+os.environ['PATH'],'PYTHONDONTWRITEBYTECODE':'1'},timeout=180);self.assertEqual(old.returncode,0,old.stderr)
  expected_calls=(self.tools/'calls.jsonl').read_bytes();self.assertEqual(snapshot(self.source),before)
  for native in (False,True):
   with self.subTest(native=native):
    (self.tools/'calls.jsonl').unlink();receipt,result=self.generate(native);self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_return_value'],json.loads(old.stdout));self.assertEqual(receipt['original_exit_code'],0)
    self.assertEqual((self.tools/'calls.jsonl').read_bytes(),expected_calls);self.assertEqual(snapshot(self.source),before);self.assertEqual(snapshot(self.parent),({},{}));self.assertFalse(receipt['source_export_requested']);self.assertFalse(receipt['official_acceptance']);self.assertFalse(receipt['authority_transferred']);self.assertEqual(receipt['verification_scope'],'whole_original_verify_new_receipts_helper');self.assertFalse(receipt['structural_ledger_validation_included'])
    checked=inspect(receipt['record_root'],node=self.settings);self.assertTrue(checked['retained_declared_replay_consistent']);self.assertEqual(checked['original_return_value'],1);self.assertEqual(checked['verification_scope'],receipt['verification_scope']);self.assertFalse(checked['structural_ledger_validation_included'])
 def test_source_provider_temp_and_git_removed_pure_replay_both_modes_foreign_node_rejected(self):
  receipts=[self.generate(native)[0] for native in (False,True)]
  for receipt in receipts:self.assertEqual(receipt['state'],'complete',receipt)
  shutil.rmtree(self.source);shutil.rmtree(self.tools);shutil.rmtree(self.parent)
  with patch('lib.pilot_receipt_verification_ports.NativeIO',side_effect=AssertionError('No selected IO')),patch('subprocess.Popen',side_effect=AssertionError('No Git or provider')),patch('tempfile.TemporaryDirectory',side_effect=AssertionError('No temporary effect')),patch('lib.providers.personal_channel_transport.datetime',side_effect=AssertionError('No native clock')):
   for receipt in receipts:
    self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
    with self.assertRaisesRegex(ValueError,'foreign_node'):inspect(receipt['record_root'],node={**self.settings,'node_id':'b'*32})
 def test_strict_base_transport_request_shape_and_native_temporary_private_state_overlap(self):
  receipt,_=self.generate();request,*_=read_record(receipt['record_root'])
  for bad in ({**request,'schema_version':True},{**request,'base_ref':True},{**request,'base_ref':'-other'},{**request,'base_ref':''},{**request,'transport_profile':'unknown'},{**request,'temporary_parent':'relative'},{**request,'provider_executable':'bad\0path'},{**request,'argv':[]}):
   with self.assertRaises(ValueError):request_valid(bad)
  with patch('tempfile.TemporaryDirectory',side_effect=AssertionError('No private-state temporary')):receipt,_=self.generate(True,temporary_parent=str(self.instance))
  self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_return_value']);self.assertIsNone(receipt['original_exit_code'])
 def test_resealed_result_authority_base_source_clock_and_orphan_blobs_rejected(self):
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
 def test_original_missing_Git_base_is_complete_diagnostic_with_no_invented_verdict(self):
  receipt,result=self.generate(base_ref='missing-original-base');self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],1);self.assertIsNone(receipt['original_return_value']);self.assertEqual(result['kernel_result']['kernel_exception']['type'],'CalledProcessError');self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
 def test_unobserved_source_input_is_incomplete_without_original_count_or_exit(self):
  with patch.object(NativeRunIO,'read',side_effect=InputAdmissionError('Unobserved selected source')):receipt,_=self.generate()
  self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code']);self.assertIsNone(receipt['original_return_value']);self.assertFalse(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
 def test_journal_loss_after_native_scope_creation_retains_scope_no_verdict_no_retry(self):
  append=Record.append;create=NativeTemporary.create_resource;resources=[];blocked=False
  def remember(session,parent):value=create(session,parent);resources.append(value);return value
  def lost(record,row):
   nonlocal blocked
   if resources and row.get('kind')=='returned':blocked=True
   if blocked:raise OSError('Chosen journal unavailable')
   return append(record,row)
  with patch.object(NativeTemporary,'create_resource',remember),patch.object(Record,'append',lost):receipt,_=self.generate(True)
  self.assertTrue(resources);self.assertTrue(blocked);self.assertEqual(receipt['state'],'incomplete');self.assertFalse(receipt['journal_terminal_written']);self.assertIsNone(receipt['original_exit_code']);self.assertTrue(all(not r._finalizer.alive and Path(r.name).is_dir() for r in resources))
 def test_actual_top_level_already_accepted_base_cli_inspect_and_source_free_replay(self):
  from test_portable_runtime import OPA
  subprocess.run(['git','-C',str(self.source),'add','--all'],check=True,capture_output=True)
  subprocess.run(['git','-C',str(self.source),'-c','user.name=AXIOM isolated fixture','-c','user.email=fixture@invalid.example','-c','commit.gpgsign=false','-c','core.hooksPath=/dev/null','commit','--quiet','-m','Already accepted receipt fixture'],check=True,capture_output=True)
  base=subprocess.check_output(['git','-C',str(self.source),'rev-parse','HEAD']).decode().strip();node=self.source.parent/'top-level-verification-node';cli=[sys.executable,'-B',str(ROOT/'scripts/axiom_v2.py')]
  def call(args):
   p=subprocess.run([*cli,*args],capture_output=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=180);self.assertEqual(p.returncode,0,p.stderr[-4000:]);return p
  call(['--instance',str(node),'init','--development','--opa',str(OPA)])
  receipt=json.loads(call(['--instance',str(node),'pilot-receipt-verification','generate','--profile',PROFILE,'--transport-profile','legacy-preflight-receipt-git-v1','--source-worktree',str(self.source),'--base-ref',base,'--provider-executable','never-called-for-accepted-base','--temporary-parent',str(self.parent)]).stdout);self.assertEqual(receipt['state'],'complete');self.assertEqual(receipt['original_return_value'],0)
  checked=json.loads(call(['--instance',str(node),'pilot-receipt-verification','inspect','--record',receipt['record_root']]).stdout);shutil.rmtree(self.source);shutil.rmtree(self.tools);shutil.rmtree(self.parent)
  pure=json.loads(call(['pilot-receipt-verification','replay','--record',receipt['record_root']]).stdout);self.assertEqual(pure,checked);self.assertEqual(json.loads((node/'consumer.json').read_bytes())['mode'],'paused')
if __name__=='__main__':unittest.main(verbosity=2)
