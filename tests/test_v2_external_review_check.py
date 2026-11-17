"""Complete unchanged original external-file checks and retained private boundaries."""
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
sys.path.insert(0, str(ROOT/'scripts'))
from lib import review_git, review_planning
from lib.portable.contracts import canonical_digest
from lib.provider_ports import review_plan_profile
from lib.review_planning_application import ReviewPlanningContext, external_selection, run, wire, MAX_JSON, MAX_RESULTS

spec = importlib.util.spec_from_file_location('external_check_original', ROOT/'tests/acceptance/v1_review_planning_oracle.py')
oracle = importlib.util.module_from_spec(spec); spec.loader.exec_module(oracle)
FIXTURE = ROOT/'tests/fixtures/v2-review-planning'
METADATA = ROOT/'tests/fixtures/v2-review-metadata'
PROFILE = 'legacy-role-review-v1'
AT = '2026-11-17T22:20:00Z'


class ExternalReviewCheck(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.instance = self.base/'node'; self.instance.mkdir(mode=0o700)
        self.settings = {'node_id': 'external-review-check-synthetic'}
        self.planfile = self.base/'plan.json'; self.resultsfile = self.base/'results.json'

    def repository(self, object_format='sha1'):
        root = self.base/object_format; root.mkdir()
        for name, row in oracle.target_files(FIXTURE).items():
            path = root/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(row['bytes']); path.chmod(row['mode'])
        path = root/'docs/review-example.md'; path.parent.mkdir(exist_ok=True); path.write_text('original\n'); path.chmod(0o644)
        oracle.git(root, 'init', '-q', '-b', 'main', '--object-format='+object_format)
        oracle.git(root, 'add', '--all'); oracle.git(root, 'commit', '-qm', 'synthetic external-check base')
        base = oracle.git(root, 'rev-parse', 'HEAD'); oracle.git(root, 'branch', 'review-base', base)
        path.write_text('changed\n')
        return root, base

    def packet(self, root, base, paths=None):
        old = oracle.OriginalReview(FIXTURE, METADATA, root); self.addCleanup(old.close)
        plan, _, _, _ = old.prepare(base, 'Synthetic external review packet', paths)
        results = oracle.declared_results(plan); self.save(plan, results)
        return old, plan, results

    def save(self, plan, results):
        # Deliberately preserve caller formatting rather than require canonical input bytes.
        self.planfile.write_text(json.dumps(plan, indent=3)+'\n')
        self.resultsfile.write_bytes(wire(results))

    def original(self, old):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr): code = old.check_files(FIXTURE, self.planfile, self.resultsfile)
        return code, stdout.getvalue(), stderr.getvalue()

    def cli(self, root, expected=0):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = run(['check-file', '--repo', str(root), '--plan-file', str(self.planfile), '--results', str(self.resultsfile),
                        '--profile', PROFILE, '--at', AT], self.instance, self.settings)
        self.assertEqual(code, expected)
        return json.loads(stdout.getvalue())

    def test_whole_original_cli_reports_and_exit_codes_for_native_formats_and_scope_modes(self):
        for object_format in ('sha1', 'sha256'):
            root, base = self.repository(object_format)
            for selected_base, paths in [(base, None), (None, None), (base, ['docs/review-example.md'])]:
                old, plan, results = self.packet(root, selected_base, paths)
                for ready in (True, False):
                    if not ready:
                        results['reviews'][0]['status'] = 'pending'
                        results['reviews'][-1]['findings'] = [{'severity':'high', 'path':'docs/review-example.md', 'issue':'Synthetic open finding', 'status':'open'}]
                    self.save(plan, results); old_code, old_stdout, _ = self.original(old)
                    self.assertEqual(old_code, 0 if ready else 1)
                    checked = self.cli(root, old_code)
                    self.assertEqual((Path(checked['data_directory'])/'review-check.json').read_text(), old_stdout)
                    self.assertEqual(checked['schema_version'], 2); self.assertEqual(checked['plan_origin'], 'external_operator_file')
                    self.assertIsNone(checked['plan_assessment_id']); self.assertEqual(checked['declared_ready'], ready)
                    self.assertTrue(checked['target_current_state_rechecked'])
                    for name in ('agent_execution_verified','human_approval_verified','authority_transferred','official_acceptance','provider_invoked'):
                        self.assertFalse(checked[name])

    def test_original_explicit_scope_ignores_other_changes_without_export_clean_scope_rule(self):
        root, base = self.repository(); old, _, _ = self.packet(root, base, ['docs/review-example.md'])
        (root/'unrelated.txt').write_text('untracked outside explicit scope\n')
        self.assertEqual(self.original(old)[0], 0); self.cli(root)

    def test_working_scope_rejects_added_and_removed_paths_like_original(self):
        root, base = self.repository(); old, _, _ = self.packet(root, base)
        (root/'added.txt').write_text('new review scope\n')
        self.assertEqual(self.original(old)[0], 2)
        with self.assertRaisesRegex(ValueError, 'external_review_plan_stale'): self.cli(root)
        (root/'added.txt').unlink(); oracle.git(root, 'checkout', '--', 'docs/review-example.md')
        self.assertEqual(self.original(old)[0], 2)
        with self.assertRaises(ValueError): self.cli(root)
        self.assertEqual(list(ReviewPlanningContext(self.instance,self.settings).assessments.glob('*.json')), [])

    def test_index_source_mode_contract_and_head_changes_reject_like_original(self):
        root, base = self.repository(); old, _, _ = self.packet(root, base)
        path = root/'docs/review-example.md'; saved = path.read_bytes()
        mutations = [('source', lambda: path.write_text('other bytes\n'), lambda: path.write_bytes(saved)),
                     ('index', lambda: oracle.git(root,'add','docs/review-example.md'), lambda: oracle.git(root,'reset','-q','HEAD','--','docs/review-example.md')),
                     ('mode', lambda: path.chmod(0o755), lambda: path.chmod(0o644))]
        skill = root/'.agents/skills/repo-steward/SKILL.md'; raw = skill.read_bytes()
        mutations.append(('contract', lambda: skill.write_bytes(raw+b'\nchanged\n'), lambda: skill.write_bytes(raw)))
        for name, change, restore in mutations:
            with self.subTest(change=name):
                change(); self.assertEqual(self.original(old)[0], 2)
                with self.assertRaises(ValueError): self.cli(root)
                restore()
        oracle.git(root,'commit','--allow-empty','-qm','changed head')
        self.assertEqual(self.original(old)[0], 2)
        with self.assertRaises(ValueError): self.cli(root)

    def test_rehashed_external_role_authority_validation_and_extra_fields_cannot_be_admitted(self):
        root, base = self.repository(); old, plan, results = self.packet(root, base)
        for mutate in (lambda p: p['authority'].update(independent_human_approval=True),
                       lambda p: p['reviews'][0].update(access='write'),
                       lambda p: p.update(required_validations=[]),
                       lambda p: p.update(unexpected='injected')):
            bad = deepcopy(plan); mutate(bad); bad['plan_digest']=review_planning.digest({k:v for k,v in bad.items() if k!='plan_digest'})
            bad_results=deepcopy(results); bad_results['plan_digest']=bad['plan_digest']; self.save(bad,bad_results)
            self.assertEqual(self.original(old)[0], 2)
            with self.assertRaises(ValueError): self.cli(root)

    def test_replay_after_caller_and_target_deletion_retains_exact_operator_bytes(self):
        root, base = self.repository('sha256'); self.packet(root,base)
        original_bytes=self.planfile.read_bytes(); checked=self.cli(root)
        context=ReviewPlanningContext(self.instance,self.settings)
        retained=context.inputs/checked['input_id']; self.assertEqual((retained/'plan.json').read_bytes(), original_bytes)
        self.planfile.unlink(); self.resultsfile.unlink(); shutil.rmtree(root)
        inspected=context.inspect(checked['assessment_id'])
        self.assertTrue(inspected['retained_complete_outputs_reverified']); self.assertFalse(inspected['target_current_state_rechecked'])
        (retained/'plan.json').write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,'review_planning_input_changed'): context.inspect(checked['assessment_id'])

    def test_target_drift_during_admission_cannot_publish_report(self):
        root, base=self.repository(); self.packet(root,base)
        original=review_git.observe
        with patch('lib.review_git.observe', wraps=original) as observed:
            def drift(*args):
                if observed.call_count==3:(root/'docs/review-example.md').write_text('changed after capture\n')
                return original(*args)
            observed.side_effect=drift
            with self.assertRaisesRegex(ValueError,'review_target_changed_during_operation'): self.cli(root)
        self.assertEqual(list(ReviewPlanningContext(self.instance,self.settings).assessments.glob('*.json')), [])

    def test_bounded_strict_operator_json_rejects_before_assessment(self):
        root,base=self.repository(); self.packet(root,base)
        saved=self.planfile.read_bytes()
        for raw in (b'[]', b'{"selection_mode":"working_tree","selection_mode":"explicit_paths"}', b' '*(MAX_JSON+1)):
            self.planfile.write_bytes(raw)
            with self.assertRaises(ValueError): self.cli(root)
        self.planfile.write_bytes(saved); self.resultsfile.write_bytes(b' '*(MAX_RESULTS+1))
        with self.assertRaises(ValueError): self.cli(root)
        self.assertEqual(list(ReviewPlanningContext(self.instance,self.settings).assessments.glob('*.json')), [])

    def test_schema_version_and_origin_cannot_relabel_external_check_as_owned_plan(self):
        root,base=self.repository(); self.packet(root,base); checked=self.cli(root)
        context=ReviewPlanningContext(self.instance,self.settings)
        record=json.loads((context.assessments/(checked['assessment_id']+'.json')).read_text())
        for version,origin,parent in [(1,'external_operator_file',None),(2,None,None),(2,'external_operator_file','a'*64)]:
            bad=deepcopy(record); bad['schema_version']=version; bad['plan_assessment_id']=parent
            if origin is None:bad.pop('plan_origin')
            else:bad['plan_origin']=origin
            identity=canonical_digest(bad); (context.assessments/(identity+'.json')).write_bytes(wire(bad))
            with self.assertRaisesRegex(ValueError,'invalid_review_planning_assessment'): context.record(identity)


if __name__=='__main__':unittest.main()
