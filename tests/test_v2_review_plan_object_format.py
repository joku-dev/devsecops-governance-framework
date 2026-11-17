"""Original execution plans across native Git formats and explicit base selectors."""
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
import importlib.util
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
from lib import review_git, review_planning
from lib.provider_ports import resolve_review_base, review_plan_profile
from lib.review_planning_application import ReviewPlanningContext, run, wire

spec = importlib.util.spec_from_file_location('object_format_original', ROOT / 'tests/acceptance/v1_review_planning_oracle.py')
oracle = importlib.util.module_from_spec(spec); spec.loader.exec_module(oracle)
FIXTURE = ROOT / 'tests/fixtures/v2-review-planning'
METADATA = ROOT / 'tests/fixtures/v2-review-metadata'
PROFILE = 'legacy-role-review-v1'
AT = '2026-11-17T21:00:00Z'
GOAL = 'Synthetic original Git object-format comparison'


class ReviewPlanObjectFormats(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.instance = self.base / 'node'; self.instance.mkdir(mode=0o700)
        self.settings = {'node_id': 'synthetic-object-format-node'}
        self.goal = self.base / 'goal.txt'; self.goal.write_text(GOAL)

    def repository(self, object_format):
        root = self.base / object_format; root.mkdir()
        for name, row in oracle.target_files(FIXTURE).items():
            path = root / name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(row['bytes']); path.chmod(row['mode'])
        path = root / 'docs/review-example.md'; path.parent.mkdir(exist_ok=True); path.write_text('original\n'); path.chmod(0o644)
        oracle.git(root, 'init', '-q', '-b', 'main', '--object-format=' + object_format)
        oracle.git(root, 'add', '--all'); oracle.git(root, 'commit', '-qm', 'synthetic target')
        target = oracle.git(root, 'rev-parse', 'HEAD'); oracle.git(root, 'branch', 'review-base', target)
        path.write_text('committed change\n'); oracle.git(root, 'add', '--all'); oracle.git(root, 'commit', '-qm', 'synthetic proposal')
        return root, target

    def cli(self, *arguments):
        output = io.StringIO()
        with redirect_stdout(output): self.assertEqual(run(list(map(str, arguments)), self.instance, self.settings), 0)
        return json.loads(output.getvalue())

    def test_complete_original_plan_template_dispatch_and_text_for_both_formats_and_bases(self):
        for object_format in ('sha1', 'sha256'):
            root, target = self.repository(object_format)
            original = oracle.OriginalReview(FIXTURE, METADATA, root)
            try:
                for option, base in [('--base-ref', 'review-base'), ('--base-commit', target)]:
                    value = self.cli('prepare', '--repo', root, option, base, '--profile', PROFILE,
                                     '--goal-file', self.goal, '--at', AT)
                    plan, dispatch, template, text = original.prepare(base, GOAL)
                    expected = {'review-plan.json': wire(plan), 'review-dispatch.json': wire(dispatch),
                                'review-results-template.json': wire(template), 'review-dispatch.md': text.encode()}
                    self.assertEqual({name: (Path(value['data_directory']) / name).read_bytes() for name in expected}, expected)
                    self.assertTrue(value['target_current_state_rechecked'])
            finally: original.close()

    def test_sha256_retained_replay_and_original_check_after_named_branch_moves(self):
        root, target = self.repository('sha256')
        prepared = self.cli('prepare', '--repo', root, '--base-ref', 'review-base', '--profile', PROFILE,
                            '--goal-file', self.goal, '--at', AT)
        plan = json.loads((Path(prepared['data_directory']) / 'review-plan.json').read_text())
        results = oracle.declared_results(plan); path = self.base / 'results.json'; path.write_bytes(wire(results))
        # V1 freezes its resolved merge-base; subsequent checks do not follow the alias.
        oracle.git(root, 'update-ref', 'refs/heads/review-base', oracle.git(root, 'rev-parse', 'HEAD'))
        checked = self.cli('check', '--repo', root, '--plan', prepared['assessment_id'], '--results', path, '--at', AT)
        self.assertTrue(checked['declared_ready'])
        original = oracle.OriginalReview(FIXTURE, METADATA, root)
        try:
            expected = original.review.check_results(root, plan, results)
            self.assertEqual((Path(checked['data_directory']) / 'review-check.json').read_bytes(), wire(expected))
        finally: original.close()
        shutil.rmtree(root); path.unlink(); self.goal.unlink()
        context = ReviewPlanningContext(self.instance, self.settings)
        for value in (prepared, checked):
            inspected = context.inspect(value['assessment_id'])
            self.assertTrue(inspected['retained_complete_outputs_reverified'])
            self.assertFalse(inspected['target_current_state_rechecked'])

    def test_mixed_commit_and_index_object_formats_rejected(self):
        root, target = self.repository('sha256'); policy = review_plan_profile(PROFILE)
        facts, raw = review_git.capture(root, target, [], policy)
        for field in ('head_commit', 'target_commit', 'merge_base_commit'):
            bad = deepcopy(facts); bad[field] = 'a' * 40
            with self.assertRaisesRegex(ValueError, 'invalid_review_git_commit'): review_git.validate(bad, raw, policy)
        bad = deepcopy(facts); path = 'docs/review-example.md'
        self.assertEqual(len(bad['index_entries'][path]), 1)
        row = bad['index_entries'][path][0]; metadata, name = row.split('\t'); mode, blob, stage = metadata.split()
        bad['index_entries'][path] = [mode + ' ' + 'a' * 40 + ' ' + stage + '\t' + name]
        with self.assertRaisesRegex(ValueError, 'invalid_review_index_entry'): review_git.validate(bad, raw, policy)
        with self.assertRaisesRegex(ValueError, 'review_exact_base_commit_required'):
            review_git.capture(root, 'a' * 40, [], policy)

    def test_named_resolution_is_bounded_finite_and_commit_only(self):
        root, target = self.repository('sha256')
        self.assertEqual(resolve_review_base(root, 'review-base', PROFILE), target)
        for value in ('', 'main\nignored', 'main\0ignored', 'x' * 4097, False):
            with self.assertRaisesRegex(ValueError, 'invalid_review_base_reference'):
                resolve_review_base(root, value, PROFILE)
        with self.assertRaises(ValueError): resolve_review_base(root, 'HEAD^{tree}', PROFILE)
        with self.assertRaises(ValueError): resolve_review_base(root, '--help', PROFILE)
        with self.assertRaisesRegex(ValueError, 'unsupported_review_plan_profile'):
            resolve_review_base(root, 'review-base', 'unknown')

    def test_conflicting_base_selectors_reject_before_private_state_creation(self):
        root, target = self.repository('sha256')
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            self.cli('prepare', '--repo', root, '--base-commit', target, '--base-ref', 'review-base',
                     '--profile', PROFILE, '--goal-file', self.goal, '--at', AT)
        self.assertEqual(error.exception.code, 2)
        self.assertFalse((self.instance / 'state').exists())

    def test_reference_retarget_during_admission_never_publishes_assessment(self):
        root, target = self.repository('sha256')
        with patch('lib.provider_ports.resolve_review_base', side_effect=[target, 'b' * 64]), \
                self.assertRaisesRegex(ValueError, 'review_base_reference_changed_during_operation'):
            self.cli('prepare', '--repo', root, '--base-ref', 'review-base', '--profile', PROFILE,
                     '--goal-file', self.goal, '--at', AT)
        context = ReviewPlanningContext(self.instance, self.settings)
        self.assertEqual(list(context.assessments.glob('*.json')), [])

    def test_sha256_keeps_execution_protocol_authority_checks(self):
        root, target = self.repository('sha256')
        path = root / '.agents/review-protocol.yaml'
        text = path.read_text(); self.assertIn('independent_human_approval: false', text)
        path.write_text(text.replace('independent_human_approval: false', 'independent_human_approval: true'))
        with self.assertRaisesRegex(ValueError, 'review_protocol_cannot_grant_authority'):
            review_git.capture(root, target, [], review_plan_profile(PROFILE))

    def test_sha256_actual_receipt_main_and_export_keep_complete_original_files(self):
        from lib.review_receipts_application import ReviewReceiptContext
        spec = importlib.util.spec_from_file_location('object_format_receipt_original', ROOT / 'tests/acceptance/v1_review_receipts_oracle.py')
        receipt_oracle = importlib.util.module_from_spec(spec); spec.loader.exec_module(receipt_oracle)
        root, target = self.repository('sha256')
        original = oracle.OriginalReview(FIXTURE, METADATA, root)
        try:
            plan, _, _, _ = original.prepare('review-base', GOAL)
            results = oracle.declared_results(plan)
            plan_file, results_file = self.base / 'plan.json', self.base / 'results.json'
            plan_file.write_bytes(wire(plan)); results_file.write_bytes(wire(results))
            old = receipt_oracle.load(original, METADATA, ROOT / 'tests/fixtures/v2-review-receipts')
            old_output, old_log = self.base / 'old/receipt.json', self.base / 'old/usage.jsonl'
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(old.main(['--plan', plan_file, '--results', results_file,
                                          '--output', old_output, '--usage-log', old_log], recorded_at=AT), 0)
            context = ReviewReceiptContext(self.instance, self.settings)
            new_output, new_log = self.base / 'new/receipt.json', self.base / 'new/usage.jsonl'
            value = context.export(root, wire(plan), wire(results), new_output, new_log, AT, PROFILE)
            self.assertEqual(new_output.read_bytes(), old_output.read_bytes())
            self.assertEqual(new_log.read_bytes(), old_log.read_bytes())
            self.assertEqual((Path(value['data_directory']) / 'review-export-result.json').read_text(), stdout.getvalue())
            self.assertEqual(len(json.loads(new_output.read_text())['head_commit']), 64)
            self.assertFalse(value['agent_execution_verified']); self.assertFalse(value['human_approval_verified'])
        finally: original.close()


if __name__ == '__main__': unittest.main()
