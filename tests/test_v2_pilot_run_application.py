"""Registered fresh-run application: closed whole results, nodes and incomplete effects."""
from pathlib import Path
from datetime import datetime as ActualDatetime,timedelta
from unittest.mock import patch
from contextlib import redirect_stdout,redirect_stderr
import hashlib,io,json,os,shutil,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_live_preflight as original
import test_v2_personal_channel_programs as fixture
from test_v2_pilot_run_intake import CONTRACT,FIXTURE
from lib.pilot_run_intake_application import generate,inspect,request_valid,PROFILE
from lib.pilot_run_intake_ports import Record,read_record,encode
from lib.providers.pilot_run_temporary import NativeTemporary
from lib.providers.pilot_run_intake_io import NativeRunIO
from lib.requirement_validation_budget import InputAdmissionError
from lib.portable.runtime import source_digest
from lib.functional_parity import git_read

WRAPPER=r'''import runpy,sys,tempfile
from types import SimpleNamespace
from datetime import datetime as ActualDatetime
import lib.governance_lifecycle.live_evidence as evidence
script,at,recorded,parent=sys.argv[1:5];sys.argv=[script,*sys.argv[5:]]
class Clock:
 @staticmethod
 def now(zone):return ActualDatetime.fromisoformat(at.replace('Z','+00:00')).astimezone(zone)
class Recorded:
 @staticmethod
 def now(zone):return ActualDatetime.fromisoformat(recorded.replace('Z','+00:00')).astimezone(zone)
evidence.datetime=Clock;packet=runpy.run_path(script,run_name='whole_original_fixture');main=packet['main'];main.__globals__['datetime']=Recorded
main.__globals__['tempfile']=SimpleNamespace(TemporaryDirectory=lambda:tempfile.TemporaryDirectory(dir=parent));main()
'''
class PilotRunApplication(unittest.TestCase):
 def setUp(self):
  case=original.WholeLivePreflight();case.setUp();self.addCleanup(case.doCleanups);self.fixture=case
  self.source,self.tools,argv,self.at,_=case.selected('normal')
  for name,row in CONTRACT['files'].items():
   target=self.source/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((FIXTURE/row['fixture']).read_bytes())
  shutil.rmtree(self.source/'governance/lifecycle/live-validation')
  self.arguments=['--run-id',argv[1],'--expected-sequence','0']
  self.recorded=(ActualDatetime.fromisoformat(self.at.replace('Z','+00:00'))+timedelta(seconds=1)).isoformat().replace('+00:00','Z')
  self.instance=self.source.parent/'instance';self.instance.mkdir(mode=0o700)
  self.parent=self.source.parent/'temporary';self.parent.mkdir(mode=0o700)
  self.settings={'node_id':'a'*32,'source_revision':git_read(ROOT,'rev-parse','HEAD').decode().strip(),'runtime_source_digest':source_digest()}
 def original(self,args=None):
  return subprocess.run([sys.executable,'-B','-c',WRAPPER,str(self.source/'scripts/intake_lifecycle_pilot_run.py'),self.at,self.recorded,str(self.parent),*(self.arguments if args is None else args)],cwd=self.source,capture_output=True,timeout=180,env={**os.environ,'PYTHONPATH':str(self.source/'scripts'),'PATH':str(self.tools)+os.pathsep+os.environ['PATH'],'PYTHONDONTWRITEBYTECODE':'1','COLUMNS':'60','LINES':'24'})
 def generate(self,native=False,args=None,parent=None):
  samples=iter([self.at,self.recorded])
  class Clock:
   @staticmethod
   def now(zone):return ActualDatetime.fromisoformat(next(samples).replace('Z','+00:00')).astimezone(zone)
  with patch.dict(os.environ,{'COLUMNS':'60','LINES':'24'}),patch('lib.providers.personal_channel_transport.datetime',Clock):
   return generate({'source_worktree':str(self.source),'legacy_arguments':self.arguments if args is None else args,'transport_profile':'legacy-preflight-github-get-v1','provider_executable':str(self.tools/'gh'),'temporary_parent':str(self.parent if parent is None else parent),'write_selected_files':native},self.instance,self.settings)
 def reseal(self,root,events,value):
  previous='0'*64
  for index,event in enumerate(events):
   raw=encode({'sequence':index,'previous':previous,'value':event});(root/'events'/f'{index:08}.json').write_bytes(raw);previous=hashlib.sha256(raw).hexdigest()
  value['event_count'],value['event_tip']=len(events),previous;(root/'result.json').write_bytes(encode(value))
 def test_whole_original_native_private_receipt_outputs_and_temporaries_are_closed(self):
  before=fixture.snapshot(self.source);old=self.original();self.assertEqual(old.returncode,0,old.stderr);expected=fixture.snapshot(self.source);fixture.restore(self.source,before)
  for native in (False,True):
   with self.subTest(native=native):
    receipt,result=self.generate(native);self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],0)
    self.assertEqual(result['kernel_result']['stdout'].encode(),old.stdout);self.assertEqual(result['kernel_result']['stderr'].encode(),old.stderr)
    self.assertFalse(receipt['official_acceptance']);self.assertFalse(receipt['authority_transferred']);self.assertEqual(fixture.snapshot(self.parent),({},{}))
    checked=inspect(receipt['record_root'],node=self.settings);self.assertTrue(checked['retained_declared_replay_consistent']);self.assertFalse(checked['kernel_end_ledger_descriptors'])
    self.assertFalse(any(Path(name).is_relative_to(self.parent) for name in checked['successful_outputs']))
    if native:self.assertEqual(fixture.snapshot(self.source),expected)
    else:
     self.assertEqual(fixture.snapshot(self.source),before);_,_,_,_,blob,_=read_record(receipt['record_root']);files,dirs=map(dict,before)
     for label,value in result['private_projected_changes'].items():
      if not Path(label).is_relative_to(self.source):continue
      name=Path(label).relative_to(self.source).as_posix()
      if value['kind']=='file':files[name]=(blob(value['content']),value['mode'])
      elif value['kind']=='directory':dirs[name]=value['mode']
      elif value['kind']=='missing':files.pop(name,None);dirs.pop(name,None)
      else:self.fail(value)
     self.assertEqual((files,dirs),expected)
    fixture.restore(self.source,before)
 def test_deleted_source_provider_and_temporary_parent_replay_both_modes_rejects_foreign_node(self):
  before=fixture.snapshot(self.source);receipts=[]
  for native in (False,True):
   receipt,_=self.generate(native);self.assertEqual(receipt['state'],'complete',receipt);receipts.append(receipt);fixture.restore(self.source,before)
  shutil.rmtree(self.source);shutil.rmtree(self.tools);shutil.rmtree(self.parent)
  with patch('subprocess.Popen',side_effect=AssertionError('No provider')),patch('lib.pilot_run_intake_ports.NativeIO',side_effect=AssertionError('No selected IO')),patch('tempfile.TemporaryDirectory',side_effect=AssertionError('No temporary effect')),patch('lib.providers.personal_channel_transport.datetime',side_effect=AssertionError('No native clock')):
   for receipt in receipts:
    checked=inspect(receipt['record_root']);self.assertTrue(checked['retained_declared_replay_consistent']);self.assertFalse(checked['native_source_or_exports_repeated'])
    with self.assertRaisesRegex(ValueError,'foreign_node'):inspect(receipt['record_root'],node={**self.settings,'node_id':'b'*32})
 def test_strict_profiles_temporary_parent_and_resealed_result_authority_source_clock_orphan_reject(self):
  receipt,_=self.generate(args=['--help']);request,*_=read_record(receipt['record_root'])
  for bad in ({**request,'schema_version':True},{**request,'temporary_parent':'relative'},{**request,'temporary_parent':True},{**request,'transport_profile':'unknown'},{**request,'provider_executable':'bad\0provider'},{**request,'argv':[True]},{**request,'parser_context':{}}):
   with self.assertRaises(ValueError):request_valid(bad)
  for attack in ('stdout','authority','source','clock','temporary-parent','orphan'):
   with self.subTest(attack=attack):
    receipt,_=self.generate();root=Path(receipt['record_root']);request,source,value,events,blob,_=read_record(root)
    if attack=='stdout':value['result']['kernel_result']['stdout']='forged';self.reseal(root,events,value)
    elif attack=='authority':value['official_acceptance']=0;self.reseal(root,events,value)
    elif attack=='source':source['source_digest']='0'*64;(root/'source.json').write_bytes(encode(source))
    elif attack=='clock':
     index=next(i for i,row in enumerate(events) if row.get('kind')=='intent' and row.get('action')=='personal-capture-clock');row=events[index+1];wire=json.loads(blob(row['value']));wire['value']='2026-11-15T12:00:04Z';raw=encode(wire);sha=hashlib.sha256(raw).hexdigest();(root/'blobs'/sha).write_bytes(raw);row['value']={'sha256':sha,'bytes':len(raw)};self.reseal(root,events,value)
    elif attack=='temporary-parent':request['temporary_parent']=str(self.parent/'different');events[1]['request']=request;(root/'request.json').write_bytes(encode(request));self.reseal(root,events,value)
    else:raw=b'orphan';(root/'blobs'/hashlib.sha256(raw).hexdigest()).write_bytes(raw)
    with self.assertRaises(ValueError,msg=attack):inspect(root)
 def test_unobserved_input_and_private_state_temporary_overlap_are_incomplete(self):
  with patch.object(NativeRunIO,'read',side_effect=InputAdmissionError('Unobserved source')):receipt,_=self.generate()
  self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code']);self.assertFalse(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
  with patch('tempfile.TemporaryDirectory',side_effect=AssertionError('No state overlap creation')):receipt,_=self.generate(True,parent=self.instance)
  self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code'])
 def test_journal_loss_after_temporary_creation_retains_diagnostic_scope_without_finalizer_or_verdict(self):
  append=Record.append;create=NativeTemporary.create_resource;resources=[];blocked=False
  def remember(session,parent):
   value=create(session,parent);resources.append(value);return value
  def lost(record,row):
   nonlocal blocked
   if resources and row.get('kind')=='returned':blocked=True
   if blocked:raise OSError('Selected journal unavailable')
   return append(record,row)
  with patch.object(NativeTemporary,'create_resource',remember),patch.object(Record,'append',lost):receipt,_=self.generate(True)
  self.assertTrue(blocked);self.assertTrue(resources);self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code']);self.assertFalse(receipt['journal_terminal_written']);self.assertTrue(receipt['source_effects_may_be_partial'])
  self.assertTrue(all(not resource._finalizer.alive and Path(resource.name).is_dir() for resource in resources));self.assertTrue(any(not row.get('original_cleanup_attempted',True) for row in receipt['host_resource_release']))
 def test_original_cleanup_error_after_publication_has_complete_partial_record_and_no_print(self):
  def failed(name,**kwargs):
   (Path(name)/'capture/repository.json').unlink();raise OSError(5,'cleanup failed after publication')
  with patch.object(tempfile.TemporaryDirectory,'_rmtree',side_effect=failed):receipt,result=self.generate(True)
  self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],1);self.assertTrue(receipt['source_effects_may_be_partial']);self.assertEqual(result['kernel_result']['stdout'],'')
  self.assertEqual(len(list((self.source/'governance/lifecycle/live-validation/transactions').glob('*.json'))),1)
  self.assertTrue(inspect(receipt['record_root'],node=self.settings)['retained_declared_replay_consistent'])
  shutil.rmtree(self.source);shutil.rmtree(self.tools);shutil.rmtree(self.parent)
  with patch('tempfile.TemporaryDirectory',side_effect=AssertionError('No repeated cleanup')):self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
 def test_legacy_emission_preserves_opaque_provider_stderr_in_original_call_order(self):
  p=self.tools/'gh';text=p.read_text();i=text.index('import base64,json,sys');p.write_text(text[:i]+"import sys\nsys.stderr.buffer.write(b'opaque\\xfferror\\r\\n');sys.stderr.buffer.flush()\n"+text[i:]);p.chmod(0o700)
  receipt,result=self.generate();self.assertEqual(receipt['state'],'complete',receipt);calls=len((self.tools/'calls.jsonl').read_text().splitlines())
  from lib.personal_channel_application import emit_legacy
  a,b=io.BytesIO(),io.BytesIO();out,err=io.TextIOWrapper(a,encoding='utf-8'),io.TextIOWrapper(b,encoding='utf-8')
  with redirect_stdout(out),redirect_stderr(err):emit_legacy(result,read_record(receipt['record_root'])[4]);out.flush();err.flush()
  self.assertEqual(a.getvalue(),result['kernel_result']['stdout'].encode());self.assertEqual(b.getvalue(),b'opaque\xfferror\r\n'*calls);out.detach();err.detach()

 def test_actual_top_level_help_node_inspection_and_portable_replay(self):
  from test_portable_runtime import OPA
  node=self.source.parent/'top-level-node';cli=[sys.executable,'-B',str(ROOT/'scripts/axiom_v2.py')]
  env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','COLUMNS':'60','LINES':'24'}
  def call(args):
   value=subprocess.run([*cli,*args],capture_output=True,env=env,timeout=180);self.assertEqual(value.returncode,0,value.stderr[-3000:]);return value
  call(['--instance',str(node),'init','--development','--opa',str(OPA)])
  base=['--instance',str(node),'pilot-run-intake','generate','--profile',PROFILE,'--transport-profile','legacy-preflight-github-get-v1','--source-worktree',str(self.source),'--temporary-parent',str(self.parent),'--provider-executable','never-executed-help-provider']
  old=self.original(['--help']);self.assertEqual(old.returncode,0,old.stderr)
  legacy=call([*base,'--format','legacy','--','--help']);self.assertEqual(legacy.stdout,old.stdout);self.assertEqual(legacy.stderr,old.stderr)
  receipt=json.loads(call([*base,'--','--help']).stdout);self.assertEqual(receipt['state'],'complete');self.assertFalse(receipt['official_acceptance'])
  own=json.loads(call(['--instance',str(node),'pilot-run-intake','inspect','--record',receipt['record_root']]).stdout)
  shutil.rmtree(self.source);shutil.rmtree(self.tools);shutil.rmtree(self.parent)
  pure=json.loads(call(['pilot-run-intake','replay','--record',receipt['record_root']]).stdout);self.assertEqual(pure,own)
  self.assertTrue(json.loads((node/'instance.json').read_bytes())['development']);self.assertEqual(json.loads((node/'consumer.json').read_bytes())['mode'],'paused')
if __name__=='__main__':unittest.main(verbosity=2)
