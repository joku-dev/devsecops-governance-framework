"""CLI routing, exact instance bindings and honest pending/incomplete states."""
import contextlib
import io
import json
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import test_v2_repository_capture as fixture
from lib import repository_application as app
from lib import validation_application
from lib.portable import runtime
from lib.providers.repository_operations import RepositoryOperation
from lib.repository_capture import COMMITTED, WORKING
from lib import repository_operation as contract

PROFILE = 'legacy-repository-validator-v1'


@unittest.skipUnless(all(shutil.which(name) for name in ('git', 'ssh-keygen')), 'native Git tools absent')
class RepositoryApplicationTests(unittest.TestCase):
    command = fixture.RepositoryCaptureTests.command
    commit = fixture.RepositoryCaptureTests.commit

    def setUp(self):
        fixture.RepositoryCaptureTests.setUp(self)
        self.instance = self.base / 'instance'; self.instance.mkdir(mode=0o700)
        (self.instance / 'state').mkdir(mode=0o700)
        self.settings = {'node_id': 'b' * 32, 'runtime_source_digest': runtime.source_digest(),
            'source_revision': self.revision, 'source_root': str(self.source), 'opa': None}
        self.context = app.RepositoryContext(self.instance, self.settings, product_root=self.source)

    def create(self):return self.context.create('2026-11-15T12:00:00Z', engine_profile=PROFILE)

    def test_committed_operation_retains_exact_inputs_and_incomplete_is_not_a_success(self):
        operation, result = self.create()
        self.assertEqual(result['binding']['profile'], COMMITTED)
        self.assertEqual(result['binding']['engine_profile'], PROFILE)
        self.assertEqual(result['state'], 'recorded_incomplete_replay_unverified')
        self.assertEqual(result['outcome']['exit_code'], 2)
        inspected = self.context.inspect(operation)
        self.assertEqual(inspected['outcome']['exception_type'], 'FileNotFoundError')
        self.assertNotIn('inputs', inspected)
        self.assertFalse(inspected['official_acceptance'])
        self.assertEqual(self.context.status()[0]['exit_code'], 2)

    def test_runtime_instance_and_source_bindings_are_required_before_state_is_used(self):
        for field, value in [('node_id', None), ('runtime_source_digest', 'a' * 64),
                             ('source_revision', 'a' * 40), ('source_root', '/different')]:
            changed = self.settings | {field: value}
            if field == 'node_id':
                # Node syntax is checked at the versioned operation boundary.
                with self.assertRaises(ValueError):
                    app.RepositoryContext(self.instance, changed, product_root=self.source).create(
                        '2026-11-15T12:00:00Z', engine_profile=PROFILE)
            else:
                with self.assertRaisesRegex(ValueError, 'current_instance_required'):
                    app.RepositoryContext(self.instance, changed, product_root=self.source)

    def test_other_node_cannot_claim_or_replay_the_existing_operation(self):
        operation, _ = self.create()
        foreign = app.RepositoryContext(self.instance, self.settings | {'node_id': 'd' * 32}, product_root=self.source)
        with self.assertRaisesRegex(ValueError, 'node_runtime_or_source_changed'):foreign.inspect(operation)
        self.assertEqual(foreign.status()[0]['state'], 'invalid_or_foreign_operation')

    def test_runtime_or_product_revision_changes_reject_old_context_reads(self):
        operation, _ = self.create()
        with patch.object(app, 'source_digest', return_value='a' * 64):
            with self.assertRaisesRegex(ValueError, 'product_changed'):self.context.inspect(operation)
        (self.source / 'README.md').write_bytes(b'new source revision'); self.commit()
        with self.assertRaisesRegex(ValueError, 'product_changed'):self.context.inspect(operation)

    def test_bounded_replay_does_not_promote_an_incomplete_operation(self):
        operation, _ = self.create()
        with patch.object(app, 'inspect_repository_worker', side_effect=AssertionError('incomplete cannot replay')):
            result = self.context.inspect(operation, bounded_worker=True)
        self.assertEqual(result['state'], 'recorded_incomplete_replay_unverified')
        self.assertEqual(result['outcome']['exit_code'], 2)
        self.assertFalse(result['official_acceptance'])

    def test_explicit_working_source_must_be_separate_and_at_the_exact_product_commit(self):
        with self.assertRaisesRegex(ValueError, 'separate_repository_worktree'):
            self.context.create('2026-11-15T12:00:00Z', engine_profile=PROFILE, source_worktree=self.source)
        other = self.base / 'other'; shutil.copytree(self.source, other)
        (other / 'model/catalog.json').write_bytes(b'working fixture change')
        operation, result = self.context.create('2026-11-15T12:00:00Z', engine_profile=PROFILE, source_worktree=other)
        self.assertEqual(result['binding']['profile'], WORKING)
        shutil.rmtree(other)
        self.assertEqual(self.context.load(operation)['inputs']['model/catalog.json'], b'working fixture change')

    def test_abandoned_journal_stays_pending_and_malformed_record_does_not_hide_other_operations(self):
        operation = 'd' * 64; target = self.context.operations / operation; target.mkdir(mode=0o700)
        header = {'schema_version': 1, 'kind': 'product-repository-validation', **self.context.binding,
            'source_root': str(self.source), 'profile': COMMITTED, 'engine_profile': PROFILE,
            'assessed_at': '2026-11-15T12:00:00Z', 'operation_id': operation, **contract.AUTHORITY}
        with RepositoryOperation(target, header):pass
        self.assertEqual(self.context.inspect(operation)['state'], 'pending_incomplete')
        invalid = self.context.operations / ('e' * 64); invalid.mkdir(mode=0o700)
        states = {row['operation_id']: row['state'] for row in self.context.status()}
        self.assertEqual(states[operation], 'pending_incomplete')
        self.assertEqual(states['e' * 64], 'invalid_or_foreign_operation')

    def test_cli_routes_to_real_context_and_reports_incomplete_without_dumping_private_payloads(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(app, 'RepositoryContext', return_value=self.context), \
             contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = validation_application.run(['repository', '--at', '2026-11-15T12:00:00Z', '--profile', PROFILE],
                self.instance, self.settings)
        self.assertEqual(result, 2); self.assertEqual(stderr.getvalue(), '')
        value = json.loads(stdout.getvalue())
        self.assertEqual(value['state'], 'recorded_incomplete_replay_unverified')
        self.assertNotIn('journal', value); self.assertNotIn('inputs', value)
        stdout = io.StringIO()
        with patch.object(app, 'RepositoryContext', return_value=self.context), contextlib.redirect_stdout(stdout):
            self.assertEqual(validation_application.run(['repository-status'], self.instance, self.settings), 0)
        self.assertEqual(json.loads(stdout.getvalue())['operations'][0]['exit_code'], 2)

    def test_cli_requires_named_profile_and_rejects_abbreviated_or_unknown_options(self):
        for arguments in (['repository', '--at', '2026-11-15T12:00:00Z'],
                          ['repository', '--at', '2026-11-15T12:00:00Z', '--profile', 'unknown'],
                          ['repository-status', '--unknown'], ['repository-inspect', '--assess', 'a' * 64]):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                app.run(arguments, self.instance, self.settings)

    def test_foreign_operation_ids_and_symlinked_working_sources_are_rejected(self):
        for value in ('../outside', '/outside', 'a', None):
            with self.assertRaises(ValueError):self.context.load(value)
        alias = self.base / 'alias'; alias.symlink_to(self.source)
        with self.assertRaisesRegex(ValueError, 'ordinary_repository_worktree'):
            self.context.create('2026-11-15T12:00:00Z', engine_profile=PROFILE, source_worktree=alias)


class RepositoryRegistrationTests(unittest.TestCase):
    def test_all_new_modules_are_distributed_and_part_of_the_neutral_core_closure(self):
        from lib.v2_boundary import validate_boundaries
        policy = json.loads((ROOT / 'config/axiom-v2-distribution.json').read_text())
        names = [*ROOT.joinpath('scripts/lib').glob('repository_*.py'),
                 *ROOT.joinpath('scripts/lib/repository_lifecycle').glob('*.py'),
                 *ROOT.joinpath('scripts/lib/providers').glob('repository_*.py')]
        self.assertTrue(names)
        self.assertTrue({path.relative_to(ROOT).as_posix() for path in names} <= set(policy['python_files']))
        self.assertTrue(validate_boundaries(ROOT)['passed'])

    def test_mutation_of_every_new_core_or_provider_module_changes_the_runtime_digest(self):
        names = [*ROOT.joinpath('scripts/lib').glob('repository_*.py'),
                 *ROOT.joinpath('scripts/lib/repository_lifecycle').glob('*.py'),
                 *ROOT.joinpath('scripts/lib/providers').glob('repository_*.py')]
        baseline = runtime.source_digest()
        for path in names:
            original = path.read_bytes()
            try:
                path.write_bytes(original + b'\n# controlled runtime fingerprint mutation\n')
                with self.subTest(path=path.name):self.assertNotEqual(runtime.source_digest(), baseline)
            finally:path.write_bytes(original)
        self.assertEqual(runtime.source_digest(), baseline)


if __name__ == '__main__':unittest.main()
