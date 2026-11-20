"""Whole actual immutable V1 CLI vs explicit inert source/output ports."""
from pathlib import Path,PurePosixPath
from io import BytesIO
import errno,hashlib,json,os,shutil,subprocess,sys,tempfile,unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.synthetic_lifecycle_context import execute
from lib.v2_boundary import violations
from jsonschema import Draft202012Validator
from test_v2_synthetic_lifecycle_reports import REFERENCES,frozen,materialize_original_sources

TARGETS={
 'index':('status/governance-lifecycle-synthetic-index.json',),
 'pilot':('status/governance-lifecycle-closure-index.json','generated/reports/governance-lifecycle-pilot.md'),
 'exceptions':('status/governance-lifecycle-exception-index.json','generated/reports/governance-lifecycle-exceptions.md'),
 'overview':('status/governance-lifecycle-overview.json','generated/reports/governance-lifecycle-overview.md'),
 'viewer':('generated/viewer/governance-lifecycle-viewer.html',)}
AT='2026-11-15T12:00:00Z'


class MemoryIO:
 """Declared inert data/effects, never a claim of native output execution."""
 def __init__(self,files,directories):self.files=dict(files);self.directories=set(directories);self.outputs={};self.effects=[];self.reads=[]
 def text_encoding(self,encoding,errors):
  if encoding is not None:return encoding
  import io
  with io.TextIOWrapper(io.BytesIO(),errors=errors) as stream:return stream.encoding
 def probe(self,path,kind,label):
  self.reads.append(('probe',path,kind));return {'exists':path in self.files or path in self.directories,'is_dir':path in self.directories,'is_file':path in self.files,'is_symlink':False}[kind]
 def parent(self,path,label):
  for p in reversed(PurePosixPath(path).parents):
   if str(p) in self.files:raise NotADirectoryError(errno.ENOTDIR,'Not a directory',label)
  if str(PurePosixPath(path).parent) not in self.directories:raise FileNotFoundError(errno.ENOENT,'No such file or directory',label)
 def read(self,path,label):
  self.reads.append(('read',path));self.parent(path,label)
  if path in self.directories:raise IsADirectoryError(errno.EISDIR,'Is a directory',label)
  if path not in self.files:raise FileNotFoundError(errno.ENOENT,'No such file or directory',label)
  return self.files[path]
 def iterdir(self,path,label):
  self.reads.append(('iterdir',path));self.parent(path,label)
  if path in self.files:raise NotADirectoryError(errno.ENOTDIR,'Not a directory',label)
  if path not in self.directories:raise FileNotFoundError(errno.ENOENT,'No such file or directory',label)
  return sorted(PurePosixPath(p).name for p in self.directories|set(self.files) if str(PurePosixPath(p).parent)==path and p!=path)
 def mkdir(self,path,mode,parents,exist_ok,label):
  self.effects.append(('mkdir',path,mode,parents,exist_ok))
  if path in self.files or path in self.directories and not exist_ok:raise FileExistsError(errno.EEXIST,'File exists',label)
  if path in self.directories:return
  parent=str(PurePosixPath(path).parent)
  if parent not in self.directories:
   if parents:self.mkdir(parent,mode,True,True,parent)
   else:self.parent(path,label)
  self.directories.add(path)
 def write_bytes(self,path,raw,label):
  self.effects.append(('write-bytes',path));self.parent(path,label)
  if path in self.directories:raise IsADirectoryError(errno.EISDIR,'Is a directory',label)
  self.files[path]=raw;self.outputs[path]=raw;return len(raw)
 def write_text(self,path,value,encoding,errors,label):
  self.effects.append(('write-text',path,encoding,errors));self.parent(path,label)
  if path in self.directories:raise IsADirectoryError(errno.EISDIR,'Is a directory',label)
  self.files[path]=b''
  with BytesIO() as buffer:
   import io
   stream=io.TextIOWrapper(buffer,encoding=encoding,errors=errors);stream.write(value);stream.flush();raw=buffer.getvalue();stream.detach()
  self.files[path]=raw;self.outputs[path]=raw;return len(value)


