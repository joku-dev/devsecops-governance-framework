"""Complete original report bytes, committed input binding and private replay."""
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import shutil
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib import report_application, report_outputs, report_sources, report_graph
from lib.consumer_intake_store import atomic_json
from lib.functional_parity import git_read
from lib.portable.contracts import canonical_digest
from lib.report_data import ReportData, report_time


class CommittedReportSourceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve(); self.repo = self.base / 'repo'; self.repo.mkdir()
        self.git('init', '-q')
        p = self.repo / 'model/controls/example.yaml'; p.parent.mkdir(parents=True); p.write_text('value: original\n')
        self.git('add', '.'); self.git('-c', 'user.name=Synthetic test', '-c', 'user.email=test@example.invalid',
                                     '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'fixture')
        self.revision = self.git('rev-parse', 'HEAD').strip(); self.copy = self.base / 'copy'

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], text=True)

    def test_capture_uses_committed_bytes_and_ignores_ordinary_working_changes(self):
        (self.repo / 'model/controls/example.yaml').write_text('value: uncommitted\n')
        (self.repo / 'model/untracked.yaml').write_text('untracked: true\n')
        manifest = report_sources.capture(self.repo, self.revision, self.copy)
        self.assertEqual((self.copy / 'data/model/controls/example.yaml').read_text(), 'value: original\n')
        self.assertEqual(len(manifest['files']), 1)
        self.assertEqual(report_sources.verify(self.repo, self.revision, self.copy), manifest)

    def test_resealed_source_still_must_match_the_actual_git_blob(self):
        manifest = report_sources.capture(self.repo, self.revision, self.copy)
        raw = b'value: attacker\n'; (self.copy / 'data/model/controls/example.yaml').write_bytes(raw)
        row = manifest['files']['model/controls/example.yaml']
        row.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                   git_blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw, usedforsecurity=False).hexdigest())
        atomic_json(self.copy / 'manifest.json', manifest)
        with self.assertRaisesRegex(ValueError, 'git_binding_changed'):
            report_sources.verify(self.repo, self.revision, self.copy)

    def test_resealed_membership_cannot_invent_an_absent_historical_artifact(self):
        manifest = report_sources.capture(self.repo, self.revision, self.copy)
        manifest['membership']['scripts/retired.py'] = {'mode': '100644', 'git_blob': 'a' * 40, 'bytes': 0}
        atomic_json(self.copy / 'manifest.json', manifest)
        with self.assertRaisesRegex(ValueError, 'manifest_changed'):
            report_sources.verify(self.repo, self.revision, self.copy)

    def test_membership_retains_executable_identity_without_materializing_or_running_code(self):
        code = self.repo / 'scripts/retired.py'; code.parent.mkdir(); code.write_text('raise RuntimeError("never execute")\n')
        self.git('add', '.')
        self.git('-c', 'user.name=Synthetic test', '-c', 'user.email=test@example.invalid',
                 '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null', 'commit', '-qm', 'inert identity')
        revision = self.git('rev-parse', 'HEAD').strip()
        manifest = report_sources.capture(self.repo, revision, self.copy)
        data = ReportData(self.copy / 'data', manifest['membership'])
        path = data.root / 'scripts/retired.py'
        self.assertTrue(data.is_file(path)); self.assertTrue(data.exists(path.parent))
        self.assertFalse(path.exists())
        self.assertNotIn('scripts/retired.py', manifest['files'])
        with self.assertRaises(FileNotFoundError): data.raw(path)

    def test_unlisted_source_and_symlink_data_are_rejected(self):
        report_sources.capture(self.repo, self.revision, self.copy)
        extra = self.copy / 'data/extra.json'; extra.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'membership_changed'):
            report_sources.verify(self.repo, self.revision, self.copy)
        extra.unlink(); data = self.copy / 'data'; data.rename(self.copy / 'original')
        data.symlink_to(self.copy / 'original', target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'unsafe_retained_report_source'):
            report_sources.verify(self.repo, self.revision, self.copy)

    def test_source_quota_is_checked_before_materializing_blobs(self):
        with patch.object(report_sources, 'MAX_TOTAL', 1), self.assertRaisesRegex(ValueError, 'source_budget_exhausted'):
            report_sources.capture(self.repo, self.revision, self.copy)
        self.assertFalse(self.copy.exists())

    def test_oversized_manifest_is_rejected_before_it_is_written(self):
        with patch.object(report_sources, 'MAX_MANIFEST', 1), patch.object(report_sources, 'atomic_json') as write:
            with self.assertRaisesRegex(ValueError, 'source_manifest_budget_exhausted'):
                report_sources.capture(self.repo, self.revision, self.copy)
            write.assert_not_called()
        self.assertFalse((self.copy / 'manifest.json').exists())

    def test_enclosing_repository_and_nonexact_revision_are_rejected(self):
        sub = self.repo / 'nested'; sub.mkdir()
        for root, revision in [(sub, self.revision), (self.repo, 'HEAD')]:
            with self.subTest(root=root, revision=revision), self.assertRaisesRegex(ValueError, 'explicit_report_product_revision_required'):
                report_sources.inventory(root, revision)

    def test_missing_promised_blob_cannot_execute_a_repository_remote_helper(self):
        marker = self.base / 'untrusted-helper-ran'; helper = self.base / 'untrusted-helper.sh'
        helper.write_text('#!/bin/sh\n: > ' + shlex.quote(str(marker)) + '\nexit 1\n'); helper.chmod(0o700)
        blob = self.git('rev-parse', 'HEAD:model/controls/example.yaml').strip()
        (self.repo / '.git/objects' / blob[:2] / blob[2:]).unlink()
        for key, value in [('remote.origin.url', 'ext::' + str(helper)), ('remote.origin.promisor', 'true'),
                ('remote.origin.partialclonefilter', 'blob:none'), ('extensions.partialClone', 'origin'),
                ('protocol.ext.allow', 'always')]:
            self.git('config', key, value)
        with self.assertRaises(ValueError): git_read(self.repo, 'cat-file', 'blob', blob)
        self.assertFalse(marker.exists(), 'Reading inspected Git data must not execute its configured helper')


class ReportComputationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads((ROOT / 'tests/fixtures/axiom-v1-parity/reporting-cases.json').read_text())
        assert cls.fixture['v1_reference'] == '6b557fefe295b58272d2271326576ca3a3687197'
        cls.temporary = tempfile.TemporaryDirectory(); cls.addClassCleanup(cls.temporary.cleanup)
        cls.snapshot = Path(cls.temporary.name).resolve() / 'snapshot'
        revision = git_read(ROOT, 'rev-parse', 'HEAD').decode().strip()
        cls.manifest = report_sources.capture(ROOT, revision, cls.snapshot)
        cls.data = cls.snapshot / 'data'
        assert all(hashlib.sha256((cls.data / name).read_bytes()).hexdigest() == sha
                   for name, sha in cls.fixture['source_files'].items())

    def test_all_five_original_computations_return_all_six_exact_output_files(self):
        expected = {}
        for kind, files in self.fixture['expected_outputs'].items():
            with self.subTest(kind=kind):
                self.assertEqual(report_outputs.build(self.data, kind), {name: raw.encode() for name, raw in files.items()})
            expected.update({name: raw.encode() for name, raw in files.items()})
        self.assertEqual(len(expected), 6)
        extended = json.loads((ROOT / 'tests/fixtures/axiom-v1-parity/lineage-impact-cases.json').read_text())
        for files in extended['cases'][-1]['expected_outputs'].values():
            expected.update({name: raw.encode() for name, raw in files.items()})
        intake = json.loads((ROOT / 'tests/fixtures/axiom-v1-parity/source-intake-reporting-cases.json').read_text())
        for files in intake['cases'][-1]['expected_outputs'].values():
            expected.update({name: raw.encode() for name, raw in files.items()})
        models = json.loads((ROOT / 'tests/fixtures/axiom-v1-parity/model-followup-reporting-cases.json').read_text())
        for files in models['cases'][-1]['expected_outputs'].values():
            expected.update({name: raw.encode() for name, raw in files.items()})
        advisory = json.loads((ROOT / 'tests/fixtures/axiom-v1-parity/candidate-health-replay-cases.json').read_text())
        for files in advisory['cases'][-1]['expected_outputs'].values():
            expected.update({name: raw.encode() for name, raw in files.items()})
        self.assertEqual(report_outputs.build(self.data, 'all', membership=self.manifest['membership'], at=extended['at']), expected)
        self.assertEqual(len(expected), 31)
        csv = expected['generated/xlsx/traceability_matrix.csv']
        self.assertIn(b'\r\n', csv)
        self.assertNotIn(b'\r\r\n', csv)

    def test_graph_cannot_resolve_a_snapshot_outside_its_data_root(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve(); p = root / 'status/repository-results-index.json'; p.parent.mkdir()
            p.write_text(json.dumps({'repositories': [{'repository_id': 'synthetic/repo',
                'latest_result': {'pipeline_run_id': '1', 'source_file': '../outside.json'}}]}))
            with self.assertRaisesRegex(ValueError, 'invalid_v2_boundary_path'): report_graph.build_graph(root)

    def test_unknown_kind_cannot_dispatch_an_arbitrary_script(self):
        with self.assertRaisesRegex(ValueError, 'unsupported_report_kind'):
            report_outputs.build(self.data, 'scripts/generate_status_viewer.py')

    def test_both_original_lineage_and_impact_functions_match_all_output_bytes(self):
        fixture = json.loads((ROOT / 'tests/fixtures/axiom-v1-parity/lineage-impact-cases.json').read_text())
        self.assertEqual(fixture['v1_reference'], '6b557fefe295b58272d2271326576ca3a3687197')
        for case in fixture['cases']:
            for name, sha in case['source_files'].items():
                self.assertEqual(hashlib.sha256((self.data / name).read_bytes()).hexdigest(), sha)
            for kind, files in case['expected_outputs'].items():
                with self.subTest(revision=case['data_revision'], kind=kind):
                    self.assertEqual(report_outputs.build(self.data, kind, membership=case['membership'], at=fixture['at']),
                                     {name: raw.encode() for name, raw in files.items()})

    def test_lineage_requires_explicit_membership_and_a_timezone(self):
        with self.assertRaisesRegex(ValueError, 'explicit_report_membership_and_time_required'):
            report_outputs.build(self.data, 'source-lineage')
        with self.assertRaisesRegex(ValueError, 'explicit_result_timezone_required'):
            report_outputs.build(self.data, 'change-impact', membership=self.manifest['membership'], at='2026-11-15T12:00:00')
        self.assertEqual(report_time('2026-11-15T13:00:00.123+01:00'), '2026-11-15T12:00:00Z')

    def test_membership_does_not_allow_escape_links_or_uncommitted_source_reads(self):
        data = ReportData(self.data, self.manifest['membership'])
        with self.assertRaises(ValueError): data.exists(data.root / '../outside')
        with self.assertRaisesRegex(ValueError, 'uncommitted_report_input'): data.raw(data.root / 'untracked.json')
        with self.assertRaisesRegex(ValueError, 'unsupported_report_glob'): data.glob(data.root / 'model', '**/*')
        bad = {'bad': {'mode': '120000'}}
        with self.assertRaisesRegex(ValueError, 'unsafe_report_member'): ReportData(self.data, bad)

    def test_change_impact_recomputes_lineage_without_trusting_the_retained_report(self):
        fixture = json.loads((ROOT / 'tests/fixtures/axiom-v1-parity/lineage-impact-cases.json').read_text())
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary).resolve() / 'copy'; shutil.copytree(self.data, target)
            (target / 'generated/reports/source-lineage-report.json').write_text('{"lineage": []}')
            actual = report_outputs.build(target, 'change-impact', membership=self.manifest['membership'], at=fixture['at'])
            self.assertEqual(actual, {name: raw.encode() for name, raw in fixture['cases'][-1]['expected_outputs']['change-impact'].items()})


class ReportAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve(); self.node = self.base / 'node'; self.node.mkdir(mode=0o700)
        self.settings = {'node_id': 'synthetic-report-node'}; self.at = '2026-11-15T12:00:00Z'

    def context(self, settings=None): return report_application.ReportContext(self.node, settings or self.settings)

    def test_private_build_inspect_and_idempotent_repeat_reproduce_complete_outputs(self):
        context = self.context(); assessment_id, value = context.create('all', self.at)
        self.assertEqual(self.context().inspect(assessment_id), value)
        self.assertEqual(self.context().create('all', self.at), (assessment_id, value))
        for field in ['official_acceptance', 'authority_transferred', 'published', 'provider_invoked',
                      'working_tree_used', 'production_approval', 'operating_acceptance_inherited']:
            self.assertFalse(value[field])
        self.assertEqual(value['source_scope'], 'committed-governance-data-v2')
        fixture = json.loads((ROOT / 'tests/fixtures/axiom-v1-parity/reporting-cases.json').read_text())
        for files in fixture['expected_outputs'].values():
            for name, raw in files.items(): self.assertEqual((context.artifacts / assessment_id / name).read_bytes(), raw.encode())

    def test_source_and_output_corruption_are_detected_without_repair(self):
        context = self.context(); assessment_id, value = context.create('graph', self.at)
        output = context.artifacts / assessment_id / next(iter(value['files']))
        original = output.read_bytes(); output.write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'report_output_changed'): self.context().inspect(assessment_id)
        self.assertEqual(output.read_bytes(), b'corrupt'); output.write_bytes(original)
        raw = context.sources / value['source_revision'] / 'data/model/documents/source-document-register.yaml'
        raw.write_text('documents: []\n')
        with self.assertRaisesRegex(ValueError, 'source_bytes_changed'): self.context().inspect(assessment_id)

    def test_resealed_derived_report_must_still_equal_its_original_sources(self):
        context = self.context(); assessment_id, value = context.create('control-coverage', self.at)
        changed = deepcopy(value); name = next(iter(changed['files'])); raw = b'changed report\n'
        changed['files'][name] = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
        fake_id = canonical_digest(changed); shutil.copytree(context.artifacts / assessment_id, context.artifacts / fake_id)
        (context.artifacts / fake_id / name).write_bytes(raw); atomic_json(context.assessments / (fake_id + '.json'), changed)
        with self.assertRaisesRegex(ValueError, 'report_differs_from_sources'): self.context().inspect(fake_id)

    def test_foreign_node_and_authority_flag_changes_are_rejected(self):
        context = self.context(); assessment_id, value = context.create('traceability', self.at)
        with self.assertRaisesRegex(ValueError, 'node_runtime_or_source_changed'):
            self.context({'node_id': 'foreign'}).inspect(assessment_id)
        changed = deepcopy(value); changed['official_acceptance'] = True
        fake_id = canonical_digest(changed); atomic_json(context.assessments / (fake_id + '.json'), changed)
        with self.assertRaisesRegex(ValueError, 'invalid_report_assessment_contract'): self.context().inspect(fake_id)

    def test_output_quota_failure_does_not_publish_a_partial_assessment(self):
        context = self.context()
        with patch.object(report_application, 'MAX_OUTPUT', 1), self.assertRaisesRegex(ValueError, 'output_budget_exhausted'):
            context.create('all', self.at)
        self.assertEqual(list(context.assessments.iterdir()), [])
        self.assertEqual(list(context.artifacts.iterdir()), [])

    def test_actual_serialized_record_limit_is_enforced(self):
        context = self.context(); _, value = context.create('traceability', self.at)
        compact_size = len(json.dumps(value, sort_keys=True).encode())
        with patch.object(report_application, 'MAX_RECORD', compact_size + 1), self.assertRaisesRegex(ValueError, 'record_budget_exhausted'):
            context.validate(value)

    def test_finite_cli_build_and_inspect_expose_private_files_without_publishing(self):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(report_application.run(['build', '--kind', 'governance-traceability', '--at', self.at],
                                                   self.node, self.settings), 0)
        receipt = json.loads(out.getvalue()); self.assertFalse(receipt['published'])
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(report_application.run(['inspect', '--id', receipt['assessment_id']], self.node, self.settings), 0)
        self.assertTrue(json.loads(out.getvalue())['original_sources_and_complete_outputs_reverified'])


if __name__ == '__main__': unittest.main()
