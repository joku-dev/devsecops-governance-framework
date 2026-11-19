"""Exercise the fixed own-suite subprocess and source-admission boundary."""
from pathlib import Path
import hashlib
import importlib.util
import os
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'tests/integration/run_product_unit_tests.py'
spec = importlib.util.spec_from_file_location('own_product_test_controller', PATH)
controller = importlib.util.module_from_spec(spec)
spec.loader.exec_module(controller)


class ProductUnitRunner(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.source = self.root / 'source'
        self.source.mkdir()
        (self.source / 'tests').mkdir()
        self.output = self.root / 'logs'
        self.output.mkdir()
        self.environment = {'PATH': '/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE': '1'}

    def program(self, body):
        (self.source / 'tests/test_controlled.py').write_text(
            'import unittest,time\nclass Controlled(unittest.TestCase):\n'
            ' def test_case(self):\n' + ''.join('  ' + line + '\n' for line in body.splitlines()))

    def test_exact_full_discovery_command_preserves_actual_exit_and_raw_outputs(self):
        self.program('print("synthetic own-test marker")\nself.assertEqual(2+2,4)')
        result = controller.run_command('unit-tests', self.source, self.environment, self.output, timeout=10)
        self.assertEqual(result['command'], [sys.executable, '-B', '-m', 'unittest', 'discover', '-s', 'tests'])
        self.assertEqual(result['returncode'], 0)
        for value in result['outputs'].values():
            raw = (self.output / value['path']).read_bytes()
            self.assertEqual(len(raw), value['bytes'])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), value['sha256'])
        self.assertIn(b'synthetic own-test marker', (self.output / 'unit-tests-stdout.bin').read_bytes())
        self.assertIn(b'Ran 1 test', (self.output / 'unit-tests-stderr.bin').read_bytes())

    def test_output_budget_does_not_claim_an_unretained_complete_success(self):
        self.program('print("x"*8192)')
        with patch.object(controller, 'MAX_STREAM', 1024):
            with self.assertRaisesRegex(ValueError, 'output_budget'):
                controller.run_command('unit-tests', self.source, self.environment, self.output, timeout=10)
        self.assertLessEqual((self.output / 'unit-tests-stdout.bin').stat().st_size, 1024)

    def test_wall_budget_stops_the_owned_test_process(self):
        self.program('time.sleep(30)')
        started = time.monotonic()
        original = controller.subprocess.Popen
        processes = []
        def track(*args, **kwargs):
            process = original(*args, **kwargs)
            processes.append(process)
            return process
        with patch.object(controller.subprocess, 'Popen', side_effect=track):
            with self.assertRaisesRegex(TimeoutError, 'wall_budget'):
                controller.run_command('unit-tests', self.source, self.environment, self.output, timeout=.3)
        self.assertLess(time.monotonic() - started, 5)
        self.assertEqual(len(processes), 1)
        self.assertIsNotNone(processes[0].poll())

    def test_another_pinned_reference_package_never_starts_a_caller_suite(self):
        import json
        inputs = ROOT / 'tests/fixtures/product-test-reference-inputs'
        manifest = json.loads((inputs / 'manifest.json').read_bytes())
        row = manifest['snapshots'][0]
        with patch.object(controller, 'run_command') as run:
            with self.assertRaisesRegex(ValueError, 'controller_revision_mismatch'):
                controller.execute(inputs / row['path'], row['sha256'], self.root / 'candidate')
        run.assert_not_called()

    def test_closed_projection_phase_uses_the_complete_own_source_without_writing_outputs(self):
        import json
        from lib.viewer_app import project_data
        environment = {**self.environment, 'PATH': os.environ['PATH'],
            'GIT_CONFIG_GLOBAL': '/dev/null', 'GIT_CONFIG_NOSYSTEM': '1'}
        folder = ROOT / 'generated/viewer/app'
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in folder.iterdir() if p.is_file()}
        result = controller.run_command('viewer-projection', ROOT, environment, self.output, timeout=120)
        self.assertEqual(result['returncode'], 0)
        raw = (self.output / 'viewer-projection-stdout.bin').read_bytes()
        self.assertEqual(raw, (json.dumps(project_data(ROOT), ensure_ascii=False, indent=2) + '\n').encode())
        self.assertEqual(before, {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in folder.iterdir() if p.is_file()})
