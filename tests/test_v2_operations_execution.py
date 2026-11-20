"""Whole immutable original main: schema, source/clock, three files and streams."""
from contextlib import redirect_stdout,redirect_stderr
from copy import deepcopy
from datetime import datetime,timezone
import io,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'scripts'),str(ROOT/'tests')]
from lib.operations_execution import execute,FILES
from lib.providers import operations_report_profile as profile
from lib.v2_boundary import violations
from test_v2_operations_reporting import OLD,FIXTURES

NOW=datetime(2026,9,9,12,0,0,123456,tzinfo=timezone.utc)


class Files:
    def __init__(self,root):self.root=root;self.order=[]
    def mkdir(self):self.order.append('mkdir');self.root.mkdir(parents=True,exist_ok=True)
    def write(self,name,raw):self.order.append(name);return (self.root/name).write_bytes(raw)


class Environment:
    def __init__(self,root,observation,*,allow_live=True):self.root=root;self.observation=observation;self.calls=[];self.allow_live=allow_live
    def config_text(self):self.calls.append('config');return (self.root/'config.json').read_text()
    def schema_text(self):self.calls.append('schema');return (self.root/'schemas/governance-operations-report.schema.json').read_text()
    def observation_text(self):self.calls.append('provided-observation');return (self.root/'observation.json').read_text()
    def utc_now(self):self.calls.append('clock');return NOW.replace(microsecond=0)
    def collect(self,config,now):
        self.calls.append('collect')
        if not self.allow_live:raise ValueError('operations_explicit_live_collection_required')
        return deepcopy(self.observation)
    def checkout_sha(self):self.calls.append('checkout-sha');return 'b'*40


class WholeOperationsExecutionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        (self.root/'schemas').mkdir();(self.root/'schemas/governance-operations-report.schema.json').write_bytes((ROOT/'schemas/governance-operations-report.schema.json').read_bytes())
        (self.root/'config.json').write_bytes((ROOT/'.github/operations-report.json').read_bytes())
        fixture=FIXTURES.OperationsReportTests();fixture.setUp();self.observation=fixture.observation
        self.observation['observed_at']='2026-09-09T12:00:00Z'
    def compare(self,*,provided=True,as_of=None,raw=None,fail_file=None):
        root=self.root
        (root/'observation.json').write_text(json.dumps(self.observation) if raw is None else raw)
        oldout=root/'old';newout=root/'new'
        for out in (oldout,newout):
            if fail_file:
                out.mkdir(exist_ok=True)
                if fail_file=='mkdir':out.rmdir();out.write_text('existing non-directory')
                else:(out/fail_file).mkdir()
        args=['original','--config',str(root/'config.json'),'--output-dir',str(oldout)]
        if provided:args+=['--observation',str(root/'observation.json')]
        if as_of is not None:args+=['--as-of',as_of]
        class Clock(datetime):
            @classmethod
            def now(cls,*args):return NOW
        stdout=io.StringIO();stderr=io.StringIO();original_error=None;code=None
        with patch.object(OLD,'ROOT',root),patch.object(OLD,'datetime',Clock),patch.object(OLD.subprocess,'check_output',return_value='b'*40+'\n') as head,patch.object(OLD,'collect',return_value=deepcopy(self.observation)) as acquire,patch.object(sys,'argv',args),redirect_stdout(stdout),redirect_stderr(stderr):
            try:code=OLD.main()
            except Exception as error:original_error=error
        env=Environment(root,self.observation);outputs=Files(newout)
        if original_error is None:
            actual=execute(provided_observation=provided,as_of=as_of,environment=env,output=outputs,profile=profile)
            self.assertEqual(actual,{'exit_code':code,'stdout':stdout.getvalue(),'stderr':stderr.getvalue()})
            self.assertEqual(outputs.order,['mkdir',*FILES])
        else:
            with self.assertRaises(type(original_error)):execute(provided_observation=provided,as_of=as_of,environment=env,output=outputs,profile=profile)
        for name in FILES:
            a=oldout/name;b=newout/name
            self.assertEqual(a.is_file(),b.is_file(),name)
            if a.is_file():self.assertEqual(a.read_bytes(),b.read_bytes(),name)
        self.assertEqual(acquire.call_count,env.calls.count('collect'))
        self.assertEqual(head.call_count,env.calls.count('checkout-sha'))
        return env
    def test_whole_provided_main_streams_and_three_ordered_export_bytes(self):self.compare()
    def test_whole_admitted_live_main_and_captured_observation(self):self.compare(provided=False)
    def test_explicit_time_overrides_observation_and_implicit_clock_has_no_microseconds(self):
        self.compare(as_of='2026-09-09T14:00:00+02:00')
        self.observation.pop('observed_at');env=self.compare()
        self.assertIn('clock',env.calls)
        self.assertEqual(json.loads((self.root/'new/governance-operations.json').read_bytes())['generated_at'],'2026-09-09T12:00:00Z')
    def test_original_null_provided_fallback_is_only_available_to_an_admitted_collection_port(self):
        self.compare(raw='null')
        env=Environment(self.root,self.observation,allow_live=False)
        with self.assertRaisesRegex(ValueError,'operations_explicit_live_collection_required'):
            execute(provided_observation=True,as_of=None,environment=env,output=Files(self.root/'denied'),profile=profile)
        self.assertNotIn('checkout-sha',env.calls);self.assertFalse((self.root/'denied').exists())
    def test_config_validation_precedes_malformed_observation_and_all_output(self):
        value=json.loads((self.root/'config.json').read_bytes());value['review_warning_hours']=0;(self.root/'config.json').write_text(json.dumps(value))
        env=self.compare(raw='malformed');self.assertEqual(env.calls,['config','schema'])
    def test_invalid_observation_json_shape_and_time_preserve_original_failures(self):
        for raw in ('bad JSON','[1]','[]','{"observed_at":"bad timestamp"}'):
            with self.subTest(raw=raw):self.compare(raw=raw)
    def test_each_partial_write_boundary_keeps_the_same_preceding_whole_files(self):
        for name in ('mkdir',*FILES):
            with self.subTest(name=name),tempfile.TemporaryDirectory() as d:
                saved=self.root;self.root=Path(d)
                (self.root/'schemas').mkdir();(self.root/'schemas/governance-operations-report.schema.json').write_bytes((saved/'schemas/governance-operations-report.schema.json').read_bytes())
                (self.root/'config.json').write_bytes((saved/'config.json').read_bytes())
                try:self.compare(fail_file=name)
                finally:self.root=saved
    def test_neutral_execution_selects_no_provider_or_environment_program(self):
        self.assertEqual(violations('scripts/lib/operations_execution.py',(ROOT/'scripts/lib/operations_execution.py').read_text()),[])


if __name__=='__main__':unittest.main()
