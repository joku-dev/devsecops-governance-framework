"""Explicit source-signature profile, original wires and private finding-exit behavior."""
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib import report_outputs, report_sources, report_multi_consumer, report_application
from lib.report_data import ReportData
from lib.functional_parity import git_read
from lib.provider_ports import committed_intake_signatures, CONFIGURATION_SOURCE_FILES
from lib.portable.contracts import canonical_digest
from lib.consumer_intake_store import atomic_json
from lib.report_application import ReportContext

AT = '2026-11-15T12:00:00Z'
PROFILE = report_outputs.configuration_profile('github-actions')


class ConfigurationWireTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = ROOT / 'tests/fixtures/axiom-v1-parity/configuration-readiness-cases.json'
        cls.fixture = json.loads(path.read_text()); memberpath = path.with_name(cls.fixture['membership_fixture'])
        assert hashlib.sha256(memberpath.read_bytes()).hexdigest() == cls.fixture['membership_fixture_sha256']
        cls.members = json.loads(memberpath.read_text())['cases']
        cls.temporary = tempfile.TemporaryDirectory(); cls.addClassCleanup(cls.temporary.cleanup)
        cls.snapshot = Path(cls.temporary.name).resolve() / 'snapshot'
        cls.manifest = report_sources.capture(ROOT, git_read(ROOT, 'rev-parse', 'HEAD').decode().strip(), cls.snapshot)
        cls.data = cls.snapshot / 'data'

    def build(self, data=None, membership=None, profile=PROFILE):
        return report_outputs.build(data or self.data, 'multi-consumer-readiness',
            membership=membership or self.manifest['membership'], at=AT, source_configuration_profile=profile)

    def test_all_original_positive_and_synthetic_negative_files_match_both_bound_contexts(self):
        self.assertEqual(self.fixture['v1_reference'], '6b557fefe295b58272d2271326576ca3a3687197')
        for case in self.fixture['cases']:
            members = next(c['membership'] for c in self.members if c['data_revision'] == case['data_revision'])
            self.assertEqual(hashlib.sha256(json.dumps(members, sort_keys=True, separators=(',', ':')).encode()).hexdigest(), case['membership_sha256'])
            for name, sha in case['source_files'].items():
                self.assertEqual(hashlib.sha256((self.data / name).read_bytes()).hexdigest(), sha)
            self.assertEqual(self.build(membership=members), {n: v.encode() for n, v in case['expected_outputs']['multi-consumer-readiness'].items()})
            self.assertEqual(case['expected_v1_exit'], 0); self.assertTrue(case['expected_ready'])
            for variant in case['negative_variants']:
                with tempfile.TemporaryDirectory() as temporary:
                    root = Path(temporary).resolve() / 'data'; shutil.copytree(self.data, root)
                    for name, raw in variant['synthetic_input_override'].items():
                        self.assertEqual(hashlib.sha256(raw.encode()).hexdigest(), variant['override_sha256'])
                        (root / name).write_bytes(raw.encode())
                    self.assertEqual(self.build(root, members), {n: v.encode() for n, v in variant['expected_outputs']['multi-consumer-readiness'].items()})
                    self.assertEqual(variant['expected_v1_exit'], 1); self.assertFalse(variant['expected_ready'])

    def test_readiness_consumes_committed_portfolio_and_health_not_fresh_builders(self):
        with patch('lib.report_portfolio.generate', side_effect=AssertionError('fresh projection forbidden')), \
             patch('lib.report_intake_health.generate', side_effect=AssertionError('fresh health forbidden')):
            self.assertEqual(self.build(), {n: v.encode() for n, v in self.fixture['cases'][-1]['expected_outputs']['multi-consumer-readiness'].items()})

    def test_no_profile_is_inferred_and_generic_all_excludes_configuration(self):
        with self.assertRaisesRegex(ValueError, 'explicit_source_configuration_profile_required'): self.build(profile=None)
        with self.assertRaisesRegex(ValueError, 'source_configuration_profile_not_applicable'):
            report_outputs.build(self.data, 'all', membership=self.manifest['membership'], at=AT, source_configuration_profile=PROFILE)
        files = report_outputs.build(self.data, 'all', membership=self.manifest['membership'], at=AT)
        self.assertEqual(len(files), 33)
        self.assertFalse(any('multi-consumer-readiness' in name for name in files))
        with self.assertRaisesRegex(ValueError, 'intake_health_window_not_applicable'):
            report_outputs.build(self.data, 'multi-consumer-readiness', membership=self.manifest['membership'], at=AT,
                                 source_configuration_profile=PROFILE, window_days=1)

    def test_missing_declared_native_file_is_not_replaced_by_an_ambient_file(self):
        members = deepcopy(self.manifest['membership']); members.pop(CONFIGURATION_SOURCE_FILES[0])
        with self.assertRaisesRegex(ValueError, 'uncommitted_report_input'): self.build(membership=members)

    def test_unknown_or_forged_profiles_are_rejected(self):
        for provider in ['gitlab-ci', 'bamboo', 'unknown']:
            with self.assertRaisesRegex(ValueError, 'unsupported_source_configuration_profile'):
                report_outputs.configuration_profile(provider)
        for change in [{'source_signature_only': False}, {'source_signature_only': 1}, {'extra': True}]:
            profile = {**PROFILE, **change}
            with self.assertRaisesRegex(ValueError, 'invalid_source_configuration_profile'): self.build(profile=profile)


