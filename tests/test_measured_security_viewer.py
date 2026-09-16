from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

from jsonschema import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.measured_security import REPOSITORY, SERVICES, SEVERITIES, WORKFLOW, normalize, load_snapshots, store_snapshot, validate_snapshot
from lib.measured_security_view import render


class MeasuredSecurityTests(unittest.TestCase):
    def setUp(self):
        self.run = {'id': 42, 'run_attempt': 1, 'repository': {'full_name': REPOSITORY, 'id': 9},
            'head_branch': 'main', 'event': 'push', 'status': 'completed', 'conclusion': 'success',
            'path': WORKFLOW, 'head_sha': 'a' * 40, 'created_at': '2026-09-16T10:00:00Z',
            'updated_at': '2026-09-16T10:01:00Z'}
        context = {'repository': REPOSITORY, 'commit': 'a' * 40, 'run_id': '42', 'attempt': '1', 'event': 'push'}
        image_id = 'sha256:' + 'b' * 64
        self.report = {'context': context, 'report_type': 'l1-measured-evidence-coverage', 'evidence_errors': {},
            'official_compliance_result': False, 'production_approval': False, 'enforcement': 'report-only',
            'test_summary': {'pass': 57}, 'vulnerability_severities': {'HIGH': 5},
            'images': {s: {'image_id': image_id} for s in SERVICES}}
        self.bundles = {}
        for s in SERVICES:
            scan = {'Metadata': {'ImageID': image_id}, 'Results': [{'Class': 'os-pkgs', 'Packages': [{'Name': 'test'}], 'Vulnerabilities': [
                {'VulnerabilityID': 'CVE-2026-12345', 'Severity': 'HIGH', 'PkgName': 'test', 'InstalledVersion': '1'}]}]}
            files = {'subject.json': json.dumps({'service': s, 'commit': 'a' * 40, 'image_id': image_id}).encode(),
                'vulnerabilities.json': json.dumps(scan).encode(), 'vulnerabilities.execution.json': b'{"exit_code":0}'}
            manifest = {'context': context, 'files': {n: {'sha256': hashlib.sha256(b).hexdigest(), 'bytes': len(b)} for n, b in files.items()}}
            files['manifest.json'] = json.dumps(manifest).encode()
            artifact = {'name': 'l1-image-' + s, 'id': 3, 'expired': False, 'workflow_run': {
                'id': 42, 'repository_id': 9, 'head_sha': 'a' * 40, 'head_branch': 'main'}}
            self.bundles[s] = (files, artifact)

    def normalized(self):
        return normalize(self.run, self.report, self.bundles)

    def replace_raw(self, name, data):
        files = self.bundles['query-api'][0]
        files[name] = json.dumps(data).encode()
        manifest = json.loads(files['manifest.json'])
        manifest['files'][name] = {'sha256': hashlib.sha256(files[name]).hexdigest(), 'bytes': len(files[name])}
        files['manifest.json'] = json.dumps(manifest).encode()

    def test_duplicate_cve_is_not_duplicate_unique_count(self):
        item = self.normalized()
        self.assertEqual(item['counts']['HIGH'], 5)
        self.assertEqual(item['unique_cves']['HIGH'], 1)
        self.assertFalse(item['official_compliance_result'])
        self.assertFalse(item['risk_acceptance'])

    def test_pr_manual_failure_and_wrong_workflow_rejected(self):
        for field, value in [('event', 'pull_request'), ('event', 'workflow_dispatch'), ('head_branch', 'feature'),
                             ('conclusion', 'failure'), ('path', 'another.yml')]:
            with self.subTest(field=field, value=value):
                run = {**self.run, field: value}
                with self.assertRaises(ValueError):
                    normalize(run, self.report, self.bundles)

    def test_raw_tampering_rejected(self):
        self.bundles['query-api'][0]['vulnerabilities.json'] += b' '
        with self.assertRaisesRegex(ValueError, 'Changed raw'):
            self.normalized()

    def test_other_image_rejected_even_with_matching_manifest(self):
        scan = json.loads(self.bundles['query-api'][0]['vulnerabilities.json'])
        scan['Metadata']['ImageID'] = 'sha256:' + 'c' * 64
        self.replace_raw('vulnerabilities.json', scan)
        with self.assertRaisesRegex(ValueError, 'identity'):
            self.normalized()

    def test_other_attempt_and_artifact_rejected(self):
        self.report['context']['attempt'] = '2'
        with self.assertRaises(ValueError):
            self.normalized()
        self.report['context']['attempt'] = '1'
        self.bundles['query-api'][1]['workflow_run']['head_sha'] = 'd' * 40
        with self.assertRaises(ValueError):
            self.normalized()

    def test_mismatched_summary_and_failed_tool_rejected(self):
        self.report['vulnerability_severities']['HIGH'] = 0
        with self.assertRaisesRegex(ValueError, 'count mismatch'):
            self.normalized()
        self.report['vulnerability_severities']['HIGH'] = 5
        self.replace_raw('vulnerabilities.execution.json', {'exit_code': 2})
        with self.assertRaisesRegex(ValueError, 'execution'):
            self.normalized()

    def test_snapshot_cannot_promote_to_compliance_or_erase_findings(self):
        item = self.normalized()
        for field in ('official_compliance_result', 'risk_acceptance', 'independent_attestation'):
            with self.subTest(field=field), self.assertRaises(ValidationError):
                validate_snapshot({**item, field: True})
        item['images']['query-api']['findings'] = []
        with self.assertRaisesRegex(ValueError, 'details mismatch'):
            validate_snapshot(item)

    def test_append_only_idempotence_and_conflict(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            item = self.normalized()
            path = store_snapshot(root, item)
            self.assertEqual(path, store_snapshot(root, item))
            changed = deepcopy(item)
            changed['tests_passed'] += 1
            with self.assertRaisesRegex(ValueError, 'Conflicting'):
                store_snapshot(root, changed)
            self.assertEqual(json.loads(path.read_text()), item)

    def test_selection_uses_source_time_not_filename(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            old = self.normalized()
            old['run']['id'] = '900'
            new = deepcopy(old)
            new['run']['id'] = '1000'
            new['run']['created_at'] = '2026-09-16T11:00:00Z'
            store_snapshot(root, new)
            store_snapshot(root, old)
            self.assertEqual(load_snapshots(root)[-1]['run']['id'], '1000')
            new['run']['event'] = 'pull_request'
            with self.assertRaises(ValidationError):
                store_snapshot(root, new)

    def test_html_escapes_untrusted_packages_and_shows_snapshot_limits(self):
        item = self.normalized()
        item['images']['query-api']['findings'][0]['package'] = '<img src=x onerror=alert(1)>'
        html = render([item])
        self.assertNotIn('<img src=x', html)
        self.assertIn('&lt;img', html)
        self.assertIn('keine Live-Abfrage', html)
        self.assertIn('Governance-PASS bedeutet nicht schwachstellenfrei', html)
        self.assertIn('security-severity', html)
        self.assertIn('security-search', html)

    def test_no_data_is_not_zero_findings(self):
        self.assertIn('Keine erfassten Scan-Ergebnisse', render([]))

    def test_real_snapshots_cover_before_and_after(self):
        items = load_snapshots(ROOT / 'status/measured-security-results')
        self.assertGreaterEqual(len(items), 2)
        runs = {i['run']['id']: i for i in items}
        self.assertEqual([runs[r]['counts']['CRITICAL'] for r in ('35128325507', '35131185085')], [13, 1])
        self.assertEqual([runs[r]['counts']['HIGH'] for r in ('35128325507', '35131185085')], [373, 332])
        self.assertIn('13', render(items))
