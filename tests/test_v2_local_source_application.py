"""Product routes, original whole wires and retained local observation boundaries."""
from contextlib import redirect_stdout
from copy import deepcopy
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests/acceptance')]
from lib import local_source_application as app, source_inspection_application as route
from lib.consumer_intake_store import atomic_json
from lib.portable.contracts import canonical_digest
from lib.provider_ports import local_source_profile
from v1_source_inspection_oracle import load_fixture, make_repository, original_files

FIXTURES = ROOT / 'tests/fixtures/axiom-v1-parity/source-inspection'
AT = '2026-11-15T12:00:00Z'; PROFILE = local_source_profile('legacy-worktree-signatures-v1')


class LocalSourceApplicationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve(); self.fixture = load_fixture(FIXTURES)
        self.repository = self.base / 'consumer'; make_repository(self.repository, self.fixture['cases'][0])
        self.settings = {'node_id': 'synthetic-local-node', 'product': 'axiom-v2'}
        self.node = self.base / 'node'; self.node.mkdir(mode=0o700)
        self.context = app.LocalSourceInspectionContext(self.node, self.settings)

    def create(self, **changes):
        args = dict(kind='all', repository=self.repository, repository_id='synthetic/local', profile=deepcopy(PROFILE), at=AT)
        args.update(changes); return self.context.create(**args)

    def command(self, *args):
        stream = io.StringIO()
        with redirect_stdout(stream): code = route.run(list(args), self.node, self.settings)
        return code, stream.getvalue()

    def observe(self, kind='all', *args):
        return self.command('observe', '--kind', kind, '--target-repo', str(self.repository),
            '--profile', PROFILE['profile'], '--at', AT, *args)

    def assert_outputs(self, identifier, expected):
        root = self.context.artifacts / identifier
        self.assertEqual({p.name for p in root.iterdir()}, {Path(name).name for name in expected})
        for name, raw in expected.items(): self.assertEqual((root / Path(name).name).read_bytes(), raw)

    def test_complete_original_files_positive_missing_binary_and_nongit_modes(self):
        for case in self.fixture['cases']:
            target = self.base / case['id']; make_repository(target, case); shutil.rmtree(target / '.git')
            expected, exits = original_files(FIXTURES, self.base / ('oracle-' + case['id']), target, 'synthetic/local', AT)
            identifier, value = self.create(repository=target)
            self.assertEqual(self.context.inspect(identifier), value); self.assert_outputs(identifier, expected)
            self.assertEqual(self.context.legacy_exit(identifier), max(exits))
            self.assertEqual(self.create(repository=target)[0], identifier)
            self.assertTrue(value['working_tree_used']); self.assertFalse(value['content_commit_verified'])
            self.assertNotIn('consumer_commit', value); self.assertNotIn('consumer_tree', value)
            self.assertEqual(value['clock_provenance'], 'explicit_operator_time')

    def test_dirty_untracked_native_order_and_replay_after_caller_deleted(self):
        ci = self.repository / '.github/workflows/ci.yml'; ci.write_text('name: dirty\r\njobs: {}\r\n')
        (ci.parent / 'untracked.yaml').write_text('# devsecops-governance-framework\n')
        expected, _ = original_files(FIXTURES, self.base / 'oracle-dirty', self.repository, 'synthetic/local', AT)
        identifier, value = self.create(); self.assert_outputs(identifier, expected)
        shutil.rmtree(self.repository)
        self.assertEqual(self.context.inspect(identifier), value); self.assert_outputs(identifier, expected)
        code, out = self.command('inspect-observation', '--id', identifier)
        self.assertEqual(code, 0); result = json.loads(out)
        self.assertTrue(result['retained_observation_and_complete_outputs_reverified'])
        self.assertFalse(result['live_directory_rechecked'])

    def test_integration_needs_no_repository_id_onboarding_requires_one(self):
        code, output = self.observe('integration')
        self.assertEqual(code, 0); identifier = json.loads(output)['assessment_id']
        value = self.context.inspect(identifier); self.assertIsNone(value['declared_repository_id'])
        self.assertEqual(set(value['files']), {app.INTEGRATION})
        with self.assertRaisesRegex(ValueError, 'repository_id_required'): self.observe('onboarding')
        for value in ('', 'bad\nidentity', 'x' * 513):
            with self.assertRaisesRegex(ValueError, 'invalid_source_repository_id'): self.create(repository_id=value)

    def test_original_stdout_full_bytes_and_explicit_finding_exits(self):
        expected, _ = original_files(FIXTURES, self.base / 'oracle-stdout', self.repository, 'synthetic/local', AT)
        for kind, name, options in [('integration', app.INTEGRATION, []),
                ('onboarding', app.ONBOARDING + '.json', ['--repository-id', 'synthetic/local'])]:
            code, out = self.observe(kind, '--format', 'legacy', *options)
            self.assertEqual(code, 0); self.assertEqual(out.encode(), expected[name])
        shutil.rmtree(self.repository); self.repository.mkdir()
        code, out = self.observe('integration'); self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)['original_finding_exit'], 1)
        code, out = self.observe('integration', '--format', 'legacy', '--fail-on-findings')
        self.assertEqual(code, 1); self.assertEqual(json.loads(out)['status'], 'fail')
        code, out = self.observe('onboarding', '--format', 'legacy', '--repository-id', 'synthetic/local', '--fail-on-findings')
        self.assertEqual(code, 1); self.assertEqual(json.loads(out)['status'], 'not_ready')

    def test_original_output_options_whole_bytes_and_write_messages(self):
        expected, _ = original_files(FIXTURES, self.base / 'oracle-export', self.repository, 'synthetic/local', AT)
        first = self.base / 'integration.json'
        code, out = self.observe('integration', '--format', 'legacy', '--output-file', str(first))
        self.assertEqual(code, 0); self.assertEqual(out, f'Wrote {first}\n'); self.assertEqual(first.read_bytes(), expected[app.INTEGRATION])
        second = self.base / 'nested/onboarding.json'; md = self.base / 'other/onboarding.md'
        code, out = self.observe('onboarding', '--repository-id', 'synthetic/local', '--format', 'legacy',
                                 '--output-json', str(second), '--output-md', str(md))
        self.assertEqual(out, f'Wrote {second}\nWrote {md}\n'); self.assertEqual(code, 0)
        self.assertEqual(second.read_bytes(), expected[app.ONBOARDING + '.json'])
        self.assertEqual(md.read_bytes(), expected[app.ONBOARDING + '.md'])
        code, out = self.observe('onboarding', '--repository-id', 'synthetic/local', '--format', 'legacy', '--output-md', str(md))
        self.assertEqual(out, expected[app.ONBOARDING + '.json'].decode() + f'Wrote {md}\n')

    def test_runtime_clock_is_labelled_and_explicit_offset_retains_original_utc_wire(self):
        class Clock(datetime):
            @classmethod
            def now(cls, tz=None): return datetime(2026, 11, 15, 12, 0, 0, tzinfo=timezone.utc)
        with patch.object(app, 'datetime', Clock): identifier, value = self.create(at=None)
        self.assertEqual(value['clock_provenance'], 'runtime_clock'); self.assertEqual(value['assessed_at'], AT)
        offset = '2026-11-15T14:00:00.123456+02:00'
        expected, _ = original_files(FIXTURES, self.base / 'oracle-clock', self.repository, 'synthetic/local', offset)
        identifier, value = self.create(at=offset); self.assert_outputs(identifier, expected)
        self.assertEqual(value['assessed_at'], offset)

    def test_input_output_record_members_and_private_permissions_tampering_rejected(self):
        identifier, value = self.create(); inp = self.context.inputs / value['input_id']; out = self.context.artifacts / identifier
        for target in [inp / 'extra', inp / 'blobs/extra', out / 'extra']:
            target.write_bytes(b'SYNTHETIC_PRIVATE'); target.chmod(0o600)
            with self.assertRaisesRegex(ValueError, 'members_changed'): self.context.inspect(identifier)
            target.unlink()
        blob = next((inp / 'blobs').iterdir()); original = blob.read_bytes(); blob.write_bytes(original + b'changed')
        with self.assertRaisesRegex(ValueError, 'local_source_text_changed'): self.context.inspect(identifier)
        blob.write_bytes(original); blob.chmod(0o644)
        with self.assertRaisesRegex(ValueError, 'private_local_source_file_required'): self.context.inspect(identifier)
        blob.chmod(0o600)
        output = next(out.iterdir()); original = output.read_bytes(); output.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'local_source_output_changed'): self.context.inspect(identifier)
        output.write_bytes(original); output.unlink(); output.symlink_to(blob)
        with self.assertRaisesRegex(ValueError, 'private_local_source_file_required'): self.context.inspect(identifier)

    def test_relabelled_origin_profile_kind_and_foreign_node_are_rejected(self):
        identifier, value = self.create()
        for key, changed in [('source_origin', 'git'), ('working_tree_used', False), ('content_commit_verified', True),
                ('source_inspection_profile', {'kind': 'legacy-ci-source-signatures-v1', 'profile': 'legacy-ci-signatures-v1', 'source_signature_only': True}),
                ('node_id', 'foreign-node'), ('runtime_source_digest', '0' * 64), ('declared_repository_id', None)]:
            bad = deepcopy(value); bad[key] = changed; other = canonical_digest(bad)
            atomic_json(self.context.assessments / (other + '.json'), bad)
            with self.subTest(key=key), self.assertRaises(ValueError): self.context.inspect(other)
        bad = deepcopy(value); bad['inspection_kind'] = 'integration'; other = canonical_digest(bad)
        atomic_json(self.context.assessments / (other + '.json'), bad)
        with self.assertRaisesRegex(ValueError, 'input_profile_or_kind_changed'): self.context.inspect(other)

    def test_input_order_changes_are_detected_and_not_reobserved_on_replay(self):
        identifier, value = self.create(); facts = self.context.inputs / value['input_id'] / 'facts.json'
        original = facts.read_bytes(); observation = json.loads(original); observation['nodes'].reverse(); atomic_json(facts, observation)
        with self.assertRaisesRegex(ValueError, 'local_source_input_changed'): self.context.inspect(identifier)
        facts.write_bytes(original); facts.chmod(0o600)
        with patch.object(app, 'capture_local_source', side_effect=AssertionError('no live replay reads')):
            self.assertEqual(self.context.inspect(identifier), value)

    def test_space_budget_and_changed_source_rejected_before_admission(self):
        with patch.object(app, 'reserve', side_effect=ValueError('synthetic_reserve')), \
                patch.object(app, 'capture_local_source', side_effect=AssertionError('must reserve first')):
            with self.assertRaisesRegex(ValueError, 'synthetic_reserve'): self.create()
        capture = app.capture_local_source; calls = []
        def change(*args):
            if calls: (self.repository / '.github/workflows/new.yml').write_text('new observation')
            calls.append(1); return capture(*args)
        with patch.object(app, 'capture_local_source', side_effect=change):
            with self.assertRaisesRegex(ValueError, 'local_source_changed_before_commit'): self.create()
        self.assertEqual(list(self.context.inputs.iterdir()), []); self.assertEqual(list(self.context.assessments.iterdir()), [])
        with patch.object(app, 'LOCAL_SOURCE_MAX_FACTS', 1):
            with self.assertRaisesRegex(ValueError, 'local_source_facts_budget'): self.create()

    def test_profiles_options_state_overlap_and_unsafe_exports_rejected(self):
        for profile in ({'profile': 'legacy-ci-signatures-v1'}, {**PROFILE, 'working_tree_used': False}):
            with self.assertRaises(ValueError): self.create(profile=profile)
        for args in [('--format', 'legacy'), ('--output-file', str(self.base / 'bad'))]:
            with self.assertRaises(ValueError): self.observe('all', *args)
        with self.assertRaises(ValueError): self.observe('integration', '--format', 'legacy', '--output-json', 'bad')
        child = self.repository / 'node'; child.mkdir(mode=0o700)
        with self.assertRaisesRegex(ValueError, 'state_must_be_outside_target'):
            route.run(['observe', '--kind', 'integration', '--repo', str(self.repository), '--profile', PROFILE['profile']], child, self.settings)
        self.assertFalse((child / 'state').exists())
        link = self.base / 'link'; outside = self.base / 'outside'; outside.write_bytes(b'SYNTHETIC_PRIVATE'); link.symlink_to(outside)
        for destination in (link, self.node / 'config.json', ROOT / 'README.md'):
            with self.assertRaisesRegex(ValueError, 'unsafe_local_source_export'):
                app.export_file(destination, b'changed', instance_root=self.node, parents=False)
        self.assertEqual(outside.read_bytes(), b'SYNTHETIC_PRIVATE')


if __name__ == '__main__': unittest.main()
