"""Entire unchanged original fresh action intake with two real ledger locks and pure replay."""
from pathlib import Path
from unittest.mock import patch
from datetime import datetime as ActualDatetime
import ast,copy,hashlib,json,os,shutil,subprocess,sys,unittest,stat
from contextlib import ExitStack
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from jsonschema import Draft202012Validator
from lib.providers.synthetic_ledger_effects import NativeLedgerEffects
import test_v2_personal_channel_programs as reference
from lib.pilot_action_intake_context import execute
from lib.pilot_action_ledgers import ReplayActionIO,replay_effects
from lib.providers.pilot_action_ledgers import NativeActionIO,native_effects
from lib.providers.pilot_action_intake_clock import NativeActionRecordedClock
from lib.pilot_action_intake_clock import ReplayActionRecordedClock
from lib.providers.personal_channel_capture import LegacyPersonalChannelCapture
from lib.providers.personal_channel_transport import NativePersonalTransport
from lib.personal_channel_process import ReplayPersonalTransport
from lib.providers.personal_channel_protocol import LegacyPersonalProtocol
from lib.providers.synthetic_lifecycle_storage import Record,read_record
from lib.providers.retained_argparse import capture_context

FIXTURE=ROOT/'tests/fixtures/v2-pilot-action-intake-original';CONTRACT=json.loads((FIXTURE/'contract.json').read_bytes())
COLLECT='2026-11-15T12:00:02Z';RECORDED='2026-11-15T12:00:03Z'
class CollectionClock:
 @staticmethod
 def now(zone):return ActualDatetime.fromisoformat(COLLECT.replace('Z','+00:00')).astimezone(zone)
class RecordedClock:
 @staticmethod
 def now(zone):return ActualDatetime.fromisoformat(RECORDED.replace('Z','+00:00')).astimezone(zone)

def transaction_name(raw):
 value=json.loads(raw);return f"{value['sequence']:08d}-{value['transaction_id'].split(':')[1]}.json"

