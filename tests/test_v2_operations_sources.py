"""Whole original collection using held source files and retained reconstruction."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests')]
from lib.operations_collection import collect
from lib.operations_replay import ReplayCalls
from lib.operations_reporting import build_report, render_markdown
from lib.operations_sources import record_value, record_values, yaml_value
from lib.providers import operations_files as files, operations_report_profile as profile
from lib.providers.sbom_export_storage import AUTHORITY, Record, read_record
from lib.self_security import assess
from lib.v2_boundary import violations
import test_v2_operations_collection as collection_tests
from test_v2_operations_reporting import OLD


def attach(reads, sources):
    reads.registry = sources.registry
    reads.index_domains = sources.index_domains
    reads.index = sources.index
    reads.records = sources.records
    # Controlled security fixture: this tests local model acquisition, not an
    # actual native security/crypto call or whole installed CLI admission.
    reads.security = lambda repository, at: assess(sources.security_model(), reads.security_observation(repository, at))
    return reads


class HeldWholeOperationsCollectorTests(collection_tests.CompleteOperationsCollectorTests):
    def compare(self, **scenario):
        old = collection_tests.ControlledReads(self.root, **scenario)
        with patch.object(OLD, 'command_json', side_effect=old.original_command), patch.object(OLD, 'collect_live', side_effect=old.security_observation):
            expected = OLD.collect(self.config, self.root, self.now)
        with tempfile.TemporaryDirectory() as temporary:
            record = Record(Path(temporary).resolve() / 'records', {'kind': 'controlled-source-test'}, {})
            native = files.NativeSources(self.root.resolve(), record, profile.INDEXES)
            new = attach(collection_tests.ControlledReads(self.root, **scenario), native)
            actual = collect(self.config, self.now, new)
            self.assertEqual(json.dumps(actual, indent=2), json.dumps(expected, indent=2))
            self.assertEqual(new.calls, old.calls)
            record.finish('complete', {'exit_code': 0}, {})
            _, _, result, events, blob, closed = read_record(record.root)
            calls = ReplayCalls(events, blob, expected_opened={'kind': 'opened', **AUTHORITY})
            retained = attach(collection_tests.ControlledReads(self.root, **scenario), files.RetainedSources(calls, profile.INDEXES))
            with patch.object(files, 'held_root', side_effect=AssertionError('No source root in retained reconstruction')):
                replayed = collect(self.config, self.now, retained)
            calls.finish(result['result'])
            self.assertTrue(closed())
            self.assertEqual(json.dumps(replayed, indent=2), json.dumps(expected, indent=2))
            try:
                expected_report = OLD.build_report(expected, self.config, self.now, 'b' * 40)
            except (ValueError, TypeError, KeyError) as expected_error:
                with self.assertRaises(type(expected_error)) as actual_error:
                    build_report(actual, self.config, self.now, 'b' * 40, profile=profile)
                self.assertEqual(str(actual_error.exception), str(expected_error))
            else:
                report = build_report(actual, self.config, self.now, 'b' * 40, profile=profile)
                self.assertEqual(json.dumps(report, indent=2), json.dumps(expected_report, indent=2))
                self.assertEqual(render_markdown(report), OLD.render_markdown(expected_report))
        return actual


class OperationsSourceBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.source = self.base / 'source'
        self.source.mkdir()
        self.record = Record(self.base / 'records', {'kind': 'technical-source-test'}, {})
        self.reader = files.NativeSources(self.source, self.record, profile.INDEXES)

    def write(self, name, value):
        path = self.source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value if isinstance(value, bytes) else json.dumps(value).encode())
        return path

    def retained(self):
        self.record.finish('complete', {'exit_code': 0}, {})
        _, _, result, events, blob, closed = read_record(self.record.root)
        calls = ReplayCalls(events, blob, expected_opened={'kind': 'opened', **AUTHORITY})
        return files.RetainedSources(calls, profile.INDEXES), calls, result, closed

    def test_many_records_use_one_group_and_path_component_sorting(self):
        self.write('status/intake-events/a/z.json', {'n': -1})
        self.write('status/intake-events/a.json', {'n': -2})
        for n in range(140):
            self.write(f'status/intake-events/n/{n:04}.json', {'n': n})
        expected = [record_value(p.read_bytes(), str(p.relative_to(self.source)))
                    for p in sorted((self.source / 'status/intake-events').rglob('*.json'))]
        self.assertEqual(self.reader.records('intake-events'), expected)
        self.assertEqual(self.record.sequence, 3)  # opening + one intent/outcome
        replay, calls, result, closed = self.retained()
        with patch.object(files, 'held_root', side_effect=AssertionError('No native source in replay')):
            self.assertEqual(replay.records('intake-events'), expected)
        calls.finish(result['result'])
        self.assertTrue(closed())

    def test_malformed_first_record_retains_only_used_prefix_and_same_error(self):
        self.write('status/results/0.json', {'_source_file': 'must be replaced', 'n': 0})
        self.write('status/results/1.json', b'{bad json')
        self.write('status/results/2.json', b'UNREAD_LATER_FILE_SENTINEL')
        original = files.raw_file
        touched = []
        def read(root, name):
            touched.append(name)
            return original(root, name)
        with patch.object(files, 'raw_file', side_effect=read):
            with self.assertRaises(json.JSONDecodeError) as error:
                self.reader.records('results')
        self.assertEqual(touched, ['status/results/0.json', 'status/results/1.json'])
        self.assertFalse(any(b'UNREAD_LATER_FILE_SENTINEL' in p.read_bytes() for p in self.record.blobs.iterdir()))
        replay, calls, result, closed = self.retained()
        with self.assertRaises(json.JSONDecodeError) as replay_error:
            replay.records('results')
        self.assertEqual(str(replay_error.exception), str(error.exception))
        calls.finish(result['result'])
        self.assertTrue(closed())

    def test_invalid_UTF8_or_non_mapping_JSON_reconstructs_original_failure(self):
        for raw in (b'\xff', b'null', b'17', b'[1]'):
            with self.subTest(raw=raw):
                self.write('status/results/bad.json', raw)
                try:
                    record_value(raw, 'status/results/bad.json')
                except (ValueError, TypeError) as expected:
                    with self.assertRaises(type(expected)) as error:
                        self.reader.records('results')
                    self.assertEqual(str(error.exception), str(expected))

    def test_missing_directory_is_empty_and_missing_index_keeps_FileNotFoundError(self):
        self.assertEqual(self.reader.records('results'), [])
        with self.assertRaises(FileNotFoundError):
            self.reader.index('devsecops')
        replay, calls, result, closed = self.retained()
        self.assertEqual(replay.records('results'), [])
        with self.assertRaises(FileNotFoundError):
            replay.index('devsecops')
        calls.finish(result['result'])
        self.assertTrue(closed())

    def test_directory_named_JSON_is_original_IsADirectoryError_and_replays(self):
        (self.source / 'status/results/0.json/child').mkdir(parents=True)
        self.write('status/results/1.json', {})
        with self.assertRaises(IsADirectoryError):
            self.reader.records('results')
        replay, calls, result, closed = self.retained()
        with self.assertRaises(IsADirectoryError):
            replay.records('results')
        calls.finish(result['result'])
        self.assertTrue(closed())

    def test_file_race_or_membership_change_never_returns_a_clean_group(self):
        path = self.write('status/results/0.json', {})
        original = files.raw_file
        def change(root, name):
            value = original(root, name)
            path.write_bytes(b'{"changed":true}')
            return value
        with patch.object(files, 'raw_file', side_effect=change), self.assertRaisesRegex(ValueError, 'membership_or_bytes_changed'):
            self.reader.records('results')

    def test_unselected_paths_symlinks_hardlinks_special_files_and_budgets_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'not_selected'):
            self.reader.read_bytes('scripts/untrusted.py')
        with self.assertRaisesRegex(ValueError, 'not_selected'):
            self.reader.records('../other')
        path = self.write('status/results/0.json', {})
        os.link(path, path.with_name('hardlink.json'))
        with self.assertRaises(ValueError):
            self.reader.records('results')
        path.with_name('hardlink.json').unlink()
        path.unlink()
        path.symlink_to(self.base / 'outside')
        with self.assertRaisesRegex(ValueError, 'unsafe_member'):
            self.reader.records('results')
        path.unlink()
        os.mkfifo(path)
        with self.assertRaisesRegex(ValueError, 'unsafe_member'):
            self.reader.records('results')
        path.unlink()
        self.write('status/results/0.json', {})
        with patch.object(files, 'MAX_FILES', 0), self.assertRaisesRegex(ValueError, 'membership_budget'):
            self.reader.records('results')

    def test_selected_source_ancestor_cannot_be_a_symlink(self):
        alias = self.base / 'alias'
        alias.symlink_to(self.source, target_is_directory=True)
        reader = files.NativeSources(alias, self.record, profile.INDEXES)
        with self.assertRaises(OSError):
            reader.registry()

    def test_text_newlines_and_normal_YAML_semantics_match_SafeLoader(self):
        import yaml
        raw = b'integrations:\r\n - &a {repository: one}\r\n - *a\r\nanswer: first\r\nanswer: second\r\n'
        self.write(files.REGISTRY, raw)
        self.assertEqual(self.reader.registry(), yaml.safe_load(raw))
        self.assertEqual(yaml_value(raw), yaml.safe_load(raw))
        with self.assertRaisesRegex(ValueError, 'recursive_alias'):
            yaml_value(b'value: &a [*a]\n')

    def test_changed_group_order_stop_or_extra_reads_are_rejected(self):
        value = {'members': ['status/results/a.json'], 'reads': [], 'stopped': None}
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            record_values(value, lambda _: b'{}', directory='results')
        value['stopped'] = {'kind': 'read', 'name': 'status/results/other.json', 'exception': 'OSError', 'message': 'bad'}
        with self.assertRaisesRegex(ValueError, 'stop_order_changed'):
            record_values(value, lambda _: b'{}', directory='results')
        value['members'] = ['status/other/a.json']
        with self.assertRaisesRegex(ValueError, 'member_changed'):
            record_values(value, lambda _: b'{}', directory='results')

    def test_neutral_decoder_has_no_provider_environment_or_program_access(self):
        name = 'scripts/lib/operations_sources.py'
        self.assertEqual(violations(name, (ROOT / name).read_text()), [])


if __name__ == '__main__':
    unittest.main()
