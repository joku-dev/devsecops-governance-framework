"""Atomic general intake, indexed replay equivalence, identity and capacity."""
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.portable.contracts import canonical_digest, endpoint
from lib.result_ledger import apply_replay_assessment, evidence_identity
from lib.result_snapshot_store import ResultLedger


class ResultSnapshotStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        fixture = json.loads((ROOT / 'tests/fixtures/axiom-v1-parity/general-result-cases.json').read_text())
        self.value = fixture['bundle_cases'][0]['expected_snapshot']
        self.architecture = fixture['bundle_cases'][2]['expected_snapshot']
        self.repository = {'provider': 'synthetic', 'instance': 'https://scm.example',
            'native_id': 'synthetic-1', 'path': self.value['repository_id'], 'url': 'https://scm.example/synthetic/results'}
        self.store = ResultLedger(self.base / 'store'); self.addCleanup(self.store.close)
        self.at = '2026-11-15T12:00:00Z'

    def admit(self, value=None, *, repository=None, origin='operator_bundle', assessment='1', snapshots=None):
        return self.store.admit(repository or self.repository,
            snapshots or {'devsecops': value or self.value}, origin=origin, assessment_id=assessment * 64, at=self.at)

    def records(self, origin='operator_bundle', domain='devsecops'):
        return self.store.records(origin=origin, domain=domain)

    def trusted_value(self, run='7001', digest='a' * 64):
        value = deepcopy(self.value)
        value['pipeline']['pipeline_run_id'] = run
        value['trust'] = {'model_id': 'evidence-trust-model-v1', 'effective_level': 'unverified',
            'assessment_status': 'evaluated', 'verified_at': self.at,
            'capture': {'source': {'repository_id': value['repository_id'], 'commit_id': value['repository']['commit_id'],
                'workflow_name': 'synthetic-workflow', 'run_id': run, 'run_attempt': 1, 'artifact_name': 'synthetic-artifact'},
                'subjects': [{'id': 'artifact', 'digest': digest}]},
            'checks': [{'id': name, 'result': 'pass'} for name in ('subject_identity_complete','content_digest_verified',
                'producer_run_resolved','commit_matches_run','artifact_belongs_to_run','baseline_ref_resolved',
                'freshness_evaluated','custody_recorded')]}
        return value

    def test_original_payload_and_first_receipt_are_preserved(self):
        first = self.admit(); second = self.admit(assessment='2')
        self.assertEqual(first['results']['devsecops']['status'], 'recorded')
        self.assertEqual(second['results']['devsecops']['status'], 'idempotent')
        record = self.records()['records'][0]
        self.assertEqual(record['payload'], self.value)
        self.assertEqual(record['assessment_id'], '1' * 64)
        self.assertEqual(record['effective_trust'], 'unverified')
        self.assertFalse(first['official_acceptance'])

    def test_same_target_conflict_is_quarantined_without_overwrite(self):
        self.admit(); changed = deepcopy(self.value); changed['overall_status'] = 'fail'
        result = self.admit(changed)['results']['devsecops']
        self.assertEqual(result['status'], 'conflict')
        self.assertEqual(self.records()['record_count'], 1)
        self.assertEqual(self.records()['records'][0]['payload'], self.value)
        count = self.store.db.execute('SELECT count(*) FROM conflicts').fetchone()[0]
        self.assertEqual(count, 1)
        self.admit(changed, assessment='2')
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM conflicts').fetchone()[0], 1)

    def test_native_and_operator_histories_are_separate_and_operator_claims_are_unverified(self):
        value = self.trusted_value()
        for origin in ('operator_bundle', 'native_reader'):
            self.assertEqual(self.admit(value, origin=origin)['results']['devsecops']['status'], 'recorded')
        operator = self.records()['records'][0]; native = self.records('native_reader')['records'][0]
        self.assertEqual(operator['effective_trust'], 'unverified')
        self.assertEqual(native['effective_trust'], 'provenance_verified')
        self.assertEqual(operator['payload'], native['payload'])

    def test_replay_query_matches_full_v1_history_including_incompatible_digest_reuse(self):
        first = self.trusted_value(); self.admit(first, origin='native_reader')
        first_record = self.records('native_reader')['records'][0]['payload']
        changed = self.trusted_value(run='7002')
        changed['repository']['commit_id'] = 'b' * 40
        changed['trust']['capture']['source']['commit_id'] = 'b' * 40
        expected = apply_replay_assessment(changed['trust'], [first_record])
        realm = canonical_digest({'provider': self.repository['provider'], 'instance': endpoint(self.repository['instance'])})
        selected = self.store.relevant_history(realm, 'native_reader', 'devsecops', changed['trust'])
        self.assertEqual(apply_replay_assessment(changed['trust'], selected), expected)
        result = self.admit(changed, origin='native_reader')['results']['devsecops']
        self.assertEqual(result['status'], 'recorded')
        payload = next(r['payload'] for r in self.records('native_reader')['records'] if r['payload']['pipeline']['pipeline_run_id'] == '7002')
        check = next(c for c in payload['trust']['checks'] if c['id'] == 'replay_key_unique')
        self.assertEqual(check['result'], 'fail')

    def test_changed_digest_in_same_context_is_found_by_context_index(self):
        first = self.trusted_value(); self.admit(first, origin='native_reader')
        changed = self.trusted_value(digest='b' * 64)
        realm = canonical_digest({'provider': self.repository['provider'], 'instance': endpoint(self.repository['instance'])})
        selected = self.store.relevant_history(realm, 'native_reader', 'devsecops', changed['trust'])
        expected = apply_replay_assessment(changed['trust'], [self.records('native_reader')['records'][0]['payload']])
        self.assertEqual(apply_replay_assessment(changed['trust'], selected), expected)
        self.assertEqual(self.admit(changed, origin='native_reader')['results']['devsecops']['status'], 'conflict')

    def test_equivalent_native_identity_at_later_timestamp_keeps_first(self):
        first = self.trusted_value(); self.admit(first, origin='native_reader')
        later = deepcopy(first); later['generated_at'] = '2026-11-16T12:00:00Z'; later['trust']['verified_at'] = later['generated_at']
        result = self.admit(later, origin='native_reader', assessment='2')['results']['devsecops']
        self.assertEqual(result['status'], 'idempotent')
        self.assertEqual(self.records('native_reader')['record_count'], 1)
        self.assertEqual(self.records('native_reader')['records'][0]['payload']['generated_at'], first['generated_at'])

    def test_reused_display_path_has_distinct_native_identity_and_visible_replay_failure(self):
        self.admit(self.trusted_value(), origin='native_reader')
        other = {**self.repository, 'native_id': 'synthetic-2'}
        self.admit(self.trusted_value(), repository=other, origin='native_reader')
        rows = self.records('native_reader')['records']
        self.assertEqual(len({r['repository_key'] for r in rows}), 2)
        second = next(row for row in rows if row['repository']['native_id'] == 'synthetic-2')
        replay = next(c for c in second['payload']['trust']['checks'] if c['id'] == 'replay_key_unique')
        self.assertEqual(replay['result'], 'fail')
        self.assertTrue(replay['related_native_repository_keys'])

    def test_other_instance_does_not_participate_in_replay(self):
        self.admit(self.trusted_value(), origin='native_reader')
        other = {**self.repository, 'instance': 'https://other.example'}
        self.admit(self.trusted_value(), repository=other, origin='native_reader')
        rows = self.records('native_reader')['records']
        self.assertEqual(len(rows), 2)
        for row in rows:
            check = next(c for c in row['payload']['trust']['checks'] if c['id'] == 'replay_key_unique')
            self.assertEqual(check['result'], 'pass')

    def test_repository_rename_keeps_old_descriptors_and_native_identity(self):
        self.admit()
        renamed = {**self.repository, 'path': 'synthetic/renamed', 'url': 'https://scm.example/synthetic/renamed'}
        later = deepcopy(self.value); later['repository_id'] = renamed['path']; later['pipeline']['pipeline_run_id'] = '7002'
        self.admit(later, repository=renamed)
        rows = self.records()['records']
        self.assertEqual(len({r['repository_key'] for r in rows}), 1)
        self.assertEqual({r['repository']['path'] for r in rows}, {'synthetic/results', 'synthetic/renamed'})

    def test_failed_second_insert_rolls_back_whole_batch(self):
        self.store.db.execute("""CREATE TRIGGER reject_devsecops BEFORE INSERT ON records
            WHEN NEW.domain='devsecops' BEGIN SELECT RAISE(ABORT,'synthetic rollback'); END""")
        with self.assertRaises(sqlite3.IntegrityError):
            self.admit(snapshots={'devsecops': self.value, 'architecture': self.architecture})
        self.assertEqual(self.records()['record_count'], 0)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM repositories').fetchone()[0], 0)
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM subjects').fetchone()[0], 0)

    def test_payload_or_descriptor_corruption_is_rejected(self):
        self.admit(); self.store.db.execute("UPDATE records SET payload='{}'"); self.store.db.commit()
        with self.assertRaises(ValueError): self.records()
        self.store.db.execute('UPDATE records SET payload=?', (json.dumps(self.value),)); self.store.db.commit()
        descriptor = {**self.repository, 'url': 'https://other.example/changed'}
        self.store.db.execute('UPDATE records SET descriptor=?', (json.dumps(descriptor),)); self.store.db.commit()
        with self.assertRaisesRegex(ValueError, 'result_ledger_payload_changed'): self.records()

    def test_foreign_or_malformed_database_is_rejected(self):
        for name, malformed in (('foreign', False), ('malformed', True)):
            root = self.base / name; root.mkdir(mode=0o700)
            path = root / 'results.sqlite3'
            if malformed:
                path.write_bytes(b'not a database')
            else:
                connection = sqlite3.connect(path)
                connection.execute('CREATE TABLE foreign_data (value TEXT)')
                connection.commit(); connection.close()
            with self.assertRaises(ValueError): ResultLedger(root)

    def test_2000_small_repository_results_are_scoped_and_paged_without_native_activity(self):
        for i in range(2000):
            repository = {**self.repository, 'native_id': f'synthetic-{i}', 'path': f'synthetic/repo-{i}'}
            value = deepcopy(self.value); value['repository_id'] = repository['path']
            self.admit(value, repository=repository)
        first = self.store.records(origin='operator_bundle', domain='devsecops', limit=1000)
        second = self.store.records(origin='operator_bundle', domain='devsecops', limit=1000, offset=1000)
        self.assertEqual(first['record_count'], 2000)
        self.assertEqual(len(first['records']), 1000); self.assertEqual(len(second['records']), 1000)
        self.assertFalse({r['repository_key'] for r in first['records']} & {r['repository_key'] for r in second['records']})
        self.assertEqual(self.records('native_reader')['record_count'], 0)


if __name__ == '__main__': unittest.main()
