"""Actual recorded engine runs and strict no-native/no-caller retained replay."""
import copy
from pathlib import Path
import shutil
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import test_v2_repository_capture as fixture
from lib import repository_operation as contract
from lib import repository_capture as capture
from lib.portable.runtime import approved_opa_hashes
from lib.provider_ports import configuration_source_profile
from lib.providers.repository_lifecycle_capture import LegacyRepositoryLifecycleCapture
from lib.providers.repository_runner import execute_repository_operation
from lib.providers.repository_operations import load_operation
from lib.repository_inspection import inspect_repository_operation, RepositoryTrace


@unittest.skipUnless(all(shutil.which(name) for name in ('git', 'ssh-keygen', 'opa', 'openssl')),
                     'native validation tools absent')
class RepositoryInspectionTests(unittest.TestCase):
    command = fixture.RepositoryCaptureTests.command
    commit = fixture.RepositoryCaptureTests.commit

    def setUp(self):
        fixture.RepositoryCaptureTests.setUp(self)
        self.operation = self.base / 'operation'; self.operation.mkdir(mode=0o700)
        self.options = {'capture_adapter_factory': LegacyRepositoryLifecycleCapture,
            'schema_identifier_bases': ('https://joku-dev.github.io/devsecops-governance-framework/schemas/',),
            'source_configuration_profile': configuration_source_profile('github-actions')}
        self.hashes = frozenset(approved_opa_hashes('1.18.2'))
        self.clock = lambda: '2026-11-15T12:00:00Z'

    def header(self):
        return {'schema_version': 1, 'kind': 'product-repository-validation', 'operation_id': 'a' * 64,
            'node_id': 'b' * 32, 'runtime_source_digest': 'c' * 64, 'source_revision': self.revision,
            'source_tree': self.command('rev-parse', 'HEAD^{tree}').decode().strip(),
            'source_root': str(self.source), 'profile': capture.WORKING,
            'engine_profile': 'legacy-repository-validator-v1',
            'assessed_at': '2026-11-15T12:00:00Z', **contract.AUTHORITY}

    def execute(self, header, **overrides):
        options = {'source': self.source, 'git_tool': shutil.which('git'), 'opa_tool': shutil.which('opa'),
            'approved_opa_hashes': self.hashes, 'clock': self.clock, 'engine_options': self.options,
            'assert_current': lambda: None}
        options.update(overrides)
        return execute_repository_operation(self.operation, header, **options)

    def inspect(self, value):
        return inspect_repository_operation(value, **self.options, approved_opa_hashes=self.hashes,
                                            engine_profile='legacy-repository-validator-v1')

    def real(self, negative):
        shutil.copytree(ROOT, self.source, dirs_exist_ok=True,
            ignore=shutil.ignore_patterns('.git', '__pycache__', '.venv*', '.DS_Store', '*.pyc'))
        self.commit()
        if negative:
            import yaml
            path = self.source / 'model/controls/dscb-l1.yaml'
            value = yaml.safe_load(path.read_bytes()); value['requirements'][0]['id'] = value['requirements'][1]['id']
            path.write_text(yaml.safe_dump(value, sort_keys=False))
        header = self.header()
        def clock():
            # The native capsule is already prepared. Future generators and
            # verification must use captured bytes, not reopen caller files.
            if self.source.exists():shutil.rmtree(self.source)
            return self.clock()
        result = self.execute(header, clock=clock)
        self.assertFalse(self.source.exists())
        self.assertEqual(result['outcome']['execution'], 'complete')
        self.assertEqual(result['outcome']['exit_code'], int(negative))
        if negative:
            self.assertEqual(result['outcome']['stdout'], "Validation failed:\n- Duplicate control IDs: ['DSCB-L1-REQ-002']\n- Traceability references unknown controls: ['DSCB-L1-REQ-001']\n- Coverage status references unknown controls: ['DSCB-L1-REQ-001']\n")
        else:self.assertTrue(result['outcome']['stdout'].startswith('Validation passed\n'))
        self.assertFalse(any(self.base.glob('.repository-native-*')))
        with patch('subprocess.Popen', side_effect=AssertionError('native execution during inspection')), \
             patch('pathlib.Path.resolve', side_effect=AssertionError('caller filesystem consulted')):
            observed = self.inspect(load_operation(self.operation, header))
        self.assertEqual(observed['state'], 'retained_declared_replay_consistent')
        self.assertTrue(observed['whole_event_order_and_bytes_equal'])
        self.assertEqual(observed['files_compared'], len(result['outputs']))
        self.assertFalse(observed['official_acceptance'])
        return result

    def test_full_positive_live_run_and_deleted_source_replay_preserve_every_file_and_event(self):
        result = self.real(False)
        # Each mutation preserves a structurally well-formed loaded record but
        # changes its declared ordered evidence; no independent auth is claimed.
        variants = []
        changed = copy.deepcopy(result)
        row = next(row for row in changed['journal'] if row['payload'].get('kind') == 'engine-event')
        row['payload']['event']['unexpected'] = True; variants.append(changed)
        changed = copy.deepcopy(result)
        indexes = [i for i, row in enumerate(changed['journal']) if row['payload'].get('kind') == 'clock']
        changed['journal'][indexes[0]]['payload']['value'] = '2026-11-16T12:00:00Z'; variants.append(changed)
        changed = copy.deepcopy(result)
        initial = next(i for i, row in enumerate(changed['journal']) if row['payload'].get('kind') == 'native')
        changed['journal'][initial], changed['journal'][initial + 1] = changed['journal'][initial + 1], changed['journal'][initial]
        variants.append(changed)
        changed = copy.deepcopy(result); changed['outcome']['stdout'] += 'fabricated'; variants.append(changed)
        changed = copy.deepcopy(result); changed['outputs']['generated/fabricated.txt'] = b'fake'; variants.append(changed)
        for index, changed in enumerate(variants):
            with self.subTest(index=index), self.assertRaises(ValueError), \
                 patch('subprocess.Popen', side_effect=AssertionError('no native replay')):
                self.inspect(changed)

    def test_full_negative_live_run_and_deleted_source_replay_preserve_all_three_findings(self):self.real(True)

    def test_incomplete_original_exception_remains_explicit_and_inspection_cannot_promote_it(self):
        result = self.execute(self.header())
        self.assertEqual(result['outcome']['execution'], 'incomplete')
        self.assertEqual(result['outcome']['exception_type'], 'FileNotFoundError')
        with self.assertRaisesRegex(ValueError, 'incomplete_cannot_replay'):self.inspect(result)

    def test_runtime_guard_failure_occurs_after_pending_journal_and_before_acquisition(self):
        header = self.header()
        def reject():raise ValueError('controlled changed runtime')
        with patch('subprocess.Popen', side_effect=AssertionError('no native call before runtime admission')):
            with self.assertRaisesRegex(ValueError, 'changed runtime'):self.execute(header, assert_current=reject)
        self.assertEqual(load_operation(self.operation, header)['state'], 'pending_incomplete')

    def test_engine_options_are_explicit_and_sources_cannot_hold_operation_state(self):
        header = self.header()
        with self.assertRaisesRegex(ValueError, 'composition_required'):self.execute(header, engine_options={})
        self.assertFalse((self.operation / 'events.jsonl').exists())
        nested = self.source / 'private-operation'; nested.mkdir(mode=0o700)
        with self.assertRaises(ValueError):
            execute_repository_operation(nested, header, source=self.source, git_tool=shutil.which('git'),
                opa_tool=None, approved_opa_hashes=self.hashes, clock=self.clock,
                engine_options=self.options, assert_current=lambda: None)

    def test_ordered_trace_compares_types_raw_values_and_consumes_all_records(self):
        for changed in ({'kind': 'clock', 'value': True}, {'kind': 'different', 'value': 1}):
            with self.assertRaises(ValueError):RepositoryTrace([{'kind': 'clock', 'value': 1}]).expect(changed)
        trace = RepositoryTrace([{'kind': 'clock', 'value': 'text\r\n'}])
        with self.assertRaises(ValueError):trace.finish()
        trace.expect({'kind': 'clock', 'value': 'text\r\n'}); trace.finish()
        with self.assertRaises(ValueError):trace.expect({'kind': 'clock', 'value': 'text\r\n'})


if __name__ == '__main__':unittest.main()
