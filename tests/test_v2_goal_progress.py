"""Goal readout must expose unfinished scope and keep test observations separate."""
from copy import deepcopy
from contextlib import redirect_stdout, redirect_stderr
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('goal_progress_generator', ROOT / 'scripts/maintenance/generate_v2_goal_progress.py')
progress = importlib.util.module_from_spec(spec)
spec.loader.exec_module(progress)


class GoalProgress(unittest.TestCase):
    def setUp(self):
        self.matrix, self.matrix_raw = progress.read_json(ROOT / progress.MATRIX)
        self.observation, self.observation_raw = progress.read_json(ROOT / progress.OBSERVATION)
        # Stable synthetic state distribution; future real progress must not require test edits.
        for name in progress.GROUPS:
            for row in self.matrix[name]:
                row['state'] = 'pending'
        for row in self.matrix['areas'][:13]:
            row['state'] = 'in_progress'
        for row in self.matrix['entrypoints'][:65]:
            row['state'] = 'in_progress'

    def project(self):
        return progress.project(self.matrix, self.observation,
                                json.dumps(self.matrix).encode(), json.dumps(self.observation).encode())

    def test_current_coverage_distinguishes_started_from_complete(self):
        report = self.project(); row = report['groups']['entrypoints']
        self.assertEqual((row['verified'], row['in_progress'], row['pending'], row['remaining']), (0, 65, 70, 135))
        self.assertEqual(report['groups']['ci_workflows']['remaining'], 37)
        self.assertEqual(report['groups']['operating_workflows']['remaining'], 16)
        self.assertEqual(report['goal_status'], 'open')
        self.assertIsNone(report['remaining_effort_estimate'])
        self.assertFalse(report['completion_gate_evaluated'])

    def test_new_mapping_reduces_pending_without_claiming_completion(self):
        row = next(r for r in self.matrix['entrypoints'] if r['state'] == 'pending')
        row['state'] = 'in_progress'; row['v2_implementation'] = 'scripts/lib/review_quality.py:prepare_files'
        report = self.project()['groups']['entrypoints']
        self.assertEqual((report['in_progress'], report['pending'], report['verified'], report['remaining']), (66, 69, 0, 135))

    def test_even_all_declared_verified_requires_separate_final_audit(self):
        for group in progress.GROUPS:
            for row in self.matrix[group]:
                row['state'] = 'verified'
        self.observation['next_work'] = None
        report = self.project()
        self.assertEqual(report['goal_status'], 'final_audit_required')
        self.assertFalse(report['completion_gate_evaluated'])
        self.assertFalse(report['authority_transferred'])
        self.assertFalse(report['independent_human_approval'])
        self.assertIn('Abschlussprüfung ausstehend', progress.summary(report))

    def test_scope_omission_and_duplicate_do_not_improve_the_readout(self):
        for name in progress.GROUPS:
            with self.subTest(group=name):
                saved = deepcopy(self.matrix[name])
                self.matrix[name].pop()
                with self.assertRaisesRegex(ValueError, 'scope changed'):
                    self.project()
                self.matrix[name] = deepcopy(saved)
                self.matrix[name][-1] = deepcopy(self.matrix[name][0])
                with self.assertRaisesRegex(ValueError, 'scope changed'):
                    self.project()
                self.matrix[name] = saved

    def test_test_checkpoint_neither_finishes_matrix_nor_recognizes_all_results_as_equal(self):
        # Explicit partial-comparison fixture, independent of the current live checkpoint.
        self.observation['last_validation'].update(
            installed_groups={'mac': 21, 'linux': 21},
            equal_complete_result_groups=20, compared_result_groups=21)
        report = self.project()
        self.assertEqual(report['last_validation']['equal_complete_result_groups'], 20)
        self.assertEqual(report['last_validation']['compared_result_groups'], 21)
        self.assertFalse(report['last_validation']['full_functional_parity'])
        text = progress.document(report, self.matrix)
        self.assertIn('20 von 21', text)
        self.assertIn(report['last_validation']['source_revision'], text)
        self.assertIn('spätere Commits nicht automatisch', text)
        self.assertIn('keine Bestätigung der Parität aller 37', text)

    def test_observed_comparison_flags_are_rendered_without_inventing_success(self):
        self.observation['last_validation']['canonical_profile_complete_results_equal'] = False
        self.observation['last_validation']['full_dcr_equal'] = False
        text = progress.document(self.project(), self.matrix)
        self.assertIn('Kanonisches Profil vollständig gleich: **nein**', text)
        self.assertIn('DCR-Bericht: Gleichheit **nein**', text)

    def test_authority_and_completion_flags_cannot_be_added_to_an_observation(self):
        for field in ('independent_human_approval', 'full_functional_parity'):
            with self.subTest(field=field):
                self.observation['last_validation'][field] = True
                with self.assertRaisesRegex(ValueError, 'cannot grant approval'):
                    self.project()
                self.observation['last_validation'][field] = False

    def test_stale_next_task_and_contradictory_counts_reject(self):
        self.observation['next_work']['entrypoints'] = ['scripts/not-in-v1.py']
        with self.assertRaisesRegex(ValueError, 'unfinished matrix'):
            self.project()
        self.observation, _ = progress.read_json(ROOT / progress.OBSERVATION)
        self.observation['last_validation']['equal_complete_result_groups'] = self.observation['last_validation']['compared_result_groups'] + 1
        with self.assertRaisesRegex(ValueError, 'contradictory validation'):
            self.project()

    def test_duplicate_workflows_and_credential_urls_reject(self):
        rows = self.observation['last_validation']['ci_workflows']
        rows.append(deepcopy(rows[0]))
        with self.assertRaisesRegex(ValueError, 'duplicate workflow'):
            self.project()
        rows.pop(); rows[0]['url'] = 'https://name:secret@ci.example/jobs/42'
        with self.assertRaisesRegex(ValueError, 'public workflow URL'):
            self.project()

    def test_nonfinite_and_duplicate_json_inputs_reject(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'input.json'
            for text in ('{"count":NaN}', '{"count":1,"count":2}'):
                with self.subTest(text=text):
                    path.write_text(text)
                    with self.assertRaises(ValueError):
                        progress.read_json(path)

    def test_check_detects_stale_projection_and_show_has_no_writes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in (progress.MATRIX, progress.OBSERVATION, 'schemas/axiom-v2-functional-parity.schema.json'):
                target = root / name; target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / name).read_bytes())
            (root / 'README.md').write_text('before\n' + progress.START + '\nstale\n' + progress.END + '\nafter\n')
            with patch.object(progress, 'require_frozen_scope'), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(progress.main(['--root', str(root), '--check']), 1)
                before = (root / 'README.md').read_bytes()
                self.assertEqual(progress.main(['--root', str(root), '--show']), 0)
                self.assertEqual((root / 'README.md').read_bytes(), before)
                self.assertFalse((root / progress.REPORT).exists())
                self.assertEqual(progress.main(['--root', str(root)]), 0)
                self.assertEqual(progress.main(['--root', str(root), '--check']), 0)
                matrix = json.loads((root / progress.MATRIX).read_text())
                next(r for r in matrix['entrypoints'] if r['state'] == 'pending')['state'] = 'in_progress'
                (root / progress.MATRIX).write_text(json.dumps(matrix))
                self.assertEqual(progress.main(['--root', str(root), '--check']), 1)
                self.assertEqual(progress.main(['--root', str(root)]), 0)
                self.assertEqual(progress.main(['--root', str(root), '--check']), 0)
                self.assertTrue((root / 'README.md').read_text().startswith('before\n'))
                self.assertTrue((root / 'README.md').read_text().endswith('\nafter\n'))

    def test_current_generated_outputs_match_actual_frozen_scope_and_inputs(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(progress.main(['--check']), 0)

    def test_missing_or_duplicate_markers_prevent_readme_damage(self):
        report = self.project()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for text in ('keep me', progress.START + progress.START + progress.END, progress.END + progress.START):
                (root / 'README.md').write_text(text)
                with self.assertRaisesRegex(ValueError, 'marker pair'):
                    progress.outputs(root, report, self.matrix)
                self.assertEqual((root / 'README.md').read_text(), text)