class SourceSignaturePortTests(unittest.TestCase):
    def test_literal_observations_remain_explicitly_source_signatures_not_effective_configuration(self):
        content = b'# github.event.client_payload.repository_id || inputs.repository_id\n# github.event.client_payload.run_id || inputs.run_id\n# cancel-in-progress: false\n'
        seen = []
        def read(name): seen.append(name); return content
        facts = committed_intake_signatures('github-actions', read)
        self.assertEqual(seen, list(CONFIGURATION_SOURCE_FILES))
        self.assertTrue(all(all(row.values()) for row in facts.values()))
        self.assertTrue(PROFILE['source_signature_only'])

    def test_each_required_signature_has_an_independent_missing_fact(self):
        tokens = [b'github.event.client_payload.repository_id || inputs.repository_id',
                  b'github.event.client_payload.run_id || inputs.run_id', b'cancel-in-progress: false']
        names = ['repository_scope_expression_present', 'run_scope_expression_present', 'cancellation_disabled_signature_present']
        for i, name in enumerate(names):
            raw = b'\n'.join(token for j, token in enumerate(tokens) if j != i)
            facts = committed_intake_signatures('github-actions', lambda _: raw)
            self.assertTrue(all(row[name] is False for row in facts.values()))
            self.assertTrue(all(sum(row.values()) == 2 for row in facts.values()))

    def test_unsupported_provider_fails_before_any_native_file_read(self):
        def forbidden(_): raise AssertionError('must not read')
        with self.assertRaisesRegex(ValueError, 'unsupported_intake_configuration_profile'):
            committed_intake_signatures('gitlab-ci', forbidden)


class PrivateConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.node = Path(self.temporary.name).resolve() / 'node'; self.node.mkdir(mode=0o700)
        (self.node / 'state').mkdir(mode=0o700); self.settings = {'node_id': 'synthetic-configuration-node'}
        self.context = ReportContext(self.node, self.settings)

    def test_profile_is_immutable_source_bound_and_inspection_rechecks_complete_files(self):
        report_id, value = self.context.create('multi-consumer-readiness', AT, source_configuration_profile=PROFILE)
        self.assertEqual(self.context.inspect(report_id), value); self.assertTrue(self.context.configuration_ready(report_id))
        self.assertEqual(value['source_configuration_profile'], PROFILE)
        self.assertFalse(value['published']); self.assertFalse(value['official_acceptance']); self.assertFalse(value['provider_invoked'])
        path = self.context.artifacts / report_id / 'generated/reports/multi-consumer-readiness.md'
        original = path.read_bytes(); path.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'report_output_changed'): self.context.inspect(report_id)
        path.write_bytes(original)
        changed = deepcopy(value); changed['source_configuration_profile']['source_signature_only'] = False
        fake = canonical_digest(changed); atomic_json(self.context.assessments / (fake + '.json'), changed)
        with self.assertRaisesRegex(ValueError, 'invalid_report_assessment_contract'): self.context.inspect(fake)

    def test_generic_record_cannot_be_resealed_into_a_configuration_claim(self):
        report_id, value = self.context.create('graph', AT)
        self.assertIsNone(value['source_configuration_profile'])
        with self.assertRaisesRegex(ValueError, 'configuration_report_required'): self.context.configuration_ready(report_id)
        changed = deepcopy(value); changed['report_kind'] = 'multi-consumer-readiness'; changed['source_configuration_profile'] = PROFILE
        fake = canonical_digest(changed); atomic_json(self.context.assessments / (fake + '.json'), changed)
        with self.assertRaisesRegex(ValueError, 'report_differs_from_sources'): self.context.inspect(fake)

    def test_explicit_cli_and_synthetic_finding_exit_preserve_operator_choice(self):
        args = ['configuration', '--kind', 'multi-consumer-readiness', '--provider', 'github-actions', '--at', AT]
        output = io.StringIO()
        with redirect_stdout(output): self.assertEqual(report_application.run(args, self.node, self.settings), 0)
        receipt = json.loads(output.getvalue()); self.assertTrue(receipt['configuration_ready']); self.assertTrue(receipt['source_signature_only'])
        self.assertFalse(receipt['finding_exit_requested'])
        fixture = json.loads((ROOT / 'tests/fixtures/axiom-v1-parity/configuration-readiness-cases.json').read_text())
        variant = fixture['cases'][-1]['negative_variants'][0]
        payload = json.loads(variant['expected_outputs']['multi-consumer-readiness']['generated/reports/multi-consumer-readiness.json'])
        # Mock only the pure generator output for the local process-exit branch;
        # independent wire tests above execute actual normalized negative facts.
        with patch.object(report_multi_consumer, 'generate', return_value=payload):
            for flag, expected in [(False, 0), (True, variant['expected_v1_exit'])]:
                output = io.StringIO()
                with redirect_stdout(output):
                    self.assertEqual(report_application.run([*args, *(['--fail-on-findings'] if flag else [])], self.node, self.settings), expected)
                self.assertFalse(json.loads(output.getvalue())['configuration_ready'])
                self.assertEqual(json.loads(output.getvalue())['finding_exit_requested'], flag)

    def test_generic_build_command_cannot_implicitly_choose_a_native_profile(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            report_application.run(['build', '--kind', 'multi-consumer-readiness', '--at', AT], self.node, self.settings)
        self.assertEqual(error.exception.code, 2)


if __name__ == '__main__': unittest.main()
