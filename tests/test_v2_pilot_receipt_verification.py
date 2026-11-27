"""Whole original independent verification with real Git/fake GET and inert replay."""
from pathlib import Path
from datetime import datetime as ActualDatetime,timedelta
from contextlib import redirect_stdout,redirect_stderr
from unittest.mock import patch
import ast,base64,copy,hashlib,io,json,os,shutil,subprocess,sys,unittest,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from jsonschema import Draft202012Validator
import test_v2_pilot_run_application as application_fixture
from test_v2_personal_channel_programs import snapshot
from lib.pilot_receipt_verification import PilotReceiptVerification
from lib.providers.pilot_receipt_verification_protocol import LegacyReceiptVerificationProtocol,NativeReceiptVerificationTransport,ReplayReceiptVerificationTransport
from lib.providers.pilot_run_intake_io import NativeRunIO
from lib.pilot_run_intake_io import ReplayRunIO
from lib.lifecycle_preflight_context import PreflightPaths
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.providers.repository_lifecycle_capture import LegacyRepositoryLifecycleCapture
from lib.providers.lifecycle_preflight import LegacyLifecyclePreflight
from lib.providers.pilot_run_temporary import NativeTemporaryFactory
from lib.pilot_run_temporary import ReplayTemporaryFactory
from lib.pilot_run_private_temporary import PrivateTemporaryFactory
from lib.personal_channel_ports import exclusive_factory
from lib.personal_channel_context import OrderedStderr
from lib.providers.synthetic_lifecycle_storage import Record,read_record
from lib.requirement_review_output import RetainedOutputError
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from lib.pilot_run_intake_ports import transaction_name

