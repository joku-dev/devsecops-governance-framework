"""Original checked binary run semantics, finite request selection and no pure effects."""
from pathlib import Path
from unittest.mock import patch
import hashlib,json,os,shutil,signal,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.pilot_update_ports import NativeUpdateIO,ReplayUpdateIO
from lib.providers.pilot_update_protocol import NativePilotUpdateTransport,ReplayPilotUpdateTransport,LegacyPilotUpdateProtocol
from lib.providers.synthetic_lifecycle_storage import Record,read_record
from lib.pilot_action_intake_ports import transaction_name
from lib.requirement_review_output import RetainedOutputError
from lib.requirement_validation_budget import InputAdmissionError
class CheckedPilotUpdateGit(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name).resolve();self.source=self.base/'source';self.source.mkdir(mode=0o700);self.private=self.base/'state';self.private.mkdir(mode=0o700);self.path='model/governance/lifecycle/action-requests/request.data';p=self.source/self.path;p.parent.mkdir(parents=True);p.write_bytes(b'opaque\0request\xff');self.command=['git','ls-files','--error-unmatch','--',self.path]
  for args in (['init','--initial-branch=checked-read-fixture'],['config','gc.auto','0'],['config','maintenance.auto','false'],['add','--',self.path]):subprocess.run(['git','-C',str(self.source),*args],check=True,capture_output=True)
 def compare(self,*,tracked=True,fake_signal=False):
  if not tracked:subprocess.run(['git','-C',str(self.source),'rm','--cached','--',self.path],check=True,capture_output=True)
  env={k:v for k,v in os.environ.items() if not k.startswith(('GIT_','LD_','DYLD_'))};env.update(GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_SYSTEM='/dev/null',GIT_CONFIG_NOSYSTEM='1')
  if fake_signal:
   tools=self.base/'tools';tools.mkdir(mode=0o700);fake=tools/'git';fake.write_text('#!'+sys.executable+'\nimport os,signal,sys\nsys.stdout.buffer.write(b"opaque\\x00\\xff\\r\\n");sys.stdout.buffer.flush();sys.stderr.buffer.write(b"captured\\xf1stderr\\r\\n");sys.stderr.buffer.flush();os.kill(os.getpid(),signal.SIGTERM)\n');fake.chmod(0o700);env['PATH']=str(tools)+os.pathsep+env.get('PATH','')
  before={p.relative_to(self.source).as_posix():(p.read_bytes(),p.stat().st_mode&511) for p in self.source.rglob('*') if p.is_file()};original=None;error=None
  try:original=subprocess.run(self.command,cwd=self.source,check=True,capture_output=True,env=env)
  except subprocess.CalledProcessError as caught:error=caught
  record=Record(self.private/'records',{'prototype':'checked binary Git'},{'prototype':True});record.append({'kind':'execution-intent'});owner=NativeUpdateIO(record,mode='private-candidate',cwd=str(self.source),private_state=self.private,source=str(self.source),transaction_name=transaction_name);emitted=[];port=NativePilotUpdateTransport(owner,str(self.source),emit_stderr=emitted.append,environment=env)
  if error:
   with self.assertRaises(RetainedOutputError) as caught:port.run(self.command,cwd=str(self.source),check=True,capture_output=True)
   self.assertEqual(caught.exception.original_type,type(error).__name__);self.assertEqual(caught.exception.original_message,str(error));current=None
  else:
   current=port.run(self.command,cwd=str(self.source),check=True,capture_output=True);self.assertEqual((current.args,current.returncode,current.stdout,current.stderr),(original.args,original.returncode,original.stdout,original.stderr))
  self.assertEqual(emitted,[]);self.assertEqual({p.relative_to(self.source).as_posix():(p.read_bytes(),p.stat().st_mode&511) for p in self.source.rglob('*') if p.is_file()},before);record.finish('complete',{'exit_code':0},owner.touched);_,_,_,events,blob,closed=read_record(record.root);cache={p.name:p.read_bytes() for p in record.blobs.iterdir()};seen=set()
  def inert(ref):
   raw=cache[ref['sha256']];self.assertEqual(len(raw),ref['bytes']);self.assertEqual(hashlib.sha256(raw).hexdigest(),ref['sha256']);seen.add(ref['sha256']);return raw
  shutil.rmtree(self.source);replay=ReplayUpdateIO(events,inert,'private-candidate',str(self.source),source=str(self.source),transaction_name=transaction_name);pure=ReplayPilotUpdateTransport(replay,str(self.source),emit_stderr=emitted.append)
  with patch('subprocess.Popen',side_effect=AssertionError('No Git')),patch('os.open',side_effect=AssertionError('No source')):
   if error:
    with self.assertRaises(RetainedOutputError) as caught:pure.run(self.command,cwd=str(self.source),check=True,capture_output=True)
    self.assertEqual(caught.exception.original_message,str(error))
   else:
    actual=pure.run(self.command,cwd=str(self.source),check=True,capture_output=True);self.assertEqual(vars(actual),vars(current))
   replay.finish()
  self.assertEqual(emitted,[]);self.assertEqual(seen,set(cache))
  for name,raw in cache.items():blob({'sha256':name,'bytes':len(raw)})
  self.assertTrue(closed())
 def test_checked_success_retains_completed_binary_result_without_emission(self):self.compare()
 def test_untracked_request_retains_CPE_and_captured_stderr_without_emission(self):self.compare(tracked=False)
 def test_original_signal_CPE_and_opaque_binary_streams_have_closed_replay(self):self.compare(fake_signal=True)
 def test_fixed_read_profile_rejects_unchecked_unknown_writer_and_foreign_path_before_execution(self):
  profile=LegacyPilotUpdateProtocol();args={'command':self.command,'cwd':str(self.source),'check':True,'capture_output':True}
  for bad in ({**args,'check':False},{**args,'check':1},{**args,'capture_output':False},{**args,'command':['git','add','--',self.path]},{**args,'command':self.command[:-1]+['model/governance/lifecycle/action-requests/../../secret']},{**args,'command':self.command[:-1]+['outside/secret']},{**args,'extra':True}):
   with self.subTest(bad=bad),self.assertRaises(InputAdmissionError):profile.request('git-checked-run',bad,str(self.source),str(self.source))
if __name__=='__main__':unittest.main(verbosity=2)