class WholeSyntheticLifecycleContext(unittest.TestCase):
 def setUp(self):
  tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);self.root=Path(tmp.name).resolve()/'data';self.root.mkdir(mode=0o700)
  # Same explicit data bytes on both sides; immutable entire V1 code comes from
  # existing frozen fixtures, so neither a Git history nor a source checkout's
  # executable code is needed by the comparison oracle.
  for name in ('model','schemas','governance','status'):
   shutil.copytree(ROOT/name,self.root/name,ignore=shutil.ignore_patterns('__pycache__','.DS_Store'))
  for directory in ('scripts/templates','generated/reports','generated/viewer'):(self.root/directory).mkdir(parents=True)
  target=self.root/'scripts/templates/governance-lifecycle-viewer.html';target.write_bytes((ROOT/'scripts/templates/governance-lifecycle-viewer.html').read_bytes())
  for paths in TARGETS.values():
   for name in paths:
    if name.startswith('generated/') and (ROOT/name).is_file():(self.root/name).write_bytes((ROOT/name).read_bytes())
  materialize_original_sources(self.root)
  for name,(filename,_,_) in REFERENCES.items():self.assertEqual((self.root/'scripts'/filename).read_bytes(),frozen(name)[1])
 def snapshot(self):
  files={str(p):p.read_bytes() for p in self.root.rglob('*') if p.is_file()};dirs={str(p) for p in self.root.rglob('*') if p.is_dir()}|{str(self.root)}
  dirs.update(str(p) for p in self.root.parents);return files,dirs
 def arguments(self,name):return [] if name=='viewer' else ['--as-of',AT]
 def compare(self,name,args=None,*,expected_code=0):
  args=self.arguments(name) if args is None else args;before,dirs=self.snapshot();filename=REFERENCES[name][0]
  old=subprocess.run([sys.executable,str(self.root/'scripts'/filename),*args],cwd=self.root,capture_output=True,timeout=90,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
  self.assertEqual(old.returncode,expected_code,old.stderr[-2000:]);after,_=self.snapshot();memory=MemoryIO(before,dirs)
  with patch('subprocess.Popen',side_effect=AssertionError('Pure reexecution starts no native program')):
   result=execute(str(self.root),str(self.root),name,args,memory,validator_class=Draft202012Validator)
  self.assertEqual(result['exit_code'],old.returncode);self.assertEqual(result['stdout'].encode(),old.stdout)
  if expected_code==0:
   self.assertIsNone(result['kernel_exception']);self.assertEqual(result['stderr'].encode(),old.stderr)
  elif result['kernel_exception'] is not None:
   error=result['kernel_exception'];self.assertTrue(old.stderr.decode().endswith(error['type']+': '+error['message']+'\n'),(error,old.stderr[-2000:]));self.assertFalse(result['stderr'])
  else:self.assertEqual(result['stderr'].encode(),old.stderr)
  self.assertEqual(memory.files,after)
  self.assertTrue(all(after[p]==raw for p,raw in memory.outputs.items()))
  return result,memory
 def test_entire_default_index_all_original_bytes_and_streams(self):
  _,data=self.compare('index');self.assertEqual(set(data.outputs),{str(self.root/p) for p in TARGETS['index']})
 def test_entire_default_pilot_all_original_bytes_and_streams(self):
  _,data=self.compare('pilot');self.assertEqual(set(data.outputs),{str(self.root/p) for p in TARGETS['pilot']})
 def test_entire_default_exception_projection_all_original_bytes_and_streams(self):
  _,data=self.compare('exceptions');self.assertEqual(set(data.outputs),{str(self.root/p) for p in TARGETS['exceptions']})
 def test_entire_default_three_scenario_overview_all_original_bytes_and_streams(self):
  _,data=self.compare('overview');self.assertEqual(set(data.outputs),{str(self.root/p) for p in TARGETS['overview']})
 def test_entire_default_CSP_viewer_all_original_bytes_and_streams(self):
  _,data=self.compare('viewer');self.assertEqual(set(data.outputs),{str(self.root/p) for p in TARGETS['viewer']})
 def test_nonexistent_selected_ledger_is_original_complete_empty_projection(self):
  result,data=self.compare('index',['--ledger',str(self.root/'absent'),'--as-of',AT]);self.assertEqual(result['exit_code'],0)
  value=json.loads(next(iter(data.outputs.values())));self.assertEqual(value['counts']['findings'],0)
 def test_immutable_ledger_output_guard_is_original_error_before_any_source_read(self):
  result,data=self.compare('index',['--as-of',AT,'--output',str(self.root/'governance/lifecycle/synthetic/forbidden.json')],expected_code=1)
  self.assertEqual(result['kernel_exception']['type'],'ContractError');self.assertFalse(data.outputs);self.assertFalse(data.reads)
 def test_second_export_directory_error_keeps_whole_first_original_index(self):
  target=self.root/'directory-output';target.mkdir();result,data=self.compare('pilot',['--as-of',AT,'--report',str(target)],expected_code=1)
  self.assertEqual(result['kernel_exception']['type'],'IsADirectoryError');self.assertEqual(set(data.outputs),{str(self.root/TARGETS['pilot'][0])})
 def test_official_viewer_output_guard_is_original_error_without_overview_reads(self):
  result,data=self.compare('viewer',['--output',str(self.root/'generated/viewer/status-viewer.html')],expected_code=1)
  self.assertEqual(result['kernel_exception']['message'],'Official status viewer is separate');self.assertFalse(data.reads);self.assertFalse(data.outputs)
 def test_old_cutoff_cannot_hide_bad_later_transaction(self):
  last=sorted((self.root/'governance/lifecycle/synthetic/transactions').glob('*.json'))[-1];last.write_bytes(b'{not valid')
  result,data=self.compare('overview',['--as-of','1900-01-01T00:00:00Z'],expected_code=1)
  self.assertEqual(result['kernel_exception']['type'],'JSONDecodeError');self.assertFalse(data.outputs)
 def test_help_and_unknown_flag_are_original_complete0_2_without_selected_IO(self):
  for args,code in ((['--help'],0),(['--unknown'],2)):
   with self.subTest(args=args):result,data=self.compare('overview',args,expected_code=code);self.assertFalse(data.reads);self.assertFalse(data.outputs);self.assertEqual(result['original_exit_signal'],{'type':'SystemExit','value':code})
 def test_neutral_context_has_no_provider_or_legacy_imports(self):self.assertEqual(violations('scripts/lib/synthetic_lifecycle_context.py',(ROOT/'scripts/lib/synthetic_lifecycle_context.py').read_text()),[])


if __name__=='__main__':unittest.main()
