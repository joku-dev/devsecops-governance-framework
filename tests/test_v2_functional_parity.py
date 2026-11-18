"""Frozen V1 inventory and fail-closed completeness claims; no native operations."""
from copy import deepcopy
from pathlib import Path
import json
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from lib.functional_parity import audit, require_frozen_scope, implementation_checked
from lib.v2_application import run
from contextlib import redirect_stdout
import io


class ParityAudit(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);(self.root/'config').mkdir();(self.root/'schemas').mkdir()
        self.matrix=json.loads((ROOT/'config/axiom-v2-functional-parity.json').read_text())
        # These tests exercise an unfinished synthetic matrix, independently of
        # future current-product subject promotions and private evidence files.
        for group in ('areas','entrypoints','ci_workflows','operating_workflows'):
            for row in self.matrix[group]:
                row['state']='pending'
                if 'evidence' in row:row['evidence']=[]
        shutil.copyfile(ROOT/'schemas/axiom-v2-functional-parity.schema.json',
                        self.root/'schemas/axiom-v2-functional-parity.schema.json')
        self.save()

    def save(self):
        (self.root/'config/axiom-v2-functional-parity.json').write_text(json.dumps(self.matrix))

    def test_pending_scope_is_never_reported_complete(self):
        report=audit(self.root)
        self.assertFalse(report['functional_parity_complete'])
        self.assertFalse(report['authority_transferred'])
        self.assertEqual(report['scope_counts']['areas'],22)
        self.assertTrue(report['remaining'])

    def test_complete_gate_returns_nonzero_while_any_function_is_pending(self):
        with patch('lib.v2_application.ROOT',self.root),redirect_stdout(io.StringIO()):
            self.assertEqual(run('parity',['--require-complete']),1)

    def test_omitting_a_v1_entrypoint_is_detected_against_original_git(self):
        changed=deepcopy(self.matrix);changed['entrypoints'].pop()
        with self.assertRaisesRegex(ValueError,'scope_changed'):require_frozen_scope(changed,ROOT)

    def test_altered_source_hash_is_not_a_new_baseline(self):
        changed=deepcopy(self.matrix);changed['entrypoints'][0]['v1_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'reference_changed'):require_frozen_scope(changed,ROOT)

    def test_missing_area_cannot_be_hidden_by_duplicating_another(self):
        self.matrix['areas'][-1]=deepcopy(self.matrix['areas'][0]);self.save()
        with self.assertRaisesRegex(ValueError,'area_scope_changed'):audit(self.root)

    def test_source_retention_is_not_an_installed_counterpart(self):
        with self.assertRaisesRegex(ValueError,'implementation_not_installed'):
            implementation_checked(ROOT,'scripts/run_consumer_lifecycle.py:main')

    def test_declaring_verified_without_implementation_fails(self):
        self.matrix['entrypoints'][0]['state']='verified';self.save()
        with self.assertRaisesRegex(ValueError,'implementation_missing'):audit(self.root)

    def test_unapproved_scope_exception_cannot_reduce_the_goal(self):
        self.matrix['scope_exceptions']=['skip lifecycle'];self.save()
        with self.assertRaisesRegex(ValueError,'invalid_functional_parity_matrix'):audit(self.root)
