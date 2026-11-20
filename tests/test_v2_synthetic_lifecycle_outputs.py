"""Actual owned file effects, original whole CLIs and closed no-native replay."""
from pathlib import Path
from unittest.mock import patch
import copy,errno,json,os,shutil,stat,subprocess,sys,tempfile,unittest

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.providers.synthetic_lifecycle_storage import Record,read_record
from lib.providers.synthetic_lifecycle_io import NativeIO
from lib.synthetic_lifecycle_io import ReplayIO
from lib.synthetic_lifecycle_context import execute
from lib.requirement_review_output import RetainedOutputError
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from jsonschema import Draft202012Validator
import test_v2_synthetic_lifecycle_context as reference
from test_v2_synthetic_lifecycle_reports import REFERENCES


class NativeLifecycleOutput(unittest.TestCase):
 def setUp(self):
  temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.work=Path(temporary.name).resolve()
  self.data=self.work/'data';self.data.mkdir(mode=0o700);self.private=self.work/'private';self.private.mkdir(mode=0o700)
 def capture(self,mode='selected-files'):
  request={'mode':mode,'cwd_label':str(self.data)};record=Record(self.private/'records',request,{'declared_output_test':True});record.append({'kind':'execution-intent','request':request})
  return record,NativeIO(record,mode=mode,cwd=str(self.data),private_state=self.private,product_root=ROOT)
 def close(self,record,io,code=0):record.finish('complete',{'exit_code':code},io.touched);return record.root
 def replay(self,root):
  request,source,result,events,blob,closed=read_record(root);return ReplayIO(events,blob,request['mode'],request['cwd_label']),closed
 def test_nested_mkdir_byte_and_unicode_text_outputs_replay_without_selected_tree(self):
  record,io=self.capture();directory=str(self.data/'new'/'nested');binary=str(Path(directory)/'bytes.bin');text=str(Path(directory)/'text.txt')
  self.assertIsNone(io.mkdir(directory,0o777,True,True,directory));self.assertEqual(io.write_bytes(binary,b'raw\x00\xff\r\n',binary),7)
  self.assertEqual(io.write_text(text,'Änderung\n日本語', 'utf-8',None,text),12)
  expected={p:Path(p).read_bytes() for p in (binary,text)};root=self.close(record,io);shutil.rmtree(self.data)
  replay,closed=self.replay(root)
  with patch('lib.providers.synthetic_lifecycle_output.NativeOutput.mkdir_one',side_effect=AssertionError('No native mkdir')),patch('lib.providers.synthetic_lifecycle_output.NativeOutput.write_chunk',side_effect=AssertionError('No native write')),patch('subprocess.Popen',side_effect=AssertionError('No programs')):
   replay.mkdir(directory,0o777,True,True,directory);replay.write_bytes(binary,b'raw\x00\xff\r\n',binary);replay.write_text(text,'Änderung\n日本語','utf-8',None,text)
  replay.finish();self.assertTrue(closed());self.assertEqual(io.files,replay.files);self.assertEqual(io.writes,replay.writes);self.assertEqual(io.touched,replay.touched)
  self.assertEqual(set(expected),set(replay.files));self.assertFalse(self.data.exists())
 def test_read_overwrite_read_preserves_identity_and_invalidates_only_owned_effect(self):
  path=self.data/'existing';path.write_bytes(b'old');path.chmod(0o640);original=path.stat();name=str(path);directory=str(self.data)
  record,io=self.capture();self.assertEqual(io.read(name,name),b'old');self.assertTrue(io.probe(directory,'is_dir',directory))
  io.write_bytes(name,b'new bytes',name);self.assertEqual(io.read(name,name),b'new bytes');self.assertTrue(io.probe(directory,'is_dir',directory))
  self.assertEqual(path.stat().st_ino,original.st_ino);self.assertEqual(path.stat().st_mode,original.st_mode)
  root=self.close(record,io);shutil.rmtree(self.data);replay,closed=self.replay(root)
  self.assertEqual(replay.read(name,name),b'old');self.assertTrue(replay.probe(directory,'is_dir',directory));replay.write_bytes(name,b'new bytes',name)
  self.assertEqual(replay.read(name,name),b'new bytes');self.assertTrue(replay.probe(directory,'is_dir',directory));replay.finish();self.assertTrue(closed())
 def test_original_open_failure_keeps_existing_directory_and_missing_parent(self):
  directory=self.data/'directory';directory.mkdir();missing=self.data/'absent'/'file'
  for path in (directory,missing):
   with self.subTest(path=path):
    with self.assertRaises(OSError) as original:path.write_bytes(b'content')
    record,io=self.capture();name=str(path)
    with self.assertRaises(type(original.exception)) as actual:io.write_bytes(name,b'content',name)
    self.assertEqual(str(actual.exception),str(original.exception));root=self.close(record,io,1);replay,closed=self.replay(root)
    with self.assertRaises(RetainedOutputError) as retained:replay.write_bytes(name,b'content',name)
    self.assertEqual(retained.exception.original_message,str(original.exception));self.assertEqual(retained.exception.original_type,type(original.exception).__name__)
    self.assertFalse(io.touched);replay.finish();self.assertTrue(closed())
 def test_unicode_encoding_error_retains_original_truncation_and_diagnostic(self):
  old=self.data/'old';old.write_bytes(b'original preimage');name=str(old);value='text\ud800'
  with self.assertRaises(UnicodeEncodeError) as original:old.write_text(value,encoding='utf-8')
  self.assertEqual(old.read_bytes(),b'');old.write_bytes(b'original preimage')
  record,io=self.capture()
  with self.assertRaises(UnicodeEncodeError) as actual:io.write_text(name,value,'utf-8',None,name)
  self.assertEqual(str(actual.exception),str(original.exception));self.assertEqual(old.read_bytes(),b'')
  root=self.close(record,io,1);shutil.rmtree(self.data);replay,closed=self.replay(root)
  with self.assertRaises(RetainedOutputError) as retained:replay.write_text(name,value,'utf-8',None,name)
  self.assertEqual(retained.exception.original_message,str(original.exception));self.assertEqual(io.touched,replay.touched);replay.finish();self.assertTrue(closed())
 def test_partial_native_write_retains_exact_written_prefix_and_failure(self):
  path=self.data/'partial';path.write_bytes(b'old');name=str(path);record,io=self.capture();native=io.output.write_chunk;calls=[]
  def partial(fd,view):
   calls.append(1)
   if len(calls)==1:return native(fd,view[:3])
   raise OSError(errno.EIO,'injected write failure')
  with patch.object(io.output,'write_chunk',side_effect=partial),self.assertRaises(OSError) as actual:io.write_bytes(name,b'abcdef',name)
  self.assertEqual(path.read_bytes(),b'abc');self.assertFalse(io.record.capture_incomplete)
  root=self.close(record,io,1);shutil.rmtree(self.data);replay,closed=self.replay(root)
  with self.assertRaises(RetainedOutputError) as retained:replay.write_bytes(name,b'abcdef',name)
  self.assertEqual(retained.exception.original_message,str(actual.exception));self.assertEqual(io.touched,replay.touched);replay.finish();self.assertTrue(closed())
 def test_actual_read_only_file_is_original_permission_error_without_output_change(self):
  path=self.data/'read-only';path.write_bytes(b'original bytes');path.chmod(0o444);name=str(path)
  with self.assertRaises(PermissionError) as original:path.write_bytes(b'not allowed')
  record,io=self.capture()
  with self.assertRaises(PermissionError) as actual:io.write_bytes(name,b'not allowed',name)
  self.assertEqual(str(actual.exception),str(original.exception));self.assertEqual(path.read_bytes(),b'original bytes');self.assertFalse(io.touched)
  root=self.close(record,io,1);shutil.rmtree(self.data);replay,closed=self.replay(root)
  with self.assertRaises(RetainedOutputError) as retained:replay.write_bytes(name,b'not allowed',name)
  self.assertEqual(retained.exception.original_message,str(original.exception));replay.finish();self.assertTrue(closed())
 def test_mkdir_original_file_collision_and_exist_ok_false(self):
  file=self.data/'file';file.write_bytes(b'unchanged')
  for path in (file,self.data):
   with self.subTest(path=path):
    with self.assertRaises(FileExistsError) as original:path.mkdir(parents=True,exist_ok=False)
    record,io=self.capture();name=str(path)
    with self.assertRaises(FileExistsError) as actual:io.mkdir(name,0o777,True,False,name)
    self.assertEqual(str(original.exception),str(actual.exception));root=self.close(record,io,1);replay,closed=self.replay(root)
    with self.assertRaises(RetainedOutputError):replay.mkdir(name,0o777,True,False,name)
    replay.finish();self.assertTrue(closed());self.assertFalse(io.touched)
 def test_partial_mkdir_retains_created_parent_and_original_failure(self):
  name=str(self.data/'new'/'denied');record,io=self.capture();native=io.output.mkdir_one
  def fail_leaf(anchor,parts,mode):
   if parts[-1]=='denied' and (self.data/'new').exists():raise PermissionError(errno.EACCES,'injected mkdir failure')
   return native(anchor,parts,mode)
  with patch.object(io.output,'mkdir_one',side_effect=fail_leaf),self.assertRaises(PermissionError) as actual:io.mkdir(name,0o777,True,True,name)
  self.assertTrue((self.data/'new').is_dir());self.assertFalse(Path(name).exists());self.assertEqual(set(io.touched),{str(self.data/'new')})
  root=self.close(record,io,1);shutil.rmtree(self.data);replay,closed=self.replay(root)
  with self.assertRaises(RetainedOutputError) as retained:replay.mkdir(name,0o777,True,True,name)
  self.assertEqual(retained.exception.original_message,str(actual.exception));self.assertEqual(io.touched,replay.touched);replay.finish();self.assertTrue(closed())
 def test_none_text_encoding_replays_retained_effective_encoding_without_locale_resolution(self):
  path=self.data/'default-text';name=str(path);record,io=self.capture();io.write_text(name,'Ä\n',None,None,name);expected=path.read_bytes()
  root=self.close(record,io);shutil.rmtree(self.data);replay,closed=self.replay(root)
  with patch('locale.getencoding',side_effect=AssertionError('No replay locale selection')):self.assertEqual(replay.write_text(name,'Ä\n',None,None,name),2)
  replay.finish();self.assertTrue(closed());self.assertEqual(expected,'Ä\n'.encode())
 def test_tampered_progress_or_original_payload_rejected_even_with_new_outer_chain(self):
  record,io=self.capture();name=str(self.data/'report');io.write_bytes(name,b'complete',name);root=self.close(record,io)
  request,source,result,events,blob,_=read_record(root)
  changed=copy.deepcopy(events);after=next(row for row in changed if row['kind']=='lifecycle-write-after');after['progress']['written_bytes']=1
  replay=ReplayIO(changed,blob,'selected-files',str(self.data))
  with self.assertRaises(IntegrityError):replay.write_bytes(name,b'complete',name)
  replay=ReplayIO(events,blob,'selected-files',str(self.data))
  with self.assertRaises(IntegrityError):replay.write_bytes(name,b'different',name)
 def test_replaced_new_output_is_incomplete_even_when_replacement_bytes_are_equal(self):
  path=self.data/'replaced';name=str(path);record,io=self.capture();native=io.output.write_chunk
  def replace(fd,view):
   count=native(fd,view);path.unlink();path.write_bytes(bytes(view));return count
  with patch.object(io.output,'write_chunk',side_effect=replace),self.assertRaises(InputAdmissionError):io.write_bytes(name,b'same bytes',name)
  self.assertTrue(record.capture_incomplete);self.assertEqual(path.read_bytes(),b'same bytes')
 def test_relative_parent_display_label_can_select_output_outside_source(self):
  path=self.work/'outside-output';name=str(path);label='../outside-output';record,io=self.capture()
  self.assertEqual(io.write_bytes(name,b'explicit outside output',label),23);self.assertEqual(path.read_bytes(),b'explicit outside output')
  root=self.close(record,io);path.unlink();replay,closed=self.replay(root);replay.write_bytes(name,b'explicit outside output',label);replay.finish();self.assertTrue(closed());self.assertFalse(path.exists())
 def test_scoped_journal_bytes_fail_closed_before_a_new_effect(self):
  record,io=self.capture();name=str(self.data/'never-written')
  with patch('lib.providers.synthetic_lifecycle_storage.MAX_JOURNAL_BYTES',record.journal_bytes+10),self.assertRaises(InputAdmissionError):io.write_bytes(name,b'payload',name)
  self.assertTrue(record.capture_incomplete);self.assertFalse(Path(name).exists());self.assertFalse(io.touched)
  with self.assertRaisesRegex(ValueError,'incomplete_capture_cannot_complete'):self.close(record,io)
 def test_private_projection_does_not_claim_successful_native_effects(self):
  record,io=self.capture('private-candidate');name=str(self.data/'private-output')
  self.assertEqual(io.write_bytes(name,b'not written',name),11)
  self.assertFalse(Path(name).exists());self.assertFalse(io.touched);self.assertIn(name,io.projected_changes)
  root=self.close(record,io);replay,closed=self.replay(root);replay.write_bytes(name,b'not written',name);replay.finish();self.assertTrue(closed())
 def test_observation_guard_failure_is_incomplete_not_an_original_generator_verdict(self):
  path=self.data/'source';path.write_bytes(b'original');name=str(path);directory=str(self.data)
  for operation in ('read','probe','iterdir','write'):
   with self.subTest(operation=operation):
    record,io=self.capture()
    def fail(*args,**kwargs):raise ValueError('operations_source_ancestor_changed')
    with patch('lib.providers.workbook_import_io.held_root',side_effect=fail),patch('lib.providers.synthetic_lifecycle_io.held_root',side_effect=fail),self.assertRaises(InputAdmissionError):
     if operation=='read':io.read(name,name)
     elif operation=='probe':io.probe(name,'is_file',name)
     elif operation=='iterdir':io.iterdir(directory,directory)
     else:io.write_bytes(name,b'not written',name)
    self.assertTrue(record.capture_incomplete);self.assertEqual(path.read_bytes(),b'original')
    with self.assertRaisesRegex(ValueError,'incomplete_capture_cannot_complete'):self.close(record,io)