WRAPPER='''from pathlib import Path
from datetime import datetime as ActualDatetime
import json,sys
import lib.governance_lifecycle.live_evidence as fresh
import lib.governance_lifecycle.live_admission as admission
at,now,base=sys.argv[1:]
class Collection:
 @staticmethod
 def now(zone):return ActualDatetime.fromisoformat(at.replace('Z','+00:00')).astimezone(zone)
class Receipt:
 @staticmethod
 def now(zone):return ActualDatetime.fromisoformat(now.replace('Z','+00:00')).astimezone(zone)
fresh.datetime=Collection;admission.datetime=Receipt
print(json.dumps(admission.verify_new_receipts(Path.cwd(),base)))
'''
class WholePilotReceiptVerification(unittest.TestCase):
 def setUp(self):
  case=application_fixture.PilotRunApplication();case.setUp();self.addCleanup(case.doCleanups);self.fixture=case
 def prepare(self,kind):
  c=self.fixture
  def git(*a):return subprocess.check_output(['git','-C',str(c.source),*a],env={**os.environ,'GIT_CONFIG_GLOBAL':'/dev/null','GIT_CONFIG_NOSYSTEM':'1'})
  git('init','--initial-branch=original-receipt-fixture');git('config','gc.auto','0');git('config','maintenance.auto','false');git('add','--all')
  git('-c','user.name=AXIOM isolated original fixture','-c','user.email=fixture@invalid.example','-c','commit.gpgsign=false','-c','core.hooksPath=/dev/null','commit','--quiet','-m','No accepted receipts in this immutable fixture base')
  base=git('rev-parse','HEAD').decode().strip()
  if kind=='future':c.recorded=(ActualDatetime.fromisoformat(c.at.replace('Z','+00:00'))+timedelta(seconds=10)).isoformat().replace('+00:00','Z')
  old=c.original();self.assertEqual(old.returncode,0,old.stderr[-3000:])
  if kind=='accepted':
   git('add','--all');git('-c','user.name=AXIOM isolated original fixture','-c','user.email=fixture@invalid.example','-c','commit.gpgsign=false','-c','core.hooksPath=/dev/null','commit','--quiet','-m','Receipt already in immutable base');base=git('rev-parse','HEAD').decode().strip()
  if kind=='bad-base':base='missing-immutable-original-base'
  (c.tools/'calls.jsonl').unlink()
  at=ActualDatetime.fromisoformat(c.at.replace('Z','+00:00'))
  offset=2
  if kind=='stale':offset=json.loads((c.source/'model/governance/lifecycle/live-operating/00000001.json').read_bytes())['operating_policy']['maximum_age_seconds']+2
  captured=(at+timedelta(seconds=offset)).isoformat().replace('+00:00','Z');now=(at+timedelta(seconds=offset+1)).isoformat().replace('+00:00','Z')
  if kind=='different':
   p=c.tools/'responses.json';wire=json.loads(p.read_bytes());values={k:[base64.b64decode(v,validate=True) for v in rows] for k,rows in wire.items()};key=next(k for k in values if k.endswith('/zip'));out=io.BytesIO()
   with zipfile.ZipFile(io.BytesIO(values[key][0])) as archive,zipfile.ZipFile(out,'w',compression=zipfile.ZIP_STORED) as target:
    for entry in archive.infolist():target.writestr(entry,archive.read(entry.filename)+(b'\nDifferent freshly observed artifact bytes\n' if entry.filename.endswith('.md') else b''))
   raw=out.getvalue();values[key]=[raw]
   for name,rows in values.items():
    if name==key or '/actions/artifacts/' not in name and '/artifacts?' not in name:continue
    updated=[]
    for body in rows:
     value=json.loads(body)
     def change(v):
      if isinstance(v,dict):
       if 'workflow_run' in v and 'expired' in v:v['digest']='sha256:'+hashlib.sha256(raw).hexdigest();v['size_in_bytes']=len(raw)
       for nested in v.values():change(nested)
      elif isinstance(v,list):
       for nested in v:change(nested)
     change(value);updated.append(json.dumps(value).encode())
    values[name]=updated
   p.write_text(json.dumps({k:[base64.b64encode(v).decode() for v in rows] for k,rows in values.items()}))
  return base,captured,now
 def invoke(self,owner,base,*,pure=False):
  c=self.fixture;out,err=io.StringIO(),OrderedStderr();paths=PreflightPaths(str(c.source),str(c.source),owner,exclusive_factory);root=paths.path(str(c.source))
  context=RepositoryLifecycle(root,validator_class=Draft202012Validator,path_factory=paths.path,provider_factory=lambda context:LegacyRepositoryLifecycleCapture(context))
  transport=(ReplayReceiptVerificationTransport(owner,root,emit_stderr=err.emit_raw) if pure else NativeReceiptVerificationTransport(owner,root,emit_stderr=err.emit_raw,provider_executable=str(c.tools/'gh')))
  fresh=LegacyLifecyclePreflight(context,transport=transport,clock=transport.clock)
  kind=PrivateTemporaryFactory if owner.mode=='private-candidate' else ReplayTemporaryFactory if pure else NativeTemporaryFactory
  program=PilotReceiptVerification(context,fresh,path_factory=paths.path,temporary=kind(owner,str(c.parent)),clock=transport.clock,git=transport)
  error=value=None;code=0
  with redirect_stdout(out),redirect_stderr(err):
   try:value=program.verify_new_receipts(str(c.source),base)
   except RetainedOutputError as e:code,error=1,{'type':e.original_type,'message':e.original_message}
   except (InputAdmissionError,IntegrityError):raise
   except Exception as e:code,error=1,{'type':type(e).__name__,'message':str(e)}
  for session in getattr(owner,'pilot_temporary_sessions',[]):session.release()
  return {'exit_code':code,'return_value':value,'kernel_exception':error,'stdout':out.getvalue(),'stderr':err.getvalue(),'stderr_parts':err.parts}
 def compare(self,kind,native):
  c=self.fixture;base,at,now=self.prepare(kind);before=snapshot(c.source)
  old=subprocess.run([sys.executable,'-B','-c',WRAPPER,at,now,base],cwd=c.source,capture_output=True,timeout=180,env={**os.environ,'PYTHONPATH':str(c.source/'scripts'),'PATH':str(c.tools)+os.pathsep+os.environ['PATH'],'PYTHONDONTWRITEBYTECODE':'1'})
  self.assertEqual(old.returncode,0 if kind in ('normal','accepted') else 1,old.stderr[-3000:]);self.assertEqual(snapshot(c.source),before);calls=c.tools/'calls.jsonl';expected_calls=calls.read_bytes() if calls.exists() else b''
  if calls.exists():calls.unlink()
  state=c.source.parent/'verification-record';state.mkdir(mode=0o700);record=Record(state/'records',{'prototype':'whole independent receipt verification'},{'source_only':True});record.append({'kind':'execution-intent'})
  mode='selected-files' if native else 'private-candidate';ledger=str(c.source/'governance/lifecycle/live-validation');owner=NativeRunIO(record,mode=mode,cwd=str(c.source),private_state=state,product_root=ROOT,ledger=ledger,transaction_name=transaction_name)
  samples=iter([at,now])
  class Clock:
   @staticmethod
   def now(zone):return ActualDatetime.fromisoformat(next(samples).replace('Z','+00:00')).astimezone(zone)
  with patch('lib.providers.personal_channel_transport.datetime',Clock):actual=self.invoke(owner,base)
  self.assertFalse(record.capture_incomplete);self.assertEqual(actual['exit_code'],old.returncode,actual);self.assertEqual(snapshot(c.source),before);self.assertEqual(snapshot(c.parent),({},{}));self.assertEqual(calls.read_bytes() if calls.exists() else b'',expected_calls)
  if old.returncode:self.assertTrue(old.stderr.endswith((actual['kernel_exception']['type']+': '+actual['kernel_exception']['message']+'\n').encode()),(actual,old.stderr[-2000:]))
  else:self.assertEqual(actual['return_value'],json.loads(old.stdout));self.assertEqual(actual['return_value'],0 if kind=='accepted' else 1)
  if kind=='different':self.assertEqual(actual['kernel_exception']['message'],'New receipt differs from independently retrieved GitHub evidence')
  if kind=='stale':self.assertEqual(actual['kernel_exception']['message'],'New receipt is stale at PR acceptance')
  if kind=='future':self.assertEqual(actual['kernel_exception']['message'],'Receipt claims a future acceptance time')
  record.finish('complete',{'exit_code':actual['exit_code'],'kernel_result':actual},owner.touched);_,_,_,events,blob,closed=read_record(record.root);cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};seen=set()
  def inert(ref):
   raw=cache[ref['sha256']];self.assertEqual(len(raw),ref['bytes']);self.assertEqual(hashlib.sha256(raw).hexdigest(),ref['sha256']);seen.add(ref['sha256']);return raw
  shutil.rmtree(c.source);shutil.rmtree(c.tools);shutil.rmtree(c.parent);replay=ReplayRunIO(events,inert,mode,str(c.source),ledger=ledger,transaction_name=transaction_name)
  with patch('os.open',side_effect=AssertionError('No selected IO')),patch('subprocess.Popen',side_effect=AssertionError('No fresh program')),patch('tempfile.TemporaryDirectory',side_effect=AssertionError('No fresh temporary')),patch('lib.providers.personal_channel_transport.datetime',side_effect=AssertionError('No fresh clock')):pure=self.invoke(replay,base,pure=True);replay.finish()
  self.assertEqual(pure,actual);self.assertEqual(replay.files,owner.files);self.assertEqual(replay.writes,owner.writes);self.assertEqual(replay.projected_changes,owner.projected_changes);self.assertEqual(seen,set(cache))
  for ref in cache:blob({'sha256':ref,'bytes':len(cache[ref])})
  self.assertTrue(closed())
 def test_entire_original_verify_function_AST_only_declared_ports(self):
  old=next(n for n in ast.parse((ROOT/'tests/fixtures/v2-pilot-run-intake-original/live_admission.py.txt').read_bytes()).body if isinstance(n,ast.FunctionDef) and n.name=='verify_new_receipts')
  cls=next(n for n in ast.parse((ROOT/'scripts/lib/pilot_receipt_verification.py').read_bytes()).body if isinstance(n,ast.ClassDef));new=copy.deepcopy(next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='verify_new_receipts'));self.assertEqual(new.args.args.pop(0).arg,'self')
  values={'self.Path':'Path','self.context.admission.load_operating':'load_operating','self.context.admission.VALIDATION_LEDGER':'VALIDATION_LEDGER','self.context.adapter.strict_json':'strict_json','self.fresh.collect_preflight':'collect_preflight','self.context.contracts.require':'require','self.context.admission.origin_key':'origin_key','self.context.admission.producer_fingerprint':'producer_fingerprint','self.context.contracts.timestamp':'timestamp','self.git.check_output':'subprocess.check_output','self.temporary.TemporaryDirectory':'tempfile.TemporaryDirectory'}
  class Restore(ast.NodeTransformer):
   def visit_Call(self,node):
    if ast.unparse(node.func)=='self.clock':return ast.copy_location(ast.parse("datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')",mode='eval').body,node)
    return self.generic_visit(node)
   def visit_Attribute(self,node):return ast.copy_location(ast.parse(values[ast.unparse(node)],mode='eval').body,node) if ast.unparse(node) in values else self.generic_visit(node)
  self.assertEqual(ast.dump(Restore().visit(new),include_attributes=False),ast.dump(old,include_attributes=False))
 def test_new_and_accepted_original_receipts_real_Git_GET_both_modes_then_source_free_replay(self):
  for kind in ('normal','accepted'):
   for native in (False,True):
    with self.subTest(kind=kind,native=native):self.setUp();self.compare(kind,native)
 def test_independent_fresh_different_raw_artifact_is_rejected_both_modes_and_pure_replay(self):
  for native in (False,True):
   with self.subTest(native=native):self.setUp();self.compare('different',native)
 def test_freshness_and_future_recorded_time_original_guards_both_modes_and_pure_replay(self):
  for kind in ('stale','future'):
   for native in (False,True):
    with self.subTest(kind=kind,native=native):self.setUp();self.compare(kind,native)
 def test_real_missing_Git_base_original_exception_and_no_GET_both_modes_then_pure_replay(self):
  for native in (False,True):
   with self.subTest(native=native):self.setUp();self.compare('bad-base',native)
 def test_protocol_limits_original_tree_scope_and_fixed_preflight_GET(self):
  p=LegacyReceiptVerificationProtocol();good={'command':['git','ls-tree','-r','--name-only','HEAD','--','governance/lifecycle/live-validation'],'cwd':'/owned/source','text':True}
  spec=p.request('git-tree',good,'/owned/source','/owned/source');self.assertEqual(spec['original_arguments'],good['command']);self.assertEqual(p.request('get',{'endpoint':'repos/owner/repo','raw':False},'/owned/source','/owned/source')['original_arguments'][:6],['gh','api','--hostname','github.com','--method','GET'])
  for bad in ({**good,'text':False},{**good,'cwd':'/other'},{**good,'command':[*good['command'][:4],'-other',*good['command'][5:]]},{**good,'command':[*good['command'][:-1],'elsewhere']}):
   with self.assertRaises(InputAdmissionError):p.request('git-tree',bad,'/owned/source','/owned/source')
if __name__=='__main__':unittest.main(verbosity=2)
