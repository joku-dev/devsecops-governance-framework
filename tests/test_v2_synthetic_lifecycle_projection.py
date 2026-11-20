"""Private preimages and logical effects vs actual whole V1 execution."""
from pathlib import Path
from unittest.mock import patch
import argparse,copy,hashlib,io as pythonio,json,os,shutil,stat,subprocess,sys,tempfile,unittest

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.providers.synthetic_lifecycle_storage import Record,read_record
from lib.providers.synthetic_lifecycle_io import NativeIO
from lib.synthetic_lifecycle_io import ReplayIO
from lib.synthetic_lifecycle_context import execute,LifecyclePaths
from lib.synthetic_lifecycle_reports import SyntheticOverview,SyntheticViewer
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from jsonschema import Draft202012Validator
import test_v2_synthetic_lifecycle_context as reference
from test_v2_synthetic_lifecycle_reports import REFERENCES


class PrivateLifecycleProjection(unittest.TestCase):
 def setUp(self):
  temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.work=Path(temporary.name).resolve();self.data=self.work/'data';self.data.mkdir(mode=0o700);self.private=self.work/'private';self.private.mkdir(mode=0o700)
 def capture(self):
  request={'mode':'private-candidate','cwd_label':str(self.data)};record=Record(self.private/'records',request,{'projection_is_not_native_export':True});record.append({'kind':'execution-intent','request':request})
  return record,NativeIO(record,mode='private-candidate',cwd=str(self.data),private_state=self.private,product_root=ROOT)
 def close(self,record,io,code=0):record.finish('complete',{'exit_code':code,'candidate_changes':io.projected_changes},io.touched);return record.root
 def replay(self,root):
  request,source,result,events,blob,closed=read_record(root);return ReplayIO(events,blob,'private-candidate',request['cwd_label']),closed
 def test_new_nested_candidates_are_readable_without_creating_selected_paths(self):
  record,io=self.capture();directory=str(self.data/'new'/'nested');file=str(Path(directory)/'report')
  with patch('lib.providers.synthetic_lifecycle_output.NativeOutput.mkdir_one',side_effect=AssertionError('No selected mkdir')),patch('lib.providers.synthetic_lifecycle_output.NativeOutput.write_chunk',side_effect=AssertionError('No selected write')):
   io.mkdir(directory,0o777,True,True,directory);io.write_bytes(file,b'candidate',file)
   self.assertTrue(io.probe(file,'is_file',file));self.assertEqual(io.read(file,file),b'candidate');self.assertEqual(io.iterdir(directory,directory),['report'])
  self.assertFalse((self.data/'new').exists());self.assertFalse(io.touched);self.assertEqual(io.projected_changes[file]['mode'],0o600)
  root=self.close(record,io);shutil.rmtree(self.data);replay,closed=self.replay(root)
  replay.mkdir(directory,0o777,True,True,directory);replay.write_bytes(file,b'candidate',file);self.assertTrue(replay.probe(file,'is_file',file));self.assertEqual(replay.read(file,file),b'candidate');self.assertEqual(replay.iterdir(directory,directory),['report'])
  replay.finish();self.assertTrue(closed());self.assertEqual(io.projected_changes,replay.projected_changes);self.assertFalse(replay.touched)
 def test_existing_directory_membership_merges_overlay_without_touching_source(self):
  original=self.data/'original';original.write_bytes(b'original');record,io=self.capture();file=str(self.data/'added');directory=str(self.data)
  io.write_bytes(file,b'new',file);names=io.iterdir(directory,directory);self.assertEqual(set(names),{'original','added'});self.assertEqual([p.name for p in self.data.iterdir()],['original'])
  root=self.close(record,io);shutil.rmtree(self.data);replay,closed=self.replay(root);replay.write_bytes(file,b'new',file);self.assertEqual(replay.iterdir(directory,directory),names);replay.finish();self.assertTrue(closed())
 def test_original_unicode_error_truncates_only_candidate_and_keeps_source_preimage(self):
  path=self.data/'existing';path.write_bytes(b'original');name=str(path);value='bad\ud800'
  with self.assertRaises(UnicodeEncodeError) as original:path.write_text(value,encoding='utf-8')
  path.write_bytes(b'original');record,io=self.capture()
  with self.assertRaises(UnicodeEncodeError) as actual:io.write_text(name,value,'utf-8',None,name)
  self.assertEqual(str(actual.exception),str(original.exception));self.assertEqual(path.read_bytes(),b'original');self.assertEqual(io.read(name,name),b'');self.assertFalse(io.touched)
  root=self.close(record,io,1);shutil.rmtree(self.data);replay,closed=self.replay(root)
  with self.assertRaises(UnicodeEncodeError):replay.write_text(name,value,'utf-8',None,name)
  self.assertEqual(replay.read(name,name),b'');replay.finish();self.assertTrue(closed())
 def test_existing_read_only_file_preserves_original_permission_failure(self):
  path=self.data/'read-only';path.write_bytes(b'original');path.chmod(0o444);name=str(path)
  with self.assertRaises(PermissionError) as original:path.write_bytes(b'bad')
  record,io=self.capture()
  with self.assertRaises(PermissionError) as actual:io.write_bytes(name,b'bad',name)
  self.assertEqual(str(actual.exception),str(original.exception));self.assertFalse(io.projected_changes);self.assertEqual(path.read_bytes(),b'original')
  root=self.close(record,io,1);shutil.rmtree(self.data);replay,closed=self.replay(root)
  with self.assertRaises(PermissionError):replay.write_bytes(name,b'bad',name)
  replay.finish();self.assertTrue(closed())
 def test_changed_actual_preimage_after_projection_is_incomplete(self):
  path=self.data/'existing';path.write_bytes(b'original');name=str(path);record,io=self.capture();io.write_bytes(name,b'candidate',name);path.write_bytes(b'external change')
  with self.assertRaises(InputAdmissionError):io.write_bytes(name,b'next candidate',name)
  self.assertTrue(record.capture_incomplete);self.assertEqual(path.read_bytes(),b'external change')
 def test_projection_context_cannot_be_relabelled_as_native_effect(self):
  record,io=self.capture();name=str(self.data/'report');io.write_bytes(name,b'candidate',name);root=self.close(record,io)
  request,source,result,events,blob,_=read_record(root);changed=copy.deepcopy(events);row=next(v for v in changed if v['kind']=='lifecycle-private-context');row['native_source_effects']=True
  replay=ReplayIO(changed,blob,'private-candidate',str(self.data))
  with self.assertRaises(IntegrityError):replay.write_bytes(name,b'candidate',name)
 def test_default_read_text_codec_is_retained_and_does_not_use_replay_locale(self):
  path=self.data/'text';path.write_text('Änderung 日本語\n',encoding='utf-8');record,io=self.capture();paths=LifecyclePaths(str(self.data),str(self.data),io);logical=paths.path(str(path));expected=logical.read_text()
  root=self.close(record,io);shutil.rmtree(self.data);replay,closed=self.replay(root);paths=LifecyclePaths(str(self.data),str(self.data),replay)
  constructor=pythonio.TextIOWrapper
  def explicit_codec(*args,**kwargs):
   if kwargs.get('encoding') is None:raise AssertionError('Replay must supply the retained codec to the decoder')
   return constructor(*args,**kwargs)
  with patch('locale.getencoding',side_effect=AssertionError('No replay locale')),patch('io.TextIOWrapper',side_effect=explicit_codec):self.assertEqual(paths.path(str(path)).read_text(),expected)
  replay.finish();self.assertTrue(closed())


