"""Unchanged original starter with explicit inert bootstrap/interpreter doubles.

This verifies actual shell branch/argument/exit behavior, not real HTTP serving,
package acquisition, consumer assessment or independent native V1/V2 acceptance.
"""
from pathlib import Path
import hashlib,json,os,shutil,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from lib.workbench_startup import replay
from lib.environment_bootstrap import BootstrapFailure

class OriginalStartup(unittest.TestCase):
    def original(self,*,existing=False,bootstrap_exit=0,server_exit=0):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary).resolve();scripts=root/'scripts';scripts.mkdir()
            raw=(ROOT/'tests/fixtures/v2-workbench-original-start/start_governance_workbench.sh').read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),'bd01e5708c009324f761079c9048a126c3c216df36c41ebd94bf59acd59ffb3c')
            starter=scripts/'start_governance_workbench.sh';starter.write_bytes(raw)
            venv=root/'operator environment';(venv/'bin').mkdir(parents=True)
            calls=root/'calls.jsonl'
            fake=scripts/'fake-interpreter';fake.write_text('#!'+sys.executable+'\nimport json,os,sys\nwith open(os.environ["CALLS"],"a") as f:f.write(json.dumps({"kind":"server","argv":sys.argv[1:]})+"\\n")\nraise SystemExit(int(os.environ["SERVER_EXIT"]))\n');fake.chmod(0o700)
            bootstrap=scripts/'bootstrap_validation_env.sh'
            bootstrap.write_text('#!'+sys.executable+'\nimport json,os,shutil\nfrom pathlib import Path\nwith open(os.environ["CALLS"],"a") as f:f.write(json.dumps({"kind":"bootstrap"})+"\\n")\ncode=int(os.environ["BOOTSTRAP_EXIT"])\nif not code:shutil.copyfile('+repr(str(fake))+',Path(os.environ["VALIDATION_VENV"])/"bin/python");(Path(os.environ["VALIDATION_VENV"])/"bin/python").chmod(0o700)\nraise SystemExit(code)\n');bootstrap.chmod(0o700)
            if existing:shutil.copyfile(fake,venv/'bin/python');(venv/'bin/python').chmod(0o700)
            environment={**os.environ,'VALIDATION_VENV':str(venv),'CALLS':str(calls),'BOOTSTRAP_EXIT':str(bootstrap_exit),'SERVER_EXIT':str(server_exit)}
            args=['--port','18875','--consumer-projection','operator path with spaces','--enable-pr']
            result=subprocess.run(['/bin/bash',str(starter),*args],env=environment,capture_output=True,timeout=30)
            rows=[json.loads(line) for line in calls.read_text().splitlines()]
            if result.returncode==server_exit and any(r['kind']=='server' for r in rows):
                self.assertEqual(rows[-1]['argv'],[str(scripts/'serve_governance_workbench.py'),*args])
            return result,rows
    def test_actual_original_first_setup_then_handoff_matches_finite_branch(self):
        actual,rows=self.original();self.assertEqual(actual.returncode,0)
        self.assertEqual([r['kind'] for r in rows],['bootstrap','server']);self.assertIn(b'initial local setup',actual.stdout)
        observed=[{'action':a,'value':False if a=='environment_python_executable' else 0 if a=='handoff_workbench' else None} for a in ('preflight','environment_python_executable','bootstrap_environment','admit_environment','admit_instance','handoff_workbench')]
        self.assertEqual(replay(observed),actual.returncode)
    def test_actual_original_existing_interpreter_skips_bootstrap_even_if_it_would_fail(self):
        actual,rows=self.original(existing=True,bootstrap_exit=23)
        self.assertEqual(actual.returncode,0);self.assertEqual([r['kind'] for r in rows],['server']);self.assertEqual(actual.stdout,b'')
    def test_actual_original_bootstrap_native_exit_propagates_without_server_handoff(self):
        actual,rows=self.original(bootstrap_exit=24)
        self.assertEqual(actual.returncode,24);self.assertEqual([r['kind'] for r in rows],['bootstrap'])
        # V2 uses structured known failure1, explicitly documented rather than
        # claiming shell-native status24 compatibility.
        observed=[{'action':'preflight','value':None},{'action':'environment_python_executable','value':False},{'action':'bootstrap_environment','failure':'explicit_original_exit_24'}]
        with self.assertRaises(BootstrapFailure):replay(observed)
    def test_actual_original_server_exit_is_retained_after_process_replacement(self):
        actual,rows=self.original(existing=True,server_exit=23)
        self.assertEqual(actual.returncode,23);self.assertEqual(len(rows),1)
        observed=[{'action':a,'value':True if a=='environment_python_executable' else 23 if a=='handoff_workbench' else None} for a in ('preflight','environment_python_executable','admit_environment','admit_instance','handoff_workbench')]
        self.assertEqual(replay(observed),23)

if __name__=='__main__':unittest.main()
