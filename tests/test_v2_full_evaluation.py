"""Real pinned OPA against independently frozen V1 pass/finding reports."""
from pathlib import Path
import hashlib
import io
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from contextlib import redirect_stdout

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from lib.full_evaluation import evaluate, persist, validate
from lib.v2_application import initialize, run
from lib.v2_application import revision
from test_portable_runtime import OPA

AT='2026-11-15T12:00:00Z'
SOURCE=revision()
FIXTURES=ROOT/'tests/fixtures/axiom-v1-parity'


class FullAssessment(unittest.TestCase):
    def test_full_reports_match_frozen_v1_for_positive_and_negative_inputs(self):
        manifest=json.loads((FIXTURES/'manifest.json').read_text())
        self.assertEqual(manifest['v1_reference'],'6b557fefe295b58272d2271326576ca3a3687197')
        for case in manifest['cases']:
            with self.subTest(case=case['id']):
                source=ROOT/case['input'];golden=FIXTURES/case['report']
                self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),case['input_sha256'])
                self.assertEqual(hashlib.sha256(golden.read_bytes()).hexdigest(),case['report_sha256'])
                assessment=evaluate(case['domain'],source,opa=OPA,at=AT,source_revision=SOURCE)
                self.assertEqual(assessment['report'],json.loads(golden.read_text()))
                self.assertEqual(assessment['execution'],'complete')
                self.assertFalse(assessment['official_compliance_result'])
                self.assertEqual(assessment['evidence_trust'],'unverified')
                if case['domain']=='controls':self.assertEqual(assessment['report']['summary']['total_controls'],46)
                else:self.assertEqual(assessment['report']['summary']['gate_count'],4)

    def test_fake_opa_is_rejected_before_any_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            fake=Path(directory)/'opa';fake.write_bytes(b'not an OPA binary')
            with patch('lib.tool_integrity.subprocess.run',side_effect=AssertionError('must not execute')):
                with self.assertRaisesRegex(ValueError,'opa_checksum_mismatch'):
                    evaluate('controls',ROOT/'demo/inputs/release-candidate-green.json',opa=fake,at=AT,source_revision=SOURCE)

    def test_duplicate_input_keys_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'input.json';path.write_text('{"release_candidate":true,"release_candidate":false}')
            with self.assertRaisesRegex(ValueError,'duplicate_json_key'):
                evaluate('controls',path,opa=OPA,at=AT,source_revision=SOURCE)

    def test_input_bytes_are_frozen_across_policy_queries(self):
        from control_evaluation import generate_control_evaluation_report
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'input.json';original=(ROOT/'demo/inputs/release-candidate-green.json').read_bytes();path.write_bytes(original)
            def assess(snapshot,**kwargs):
                path.write_text('{}')
                return generate_control_evaluation_report(snapshot,**kwargs)
            with patch('control_evaluation.generate_control_evaluation_report',side_effect=assess):
                result=evaluate('controls',path,opa=OPA,at=AT,source_revision=SOURCE)
            self.assertEqual(result['input_sha256'],hashlib.sha256(original).hexdigest())
            self.assertEqual(result['report']['summary']['total_controls'],46)

    def test_real_instance_cli_persists_private_report_without_touching_source(self):
        with tempfile.TemporaryDirectory() as directory:
            instance=Path(directory)/'instance';initialize(instance,opa=OPA,development=True)
            output=io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(run('evaluate',['--domain','controls','--input',str(ROOT/'demo/inputs/release-candidate-red.json'),
                                               '--at',AT],instance_path=instance),0)
            summary=json.loads(output.getvalue());self.assertGreater(summary['summary']['fail'],0)
            report=instance/'state/assessments'/(summary['assessment_id']+'.json')
            self.assertTrue(report.is_file());self.assertEqual(report.stat().st_mode&0o077,0)
            self.assertEqual(json.loads(report.read_text())['mode'],'report-only')

    def test_assessment_state_cannot_be_redirected_by_symlink(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'state').mkdir();(root/'foreign').mkdir()
            (root/'state/assessments').symlink_to(root/'foreign',target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'unsafe_assessment_state'):persist({},root)

    def test_caller_cannot_claim_another_runtime_revision(self):
        with self.assertRaisesRegex(ValueError,'source_revision_mismatch'):
            evaluate('controls',ROOT/'demo/inputs/release-candidate-green.json',opa=OPA,at=AT,source_revision='0'*40)

    def test_tampered_counts_and_approval_flags_cannot_be_persisted(self):
        result=evaluate('controls',ROOT/'demo/inputs/release-candidate-red.json',opa=OPA,at=AT,source_revision=SOURCE)
        result['report']['summary']['fail']=0
        with self.assertRaisesRegex(ValueError,'summary_mismatch'):validate(result)
        result['official_compliance_result']=True
        with self.assertRaisesRegex(ValueError,'invalid_full_assessment'):validate(result)
