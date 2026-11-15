from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from jsonschema import ValidationError
from scripts.dispatch_governance_agents import build_dispatch
from scripts.lib.agent_review import changed_files, digest, prepare_plan, results_template
from scripts.lib.agent_receipts import (append_review_usage, build_receipt, load_review_usage,
    summarize_review_usage, validate_receipt, write_receipt)
from tests.agent_harness import test_review_execution as fixtures


class AgentReceiptTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ReviewExecutionTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.base = self.fixture.git('rev-parse', 'HEAD').strip()
        path = self.root / 'scripts/workbench/fixture.js'
        path.parent.mkdir(parents=True)
        path.write_text('review input')
        self.fixture.git('add', '.')
        self.fixture.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                         '-c', 'commit.gpgsign=false', 'commit', '-m', 'review subject')
        paths = changed_files(self.root, self.base)
        self.plan = prepare_plan(self.root, build_dispatch(paths), 'PRIVATE_GOAL', base_ref=self.base)
        self.results = self.fixture.completed(self.plan)
        for review in self.results['reviews']:
            review['executor'] = 'PRIVATE_EXECUTOR'
            review['summary'] = 'PRIVATE_SUMMARY'
            review['outputs'] = {k: 'PRIVATE_OUTPUT' for k in review['outputs']}
        for validation in self.results['validations']:
            validation['evidence'] = '/private/PRIVATE_LOG'

    def receipt(self, results=None):
        return build_receipt(self.root, self.plan, results or self.results,
                             recorded_at='2026-11-13T12:00:00Z')

    def test_receipt_is_bound_and_excludes_private_packet_text(self):
        receipt = self.receipt()
        validate_receipt(receipt)
        self.assertTrue(receipt['eligible_for_human_review'])
        self.assertFalse(receipt['independent_human_approval'])
        self.assertEqual(receipt['head_commit'], self.fixture.git('rev-parse', 'HEAD').strip())
        self.assertEqual(receipt['results_digest'], digest(self.results))
        self.assertNotIn('PRIVATE_', json.dumps(receipt))

    def test_clean_committed_full_scope_is_required(self):
        (self.root / 'untracked.txt').write_text('new input')
        with self.assertRaisesRegex(ValueError, 'clean checkout'):
            self.receipt()
        (self.root / 'untracked.txt').unlink()
        self.plan['selection_mode'] = 'explicit_paths'
        with self.assertRaisesRegex(ValueError, 'full branch'):
            self.receipt()

    def test_head_change_invalidates_export(self):
        self.fixture.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                         '-c', 'commit.gpgsign=false', 'commit', '--allow-empty', '-m', 'new head')
        with self.assertRaisesRegex(ValueError, 'stale'):
            self.receipt()

    def test_pending_selected_failed_executed_and_completed_are_distinct(self):
        pending = results_template(self.plan)
        pending['reviews'][0] = deepcopy(self.results['reviews'][0])
        pending['reviews'][0]['status'] = 'failed'
        receipt = self.receipt(pending)
        summary = summarize_review_usage([receipt])
        self.assertFalse(receipt['eligible_for_human_review'])
        self.assertEqual(sum(summary['selected_roles'].values()), len(self.plan['reviews']))
        self.assertEqual(sum(summary['declared_executed_roles'].values()), 1)
        self.assertEqual(summary['completed_roles'], {})

    def test_private_files_and_idempotent_log_retries(self):
        with tempfile.TemporaryDirectory() as directory:
            path, log = Path(directory) / 'receipt.json', Path(directory) / 'usage.jsonl'
            receipt = write_receipt(self.root, path, self.receipt())
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            later = build_receipt(self.root, self.plan, self.results, recorded_at='2026-11-13T13:00:00Z')
            self.assertEqual(write_receipt(self.root, path, later), receipt)
            self.assertTrue(append_review_usage(self.root, log, receipt))
            self.assertFalse(append_review_usage(self.root, log, later))
            self.assertEqual(len(load_review_usage(log)), 1)
            self.assertEqual(log.stat().st_mode & 0o777, 0o600)
            self.assertFalse(log.with_name(log.name + '.lock').exists())

    def test_repository_outputs_existing_other_review_and_unknown_fields_rejected(self):
        with self.assertRaisesRegex(ValueError, 'outside'):
            write_receipt(self.root, self.root / 'receipt.json', self.receipt())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'receipt.json'
            write_receipt(self.root, path, self.receipt())
            changed = deepcopy(self.results)
            changed['reviews'][0]['summary'] += ' different review'
            with self.assertRaisesRegex(ValueError, 'different review'):
                write_receipt(self.root, path, self.receipt(changed))
        receipt = self.receipt()
        receipt['private_summary'] = 'must not publish'
        with self.assertRaises(ValidationError):
            validate_receipt(receipt)

    def test_changed_digest_and_unsafe_path_are_rejected(self):
        receipt = self.receipt()
        receipt['head_commit'] = '0' * 40
        with self.assertRaisesRegex(ValueError, 'digest'):
            validate_receipt(receipt)
        receipt = self.receipt()
        receipt['changed_paths'] = ['../outside']
        receipt['receipt_digest'] = digest({k: v for k, v in receipt.items() if k != 'receipt_digest'})
        with self.assertRaisesRegex(ValueError, 'repository'):
            validate_receipt(receipt)

    def test_readiness_cannot_hide_failed_work_or_open_high_finding(self):
        results = deepcopy(self.results)
        results['reviews'][0]['findings'] = [{'severity':'high', 'path':'README.md', 'issue':'PRIVATE_FINDING', 'status':'open'}]
        receipt = self.receipt(results)
        self.assertFalse(receipt['eligible_for_human_review'])
        self.assertNotIn('PRIVATE_FINDING', json.dumps(receipt))
        receipt['eligible_for_human_review'] = True
        receipt['receipt_digest'] = digest({k:v for k,v in receipt.items() if k != 'receipt_digest'})
        with self.assertRaisesRegex(ValueError, 'contradicts'):
            validate_receipt(receipt)
