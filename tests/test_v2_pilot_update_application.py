"""Public pilot runner records: original effects, closed replay and paused CLI."""
from pathlib import Path
from unittest.mock import patch
from datetime import datetime as ActualDatetime
import hashlib,json,os,shutil,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_pilot_update_execution as reference
from test_v2_personal_channel_programs import snapshot
from lib.pilot_update_application import generate,inspect,request_valid,PROFILE
from lib.pilot_update_ports import Record,read_record,encode,NativeUpdateIO
from lib.requirement_validation_budget import InputAdmissionError
from lib.portable.runtime import source_digest
from lib.functional_parity import git_read

class PilotUpdateApplication(unittest.TestCase):
 def setUp(self):
  case=reference.WholePilotUpdateExecution();case.setUp();self.addCleanup(case.doCleanups);self.case=case;self.source=case.source
  self.instance=self.source.parent/'pilot-update-instance';self.instance.mkdir(mode=0o700)
  self.settings={'node_id':'a'*32,'source_revision':git_read(ROOT,'rev-parse','HEAD').decode().strip(),'runtime_source_digest':source_digest()}
 def generate(self,argv=(),native=False,**extra):
  chosen=self.case.at
  class Clock:
   @staticmethod
   def now(zone):return ActualDatetime.fromisoformat(chosen.replace('Z','+00:00')).astimezone(zone)
  options={'source_worktree':str(self.source),'legacy_arguments':list(argv),'transport_profile':'legacy-pilot-update-readonly-v1','provider_executable':self.case.reference.provider,'temporary_parent':str(self.case.reference.temporary),'write_selected_files':native,**extra}
  with patch('lib.providers.personal_channel_transport.datetime',Clock),patch('lib.providers.pilot_action_intake_clock.datetime',Clock):return generate(options,self.instance,self.settings)
 def reseal(self,root,events,value):
  previous='0'*64
  for i,event in enumerate(events):
   raw=encode({'sequence':i,'previous':previous,'value':event});(root/'events'/f'{i:08}.json').write_bytes(raw);previous=hashlib.sha256(raw).hexdigest()
  value['event_count'],value['event_tip']=len(events),previous;(root/'result.json').write_bytes(encode(value))
 def test_private_refresh_keeps_source_and_all_original_report_projections(self):
  before=snapshot(self.source);receipt,result=self.generate(['--operation','refresh']);self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],0,result);self.assertIsNone(receipt['original_return_value']);self.assertFalse(receipt['source_export_requested']);self.assertEqual(snapshot(self.source),before);self.assertFalse(receipt['official_acceptance']);self.assertFalse(receipt['authority_transferred']);self.assertFalse(receipt['publication_included']);self.assertFalse(receipt['node_operating_activation_included'])
  checked=inspect(receipt['record_root'],node=self.settings);self.assertTrue(checked['retained_declared_replay_consistent']);self.assertTrue(checked['private_projected_changes']);self.assertEqual(checked['verification_scope'],'whole_original_pilot_update_run_and_operating_capture_generate')
 def test_original_helper_and_parser_failures_are_complete_records_not_fabricated_passes(self):
  for argv,extra,code in ((['--help'],{},0),([],{},2),(['--operation','invalid'],{},2),(['--operation','observe'],{},1),((),{'helper':'generate'},0),((),{'invocation':{'method':'run','arguments':{'operation':'unknown'}}},1)):
   with self.subTest(argv=argv,extra=extra):
    receipt,result=self.generate(argv,**extra);self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],code,result);self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
 def test_native_committed_action_observations_bind_both_ledgers_and_replay_without_source(self):
  relative=self.case.prepare_action();receipt,result=self.generate(['--operation','action','--request-path',relative],native=True);self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],0,result);checked=inspect(receipt['record_root'],node=self.settings);self.assertTrue(receipt['source_export_requested']);self.assertTrue(checked['native_ledger_observations']);self.assertEqual(set(checked['native_ledger_observations']),{str(self.source/'governance/lifecycle/live-validation'),str(self.source/'governance/lifecycle/pilot-actions')});self.assertTrue(receipt['source_output_paths_observed']);self.assertFalse(any(checked['kernel_end_ledger_descriptors'].values()));shutil.rmtree(self.source);shutil.rmtree(self.case.reference.provider_tools);shutil.rmtree(self.case.reference.temporary)
  with patch('subprocess.Popen',side_effect=AssertionError('No Git/provider')),patch('tempfile.TemporaryDirectory',side_effect=AssertionError('No native temporary')),patch('lib.providers.pilot_action_intake_clock.datetime',side_effect=AssertionError('No clock')):self.assertEqual(inspect(receipt['record_root']),checked)
  with self.assertRaisesRegex(ValueError,'foreign_node'):inspect(receipt['record_root'],node={**self.settings,'node_id':'b'*32})
 def test_native_partial_report_failure_remains_original_and_observable(self):
  target=self.source/'generated/reports/governance-lifecycle-live.md';target.unlink();target.mkdir(mode=0o700);receipt,result=self.generate(native=True,helper='generate');self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],1,result);self.assertTrue(receipt['source_effects_may_be_partial']);self.assertEqual(result['kernel_result']['kernel_exception']['type'],'IsADirectoryError');self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
 def test_strict_request_rejects_parser_invocation_source_and_authority_forgery(self):
  receipt,_=self.generate(['--help']);request,*_=read_record(receipt['record_root'])
  for bad in ({**request,'schema_version':True},{**request,'argv':True},{**request,'profile':'other'},{**request,'transport_profile':'other'},{**request,'parser_context':{}},{**request,'invocation':False},{**request,'invocation':{'method':'capture','arguments':{'authority':True}}},{**request,'invocation':{'method':'run','arguments':{'operation':False}}},{**request,'invocation':{'method':'generate','arguments':{}}},{**request,'official_acceptance':True}):
   with self.assertRaises(ValueError,msg=str(bad)):request_valid(bad)
 def test_resealed_return_authority_invocation_source_and_orphan_blobs_rejected(self):
  for attack in ('return','authority','invocation','source','orphan'):
   with self.subTest(attack=attack):
    receipt,_=self.generate(['--help']);root=Path(receipt['record_root']);request,source,value,events,blob,_=read_record(root)
    if attack=='return':value['result']['kernel_result']['return_value']=999;self.reseal(root,events,value)
    elif attack=='authority':value['official_acceptance']=0;self.reseal(root,events,value)
    elif attack=='invocation':request['invocation']=False;events[1]['request']=request;(root/'request.json').write_bytes(encode(request));self.reseal(root,events,value)
    elif attack=='source':source['source_digest']='0'*64;(root/'source.json').write_bytes(encode(source))
    else:raw=b'orphan';(root/'blobs'/hashlib.sha256(raw).hexdigest()).write_bytes(raw)
    with self.assertRaises(ValueError,msg=attack):inspect(root)
 def test_unobserved_input_and_lost_completion_keep_incomplete_without_retry(self):
  with patch.object(NativeUpdateIO,'read',side_effect=InputAdmissionError('Unobserved pilot input')):receipt,_=self.generate(['--operation','refresh'])
  self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code']);self.assertFalse(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
  append=Record.append;lost=False;intents=[]
  def unavailable(record,row):
   nonlocal lost
   if row.get('kind')=='intent':intents.append(row)
   if row.get('kind')=='returned':lost=True
   if lost:raise OSError('Explicit journal completion loss')
   return append(record,row)
  with patch.object(Record,'append',unavailable):receipt,_=self.generate(['--operation','refresh'])
  self.assertTrue(lost);self.assertEqual(len(intents),1);self.assertEqual(receipt['state'],'incomplete');self.assertFalse(receipt['journal_terminal_written']);self.assertIsNone(receipt['original_exit_code'])
 def test_actual_public_generate_inspect_source_free_replay_and_paused_node(self):
  from test_portable_runtime import OPA
  node=self.source.parent/'actual-pilot-update-node';cli=[sys.executable,'-B',str(ROOT/'scripts/axiom_v2.py')]
  def call(args):
   p=subprocess.run([*cli,*args],capture_output=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},timeout=300);self.assertEqual(p.returncode,0,p.stderr[-4000:]);return p
  call(['--instance',str(node),'init','--development','--opa',str(OPA)])
  receipt=json.loads(call(['--instance',str(node),'pilot-update','generate','--profile',PROFILE,'--transport-profile','legacy-pilot-update-readonly-v1','--source-worktree',str(self.source),'--provider-executable',self.case.reference.provider,'--helper','generate']).stdout);self.assertEqual(receipt['state'],'complete');self.assertEqual(receipt['original_exit_code'],0)
  checked=json.loads(call(['--instance',str(node),'pilot-update','inspect','--record',receipt['record_root']]).stdout);shutil.rmtree(self.source);pure=json.loads(call(['pilot-update','replay','--record',receipt['record_root']]).stdout);self.assertEqual(pure,checked);self.assertEqual(json.loads((node/'consumer.json').read_bytes())['mode'],'paused')
if __name__=='__main__':unittest.main(verbosity=2)
