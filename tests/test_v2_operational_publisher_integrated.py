"""Whole publisher with real synthetic lifecycle gates and isolated native Git/POST.

Only owned temporary origins and a fake provider are written. The journal here
covers gate observations only; a complete publisher record remains separate.
"""
from contextlib import redirect_stdout,redirect_stderr
from pathlib import Path
import hashlib,io,json,os,subprocess,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tests'),str(ROOT/'scripts')]
import test_v2_lifecycle_ledger_validation_execution as fixture
from jsonschema import Draft202012Validator
from lib.operational_publication_gate_ports import gates,release
from lib.personal_channel_context import OrderedStderr
from lib.providers.operational_publication_native import native_publisher
from lib.providers.pilot_run_intake_io import NativeRunIO
from lib.pilot_run_intake_ports import ledger,transaction_name
from lib.providers.synthetic_lifecycle_storage import Record
def snapshot(root):
    return {p.relative_to(root).as_posix():(p.read_bytes(),p.stat().st_mode&0o777) for p in root.rglob('*') if p.is_file() and '.git' not in p.relative_to(root).parts}
ORIGINAL=ROOT/'tests/fixtures/v2-operational-publisher-original'
WRAPPER='''from pathlib import Path
import json,runpy,sys
root=Path(sys.argv[1]);sys.path.insert(0,str(root/'scripts'))
module=runpy.run_path(str(root/'scripts/publish_operational_update.py'),run_name='immutable_original_publisher')
returned=error=None
try:returned=module['publish'](root,scope='lifecycle-synthetic',repository='example/project',run_id='42',attempt='1')
except Exception as e:error={'type':type(e).__name__,'message':str(e)}
print('\\nAXIOM_ORIGINAL_RESULT='+json.dumps({'return_value':returned,'kernel_exception':error}))
'''
class WholeOperationalPublisherIntegrated(unittest.TestCase):
    def setUp(self):
        previous=os.umask(0o077);self.addCleanup(os.umask,previous)
        self.case=fixture.WholeLifecycleValidatorExecution();self.case.setUp();self.addCleanup(self.case.doCleanups)
        self.root=self.case.source;self.root.chmod(0o700);self.base=self.root.parent
        contract=json.loads((ORIGINAL/'contract.json').read_bytes());raw=(ORIGINAL/'publish_operational_update.py.txt').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),contract['files']['scripts/publish_operational_update.py']['sha256'])
        (self.root/'scripts/publish_operational_update.py').write_bytes(raw)
        self.env={k:v for k,v in os.environ.items() if not k.startswith(('GIT_','LD_','DYLD_'))}
        self.env.update(PYTHONDONTWRITEBYTECODE='1',GIT_CONFIG_GLOBAL='/dev/null',GIT_CONFIG_SYSTEM='/dev/null',GIT_CONFIG_NOSYSTEM='1',GIT_AUTHOR_DATE='2026-11-15T12:00:00+00:00',GIT_COMMITTER_DATE='2026-11-15T12:00:00+00:00')
        self.initial=self.case.base().strip();self.git('branch','-m','main')
        self.origin=self.base/'integrated-local-origin.git';subprocess.run(['git','clone','--bare',str(self.root),str(self.origin)],env=self.env,check=True,capture_output=True);self.origin.chmod(0o700);self.git('remote','add','origin',str(self.origin))
        self.provider=self.base/'publisher-provider';self.provider.mkdir(mode=0o700);self.calls=self.provider/'calls.jsonl'
        tool=self.provider/'gh';tool.write_text('#!'+sys.executable+'\n'+'''from pathlib import Path
import json,sys
assert sys.argv[1:4]==['api','--method','POST']
raw=sys.stdin.read()
with Path(__file__).with_name('calls.jsonl').open('a') as f:f.write(json.dumps({'arguments':sys.argv[1:],'input':raw})+'\\n')
if sys.argv[4].endswith('/pulls'):print(json.dumps({'number':123,'html_url':'https://github.com/example/project/pull/123'}))
''');tool.chmod(0o700);self.tool=tool;self.env['PATH']=str(self.provider)+os.pathsep+self.env.get('PATH','')
        self.output=self.base/'publisher-output';self.output.write_bytes(b'earlier=1\n');self.env['GITHUB_OUTPUT']=str(self.output)
    def git(self,*args):return subprocess.check_output(['git','-C',str(self.root),'-c','core.hooksPath=/dev/null',*args],env=self.env,stderr=subprocess.PIPE).decode()
    def run_case(self,damage=None):
        path=self.root/'status/governance-lifecycle-overview.json';path.write_bytes(path.read_bytes()+b'\n')
        if damage=='report':
            p=self.root/'generated/reports/governance-lifecycle-pilot.md';p.write_bytes(p.read_bytes()+b'wrong report\n')
        starting=snapshot(self.root);old=subprocess.run([sys.executable,'-B','-c',WRAPPER,str(self.root)],env=self.env,cwd=self.root,capture_output=True,timeout=300)
        self.assertEqual(old.returncode,0,old.stderr[-4000:]);parts=old.stdout.rsplit(b'\nAXIOM_ORIGINAL_RESULT=',1);self.assertEqual(len(parts),2);expected=json.loads(parts[1]);old_source=snapshot(self.root);old_branch=self.git('branch','--show-current');old_head=self.git('rev-parse','HEAD');old_calls=self.calls.read_bytes() if self.calls.exists() else b'';old_output=self.output.read_bytes()
        self.git('checkout','--force','main');self.git('reset','--hard',self.initial)
        if damage is None:
            self.git('branch','-D','automation/lifecycle-synthetic/42-1');subprocess.run(['git','--git-dir',str(self.origin),'update-ref','-d','refs/heads/automation/lifecycle-synthetic/42-1'],check=True,env=self.env,capture_output=True)
        for name,(raw,mode) in starting.items():
            p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);p.chmod(mode)
        self.calls.unlink(missing_ok=True);self.output.write_bytes(b'earlier=1\n')
        record=Record(self.case.private/'real-publisher-gate-records',{'test':'gate capture only'},{'test':True});record.append({'kind':'execution-intent'})
        owner=NativeRunIO(record,mode='private-candidate',cwd=str(self.root),private_state=self.case.private,ledger=ledger(str(self.root)),transaction_name=transaction_name)
        out,err=io.StringIO(),OrderedStderr();actual_gates=gates(str(self.root),str(self.root),owner,validator_class=Draft202012Validator,provider_executable=str(self.tool),temporary_parent=str(self.case.temporary),emit_stderr=err.emit_raw,environment=self.env)
        error=returned=None
        try:
            with redirect_stdout(out),redirect_stderr(err):
                try:
                    publisher,process=native_publisher(self.root,scope='lifecycle-synthetic',repository='example/project',run_id='42',attempt='1',gates=actual_gates,environment=self.env,provider_executable=str(self.tool),local_origin_root=self.base)
                    returned=publisher.publish(self.root,scope='lifecycle-synthetic',repository='example/project',run_id='42',attempt='1')
                except Exception as e:error={'type':type(e).__name__,'message':str(e)}
        finally:release(owner)
        self.assertEqual({'return_value':returned,'kernel_exception':error},expected)
        self.assertEqual(out.getvalue().encode(),parts[0]);self.assertEqual(err.getvalue().encode(),old.stderr)
        self.assertEqual(snapshot(self.root),old_source);self.assertEqual(self.git('branch','--show-current'),old_branch);self.assertEqual(self.git('rev-parse','HEAD'),old_head)
        self.assertEqual(self.calls.read_bytes() if self.calls.exists() else b'',old_calls);self.assertEqual(self.output.read_bytes(),old_output)
        return expected
    def test_whole_synthetic_publisher_with_real_prefix_pilot_overview_viewer_and_local_push(self):
        value=self.run_case();self.assertIsNone(value['kernel_exception']);self.assertEqual(value['return_value']['number'],123)
    def test_real_pilot_report_failure_stops_before_branch_push_or_POST(self):
        value=self.run_case('report');self.assertEqual(value['kernel_exception'],{'type':'ContractError','message':'Lifecycle pilot report differs from projection'});self.assertEqual(self.git('branch','--show-current'),'main\n');self.assertFalse(self.calls.exists())
