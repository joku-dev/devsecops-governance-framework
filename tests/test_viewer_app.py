"""Protect official selection, missing evidence and the presentation build boundary."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from jsonschema import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.viewer_app import project, build, load_repository_security
from lib.measured_security import load_snapshots
from lib.control_evidence_assurance import build_assurance
from publish_operational_update import allowed


class ViewerAppTests(unittest.TestCase):
    def setUp(self):
        self.dev = json.loads((ROOT / 'status/repository-results-index.json').read_text())
        self.arch = json.loads((ROOT / 'status/architecture-results-index.json').read_text())
        self.scans = load_snapshots(ROOT / 'status/measured-security-results')

    def test_official_latest_is_not_inferred_from_history(self):
        official = deepcopy(self.dev['repositories'][0]['latest_result'])
        self.dev['repositories'][0]['history'].append({'status':'pass','generated_at':'2099-01-01T00:00:00Z','pipeline_event':'pull_request'})
        data = project(self.dev, self.arch, self.scans)
        repo = next(r for r in data['repositories'] if r['id']==self.dev['repositories'][0]['repository_id'])
        self.assertEqual(official, repo['devsecops'])

    def test_missing_results_are_not_pass_or_zero_scan(self):
        data = project({'repositories':[{'repository_id':'org/empty','history':[]}]}, {'repositories':[]}, [])
        repo = data['repositories'][0]
        self.assertIsNone(repo['devsecops'])
        self.assertIsNone(repo['architecture'])
        self.assertIsNone(repo['security'])
        self.assertEqual([], repo['findings'])

    def test_measured_history_sorted_and_attempts_preserved(self):
        first = deepcopy(self.scans[0]); later = deepcopy(self.scans[-1])
        attempt = deepcopy(later); attempt['run']['attempt'] += 1
        data = project({'repositories':[]}, {'repositories':[]}, [attempt, first, later])
        repo = data['repositories'][0]
        self.assertEqual(attempt, repo['security'])
        self.assertEqual([attempt['run'],later['run'],first['run']], [s['run'] for s in repo['security_history']])

    def test_scan_selection_uses_instants_not_timestamp_strings(self):
        earlier = deepcopy(self.scans[0]); later = deepcopy(self.scans[-1])
        earlier['run']['created_at'] = '2026-09-16T12:00:00+02:00'
        later['run']['created_at'] = '2026-09-16T11:00:00Z'
        data = project({'repositories':[]}, {'repositories':[]}, [later, earlier])
        self.assertEqual(later, data['repositories'][0]['security'])

    def test_occurrences_and_distinct_ids_are_different(self):
        data = project(self.dev,self.arch,self.scans)
        repo = next(r for r in data['repositories'] if r['id']=='joku-dev/ha-CPsWMS')
        total = repo['security']['counts']['HIGH'] + repo['security']['counts']['CRITICAL']
        self.assertEqual(total, sum(f['occurrences'] for f in repo['findings']))
        self.assertLess(len({f['id'] for f in repo['findings']}),total)
        self.assertEqual('CRITICAL',repo['findings'][0]['severity'])
        self.assertTrue(any(len(f['images'])>1 for f in repo['findings']))

    def test_projection_does_not_change_inputs(self):
        before = deepcopy((self.dev,self.arch,self.scans))
        project(self.dev,self.arch,self.scans)
        self.assertEqual(before,(self.dev,self.arch,self.scans))

    def test_control_assurance_is_selected_separately_from_l1_assessment(self):
        measured=json.loads(next((ROOT/'status/measured-l1-results/joku-dev__ha-CPsWMS').glob('*.json')).read_text())
        assurance=build_assurance(measured,[],measured_source_file='status/measured-l1-results/joku-dev__ha-CPsWMS/run-35131185085-attempt-1.json',verified_at='2026-09-16T18:00:00Z')
        data=project(self.dev,self.arch,self.scans,[measured],[assurance])
        repo=next(row for row in data['repositories'] if row['id']=='joku-dev/ha-CPsWMS')
        self.assertEqual(measured,repo['l1_assessment'])
        self.assertEqual(assurance,repo['control_assurance'])
        self.assertEqual(16,repo['control_assurance']['summary']['total_controls'])

    def test_repository_security_report_is_validated_and_projected(self):
        report = load_repository_security(ROOT)
        self.assertEqual('joku-dev/devsecops-governance-framework', report['repository_id'])
        self.assertEqual(16, report['summary']['criteria'])
        self.assertEqual(13, report['summary']['pass'])
        self.assertEqual(3, report['summary']['fail'])
        self.assertEqual(
            ['GRS-002', 'GRS-005', 'GRS-014'],
            [item['id'] for item in report['criteria'] if item['status'] == 'fail'],
        )
        self.assertNotIn('observation', report)
        self.assertEqual(
            'generated/reports/governance-repository-security.json',
            report['source_file'],
        )

    def test_deterministic_build_and_separate_assets(self):
        import shutil
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            shutil.copytree(ROOT/'apps/governance-viewer',root/'apps/governance-viewer')
            (root/'status').mkdir()
            for name,data in [('repository-results-index.json',self.dev),('architecture-results-index.json',self.arch)]:
                (root/'status'/name).write_text(json.dumps(data))
            shutil.copytree(ROOT/'status/measured-security-results',root/'status/measured-security-results')
            shutil.copytree(ROOT/'generated/reports',root/'generated/reports')
            (root/'schemas').mkdir()
            shutil.copyfile(
                ROOT/'schemas/governance-repository-security-report.schema.json',
                root/'schemas/governance-repository-security-report.schema.json',
            )
            build(root)
            first={p.name:p.read_bytes() for p in (root/'generated/viewer/app').iterdir()}
            build(root)
            self.assertEqual(first,{p.name:p.read_bytes() for p in (root/'generated/viewer/app').iterdir()})
            self.assertEqual({'index.html','app.css','app.js','technical.js','technical.css','data.json'},set(first))
            self.assertIn(b"script-src 'self'",first['index.html'])
            payload=json.loads(first['data.json'])
            self.assertEqual(13,payload['repository_security']['summary']['pass'])

    def test_operational_intake_cannot_publish_application_artifacts(self):
        for scope in ('devsecops','architecture','typed-evidence'):
            self.assertFalse(allowed('generated/viewer/app/data.json',scope))
            for name in ('app.js','app.css','index.html'):
                self.assertFalse(allowed('generated/viewer/app/'+name,scope))
            self.assertFalse(allowed('apps/governance-viewer/app.js',scope))

    def test_build_rejects_invalid_security_evidence(self):
        import shutil
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'status/measured-security-results/org').mkdir(parents=True)
            for name,data in [('repository-results-index.json',self.dev),('architecture-results-index.json',self.arch)]:
                (root/'status'/name).write_text(json.dumps(data))
            invalid=deepcopy(self.scans[0]);invalid['official_compliance_result']=True
            (root/'status/measured-security-results/org/run-invalid.json').write_text(json.dumps(invalid))
            with self.assertRaises(ValidationError): build(root)
            self.assertFalse((root/'generated/viewer/app/data.json').exists())

    def test_repository_security_projection_rejects_invalid_report(self):
        import shutil
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            shutil.copytree(ROOT/'generated/reports',root/'generated/reports')
            (root/'schemas').mkdir()
            shutil.copyfile(
                ROOT/'schemas/governance-repository-security-report.schema.json',
                root/'schemas/governance-repository-security-report.schema.json',
            )
            report_path=root/'generated/reports/governance-repository-security.json'
            report=json.loads(report_path.read_text())
            report['overall_status']='pass'
            report['summary']['fail']=-1
            report_path.write_text(json.dumps(report))
            with self.assertRaises(ValidationError):
                load_repository_security(root)
