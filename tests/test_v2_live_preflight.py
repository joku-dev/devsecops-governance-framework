"""Whole unchanged original capture/replay, real GET executable and source-deleted replay."""
from pathlib import Path
from datetime import datetime as ActualDatetime
from unittest.mock import patch
from contextlib import ExitStack
import ast,base64,copy,hashlib,io,json,os,shutil,subprocess,sys,unittest,zipfile
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from jsonschema import Draft202012Validator
import test_v2_personal_channel_programs as reference
from lib.lifecycle_preflight_context import execute
from lib.providers.lifecycle_preflight import LegacyLifecyclePreflight
from lib.providers.lifecycle_preflight_protocol import NativePreflightTransport,ReplayPreflightTransport
from lib.providers.lifecycle_preflight_io import NativePreflightIO as NativeIO
from lib.lifecycle_preflight_io import ReplayPreflightIO as ReplayIO
from lib.providers.synthetic_lifecycle_storage import Record,read_record
from lib.personal_channel_ports import exclusive_factory
from lib.providers.retained_argparse import capture_context

FIXTURE=ROOT/'tests/fixtures/v2-live-preflight-original';CONTRACT=json.loads((FIXTURE/'contract.json').read_bytes())
class WholeLivePreflight(unittest.TestCase):
 def setUp(self):
  f=reference.WholePersonalChannelPrograms();f.setUp();self.addCleanup(f.doCleanups);self.fixture=f
 def selected(self,kind):
  root,_,tools=self.fixture.fixture(prefix=False)
  for name,row in CONTRACT['files'].items():
   raw=(FIXTURE/row['fixture']).read_bytes();self.assertEqual(hashlib.sha256(raw).hexdigest(),row['sha256']);self.assertEqual(hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),row['git_blob']);(root/name).write_bytes(raw)
  receipt=json.loads(next((root/'governance/lifecycle/live-validation/transactions').glob('*.json')).read_bytes())
  files={n:base64.b64decode(v,validate=True) for n,v in receipt['capture'].items()};record=json.loads(files['preflight.json']);profile=json.loads(files['profile.json']);run=json.loads(files['run-before.json']);artifact=json.loads(files['artifact-before.json'])
  endpoint='repos/'+profile['scope']['repository_id'];run_endpoint=endpoint+'/actions/runs/'+str(run['id']);artifact_endpoint=endpoint+'/actions/artifacts/'+str(artifact['id'])
  replies={endpoint:[files['repository.json']],run_endpoint:[files['run-before.json'],files['run-after.json']],endpoint+'/actions/workflows/'+str(run['workflow_id']):[files['workflow.json']],artifact_endpoint:[files['artifact-before.json'],files['artifact-after.json']],artifact_endpoint+'/zip':[files['artifact.zip']]}
  pages=sorted(n for n in files if n.startswith('artifacts-page-'))
  for name in pages:replies[run_endpoint+'/artifacts?per_page=100&page='+name.split('-')[-1].split('.')[0]]=[files[name]]
  for name in profile['source']['reference_files']:replies[endpoint+'/contents/'+name+'?ref='+run['head_sha']]=[files['producer/'+name]]
  if kind=='maximum-archive':
   # A complete valid ZIP at the original10MiB limit, above the old8MiB
   # personal-stream budget; do not change or bypass the original verifier.
   def archive(markdown):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_STORED) as bundle:
     for name,raw in [(profile['source']['report_path'],files['report.json']),('governance-repository-security.md',markdown)]:
      entry=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));bundle.writestr(entry,raw)
    return stream.getvalue()
   raw=archive(b'x'*(10*1024**2-len(archive(b''))));self.assertEqual(len(raw),10*1024**2)
   changed=dict(artifact);changed.update(size_in_bytes=len(raw),digest='sha256:'+hashlib.sha256(raw).hexdigest())
   encoded=json.dumps(changed).encode();replies[artifact_endpoint]=[encoded,encoded];replies[artifact_endpoint+'/zip']=[raw]
   replies[run_endpoint+'/artifacts?per_page=100&page=1']=[json.dumps({'total_count':1,'artifacts':[changed]}).encode()]
  if kind=='metadata-race':
   changed=dict(run);changed['updated_at']='2026-11-15T12:00:00Z';replies[run_endpoint][1]=json.dumps(changed).encode()
  if kind=='bad-digest':replies[artifact_endpoint+'/zip']=[files['artifact.zip']+b'changed']
  if kind=='invalid-json':replies[endpoint]=[b'{']
  if kind=='missing-artifact':
   replies[run_endpoint+'/artifacts?per_page=100&page=1']=[b'{"total_count":0,"artifacts":[]}']
  if kind=='rerun':
   changed=dict(run);changed['run_attempt']=2;replies[run_endpoint][0]=json.dumps(changed).encode()
  config={name:[base64.b64encode(raw).decode() for raw in values] for name,values in replies.items()};(tools/'responses.json').write_text(json.dumps(config))
  fake='''import base64,json,sys
from pathlib import Path
b=Path(__file__).resolve().parent;args=sys.argv[1:]
assert args[:5]==['api','--hostname','github.com','--method','GET']
assert len(args)==6 or len(args)==8 and args[6:]==['-H','Accept: application/vnd.github.raw+json']
endpoint=args[5];raw=len(args)==8;path=b/'calls.jsonl'
old=[json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []
with path.open('a') as stream:stream.write(json.dumps([endpoint,raw])+'\\n')
appearance=b/'appearance.json'
if not old and appearance.exists():
 entry=json.loads(appearance.read_bytes());target=Path(entry['path']);target.parent.mkdir(parents=True,exist_ok=True)
 if entry['kind']=='directory':target.mkdir()
 else:target.write_bytes(b'concurrent')
values=json.loads((b/'responses.json').read_bytes())[endpoint];index=sum(x[0]==endpoint for x in old)
sys.stdout.buffer.write(base64.b64decode(values[min(index,len(values)-1)],validate=True))
'''
  (tools/'gh').write_text('#!'+sys.executable+'\n'+fake);(tools/'gh').chmod(0o700)
  destination=root/'generated/reports/lifecycle-live-preflight/fresh'
  if kind.startswith('during-get-'):(tools/'appearance.json').write_text(json.dumps({'path':str(destination),'kind':kind.removeprefix('during-get-')}))
  if kind=='existing':destination.mkdir(parents=True)
  if kind=='wrong-directory':destination=root/'wrong'
  argv=['--run-id',str(run['id']),'--output-dir',str(destination)]
  if kind=='help':argv=['--help']
  if kind=='unknown':argv=['--unknown']
  if kind=='missing-output':argv=['--run-id',str(run['id'])]
  return root,tools,argv,record['captured_at'],destination
 def compare(self,kind='normal',native=True):
  root,tools,args,at,destination=self.selected(kind);program=root/'scripts/preflight_lifecycle_live_evidence.py'
  wrapper='''import runpy,sys
from datetime import datetime as ActualDatetime
import lib.governance_lifecycle.live_evidence as preflight
at=sys.argv[1]
class Clock:
 @staticmethod
 def now(zone):return ActualDatetime.fromisoformat(at.replace('Z','+00:00')).astimezone(zone)
preflight.datetime=Clock;sys.argv=sys.argv[2:];runpy.run_path(sys.argv[0],run_name='__main__')
'''
  if kind.startswith('race-'):
   injection="""from pathlib import Path
import subprocess
original_mkdir=Path.mkdir
def race(path,mode=0o777,parents=False,exist_ok=False):
 if str(path)==DESTINATION and not parents and not exist_ok:
  create="from pathlib import Path;import sys;p=Path(sys.argv[1]);p.mkdir()" if ENTRY_KIND=='directory' else "from pathlib import Path;import sys;p=Path(sys.argv[1]);p.write_bytes(b'concurrent')"
  subprocess.run([sys.executable,'-B','-c',create,str(path)],check=True)
 return original_mkdir(path,mode=mode,parents=parents,exist_ok=exist_ok)
Path.mkdir=race
"""
   injection=injection.replace('DESTINATION',repr(str(destination))).replace('ENTRY_KIND',repr(kind.removeprefix('race-')))
   wrapper=wrapper.replace('preflight.datetime=Clock;',injection+'preflight.datetime=Clock;')
  if kind=='partial-seven-bytes':
   injection="""import io
original_open=io.open
class Partial:
 def __init__(self,stream):self.stream=stream
 def __getattr__(self,name):return getattr(self.stream,name)
 def __enter__(self):return self
 def __exit__(self,*args):return self.stream.__exit__(*args)
 def write(self,raw):
  self.stream.write(raw[:7]);self.stream.flush();raise OSError(28,'No space left on device')
def partial(file,mode='r',*args,**kwargs):
 stream=original_open(file,mode,*args,**kwargs)
 return Partial(stream) if mode=='xb' and str(file)==PARTIAL_PATH else stream
io.open=partial
""".replace('PARTIAL_PATH',repr(str(destination/'repository.json')))
   wrapper=wrapper.replace('preflight.datetime=Clock;',injection+'preflight.datetime=Clock;')
  env={**os.environ,'PYTHONPATH':str(root/'scripts'),'PYTHONDONTWRITEBYTECODE':'1','PATH':str(tools)+os.pathsep+os.environ['PATH'],'COLUMNS':'60','LINES':'24'}
  if kind=='replay':
   seed=subprocess.run([sys.executable,'-B','-c',wrapper,at,str(program),*args],cwd=root,env=env,capture_output=True,timeout=180);self.assertEqual(seed.returncode,0,seed.stderr[-3000:]);args=['--verify-bundle',str(destination)]
   (tools/'calls.jsonl').unlink()
  invocation=None
  if kind.startswith('api-'):
   arguments={'run_id':args[1],'output_dir':str(destination)}
   if kind=='api-explicit':arguments.update(repo_root=str(root),captured_at=at)
   if kind=='api-empty-clock':arguments['captured_at']=''
   if kind=='api-none-fetch':arguments['fetch']=None
   invocation={'method':'collect_preflight','arguments':arguments}
   call='print(__import__("json").dumps(preflight.collect_preflight(**__import__("json").loads('+repr(json.dumps(arguments))+'))))'
   ast.parse(call)
   wrapper=wrapper.replace("runpy.run_path(sys.argv[0],run_name='__main__')",call)
  before=reference.snapshot(root);old=subprocess.run([sys.executable,'-B','-c',wrapper,at,str(program),*args],cwd=root,env=env,capture_output=True,timeout=180)
  expected_code=0 if kind in ('normal','maximum-archive','help','replay','api-default','api-explicit','api-empty-clock') else 2 if kind in ('unknown','missing-output') else 1
  self.assertEqual(old.returncode,expected_code,(kind,old.stderr[-4000:]));expected=reference.snapshot(root);reference.restore(root,before)
  calls=tools/'calls.jsonl';old_calls=calls.read_bytes() if calls.exists() else b''
  if calls.exists():calls.unlink()
  state=root.parent/('state-'+str(self.fixture.serial));state.mkdir(mode=0o700);record=Record(state/'records',{'prototype':'whole original diagnostic preflight'},{'prototype':True});record.append({'kind':'execution-intent'})
  owner_type=NativeIO
  if kind.startswith('race-'):
   class CompetingIO(NativeIO):
    def make_exclusive_directory(self,anchor,path,mode):
     create="from pathlib import Path;import sys;p=Path(sys.argv[1]);p.mkdir()" if kind=='race-directory' else "from pathlib import Path;import sys;p=Path(sys.argv[1]);p.write_bytes(b'concurrent')"
     subprocess.run([sys.executable,'-B','-c',create,path],check=True)
     return super().make_exclusive_directory(anchor,path,mode)
   owner_type=CompetingIO
  mode='selected-files' if native else 'private-candidate';owner=owner_type(record,mode=mode,cwd=str(root),private_state=state,product_root=ROOT)
  with patch.dict(os.environ,{'COLUMNS':'60','LINES':'24'}):frame=capture_context()
  def transport(io,source,emit):return NativePreflightTransport(io,source,emit_stderr=emit,provider_executable=str(tools/'gh'))
  selected_exclusive=exclusive_factory
  if kind=='partial-seven-bytes':
   class Partial:
    def __init__(self,stream):self.stream=stream
    def __getattr__(self,name):return getattr(self.stream,name)
    def write(self,raw):
     self.stream.write(raw[:7]);self.stream.flush();raise OSError(28,'No space left on device')
   def selected_exclusive(io,path,label):
    value=exclusive_factory(io,path,label)
    if path==str(destination/'repository.json') and hasattr(io,'record'):value.stream=Partial(value.stream)
    return value
  common={'validator_class':Draft202012Validator,'provider_factory':lambda context,port:LegacyLifecyclePreflight(context,transport=port,clock=port.clock),'exclusive_factory':selected_exclusive,'parser_context':frame}
  class Clock:
   @staticmethod
   def now(zone):return ActualDatetime.fromisoformat(at.replace('Z','+00:00')).astimezone(zone)
  with patch('lib.providers.personal_channel_transport.datetime',Clock):actual=execute(str(root),str(root),args,owner,transport_factory=transport,invocation=invocation,**common)
  if kind=='partial-seven-bytes':self.assertEqual(len((destination/'repository.json').read_bytes()),7)
  if kind.startswith(('race-','during-get-')):
   self.assertEqual(set(getattr(owner,'preflight_external_changes',{})),{str(destination)})
   self.assertNotIn(str(destination),owner.touched)
   self.assertFalse((destination/'preflight.json').is_file())
  self.assertFalse(record.capture_incomplete);self.assertEqual(actual['exit_code'],old.returncode,actual);self.assertEqual(actual['return_value'],json.loads(old.stdout)) if invocation is not None and old.returncode==0 else self.assertEqual(actual['stdout'].encode(),old.stdout)
  if actual['kernel_exception'] is None:self.assertEqual(actual['stderr'].encode(),old.stderr)
  else:
   e=actual['kernel_exception'];self.assertTrue(old.stderr.endswith((e['type']+': '+e['message']+'\n').encode()),(actual,old.stderr[-3000:]))
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
  clocks=[r for r in events if r.get('action')=='personal-capture-clock' and r.get('kind')=='intent'];self.assertEqual(len(clocks),1 if kind in ('normal','maximum-archive','bad-digest','api-default','api-empty-clock','race-directory','race-file','during-get-directory','during-get-file','partial-seven-bytes') else 0)
  if kind in ('normal','maximum-archive','api-default','api-explicit','api-empty-clock'):
   paths=[row['path'] for row in owner.writes];self.assertEqual(paths[-1],str(destination/'preflight.json'));self.assertIn(str(destination/'artifact.zip'),paths)
  cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};seen=set()
  def inert(ref):
   raw=cache[ref['sha256']];self.assertEqual(len(raw),ref['bytes']);self.assertEqual(hashlib.sha256(raw).hexdigest(),ref['sha256']);seen.add(ref['sha256']);return raw
  shutil.rmtree(root);shutil.rmtree(tools);replay=ReplayIO(events,inert,mode,str(root))
  def pure_transport(io,source,emit):return ReplayPreflightTransport(io,source,emit_stderr=emit)
  with patch('os.open',side_effect=AssertionError('No native IO')),patch('subprocess.Popen',side_effect=AssertionError('No programs')),patch('lib.providers.personal_channel_transport.datetime',side_effect=AssertionError('No clock')):
   pure=execute(str(root),str(root),args,replay,transport_factory=pure_transport,invocation=invocation,**common);replay.finish()
  self.assertEqual(getattr(replay,'preflight_external_changes',{}),getattr(owner,'preflight_external_changes',{}))
  self.assertEqual(pure,actual);self.assertEqual(replay.files,owner.files);self.assertEqual(replay.writes,owner.writes);self.assertEqual(replay.projected_changes,owner.projected_changes)
  self.assertEqual(seen,set(cache))
  for sha in seen:blob({'sha256':sha,'bytes':len(cache[sha])})
  self.assertTrue(closed())
 def test_whole_original_actual_competing_entries_during_GET_and_at_exclusive_mkdir(self):
  for kind in ('race-directory','race-file','during-get-directory','during-get-file'):
   with self.subTest(kind=kind):self.compare(kind,True)
 def test_whole_original_partial_exclusive_write_keeps_exact_seven_bytes_and_no_completion_manifest(self):
  self.compare('partial-seven-bytes',True)
 def test_whole_original_collect_API_default_explicit_empty_clock_and_explicit_None_fetch(self):
  for kind in ('api-default','api-explicit','api-empty-clock','api-none-fetch'):
   for native in (True,False):
    with self.subTest(kind=kind,native=native):self.compare(kind,native)
 def test_complete_original_collect_and_main_AST_with_only_declared_port_bindings(self):
  original=ast.parse((FIXTURE/'live_evidence.py.txt').read_bytes());old=next(v for v in original.body if isinstance(v,ast.FunctionDef) and v.name=='collect_preflight')
  current=ast.parse((ROOT/'scripts/lib/providers/lifecycle_preflight.py').read_bytes());cls=next(v for v in current.body if isinstance(v,ast.ClassDef));new=copy.deepcopy(next(v for v in cls.body if isinstance(v,ast.FunctionDef) and v.name=='collect_preflight'))
  self.assertEqual(new.args.args.pop(0).arg,'self')
  self.assertEqual(ast.unparse(new.body[0]),'if repo_root is _OMITTED:\n    repo_root = self.context.root')
  self.assertEqual(ast.unparse(new.body[1]),'if fetch is _OMITTED:\n    fetch = self.default_fetch')
  new.body=new.body[2:];self.assertEqual([ast.unparse(v) for v in new.args.kw_defaults],['_OMITTED','_OMITTED','None']);new.args.kw_defaults=copy.deepcopy(old.args.kw_defaults)
  clock=next(v.value for v in old.body if isinstance(v,ast.Assign) and isinstance(v.targets[0],ast.Name) and v.targets[0].id=='at').values[1]
  bindings={'self.context.preparation.validate_preparation':'validate_preparation','self.context.contracts.require':'require','self.path_factory':'Path','self.context.adapter.strict_json':'strict_json','self.context.adapter.json_bytes':'json_bytes','self.positive_id':'positive_id','self.verify_capture':'verify_capture','self.sha':'sha','self.default_fetch':'github_get','self.argument_parser':'argparse.ArgumentParser','self.description':'__doc__','self.provider.collect_preflight':'collect_preflight','self.provider.replay_capture':'replay_capture'}
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
  self.assertEqual(ast.dump(Restore().visit(new),include_attributes=False),ast.dump(old,include_attributes=False))
  program=ast.parse((FIXTURE/'preflight_lifecycle_live_evidence.py.txt').read_bytes());old=next(v for v in program.body if isinstance(v,ast.FunctionDef) and v.name=='main')
  current=ast.parse((ROOT/'scripts/lib/lifecycle_preflight_program.py').read_bytes());cls=next(v for v in current.body if isinstance(v,ast.ClassDef));new=copy.deepcopy(next(v for v in cls.body if isinstance(v,ast.FunctionDef) and v.name=='main'));self.assertEqual(new.args.args.pop(0).arg,'self')
  self.assertEqual(ast.dump(Restore().visit(new),include_attributes=False),ast.dump(old,include_attributes=False))
 def test_whole_original_native_and_private_capture_query_order_filebytes_modes_and_pure_replay(self):
  for native in (True,False):
   with self.subTest(native=native):self.compare(native=native)
 def test_whole_original_maximum_10MiB_archive_exceeds_old_personal_budget_without_weakening_it(self):
  for native in (True,False):
   with self.subTest(native=native):self.compare('maximum-archive',native)
  from lib.providers.personal_channel_process import NativeReadProcess
  from lib.personal_channel_process import MAX_STDOUT
  from lib.requirement_validation_budget import InputAdmissionError
  self.assertEqual(MAX_STDOUT,8*1024**2)
  process=NativeReadProcess()
  with self.assertRaises(InputAdmissionError):
   process.run([sys.executable,'-B','-c',"import sys;sys.stdout.buffer.write(b'x'*(8*1024**2+1))"],str(ROOT),dict(os.environ),90)
  self.assertTrue(process.observation['stream_budget_exceeded'])
 def test_whole_original_existing_bundle_replay_does_not_get_or_sample_clock(self):
  for native in (True,False):
   with self.subTest(native=native):self.compare('replay',native)
 def test_whole_original_parser_help_unknown_and_missing_output(self):
  for kind in ('help','unknown','missing-output'):
   for native in (True,False):
    with self.subTest(kind=kind,native=native):self.compare(kind,native)
 def test_whole_original_preparation_output_run_race_digest_json_and_missing_artifact_errors(self):
  for kind in ('existing','wrong-directory','rerun','metadata-race','bad-digest','invalid-json','missing-artifact'):
   for native in (True,False):
    with self.subTest(kind=kind,native=native):self.compare(kind,native)
if __name__=='__main__':unittest.main()