class WholeOriginalLifecycleNative(unittest.TestCase):
 def compare(self,name,args=None,code=0):
  fixture=reference.WholeSyntheticLifecycleContext('test_entire_default_index_all_original_bytes_and_streams');fixture.setUp();self.addCleanup(fixture.doCleanups)
  root=fixture.root;before,dirs=fixture.snapshot();args=fixture.arguments(name) if args is None else args(root)
  # Original V1 itself executes from the previously hash-checked frozen source.
  old=subprocess.run([sys.executable,str(root/'scripts'/REFERENCES[name][0]),*args],cwd=root,capture_output=True,timeout=120,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
  self.assertEqual(old.returncode,code,old.stderr[-2000:]);expected,after_dirs=fixture.snapshot()
  expected_modes={str(path):stat.S_IMODE(path.stat().st_mode) for path in root.rglob('*')}
  for path in set(expected)-set(before):Path(path).unlink()
  for path,raw in before.items():
   if expected.get(path)!=raw:Path(path).write_bytes(raw)
  for path in sorted(after_dirs-dirs,key=lambda name:len(Path(name).parts),reverse=True):Path(path).rmdir()
  private=root.parent/'records';private.mkdir(mode=0o700);request={'generator':name,'argv':args,'source_label':str(root),'cwd_label':str(root),'mode':'selected-files'}
  record=Record(private,request,{'whole_original_V1_reference':True});record.append({'kind':'execution-intent','request':request});io=NativeIO(record,mode='selected-files',cwd=str(root),private_state=private,product_root=ROOT)
  with patch('subprocess.Popen',side_effect=AssertionError('V2 executes no selected-source code or native program')):actual=execute(str(root),str(root),name,args,io,validator_class=Draft202012Validator)
  self.assertEqual(actual['exit_code'],old.returncode);self.assertEqual(actual['stdout'].encode(),old.stdout)
  if code==0:self.assertEqual(actual['stderr'].encode(),old.stderr);self.assertIsNone(actual['kernel_exception'])
  else:
   error=actual['kernel_exception'];self.assertIsNotNone(error);self.assertTrue(old.stderr.decode().endswith(error['type']+': '+error['message']+'\n'),(error,old.stderr[-2000:]))
  self.assertEqual(fixture.snapshot()[0],expected);self.assertEqual({str(path):stat.S_IMODE(path.stat().st_mode) for path in root.rglob('*')},expected_modes)
  self.assertFalse(record.capture_incomplete);record.finish('complete',actual,io.touched)
  request,source,retained,events,blob,closed=read_record(record.root);replay=ReplayIO(events,blob,'selected-files',str(root));shutil.rmtree(root)
  with patch('lib.providers.synthetic_lifecycle_io.NativeIO.read',side_effect=AssertionError('No selected source')),patch('lib.providers.synthetic_lifecycle_output.NativeOutput.mkdir_one',side_effect=AssertionError('No native mkdir')),patch('lib.providers.synthetic_lifecycle_output.NativeOutput.write_chunk',side_effect=AssertionError('No native write')),patch('subprocess.Popen',side_effect=AssertionError('No programs')):reconstructed=execute(str(root),str(root),name,args,replay,validator_class=Draft202012Validator)
  replay.finish();self.assertEqual(reconstructed,actual);self.assertEqual(io.files,replay.files);self.assertEqual(io.writes,replay.writes);self.assertEqual(io.touched,replay.touched);self.assertTrue(closed());return actual,io
 def test_whole_five_original_CLIs_native_outputs_and_replay_after_data_deleted(self):
  for name in REFERENCES:
   with self.subTest(generator=name):self.compare(name)
 def test_whole_original_pilot_directory_failure_preserves_first_index(self):
  actual,io=self.compare('pilot',lambda root:['--as-of',reference.AT,'--report',str(root/'generated/reports')],1)
  self.assertEqual(actual['kernel_exception']['type'],'IsADirectoryError');self.assertEqual(len(io.files),1)
 def test_whole_original_custom_nested_output_paths(self):
  self.compare('exceptions',lambda root:['--as-of',reference.AT,'--output',str(root/'custom/deep/index.json'),'--report',str(root/'custom/deep/report.md')])


if __name__=='__main__':unittest.main()
