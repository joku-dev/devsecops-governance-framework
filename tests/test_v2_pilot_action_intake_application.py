"""Registered whole action intake, strict bindings and actual source CLI."""
from pathlib import Path
from unittest.mock import patch
from contextlib import ExitStack,redirect_stdout,redirect_stderr
import copy,hashlib,io,json,os,shutil,stat,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_pilot_action_intake as original
import test_v2_personal_channel_programs as fixture
from lib.pilot_action_intake_application import generate,inspect,request_valid,run,PROFILE
from lib.pilot_action_intake_ports import Record,read_record,encode
from lib.providers.synthetic_ledger_effects import NativeLedgerEffects
from lib.portable.runtime import source_digest
from lib.functional_parity import git_read
from lib.requirement_validation_budget import InputAdmissionError

WRAPPER='''import builtins,runpy,sys,types
from datetime import datetime as ActualDatetime,timezone
import lib.governance_lifecycle.personal_probe as probe
path,collected,recorded=sys.argv[1:4];native_import=builtins.__import__
class Collect:
 @staticmethod
 def now(zone):return ActualDatetime.fromisoformat(collected.replace('Z','+00:00')).astimezone(zone)
class Recorded:
 @staticmethod
 def now(zone):return ActualDatetime.fromisoformat(recorded.replace('Z','+00:00')).astimezone(zone)
probe.datetime=Collect
def selected(name,globals=None,locals=None,fromlist=(),level=0):
 if name=='datetime' and globals and globals.get('__file__')==path:return types.SimpleNamespace(datetime=Recorded,timezone=timezone)
 return native_import(name,globals,locals,fromlist,level)
builtins.__import__=selected;sys.argv=[path,*sys.argv[4:]];runpy.run_path(path,run_name='__main__')
'''

