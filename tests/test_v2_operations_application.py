"""Whole private CLI: original files/streams, retained live reads and partial writes."""
from contextlib import redirect_stdout, redirect_stderr
from copy import deepcopy
from datetime import datetime
import base64
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests')]
from lib.operations_application import generate, inspect, run
from lib.operations_execution import FILES
from lib.portable.runtime import source_digest
from lib.functional_parity import git_read
from lib.providers import operations_report_profile as profile, operations_http as transport
from lib.providers import operations_session as session
from lib.providers.sbom_export_storage import read_record, encode
from test_v2_operations_reporting import OLD, FIXTURES


class DeniedWorker:
    def __init__(self, owner, args, options):
        self.owner = owner
        self.args = args
        self.options = options
        self.returncode = None

    def communicate(self, input=None, timeout=None):
        value = json.loads(input)
        self.owner.worker_inputs.append(value)
        self.owner.assertNotIn('GH_TOKEN', self.options['env'])
        self.owner.assertNotIn(value['token'], ' '.join(self.args)) if value['token'] else None
        self.returncode = 0
        return json.dumps({'status': 403, 'native_code': 'http_403',
                           'body_b64': base64.b64encode(b'controlled denied read').decode()}).encode(), b''

    def poll(self):
        return self.returncode

    def kill(self):
        self.returncode = -9


class CompletePrivateOperationsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.instance = self.base / 'instance'
        self.instance.mkdir(mode=0o700)
        self.config = self.base / 'config.json'
        self.config.write_bytes((ROOT / '.github/operations-report.json').read_bytes())
        data = FIXTURES.OperationsReportTests()
        data.setUp()
        self.observation = data.observation
        self.observation['observed_at'] = '2026-09-09T12:00:00Z'
        self.observation_file = self.base / 'observation.json'
        self.observation_file.write_text(json.dumps(self.observation))
        self.output = self.base / 'exports'
        self.node = {'node_id': 'd' * 32, 'source_revision': git_read(ROOT, 'rev-parse', 'HEAD').decode().strip(),
                     'runtime_source_digest': source_digest()}
        self.options = {'profile': profile.PROFILE, 'config': str(self.config),
                        'observation': str(self.observation_file), 'output_directory': str(self.output)}
        self.worker_inputs = []

    def original(self, observation=None, as_of=None):
        path = self.base / 'original-observation.json'
        path.write_text(json.dumps(self.observation if observation is None else observation))
        output = self.base / 'original-exports'
        arguments = ['original', '--config', str(self.config), '--observation', str(path), '--output-dir', str(output)]
        if as_of:
            arguments += ['--as-of', as_of]
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(OLD, 'ROOT', ROOT), patch.object(sys, 'argv', arguments), redirect_stdout(stdout), redirect_stderr(stderr):
            code = OLD.main()
        return {'exit_code': code, 'stdout': stdout.getvalue(), 'stderr': stderr.getvalue()}, output

    def assert_files(self, expected):
        for name in FILES:
            self.assertEqual((self.output / name).read_bytes(), (expected / name).read_bytes(), name)
            self.assertEqual((self.output / name).stat().st_mode & 0o077, 0)

    def test_provided_whole_main_three_original_exports_streams_and_portable_replay(self):
        expected, output = self.original()
        with patch.object(session.Environment, 'collect', side_effect=AssertionError('No acquisition for provided object')):
            receipt, result, code = generate(self.options, self.instance, self.node)
        self.assertEqual(code, expected['exit_code'])
        self.assertEqual(result, {**expected, 'kernel_exception': None})
        self.assert_files(output)
        _, _, _, events, _, _ = read_record(receipt['record_root'])
        self.assertEqual([e['arguments']['kind'] for e in events if e.get('action') == 'operations_input'], ['config', 'schema', 'observation'])
        self.assertEqual([e['name'] for e in events if e.get('kind') == 'export-before'], list(FILES))
        for field in ('official_acceptance', 'production_approval', 'authority_transferred', 'independent_execution_authenticated', 'published'):
            self.assertIs(receipt[field], False)
        # Inspection consumes recorded sources/outputs, never their current paths.
        self.observation_file.unlink()
        (self.output / FILES[0]).write_text('modified after original observation')
        with patch('subprocess.Popen', side_effect=AssertionError('No fresh program in replay')), \
             patch.object(session, 'input_bytes', side_effect=AssertionError('No original input read')):
            replay = inspect(receipt['record_root'])
        self.assertTrue(replay['retained_declared_replay_consistent'])
        self.assertIs(replay['current_exports_rechecked'], False)

    def test_findings_and_unknown_checks_preserve_original_success_exit(self):
        self.observation['workflow_runs'] = {}
        self.observation['errors'] = [{'source': 'controlled', 'error': 'PermissionError'}]
        self.observation_file.write_text(json.dumps(self.observation))
        expected, output = self.original()
        receipt, result, code = generate(self.options, self.instance, self.node)
        self.assertEqual(code, 0)
        self.assertEqual(result, {**expected, 'kernel_exception': None})
        self.assert_files(output)
        report = json.loads((self.output / FILES[0]).read_bytes())
        self.assertGreater(report['summary']['unknown'], 0)
        self.assertEqual(receipt['state'], 'complete')

    def test_legacy_CLI_streams_and_receipt_inspect_commands(self):
        expected, output = self.original()
        arguments = ['generate', '--profile', profile.PROFILE, '--config', str(self.config),
                     '--observation', str(self.observation_file), '--output-dir', str(self.output), '--format', 'legacy']
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = run(arguments, self.instance, self.node)
        self.assertEqual((code, stdout.getvalue(), stderr.getvalue()), (0, expected['stdout'], ''))
        self.assert_files(output)
        record = next((self.instance / 'state/operations-report/records').iterdir())
        for mode in ('inspect', 'replay'):
            with redirect_stdout(io.StringIO()) as stream:
                self.assertEqual(run([mode, '--record', str(record)], self.instance, self.node), 0)
            self.assertTrue(json.loads(stream.getvalue())['retained_declared_replay_consistent'])
        with self.assertRaisesRegex(ValueError, 'explicit_instance_required'):
            run(['inspect', '--record', str(record)])
        with redirect_stdout(io.StringIO()):
            self.assertEqual(run(['replay', '--record', str(record)]), 0)

    def test_time_override_and_default_clock_are_original_and_retained(self):
        as_of = '2026-09-09T15:00:00+02:00'
        expected, output = self.original(as_of=as_of)
        _, result, _ = generate({**self.options, 'as_of': as_of}, self.instance, self.node)
        self.assertEqual(result, {**expected, 'kernel_exception': None})
        self.assert_files(output)
        self.observation.pop('observed_at')
        self.observation_file.write_text(json.dumps(self.observation))
        class Clock(datetime):
            @classmethod
            def now(cls, *args):
                return datetime.fromisoformat('2026-09-09T12:00:00.999999+00:00')
        with patch.object(session, 'datetime', Clock):
            receipt, result, code = generate(self.options, self.instance, self.node)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads((self.output / FILES[0]).read_bytes())['generated_at'], '2026-09-09T12:00:00Z')
        self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])

    def test_bad_config_precedes_observation_read_and_keeps_original_validation_exception(self):
        config = json.loads(self.config.read_bytes())
        config['review_warning_hours'] = 0
        self.config.write_text(json.dumps(config))
        self.observation_file.write_text('invalid JSON')
        receipt, result, code = generate(self.options, self.instance, self.node)
        self.assertEqual(code, 1)
        self.assertEqual(result['kernel_exception']['type'], 'ValidationError')
        self.assertFalse(self.output.exists())
        _, _, _, events, _, _ = read_record(receipt['record_root'])
        self.assertEqual([e['arguments']['kind'] for e in events if e.get('action') == 'operations_input'], ['config', 'schema'])
        self.assertEqual(inspect(receipt['record_root'])['kernel_exception'], 'ValidationError')

    def test_null_provided_requires_explicit_fallback_before_any_native_source_or_credential(self):
        self.observation_file.write_text('null')
        with patch.object(session.Environment, 'credential', side_effect=AssertionError('No selected credential read')):
            receipt, result, code = generate(self.options, self.instance, self.node)
        self.assertEqual(code, 1)
        self.assertEqual(result['kernel_exception'], {'type': 'ValueError', 'message': 'operations_null_observation_requires_explicit_live_fallback'})
        self.assertFalse(self.output.exists())
        self.assertEqual(inspect(receipt['record_root'])['original_exit_code'], 1)

    def denied_process(self, real):
        def start(args, **options):
            return DeniedWorker(self, args, options) if args[-1].endswith('operations_http_worker.py') else real(args, **options)
        return start

    def test_live_whole_private_capture_and_null_fallback_replay_with_visible_native_fact_gaps(self):
        source = self.base / 'empty-source'
        source.mkdir()
        real = subprocess.Popen
        for provided in (False, True):
            with self.subTest(provided=provided):
                self.observation_file.write_text('null')
                options = {**self.options, 'source_worktree': str(source), 'as_of': '2026-09-09T12:00:00Z'}
                if provided:
                    options['allow_live_fallback'] = True
                else:
                    options['observation'] = None
                with patch.object(transport.subprocess, 'Popen', side_effect=self.denied_process(real)):
                    receipt, result, code = generate(options, self.instance, self.node)
                self.assertEqual(code, 0)
                self.assertEqual(receipt['state'], 'complete')
                observation = json.loads((self.output / FILES[1]).read_bytes())
                self.assertIn({'source': 'pull_requests', 'error': 'CalledProcessError'}, observation['errors'])
                self.assertIn({'source': 'security', 'error': 'FileNotFoundError'}, observation['errors'])
                with patch.object(OLD, 'command_json', side_effect=subprocess.CalledProcessError(1, ['controlled-read'])):
                    expected_observation = OLD.collect(json.loads(self.config.read_bytes()), source, datetime.fromisoformat(options['as_of']))
                self.assertEqual(json.dumps(observation, indent=2), json.dumps(expected_observation, indent=2))
                expected, output = self.original(observation=expected_observation, as_of=options['as_of'])
                self.assertEqual(result, {**expected, 'kernel_exception': None})
                self.assert_files(output)
                with patch('subprocess.Popen', side_effect=AssertionError('No program during full retained live replay')):
                    self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])

    def test_unused_fallback_source_and_selected_credential_are_not_read_for_object_observation(self):
        nonexistent = self.base / 'never-read-token'
        options = {**self.options, 'allow_live_fallback': True, 'source_worktree': str(self.base / 'not-read-source'), 'token_file': str(nonexistent)}
        with patch.object(session.Environment, 'credential', side_effect=AssertionError('No credential read for object observation')):
            receipt, _, code = generate(options, self.instance, self.node)
        self.assertEqual(code, 0)
        self.assertFalse(nonexistent.exists())
        self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])

    def test_selected_token_only_reaches_worker_stdin_and_never_retained_or_inherited(self):
        token = 'EXPLICIT_PRIVATE_TEST_BEARER_NOT_REAL'
        secret = self.base / 'selected-token'
        secret.write_text(token)
        secret.chmod(0o600)
        source = self.base / 'empty-source'
        source.mkdir()
        options = {**self.options, 'observation': None, 'source_worktree': str(source),
                   'token_file': str(secret), 'as_of': '2026-09-09T12:00:00Z'}
        real = subprocess.Popen
        with patch.object(transport.subprocess, 'Popen', side_effect=self.denied_process(real)), patch.dict(os.environ, {'GH_TOKEN': 'UNSELECTED_AMBIENT_BEARER'}):
            receipt, _, code = generate(options, self.instance, self.node)
        self.assertEqual(code, 0)
        self.assertTrue(self.worker_inputs)
        self.assertTrue(all(r['token'] == token for r in self.worker_inputs))
        for path in Path(receipt['record_root']).rglob('*'):
            if path.is_file():
                self.assertNotIn(token.encode(), path.read_bytes())
                self.assertNotIn(b'UNSELECTED_AMBIENT_BEARER', path.read_bytes())

    def test_partial_native_write_keeps_actual_prefix_prior_complete_file_and_replays_without_writes(self):
        real_open, real_write = os.open, os.write
        target = self.output / FILES[1]
        failure_inode = None
        failed = False
        def opened(path, flags, *args, **kwargs):
            nonlocal failure_inode
            fd = real_open(path, flags, *args, **kwargs)
            if Path(path) == target and flags & os.O_WRONLY:
                failure_inode = os.fstat(fd).st_ino
            return fd
        def written(fd, raw):
            nonlocal failed
            if failure_inode is not None and os.fstat(fd).st_ino == failure_inode and not failed:
                failed = True
                real_write(fd, raw[:7])
                raise OSError('controlled_partial_export')
            return real_write(fd, raw)
        with patch.object(os, 'open', side_effect=opened), patch.object(os, 'write', side_effect=written):
            receipt, result, code = generate(self.options, self.instance, self.node)
        self.assertEqual(code, 1)
        self.assertEqual(result['kernel_exception'], {'type': 'OSError', 'message': 'controlled_partial_export'})
        self.assertTrue((self.output / FILES[0]).is_file())
        self.assertEqual(target.stat().st_size, 7)
        self.assertFalse((self.output / FILES[2]).exists())
        with patch.object(os, 'write', side_effect=AssertionError('No export/journal writes in retained inspection')):
            receipt = inspect(receipt['record_root'])
        self.assertTrue(receipt['retained_declared_replay_consistent'])

    def test_output_preparation_failures_preserve_prior_whole_exports(self):
        for index, name in enumerate(FILES):
            with self.subTest(name=name):
                output = self.base / ('case-' + str(index))
                output.mkdir()
                (output / name).mkdir()
                receipt, result, code = generate({**self.options, 'output_directory': str(output)}, self.instance, self.node)
                self.assertEqual(code, 1)
                self.assertEqual(result['kernel_exception']['type'], 'ValueError')
                self.assertTrue(all((output / n).is_file() for n in FILES[:index]))
                self.assertTrue(all(not (output / n).exists() for n in FILES[index + 1:]))
                self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])

    def test_output_input_source_instance_and_credential_collisions_are_rejected_before_exports(self):
        cases = [{'output_directory': str(ROOT)}, {'output_directory': str(self.instance)},
                 {'output_directory': str(self.base), 'config': str(self.base / FILES[0])},
                 {'source_worktree': str(self.base / 'observed'), 'observation': None, 'output_directory': str(self.base / 'observed/out')},
                 {'observation': None, 'source_worktree': str(self.base), 'token_file': str(self.config)}]
        for changes in cases:
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                generate({**self.options, **changes}, self.instance, self.node)
        self.assertFalse(self.output.exists())

    def test_wrong_node_record_payload_and_extra_blob_cannot_be_admitted(self):
        receipt, _, _ = generate(self.options, self.instance, self.node)
        with self.assertRaisesRegex(ValueError, 'node_context_changed'):
            inspect(receipt['record_root'], node={**self.node, 'node_id': 'e' * 32})
        root = Path(receipt['record_root'])
        blob = next((root / 'blobs').iterdir())
        original = blob.read_bytes()
        blob.write_bytes(original + b'changed')
        with self.assertRaises(ValueError):
            inspect(root)
        blob.write_bytes(original)
        extra = root / 'blobs' / ('f' * 64)
        extra.write_bytes(b'unused')
        extra.chmod(0o600)
        with self.assertRaisesRegex(ValueError, 'complete_retained_replay_changed'):
            inspect(root)

    def test_coherent_schema_blob_or_path_rewrite_cannot_escape_admitted_product_schema(self):
        # Rehash an otherwise internally consistent journal. Hash-chain validity
        # alone must not permit a schema the actual own-code path never selected.
        for change in ('bytes', 'label'):
            with self.subTest(change=change):
                receipt, _, _ = generate(self.options, self.instance, self.node)
                root = Path(receipt['record_root'])
                request_path = root / 'request.json'
                request = json.loads(request_path.read_bytes())
                rows = [(p, json.loads(p.read_bytes())) for p in sorted((root / 'events').iterdir())]
                operation = next(row['value']['operation'] for _, row in rows
                                 if row['value'].get('action') == 'operations_input'
                                 and row['value']['arguments']['kind'] == 'schema')
                if change == 'label':
                    request['schema_label'] = '/not-the-product/schema.json'
                    request_path.write_bytes(encode(request))
                    for _, row in rows:
                        event = row['value']
                        if event.get('kind') == 'intent' and event.get('operation') == operation:
                            event['arguments']['label'] = request['schema_label']
                else:
                    event = next(row['value'] for _, row in rows
                                 if row['value'].get('kind') == 'returned' and row['value'].get('operation') == operation)
                    old = root / 'blobs' / event['value']['sha256']
                    altered = old.read_bytes() + b'\n '
                    digest = hashlib.sha256(altered).hexdigest()
                    new = root / 'blobs' / digest
                    new.write_bytes(altered)
                    new.chmod(0o600)
                    old.unlink()
                    event['value'] = {'sha256': digest, 'bytes': len(altered)}
                previous = '0' * 64
                for path, row in rows:
                    row['previous'] = previous
                    raw = encode(row)
                    path.write_bytes(raw)
                    previous = hashlib.sha256(raw).hexdigest()
                terminal_path = root / 'result.json'
                terminal = json.loads(terminal_path.read_bytes())
                terminal['event_tip'] = previous
                terminal_path.write_bytes(encode(terminal))
                with self.assertRaises(ValueError):
                    inspect(root)


if __name__ == '__main__':
    unittest.main()
