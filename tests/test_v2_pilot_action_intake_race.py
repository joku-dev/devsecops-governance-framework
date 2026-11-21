"""Two actual native processes recheck the shared state under original ordered locks."""
from pathlib import Path
from unittest.mock import patch
import hashlib,json,os,shutil,subprocess,sys,time,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_pilot_action_intake as whole
import test_v2_personal_channel_programs as fixture

CHILD='''from pathlib import Path
import contextlib,json,os,sys,time
kind,root,control,which,state,product=sys.argv[1:];root=Path(root);control=Path(control);state=Path(state)
snapshots=json.loads((control/'snapshots.json').read_bytes());snapshot=snapshots[0 if which=='first' else 1]
def announce(stage):
 (control/(which+'-'+stage)).write_text('observed actual lock boundary')
 if stage=='held' and which=='first':
  start=time.monotonic()
  while not (control/'release-first').exists():
   assert time.monotonic()-start<25,'Test barrier timed out; never infer successful append'
   time.sleep(.01)
if kind=='original':
 sys.path.insert(0,str(root/'scripts'))
 import fcntl
 from lib.governance_lifecycle.pilot_actions import append_action_snapshot
 actual=fcntl.flock;identity=os.stat(root/'governance/lifecycle/live-validation/.append.lock')
 def observed(fd,operation):
  selected=operation==fcntl.LOCK_EX and (os.fstat(fd).st_dev,os.fstat(fd).st_ino)==(identity.st_dev,identity.st_ino)
  if selected:announce('attempt')
  result=actual(fd,operation)
  if selected:announce('held')
  return result
 fcntl.flock=observed
 try:result=append_action_snapshot(root,snapshot,recorded_at='2026-11-15T12:00:03Z',expected_sequence=0);value={'exit_code':0,'return_value':result,'kernel_exception':None}
 except Exception as error:value={'exit_code':1,'return_value':None,'kernel_exception':{'type':type(error).__name__,'message':str(error)}}
else:
 sys.path.insert(0,str(Path(product)/'scripts'))
 from jsonschema import Draft202012Validator
 from lib.pilot_action_intake_context import execute
 from lib.providers.pilot_action_ledgers import NativeActionIO,native_effects
 from lib.providers.synthetic_ledger_effects import NativeLedgerEffects
 from lib.providers.synthetic_lifecycle_storage import Record
 from lib.providers.personal_channel_transport import NativePersonalTransport
 from lib.providers.personal_channel_capture import LegacyPersonalChannelCapture
 from lib.providers.personal_channel_protocol import LegacyPersonalProtocol
 from lib.providers.pilot_action_intake_clock import NativeActionRecordedClock
 from lib.providers.retained_argparse import capture_context
 actual=NativeLedgerEffects.flock
 def observed(effect,descriptor,operation):
  selected=operation==effect.LOCK_EX and effect.descriptor(descriptor)['path']==str(root/'governance/lifecycle/live-validation/.append.lock')
  if selected:announce('attempt')
  result=actual(effect,descriptor,operation)
  if selected:announce('held')
  return result
 NativeLedgerEffects.flock=observed
 state.mkdir(mode=0o700);record=Record(state/'records',{'prototype':'native competing action API'},{'prototype':True});record.append({'kind':'execution-intent'})
 def name_of(raw):
  value=json.loads(raw);return f"{value['sequence']:08d}-{value['transaction_id'].split(':')[1]}.json"
 owner=NativeActionIO(record,source=str(root),transaction_name=name_of,mode='selected-files',cwd=str(root),private_state=state,product_root=Path(product))
 def transport(io,root,emit):return NativePersonalTransport(io,root,LegacyPersonalProtocol(),emit_stderr=emit,provider_executable='never-executed-test-provider')
 result=execute(str(root),str(root),[],owner,validator_class=Draft202012Validator,
  provider_factory=lambda context,port:LegacyPersonalChannelCapture(context,fetch=port.fetch,clock=port.clock),transport_factory=transport,effects_factory=native_effects,clock_factory=NativeActionRecordedClock,parser_context=capture_context(),
  invocation={'method':'append_action_snapshot','arguments':{'repo':str(root),'snapshot':snapshot,'recorded_at':'2026-11-15T12:00:03Z','expected_sequence':0}})
 assert not record.capture_incomplete
 record.finish('complete',{'exit_code':result['exit_code'],'kernel_result':result},owner.touched)
 value={key:result[key] for key in ('exit_code','return_value','kernel_exception')};value['record_root']=str(record.root)
 print(json.dumps(value));raise SystemExit(0)
print(json.dumps(value))
'''

