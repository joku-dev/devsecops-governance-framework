"""Actual unchanged shell orchestration with controlled native operation results.

The original metadata-probe body and host awk really execute. Validator/test
program doubles are explicit; this is not a real full validation or host pass.
"""
from pathlib import Path
import base64,hashlib,io,json,os,shutil,subprocess,sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from lib.validation_suite import run,replay,Observation,TOOL_PHASES,VALIDATOR_PHASES
from test_v2_validation_suite import Sink,Journal

ORIGINAL_CASES=[]

STUB=r'''from pathlib import Path
import base64,contextlib,importlib.metadata,io,json,os,sys
configuration=json.loads(Path(os.environ['ORACLE_CONFIG']).read_bytes())
args=sys.argv[1:];is_opa=Path(sys.argv[0]).name=='opa'
if is_opa:action='opa_version' if args==['version'] else 'opa_check'
elif args[:1]==['-']:action='dependency_versions'
elif args[:3]==['-m','pip','check']:action='dependency_consistency'
elif args==['-m','unittest','discover','-s','tests']:action='unit_tests'
else:
 name=Path(args[0]).name
 action={'validate_runtime_governance.py':'runtime_validation','validate_governance_repo.py':'repository_validation','validate_evidence_agent_provenance.py':'provenance_validation'}[name]
code=configuration.get('failure_code',23) if action==configuration.get('fail') else 0
out=(configuration.get('opa_raw','Version: 1.18.2\n') if action=='opa_version' else 'observed '+action+' stdout\n').encode()
err=(('observed '+action+' diagnostic\n').encode() if code else b'')
if action=='dependency_versions':
 query=sys.stdin.read();assert query==configuration['original_query']
 original_version=importlib.metadata.version
 def selected_version(name):
  if name in configuration.get('missing',[]):raise importlib.metadata.PackageNotFoundError(name)
  return configuration.get('versions',{}).get(name,configuration['pins'][name])
 importlib.metadata.version=selected_version
 captured_out=io.StringIO();captured_err=io.StringIO();sys.argv=['-',args[1]]
 try:
  with contextlib.redirect_stdout(captured_out),contextlib.redirect_stderr(captured_err):
   exec(compile(query,'<stdin>','exec'),{'__name__':'__main__'})
 except SystemExit as error:
  if isinstance(error.code,str):captured_err.write(error.code+'\n');code=1
  else:code=error.code or 0
 finally:importlib.metadata.version=original_version
 out=captured_out.getvalue().encode();err=captured_err.getvalue().encode()
 if action==configuration.get('fail'):code=configuration.get('failure_code',23);err+=b'observed dependency_versions diagnostic\n'
row={'action':action,'native_returncode':code,'stdout_base64':base64.b64encode(out).decode(),'stderr_base64':base64.b64encode(err).decode(),'cwd':str(Path.cwd()),'argv':args,'PATH':os.environ.get('PATH','')}
with Path(os.environ['ORACLE_TRACE']).open('a') as target:target.write(json.dumps(row)+'\n')
sys.stdout.buffer.write(out);sys.stderr.buffer.write(err);raise SystemExit(code)
'''