class PilotActionIntakeApplication(unittest.TestCase):
 def setUp(self):
  case=original.WholePilotActionIntake();case.setUp();self.addCleanup(case.doCleanups);self.fixture=case
  self.source,self.tools,self.arguments=case.selected('normal');self.instance=self.source.parent/'instance';self.instance.mkdir(mode=0o700)
  self.settings={'node_id':'a'*32,'source_revision':git_read(ROOT,'rev-parse','HEAD').decode().strip(),'runtime_source_digest':source_digest()}
 def original(self,args=None,*,collected=original.COLLECT,recorded=original.RECORDED,fault=False):
  wrapper=WRAPPER
  if fault:
   code="import os,stat\nactual_sync=os.fsync\ndef selected_sync(fd):\n if stat.S_ISDIR(os.fstat(fd).st_mode):raise OSError(5,'Input/output error')\n return actual_sync(fd)\nos.fsync=selected_sync\n"
   wrapper=wrapper.replace('builtins.__import__=selected',code+'builtins.__import__=selected')
  return subprocess.run([sys.executable,'-B','-c',wrapper,str(self.source/'scripts/intake_lifecycle_pilot_action.py'),collected,recorded,*(self.arguments if args is None else args)],cwd=self.source,capture_output=True,timeout=180,env={**os.environ,'PYTHONPATH':str(self.source/'scripts'),'PATH':str(self.tools)+os.pathsep+os.environ['PATH'],'PYTHONDONTWRITEBYTECODE':'1','COLUMNS':'60','LINES':'24'})
 def generate(self,native=False,args=None,**options):
  with patch.dict(os.environ,{'COLUMNS':'60','LINES':'24'}),patch('lib.providers.personal_channel_transport.datetime',original.CollectionClock),patch('lib.providers.pilot_action_intake_clock.datetime',original.RecordedClock):
   return generate({'source_worktree':str(self.source),'legacy_arguments':self.arguments if args is None else args,'transport_profile':'legacy-personal-github-get-v1','provider_executable':str(self.tools/'gh'),'write_selected_files':native,**options},self.instance,self.settings)
 def reseal(self,root,events,value):
  previous='0'*64
  for index,event in enumerate(events):
   raw=encode({'sequence':index,'previous':previous,'value':event});(root/'events'/f'{index:08}.json').write_bytes(raw);previous=hashlib.sha256(raw).hexdigest()
  value['event_count'],value['event_tip']=len(events),previous;(root/'result.json').write_bytes(encode(value))
 def test_whole_original_native_private_append_bytes_modes_streams_and_end_descriptors(self):
  before=fixture.snapshot(self.source);old=self.original();self.assertEqual(old.returncode,0,old.stderr);expected=fixture.snapshot(self.source);fixture.restore(self.source,before)
  for native in (False,True):
   with self.subTest(native=native):
    receipt,result=self.generate(native);self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],0)
    self.assertEqual(result['kernel_result']['stdout'].encode(),old.stdout);self.assertEqual(result['kernel_result']['stderr'].encode(),old.stderr)
    self.assertFalse(receipt['official_acceptance']);self.assertFalse(receipt['authority_transferred']);self.assertTrue(all(not rows for rows in result['kernel_result']['kernel_end_ledger_descriptors'].values()))
    if native:
     self.assertEqual(fixture.snapshot(self.source),expected);self.assertEqual(len(result['kernel_result']['native_ledger_observations']),2)
     self.assertTrue(any(name.endswith('.json') for name in receipt['source_output_paths_observed']))
     self.assertTrue(all(row['remaining_descriptors']==0 for row in receipt['host_resource_release']))
    else:
     self.assertEqual(fixture.snapshot(self.source),before);_,_,_,_,blob,_=read_record(receipt['record_root']);files,dirs=map(dict,before)
     for label,value in result['private_projected_changes'].items():
      name=Path(label).relative_to(self.source).as_posix()
      if value['kind']=='file':files[name]=(blob(value['content']),value['mode'])
      elif value['kind']=='directory':dirs[name]=value['mode']
      elif value['kind']=='missing':files.pop(name,None);dirs.pop(name,None)
      else:self.fail(value)
     self.assertEqual((files,dirs),expected)
    self.assertTrue(inspect(receipt['record_root'],node=self.settings)['retained_declared_replay_consistent']);fixture.restore(self.source,before)
 def test_source_deleted_pure_replay_both_modes_and_foreign_originating_node_rejection(self):
  before=fixture.snapshot(self.source);receipts=[]
  for native in (False,True):
   receipt,_=self.generate(native);self.assertEqual(receipt['state'],'complete',receipt);receipts.append(receipt);fixture.restore(self.source,before)
  shutil.rmtree(self.source);shutil.rmtree(self.tools)
  with patch('subprocess.Popen',side_effect=AssertionError('No program')),patch('lib.pilot_action_intake_ports.NativeIO',side_effect=AssertionError('No selected IO')),patch('lib.pilot_action_intake_ports.NativeActionRecordedClock',side_effect=AssertionError('No native clock')):
   for receipt in receipts:
    value=inspect(receipt['record_root']);self.assertTrue(value['retained_declared_replay_consistent']);self.assertFalse(value['native_source_or_exports_repeated'])
    with self.assertRaisesRegex(ValueError,'foreign_node'):inspect(receipt['record_root'],node={**self.settings,'node_id':'b'*32})
 def test_original_native_directory_fsync_failure_retains_visible_action_and_partial_indication(self):
  before=fixture.snapshot(self.source);old=self.original(fault=True);self.assertEqual(old.returncode,1);expected=fixture.snapshot(self.source);fixture.restore(self.source,before)
  actual_sync=NativeLedgerEffects.sync_descriptor
  def selected(effect,descriptor):
   if stat.S_ISDIR(os.fstat(descriptor).st_mode):raise OSError(5,'Input/output error')
   return actual_sync(effect,descriptor)
  with patch.object(NativeLedgerEffects,'sync_descriptor',selected):receipt,result=self.generate(True)
  self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],1);self.assertTrue(receipt['source_effects_may_be_partial']);self.assertEqual(fixture.snapshot(self.source),expected)
  self.assertEqual(result['kernel_result']['stdout'].encode(),old.stdout);error=result['kernel_result']['kernel_exception'];self.assertTrue(old.stderr.endswith((error['type']+': '+error['message']+'\n').encode()))
  self.assertEqual(len(list((self.source/'governance/lifecycle/pilot-actions/transactions').glob('*.json'))),1);shutil.rmtree(self.source)
  self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
 def test_unobserved_input_clock_and_journal_failure_never_get_original_verdict_and_release_locks(self):
  with patch('lib.providers.pilot_action_ledgers.NativeActionIO.read',side_effect=InputAdmissionError('Unobserved request')):receipt,_=self.generate()
  self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code']);self.assertFalse(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
  with patch('lib.providers.pilot_action_intake_clock.NativeActionRecordedClock.__call__',side_effect=InputAdmissionError('Unobserved recording clock')):receipt,_=self.generate()
  self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code'])
  append=Record.append;blocked=False
  def lost(record,row):
   nonlocal blocked
   if row.get('kind')=='synthetic-ledger-effect-after' and row.get('action')=='flock':blocked=True
   if blocked:raise OSError('Selected test journal is unavailable')
   return append(record,row)
  with patch.object(Record,'append',lost):receipt,_=self.generate(True)
  self.assertTrue(blocked);self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code']);self.assertFalse(receipt['journal_terminal_written']);self.assertTrue(receipt['source_effects_may_be_partial'])
  cleanup=receipt['host_resource_release'];self.assertTrue(cleanup);self.assertGreaterEqual(sum(row['released_descriptors'] for row in cleanup),1);self.assertTrue(all(row['remaining_descriptors']==0 and not row['errors'] for row in cleanup))
 def test_strict_request_profiles_and_resealed_source_node_result_clock_authority_orphans_reject(self):
  receipt,_=self.generate(args=['--help']);request,*_=read_record(receipt['record_root'])
  for bad in ({**request,'schema_version':True},{**request,'transport_profile':'unknown'},{**request,'provider_executable':'bad\0provider'},{**request,'argv':[True]},{**request,'parser_context':{}},{**request,'resources':[{'uri':'https://invalid','label':'relative'}]}):
   with self.assertRaises(ValueError):request_valid(bad)
  for attack in ('stdout','native-state','authority','source','clock','parser','orphan'):
   with self.subTest(attack=attack):
    receipt,_=self.generate(args=['--help'] if attack=='parser' else None);root=Path(receipt['record_root']);request,source,value,events,blob,_=read_record(root)
    if attack=='stdout':value['result']['kernel_result']['stdout']='forged intake';self.reseal(root,events,value)
    elif attack=='native-state':value['result']['kernel_result']['native_ledger_observations']={'forged':{}};self.reseal(root,events,value)
    elif attack=='authority':value['official_acceptance']=0;self.reseal(root,events,value)
    elif attack=='source':source['source_digest']='0'*64;(root/'source.json').write_bytes(encode(source))
    elif attack=='clock':
     index=next(i for i,row in enumerate(events) if row.get('kind')=='intent' and row.get('action')=='pilot-action-recorded-clock');row=events[index+1];wire=json.loads(blob(row['value']));wire['value']='2026-11-15T12:00:04Z';raw=encode(wire);sha=hashlib.sha256(raw).hexdigest();(root/'blobs'/sha).write_bytes(raw);row['value']={'sha256':sha,'bytes':len(raw)};self.reseal(root,events,value)
    elif attack=='parser':request['parser_context']['width']=24;events[1]['request']=request;(root/'request.json').write_bytes(encode(request));self.reseal(root,events,value)
    else:raw=b'orphan';(root/'blobs'/hashlib.sha256(raw).hexdigest()).write_bytes(raw)
    with self.assertRaises(ValueError,msg=attack):inspect(root)
 def test_legacy_emission_preserves_ordered_opaque_GET_stderr_bytes(self):
  gh=self.tools/'gh';raw=gh.read_text();position=raw.index('import json,sys');gh.write_text(raw[:position]+"import sys\nsys.stderr.buffer.write(b'opaque\\xfferror\\r\\n');sys.stderr.buffer.flush()\n"+raw[position:]);gh.chmod(0o700)
  receipt,result=self.generate();self.assertEqual(receipt['state'],'complete',receipt)
  from lib.personal_channel_application import emit_legacy
  out_raw,err_raw=io.BytesIO(),io.BytesIO();out,err=io.TextIOWrapper(out_raw,encoding='utf-8'),io.TextIOWrapper(err_raw,encoding='utf-8')
  with redirect_stdout(out),redirect_stderr(err):emit_legacy(result,read_record(receipt['record_root'])[4]);out.flush();err.flush()
  self.assertEqual(out_raw.getvalue(),result['kernel_result']['stdout'].encode());self.assertEqual(err_raw.getvalue(),b'opaque\xfferror\r\n'*3);out.detach();err.detach()
 def test_actual_top_level_CLI_generate_help_original_bound_clocks_inspect_and_source_free_replay(self):
  from test_portable_runtime import OPA
  node=self.source.parent/'cli-node';cli=[sys.executable,'-B',str(ROOT/'scripts/axiom_v2.py')];environment={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','COLUMNS':'60','LINES':'24'}
  def call(args,expected=0):
   result=subprocess.run([*cli,*args],capture_output=True,env=environment,timeout=180);self.assertEqual(result.returncode,expected,result.stderr[-3000:]);return result
  call(['--instance',str(node),'init','--development','--opa',str(OPA)])
  base=['--instance',str(node),'pilot-action-intake','generate','--profile',PROFILE,'--transport-profile','legacy-personal-github-get-v1','--provider-executable',str(self.tools/'gh'),'--source-worktree',str(self.source)]
  old=self.original(['--help']);legacy=call([*base,'--format','legacy','--','--help']);self.assertEqual(legacy.stdout,old.stdout);self.assertEqual(legacy.stderr,old.stderr)
  before=fixture.snapshot(self.source);receipt=json.loads(call([*base,'--',*self.arguments]).stdout);self.assertEqual(receipt['state'],'complete')
  _,_,retained,events,blob,_=read_record(receipt['record_root'])
  def sampled(action):
   index=next(i for i,row in enumerate(events) if row.get('kind')=='intent' and row.get('action')==action);return json.loads(blob(events[index+1]['value']))['value']
  old=self.original(collected=sampled('personal-capture-clock'),recorded=sampled('pilot-action-recorded-clock'));self.assertEqual(old.returncode,0,old.stderr);expected=fixture.snapshot(self.source);fixture.restore(self.source,before)
  result=retained['result'];self.assertEqual(result['kernel_result']['stdout'].encode(),old.stdout);self.assertEqual(result['kernel_result']['stderr'].encode(),old.stderr)
  files,dirs=map(dict,before)
  for label,value in result['private_projected_changes'].items():
   name=Path(label).relative_to(self.source).as_posix()
   if value['kind']=='file':files[name]=(blob(value['content']),value['mode'])
   elif value['kind']=='directory':dirs[name]=value['mode']
   elif value['kind']=='missing':files.pop(name,None);dirs.pop(name,None)
   else:self.fail(value)
  self.assertEqual((files,dirs),expected);checked=json.loads(call(['--instance',str(node),'pilot-action-intake','inspect','--record',receipt['record_root']]).stdout)
  shutil.rmtree(self.source);shutil.rmtree(self.tools);replayed=json.loads(call(['pilot-action-intake','replay','--record',receipt['record_root']]).stdout);self.assertEqual(checked,replayed)
  self.assertTrue(json.loads((node/'instance.json').read_bytes())['development']);self.assertEqual(json.loads((node/'consumer.json').read_bytes())['mode'],'paused')

if __name__=='__main__':unittest.main(verbosity=2)