class WholePilotActionRace(unittest.TestCase):
 def test_two_real_processes_recheck_context_after_wait_and_cannot_share_sequence(self):
  reference=whole.WholePilotActionIntake();reference.setUp();self.addCleanup(reference.doCleanups);root,tools,_=reference.selected('api-append')
  first=json.loads((root/'snapshot.json').read_bytes())
  # Build the competing request and complete snapshot through unchanged V1
  # validators with explicit injected transport; never patch validation results.
  script='''import json
from prepare_lifecycle_pilot_action import prepare
from lib.governance_lifecycle.personal_probe import statement_body
from lib.governance_lifecycle.pilot_actions import collect_action
request=prepare({'kind':'role_withdrawal','reason':'Second explicitly synthetic competing request; no authority.'},900002,created_at='2026-11-15T12:00:00Z')
repo=request['repository_id'];number=request['discussion_number']
comment={'id':900002,'body':statement_body(request),'user':{'id':81616324,'type':'User'},'performed_via_github_app':None,'issue_url':f'https://api.github.com/repos/{repo}/issues/{number}','html_url':f'https://github.com/{repo}/pull/{number}#issuecomment-900002','created_at':'2026-11-15T12:00:01Z','updated_at':'2026-11-15T12:00:01Z'}
def fetch(endpoint):return json.dumps([comment] if '/comments?' in endpoint else {'number':number,'html_url':f'https://github.com/{repo}/pull/{number}','pull_request':{'url':'explicit injected test transport'}}).encode()
print(json.dumps(collect_action(request,fetch=fetch,captured_at='2026-11-15T12:00:02Z')))
'''
  made=subprocess.run([sys.executable,'-B','-c',script],cwd=root,capture_output=True,env={**os.environ,'PYTHONPATH':str(root/'scripts'),'PYTHONDONTWRITEBYTECODE':'1'},timeout=180);self.assertEqual(made.returncode,0,made.stderr[-3000:]);second=json.loads(made.stdout);self.assertEqual(second['capture_method'],'injected_test_transport')
  for name in ('governance/lifecycle/live-validation','governance/lifecycle/pilot-actions'):
   directory=root/name;(directory/'transactions').mkdir(parents=True,exist_ok=True);(directory/'.append.lock').write_bytes(b'');(directory/'.append.lock').chmod(0o600)
  before=fixture.snapshot(root);all_results={}
  for kind in ('original','v2'):
   control=root.parent/('race-'+kind);control.mkdir(mode=0o700);(control/'snapshots.json').write_text(json.dumps([first,second]));script_path=control/'child.py';script_path.write_text(CHILD)
   processes={};logs={}
   try:
    for which in ('first','second'):
     log=(control/(which+'.stderr')).open('xb');logs[which]=log
     processes[which]=subprocess.Popen([sys.executable,'-B',str(script_path),kind,str(root),str(control),which,str(control/('state-'+which)),str(ROOT)],stdout=subprocess.PIPE,stderr=log,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','COLUMNS':'60','LINES':'24'})
     start=time.monotonic();marker=control/('first-held' if which=='first' else 'second-attempt')
     while not marker.exists():
      self.assertIsNone(processes[which].poll(),(kind,which,(control/(which+'.stderr')).read_bytes()[-3000:]));self.assertLess(time.monotonic()-start,25);time.sleep(.01)
    self.assertIsNone(processes['first'].poll());self.assertIsNone(processes['second'].poll());self.assertFalse((control/'second-held').exists())
    (control/'release-first').write_text('Parent observed first real lock held and second actual attempt')
    values={}
    for which,process in processes.items():
     stdout,_=process.communicate(timeout=30);self.assertEqual(process.returncode,0,(kind,which,(control/(which+'.stderr')).read_bytes()[-3000:]));values[which]=json.loads(stdout)
    self.assertEqual(values['first']['exit_code'],0);self.assertEqual(values['first']['return_value']['outcome'],'eligible_for_pilot')
    self.assertEqual(values['second']['exit_code'],1);self.assertEqual(values['second']['kernel_exception'],{'type':'ContractError','message':'Stale action sequence'})
    self.assertEqual(len(list((root/'governance/lifecycle/pilot-actions/transactions').glob('*.json'))),1)
    all_results[kind]=values
    after=fixture.snapshot(root)
    if kind=='original':expected=after;fixture.restore(root,before)
    else:
     self.assertEqual(after,expected)
     for which in ('first','second'):self.assertEqual({k:v for k,v in values[which].items() if k!='record_root'},all_results['original'][which])
   finally:
    for process in processes.values():
     if process.poll() is None:process.terminate();process.wait(timeout=10)
    for log in logs.values():log.close()
  # The second actual capture contains the newly appended first action. Its
  # complete observation must replay with no source/process/effect re-execution.
  shutil.rmtree(root);shutil.rmtree(tools)
  from jsonschema import Draft202012Validator
  from lib.pilot_action_ledgers import ReplayActionIO,replay_effects
  from lib.pilot_action_intake_context import execute
  from lib.personal_channel_process import ReplayPersonalTransport
  from lib.providers.personal_channel_protocol import LegacyPersonalProtocol
  from lib.providers.personal_channel_capture import LegacyPersonalChannelCapture
  from lib.pilot_action_intake_clock import ReplayActionRecordedClock
  from lib.providers.synthetic_lifecycle_storage import read_record
  from lib.providers.retained_argparse import capture_context
  for which,snapshot in [('first',first),('second',second)]:
   record=Path(all_results['v2'][which]['record_root']);_,_,value,events,blob,closed=read_record(record);cache={p.name:p.read_bytes() for p in (record/'blobs').iterdir()};seen=set()
   def inert(ref):
    raw=cache[ref['sha256']];self.assertEqual(hashlib.sha256(raw).hexdigest(),ref['sha256']);self.assertEqual(len(raw),ref['bytes']);seen.add(ref['sha256']);return raw
   owner=ReplayActionIO(events,inert,'selected-files',str(root),source=str(root),transaction_name=whole.transaction_name)
   def transport(io,root,emit):return ReplayPersonalTransport(io,root,LegacyPersonalProtocol(),emit_stderr=emit)
   with patch('os.open',side_effect=AssertionError('No native effects')),patch('subprocess.Popen',side_effect=AssertionError('No native process')):
    result=execute(str(root),str(root),[],owner,validator_class=Draft202012Validator,provider_factory=lambda context,port:LegacyPersonalChannelCapture(context,fetch=port.fetch,clock=port.clock),transport_factory=transport,effects_factory=replay_effects,clock_factory=ReplayActionRecordedClock,parser_context=capture_context(),invocation={'method':'append_action_snapshot','arguments':{'repo':str(root),'snapshot':snapshot,'recorded_at':whole.RECORDED,'expected_sequence':0}});owner.finish()
   self.assertEqual(result,value['result']['kernel_result']);self.assertEqual(seen,set(cache))
   for sha in seen:blob({'sha256':sha,'bytes':len(cache[sha])})
   self.assertTrue(closed())

if __name__=='__main__':unittest.main(verbosity=2)