class OriginalWholeValidation(unittest.TestCase):
    def compare(self,args=(),*,failed=None,code=23,version='Version: 1.18.2\n',missing=(),versions=None,absent=None,space_environment=False):
        with tempfile.TemporaryDirectory() as temporary:
            work=Path(temporary).resolve();source=work/'own source';scripts=source/'scripts';scripts.mkdir(parents=True)
            raw=(ROOT/'tests/fixtures/v2-validation-suite-original/validate_all.sh').read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(),'0afc7a62effc614493e9b3dc434f93ac33d0d28495b808dbc7c67b13a98717a7')
            (scripts/'validate_all.sh').write_bytes(raw)
            toolchain=(ROOT/'tests/fixtures/v2-validation-suite-original/validation-toolchain.env').read_bytes();(scripts/'validation-toolchain.env').write_bytes(toolchain)
            requirements=(ROOT/'tests/fixtures/v2-validation-suite-original/requirements-validation.txt').read_bytes();(source/'requirements-validation.txt').write_bytes(requirements)
            pins=dict(line.split('==',1) for line in requirements.decode().splitlines() if line and not line.startswith('#'))
            query=raw.decode().split("<<'PY'\n",1)[1].split('\nPY\n',1)[0]+'\n'
            config={'fail':failed,'failure_code':code,'opa_raw':version,'pins':pins,'original_query':query,'missing':list(missing),'versions':versions or {}}
            (work/'config.json').write_text(json.dumps(config));trace=work/'trace.jsonl'
            environment=work/('operator environment' if space_environment else 'operator-environment');(environment/'bin').mkdir(parents=True)
            for name in ('python','opa'):
                if name!=absent:
                    p=environment/'bin'/name;p.write_text('#!'+sys.executable+'\n'+STUB);p.chmod(0o700)
            env={**os.environ,'PATH':'/usr/bin:/bin','VALIDATION_VENV':str(environment),'ORACLE_CONFIG':str(work/'config.json'),'ORACLE_TRACE':str(trace),'PYTHONDONTWRITEBYTECODE':'1','LANG':'C'}
            actual=subprocess.run(['/bin/bash',str(scripts/'validate_all.sh'),*args],cwd=work,env=env,capture_output=True,timeout=30)
            native=[json.loads(line) for line in trace.read_text().splitlines()] if trace.exists() else []
            if space_environment:
                # Actual unchanged original source expands $OPA unquoted in
                # command substitution. Keep the real127 failure as a known
                # compatibility limitation; never require V2 to run a wrong tool.
                self.assertEqual(actual.returncode,127)
                self.assertIn(str(environment).split(' ')[0].encode(),actual.stderr)
                self.assertEqual(native,[])
                self.assertEqual((scripts/'validate_all.sh').read_bytes(),raw)
                ORIGINAL_CASES.append({'arguments':list(args),'original_exit':127,'original_unquoted_path_limitation':True,'selected_policy_tool_executed':False,'V2_native_compatibility_claimed':False})
                return [],127
            observations={r['action']:r for r in native}
            sink=Sink();journal=Journal()
            class Ports:
                def perform(inner,action):
                    if action=='require_tools':
                        present=all((environment/'bin'/n).is_file() for n in ('python','opa'))
                        err=b'' if present else ('Validation environment is incomplete: '+str(environment)+'\nRun: ./scripts/bootstrap_validation_env.sh\n').encode()
                        return Observation(0 if present else 1,b'',err)
                    if action not in observations:raise AssertionError({'missing_original_phase':action,'original_exit':actual.returncode,'original_stderr':actual.stderr.decode()})
                    row=observations[action];out=base64.b64decode(row['stdout_base64']);err=base64.b64decode(row['stderr_base64']);status=row['native_returncode']
                    if action=='opa_version':
                        awk=subprocess.run(['/usr/bin/awk','/^Version:/ {print $2}'],input=out,capture_output=True,env={'PATH':'/usr/bin:/bin','LANG':'C'},timeout=5)
                        out=awk.stdout;err+=awk.stderr;status=awk.returncode or status
                    return Observation(status,out,err)
            expected=dict(line.split('=',1) for line in toolchain.decode().splitlines() if line and not line.startswith('#'))['OPA_VERSION']
            result=run(list(args),Ports(),journal,sink,environment_label=str(environment),expected_opa_version=expected)
            self.assertEqual((result,sink.streams['stdout'].getvalue(),sink.streams['stderr'].getvalue()),(actual.returncode,actual.stdout,actual.stderr))
            actions=[r['action'] for r in journal.rows]
            self.assertEqual([a for a in actions if a!='require_tools'],[r['action'] for r in native])
            for row in native:
                if row['action'] in VALIDATOR_PHASES:
                    self.assertEqual(row['cwd'],str(source));self.assertEqual(row['PATH'].split(os.pathsep)[0],str(environment/'bin'))
            repeated=Sink();self.assertEqual(replay(list(args),journal.rows,repeated,environment_label=str(environment),expected_opa_version=expected),result)
            self.assertEqual({k:v.getvalue() for k,v in repeated.streams.items()},{k:v.getvalue() for k,v in sink.streams.items()})
            self.assertEqual((scripts/'validate_all.sh').read_bytes(),raw)
            ORIGINAL_CASES.append({'arguments':list(args),'failed_native_action':failed,'native_failure_code':code if failed else None,'opa_raw':version,'missing_packages':list(missing),'version_overrides':versions or {},'absent_tool':absent,'original_exit':actual.returncode,'original_native_actions':[r['action'] for r in native],'core_actions':actions,'whole_stdout_and_stderr_equal':True,'ordered_replay_equal':True,'original_stdout_sha256':hashlib.sha256(actual.stdout).hexdigest(),'original_stderr_sha256':hashlib.sha256(actual.stderr).hexdigest()})
            return actions,result
    def test_default_complete_chain_native_order_cwd_path_and_whole_wires(self):self.assertEqual(self.compare()[0],[*TOOL_PHASES,*VALIDATOR_PHASES])
    def test_empty_single_argument_retains_original_default_scope(self):self.assertEqual(self.compare([''])[0],[*TOOL_PHASES,*VALIDATOR_PHASES])
    def test_explicit_check_tools_stops_before_all_validators(self):self.assertEqual(self.compare(['--check-tools'])[0],list(TOOL_PHASES))
    def test_original_help_exits_before_extra_argument_validation(self):
        for args in (['--help'],['-h'],['--help','ignored'],['-h','--unknown']):
            with self.subTest(args=args):self.assertEqual(self.compare(args),([],0))
    def test_original_unknown_extra_and_empty_extra_arguments_fail_without_any_tool(self):
        for args in (['--unknown'],['--check-tools','extra'],['','extra']):
            with self.subTest(args=args):self.assertEqual(self.compare(args),([],2))
    def test_missing_selected_python_or_policy_binary_stops_before_version_probe(self):
        for name in ('python','opa'):
            with self.subTest(name=name):self.assertEqual(self.compare(absent=name),(['require_tools'],1))
    def test_original_unquoted_policy_path_with_spaces_fails_before_the_selected_tool_runs(self):self.assertEqual(self.compare(space_environment=True),([],127))
    def test_actual_host_awk_version_fields_cr_and_multiple_lines(self):
        for raw in ('Version: 1.18.2\n','Version:\t1.18.2 extra\n','Version:1.18.2\n','Version: 1.18.2\r\n','Version: 1.18.2\nVersion: 1.18.2\n','No version\n'):
            with self.subTest(raw=raw):self.compare(version=raw)
    def test_original_pipefail_preserves_version_native_error_without_mismatch_message(self):self.assertEqual(self.compare(failed='opa_version',code=42)[1],42)
    def test_original_metadata_body_reports_all_missing_and_wrong_pins_in_source_order(self):
        self.assertEqual(self.compare(missing=['PyYAML','attrs'],versions={'jsonschema':'0.0.0'})[1],1)
    def test_every_original_native_failure_propagates_and_stops_later_commands(self):
        for action in (*TOOL_PHASES[1:],*VALIDATOR_PHASES):
            with self.subTest(action=action):
                chain,result=self.compare(failed=action,code=29);self.assertEqual(result,29);self.assertEqual(chain[-1],action)

if __name__=='__main__':unittest.main()