class WholePrivateLifecycleProjection(unittest.TestCase):
 def helper_api(self,root,io):
  paths=LifecyclePaths(str(root),str(root),io);logical=paths.path(str(root));context=RepositoryLifecycle(logical,validator_class=Draft202012Validator,path_factory=paths.path)
  options={'path_factory':paths.path,'argument_parser':argparse.ArgumentParser,'argv':[]};overview=SyntheticOverview(logical,context,**options);context.governance_lifecycle_overview=overview;viewer=SyntheticViewer(logical,context,overview=overview,**options)
  index=overview.generate(as_of=reference.AT);self.assertEqual(overview.validate_overview(),index);html=viewer.generate();self.assertEqual(viewer.validate_viewer(),html);self.assertEqual(viewer.validate_viewer(overview=index),html)
  failures=[];report=logical/overview.REPORT;report.write_text('changed report',encoding='utf-8')
  try:overview.validate_overview()
  except Exception as error:failures.append({'type':type(error).__name__,'message':str(error)})
  else:self.fail('Modified report must fail whole original validation')
  report.write_text(overview.render_report(index),encoding='utf-8');(logical/viewer.OUTPUT).write_text('changed viewer',encoding='utf-8')
  try:viewer.validate_viewer(overview=index)
  except Exception as error:failures.append({'type':type(error).__name__,'message':str(error)})
  else:self.fail('Modified viewer must fail whole original validation')
  return {'exit_code':0,'index':index,'html_sha256':hashlib.sha256(html.encode()).hexdigest(),'failures':failures}
 def compare(self,name,args_factory=None,code=0):
  fixture=reference.WholeSyntheticLifecycleContext('test_entire_default_index_all_original_bytes_and_streams');fixture.setUp();self.addCleanup(fixture.doCleanups);root=fixture.root;before,dirs=fixture.snapshot();modes={str(p):stat.S_IMODE(p.stat().st_mode) for p in root.rglob('*')}
  args=fixture.arguments(name) if args_factory is None else args_factory(root)
  old=subprocess.run([sys.executable,str(root/'scripts'/REFERENCES[name][0]),*args],cwd=root,capture_output=True,timeout=120,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},umask=0o077)
  self.assertEqual(old.returncode,code,old.stderr[-2000:]);expected,after_dirs=fixture.snapshot()
  for name_added in set(expected)-set(before):Path(name_added).unlink()
  for path,raw in before.items():
   if expected.get(path)!=raw:Path(path).write_bytes(raw)
  for path in sorted(after_dirs-dirs,key=lambda value:len(Path(value).parts),reverse=True):Path(path).rmdir()
  private=root.parent/'private';private.mkdir(mode=0o700);request={'mode':'private-candidate','source_label':str(root),'cwd_label':str(root),'generator':name,'argv':args};record=Record(private,request,{'original_source_only_used_by_test_oracle':True});record.append({'kind':'execution-intent','request':request});io=NativeIO(record,mode='private-candidate',cwd=str(root),private_state=private,product_root=ROOT)
  with patch('subprocess.Popen',side_effect=AssertionError('No program in projection')),patch('lib.providers.synthetic_lifecycle_output.NativeOutput.mkdir_one',side_effect=AssertionError('No selected mkdir')),patch('lib.providers.synthetic_lifecycle_output.NativeOutput.write_chunk',side_effect=AssertionError('No selected write')):actual=execute(str(root),str(root),name,args,io,validator_class=Draft202012Validator)
  self.assertEqual(actual['exit_code'],code);self.assertEqual(actual['stdout'].encode(),old.stdout)
  if code==0:self.assertIsNone(actual['kernel_exception']);self.assertEqual(actual['stderr'].encode(),old.stderr)
  else:
   error=actual['kernel_exception'];self.assertIsNotNone(error);self.assertTrue(old.stderr.decode().endswith(error['type']+': '+error['message']+'\n'),(error,old.stderr[-2000:]))
  self.assertEqual(fixture.snapshot()[0],before);self.assertEqual({str(p):stat.S_IMODE(p.stat().st_mode) for p in root.rglob('*')},modes);self.assertFalse(io.touched)
  for path,ref in io.files.items():self.assertEqual(io.projection.resolve(ref),expected[path])
  self.assertTrue(io.files);record.finish('complete',actual,io.touched);request,source,result,events,blob,closed=read_record(record.root);replay=ReplayIO(events,blob,'private-candidate',str(root));shutil.rmtree(root)
  with patch('lib.providers.synthetic_lifecycle_io.NativeIO.read',side_effect=AssertionError('No selected source')),patch('subprocess.Popen',side_effect=AssertionError('No replay programs')),patch('locale.getencoding',side_effect=AssertionError('No replay locale')):value=execute(str(root),str(root),name,args,replay,validator_class=Draft202012Validator)
  replay.finish();self.assertEqual(value,actual);self.assertEqual(io.files,replay.files);self.assertEqual(io.projected_changes,replay.projected_changes);self.assertFalse(replay.touched);self.assertTrue(closed())
 def test_all_five_whole_original_CLIs_project_without_source_changes_and_replay(self):
  for name in REFERENCES:
   with self.subTest(generator=name):self.compare(name)
 def test_whole_original_first_index_retained_when_second_output_is_directory(self):self.compare('pilot',lambda root:['--as-of',reference.AT,'--report',str(root/'generated/reports')],1)
 def test_whole_original_nested_custom_candidate_outputs(self):self.compare('exceptions',lambda root:['--as-of',reference.AT,'--output',str(root/'new/deep/index.json'),'--report',str(root/'new/deep/report.md')])
 def test_whole_original_generate_validate_overview_and_viewer_apis_with_changed_candidate_errors(self):
  fixture=reference.WholeSyntheticLifecycleContext('test_entire_default_index_all_original_bytes_and_streams');fixture.setUp();self.addCleanup(fixture.doCleanups);root=fixture.root;before,dirs=fixture.snapshot()
  oracle='''import hashlib,json
from pathlib import Path
import generate_governance_lifecycle_overview as overview
import generate_governance_lifecycle_viewer as viewer
index=overview.generate(as_of="2026-11-15T12:00:00Z")
assert overview.validate_overview()==index
html=viewer.generate()
assert viewer.validate_viewer()==html
assert viewer.validate_viewer(overview=index)==html
failures=[]
Path(overview.REPORT).write_text("changed report",encoding="utf-8")
try:overview.validate_overview()
except Exception as error:failures.append({"type":type(error).__name__,"message":str(error)})
Path(overview.REPORT).write_text(overview.render_report(index),encoding="utf-8")
Path(viewer.OUTPUT).write_text("changed viewer",encoding="utf-8")
try:viewer.validate_viewer(overview=index)
except Exception as error:failures.append({"type":type(error).__name__,"message":str(error)})
print(json.dumps({"exit_code":0,"index":index,"html_sha256":hashlib.sha256(html.encode()).hexdigest(),"failures":failures}))
'''
  old=subprocess.run([sys.executable,'-B','-c',oracle],cwd=root,capture_output=True,timeout=180,env={**os.environ,'PYTHONPATH':str(root/'scripts'),'PYTHONDONTWRITEBYTECODE':'1'})
  self.assertEqual(old.returncode,0,old.stderr[-2000:]);expected=json.loads(old.stdout);self.assertEqual(len(expected['failures']),2);expected_files,_=fixture.snapshot()
  for path in set(expected_files)-set(before):Path(path).unlink()
  for path,raw in before.items():
   if expected_files.get(path)!=raw:Path(path).write_bytes(raw)
  private=root.parent/'private';private.mkdir(mode=0o700);request={'mode':'private-candidate','cwd_label':str(root)};record=Record(private,request,{'whole_original_helper_API_comparison':True});record.append({'kind':'execution-intent','request':request});io=NativeIO(record,mode='private-candidate',cwd=str(root),private_state=private,product_root=ROOT)
  with patch('subprocess.Popen',side_effect=AssertionError('No program in V2 helper API')):actual=self.helper_api(root,io)
  self.assertEqual(actual,expected);self.assertEqual(fixture.snapshot()[0],before);self.assertFalse(io.touched)
  for path,ref in io.files.items():self.assertEqual(io.projection.resolve(ref),expected_files[path])
  record.finish('complete',actual,io.touched);request,source,result,events,blob,closed=read_record(record.root);replay=ReplayIO(events,blob,'private-candidate',str(root));shutil.rmtree(root)
  with patch('locale.getencoding',side_effect=AssertionError('No replay locale')),patch('subprocess.Popen',side_effect=AssertionError('No replay program')):retained=self.helper_api(root,replay)
  replay.finish();self.assertEqual(retained,actual);self.assertEqual(io.projected_changes,replay.projected_changes);self.assertTrue(closed())


if __name__=='__main__':unittest.main()
