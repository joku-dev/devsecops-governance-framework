"""Actual bounded input observations, isolated journal and no-native input replay."""
from pathlib import Path
from unittest.mock import patch
import hashlib,json,os,shutil,sys,tempfile,unittest

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.providers.synthetic_lifecycle_storage import Record,read_record,MAX_EVENTS,encode
from lib.providers.sbom_export_storage import MAX_EVENTS as OTHER_PROFILE_EVENTS
from lib.providers.synthetic_lifecycle_io import NativeIO
from lib.synthetic_lifecycle_io import ReplayIO,path_spec
from lib.synthetic_lifecycle_context import execute
from lib.requirement_validation_budget import InputAdmissionError
from lib.requirement_validation_replay import IntegrityError
from jsonschema import Draft202012Validator
import test_v2_synthetic_lifecycle_context as context_reference
from test_v2_synthetic_lifecycle_context import MemoryIO,AT


class LifecycleInputCapture(unittest.TestCase):
 def setUp(self):
  temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.work=Path(temporary.name).resolve()
  self.data=self.work/'data';self.data.mkdir(mode=0o700);self.private=self.work/'private';self.private.mkdir(mode=0o700)
  (self.data/'source.txt').write_bytes(b'Original raw source\r\n')
 def record(self):
  request={'scope':'input-phase-only','source_label':str(self.data),'cwd_label':str(self.data)}
  record=Record(self.private/'records',request,{'declared_engineering_input_test':True});record.append({'kind':'execution-intent','request':request})
  return record,NativeIO(record,mode='private-candidate',cwd=str(self.data),private_state=self.private,product_root=ROOT)
 def close(self,record,value):record.finish('complete',{'exit_code':0,'input_phase_value':value},{});return record.root
 def replay(self,root):
  request,source,result,events,blob,closed=read_record(root);return ReplayIO(events,blob,'private-candidate',request['cwd_label']),result,closed
 def test_raw_read_probe_and_directory_results_reconstructed_after_source_deletion(self):
  record,io=self.record();source=str(self.data/'source.txt');directory=str(self.data)
  values=[io.probe(source,'exists',source),io.probe(source,'is_file',source),io.probe(source,'is_symlink',source),io.iterdir(directory,directory),io.read(source,source)]
  root=self.close(record,{'first':values[:4],'raw_sha256':hashlib.sha256(values[-1]).hexdigest()});shutil.rmtree(self.data)
  replay,result,closed=self.replay(root)
  # Retained journal storage remains available. Selected source observations
  # and external programs are forbidden during reconstruction.
  with patch('lib.providers.synthetic_lifecycle_io.NativeIO.entry',side_effect=AssertionError('No selected filesystem')),patch('lib.providers.synthetic_lifecycle_io.NativeIO.read',side_effect=AssertionError('No selected source')),patch('subprocess.Popen',side_effect=AssertionError('No program')):
   actual=[replay.probe(source,'exists',source),replay.probe(source,'is_file',source),replay.probe(source,'is_symlink',source),replay.iterdir(directory,directory),replay.read(source,source)]
  replay.finish();self.assertEqual(values,actual);self.assertTrue(closed())
 def test_relative_parent_label_retains_original_diagnostic_and_closed_mapping(self):
  record,io=self.record();path=str(self.work/'outside-missing');label='../outside-missing'
  with self.assertRaises(FileNotFoundError) as original:io.read(path,label)
  root=self.close(record,{'type':type(original.exception).__name__,'message':str(original.exception)})
  replay,_,closed=self.replay(root)
  with self.assertRaises(FileNotFoundError) as retained:replay.read(path,label)
  self.assertEqual(str(original.exception),str(retained.exception));replay.finish();self.assertTrue(closed())
  with self.assertRaises(IntegrityError):path_spec(path,'../../outside-missing',str(self.data))
 def test_missing_and_file_directory_probes_preserve_original_false_results(self):
  record,io=self.record();missing=str(self.data/'missing'/'child');source=str(self.data/'source.txt')
  values=[io.probe(missing,k,missing) for k in ('exists','is_file','is_dir','is_symlink')]
  values.append(io.probe(source,'is_dir',source));self.assertEqual(values,[False]*5)
  root=self.close(record,values);replay,_,closed=self.replay(root)
  actual=[replay.probe(missing,k,missing) for k in ('exists','is_file','is_dir','is_symlink')]+[replay.probe(source,'is_dir',source)]
  self.assertEqual(actual,values);replay.finish();self.assertTrue(closed())
 def test_directory_file_error_is_retained_original_error_without_native_reexecution(self):
  record,io=self.record();path=str(self.data/'source.txt')
  with self.assertRaises(NotADirectoryError) as before:io.iterdir(path,path)
  root=self.close(record,{'message':str(before.exception)});replay,_,closed=self.replay(root)
  with self.assertRaises(NotADirectoryError) as after:replay.iterdir(path,path)
  self.assertEqual(str(before.exception),str(after.exception));replay.finish();self.assertTrue(closed())
 def test_probe_then_changed_or_disappeared_source_is_incomplete_not_original_verdict(self):
  for operation in ('changed','missing'):
   with self.subTest(operation=operation):
    path=self.data/'source.txt';path.write_bytes(b'before');record,io=self.record();io.probe(str(path),'is_file',str(path))
    if operation=='changed':path.write_bytes(b'different-content')
    else:path.unlink()
    with self.assertRaises(InputAdmissionError):io.read(str(path),str(path))
 def test_private_source_alias_and_product_export_are_additional_admission_failures(self):
  record,io=self.record();link=self.data/'alias';link.symlink_to(self.data/'source.txt')
  for path in (link,self.private/'secret'):
   with self.subTest(path=path),self.assertRaises(InputAdmissionError):io.probe(str(path),'exists',str(path))
  io=NativeIO(record,mode='selected-files',cwd=str(self.data),private_state=self.private,product_root=ROOT)
  with self.assertRaises(InputAdmissionError):io.check(str(ROOT/'status/example.json'),str(ROOT/'status/example.json'),write=True)
 def test_new_scoped_journal_can_exceed_256_without_weakening_other_profiles(self):
  self.assertEqual(OTHER_PROFILE_EVENTS,256);self.assertEqual(MAX_EVENTS,16384)
  record,io=self.record();path=str(self.data/'source.txt')
  values=[io.probe(path,'is_file',path) for _ in range(100)];root=self.close(record,values)
  replay,_,closed=self.replay(root)
  self.assertEqual(len(replay.events),303);self.assertTrue(all(replay.probe(path,'is_file',path) for _ in values));replay.finish();self.assertTrue(closed())
 def test_coherently_rehashed_probe_boolean_cannot_override_native_metadata(self):
  record,io=self.record();path=str(self.data/'source.txt');io.probe(path,'is_file',path);root=self.close(record,True)
  request,source,value,events,blob,_=read_record(root);returned=events[3];self.assertEqual(returned['kind'],'returned')
  raw=b'false\n';ref={'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw)};(root/'blobs'/ref['sha256']).write_bytes(raw);returned['value']=ref
  previous='0'*64
  for index,event in enumerate(events):
   raw=encode({'sequence':index,'previous':previous,'value':event});(root/'events'/f'{index:08}.json').write_bytes(raw);previous=hashlib.sha256(raw).hexdigest()
  value.update(event_tip=previous,event_count=len(events));(root/'result.json').write_bytes(encode(value))
  replay,_,_=self.replay(root)
  with self.assertRaises(IntegrityError):replay.probe(path,'is_file',path)


class WholeLifecycleInputPhase(unittest.TestCase):
 def test_complete_original_overview_reads_captured_with_inert_outputs_and_no_native_input_replay(self):
  fixture=context_reference.WholeSyntheticLifecycleContext('test_entire_default_three_scenario_overview_all_original_bytes_and_streams');fixture.setUp();self.addCleanup(fixture.doCleanups)
  root=fixture.root;before,dirs=fixture.snapshot();private=root.parent/'input-phase';private.mkdir(mode=0o700)
  request={'scope':'whole-input-phase-plus-inert-output-model','source_label':str(root),'cwd_label':str(root)}
  record=Record(private/'records',request,{'input_phase_only_not_complete_export_capture':True});record.append({'kind':'execution-intent','request':request})
  outputs=MemoryIO(before,dirs)
  class Hybrid(NativeIO):
   def mkdir(self,*args):return outputs.mkdir(*args)
   def write_bytes(self,*args):return outputs.write_bytes(*args)
   def write_text(self,*args):return outputs.write_text(*args)
  io=Hybrid(record,mode='private-candidate',cwd=str(root),private_state=private)
  result=execute(str(root),str(root),'overview',['--as-of',AT],io,validator_class=Draft202012Validator)
  self.assertEqual(result['exit_code'],0);self.assertEqual(fixture.snapshot()[0],before);record.finish('complete',{'exit_code':0,'kernel_result':result},{})
  request,source,retained,events,blob,closed=read_record(record.root);self.assertGreater(len(events),256)
  projected=MemoryIO(before,dirs)
  class ReplayInputs(ReplayIO):
   def mkdir(self,*args):return projected.mkdir(*args)
   def write_bytes(self,*args):return projected.write_bytes(*args)
   def write_text(self,*args):return projected.write_text(*args)
  replay=ReplayInputs(events,blob,'private-candidate',str(root));shutil.rmtree(root)
  with patch('lib.providers.synthetic_lifecycle_io.NativeIO.read',side_effect=AssertionError('No selected source')),patch('subprocess.Popen',side_effect=AssertionError('No program')):
   actual=execute(str(root),str(root),'overview',['--as-of',AT],replay,validator_class=Draft202012Validator)
  replay.finish();self.assertEqual(actual,result);self.assertEqual(outputs.outputs,projected.outputs);self.assertTrue(closed())


if __name__=='__main__':unittest.main()
