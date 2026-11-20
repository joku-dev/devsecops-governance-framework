"""Whole application routing, source/node binding and closed private records."""
from contextlib import redirect_stdout,redirect_stderr
from pathlib import Path
from unittest.mock import patch
import hashlib,io,json,os,shutil,subprocess,sys,unittest

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.synthetic_lifecycle_application import generate,inspect,run,PROFILE,request_valid
from lib.synthetic_lifecycle_ports import current_source,read_record,encode
from lib.portable.runtime import source_digest
from lib.functional_parity import git_read
import test_v2_synthetic_lifecycle_context as reference
from test_v2_synthetic_lifecycle_reports import REFERENCES,frozen


class WholeSyntheticLifecycleApplication(unittest.TestCase):
 def setUp(self):
  self.fixture=reference.WholeSyntheticLifecycleContext('test_entire_default_index_all_original_bytes_and_streams');self.fixture.setUp();self.addCleanup(self.fixture.doCleanups);self.data=self.fixture.root
  self.instance=self.data.parent/'instance';self.instance.mkdir(mode=0o700)
  self.settings={'node_id':'e'*32,'source_revision':git_read(ROOT,'rev-parse','HEAD').decode().strip(),'runtime_source_digest':source_digest()}
 def execute(self,name='index',*,native=False,args=None,**extra):
  return generate({'generator':name,'source_worktree':str(self.data),'write_selected_reports':native,'legacy_arguments':self.fixture.arguments(name) if args is None else args,**extra},self.instance,self.settings)
 def test_all_five_private_application_choices_replay_complete_candidates_without_source_changes(self):
  before=self.fixture.snapshot()[0]
  for name in REFERENCES:
   with self.subTest(generator=name):
    receipt,result=self.execute(name);self.assertEqual(receipt['state'],'complete');self.assertEqual(receipt['original_exit_code'],0);self.assertTrue(receipt['journal_terminal_written'])
    self.assertFalse(receipt['source_output_paths_observed']);self.assertFalse(receipt['official_acceptance']);self.assertEqual(self.fixture.snapshot()[0],before)
    self.assertEqual(set(result['successful_outputs']),{str(self.data/path) for path in reference.TARGETS[name]})
    self.assertTrue(result['private_projected_changes']);checked=inspect(receipt['record_root'],node=self.settings)
    self.assertTrue(checked['retained_declared_replay_consistent']);self.assertFalse(checked['native_source_or_exports_repeated']);self.assertEqual(checked['private_creation_mask'],0o077)
 def test_native_original_second_file_failure_keeps_first_file_and_whole_result(self):
  args=['--as-of',reference.AT,'--report',str(self.data/'generated/reports')]
  old=subprocess.run([sys.executable,str(self.data/'scripts'/REFERENCES['pilot'][0]),*args],cwd=self.data,capture_output=True,timeout=120,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(self.data/'scripts')})
  self.assertEqual(old.returncode,1);receipt,result=self.execute('pilot',native=True,args=args)
  self.assertEqual(receipt['state'],'complete');self.assertEqual(receipt['original_exit_code'],1);self.assertEqual(len(result['successful_outputs']),1)
  kernel=result['kernel_result'];self.assertEqual(kernel['stdout'].encode(),old.stdout);self.assertEqual(kernel['kernel_exception']['type'],'IsADirectoryError');self.assertTrue(old.stderr.decode().endswith('IsADirectoryError: '+kernel['kernel_exception']['message']+'\n'))
  checked=inspect(receipt['record_root']);self.assertEqual(len(checked['source_output_paths_observed']),1);self.assertFalse(checked['private_projected_changes'])
 def test_complete_original_help_zero_and_parser_two_need_no_selected_source(self):
  for name in REFERENCES:
   for args,code in ((['--help'],0),(['--unknown'],2)):
    with self.subTest(generator=name,args=args):
     receipt,result=self.execute(name,args=args,source_worktree='/axiom-no-such-selected-data')
     self.assertEqual(receipt['state'],'complete');self.assertEqual(receipt['original_exit_code'],code);self.assertFalse(result['successful_outputs']);self.assertEqual(result['kernel_result']['original_exit_signal'],{'type':'SystemExit','value':code})
     self.assertEqual(inspect(receipt['record_root'])['original_exit_code'],code)
 def test_private_alias_is_incomplete_with_no_original_verdict(self):
  path=self.data/'model/governance/lifecycle/synthetic-grs002-profile.json';raw=path.read_bytes();target=self.data/'profile-copy';target.write_bytes(raw);path.unlink();path.symlink_to(target)
  receipt,result=self.execute();self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code']);self.assertIsNone(result);self.assertTrue(receipt['journal_terminal_written'])
  self.assertFalse(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
 def test_explicit_product_export_is_incomplete_and_leaves_product_bytes_unchanged(self):
  target=ROOT/'scripts/lib/synthetic_lifecycle_application.py';raw=target.read_bytes()
  receipt,result=self.execute(native=True,args=['--as-of',reference.AT,'--output',str(target)])
  self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code']);self.assertIsNone(result);self.assertEqual(target.read_bytes(),raw)
  self.assertTrue(receipt['source_effects_may_be_partial']);self.assertFalse(receipt['source_output_paths_observed'])
 def test_deleted_sources_replay_without_native_ports_and_foreign_node_is_rejected(self):
  receipt,_=self.execute();shutil.rmtree(self.data)
  with patch('lib.synthetic_lifecycle_application.NativeIO',side_effect=AssertionError('No selected source or exports')),patch('subprocess.Popen',side_effect=AssertionError('No native program')):self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
  with self.assertRaisesRegex(ValueError,'foreign_node'):inspect(receipt['record_root'],node={**self.settings,'node_id':'a'*32})
 def test_cli_receipt_legacy_streams_node_inspect_and_instance_free_replay(self):
  base=['generate','--profile',PROFILE,'--generator','index','--source-worktree',str(self.data),'--','--as-of',reference.AT];stdout,stderr=io.StringIO(),io.StringIO()
  with redirect_stdout(stdout),redirect_stderr(stderr):code=run(base,self.instance,self.settings)
  self.assertEqual(code,0);receipt=json.loads(stdout.getvalue())
  for command in ('inspect','replay'):
   output=io.StringIO()
   with redirect_stdout(output):code=run([command,'--record',receipt['record_root']],*([] if command=='replay' else [self.instance,self.settings]))
   self.assertEqual(code,0);self.assertTrue(json.loads(output.getvalue())['retained_declared_replay_consistent'])
  old=subprocess.run([sys.executable,str(self.data/'scripts'/REFERENCES['index'][0]),'--help'],cwd=self.data,capture_output=True,timeout=30)
  output,error=io.StringIO(),io.StringIO()
  with redirect_stdout(output),redirect_stderr(error):code=run(['generate','--profile',PROFILE,'--generator','index','--source-worktree',str(self.data),'--format','legacy','--','--help'],self.instance,self.settings)
  self.assertEqual(code,old.returncode);self.assertEqual(output.getvalue().encode(),old.stdout);self.assertEqual(error.getvalue().encode(),old.stderr)
 def reseal(self,root,events,value):
  previous='0'*64
  for index,event in enumerate(events):
   raw=encode({'sequence':index,'previous':previous,'value':event});(root/'events'/f'{index:08}.json').write_bytes(raw);previous=hashlib.sha256(raw).hexdigest()
  value['event_count']=len(events);value['event_tip']=previous;(root/'result.json').write_bytes(encode(value))
 def test_source_authority_request_result_orphan_and_resealed_projection_tampering_rejected(self):
  for attack in ('source','authority','authority-type','request','result','orphan','projection'):
   with self.subTest(attack=attack):
    receipt,_=self.execute();root=Path(receipt['record_root']);request,source,value,events,blob,_=read_record(root)
    if attack=='source':source['source_digest']='0'*64;(root/'source.json').write_bytes(encode(source))
    elif attack=='authority':value['official_acceptance']=True;(root/'result.json').write_bytes(encode(value))
    elif attack=='authority-type':value['authority_transferred']=0;(root/'result.json').write_bytes(encode(value))
    elif attack=='request':request['generator']='viewer';(root/'request.json').write_bytes(encode(request))
    elif attack=='result':value['result']['kernel_result']['stdout']+='forged';(root/'result.json').write_bytes(encode(value))
    elif attack=='orphan':raw=b'orphan';(root/'blobs'/hashlib.sha256(raw).hexdigest()).write_bytes(raw)
    else:
     next(row for row in events if row['kind']=='lifecycle-private-context')['native_source_effects']=True;self.reseal(root,events,value)
    with self.assertRaises((ValueError,TypeError,KeyError)):inspect(root)
 def test_request_generation_binding_and_missing_closure_rejected_before_records(self):
  request={'schema_version':1,'profile':PROFILE,'generator':'index','source_label':str(self.data),'cwd_label':str(self.data),'argv':['--as-of',reference.AT],'export_mode':'private-candidate','resources':[]}
  for change in ({'schema_version':True},{'generator':'live-pilot'},{'argv':['bad\n']},{'argv':['x'*8193]},{'source_label':'//changed'},{'extra':False},{'export_mode':'automatic-publish'},{'resources':None},{'resources':[{'uri':'bad uri','label':str(self.data)}]},{'resources':[{'uri':'urn:x','label':str(self.data)},{'uri':'urn:x','label':str(self.data)}]},{'resources':[{'uri':'urn:x','label':'relative'}]},{'resources':[{'uri':'urn:'+str(n),'label':str(self.data)} for n in range(129)]}):
   with self.subTest(change=change),self.assertRaises(ValueError):request_valid({**request,**change})
  for change in ({'source_revision':'0'*40},{'runtime_source_digest':'0'*64},{'node_id':'invalid'}):
   with self.subTest(change=change),self.assertRaisesRegex(ValueError,'synthetic_lifecycle_node_'):current_source({**self.settings,**change})
  with patch('lib.synthetic_lifecycle_ports.selected_paths',return_value=[]),self.assertRaisesRegex(ValueError,'closure_not_registered'):current_source(self.settings)
  self.assertFalse((self.instance/'state').exists())
 def test_interrupted_journal_is_incomplete_and_never_retried_implicitly(self):
  with patch('lib.synthetic_lifecycle_application.Record.finish',side_effect=OSError('injected terminal storage failure')):receipt,result=self.execute(args=['--help'])
  self.assertEqual(receipt['state'],'incomplete');self.assertFalse(receipt['journal_terminal_written']);self.assertIsNone(receipt['original_exit_code']);self.assertEqual(result['exit_code'],0)
  with self.assertRaisesRegex(ValueError,'record_members_changed'):inspect(receipt['record_root'])
 def test_overlapping_source_and_instance_are_rejected_before_journal_writes(self):
  before=list(self.instance.iterdir())
  with self.assertRaisesRegex(ValueError,'source_instance_overlap'):self.execute(source_worktree=str(self.instance))
  self.assertEqual(list(self.instance.iterdir()),before)
  nested=self.data/'instance';nested.mkdir(mode=0o700)
  with self.assertRaisesRegex(ValueError,'source_instance_overlap'):generate({'generator':'index','source_worktree':str(self.data),'legacy_arguments':['--help']},nested,self.settings)
  self.assertFalse(list(nested.iterdir()))
 def test_unselected_external_schema_never_uses_implicit_HTTP_and_has_no_original_verdict(self):
  (self.data/'schemas/governance-repository-security-report.schema.json').write_bytes(b'{"$ref":"https://example.invalid/selected-schema"}')
  for native in (False,True):
   with self.subTest(native=native),patch('urllib.request.urlopen',side_effect=AssertionError('No implicit HTTP')) as network:
    receipt,result=self.execute(native=native);self.assertFalse(network.called)
    self.assertEqual(receipt['state'],'incomplete');self.assertIsNone(receipt['original_exit_code']);self.assertEqual(receipt['exit_code'],2)
    self.assertFalse(receipt['source_output_paths_observed']);self.assertFalse(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
 def test_selected_external_schema_matches_whole_original_and_replays_after_all_resources_deleted(self):
  import tempfile
  uri='https://example.invalid/selected-schema';raw=b'{"type":"object"}'
  (self.data/'schemas/governance-repository-security-report.schema.json').write_bytes(json.dumps({'$ref':uri}).encode())
  selected=self.data.parent/'selected-schema.json';selected.write_bytes(raw);before,dirs=self.fixture.snapshot()
  # Whole unchanged original CLI, with only its selected HTTP response mocked
  # inside its own process. The V2 application must never use that transport.
  original=self.data/'scripts'/REFERENCES['index'][0]
  driver="import io,runpy,sys; from unittest.mock import patch; path=sys.argv[1]; sys.argv=sys.argv[1:]; transport=patch('urllib.request.urlopen',side_effect=lambda *a,**k:io.BytesIO("+repr(raw)+")); transport.start(); runpy.run_path(path,run_name='__main__')"
  old=subprocess.run([sys.executable,'-B','-c',driver,str(original),*self.fixture.arguments('index')],cwd=self.data,capture_output=True,timeout=120,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','PYTHONPATH':str(self.data/'scripts')})
  self.assertEqual(old.returncode,0,old.stderr[-2000:]);expected,after_dirs=self.fixture.snapshot()
  for p in set(expected)-set(before):Path(p).unlink()
  for p,value in before.items():
   if expected.get(p)!=value:Path(p).write_bytes(value)
  for p in sorted(after_dirs-dirs,key=lambda p:len(Path(p).parts),reverse=True):Path(p).rmdir()
  with patch('urllib.request.urlopen',side_effect=AssertionError('No capture or replay HTTP')) as network:
   receipt,result=self.execute(schema_resource=[[uri,str(selected)]]);self.assertFalse(network.called)
  self.assertEqual(receipt['state'],'complete');self.assertEqual(result['kernel_result']['stdout'].encode(),old.stdout);self.assertEqual(result['kernel_result']['stderr'], '');self.assertEqual(self.fixture.snapshot()[0],before)
  _,_,retained,events,blob,_=read_record(receipt['record_root']);self.assertEqual({p:blob(ref) for p,ref in retained['result']['successful_outputs'].items()},{str(self.data/p):expected[str(self.data/p)] for p in reference.TARGETS['index']})
  self.assertTrue(any(row.get('selection',{}).get('path')==str(selected) for row in events));selected.unlink();shutil.rmtree(self.data)
  with patch('urllib.request.urlopen',side_effect=AssertionError('No replay HTTP')),patch('lib.providers.synthetic_lifecycle_io.NativeIO.read',side_effect=AssertionError('No selected source')),patch('subprocess.Popen',side_effect=AssertionError('No native program')):
   checked=inspect(receipt['record_root']);self.assertTrue(checked['retained_declared_replay_consistent']);self.assertEqual(checked['original_exit_code'],0)
 def test_source_facades_export_entire_original_apis_and_legacy_adapters_keep_whole_original_bytes(self):
  import importlib,ast
  from lib.v2_source import selected_paths
  policy=json.loads((ROOT/'config/axiom-v2-distribution.json').read_bytes());selected=set(selected_paths(ROOT))
  for name,(filename,cls,sha) in REFERENCES.items():
   with self.subTest(generator=name):
    provider=ROOT/'scripts/lib/providers'/('legacy_synthetic_lifecycle_'+name+'.py');self.assertEqual(provider.read_bytes(),frozen(name)[1]);self.assertEqual(hashlib.sha256(provider.read_bytes()).hexdigest(),sha)
    for path in (provider,ROOT/'scripts'/filename):
     relative=path.relative_to(ROOT).as_posix();self.assertIn(relative,policy['retired_entrypoints']);self.assertNotIn(relative,policy['python_files']);self.assertNotIn(relative,selected)
    module=importlib.import_module(filename.removesuffix('.py'));legacy=importlib.import_module('lib.providers.legacy_synthetic_lifecycle_'+name);self.assertIs(module,legacy)
    for node in ast.parse(frozen(name)[1]).body:
     if isinstance(node,ast.FunctionDef):self.assertTrue(callable(getattr(module,node.name)))


if __name__=='__main__':unittest.main()
