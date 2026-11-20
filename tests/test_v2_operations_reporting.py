"""Whole immutable-V1 operational reports and presentation, without native claims."""
from copy import deepcopy
from importlib.machinery import SourceFileLoader
import ast,hashlib,importlib.util,json,sys,unittest
from pathlib import Path
from jsonschema import Draft202012Validator

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from lib import operations_reporting as core
from lib.providers import operations_report_profile as profile
from lib.v2_boundary import violations


def load(name,path,digest):
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
    loader=SourceFileLoader(name,str(path));spec=importlib.util.spec_from_loader(name,loader)
    module=importlib.util.module_from_spec(spec);loader.exec_module(module);return module


OLD=load('immutable_V1_operations',ROOT/'tests/fixtures/v2-operations-report-original/generate_operations_report.py.txt',
         'a390f8bc7cac07201efef4623ab50331e6d8793c0a418bca425b9a40ed493448')
FIXTURES=load('immutable_V1_operations_testdata',ROOT/'tests/test_operations_report.py',
              '40c38f8294e6a062e749865f41700baf768c5cd967fac880704e3d90b532754c')
CASES=[]


class CompleteOperationalDecisions(FIXTURES.OperationsReportTests):
    # Those original cases concern the as-yet-unported collector/workflow.
    # They must not be counted as execution of a new whole counterpart.
    test_collector_uses_schedule_event_and_preserves_access_errors=None
    test_workflow_only_reads_and_retains_observations=None

    def report(self):
        before=deepcopy(self.observation)
        expected=OLD.build_report(self.observation,self.config,self.now,'b'*40)
        actual=core.build_report(self.observation,self.config,self.now,'b'*40,profile=profile)
        self.assertEqual(actual,expected)
        expected_raw=(json.dumps(expected,indent=2)+'\n').encode()
        actual_raw=(json.dumps(actual,indent=2)+'\n').encode()
        self.assertEqual(actual_raw,expected_raw)
        self.assertEqual(core.render_markdown(actual),OLD.render_markdown(expected))
        self.assertEqual(self.observation,before)
        self.assertEqual(sum(actual['summary'].values()),len(actual['checks']))
        self.assertEqual(actual['decision_boundary'],{'changes_official_results':False,'approves_prs':False,'changes_enforcement':False})
        Draft202012Validator(self.schema,format_checker=Draft202012Validator.FORMAT_CHECKER).validate(actual)
        CASES.append({'whole_report_sha256':hashlib.sha256(actual_raw).hexdigest(),
                      'whole_markdown_sha256':hashlib.sha256(core.render_markdown(actual).encode()).hexdigest(),
                      'whole_report_equal':True,'whole_markdown_equal':True,'checks':len(actual['checks'])})
        return actual

    def test_complete_PR_age_review_merge_and_draft_combinations(self):
        for merge in ('CLEAN','DIRTY','BEHIND','UNSTABLE','BLOCKED',None):
            for review in ('APPROVED','REVIEW_REQUIRED','CHANGES_REQUESTED',None):
                for draft in (True,False):
                    with self.subTest(merge=merge,review=review,draft=draft):
                        self.observation['pull_requests']=[{'number':1,'createdAt':'2026-09-09T11:00:00Z',
                            'reviewDecision':review,'mergeStateStatus':merge,'isDraft':draft,'url':'https://example.invalid/pr/1'}]
                        self.report()

    def test_all_intake_states_and_invalid_timestamps_keep_full_window_semantics(self):
        for status in ('completed','queued','in_progress'):
            for conclusion in ('success','failure','cancelled','skipped',None):
                for created in ('2026-09-09T11:00:00Z','2026-09-09T01:00:00Z','2026-09-01T00:00:00Z','bad'):
                    with self.subTest(status=status,conclusion=conclusion,created=created):
                        self.observation['workflow_runs'][profile.INTAKES[0]]=[dict(self.run,status=status,conclusion=conclusion,created_at=created)]
                        self.report()

    def test_complete_missing_security_inputs_and_expected_error_text(self):
        for errors in ([],['HTTP 404'],['HTTP 403'],['path: http_404'],['unrelated HTTP 404 suffix'],['HTTP 404','HTTP 500']):
            for missing in (True,False):
                with self.subTest(errors=errors,missing=missing):
                    self.observation['security']['observation']['api_errors']=errors
                    self.observation['security']['observation']['repository']['visibility']=None if missing else 'public'
                    self.report()

    def test_typed_evidence_whole_verification_state_and_optional_domain_handling(self):
        for collector in ('collected','failed',None):
            for findings in (0,1):
                for freshness in ('pass','fail',None):
                    with self.subTest(collector=collector,findings=findings,freshness=freshness):
                        latest=dict(self.latest,collector_status=collector,finding_count=findings,freshness=freshness,content_integrity='pass',replay='pass')
                        self.observation['indexes']['typed_evidence']['repositories']=[{'repository_id':'owner/consumer','latest_result':latest}]
                        self.report()

    def test_unknown_or_empty_registry_indexes_health_security_are_not_success(self):
        for key in ('registry','intake_health','security'):
            original=deepcopy(self.observation[key])
            for value in (None,{}):
                with self.subTest(key=key,value=value):
                    self.observation[key]=value
                    if key=='intake_health' and value=={}:
                        # The original distinguishes absent telemetry from a
                        # malformed non-null object and raises for the latter.
                        with self.assertRaises(KeyError):OLD.build_report(self.observation,self.config,self.now,'b'*40)
                        with self.assertRaises(KeyError):core.build_report(self.observation,self.config,self.now,'b'*40,profile=profile)
                    else:self.report()
            self.observation[key]=original
        for domain in profile.INDEXES:
            original=self.observation['indexes'][domain]
            self.observation['indexes'][domain]=None;self.report();self.observation['indexes'][domain]=original

    def test_invalid_observation_shapes_preserve_original_exceptions(self):
        for observation in (None,{'errors':None},{'errors':[None]},{'workflow_runs':None}):
            with self.subTest(observation=observation):
                try:OLD.build_report(observation,self.config,self.now,'b'*40)
                except Exception as error:
                    with self.assertRaises(type(error)) as caught:core.build_report(observation,self.config,self.now,'b'*40,profile=profile)
                    self.assertEqual(str(caught.exception),str(error))
                else:self.fail('Original malformed shape unexpectedly returned')

    def test_three_pure_functions_are_exact_original_AST_and_core_has_no_provider_access(self):
        before={n.name:n for n in ast.parse((ROOT/'tests/fixtures/v2-operations-report-original/generate_operations_report.py.txt').read_bytes()).body if isinstance(n,ast.FunctionDef)}
        after={n.name:n for n in ast.parse((ROOT/'scripts/lib/operations_reporting.py').read_bytes()).body if isinstance(n,ast.FunctionDef)}
        for name in ('timestamp','age_hours','render_markdown'):
            self.assertEqual(ast.dump(after[name],include_attributes=False),ast.dump(before[name],include_attributes=False))
        self.assertEqual(violations('scripts/lib/operations_reporting.py',(ROOT/'scripts/lib/operations_reporting.py').read_text()),[])


if __name__=='__main__':unittest.main()