class WholePilotActionIntake(unittest.TestCase):
 def setUp(self):
  f=reference.WholePersonalChannelPrograms();f.setUp();self.addCleanup(f.doCleanups);self.fixture=f
 def selected(self,kind):
  root,config,tools=self.fixture.fixture(prefix=False)
  for path,row in CONTRACT['files'].items():
   raw=(FIXTURE/row['fixture']).read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),row['sha256']);(root/path).write_bytes(raw)
  # Whole immutable original request preparation and statement construction;
  # no replay_receipts/prepare_action/schema validation function is patched.
  (root/'scripts/prepare_lifecycle_pilot_action.py').write_bytes((ROOT/'tests/fixtures/v2-pilot-action-preparation-original/prepare_lifecycle_pilot_action.py.txt').read_bytes())
  make='''import json
from prepare_lifecycle_pilot_action import prepare
from lib.governance_lifecycle.personal_probe import statement_body
request=prepare({'kind':'role_withdrawal','reason':'Explicit synthetic intake test; no real consent or activation.'},900001,created_at='2026-11-15T12:00:00Z')
print(json.dumps({'request':request,'statement':statement_body(request)}))
'''
  old=subprocess.run([sys.executable,'-B','-c',make],cwd=root,capture_output=True,env={**os.environ,'PYTHONPATH':str(root/'scripts'),'PYTHONDONTWRITEBYTECODE':'1'},timeout=180);self.assertEqual(old.returncode,0,old.stderr[-3000:]);made=json.loads(old.stdout);request=made['request'];n=request['discussion_number'];repo=request['repository_id']
  comment={'id':900001,'body':made['statement'],'user':{'id':81616324,'type':'User'},'performed_via_github_app':None,'issue_url':f'https://api.github.com/repos/{repo}/issues/{n}','html_url':f'https://github.com/{repo}/pull/{n}#issuecomment-900001','created_at':'2026-11-15T12:00:01Z','updated_at':'2026-11-15T12:00:01Z'}
  config.update(endpoint=f'repos/{repo}/issues/{n}',issue=json.dumps({'number':n,'html_url':f'https://github.com/{repo}/pull/{n}','pull_request':{'url':'explicit injected test transport'}}),comments=json.dumps([comment]))
  if kind=='changed-discussion':config['kind']='race'
  if kind=='missing-statement':config['comments']='[]'
  (tools/'config.json').write_text(json.dumps(config));path=root/'request.json';path.write_text(json.dumps(request))
  if kind=='invalid-json':path.write_bytes(b'{')
  if kind.startswith('api-append'):
   make_snapshot='''import json,sys
from lib.governance_lifecycle.pilot_actions import collect_action
request=json.loads(open(sys.argv[1]).read());print(json.dumps(collect_action(request,captured_at='2026-11-15T12:00:02Z')))
'''
   snapshot=subprocess.run([sys.executable,'-B','-c',make_snapshot,str(path)],cwd=root,capture_output=True,env={**os.environ,'PYTHONPATH':str(root/'scripts'),'PATH':str(tools)+os.pathsep+os.environ['PATH'],'PYTHONDONTWRITEBYTECODE':'1'},timeout=180);self.assertEqual(snapshot.returncode,0,snapshot.stderr[-3000:]);(root/'snapshot.json').write_bytes(snapshot.stdout)
   calls=tools/'calls.jsonl'
   if calls.exists():calls.unlink()
  args=['--request',str(path),'--expected-sequence','99' if kind=='stale-sequence' else '0']
  if kind=='help':args=['--help']
  if kind=='unknown':args=['--unknown']
  return root,tools,args
 def compare(self,kind='normal',native=True):
  root,tools,args=self.selected(kind);before=reference.snapshot(root);program=root/'scripts/intake_lifecycle_pilot_action.py'
  wrapper='''import builtins,runpy,sys,types
from datetime import datetime as ActualDatetime,timezone
import lib.governance_lifecycle.personal_probe as probe
class Collect:
 @staticmethod
 def now(zone):return ActualDatetime.fromisoformat('2026-11-15T12:00:02+00:00').astimezone(zone)
class Recorded:
 @staticmethod
 def now(zone):return ActualDatetime.fromisoformat('2026-11-15T12:00:03+00:00').astimezone(zone)
probe.datetime=Collect;native_import=builtins.__import__;path=sys.argv[1]
def selected(name,globals=None,locals=None,fromlist=(),level=0):
 if name=='datetime' and globals and globals.get('__file__')==path:return types.SimpleNamespace(datetime=Recorded,timezone=timezone)
 return native_import(name,globals,locals,fromlist,level)
builtins.__import__=selected;sys.argv=[path,*sys.argv[2:]];runpy.run_path(path,run_name='__main__')
'''
  invocation=None
  if kind.startswith('api-'):
   if kind.startswith('api-collect'):
    arguments={'request':json.loads((root/'request.json').read_bytes())}
    if kind=='api-collect-explicit':arguments.update(repo=str(root),captured_at=COLLECT)
    invocation={'method':'collect_action','arguments':arguments}
   else:invocation={'method':'append_action_snapshot','arguments':{'repo':str(root),'snapshot':json.loads((root/'snapshot.json').read_bytes()),'recorded_at':RECORDED,'expected_sequence':99 if kind=='api-append-stale' else 0}}
   call='import json,lib.governance_lifecycle.pilot_actions as actions\nprint(json.dumps(getattr(actions,'+repr(invocation['method'])+')(**json.loads('+repr(json.dumps(invocation['arguments']))+'))))'
   ast.parse(call)
   wrapper=wrapper.replace("runpy.run_path(path,run_name='__main__')",call)
  if kind=='directory-fsync-error':
   injection='''import os,stat
actual_sync=os.fsync
def failed_directory(fd):
 if stat.S_ISDIR(os.fstat(fd).st_mode):raise OSError(5,'Input/output error')
 return actual_sync(fd)
os.fsync=failed_directory
'''
   wrapper=wrapper.replace('builtins.__import__=selected',injection+'builtins.__import__=selected')
  env={**os.environ,'PYTHONPATH':str(root/'scripts'),'PATH':str(tools)+os.pathsep+os.environ['PATH'],'PYTHONDONTWRITEBYTECODE':'1','COLUMNS':'60','LINES':'24'}
  if kind=='duplicate':
   seed=subprocess.run([sys.executable,'-B','-c',wrapper,str(program),*args],cwd=root,capture_output=True,env=env,timeout=180);self.assertEqual(seed.returncode,0,seed.stderr[-3000:]);before=reference.snapshot(root);calls=tools/'calls.jsonl'
   if calls.exists():calls.unlink()
   args=args[:-1]+['99']
  old=subprocess.run([sys.executable,'-B','-c',wrapper,str(program),*args],cwd=root,capture_output=True,env=env,timeout=180)
  expected_code=0 if kind in ('normal','help','duplicate','api-collect-default','api-collect-explicit','api-append') else 2 if kind=='unknown' else 1
  self.assertEqual(old.returncode,expected_code,(kind,old.stderr[-4000:]))
  expected=reference.snapshot(root)
  if kind=='directory-fsync-error':self.assertEqual(len([n for n in expected[0] if n.startswith('governance/lifecycle/pilot-actions/transactions/') and n.endswith('.json')]),1)
  reference.restore(root,before)
  calls=tools/'calls.jsonl';old_calls=calls.read_bytes() if calls.exists() else b''
  if calls.exists():calls.unlink()
  state=root.parent/('state-'+str(self.fixture.serial));state.mkdir(mode=0o700);record=Record(state/'records',{'prototype':'complete original action intake'},{'prototype':True});record.append({'kind':'execution-intent'})
  mode='selected-files' if native else 'private-candidate';owner=NativeActionIO(record,mode=mode,cwd=str(root),private_state=state,product_root=ROOT,source=str(root),transaction_name=transaction_name)
  with patch.dict(os.environ,{'COLUMNS':'60','LINES':'24'}):frame=capture_context()
  def transport(io,source,emit):return NativePersonalTransport(io,source,LegacyPersonalProtocol(),emit_stderr=emit,provider_executable=str(tools/'gh'))
  common={'validator_class':Draft202012Validator,'provider_factory':lambda context,port:LegacyPersonalChannelCapture(context,fetch=port.fetch,clock=port.clock),'parser_context':frame}
  with ExitStack() as stack:
   stack.enter_context(patch('lib.providers.personal_channel_transport.datetime',CollectionClock));stack.enter_context(patch('lib.providers.pilot_action_intake_clock.datetime',RecordedClock))
   if kind=='directory-fsync-error':
    original_sync=NativeLedgerEffects.sync_descriptor
    def selected_sync(effect,descriptor):
     if stat.S_ISDIR(os.fstat(descriptor).st_mode):raise OSError(5,'Input/output error')
     return original_sync(effect,descriptor)
    stack.enter_context(patch.object(NativeLedgerEffects,'sync_descriptor',selected_sync))
   actual=execute(str(root),str(root),args,owner,**common,transport_factory=transport,effects_factory=native_effects,clock_factory=NativeActionRecordedClock,invocation=invocation)
  self.assertFalse(record.capture_incomplete);self.assertEqual(actual['exit_code'],old.returncode,actual)
  if invocation is not None and old.returncode==0:
   self.assertEqual(actual['return_value'],json.loads(old.stdout));self.assertEqual(actual['stdout'],'')
  else:self.assertEqual(actual['stdout'].encode(),old.stdout)
  if actual['kernel_exception'] is None:self.assertEqual(actual['stderr'].encode(),old.stderr)
  else:
   error=actual['kernel_exception'];self.assertTrue(old.stderr.endswith((error['type']+': '+error['message']+'\n').encode()),(actual,old.stderr[-4000:]))
  self.assertEqual(calls.read_bytes() if calls.exists() else b'',old_calls)
  if native:self.assertEqual(reference.snapshot(root),expected)
  else:
   self.assertEqual(reference.snapshot(root),before);files,dirs=map(dict,before)
   for label,value in owner.projected_changes.items():
    name=Path(label).relative_to(root).as_posix()
    if value['kind']=='file':files[name]=((record.blobs/value['content']['sha256']).read_bytes(),value['mode'])
    elif value['kind']=='directory':dirs[name]=value['mode']
    elif value['kind']=='missing':files.pop(name,None);dirs.pop(name,None)
    else:self.fail(value)
   self.assertEqual((files,dirs),expected)
  record.finish('complete',{'exit_code':actual['exit_code'],'kernel_result':actual},owner.touched)
  _,_,_,events,blob,closed=read_record(record.root)
  intents=[(i,row) for i,row in enumerate(events) if row.get('kind')=='intent']
  collected=[i for i,row in intents if row.get('action')=='personal-capture-clock']
  recorded=[i for i,row in intents if row.get('action')=='pilot-action-recorded-clock']
  self.assertEqual(len(collected),1 if kind in ('normal','duplicate','stale-sequence','missing-statement','directory-fsync-error','api-collect-default') else 0)
  self.assertEqual(len(recorded),1 if kind in ('normal','duplicate','stale-sequence','directory-fsync-error') else 0)
  if recorded:self.assertLess(collected[0],recorded[0])
  action='synthetic-ledger-open' if native else 'synthetic-ledger-private-open'
  opened=[(i,row['arguments']['path']) for i,row in intents if row.get('action')==action and row['arguments']['path'].endswith('/.append.lock')]
  expected_locks=[str(root/'governance/lifecycle/live-validation/.append.lock'),str(root/'governance/lifecycle/pilot-actions/.append.lock')]
  self.assertEqual([name for _,name in opened],expected_locks if recorded or kind.startswith('api-append') else [])
  if opened and recorded:self.assertLess(recorded[0],opened[0][0])
  def replay_transport(io,source,emit):return ReplayPersonalTransport(io,source,LegacyPersonalProtocol(),emit_stderr=emit)
  cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};seen=set()
  def inert(ref):
   raw=cache[ref['sha256']];self.assertEqual(len(raw),ref['bytes']);self.assertEqual(hashlib.sha256(raw).hexdigest(),ref['sha256']);seen.add(ref['sha256']);return raw
  shutil.rmtree(root);shutil.rmtree(tools);replay=ReplayActionIO(events,inert,mode,str(root),source=str(root),transaction_name=transaction_name)
  with patch('os.open',side_effect=AssertionError('No native effects')),patch('subprocess.Popen',side_effect=AssertionError('No native process')),patch('lib.providers.personal_channel_transport.datetime',side_effect=AssertionError('No native clock')),patch('lib.providers.pilot_action_intake_clock.datetime',side_effect=AssertionError('No native clock')):
   pure=execute(str(root),str(root),args,replay,**common,transport_factory=replay_transport,effects_factory=replay_effects,clock_factory=ReplayActionRecordedClock,invocation=invocation);replay.finish()
  self.assertEqual(pure,actual);self.assertEqual(replay.files,owner.files);self.assertEqual(replay.writes,owner.writes);self.assertEqual(replay.projected_changes,owner.projected_changes)
  self.assertEqual(seen,set(cache))
  for sha in seen:blob({'sha256':sha,'bytes':len(cache[sha])})
  self.assertTrue(closed())
 def test_whole_original_collect_and_append_APIs_default_explicit_and_stale_inputs(self):
  for kind in ('api-collect-default','api-collect-explicit','api-append','api-append-stale'):
   for native in (False,True):
    with self.subTest(kind=kind,native=native):self.compare(kind,native)

 def test_original_directory_fsync_failure_retains_visible_atomic_action_and_releases_both_locks(self):
  self.compare('directory-fsync-error',True)

 def test_whole_original_help_and_parser_errors_without_collection_or_ledger_effects(self):
  for kind in ('help','unknown'):
   for native in (False,True):
    with self.subTest(kind=kind,native=native):self.compare(kind,native)
 def test_whole_original_fresh_collection_two_locks_atomic_append_and_statement(self):
  for native in (False,True):
   with self.subTest(native=native):self.compare(native=native)
 def test_whole_original_invalid_json_missing_statement_race_and_stale_sequence(self):
  for kind in ('invalid-json','missing-statement','changed-discussion','stale-sequence'):
   for native in (False,True):
    with self.subTest(kind=kind,native=native):self.compare(kind,native)


 def test_whole_original_duplicate_precedes_stale_expected_sequence_and_retains_two_locks(self):
  for native in (False,True):
   with self.subTest(native=native):self.compare('duplicate',native)

 def test_complete_collect_append_and_main_AST_after_only_explicit_dependencies(self):
  old=ast.parse((FIXTURE/'pilot_actions.py.txt').read_bytes());program=ast.parse((FIXTURE/'intake_lifecycle_pilot_action.py.txt').read_bytes());whole=ast.parse((ROOT/'scripts/lib/pilot_action_intake.py').read_bytes());cls=next(n for n in whole.body if isinstance(n,ast.ClassDef))
  bindings={'self.context.actions.load_context':'load_context','self.context.contracts.schema_validator':'schema_validator','self.context.provider.collect_bound':'collect_bound','self.context.actions.assess_action_comments':'assess_action_comments','self.context.actions.prior_statements':'prior_statements','self.context.actions.prepare_action':'prepare_action','self.Path':'Path','self.context.admission.VALIDATION_LEDGER':'VALIDATION_LEDGER','self.context.actions.ACTION_LEDGER':'ACTION_LEDGER','self.context.store.writer_lock':'writer_lock','self.context.store.publish_transaction':'publish_transaction','self.context.kernel.transaction_ref':'transaction_ref','self.context.contracts.require':'require','self.context.adapter.strict_json':'strict_json','self.root':'ROOT','self.collect_action':'collect_action','self.append_action_snapshot':'append_action_snapshot','self.argument_parser':'argparse.ArgumentParser','self.description':'__doc__'}
  guard=next(n for n in program.body if isinstance(n,ast.If));clock=copy.deepcopy(next(n.value for n in guard.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='at' for t in n.targets)))
  class Restore(ast.NodeTransformer):
   def visit_Attribute(self,node):
    name=ast.unparse(node)
    return ast.copy_location(ast.parse(bindings[name],mode='eval').body,node) if name in bindings else self.generic_visit(node)
   def visit_Call(self,node):
    if ast.unparse(node.func)=='self.clock':
     assert not node.args and not node.keywords;return copy.deepcopy(clock)
    if ast.unparse(node.func)=='parser.parse_args':
     assert len(node.args)==1 and ast.unparse(node.args[0])=='self.argv' and not node.keywords;node.args=[]
    return self.generic_visit(node)
  for name in ('collect_action','append_action_snapshot'):
   original=next(n for n in old.body if isinstance(n,ast.FunctionDef) and n.name==name);current=copy.deepcopy(next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name==name));self.assertEqual(current.args.args.pop(0).arg,'self')
   if name=='collect_action':
    self.assertEqual(ast.unparse(current.args.defaults[0]),'_OMITTED');self.assertEqual(ast.unparse(current.body[0]),'if repo is _OMITTED:\n    repo = self.root');current.body.pop(0);current.args.defaults=copy.deepcopy(original.args.defaults)
   self.assertEqual(ast.dump(Restore().visit(current),include_attributes=False),ast.dump(original,include_attributes=False))
  main=copy.deepcopy(next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='main'));self.assertEqual(main.args.args.pop(0).arg,'self')
  self.assertEqual(ast.dump(ast.Module(body=[Restore().visit(n) for n in main.body],type_ignores=[]),include_attributes=False),ast.dump(ast.Module(body=guard.body,type_ignores=[]),include_attributes=False))

if __name__=='__main__':unittest.main(verbosity=2)
