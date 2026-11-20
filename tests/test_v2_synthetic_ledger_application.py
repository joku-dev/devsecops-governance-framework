"""Complete application results, current-node binding and portable replay."""
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
from unittest.mock import patch
import copy, hashlib, io, json, shutil, sys, unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests')]
import test_v2_synthetic_ledger_core as reference
from lib.synthetic_ledger_application import generate, inspect, run, PROFILE, request_valid
from lib.synthetic_ledger_ports import current_source, read_record, encode
from lib.portable.runtime import source_digest
from lib.functional_parity import git_read


class WholeLedgerApplication(unittest.TestCase):
    def setUp(self):
        self.fixture = reference.WholeSyntheticLedgerCore('test_complete_synthetic_demo_all_history_bytes_modes_stdout_and_nonempty_guard')
        self.fixture.setUp(); self.addCleanup(self.fixture.doCleanups)
        self.data = self.fixture.root; self.instance = self.data.parent / 'instance'
        self.instance.mkdir(mode=0o700)
        self.settings = {'node_id': 'b' * 32, 'source_revision': git_read(ROOT, 'rev-parse', 'HEAD').decode().strip(),
                         'runtime_source_digest': source_digest()}

    def generate(self, program='synthetic', *, native=False, args=None, **extra):
        if args is None:
            args = ['--ledger', str(self.data / 'ledger'), '--output', str(self.data / 'exports/index.json')]
            if program in ('closure', 'exception'): args += ['--report', str(self.data / 'exports/report.md')]
        return generate({'program': program, 'source_worktree': str(self.data), 'write_selected_files': native,
                         'legacy_arguments': args, **extra}, self.instance, self.settings)

    def test_private_whole_synthetic_history_has_source_bound_consistent_record_and_no_source_writes(self):
        before = reference.snapshot(self.data)
        receipt, result = self.generate()
        self.assertEqual(receipt['state'], 'complete', receipt)
        self.assertEqual(receipt['original_exit_code'], 0)
        self.assertTrue(receipt['retained_declared_replay_consistent'])
        self.assertEqual(reference.snapshot(self.data), before)
        self.assertTrue(result['private_projected_changes'])
        self.assertFalse(result['native_ledger_observations'])
        checked = inspect(receipt['record_root'], node=self.settings)
        self.assertEqual(checked['original_exit_code'], 0)
        self.assertEqual(checked['private_creation_mask'], 0o077)
        self.assertFalse(checked['source_output_paths_observed'])
        self.assertFalse(checked['official_acceptance'])

    def test_native_history_and_source_deleted_replay_keep_all_native_observations_without_repeated_effects(self):
        receipt, result = self.generate(native=True)
        self.assertEqual(receipt['state'], 'complete', receipt)
        self.assertTrue(result['native_ledger_observations'])
        self.assertTrue((self.data / 'ledger/transactions').is_dir())
        self.assertTrue((self.data / 'exports/index.json').is_file())
        shutil.rmtree(self.data)
        with (patch('lib.synthetic_ledger_application.NativeIO', side_effect=AssertionError('No native inputs')),
              patch('lib.synthetic_ledger_application.NativeLedgerEffects', side_effect=AssertionError('No native effects')),
              patch('subprocess.Popen', side_effect=AssertionError('No programs'))):
            checked = inspect(receipt['record_root'])
        self.assertEqual(checked['native_ledger_observations'], result['native_ledger_observations'])
        self.assertFalse(checked['native_source_or_exports_repeated'])
        with self.assertRaisesRegex(ValueError, 'foreign_node'):
            inspect(receipt['record_root'], node={**self.settings, 'node_id': 'a' * 32})

    def test_all_six_help_and_parser_two_records_need_no_selected_source_or_ledger_binding(self):
        for program in ('synthetic', 'action', 'closure', 'exception', 'observation', 'record'):
            for args, code in ((['--help'], 0), (['--unknown'], 2)):
                with self.subTest(program=program, argv=args):
                    receipt, result = self.generate(program, args=args, source_worktree='/no-such-selected-source')
                    self.assertEqual(receipt['state'], 'complete', receipt)
                    self.assertEqual(receipt['original_exit_code'], code)
                    self.assertIsNone(result['ledger_binding'])
                    self.assertFalse(result['private_projected_changes'])
                    self.assertEqual(inspect(receipt['record_root'])['original_exit_signal'], {'type': 'SystemExit', 'value': code})

    def test_original_error_after_candidate_history_is_complete_record_with_partial_progress(self):
        directory = self.data / 'directory'; directory.mkdir()
        receipt, result = self.generate(args=['--ledger', str(self.data / 'ledger'), '--output', str(directory)])
        self.assertEqual(receipt['state'], 'complete', receipt)
        self.assertEqual(receipt['original_exit_code'], 1)
        self.assertEqual(result['kernel_result']['kernel_exception']['type'], 'IsADirectoryError')
        self.assertTrue(result['private_projected_changes'])
        self.assertEqual(inspect(receipt['record_root'])['original_exit_code'], 1)

    def test_implicit_schema_URI_is_incomplete_without_original_verdict_or_network(self):
        (self.data / 'schemas/governance-repository-security-report.schema.json').write_text('{"$ref":"https://example.invalid/missing-resource"}')
        for native in (False, True):
            with self.subTest(native=native), patch('urllib.request.urlopen', side_effect=AssertionError('No implicit HTTP')) as network:
                # Observation intake exercises the plain snapshot validator.
                paths, index, row, record = self.fixture.selected_transaction('synthetic-closure', 'observation')
                import base64
                inputs = self.data / ('schema-inputs-' + str(native)); inputs.mkdir()
                (inputs / 'report.json').write_bytes(base64.b64decode(row['resources'][record['body']['snapshot_ref']['uri']], validate=True))
                (inputs / 'context.json').write_text(json.dumps(record['body']['source_context']))
                (inputs / 'trust.json').write_text(json.dumps(record['body']['trust']))
                args = ['--synthetic', '--ledger', str(self.data / ('schema-ledger-' + str(native))),
                    '--report', str(inputs / 'report.json'), '--context', str(inputs / 'context.json'),
                    '--trust', str(inputs / 'trust.json'), '--recorded-at', record['recorded_at'],
                    '--policy-version', record['body']['policy_version'], '--expected-revision', '0']
                receipt, _ = self.generate('observation', native=native, args=args)
                self.assertFalse(network.called)
                self.assertEqual(receipt['state'], 'incomplete')
                self.assertIsNone(receipt['original_exit_code'])
                self.assertEqual(receipt['exit_code'], 2)
                self.assertFalse(inspect(receipt['record_root'])['retained_declared_replay_consistent'])

    def test_source_instance_overlap_and_unregistered_closure_fail_before_records(self):
        with self.assertRaisesRegex(ValueError, 'source_instance_overlap'):
            self.generate(source_worktree=str(self.instance))
        with patch('lib.synthetic_ledger_ports.selected_paths', return_value=[]), self.assertRaisesRegex(ValueError, 'closure_not_registered'):
            current_source(self.settings)
        self.assertFalse((self.instance / 'state').exists())

    def observation_args(self, suffix):
        import base64
        _, _, row, record = self.fixture.selected_transaction('synthetic-closure', 'observation')
        inputs = self.data / ('observation-' + suffix); inputs.mkdir()
        (inputs / 'report.json').write_bytes(base64.b64decode(row['resources'][record['body']['snapshot_ref']['uri']], validate=True))
        (inputs / 'context.json').write_text(json.dumps(record['body']['source_context']))
        (inputs / 'trust.json').write_text(json.dumps(record['body']['trust']))
        return ['--synthetic', '--ledger', str(self.data / ('ledger-' + suffix)),
            '--report', str(inputs / 'report.json'), '--context', str(inputs / 'context.json'),
            '--trust', str(inputs / 'trust.json'), '--recorded-at', record['recorded_at'],
            '--policy-version', record['body']['policy_version'], '--expected-revision', '0']

    def test_all_six_application_programs_preserve_private_and_native_contracts(self):
        for native in (False, True):
            for program in ('synthetic', 'action', 'closure', 'exception', 'observation', 'record'):
                with self.subTest(program=program, native=native):
                    suffix = program + '-' + str(native)
                    if program == 'observation': args = self.observation_args(suffix)
                    elif program == 'record': args, *_ = self.fixture.record_arguments('synthetic-closure', 'decision', suffix)
                    else:
                        args = ['--ledger', str(self.data / ('ledger-' + suffix)), '--output', str(self.data / 'exports' / (suffix + '.json'))]
                        if program in ('closure', 'exception'): args += ['--report', str(self.data / 'exports' / (suffix + '.md'))]
                    before = reference.snapshot(self.data)
                    receipt, result = self.generate(program, native=native, args=args)
                    self.assertEqual(receipt['state'], 'complete', receipt)
                    self.assertEqual(receipt['original_exit_code'], 0, result)
                    self.assertEqual(bool(result['native_ledger_observations']), native)
                    self.assertEqual(bool(result['private_projected_changes']), not native)
                    if not native: self.assertEqual(reference.snapshot(self.data), before)
                    checked = inspect(receipt['record_root'], node=self.settings)
                    self.assertEqual(checked['program'], program)
                    self.assertTrue(checked['retained_declared_replay_consistent'])
                    self.assertFalse(checked['authority_transferred'])

    def reseal(self, root, events, value):
        previous = '0' * 64
        for index, event in enumerate(events):
            raw = encode({'sequence': index, 'previous': previous, 'value': event})
            (root / 'events' / f'{index:08}.json').write_bytes(raw)
            previous = hashlib.sha256(raw).hexdigest()
        value['event_count'], value['event_tip'] = len(events), previous
        (root / 'result.json').write_bytes(encode(value))

    def test_source_request_authority_binding_result_orphan_and_private_frame_tampering_fail_closed(self):
        for attack in ('source', 'request', 'authority', 'authority-type', 'binding', 'result', 'orphan', 'private'):
            with self.subTest(attack=attack):
                receipt, _ = self.generate()
                self.assertEqual(receipt['state'], 'complete')
                root = Path(receipt['record_root'])
                request, source, value, events, _, _ = read_record(root)
                if attack == 'source':
                    source['source_digest'] = '0' * 64; (root / 'source.json').write_bytes(encode(source))
                elif attack == 'request':
                    request['program'] = 'action'; (root / 'request.json').write_bytes(encode(request))
                elif attack.startswith('authority'):
                    value['authority_transferred'] = True if attack == 'authority' else 0
                    (root / 'result.json').write_bytes(encode(value))
                elif attack == 'result':
                    value['result']['kernel_result']['stdout'] += 'forged'
                    (root / 'result.json').write_bytes(encode(value))
                elif attack == 'orphan':
                    raw = b'orphan'; (root / 'blobs' / hashlib.sha256(raw).hexdigest()).write_bytes(raw)
                else:
                    if attack == 'binding': next(row for row in events if row['kind'] == 'synthetic-ledger-root-bound')['selection']['path'] += '-changed'
                    else: next(row for row in events if row['kind'] == 'synthetic-ledger-private-context')['native_source_effects'] = True
                    self.reseal(root, events, value)
                with self.assertRaises((ValueError, TypeError, KeyError)): inspect(root)

    def test_terminal_storage_failure_never_returns_an_original_verdict_or_retries(self):
        with patch('lib.synthetic_ledger_application.Record.finish', side_effect=OSError('terminal unavailable')):
            receipt, result = self.generate(args=['--help'])
        self.assertEqual(receipt['state'], 'incomplete')
        self.assertEqual(receipt['exit_code'], 2)
        self.assertIsNone(receipt['original_exit_code'])
        self.assertFalse(receipt['journal_terminal_written'])
        self.assertEqual(result['exit_code'], 0)

    def test_journal_failure_after_native_lock_releases_writer_without_replaying_failed_finally(self):
        import fcntl, os
        from lib.providers.synthetic_ledger_effects import NativeLedgerEffects
        from lib.providers.synthetic_lifecycle_io import Budget
        from lib.requirement_validation_budget import InputAdmissionError
        owners = []
        original_reserve = Budget.reserve
        class AbortAfterLock(NativeLedgerEffects):
            def flock(owner, descriptor, operation):
                value = super().flock(descriptor, operation)
                if operation == owner.LOCK_EX:
                    owner.io.abort_after_lock = True
                    owners.append(owner)
                return value
        def reserve(owner):
            if getattr(owner, 'abort_after_lock', False):
                raise InputAdmissionError('test_event_budget_after_native_lock')
            return original_reserve(owner)
        with (patch('lib.synthetic_ledger_application.NativeLedgerEffects', AbortAfterLock),
              patch.object(Budget, 'reserve', reserve)):
            receipt, result = self.generate(native=True)
        self.assertEqual(receipt['state'], 'incomplete')
        self.assertIsNone(receipt['original_exit_code'])
        self.assertEqual(receipt['host_resource_release']['released_descriptors'], 1)
        self.assertEqual(receipt['host_resource_release']['remaining_descriptors'], 0)
        self.assertEqual(owners[0].descriptors, {})
        descriptor = os.open(self.data / 'ledger/.append.lock', os.O_RDWR)
        try: fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally: os.close(descriptor)

    def test_original_failed_close_keeps_kernel_resource_facts_before_separate_host_release(self):
        import errno
        from lib.providers.synthetic_ledger_effects import NativeLedgerEffects
        owners = []
        class FailOriginalClose(NativeLedgerEffects):
            def close(owner, descriptor):
                row = owner.descriptor(descriptor)
                if row['role'] != 'lock': return super().close(descriptor)
                owners.append(owner)
                def failure(): raise OSError(errno.EIO, 'original close failed before release')
                return owner.call('close', {'descriptor': descriptor}, [row['path']], failure)
        with patch('lib.synthetic_ledger_application.NativeLedgerEffects', FailOriginalClose):
            receipt, result = self.generate(native=True)
        self.assertEqual(receipt['state'], 'complete', receipt)
        self.assertEqual(receipt['original_exit_code'], 1)
        self.assertEqual(len(result['kernel_end_descriptors']), 1)
        self.assertEqual(receipt['host_resource_release']['released_descriptors'], 1)
        self.assertEqual(owners[0].descriptors, {})
        self.assertEqual(inspect(receipt['record_root'])['kernel_end_descriptors'],
                         result['kernel_end_descriptors'])

    def test_unclosed_buffered_stream_teardown_has_no_complete_original_verdict(self):
        import errno, os
        original = os.fdopen
        class FailedEnter:
            def __init__(owner, handle): owner.handle = handle
            def __getattr__(owner, name): return getattr(owner.handle, name)
            def __enter__(owner): raise OSError(errno.EIO, 'original stream enter failed')
        with patch('lib.providers.synthetic_ledger_effects.os.fdopen',
                   side_effect=lambda *a, **k: FailedEnter(original(*a, **k))):
            receipt, result = self.generate(native=True)
        self.assertEqual(receipt['state'], 'incomplete', receipt)
        self.assertIsNone(receipt['original_exit_code'])
        self.assertEqual(result['kernel_result']['kernel_exception']['type'], 'OSError')
        self.assertEqual(receipt['host_resource_release']['buffered_streams'], 1)
        self.assertEqual(receipt['host_resource_release']['released_descriptors'], 1)
        self.assertEqual(receipt['host_resource_release']['remaining_descriptors'], 0)
        self.assertFalse(list((self.data / 'ledger/transactions').iterdir()))

    def test_command_receipt_legacy_streams_instance_inspection_and_portable_replay(self):
        base = ['generate', '--profile', PROFILE, '--program', 'synthetic',
                '--source-worktree', str(self.data)]
        output = io.StringIO()
        with redirect_stdout(output):
            code = run([*base, '--', '--help'], self.instance, self.settings)
        self.assertEqual(code, 0)
        receipt = json.loads(output.getvalue())
        for command in ('inspect', 'replay'):
            output = io.StringIO()
            with redirect_stdout(output):
                code = run([command, '--record', receipt['record_root']],
                           *([] if command == 'replay' else [self.instance, self.settings]))
            self.assertEqual(code, 0)
            self.assertTrue(json.loads(output.getvalue())['retained_declared_replay_consistent'])
        import subprocess
        original = subprocess.run([sys.executable, '-B', str(self.data / 'scripts' /
            'run_governance_lifecycle_synthetic_demo.py'), '--help'], cwd=self.data,
            capture_output=True, timeout=30)
        output, error = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(error):
            code = run([*base, '--format', 'legacy', '--', '--help'], self.instance, self.settings)
        self.assertEqual(code, original.returncode)
        self.assertEqual(output.getvalue().encode(), original.stdout)
        self.assertEqual(error.getvalue().encode(), original.stderr)

    def test_selected_external_schema_is_retained_and_replays_without_schema_or_source(self):
        uri = 'https://example.invalid/selected-resource'
        (self.data / 'schemas/governance-repository-security-report.schema.json').write_text(json.dumps({'$ref': uri}))
        resource = self.data.parent / 'selected-schema.json'; resource.write_text('{"type":"object"}')
        args = self.observation_args('selected-schema')
        with patch('urllib.request.urlopen', side_effect=AssertionError('No implicit HTTP')):
            receipt, result = self.generate('observation', args=args, schema_resource=[[uri, str(resource)]])
        self.assertEqual(receipt['state'], 'complete', receipt)
        self.assertEqual(result['exit_code'], 0)
        resource.unlink(); shutil.rmtree(self.data)
        with patch('urllib.request.urlopen', side_effect=AssertionError('No replay HTTP')):
            self.assertTrue(inspect(receipt['record_root'])['retained_declared_replay_consistent'])
