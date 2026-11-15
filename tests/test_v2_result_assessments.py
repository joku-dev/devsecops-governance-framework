"""Exact-byte declared results, source/node binding and resealed-report rejection."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.ci_bundle_storage import describe
from lib.consumer_intake_store import atomic_json
from lib.portable.contracts import canonical_digest
from lib.result_assessments import ResultContext


class ResultAssessmentTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.instance = self.base / 'node'; self.instance.mkdir(mode=0o700)
        self.settings = {'node_id': 'synthetic-general-result-node'}
        self.fixture = json.loads((ROOT / 'tests/fixtures/axiom-v1-parity/general-result-cases.json').read_text())
        self.at = '2026-11-15T12:00:00Z'

    def context(self, settings=None):
        return ResultContext(self.instance, settings or self.settings)

    def metadata(self, case, kind='bundle'):
        path = self.base / 'metadata.json'
        repo = case['expected_snapshot']['repository_id']
        value = {'schema_version': 1, 'input_kind': kind, 'domain': case.get('domain', 'devsecops'),
            'repository': {'provider': 'synthetic', 'instance': 'https://scm.example', 'native_id': 'synthetic-1',
                           'path': repo, 'url': 'https://scm.example/' + repo},
            'governance_repository': case['governance_repository'], 'parameters': case['metadata']}
        path.write_text(json.dumps(value))
        return path

    def bundle(self, case, *, zipped=False):
        source = self.base / 'bundle'; source.mkdir(exist_ok=True)
        for name, value in case['files'].items(): (source / name).write_text(json.dumps(value))
        if not zipped: return source
        target = self.base / 'bundle.zip'
        with zipfile.ZipFile(target, 'w') as archive:
            for path in source.iterdir(): archive.write(path, 'nested/' + path.name)
        return target

    def create_bundle(self, case=None, *, zipped=False):
        case = case or self.fixture['bundle_cases'][0]
        source = self.bundle(case, zipped=zipped)
        return self.context().create(metadata_path=self.metadata(case), at=self.at, bundle=source,
                                     sha256=describe(source)['input_sha256'])

    def reseal(self, value):
        identity = canonical_digest(value)
        atomic_json(self.context().assessments / (identity + '.json'), value)
        return identity

    def test_all_local_bundle_outputs_equal_independent_v1_snapshots(self):
        for case in self.fixture['bundle_cases']:
            with self.subTest(case=case['id']):
                identity, value = self.create_bundle(case)
                self.assertEqual(value['snapshots'], {case['domain']: case['expected_snapshot']})
                self.assertEqual(self.context().load(identity), value)
                self.assertEqual(value['evidence_trust'], 'unverified')
                self.assertFalse(value['official_acceptance']); self.assertFalse(value['authority_transferred'])

    def test_manual_summary_is_retained_and_replayed_without_original_paths(self):
        case = self.fixture['manual_cases'][0]
        metadata = self.metadata(case, 'manual'); summary = self.base / 'summary.json'
        summary.write_text(json.dumps(case['control_summary']))
        identity, value = self.context().create(metadata_path=metadata, summary_path=summary, at=self.at)
        metadata.unlink(); summary.unlink()
        self.assertEqual(self.context().load(identity)['snapshots']['devsecops'], case['expected_snapshot'])
        self.assertIsNone(value['raw_manifest']['bundle'])

    def test_zip_replays_original_archive_after_operator_input_is_removed(self):
        identity, value = self.create_bundle(zipped=True)
        (self.base / 'bundle.zip').unlink(); shutil.rmtree(self.base / 'bundle')
        self.assertEqual(self.context().load(identity), value)

    def test_resealed_outcome_or_authority_cannot_replace_original_report(self):
        _, value = self.create_bundle()
        changed = deepcopy(value); changed['snapshots']['devsecops']['overall_status'] = 'fail'
        with self.assertRaisesRegex(ValueError, 'differs_from_exact_sources'):
            self.context().load(self.reseal(changed))
        changed = deepcopy(value); changed['official_acceptance'] = True
        with self.assertRaisesRegex(ValueError, 'invalid_result_input_contract'):
            self.context().load(self.reseal(changed))

    def test_foreign_node_runtime_or_source_is_rejected(self):
        identity, value = self.create_bundle()
        with self.assertRaisesRegex(ValueError, 'node_runtime_or_source'):
            self.context({'node_id': 'other-node'}).load(identity)
        for field in ('runtime_source_digest', 'source_revision'):
            changed = deepcopy(value); changed[field] = '0' * len(changed[field])
            with self.assertRaisesRegex(ValueError, 'node_runtime_or_source'):
                self.context().load(self.reseal(changed))

    def test_retained_metadata_and_material_tamper_are_detected(self):
        identity, value = self.create_bundle()
        raw = self.context().raw / value['input_id']
        metadata = raw / 'metadata.json'; original = metadata.read_bytes(); metadata.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'retained_metadata_changed'): self.context().load(identity)
        metadata.write_bytes(original)
        (raw / 'bundle/material/baseline-gate-result.json').write_text('{"status":"fail"}')
        with self.assertRaisesRegex(ValueError, 'retained_material_changed'): self.context().load(identity)

    def test_resealed_zip_material_still_must_match_retained_archive(self):
        _, value = self.create_bundle(zipped=True)
        context = self.context(); original = context.raw / value['input_id']; changed = deepcopy(value)
        material = original / 'bundle/material/nested/baseline-gate-result.json'
        material.write_text('{"status":"fail"}')
        from lib.ci_bundle_storage import inventory
        changed['raw_manifest']['bundle']['files'] = inventory(original / 'bundle/material')
        changed['raw_manifest']['bundle']['material_bytes'] = sum(row['bytes'] for row in changed['raw_manifest']['bundle']['files'].values())
        changed['input_id'] = canonical_digest(changed['raw_manifest'])
        clone = context.raw / changed['input_id']; shutil.copytree(original, clone)
        atomic_json(clone / 'manifest.json', changed['raw_manifest'])
        with self.assertRaisesRegex(ValueError, 'archive_material_mismatch'):
            self.context().load(self.reseal(changed))

    def test_unknown_credentials_duplicate_keys_and_nonfinite_metadata_fail_closed(self):
        case = self.fixture['manual_cases'][0]; metadata = self.metadata(case, 'manual')
        value = json.loads(metadata.read_text()); value['token'] = 'synthetic-not-a-real-secret'
        metadata.write_text(json.dumps(value))
        with self.assertRaisesRegex(ValueError, 'invalid_result_input_contract'):
            self.context().create(metadata_path=metadata, at=self.at)
        metadata.write_text('{"schema_version":1,"schema_version":1}')
        with self.assertRaisesRegex(ValueError, 'duplicate_result_input_key'):
            self.context().create(metadata_path=metadata, at=self.at)
        metadata.write_text('{"schema_version":NaN}')
        with self.assertRaisesRegex(ValueError, 'nonfinite_result_input_number'):
            self.context().create(metadata_path=metadata, at=self.at)
        self.assertFalse(list(self.context().assessments.glob('*.json')))

    def test_loaded_values_do_not_mutate_cached_or_persisted_assessments(self):
        identity, value = self.create_bundle(); context = self.context()
        loaded = context.load(identity); loaded['snapshots']['devsecops']['notes'] = 'Changed local copy'
        self.assertEqual(context.load(identity), value)


if __name__ == '__main__': unittest.main()
