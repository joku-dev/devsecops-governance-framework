"""Additional native admission boundaries; these are not V1 equivalence claims."""
from pathlib import Path
import json,os,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
import test_v2_operational_publisher_native as reference
from lib.providers.operational_publication_native import native_publisher
from lib.providers.operational_publication_process import NativePublisherPipes
from lib.requirement_validation_budget import InputAdmissionError
class OperationalPublisherBoundaries(unittest.TestCase):
 def setUp(self):
  c=reference.WholeOperationalPublisherNative();c.setUp();self.addCleanup(c.doCleanups);self.case=c;self.root,self.origin,self.tools,self.output,self.summary,self.env=c.fixture('boundary');self.gates=object()
 def publisher(self,**extra):return native_publisher(self.root,scope='portfolio',repository=reference.REPOSITORY,run_id=reference.RUN,attempt=reference.ATTEMPT,gates=self.gates,environment=self.env,provider_executable=str(self.tools/'gh'),local_origin_root=self.case.base,**extra)
 def candidate(self):(self.root/'generated/reports/portfolio-onboarding-status.json').write_text('{"explicit":"proposal"}\n')
 def test_Main_push_or_force_push_is_rejected_before_execution(self):
  pub,process=self.publisher()
  for args in (['git','push','origin','HEAD:refs/heads/main'],['git','push','--force','origin','HEAD:refs/heads/automation/portfolio/42-1']):
   with self.assertRaises(InputAdmissionError):process.run(args,cwd=self.root,text=True,capture_output=True,check=True)
  self.assertEqual(process.observations,[]);self.assertEqual(self.case.git(self.origin,'rev-parse','main').strip(),self.case.initial)
 def test_source_hook_is_not_executed_by_native_commit(self):
  marker=self.case.base/'hook-must-not-run';hook=self.root/'.git/hooks/pre-commit';hook.write_text('#!/bin/sh\nprintf forbidden > '+str(marker)+'\nexit 99\n');hook.chmod(0o700);self.candidate();pub,process=self.publisher();value=pub.publish(self.root,scope='portfolio',repository=reference.REPOSITORY,run_id=reference.RUN,attempt=reference.ATTEMPT);self.assertEqual(value['number'],123);self.assertFalse(marker.exists())
 def test_external_filter_config_is_incomplete_before_fetch_or_commit_not_executed(self):
  marker=self.case.base/'filter-must-not-run';self.case.git(self.root,'config','filter.explicit.clean','sh -c "echo forbidden > '+str(marker)+'"');(self.root/'.git/info/attributes').write_text('generated/reports/portfolio-onboarding-status.json filter=explicit\n');self.candidate();pub,process=self.publisher()
  with self.assertRaisesRegex(InputAdmissionError,'external_filter_profile_required'):pub.publish(self.root,scope='portfolio',repository=reference.REPOSITORY,run_id=reference.RUN,attempt=reference.ATTEMPT)
  self.assertFalse(marker.exists());self.assertEqual(self.case.git(self.root,'branch','--show-current').strip(),'main');self.assertFalse((self.tools/'calls.jsonl').exists())
 def test_provider_host_mismatch_cannot_redirect_the_POST_profile(self):
  self.env['GH_HOST']='unselected.example.invalid';pub,process=self.publisher()
  with self.assertRaisesRegex(InputAdmissionError,'explicit_host_profile_required'):pub.provider_api('repos/example/project/pulls',{'title':'Explicit test','head':'automation/portfolio/42-1','base':'main','body':'fixture only'})
  self.assertEqual(process.observations,[]);self.assertFalse((self.tools/'calls.jsonl').exists())
 def test_wrong_repository_endpoint_or_protected_target_is_not_admitted(self):
  pub,process=self.publisher()
  for endpoint,payload in [('repos/other/project/pulls',{}),('repos/example/project/pulls',{'title':'fixture','head':'main','base':'main','body':'fixture'}),('repos/example/project/actions/workflows/codeql.yml/dispatches',{'ref':'main'})]:
   with self.assertRaises(InputAdmissionError):pub.provider_api(endpoint,payload)
  self.assertEqual(process.observations,[])
 def test_local_remote_escape_is_rejected_before_new_branch(self):
  pub,process=self.publisher();process.local_origin_root=self.case.base/'not-the-admitted-root';self.candidate()
  with self.assertRaisesRegex(InputAdmissionError,'remote_binding_required'):pub.publish(self.root,scope='portfolio',repository=reference.REPOSITORY,run_id=reference.RUN,attempt=reference.ATTEMPT)
  self.assertEqual(self.case.git(self.root,'branch','--show-current').strip(),'main');self.assertFalse((self.tools/'calls.jsonl').exists())
 def test_shared_or_linked_Git_directories_require_a_separate_write_profile(self):
  for name in ('commondir','config.worktree','objects/info/alternates','objects/info/http-alternates'):
   with self.subTest(name=name):
    path=self.root/'.git'/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(str(self.origin))
    try:
     with self.assertRaisesRegex(InputAdmissionError,'shared_Git_profile_required'):self.publisher()
    finally:path.unlink()
 def test_nested_Git_write_alias_is_rejected_before_fetch_or_new_branch(self):
  outside=self.case.base/'unselected-refs';outside.mkdir();alias=self.root/'.git/refs/explicit-unselected';alias.symlink_to(outside,target_is_directory=True);self.candidate();pub,process=self.publisher()
  with self.assertRaisesRegex(InputAdmissionError,'Git_write_alias_not_admitted'):pub.publish(self.root,scope='portfolio',repository=reference.REPOSITORY,run_id=reference.RUN,attempt=reference.ATTEMPT)
  self.assertEqual(list(outside.iterdir()),[]);self.assertFalse((self.tools/'calls.jsonl').exists())
 def test_external_config_or_worktree_binding_rejected_before_first_diff(self):
  for key,value in (('include.path',str(self.case.base/'unselected-config')),('core.worktree',str(self.case.base/'unselected-worktree')),('extensions.worktreeConfig','true')):
   with self.subTest(key=key):
    self.case.git(self.root,'config',key,value)
    try:
     pub,process=self.publisher()
     with self.assertRaisesRegex(InputAdmissionError,'external_filter_profile_required'):pub.publish(self.root,scope='portfolio',repository=reference.REPOSITORY,run_id=reference.RUN,attempt=reference.ATTEMPT)
     self.assertEqual(process.observations,[])
    finally:self.case.git(self.root,'config','--unset',key)
