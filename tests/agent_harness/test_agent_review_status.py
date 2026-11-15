from copy import deepcopy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml
from scripts import report_agent_review_status as cli
from scripts.lib.agent_review import digest
from scripts.lib.agent_review_status import expected_reviews, inspect_pr, parse_receipt, receipt_block, render_status
from tests.agent_harness import test_agent_receipts as fixtures


class AgentReviewStatusTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.AgentReceiptTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.receipt = self.fixture.receipt()
        self.event = {'pull_request': {'base': {'sha': self.fixture.base},
            'head': {'sha': self.receipt['head_commit']}, 'body': receipt_block(self.receipt)}}

    def inspect(self, body=None):
        event = deepcopy(self.event)
        if body is not None:
            event['pull_request']['body'] = body
        return inspect_pr(self.root, event)

    def test_complete_metadata_is_consistent_but_not_approval(self):
        report = self.inspect()
        self.assertEqual(report['status'], 'declared_complete')
        self.assertEqual(report['enforcement'], 'report_only')
        self.assertFalse(report['independent_human_approval'])
        self.assertNotIn('PRIVATE_', render_status(report))

    def test_missing_incomplete_stale_and_duplicate_blocks_remain_distinct(self):
        self.assertEqual(self.inspect('No receipt')['status'], 'missing')
        pending = deepcopy(self.fixture.results)
        pending['reviews'][0]['status'] = 'skipped'
        incomplete = self.fixture.receipt(pending)
        self.assertEqual(self.inspect(receipt_block(incomplete))['status'], 'incomplete')
        stale = deepcopy(self.receipt)
        stale['head_commit'] = '0' * 40
        stale['receipt_digest'] = digest({k:v for k,v in stale.items() if k != 'receipt_digest'})
        self.assertEqual(self.inspect(receipt_block(stale))['status'], 'stale')
        block = receipt_block(self.receipt)
        self.assertEqual(self.inspect(block + block)['status'], 'invalid')

    def test_schema_errors_never_echo_private_fields_or_model_instructions(self):
        body = receipt_block(self.receipt).replace('"schema_version": "1.0.0"', '"schema_version": "PRIVATE_SECRET", "private_note": "<script>run me</script>"')
        report = self.inspect(body)
        self.assertEqual(report['status'], 'invalid')
        self.assertNotIn('PRIVATE_SECRET', json.dumps(report))
        self.assertNotIn('<script>', render_status(report))
        with self.assertRaises(ValueError):
            parse_receipt('x' * 1048577)

    def test_pr_code_is_never_imported_and_head_contracts_are_read_as_data(self):
        malicious = self.root / 'scripts/report_agent_review_status.py'
        malicious.write_text('raise AssertionError("PR_CODE_EXECUTED")')
        self.fixture.fixture.git('add', '.')
        self.fixture.fixture.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                                 '-c', 'commit.gpgsign=false', 'commit', '-m', 'untrusted head code')
        self.event['pull_request']['head']['sha'] = self.fixture.fixture.git('rev-parse', 'HEAD').strip()
        self.assertEqual(self.inspect()['status'], 'stale')
        # The contract snapshot, not the trusted reporter's cached routing, selects roles.
        routing = self.root / '.agents/routing/governance-agent-routing.yaml'
        routing.write_text(routing.read_text().replace('always_select:\n  - repo-steward', 'always_select:\n  - repo-steward\n  - release-manager'))
        self.fixture.fixture.git('add', '.')
        self.fixture.fixture.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                                 '-c', 'commit.gpgsign=false', 'commit', '-m', 'head contract')
        head = self.fixture.fixture.git('rev-parse', 'HEAD').strip()
        self.assertIn('release-manager', expected_reviews(self.root, head, ['README.md'])['roles'])
        routing.write_text(routing.read_text().replace('agents: [evidence-and-intake, governance-analyst]', 'agents: [governance-analyst]'))
        self.fixture.fixture.git('add', '.')
        self.fixture.fixture.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                                 '-c', 'commit.gpgsign=false', 'commit', '-m', 'proposed reduced routing')
        self.event['pull_request']['head']['sha'] = self.fixture.fixture.git('rev-parse', 'HEAD').strip()
        self.assertIn('evidence-and-intake', self.inspect()['required_roles'])

    def test_symlink_contract_input_and_non_commit_refs_are_rejected(self):
        role = self.root / '.agents/roles/repo-steward.yaml'
        role.unlink()
        role.symlink_to('/etc/passwd')
        self.fixture.fixture.git('add', '.')
        self.fixture.fixture.git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid',
                                 '-c', 'commit.gpgsign=false', 'commit', '-m', 'symlink')
        head = self.fixture.fixture.git('rev-parse', 'HEAD').strip()
        with self.assertRaisesRegex(ValueError, 'regular files'):
            expected_reviews(self.root, head, ['README.md'])
        event = deepcopy(self.event)
        event['pull_request']['head']['sha'] = '--help'
        with self.assertRaisesRegex(ValueError, 'full commit'):
            inspect_pr(self.root, event)

    def test_missing_receipt_cli_still_exits_zero_and_writes_report(self):
        event = deepcopy(self.event)
        event['pull_request']['body'] = ''
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'event.json').write_text(json.dumps(event))
            with patch.object(cli, 'ROOT', self.root):
                result = cli.main(['--event-file', str(root/'event.json'), '--output-json', str(root/'out.json'), '--output-md', str(root/'out.md')])
            self.assertEqual(result, 0)
            self.assertEqual(json.loads((root/'out.json').read_text())['status'], 'missing')

    def test_summary_escapes_untrusted_markdown_and_html(self):
        report = self.inspect()
        report['diagnostics'] = ['<script>bad</script> | `x`\n# forged']
        output = render_status(report)
        self.assertNotIn('<script>', output)
        self.assertNotIn('\n# forged', output)

    def test_workflow_is_separate_read_only_report_only_and_uses_base_code(self):
        root = Path(__file__).resolve().parents[2]
        text = (root/'.github/workflows/agent-review-status.yml').read_text()
        workflow = yaml.load(text, Loader=yaml.BaseLoader)
        self.assertEqual(set(workflow['permissions'].values()), {'read'})
        job = workflow['jobs']['report-review-metadata']
        self.assertEqual(job['continue-on-error'], 'true')
        self.assertEqual(job['steps'][0]['with']['ref'], '${{ github.event.pull_request.base.sha }}')
        self.assertEqual(job['steps'][0]['with']['persist-credentials'], 'false')
        self.assertNotIn('pull_request_target', text)
        self.assertIn('Explain first installation', text)
