"""Whole original saved-capture append APIs; fresh main and temporary ports remain separate."""
from pathlib import Path
from unittest.mock import patch
import ast,base64,copy,hashlib,json,os,shutil,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from jsonschema import Draft202012Validator
import test_v2_personal_channel_programs as reference
from lib.pilot_run_intake_context import execute
from lib.providers.pilot_run_intake_io import NativeRunIO
from lib.pilot_run_intake_io import ReplayRunIO
from lib.providers.synthetic_ledger_effects import NativeLedgerEffects
from lib.synthetic_ledger_replay_effects import ReplayLedgerEffects
from lib.synthetic_ledger_private import PrivateLedgerPort
from lib.providers.repository_lifecycle_capture import LegacyRepositoryLifecycleCapture
from lib.personal_channel_ports import exclusive_factory
from lib.providers.synthetic_lifecycle_storage import Record,read_record
from lib.providers.retained_argparse import capture_context
FIXTURE=ROOT/'tests/fixtures/v2-pilot-run-intake-original';CONTRACT=json.loads((FIXTURE/'contract.json').read_bytes())
def transaction_name(raw):
 value=json.loads(raw);return f"{value['sequence']:08d}-{value['transaction_id'].split(':')[1]}.json"
class WholePilotRunIntake(unittest.TestCase):
 def setUp(self):
  f=reference.WholePersonalChannelPrograms();f.setUp();self.addCleanup(f.doCleanups);self.fixture=f
 def test_complete_original_capture_append_and_main_AST_after_only_explicit_port_bindings(self):
  old=ast.parse((FIXTURE/'live_admission.py.txt').read_bytes());program=ast.parse((FIXTURE/'intake_lifecycle_pilot_run.py.txt').read_bytes());cls=next(v for v in ast.parse((ROOT/'scripts/lib/pilot_run_intake.py').read_bytes()).body if isinstance(v,ast.ClassDef))
  bindings={'self.Path':'Path','self.context.provider.replay_capture':'replay_capture','self.context.contracts.require':'require','self.context.admission.MAX_CAPTURE_BYTES':'MAX_CAPTURE_BYTES','self.capture_files':'capture_files','self.context.store.writer_lock':'writer_lock','self.context.admission.replay_receipts':'replay_receipts','self.context.store.load_transactions':'load_transactions','self.context.admission.prepare_receipt':'prepare_receipt','self.context.store.publish_transaction':'publish_transaction','self.context.kernel.transaction_ref':'transaction_ref','self.context.admission.load_operating':'load_operating','self.fresh.collect_preflight':'collect_preflight','self.root':'ROOT','self.context.admission.VALIDATION_LEDGER':'VALIDATION_LEDGER','self.append_capture':'append_capture','self.description':'__doc__','self.argument_parser':'argparse.ArgumentParser','self.temporary.TemporaryDirectory':'tempfile.TemporaryDirectory'}
  main=next(v for v in program.body if isinstance(v,ast.FunctionDef) and v.name=='main');clock=next(v.value for v in ast.walk(main) if isinstance(v,ast.Assign) and ast.unparse(v.targets[0])=='at')
  class Restore(ast.NodeTransformer):
   def visit_Attribute(self,node):
    name=ast.unparse(node)
    return ast.copy_location(ast.parse(bindings[name],mode='eval').body,node) if name in bindings else self.generic_visit(node)
   def visit_Call(self,node):
    if ast.unparse(node.func)=='self.clock':
     assert not node.args and not node.keywords;return copy.deepcopy(clock)
    if ast.unparse(node.func)=='parser.parse_args':assert len(node.args)==1 and ast.unparse(node.args[0])=='self.argv';node.args=[]
    return self.generic_visit(node)
  for name in ('capture_files','append_capture','main'):
   source=program if name=='main' else old;expected=next(v for v in source.body if isinstance(v,ast.FunctionDef) and v.name==name);actual=copy.deepcopy(next(v for v in cls.body if isinstance(v,ast.FunctionDef) and v.name==name));self.assertEqual(actual.args.args.pop(0).arg,'self');self.assertEqual(ast.dump(Restore().visit(actual),include_attributes=False),ast.dump(expected,include_attributes=False))
 def compare_saved(self,native,*,fresh=False,stale=False,large=False):
  root,_,tools=self.fixture.fixture(prefix=False)
  for name,row in CONTRACT['files'].items():
   raw=(FIXTURE/row['fixture']).read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),row['sha256']);p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
  receipt=json.loads(next((root/'governance/lifecycle/live-validation/transactions').glob('*.json')).read_bytes());directory=root/'prepared-capture';directory.mkdir()
  for n,v in receipt['capture'].items():
   p=directory/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(base64.b64decode(v,validate=True))
  if large:
   self.assertTrue(fresh)
   # JSON permits insignificant whitespace. Keep every semantic provider fact,
   # frozen producer digest, profile and schema unchanged; bind the actual raw
   # metadata bytes in the original capture manifest. Whole V1 append_capture
   # must itself accept this complete bundle, without a substituted validator.
   metadata=directory/'repository.json'
   raw=b' '*(13*1024**2)+metadata.read_bytes();metadata.write_bytes(raw)
   captured=json.loads((directory/'preflight.json').read_bytes())
   captured['capture']['snapshot_sha256']['repository.json']=hashlib.sha256(raw).hexdigest()
   (directory/'preflight.json').write_text(json.dumps(captured,indent=2,sort_keys=True)+'\n')
   self.assertLessEqual(sum(p.stat().st_size for p in directory.rglob('*') if p.is_file()),25*1024**2)
  capture=json.loads((directory/'preflight.json').read_bytes());at=capture['captured_at'];ledger=root/('new-run-ledger' if fresh else 'governance/lifecycle/live-validation')
  args={'root':str(ledger),'directory':str(directory),'recorded_at':at,'expected_sequence':99 if stale or not fresh else 0}
  wrapper='import json,os\nos.umask(0o077)\nfrom lib.governance_lifecycle.live_admission import append_capture,load_operating\narguments=json.loads('+repr(json.dumps(args))+');print(json.dumps(append_capture(**arguments,profile=load_operating())))'
  before=reference.snapshot(root);old=subprocess.run([sys.executable,'-B','-c',wrapper],cwd=root,capture_output=True,env={**os.environ,'PYTHONPATH':str(root/'scripts'),'PYTHONDONTWRITEBYTECODE':'1'},timeout=180);self.assertEqual(old.returncode,1 if stale else 0,old.stderr[-3000:])
  if not stale:
   self.assertEqual(json.loads(old.stdout)['outcome'],'eligible_for_pilot' if fresh else 'duplicate')
  else:self.assertTrue(old.stderr.decode().endswith('ContractError: Stale receipt sequence\n'),old.stderr[-2000:])
  if large:
   published=list((ledger/'transactions').glob('*.json'));self.assertEqual(len(published),1);self.assertGreater(published[0].stat().st_size,16*1024**2)
  expected=reference.snapshot(root);reference.restore(root,before)
  # The original profile load is a separate original pre-append input. Retain
  # its exact supplied value; complete original receipt/schema replay is live.
  profile=json.loads((root/'model/governance/lifecycle/live-operating/00000001.json').read_bytes());args['profile']=profile
  state=root.parent/('state-'+str(self.fixture.serial));state.mkdir(mode=0o700);record=Record(state/'records',{'prototype':'whole original append_capture duplicate'},{'prototype':True});record.append({'kind':'execution-intent'})
  mode='selected-files' if native else 'private-candidate';owner=NativeRunIO(record,mode=mode,cwd=str(root),private_state=state,product_root=ROOT,ledger=str(ledger),transaction_name=transaction_name)
  with patch.dict(os.environ,{'COLUMNS':'60','LINES':'24'}):parser=capture_context()
  def native_effects(io):return NativeLedgerEffects(io,str(ledger),transaction_name=transaction_name) if native else PrivateLedgerPort(io,str(ledger))
  common={'validator_class':Draft202012Validator,'historical_provider_factory':lambda context:LegacyRepositoryLifecycleCapture(context),'fresh_provider_factory':lambda context,emit:None,'exclusive_factory':exclusive_factory,'temporary_factory':lambda io:None,'parser_context':parser,'clock_factory':lambda io:None,'invocation':{'method':'append_capture','arguments':args}}
  previous=os.umask(0o077)
  try:result=execute(str(root),str(root),[],owner,effects_factory=native_effects,**common)
  finally:os.umask(previous)
  self.assertFalse(record.capture_incomplete);self.assertEqual(result['exit_code'],old.returncode,result);self.assertFalse(result['kernel_end_ledger_descriptors'])
  if stale:self.assertEqual(result['kernel_exception'],{'type':'ContractError','message':'Stale receipt sequence'})
  else:self.assertEqual(result['return_value'],json.loads(old.stdout))
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
  record.finish('complete',{'exit_code':result['exit_code'],'kernel_result':result},owner.touched);_,_,_,events,blob,closed=read_record(record.root);cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};seen=set()
  def inert(ref):
   raw=cache[ref['sha256']];self.assertEqual(len(raw),ref['bytes']);self.assertEqual(hashlib.sha256(raw).hexdigest(),ref['sha256']);seen.add(ref['sha256']);return raw
  shutil.rmtree(root);replay=ReplayRunIO(events,inert,mode,str(root),ledger=str(ledger),transaction_name=transaction_name)
  def replay_effects(io):return ReplayLedgerEffects(io,str(ledger),transaction_name=transaction_name) if native else PrivateLedgerPort(io,str(ledger))
  with patch('os.open',side_effect=AssertionError('No selected IO')),patch('subprocess.Popen',side_effect=AssertionError('No program')):
   actual=execute(str(root),str(root),[],replay,effects_factory=replay_effects,**common);replay.finish()
  self.assertEqual(actual,result);self.assertEqual(replay.files,owner.files);self.assertEqual(replay.writes,owner.writes);self.assertEqual(replay.projected_changes,owner.projected_changes);self.assertEqual(seen,set(cache))
  for name in seen:blob({'sha256':name,'bytes':len(cache[name])})
  self.assertTrue(closed())
 def test_whole_original_saved_capture_duplicate_before_stale_sequence_both_modes_and_pure_replay(self):
  for native in (True,False):
   with self.subTest(native=native):self.compare_saved(native)
 def test_whole_original_saved_capture_new_receipt_full_validation_atomic_publication_and_pure_replay(self):
  for native in (True,False):
   with self.subTest(native=native):self.compare_saved(native,fresh=True)
 def test_whole_original_stale_sequence_releases_lock_without_publishing_and_pure_replay(self):
  for native in (True,False):
   with self.subTest(native=native):self.compare_saved(native,fresh=True,stale=True)
 def test_whole_original_valid_capture_above_16MiB_receipt_without_bypassing_any_validator(self):
  for native in (True,False):
   with self.subTest(native=native):self.compare_saved(native,fresh=True,large=True)
 def test_original_help_and_required_parser_errors_need_no_fresh_IO_or_temporary_ports(self):
  for argv in (['--help'],['--unknown'],['--run-id','1']):
   for native in (True,False):
    with self.subTest(argv=argv,native=native):
     root,_,_=self.fixture.fixture(prefix=False)
     program=root/'scripts/intake_lifecycle_pilot_run.py'
     program.write_bytes((FIXTURE/'intake_lifecycle_pilot_run.py.txt').read_bytes())
     env={**os.environ,'PYTHONPATH':str(root/'scripts'),'PYTHONDONTWRITEBYTECODE':'1','COLUMNS':'60','LINES':'24'}
     old=subprocess.run([sys.executable,'-B',str(program),*argv],cwd=root,env=env,capture_output=True,timeout=90)
     self.assertEqual(old.returncode,0 if argv==['--help'] else 2,old.stderr)
     before=reference.snapshot(root);ledger=root/'governance/lifecycle/live-validation'
     state=root.parent/('parser-state-'+str(self.fixture.serial));state.mkdir(mode=0o700)
     record=Record(state/'records',{'test':'whole original run-intake parser'},{'source_only':True});record.append({'kind':'execution-intent'})
     mode='selected-files' if native else 'private-candidate'
     owner=NativeRunIO(record,mode=mode,cwd=str(root),private_state=state,product_root=ROOT,ledger=str(ledger),transaction_name=transaction_name)
     with patch.dict(os.environ,{'COLUMNS':'60','LINES':'24'}):parser=capture_context()
     common={'validator_class':Draft202012Validator,'historical_provider_factory':lambda context:LegacyRepositoryLifecycleCapture(context),'fresh_provider_factory':lambda context,emit:None,'exclusive_factory':exclusive_factory,'temporary_factory':lambda io:None,'parser_context':parser,'clock_factory':lambda io:None}
     def effects(io,replay=False):return (ReplayLedgerEffects if replay else NativeLedgerEffects)(io,str(ledger),transaction_name=transaction_name) if native else PrivateLedgerPort(io,str(ledger))
     result=execute(str(root),str(root),argv,owner,effects_factory=effects,**common)
     self.assertEqual(result['exit_code'],old.returncode);self.assertEqual(result['stdout'].encode(),old.stdout);self.assertEqual(result['stderr'].encode(),old.stderr);self.assertIsNone(result['kernel_exception'])
     self.assertEqual(reference.snapshot(root),before);self.assertEqual(owner.metadata,{})
     record.finish('complete',{'exit_code':result['exit_code'],'kernel_result':result},{})
     _,_,_,events,blob,closed=read_record(record.root)
     shutil.rmtree(root)
     replay=ReplayRunIO(events,blob,mode,str(root),ledger=str(ledger),transaction_name=transaction_name)
     with patch('os.open',side_effect=AssertionError('No source')),patch('subprocess.Popen',side_effect=AssertionError('No fresh process')):
      actual=execute(str(root),str(root),argv,replay,effects_factory=lambda io:effects(io,True),**common);replay.finish()
     self.assertEqual(actual,result);self.assertTrue(closed())
if __name__=='__main__':unittest.main(verbosity=2)
