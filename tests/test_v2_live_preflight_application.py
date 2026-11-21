"""Registered exact-source diagnostic capture, strict receipt binding and inert replay."""
from pathlib import Path
from datetime import datetime as ActualDatetime
from unittest.mock import patch
from contextlib import redirect_stdout,redirect_stderr
import copy,hashlib,io,json,os,shutil,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_live_preflight as original
import test_v2_personal_channel_programs as fixture
from lib.lifecycle_preflight_application import generate,inspect,request_valid,PROFILE
from lib.lifecycle_preflight_ports import Record,read_record,encode
from lib.providers.personal_channel_exclusive import NativeExclusive
from lib.providers.lifecycle_preflight_io import NativePreflightIO
from lib.requirement_validation_budget import InputAdmissionError
from lib.portable.runtime import source_digest
from lib.functional_parity import git_read

WRAPPER='''import runpy,sys
from datetime import datetime as ActualDatetime
import lib.governance_lifecycle.live_evidence as preflight
path,at=sys.argv[1:3]
class Clock:
 @staticmethod
 def now(zone):return ActualDatetime.fromisoformat(at.replace('Z','+00:00')).astimezone(zone)
preflight.datetime=Clock;sys.argv=[path,*sys.argv[3:]];runpy.run_path(path,run_name='__main__')
'''
class LivePreflightApplication(unittest.TestCase):
 def setUp(self):
  case=original.WholeLivePreflight();case.setUp();self.addCleanup(case.doCleanups);self.fixture=case
  self.source,self.tools,self.arguments,self.at,self.destination=case.selected('normal')
  self.instance=self.source.parent/'instance';self.instance.mkdir(mode=0o700)
  self.settings={'node_id':'a'*32,'source_revision':git_read(ROOT,'rev-parse','HEAD').decode().strip(),'runtime_source_digest':source_digest()}
 def original(self,args=None,at=None):
  return subprocess.run([sys.executable,'-B','-c',WRAPPER,str(self.source/'scripts/preflight_lifecycle_live_evidence.py'),self.at if at is None else at,*(self.arguments if args is None else args)],cwd=self.source,capture_output=True,timeout=180,env={**os.environ,'PYTHONPATH':str(self.source/'scripts'),'PATH':str(self.tools)+os.pathsep+os.environ['PATH'],'PYTHONDONTWRITEBYTECODE':'1','COLUMNS':'60','LINES':'24'})
 def generate(self,native=False,args=None):
  at=self.at
  class Clock:
   @staticmethod
   def now(zone):return ActualDatetime.fromisoformat(at.replace('Z','+00:00')).astimezone(zone)
  with patch.dict(os.environ,{'COLUMNS':'60','LINES':'24'}),patch('lib.providers.personal_channel_transport.datetime',Clock):
   return generate({'source_worktree':str(self.source),'legacy_arguments':self.arguments if args is None else args,'transport_profile':'legacy-preflight-github-get-v1','provider_executable':str(self.tools/'gh'),'write_selected_files':native},self.instance,self.settings)
 def reseal(self,root,events,value):
  previous='0'*64
  for index,event in enumerate(events):
   raw=encode({'sequence':index,'previous':previous,'value':event});(root/'events'/f'{index:08}.json').write_bytes(raw);previous=hashlib.sha256(raw).hexdigest()
  value['event_count'],value['event_tip']=len(events),previous;(root/'result.json').write_bytes(encode(value))
 def test_whole_original_native_private_stdout_files_modes_and_manifest_last(self):
  before=fixture.snapshot(self.source);old=self.original();self.assertEqual(old.returncode,0,old.stderr);expected=fixture.snapshot(self.source);fixture.restore(self.source,before)
  for native in (False,True):
   with self.subTest(native=native):
    receipt,result=self.generate(native);self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],0)
    kernel=result['kernel_result'];self.assertEqual(kernel['stdout'].encode(),old.stdout);self.assertEqual(kernel['stderr'].encode(),old.stderr)
    self.assertFalse(receipt['official_acceptance']);self.assertFalse(receipt['authority_transferred']);self.assertEqual(kernel['external_native_path_observations'],{})
    checked=inspect(receipt['record_root'],node=self.settings);self.assertTrue(checked['retained_declared_replay_consistent']);self.assertEqual(list(checked['successful_writes'])[-1]['path'],str(self.destination/'preflight.json'))
    if native:self.assertEqual(fixture.snapshot(self.source),expected)
    else:
     self.assertEqual(fixture.snapshot(self.source),before);_,_,_,_,blob,_=read_record(receipt['record_root']);files,dirs=map(dict,before)
     for label,value in result['private_projected_changes'].items():
      name=Path(label).relative_to(self.source).as_posix()
      if value['kind']=='file':files[name]=(blob(value['content']),value['mode'])
      elif value['kind']=='directory':dirs[name]=value['mode']
      elif value['kind']=='missing':files.pop(name,None);dirs.pop(name,None)
      else:self.fail(value)
     self.assertEqual((files,dirs),expected)
    fixture.restore(self.source,before)
 def test_deleted_source_and_program_replay_both_modes_and_reject_foreign_node(self):
  before=fixture.snapshot(self.source);receipts=[]
  for native in (False,True):
   receipt,_=self.generate(native);self.assertEqual(receipt['state'],'complete',receipt);receipts.append(receipt);fixture.restore(self.source,before)
  shutil.rmtree(self.source);shutil.rmtree(self.tools)
  with patch('subprocess.Popen',side_effect=AssertionError('No program')),patch('lib.lifecycle_preflight_ports.NativeIO',side_effect=AssertionError('No selected IO')),patch('lib.providers.personal_channel_transport.datetime',side_effect=AssertionError('No native clock')):
   for receipt in receipts:
    value=inspect(receipt['record_root']);self.assertTrue(value['retained_declared_replay_consistent']);self.assertFalse(value['native_source_or_exports_repeated'])
    with self.assertRaisesRegex(ValueError,'foreign_node'):inspect(receipt['record_root'],node={**self.settings,'node_id':'b'*32})
 def test_strict_profiles_and_resealed_result_external_state_authority_source_clock_parser_orphans_reject(self):
  receipt,_=self.generate(args=['--help']);request,*_=read_record(receipt['record_root'])
  for bad in ({**request,'schema_version':True},{**request,'transport_profile':'unknown'},{**request,'provider_executable':'bad\0provider'},{**request,'argv':[True]},{**request,'parser_context':{}},{**request,'resources':[{'uri':'https://invalid','label':'relative'}]}):
   with self.assertRaises(ValueError):request_valid(bad)
  for attack in ('stdout','external-state','authority','source','clock','parser','orphan'):
   with self.subTest(attack=attack):
    receipt,_=self.generate(args=['--help'] if attack=='parser' else None);root=Path(receipt['record_root']);request,source,value,events,blob,_=read_record(root)
    if attack=='stdout':value['result']['kernel_result']['stdout']='forged';self.reseal(root,events,value)
    elif attack=='external-state':value['result']['kernel_result']['external_native_path_observations']={'forged':{}};self.reseal(root,events,value)
    elif attack=='authority':value['official_acceptance']=0;self.reseal(root,events,value)
    elif attack=='source':source['source_digest']='0'*64;(root/'source.json').write_bytes(encode(source))
    elif attack=='clock':
     index=next(i for i,row in enumerate(events) if row.get('kind')=='intent' and row.get('action')=='personal-capture-clock');row=events[index+1];old_ref=row['value'];wire=json.loads(blob(old_ref));wire['value']='2026-11-15T12:00:04Z';raw=encode(wire);sha=hashlib.sha256(raw).hexdigest();(root/'blobs'/sha).write_bytes(raw);row['value']={'sha256':sha,'bytes':len(raw)};self.reseal(root,events,value)
    elif attack=='parser':request['parser_context']['width']=24;events[1]['request']=request;(root/'request.json').write_bytes(encode(request));self.reseal(root,events,value)
    else:raw=b'orphan';(root/'blobs'/hashlib.sha256(raw).hexdigest()).write_bytes(raw)
    with self.assertRaises(ValueError,msg=attack):inspect(root)
 def test_unobserved_input_clock_and_journal_failure_are_incomplete_and_release_owned_stream(self):
  with patch.object(NativePreflightIO,'read',side_effect=InputAdmissionError('Unobserved input')):receipt,_=self.generate()
  self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code']);self.assertFalse(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
  with patch('lib.providers.lifecycle_preflight_protocol.NativePreflightTransport.clock',side_effect=InputAdmissionError('Unobserved clock')):receipt,_=self.generate()
  self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code'])
  append=Record.append;blocked=False;opened=[];open_stream=NativeExclusive.open_stream
  def remember(session):
   value=open_stream(session);opened.append(session);return value
  def lost(record,row):
   nonlocal blocked
   if row.get('kind')=='returned' and opened:blocked=True
   if blocked:raise OSError('Selected journal unavailable')
   return append(record,row)
  with patch.object(Record,'append',lost),patch.object(NativeExclusive,'open_stream',remember):receipt,_=self.generate(True)
  self.assertTrue(blocked);self.assertTrue(opened);self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code']);self.assertFalse(receipt['journal_terminal_written']);self.assertTrue(receipt['source_effects_may_be_partial'])
  self.assertTrue(all(session.resource.closed and not session.descriptor_owned() for session in opened))
 def test_legacy_emission_keeps_opaque_GET_stderr_bytes_in_original_query_order(self):
  p=self.tools/'gh';s=p.read_text();i=s.index('import base64,json,sys');p.write_text(s[:i]+"import sys\nsys.stderr.buffer.write(b'opaque\\xfferror\\r\\n');sys.stderr.buffer.flush()\n"+s[i:]);p.chmod(0o700)
  receipt,result=self.generate();self.assertEqual(receipt['state'],'complete',receipt)
  calls=len((self.tools/'calls.jsonl').read_text().splitlines())
  from lib.personal_channel_application import emit_legacy
  a,c=io.BytesIO(),io.BytesIO();out,err=io.TextIOWrapper(a,encoding='utf-8'),io.TextIOWrapper(c,encoding='utf-8')
  with redirect_stdout(out),redirect_stderr(err):emit_legacy(result,read_record(receipt['record_root'])[4]);out.flush();err.flush()
  self.assertEqual(a.getvalue(),result['kernel_result']['stdout'].encode());self.assertEqual(c.getvalue(),b'opaque\xfferror\r\n'*calls);out.detach();err.detach()
 def test_externally_created_entry_is_observed_without_claiming_ownership_or_completing_bundle(self):
  real=NativePreflightIO.make_exclusive_directory
  def compete(port,anchor,path,mode):
   subprocess.run([sys.executable,'-B','-c','from pathlib import Path;import sys;Path(sys.argv[1]).mkdir()',path],check=True)
   return real(port,anchor,path,mode)
  with patch.object(NativePreflightIO,'make_exclusive_directory',compete):receipt,result=self.generate(True)
  self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],1);self.assertEqual(result['kernel_result']['kernel_exception']['type'],'FileExistsError')
  self.assertEqual(receipt['external_paths_observed'],[str(self.destination)]);self.assertNotIn(str(self.destination),receipt['source_output_paths_observed']);self.assertFalse((self.destination/'preflight.json').exists())
  shutil.rmtree(self.source);shutil.rmtree(self.tools);self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
 def test_original_native_partial_seven_byte_write_and_receipt_partial_hint(self):
  injection='''import io
native_open=io.open
class Partial:
 def __init__(self,stream):self.stream=stream
 def __getattr__(self,name):return getattr(self.stream,name)
 def __enter__(self):return self
 def __exit__(self,*args):return self.stream.__exit__(*args)
 def write(self,raw):
  self.stream.write(raw[:7]);self.stream.flush();raise OSError(28,'No space left on device')
def partial(file,mode='r',*args,**kwargs):
 stream=native_open(file,mode,*args,**kwargs)
 return Partial(stream) if mode=='xb' and str(file)==TARGET else stream
io.open=partial
'''.replace('TARGET',repr(str(self.destination/'repository.json')))
  wrapper=WRAPPER.replace('preflight.datetime=Clock;',injection+'preflight.datetime=Clock;');before=fixture.snapshot(self.source)
  old=subprocess.run([sys.executable,'-B','-c',wrapper,str(self.source/'scripts/preflight_lifecycle_live_evidence.py'),self.at,*self.arguments],cwd=self.source,capture_output=True,timeout=180,env={**os.environ,'PYTHONPATH':str(self.source/'scripts'),'PATH':str(self.tools)+os.pathsep+os.environ['PATH'],'PYTHONDONTWRITEBYTECODE':'1'})
  self.assertEqual(old.returncode,1);expected=fixture.snapshot(self.source);fixture.restore(self.source,before)
  native_open=NativeExclusive.open_stream
  class Partial:
   def __init__(self,stream):self.stream=stream
   def __getattr__(self,name):return getattr(self.stream,name)
   def write(self,raw):
    self.stream.write(raw[:7]);self.stream.flush();raise OSError(28,'No space left on device')
  def selected(session):
   value=native_open(session)
   return Partial(value) if session.path==str(self.destination/'repository.json') else value
  with patch.object(NativeExclusive,'open_stream',selected):receipt,result=self.generate(True)
  self.assertEqual(receipt['state'],'complete',receipt);self.assertEqual(receipt['original_exit_code'],1);self.assertTrue(receipt['source_effects_may_be_partial']);self.assertEqual(fixture.snapshot(self.source),expected)
  self.assertEqual(len((self.destination/'repository.json').read_bytes()),7);self.assertFalse((self.destination/'preflight.json').exists())
  error=result['kernel_result']['kernel_exception'];self.assertTrue(old.stderr.endswith((error['type']+': '+error['message']+'\n').encode()))
  shutil.rmtree(self.source);self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
 def test_actual_top_level_help_capture_sampled_clock_inspect_and_source_deleted_replay(self):
  # Explicit fake provider metadata; no real freshness/authentication assertion.
  # A distant expiry permits the real native clock; original verification is
  # unmodified and its sampled value is supplied back to the full V1 oracle.
  import base64
  response_path=self.tools/'responses.json';responses=json.loads(response_path.read_bytes())
  for endpoint,values in responses.items():
   for index,encoded in enumerate(values):
    try:value=json.loads(base64.b64decode(encoded,validate=True))
    except (UnicodeError,ValueError):continue
    changed=False
    if type(value) is dict and 'expires_at' in value:value['expires_at']='2099-01-01T00:00:00Z';changed=True
    if type(value) is dict and type(value.get('artifacts')) is list:
     for artifact in value['artifacts']:
      if 'expires_at' in artifact:artifact['expires_at']='2099-01-01T00:00:00Z';changed=True
    if changed:values[index]=base64.b64encode(json.dumps(value).encode()).decode()
  response_path.write_text(json.dumps(responses))
  from test_portable_runtime import OPA
  node=self.source.parent/'cli-node';cli=[sys.executable,'-B',str(ROOT/'scripts/axiom_v2.py')];environment={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','COLUMNS':'60','LINES':'24'}
  def call(args,expected=0):
   result=subprocess.run([*cli,*args],capture_output=True,env=environment,timeout=180);self.assertEqual(result.returncode,expected,result.stderr[-3000:]);return result
  call(['--instance',str(node),'init','--development','--opa',str(OPA)])
  base=['--instance',str(node),'live-preflight','generate','--profile',PROFILE,'--transport-profile','legacy-preflight-github-get-v1','--provider-executable',str(self.tools/'gh'),'--source-worktree',str(self.source)]
  old=self.original(['--help']);legacy=call([*base,'--format','legacy','--','--help']);self.assertEqual(legacy.stdout,old.stdout);self.assertEqual(legacy.stderr,old.stderr)
  before=fixture.snapshot(self.source);receipt=json.loads(call([*base,'--',*self.arguments]).stdout);self.assertEqual(receipt['state'],'complete')
  _,_,retained,events,blob,_=read_record(receipt['record_root']);index=next(i for i,row in enumerate(events) if row.get('kind')=='intent' and row.get('action')=='personal-capture-clock');at=json.loads(blob(events[index+1]['value']))['value']
  old=self.original(at=at);self.assertEqual(old.returncode,0,old.stderr);expected=fixture.snapshot(self.source);fixture.restore(self.source,before)
  result=retained['result'];self.assertEqual(result['kernel_result']['stdout'].encode(),old.stdout);self.assertEqual(result['kernel_result']['stderr'].encode(),old.stderr)
  files,dirs=map(dict,before)
  for label,value in result['private_projected_changes'].items():
   name=Path(label).relative_to(self.source).as_posix()
   if value['kind']=='file':files[name]=(blob(value['content']),value['mode'])
   elif value['kind']=='directory':dirs[name]=value['mode']
   elif value['kind']=='missing':files.pop(name,None);dirs.pop(name,None)
   else:self.fail(value)
  self.assertEqual((files,dirs),expected);checked=json.loads(call(['--instance',str(node),'live-preflight','inspect','--record',receipt['record_root']]).stdout)
  shutil.rmtree(self.source);shutil.rmtree(self.tools);replayed=json.loads(call(['live-preflight','replay','--record',receipt['record_root']]).stdout);self.assertEqual(checked,replayed)
  self.assertTrue(json.loads((node/'instance.json').read_bytes())['development']);self.assertEqual(json.loads((node/'consumer.json').read_bytes())['mode'],'paused')
if __name__=='__main__':unittest.main(verbosity=2)
