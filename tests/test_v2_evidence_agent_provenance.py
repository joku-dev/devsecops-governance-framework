"""Original declared-association wires and private generation/authority boundaries."""
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib import evidence_agent_provenance as core, provenance_application as app
from lib.candidate_workspace import inventory
from lib.portable.contracts import canonical_digest
from lib.consumer_intake_store import atomic_json

AT = '2026-11-15T12:00:00Z'
FIXTURE = ROOT / 'tests/fixtures/axiom-v1-parity/evidence-agent-provenance-cases.json'


class AssociationWireTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.fixture = json.loads(FIXTURE.read_text())

    def test_original_source_and_rule_fingerprints_remain_bound_to_frozen_v1(self):
        self.assertEqual(self.fixture['v1_reference'], '6b557fefe295b58272d2271326576ca3a3687197')
        for name, expected in self.fixture['source_sha256'].items():
            self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), expected)

    def test_five_original_record_index_and_conflict_stages_match_complete_wires(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            for case in self.fixture['cases']:
                record = core.build_record(case['metadata'], case['at']); self.assertEqual(record, case['incoming_record'])
                receipt = core.write_record(root, record); self.assertEqual(receipt['record_path'], case['record_path'])
                self.assertEqual((root / receipt['record_path']).read_text(), case['record_wire'])
                actual = {p.relative_to(root).as_posix(): p.read_text() for p in sorted((root / 'status/intake-conflicts/evidence-agent-provenance').rglob('*.json'))}
                self.assertEqual(actual, case['conflict_wires'])
                records = [json.loads(p.read_text()) for p in sorted((root / 'status/evidence-agent-provenance').rglob('*.json'))]
                self.assertEqual(app.wire(core.build_index(records, AT)), case['index_wire'].encode())

    def test_old_changed_clock_stdout_can_name_missing_attempt_but_new_receipt_points_to_retained_record(self):
        case = next(c for c in self.fixture['cases'] if c['id'] == 'changed-time')
        self.assertFalse(case['original_stdout_path_exists'])
        self.assertNotEqual(case['original_stdout'].strip(), case['record_path'])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            core.write_record(root, core.build_record(self.fixture['cases'][0]['metadata'], AT))
            receipt = core.write_record(root, case['incoming_record'])
            self.assertTrue((root / receipt['record_path']).is_file())
            self.assertEqual(receipt['attempted_path'] + '\n', case['original_stdout'])
            self.assertEqual(receipt['outcome'], 'conflict')

    def test_five_original_validator_stdout_stderr_and_exit_cases_match(self):
        records = json.loads(self.fixture['cases'][-1]['index_wire'])['records']
        paths = sorted({c['record_path'] for c in self.fixture['cases']})
        rows = sorted((path, next(record for record in records if record['provenance_id'][:12] in path)) for path in paths)
        schema = json.loads((ROOT / app.RULES).read_text())
        for case in self.fixture['validation_cases']:
            with self.subTest(case=case['id']):
                raw_rows = [(label, case.get('record_overrides', {}).get(label, app.wire(record).decode()).encode()) for label, record in rows]
                result = core.validation_raw_output(raw_rows, schema, lambda label: case['source_override'])
                self.assertEqual(result['stdout'], case['expected_stdout']); self.assertEqual(result['stderr'], case['expected_stderr'])
                self.assertEqual(result['original_exit'], case['expected_original_exit'])
                self.assertFalse(result['agent_execution_verified']); self.assertFalse(result['human_approval_verified'])

    def test_subject_lookup_preserves_three_legacy_capture_shapes_and_first_match(self):
        for payload in ({'subjects': [{'id': 'x', 'digest': 'first'}]},
                        {'capture': {'subjects': [{'id': 'x', 'digest': 'first'}]}},
                        {'trust': {'capture': {'subjects': [{'id': 'x', 'digest': 'first'}]}}}):
            self.assertEqual(core.load_subject_digest(payload, 'x'), 'first')
        self.assertIsNone(core.load_subject_digest({}, 'x'))
        self.assertEqual(core.load_subject_digest({'subjects': [{'id': 'x', 'digest': 'first'}, {'id': 'x', 'digest': 'second'}]}, 'x'), 'first')


class AssociationWorkspaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.shared = tempfile.TemporaryDirectory(); cls.addClassCleanup(cls.shared.cleanup)
        node = Path(cls.shared.name).resolve() / 'source-node'; node.mkdir(mode=0o700); (node / 'state').mkdir(mode=0o700)
        cls.source_data = app.ReportContext(node, {'node_id': 'shared-source-fixture'}).source_data()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve(); self.node = self.root / 'node'; self.node.mkdir(mode=0o700)
        (self.node / 'state').mkdir(mode=0o700); self.settings = {'node_id': 'association-node', 'product': 'axiom-v2'}
        self.fixture = json.loads(FIXTURE.read_text()); self.metadata = deepcopy(self.fixture['cases'][0]['metadata'])
        self.source = deepcopy(self.fixture['source']); self.app = app.ProvenanceWorkspace(self.node, self.settings, 'associations')
        source_patch = patch.object(app.ReportContext, 'source_data', return_value=self.source_data)
        source_patch.start(); self.addCleanup(source_patch.stop)
        self.app.initialize()

    def record(self, metadata=None, source=None, at=AT):
        return self.app.record(json.dumps(metadata or self.metadata).encode(), json.dumps(source or self.source).encode(), at)

    def current(self): return self.app.workspace.current()[0]

    def test_full_original_workspace_sequence_and_private_original_index_files(self):
        for case in self.fixture['cases']:
            pointer, receipt = self.record(case['metadata'], at=case['at'])
            root = self.app.workspace.generations / pointer['generation']
            self.assertEqual((root / receipt['record_path']).read_text(), case['record_wire'])
            pointer, _ = self.app.report('index', 'all', AT)
            self.assertEqual((self.app.workspace.generations / pointer['generation'] / app.INDEX_PATH).read_text(), case['index_wire'])
            self.assertEqual(self.app.inspect()['reports']['index'], 'current')

    def test_identical_retry_reuses_generation_and_keeps_exact_original_bytes(self):
        first, receipt = self.record(); second, repeated = self.record()
        self.assertEqual(first['generation'], second['generation']); self.assertEqual(repeated['write_decision'], 'idempotent')
        self.assertEqual(receipt['incoming_record'], repeated['incoming_record'])
        for key in app.FLAGS: self.assertIs(receipt[key], False)

    def test_append_retains_old_record_and_makes_previous_index_visibly_stale_but_recomputable(self):
        self.record(); indexed, _ = self.app.report('index', 'all', AT); old = self.current()
        index_bytes = (old / app.INDEX_PATH).read_bytes()
        metadata = deepcopy(self.metadata); metadata['dispatch']['id'] = 'new-dispatch'
        self.record(metadata)
        self.assertEqual((self.current() / app.INDEX_PATH).read_bytes(), index_bytes)
        self.assertEqual(self.app.inspect()['reports']['index'], 'stale')
        self.assertEqual(self.app.inspect(indexed['generation'])['reports']['index'], 'current')
        self.assertEqual(self.app.inspect()['declared_record_count'], 2)

    def test_conflicting_metadata_is_quarantined_without_changing_the_original_record_or_index(self):
        _, first = self.record(); self.app.report('index', 'all', AT)
        original = (self.current() / first['record_path']).read_bytes()
        changed = deepcopy(self.metadata); changed['notes'] = 'Another declared note'
        _, receipt = self.record(changed)
        self.assertEqual(receipt['outcome'], 'conflict'); self.assertTrue(receipt['conflict_path'])
        self.assertEqual((self.current() / first['record_path']).read_bytes(), original)
        self.assertEqual(self.app.inspect()['reports']['index'], 'current')
        self.assertEqual(self.app.inspect()['declared_record_count'], 1)

    def test_conflict_inspection_recomputes_the_complete_original_receipt(self):
        self.record(); metadata = deepcopy(self.metadata); metadata['notes'] = 'Changed note'
        _, result = self.record(metadata)
        def tamper(root):
            path = root / result['conflict_path']; value = json.loads(path.read_text())
            value['target_path'] = 'status/forged-target.json'; app.put(root, result['conflict_path'], app.wire(value))
        self.app.workspace.execute(tamper, write=True)
        with self.assertRaisesRegex(ValueError, 'provenance_conflict_changed'): self.app.inspect()

    def test_source_label_collision_rolls_back_the_entire_transaction(self):
        self.record(); before = self.app.workspace.current()[1]; generations = set(self.app.workspace.generations.iterdir())
        with self.assertRaisesRegex(ValueError, 'provenance_source_label_conflict'):
            self.record(source={'subjects': [{'id': 'report', 'digest': 'b' * 64}]})
        self.assertEqual(self.app.workspace.current()[1], before)
        self.assertEqual(set(self.app.workspace.generations.iterdir()), generations)

    def test_imported_record_checks_all_original_positive_and_negative_source_cases(self):
        records = json.loads(self.fixture['cases'][-1]['index_wire'])['records']
        paths = sorted({c['record_path'] for c in self.fixture['cases']})
        for case in self.fixture['validation_cases']:
            workspace = app.ProvenanceWorkspace(self.node, self.settings, 'check-' + case['id']); workspace.initialize()
            for path in paths:
                value = next(r for r in records if r['provenance_id'][:12] in path)
                override = case.get('record_overrides', {}).get(path)
                workspace.import_record(path.removeprefix(app.RECORD_PREFIX), override.encode() if override else app.wire(value),
                    json.dumps(case['source_override']).encode() if case['source_override'] is not None and not override else None, AT)
            pointer, result = workspace.report('check', 'all', AT); root = workspace.workspace.generations / pointer['generation']
            self.assertEqual((root / app.CHECK_STDOUT).read_bytes(), case['expected_stdout'].encode())
            self.assertEqual((root / app.CHECK_STDERR).read_bytes(), case['expected_stderr'].encode())
            self.assertEqual(result['original_exit'], case['expected_original_exit'])
            self.assertEqual(workspace.inspect()['reports']['check'], 'current')

    def test_schema_invalid_operator_record_stays_visible_and_never_claims_approval(self):
        invalid = deepcopy(self.fixture['cases'][0]['incoming_record']); invalid['agent']['id'] = 'BAD_ID'
        _, result = self.app.import_record('invalid.json', app.wire(invalid), json.dumps(self.source).encode(), AT)
        self.assertTrue(result['validation_errors']); self.assertFalse(result['human_approval_verified'])
        _, checked = self.app.report('check', 'private', AT); self.assertEqual(checked['original_exit'], 1)
        self.assertEqual(self.app.inspect()['declared_record_count'], 1)

    def test_approved_claim_is_only_a_declaration_and_no_authority_is_inherited(self):
        metadata = deepcopy(self.metadata); metadata['involvement'] = 'approved'
        _, result = self.record(metadata)
        self.assertEqual(result['incoming_record']['involvement'], 'approved')
        for key in app.FLAGS: self.assertIs(result[key], False)
        inspected = self.app.inspect(); self.assertEqual(inspected['evidence_trust'], 'unverified')
        for key in app.FLAGS: self.assertIs(inspected[key], False)

    def test_committed_private_all_scopes_and_empty_index_keep_their_distinct_meaning(self):
        self.app.report('index', 'committed', AT)
        self.assertEqual(json.loads((self.current() / app.INDEX_PATH).read_bytes())['summary']['record_count'], 0)
        self.record(); self.app.report('index', 'committed', AT)
        self.assertEqual(json.loads((self.current() / app.INDEX_PATH).read_bytes())['summary']['record_count'], 0)
        self.app.report('index', 'private', AT)
        self.assertEqual(json.loads((self.current() / app.INDEX_PATH).read_bytes())['summary']['record_count'], 1)
        with self.assertRaisesRegex(ValueError, 'unsupported_provenance_scope'): self.app.report('index', 'host-filesystem', AT)

    def test_bad_metadata_and_logical_paths_fail_without_a_new_generation(self):
        before = self.app.workspace.current()[1]
        for change in [{'official_acceptance': True}, {'involvement': 'activate-policy'}]:
            metadata = {**self.metadata, **change}
            with self.assertRaises(ValueError): self.record(metadata)
        metadata = deepcopy(self.metadata); metadata['evidence']['source_file'] = '../../outside.json'
        with self.assertRaises(ValueError): self.record(metadata)
        with self.assertRaises(ValueError): self.record(at='2026-11-15T12:00:00')
        self.assertEqual(self.app.workspace.current()[1], before)

    def test_import_path_and_overwrite_are_controlled_and_original_data_survives(self):
        raw = app.wire(self.fixture['cases'][0]['incoming_record'])
        for name in ('../outside.json', '/absolute.json', 'bad.txt'):
            with self.assertRaises(ValueError): self.app.import_record(name, raw, None, AT)
        self.app.import_record('record.json', raw, None, AT); before = self.app.workspace.current()[1]
        changed = json.loads(raw); changed['notes'] = 'Other'
        with self.assertRaisesRegex(ValueError, 'immutable_provenance_import_conflict'):
            self.app.import_record('record.json', app.wire(changed), None, AT)
        self.assertEqual(self.app.workspace.current()[1], before)
        self.assertEqual((self.current() / (app.RECORD_PREFIX + 'record.json')).read_bytes(), raw)

    def test_generation_or_source_mutation_and_foreign_node_are_rejected(self):
        self.record(); root = self.current(); name = next(iter(self.app.source_map(root).values()))['path']
        original = (root / name).read_bytes(); (root / name).write_bytes(b'{}')
        with self.assertRaises(ValueError): self.app.inspect()
        (root / name).write_bytes(original)
        foreign = app.ProvenanceWorkspace(self.node, {'node_id': 'foreign-node', 'product': 'axiom-v2'}, 'associations')
        with self.assertRaisesRegex(ValueError, 'candidate_workspace_binding_mismatch'): foreign.inspect()

    def test_source_limits_and_disk_reserve_fail_without_committing(self):
        self.record(); before = self.app.workspace.current()[1]
        with patch.object(app, 'MAX_SOURCE', 1), self.assertRaises(ValueError): self.record()
        with patch.object(app, 'reserve', side_effect=ValueError('disk_reserve')), self.assertRaisesRegex(ValueError, 'disk_reserve'):
            self.record()
        self.assertEqual(self.app.workspace.current()[1], before)

    def test_malformed_record_json_remains_inspectable_as_data_and_checks_fail_without_authority(self):
        raw = b'{invalid JSON'
        _, result = self.app.import_record('malformed.json', raw, None, AT)
        self.assertTrue(result['validation_errors']); self.assertFalse(result['agent_execution_verified'])
        _, checked = self.app.report('check', 'private', AT)
        self.assertEqual(checked['original_exit'], 1)
        self.assertIn('cannot read JSON', (self.current() / app.CHECK_STDERR).read_text())
        self.assertEqual(self.app.inspect()['reports']['check'], 'current')
        with self.assertRaises(ValueError): self.app.report('index', 'private', AT)

    def test_new_generations_keep_all_files_private(self):
        self.record(); self.app.report('index', 'all', AT); root = self.current()
        for path in [root, *root.rglob('*')]: self.assertEqual(path.stat().st_mode & 0o077, 0)
        self.assertEqual(canonical_digest(inventory(root)), self.app.inspect()['generation'])

    def test_cli_report_only_and_explicit_finding_exit_match_visible_invalid_digest(self):
        metadata = self.root / 'metadata.json'; source = self.root / 'source.json'
        metadata.write_text(json.dumps(self.metadata)); source.write_text(json.dumps({'subjects': [{'id': 'report', 'digest': 'b' * 64}]}))
        args = ['--workspace', 'associations', 'record', '--metadata', str(metadata), '--source', str(source), '--at', AT]
        with redirect_stdout(io.StringIO()) as out: self.assertEqual(app.run(args, self.node, self.settings), 0)
        receipt = json.loads(out.getvalue()); self.assertTrue(receipt['result']['validation_errors'])
        with redirect_stdout(io.StringIO()) as out: self.assertEqual(app.run([*args, '--fail-on-findings'], self.node, self.settings), 1)
        self.assertEqual(json.loads(out.getvalue())['generation'], receipt['generation'])


if __name__ == '__main__': unittest.main()
