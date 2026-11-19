"""Own native-environment admission/export boundaries, not full macro evidence."""
from pathlib import Path
import hashlib
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.providers.compliance_native import NativeComplianceEnvironment as Environment
from lib.providers import compliance_native as native


class NativeComplianceBoundaries(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()

    def exported_environment(self, target):
        environment = Environment.__new__(Environment)
        environment.area = self.root / 'private-operation'; environment.area.mkdir(mode=0o700)
        environment.instance = self.root / 'protected-instance'
        environment.exports = {target, target.with_name('control-evaluation-report.json'),
                               target.with_name('control-evaluation-report.md')}
        environment.write_effects = []
        return environment

    def test_working_own_module_override_cannot_read_instance_or_admit_any_package(self):
        def source(*args):
            return b'1'*40+b'\n' if args[1] == 'rev-parse' else b'working own module override'
        with patch.object(native, 'git_read', side_effect=source), \
                patch('lib.v2_application.instance') as instance, \
                patch.object(native, 'retain_package') as capture:
            with self.assertRaisesRegex(ValueError, 'committed_complete_compliance_environment_required'):
                Environment(instance_root=self.root/'never-read', package=self.root/'never-open.zip',
                    package_pin='0'*64, workarea=self.root/'never-created', at='2026-11-15T12:00:00Z',
                    output_file=self.root/'result.json', cwd=self.root, on_event=lambda row: None)
        instance.assert_not_called(); capture.assert_not_called()
        self.assertFalse((self.root/'never-created').exists())

    def test_original_cwd_resolves_relative_paths_independently_of_worker_cwd(self):
        environment = Environment.__new__(Environment)
        environment.cwd = self.root / 'operator-directory'; environment.cwd.mkdir()
        self.assertEqual(environment.resolve(Path('inputs/release.json')),
                         environment.cwd / 'inputs/release.json')
        self.assertEqual(environment.resolve(self.root/'absolute.json'), self.root/'absolute.json')

    def test_clock_matches_original_utc_whole_seconds_and_retains_the_requested_instant(self):
        environment=Environment.__new__(Environment)
        for at in ('2026-11-15T13:00:00.987654+01:00','2026-11-15T12:00:00.999999Z',
                   '2026-11-15T12:00:00Z'):
            environment.at=at
            with self.subTest(at=at):
                self.assertEqual(environment.timestamp(),'2026-11-15T12:00:00Z')
                self.assertEqual(environment.at,at)

    def test_dotdot_export_cannot_overwrite_protected_instance(self):
        safe = self.root/'allowed'; safe.mkdir()
        protected = self.root/'protected-instance'; protected.mkdir(mode=0o700)
        file = protected/'target.json'; file.write_bytes(b'preserved private state')
        target = safe/'..'/'protected-instance'/'target.json'
        environment = self.exported_environment(target)
        with self.assertRaisesRegex(ValueError, 'explicit_export_scope_required'):
            environment.write(target, 'changed')
        self.assertEqual(file.read_bytes(), b'preserved private state')
        self.assertEqual(environment.write_effects, [])

    def test_export_hardlink_cannot_overwrite_a_protected_instance_inode(self):
        protected=self.root/'protected-instance';protected.mkdir(mode=0o700)
        original=protected/'state.json';original.write_bytes(b'protected existing state')
        target=self.root/'apparently-external-export.json';os.link(original,target)
        environment=self.exported_environment(target)
        with self.assertRaisesRegex(ValueError,'explicit_export_scope_required'):
            environment.write(target,'must not overwrite state')
        self.assertEqual(original.read_bytes(),b'protected existing state')
        self.assertEqual(environment.write_effects,[])

    def test_explicit_alias_writes_retain_all_ordered_bytes_and_final_original_effect(self):
        output = self.root/'exports'; output.mkdir()
        target = output/'control-evaluation-report.json'
        environment = self.exported_environment(target)
        markdown = target.with_suffix('.md')
        values = [(target, '{"control":"first"}\n'), (markdown, '# Controls\n'),
                  (target, '{"combined":"last"}\n')]
        for path, text in values:
            environment.write(path, text)
        self.assertEqual(target.read_text(), values[-1][1])
        self.assertEqual(markdown.read_text(), values[1][1])
        self.assertEqual(len(environment.write_effects), 3)
        for row, (path, text) in zip(environment.write_effects, values):
            retained = environment.area / row['after']['retained']
            self.assertEqual(row['path'], str(path))
            self.assertEqual(retained.read_bytes(), text.encode())
            self.assertEqual(row['after']['sha256'], hashlib.sha256(text.encode()).hexdigest())
            self.assertEqual(row['outcome'], 'returned')
            self.assertEqual(retained.stat().st_mode & 0o777, 0o600)

    def test_missing_export_parent_is_not_created_and_no_successful_effect_is_invented(self):
        target = self.root/'absent-parent'/'result.json'
        environment = self.exported_environment(target)
        with self.assertRaises(FileNotFoundError):
            environment.write(target, 'not written')
        self.assertFalse(target.parent.exists())
        self.assertEqual(environment.write_effects, [{'path': str(target), 'before': {'kind': 'missing'},
            'outcome': 'raised', 'error_type': 'FileNotFoundError', 'after': {'kind': 'missing'}}])

    def test_ordinary_directory_export_preserves_original_is_a_directory_error(self):
        target = self.root/'existing-directory'; target.mkdir()
        environment = self.exported_environment(target)
        with self.assertRaises(IsADirectoryError) as caught:
            environment.write(target, 'cannot write a directory')
        self.assertEqual(caught.exception.filename, str(target))
        self.assertEqual(environment.write_effects, [{'path': str(target), 'before': {'kind': 'directory'},
            'outcome': 'raised', 'error_type': 'IsADirectoryError', 'after': {'kind': 'directory'}}])
        self.assertTrue(target.is_dir())

    def test_failed_write_retains_original_truncation_and_partial_bytes_before_reraising(self):
        target = self.root/'result.json'; target.write_bytes(b'old full output')
        environment = self.exported_environment(target)
        error = OSError(28, 'No space left on device', str(target))
        def partial(path, text, **kwargs):
            path.write_bytes(text.encode()[:5])
            raise error
        with patch.object(Path, 'write_text', partial), self.assertRaises(OSError) as caught:
            environment.write(target, 'new incomplete output')
        self.assertIs(caught.exception, error)
        self.assertEqual(target.read_bytes(), b'new i')
        row = environment.write_effects[0]
        self.assertEqual(row['outcome'], 'raised')
        self.assertEqual((environment.area/row['before']['retained']).read_bytes(), b'old full output')
        self.assertEqual((environment.area/row['after']['retained']).read_bytes(), b'new i')

    def test_missing_input_is_observed_once_and_its_original_reader_error_is_retained(self):
        environment = Environment.__new__(Environment)
        environment.input_label = self.root/'missing-input.json'
        environment.input_snapshot = self.root/'frozen.json'
        environment.input_observed = False
        environment.input_bytes = None; environment.input_error = None
        events = []; environment.on_event = events.append
        environment.observe_input()
        error = environment.input_error
        self.assertIsInstance(error, FileNotFoundError)
        self.assertEqual(error.filename, str(environment.input_label))
        environment.input_label.write_bytes(b'new caller data after frozen missing observation')
        environment.observe_input()
        self.assertIs(environment.input_error, error)
        self.assertEqual(len(events), 1)
        self.assertFalse(environment.input_snapshot.exists())
        environment.opa = object(); environment.checkpoint = lambda: None
        with self.assertRaises(FileNotFoundError) as caught:
            environment.control_report(environment.input_label)
        self.assertIs(caught.exception, error)
