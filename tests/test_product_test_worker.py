"""Native parent boundaries; these small fixtures are not full-suite evidence."""
from pathlib import Path
import hashlib
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.providers import product_test_worker as worker


class OwnProductWorkerBoundary(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.environment = {'PATH': '/usr/bin:/bin', 'PYTHONDONTWRITEBYTECODE': '1'}

    def test_native_exit_and_exact_raw_streams_are_retained(self):
        command = [sys.executable, '-B', '-c', 'import sys;print("controlled parent fixture");print("declared error",file=sys.stderr);sys.exit(7)']
        result = worker.supervise(command, self.root, self.environment, self.root, timeout=10)
        self.assertEqual(result['exit_code'], 7)
        self.assertEqual(result['command'], command)
        for name, row in result['streams'].items():
            path = self.root / row['path']
            raw = path.read_bytes()
            self.assertEqual(len(raw), row['bytes'])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), row['sha256'])
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertIn(b'controlled parent fixture' if name == 'stdout' else b'declared error', raw)

    def test_parent_output_budget_cannot_be_reported_as_complete(self):
        command = [sys.executable, '-B', '-c', 'print("x"*8192)']
        with self.assertRaisesRegex(ValueError, 'stream_budget'):
            worker.supervise(command, self.root, self.environment, self.root, timeout=10, stream_limit=512)
        self.assertLessEqual((self.root / 'controller-stdout.bin').stat().st_size, 512)

    def test_partial_native_stream_writes_retain_every_byte_and_matching_hash(self):
        original = Path.open
        class PartialWriter:
            def __init__(self, stream):
                self.stream = stream
            def write(self, raw):
                return self.stream.write(raw[:max(1, len(raw)//3)])
            def close(self):
                return self.stream.close()
        def partial(path, *args, **options):
            stream = original(path, *args, **options)
            return PartialWriter(stream) if path.name.startswith('controller-') else stream
        raw = b'complete bounded native output despite short writes\n'
        command = [sys.executable, '-B', '-c', 'import sys;sys.stdout.buffer.write(' + repr(raw) + ')']
        with patch.object(Path, 'open', new=partial):
            result = worker.supervise(command, self.root, self.environment, self.root, timeout=10)
        self.assertEqual(result['exit_code'], 0)
        self.assertEqual((self.root / 'controller-stdout.bin').read_bytes(), raw)
        self.assertEqual(result['streams']['stdout']['sha256'], hashlib.sha256(raw).hexdigest())

    def test_parent_timeout_actually_reaps_its_owned_process(self):
        command = [sys.executable, '-B', '-c', 'import time;time.sleep(30)']
        processes = []
        original = worker.subprocess.Popen
        def track(*args, **kwargs):
            process = original(*args, **kwargs)
            processes.append(process)
            return process
        started = time.monotonic()
        with patch.object(worker.subprocess, 'Popen', side_effect=track):
            with self.assertRaisesRegex(TimeoutError, 'wall_budget'):
                worker.supervise(command, self.root, self.environment, self.root, timeout=.3)
        self.assertLess(time.monotonic() - started, 5)
        self.assertEqual(len(processes), 1)
        self.assertIsNotNone(processes[0].poll())

    def test_working_worker_override_cannot_select_a_package_or_start_any_program(self):
        def source(*args, **kwargs):
            return b'1'*40 + b'\n' if args[1] == 'rev-parse' else b'changed trusted worker override'
        target = self.root / 'operation'
        with patch.object(worker, 'git', side_effect=source), patch.object(worker, 'supervise') as execute:
            with self.assertRaisesRegex(ValueError, 'committed_product_test_worker_required'):
                worker.execute_own_suite(self.root / 'never-read.zip', '0'*64, target)
        execute.assert_not_called()
        self.assertFalse(target.exists())

    def test_retained_package_survives_caller_removal_with_exact_pin_and_private_mode(self):
        raw = b'controlled package capture boundary fixture'
        source, retained = self.root / 'caller.zip', self.root / 'input.zip'
        source.write_bytes(raw)
        pin = hashlib.sha256(raw).hexdigest()
        result = worker.retain_package(source, pin, retained)
        source.unlink()
        self.assertEqual(retained.read_bytes(), raw)
        self.assertEqual(result, {'path': 'input.zip', 'bytes': len(raw), 'sha256': pin})
        self.assertEqual(retained.stat().st_mode & 0o777, 0o600)

    def test_capture_rejects_checksum_mismatch_symlinks_and_reused_destination(self):
        source = self.root / 'caller.zip'; source.write_bytes(b'controlled fixture')
        pin = hashlib.sha256(source.read_bytes()).hexdigest()
        with self.assertRaisesRegex(ValueError, 'checksum_mismatch'):
            worker.retain_package(source, '0'*64, self.root / 'bad-pin.zip')
        alias = self.root / 'alias.zip'; alias.symlink_to(source)
        with self.assertRaises(OSError):
            worker.retain_package(alias, pin, self.root / 'bad-link.zip')
        retained = self.root / 'existing.zip'; retained.write_bytes(b'earlier evidence')
        with self.assertRaises(FileExistsError):
            worker.retain_package(source, pin, retained)
        self.assertEqual(retained.read_bytes(), b'earlier evidence')

    def test_capture_detects_input_mutation_during_read(self):
        raw = b'controlled capture bytes'
        source = self.root / 'caller.zip'; source.write_bytes(raw)
        original = worker.os.read
        changed = []
        def mutate(fd, size):
            value = original(fd, size)
            if value and not changed:
                source.write_bytes(b'changed input same caller path')
                changed.append(True)
            return value
        with patch.object(worker.os, 'read', side_effect=mutate):
            with self.assertRaisesRegex(ValueError, 'changed_or_checksum_mismatch'):
                worker.retain_package(source, hashlib.sha256(raw).hexdigest(), self.root / 'incomplete.zip')
