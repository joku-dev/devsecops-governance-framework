"""Whole original pilot runner versus shared model/native store and inert replay."""
from pathlib import Path
from datetime import datetime as ActualDatetime
from unittest.mock import patch
from contextlib import nullcontext
import hashlib,json,os,shutil,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from jsonschema import Draft202012Validator
import test_v2_lifecycle_ledger_validation_execution as fixture
from test_v2_personal_channel_programs import snapshot,restore
from lib.pilot_update_ports import NativeUpdateIO,ReplayUpdateIO,execute
from lib.pilot_action_intake_ports import transaction_name
from lib.providers.synthetic_lifecycle_storage import Record,read_record
from lib.providers.retained_argparse import capture_context

WRAPPER='''import json,os,runpy,sys
from datetime import datetime as ActualDatetime
os.umask(0o077)
script,at,invocation=sys.argv[1:4];sys.argv=[script,*sys.argv[4:]]
import lib.governance_lifecycle.live_evidence as evidence
import lib.governance_lifecycle.live_admission as admission
import lib.governance_lifecycle.personal_probe as personal
class Clock:
 @staticmethod
 def now(zone):return ActualDatetime.fromisoformat(at.replace('Z','+00:00')).astimezone(zone)
evidence.datetime=admission.datetime=personal.datetime=Clock
packet=runpy.run_path(script,run_name='immutable_pilot_update');packet['run'].__globals__['datetime']=Clock
value=error=signal=None
try:
 if invocation=='main':exec(compile(__import__('ast').Module(body=next(n for n in __import__('ast').parse(open(script).read()).body if isinstance(n,__import__('ast').If)).body,type_ignores=[]),script,'exec'),packet['run'].__globals__)
 else:
  spec=json.loads(invocation)
  if spec['method']=='run':value=packet['run'](**spec['arguments'])
  else:
   import lib.governance_lifecycle.operating_acceptance as op
   value=getattr(op,spec['method'])()
except SystemExit as e:signal={'type':'SystemExit','value':e.code}
except Exception as e:error={'type':type(e).__name__,'message':str(e)}
print('\\nAXIOM_ORIGINAL_RESULT='+json.dumps({'return_value':value,'kernel_exception':error,'original_exit_signal':signal}))
'''
class WholePilotUpdateExecution(unittest.TestCase):
 def setUp(self):
  c=fixture.WholeLifecycleValidatorExecution();c.setUp();self.addCleanup(c.doCleanups);self.reference=c;self.source=c.source;self.tools=c.tools();self.private=self.source.parent/'pilot-update-state';self.private.mkdir(mode=0o700);self.serial=0;self.at='2026-09-13T17:00:01Z';self.previous_mask=os.umask(0o077);self.addCleanup(os.umask,self.previous_mask)
 def compare(self,argv=(),*,mode='private-candidate',invocation=None):
  before=snapshot(self.source);calls=self.reference.provider_calls;calls.unlink(missing_ok=True);self.serial+=1;record=Record(self.private/('records-'+str(self.serial)),{'prototype':'whole original pilot update','argv':list(argv),'invocation':invocation},{'prototype':True});record.append({'kind':'execution-intent'});owner=NativeUpdateIO(record,mode=mode,cwd=str(self.source),private_state=self.private,product_root=ROOT,source=str(self.source),transaction_name=transaction_name)
  parser_context=capture_context();chosen=self.at
  class Clock:
   @staticmethod
   def now(zone):return ActualDatetime.fromisoformat(chosen.replace('Z','+00:00')).astimezone(zone)
  with patch('lib.providers.personal_channel_transport.datetime',Clock),patch('lib.providers.pilot_action_intake_clock.datetime',Clock):
   actual=execute(str(self.source),str(self.source),argv,owner,validator_class=Draft202012Validator,parser_context=parser_context,provider_executable=self.reference.provider,temporary_parent=str(self.reference.temporary),invocation=invocation)
  query_bytes=calls.read_bytes() if calls.exists() else b'';calls.unlink(missing_ok=True)
  # Native mode must be compared against the identical original preimage.
  after=snapshot(self.source)
  if mode=='private-candidate':self.assertEqual(after,before)
  else:
   self.assertEqual({k:v for k,v in after[0].items() if k.startswith('.git/')},{k:v for k,v in before[0].items() if k.startswith('.git/')})
   for p in sorted(self.source.rglob('*'),key=lambda p:len(p.parts),reverse=True):
    key=p.relative_to(self.source).as_posix()
    if p.is_dir():
     if key not in before[1]:p.rmdir()
    elif key not in before[0]:p.unlink()
   for name,(raw,mode_bits) in before[0].items():
    p=self.source/name
    if p.read_bytes()!=raw:p.write_bytes(raw)
    if p.stat().st_mode&511!=mode_bits:p.chmod(mode_bits)
   for name,mode_bits in before[1].items():(self.source/name).chmod(mode_bits)
  env={k:v for k,v in os.environ.items() if not k.startswith(('GIT_','LD_','DYLD_'))};env.update(PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=str(self.source/'scripts'),PATH=str(self.tools)+os.pathsep+os.environ['PATH'],GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_SYSTEM='/dev/null',GIT_CONFIG_NOSYSTEM='1')
  spec='main' if invocation is None else json.dumps(invocation)
  old=subprocess.run([sys.executable,'-B','-c',WRAPPER,str(self.source/'scripts/run_lifecycle_pilot_update.py'),self.at,spec,*argv],cwd=self.source,env=env,capture_output=True,timeout=300);self.assertEqual(old.returncode,0,old.stderr[-3500:]);parts=old.stdout.rsplit(b'\nAXIOM_ORIGINAL_RESULT=',1);self.assertEqual(len(parts),2,old.stdout[-3000:]);expected=json.loads(parts[1]);self.assertEqual({k:actual[k] for k in expected},expected,(argv,actual,expected));self.assertEqual(actual['stdout'].encode(),parts[0]);raw=b''.join((record.blobs/p['blob']['sha256']).read_bytes() if 'blob' in p else p['text'].encode() for p in actual['stderr_parts']);self.assertEqual(raw,old.stderr);self.assertEqual(calls.read_bytes() if calls.exists() else b'',query_bytes)
  observed=snapshot(self.source)
  if mode=='selected-files':self.assertEqual(observed,after)
  else:
   files,dirs=map(dict,before)
   for label,value in owner.projected_changes.items():
    if not Path(label).is_relative_to(self.source):continue
    name=Path(label).relative_to(self.source).as_posix()
    if value['kind']=='file':files[name]=((record.blobs/value['content']['sha256']).read_bytes(),value['mode'])
    elif value['kind']=='directory':dirs[name]=value['mode']
    elif value['kind']=='missing':files.pop(name,None);dirs.pop(name,None)
    else:self.fail(value)
   self.assertEqual((files,dirs),observed)
  record.finish('complete',{'exit_code':actual['exit_code'],'kernel_result':actual},owner.touched);_,_,_,events,blob,closed=read_record(record.root);cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};seen=set()
  def inert(ref):
   value=cache[ref['sha256']];self.assertEqual(len(value),ref['bytes']);self.assertEqual(hashlib.sha256(value).hexdigest(),ref['sha256']);seen.add(ref['sha256']);return value
  moved=self.source.with_name(self.source.name+'-unavailable');self.source.rename(moved)
  try:
   replay=ReplayUpdateIO(events,inert,mode,str(self.source),source=str(self.source),transaction_name=transaction_name)
   with patch('subprocess.Popen',side_effect=AssertionError('No provider/Git')),patch('tempfile.TemporaryDirectory',side_effect=AssertionError('No native temporary')),patch('os.open',side_effect=AssertionError('No selected source/native effects')):
    pure=execute(str(self.source),str(self.source),argv,replay,validator_class=Draft202012Validator,parser_context=parser_context,provider_executable=self.reference.provider,temporary_parent=str(self.reference.temporary),invocation=invocation);replay.finish()
   self.assertEqual(pure,actual);self.assertEqual(seen,set(cache))
   for name,value in cache.items():blob({'sha256':name,'bytes':len(value)})
   self.assertTrue(closed())
  finally:moved.rename(self.source)
  return actual
 def test_original_refresh_regenerates_all_original_reports_without_native_source_exports(self):
  value=self.compare(['--operation','refresh']);self.assertEqual(value['exit_code'],0,value);self.assertIn('receipts',value['stdout'])
 def test_original_operating_capture_preserves_exclusive_snapshot_and_complete_return(self):
  value=self.compare(invocation={'method':'capture','arguments':{}});self.assertEqual(value['exit_code'],0,value);self.assertEqual(value['return_value']['result']['status'],'confirmed')
 def test_original_operating_generate_preserves_all_three_report_outputs(self):
  value=self.compare(invocation={'method':'generate','arguments':{}});self.assertEqual(value['exit_code'],0,value)
 def prepare_action(self,tracked=True):
  from acceptance.lifecycle_validator_fixture import append_role_withdrawal,refresh
  self.reference.base();append_role_withdrawal(self.source,self.tools,'2026-09-13T17:00:00Z')
  for path in (self.source/'governance/lifecycle/pilot-actions/transactions').glob('*.json'):
   request=json.loads(path.read_bytes())['request'];target=self.source/'model/governance/lifecycle/action-requests/synthetic-role-withdrawal.json';target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(request,indent=2,sort_keys=True)+'\n');path.unlink()
  refresh(self.source,self.tools)
  paths=list((self.source/'model/governance/lifecycle/action-requests').glob('*.json'));self.assertEqual(len(paths),1);relative=paths[0].relative_to(self.source).as_posix()
  if tracked:
   self.reference.git('add','--',relative);self.reference.git('-c','user.name=Isolated runner fixture','-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false','-c','core.hooksPath=/dev/null','commit','--quiet','-m','Committed explicit test action request')
  return relative
 def test_whole_original_acceptance_updates_reports_in_both_private_and_native_modes(self):
  for mode in ('private-candidate','selected-files'):
   with self.subTest(mode=mode):
    value=self.compare(['--operation','acceptance'],mode=mode);self.assertEqual(value['exit_code'],0,value);self.assertIn('receipts',value['stdout'])
 def test_whole_original_refresh_native_outputs_equal_all_original_bytes_modes(self):
  value=self.compare(['--operation','refresh'],mode='selected-files');self.assertEqual(value['exit_code'],0,value)
 def test_whole_original_missing_run_request_and_unknown_API_operation_keep_verification_order(self):
  for argv in (['--operation','observe'],['--operation','action'],['--operation','observe','--source-run-id','0']):
   with self.subTest(argv=argv):value=self.compare(argv);self.assertEqual(value['exit_code'],1);self.assertEqual(value['kernel_exception']['type'],'ContractError')
  value=self.compare(invocation={'method':'run','arguments':{'operation':'unknown'}});self.assertEqual(value['kernel_exception'],{'type':'ValueError','message':'Unknown pilot operation'})
 def test_whole_original_committed_role_withdrawal_action_is_collected_and_appended(self):
  relative=self.prepare_action();value=self.compare(['--operation','action','--request-path',relative]);self.assertEqual(value['exit_code'],0,value);self.assertIsNone(value['return_value'])
 def test_whole_original_untracked_action_request_preserves_checked_Git_exception_without_stderr_emission(self):
  relative=self.prepare_action(False);value=self.compare(['--operation','action','--request-path',relative]);self.assertEqual(value['exit_code'],1);self.assertEqual(value['kernel_exception']['type'],'CalledProcessError');self.assertNotIn('pathspec',value['stderr'])
 def test_whole_original_operating_generate_partial_output_and_error_are_preserved(self):
  path=self.source/'generated/reports/governance-lifecycle-live.md';path.unlink();path.mkdir(mode=0o700);value=self.compare(invocation={'method':'generate','arguments':{}});self.assertEqual(value['exit_code'],1);self.assertEqual(value['kernel_exception']['type'],'IsADirectoryError')
 def test_whole_original_observe_uses_fresh_capture_and_original_receipt_append_in_both_modes(self):
  keys=json.loads((self.tools/'responses.json').read_bytes());run_id=next(k.rsplit('/',1)[1] for k in keys if '/actions/runs/' in k and k.rsplit('/',1)[1].isdigit())
  for mode in ('private-candidate','selected-files'):
   with self.subTest(mode=mode):value=self.compare(['--operation','observe','--source-run-id',run_id],mode=mode);self.assertEqual(value['exit_code'],0,value);self.assertIn('receipts',value['stdout'])
 def test_whole_original_committed_action_native_atomic_ledgers_and_reports_match(self):
  relative=self.prepare_action();value=self.compare(['--operation','action','--request-path',relative],mode='selected-files');self.assertEqual(value['exit_code'],0,value)
 def test_original_help_invalid_choice_and_missing_argument_do_not_observe_source_or_provider(self):
  for argv,expected in ((['--help'],0),([],2),(['--operation','bad'],2),(['--operation'],2)):
   with self.subTest(argv=argv):value=self.compare(argv);self.assertEqual(value['exit_code'],expected);self.assertEqual(value['original_exit_signal']['type'],'SystemExit')
 def test_whole_original_new_observation_appends_a_new_receipt_before_report_generation(self):
  import base64
  from acceptance.lifecycle_validator_fixture import refresh
  paths=sorted((self.source/'governance/lifecycle/live-validation/transactions').glob('*.json'));self.assertEqual(len(paths),2);record=json.loads(paths[-1].read_bytes());run_id=str(json.loads(base64.b64decode(record['capture']['run-before.json']))['id']);paths[-1].unlink();refresh(self.source,self.tools)
  value=self.compare(['--operation','observe','--source-run-id',run_id]);self.assertEqual(value['exit_code'],0,value);self.assertIn("'receipts': 2",value['stdout'])
 def test_whole_original_capture_without_any_personal_statement_keeps_guard_and_source_unchanged(self):
  import base64
  for p in (self.source/'generated/reports/lifecycle-operating-acceptance').glob('*.json'):p.unlink()
  path=self.tools/'responses.json';values=json.loads(path.read_bytes())
  for key in values:
   if '/issues/91/comments?' in key:values[key]=base64.b64encode(b'[]').decode()
  path.write_text(json.dumps(values));value=self.compare(invocation={'method':'capture','arguments':{}});self.assertEqual(value['exit_code'],1);self.assertEqual(value['kernel_exception']['message'],'Personal LD-07 statement is still missing')
 def test_whole_original_action_outside_dedicated_directory_is_rejected_before_Git(self):
  value=self.compare(['--operation','action','--request-path','../outside.json']);self.assertEqual(value['exit_code'],1);self.assertEqual(value['kernel_exception']['message'],'Request must be in the dedicated action-request directory')
if __name__=='__main__':unittest.main(verbosity=2)