class PublisherBinaryPipeCapture(unittest.TestCase):
 def test_bounded_stdin_and_opaque_streams_are_captured_without_text_normalization(self):
  process=NativePublisherPipes();data=b'x'*200000;code,out,err=process.run([sys.executable,'-B','-c','import sys;data=sys.stdin.buffer.read();sys.stdout.buffer.write(str(len(data)).encode()+b"\\r\\n");sys.stderr.buffer.write(b"opaque\\xff\\r\\n")'],str(ROOT),dict(os.environ),10,data);self.assertEqual((code,out,err),(0,b'200000\r\n',b'opaque\xff\r\n'));self.assertTrue(process.observation['terminal_observed']);self.assertFalse(process.observation['OS_network_or_process_tree_isolation_attested'])
 def test_early_stdin_close_does_not_deadlock_or_repeat_the_program(self):
  process=NativePublisherPipes();code,out,err=process.run([sys.executable,'-B','-c','import sys;sys.stdin.close();print("once")'],str(ROOT),dict(os.environ),10,b'x'*1024**2);self.assertEqual((code,out,err),(0,b'once\n',b''));self.assertTrue(process.observation['terminal_observed'])
 def test_deadline_is_technical_incomplete_after_process_start(self):
  process=NativePublisherPipes()
  with self.assertRaisesRegex(InputAdmissionError,'native_deadline'):process.run([sys.executable,'-B','-c','import time;time.sleep(30)'],str(ROOT),dict(os.environ),.1,None)
  self.assertTrue(process.observation['started']);self.assertTrue(process.observation['timed_out']);self.assertFalse(process.observation['OS_network_or_process_tree_isolation_attested'])
if __name__=='__main__':unittest.main(verbosity=2)
