"""Actual generated shell starter, complete records and missing/default/explicit nodes.

Uses development product source; signed installed acceptance remains separate.
"""
from pathlib import Path
import hashlib,json,os,shlex,shutil,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.v2_distribution import launcher_text,admitted_launcher_text
from lib.operating_verification_application import PROFILE
from test_portable_runtime import OPA

class LauncherReplay(unittest.TestCase):
 def setUp(self):
  previous=os.umask(0o077);self.addCleanup(os.umask,previous);temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup);self.root=Path(temporary.name).resolve();self.prefix=self.root/'prefix with spaces';self.prefix.mkdir(mode=0o700)
  (self.prefix/'package').mkdir();(self.prefix/'package/source').symlink_to(ROOT,target_is_directory=True);(self.prefix/'venv/bin').mkdir(parents=True)
  python=self.prefix/'venv/bin/python';python.write_text('#!/bin/sh\nexec '+shlex.quote(sys.executable)+' "$@"\n');python.chmod(0o700)
  self.launcher=self.prefix/'axiom-v2';self.launcher.write_text(launcher_text());self.launcher.chmod(0o700);self.instance=self.prefix/'instance'
  self.call(['init','--development','--opa',str(OPA)],0);self.node=json.loads((self.instance/'instance.json').read_bytes());self.assertTrue(self.node['development']);self.assertEqual(json.loads((self.instance/'consumer.json').read_bytes())['mode'],'paused')
  self.selected=self.root/'selected source';self.selected.mkdir(mode=0o700)
 def call(self,args,expected):
  p=subprocess.run([str(self.launcher),*args],capture_output=True,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},stdin=subprocess.DEVNULL,timeout=300)
  self.assertEqual(p.returncode,expected,(args,p.returncode,p.stdout[-3500:],p.stderr[-3500:]));return p
 def record(self):
  p=self.call(['operating-verification','generate','--profile',PROFILE,'--transport-profile','legacy-personal-operating-git-v1','--source-worktree',str(self.selected),'--operation','collect'],1)
  receipt=json.loads(p.stdout);self.assertEqual(receipt['state'],'complete');self.assertEqual(receipt['original_exit_code'],1);self.assertFalse(receipt['authority_transferred']);self.assertFalse(receipt['official_acceptance'])
  retained=self.root/'retained record';shutil.copytree(receipt['record_root'],retained);return retained
 def fingerprint(self,root):return {p.relative_to(root).as_posix():(hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_mode&511) for p in root.rglob('*') if p.is_file()}
 def test_generated_starter_keeps_default_node_for_ordinary_operations(self):
  record=self.record();value=json.loads(self.call(['operating-verification','inspect','--record',str(record)],0).stdout);self.assertTrue(value['retained_declared_replay_consistent']);self.assertEqual(value['original_exit_code'],1);self.assertEqual(json.loads((self.instance/'instance.json').read_bytes()),self.node)
 def test_actual_starter_replays_after_default_node_and_selected_source_are_removed(self):
  record=self.record();before=self.fingerprint(record);wanted=json.loads(self.call(['operating-verification','inspect','--record',str(record)],0).stdout);shutil.rmtree(self.instance);shutil.rmtree(self.selected)
  actual=json.loads(self.call(['operating-verification','replay','--record',str(record)],0).stdout);self.assertEqual(actual,wanted);self.assertEqual(self.fingerprint(record),before);self.assertFalse(self.instance.exists())
 def test_corrupt_default_node_is_ignored_for_pure_replay_but_blocks_ordinary_operations(self):
  record=self.record();(self.instance/'instance.json').write_bytes(b'{malformed');before=self.fingerprint(record)
  value=json.loads(self.call(['operating-verification','replay','--record',str(record)],0).stdout);self.assertTrue(value['retained_declared_replay_consistent']);self.call(['operating-verification','inspect','--record',str(record)],2);self.assertEqual((self.instance/'instance.json').read_bytes(),b'{malformed');self.assertEqual(self.fingerprint(record),before)
 def test_explicit_foreign_node_overrides_default_and_cannot_inspect_its_records(self):
  record=self.record();other=self.root/'explicit node';self.call(['--instance',str(other),'init','--development','--opa',str(OPA)],0);foreign=json.loads((other/'instance.json').read_bytes());self.assertNotEqual(foreign['node_id'],self.node['node_id'])
  p=self.call(['--instance',str(other),'operating-verification','inspect','--record',str(record)],2);self.assertIn(b'foreign_node',p.stderr);self.call(['operating-verification','inspect','--record',str(record)],0);self.assertEqual(json.loads((self.instance/'instance.json').read_bytes()),self.node)
 def test_explicit_missing_node_remains_binding_even_for_replay(self):
  record=self.record();p=self.call(['--instance',str(self.root/'explicit missing'),'operating-verification','replay','--record',str(record)],2);self.assertTrue(p.stderr);self.call(['operating-verification','replay','--record',str(record)],0)
 def test_global_help_version_and_check_do_not_read_or_create_default_node(self):
  shutil.rmtree(self.instance);help=self.call(['--help'],0);self.assertNotIn(b'--default-instance',help.stdout);self.assertIn(b'operating-verification',help.stdout);self.assertTrue(self.call(['--version'],0).stdout);checked=json.loads(self.call(['check'],0).stdout);self.assertTrue(checked['passed']);self.assertFalse(self.instance.exists())
 def admitted(self,body):
  source=self.root/'admitted-source';library=source/'scripts/lib';library.mkdir(parents=True);(library/'__init__.py').write_text('');(library/'v2_distribution.py').write_text(body);return source
 def test_older_admitted_revision_without_factory_keeps_supported_legacy_arguments(self):
  source=self.admitted('# Older admitted source has no starter factory.\n')
  (source/'scripts/axiom_v2.py').write_text("import argparse,json\np=argparse.ArgumentParser();p.add_argument('--instance',required=True);p.add_argument('command',choices=('check',));a=p.parse_args();print(json.dumps({'instance':a.instance,'command':a.command}))\n")
  prefix=self.root/'older installation';(prefix/'package').mkdir(parents=True);(prefix/'package/source').symlink_to(source,target_is_directory=True);(prefix/'venv').symlink_to(self.prefix/'venv',target_is_directory=True);entry=prefix/'axiom-v2';entry.write_text(admitted_launcher_text(source,sys.executable));entry.chmod(0o700)
  result=subprocess.run([str(entry),'check'],capture_output=True,timeout=120);self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(json.loads(result.stdout),{'instance':str(prefix/'instance'),'command':'check'});self.assertFalse((prefix/'instance').exists())
 def test_admitted_factory_text_is_used_instead_of_installer_host_text(self):
  body='#!/bin/sh\nprintf "admitted-revision-starter\\n"\n';source=self.admitted('def launcher_text():return '+repr(body)+'\n');text=admitted_launcher_text(source,sys.executable);self.assertEqual(text,body);self.assertNotEqual(text,launcher_text());entry=self.root/'admitted starter';entry.write_text(text);entry.chmod(0o700);result=subprocess.run([str(entry)],capture_output=True,timeout=120);self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stdout,b'admitted-revision-starter\n')
 def test_present_failed_or_invalid_factory_cannot_silently_downgrade(self):
  source=self.admitted('');module=source/'scripts/lib/v2_distribution.py'
  for body in ('launcher_text=None\n','def launcher_text():raise RuntimeError("explicit admitted factory failure")\n','def launcher_text():return None\n','def launcher_text():return "not a shell starter"\n','print("unexpected import output")\ndef launcher_text():return "#!/bin/sh\\n"\n'):
   with self.subTest(body=body):
    module.write_text(body)
    with self.assertRaisesRegex(ValueError,'admitted_v2_launcher_'):admitted_launcher_text(source,sys.executable)
if __name__=='__main__':unittest.main(verbosity=2)
