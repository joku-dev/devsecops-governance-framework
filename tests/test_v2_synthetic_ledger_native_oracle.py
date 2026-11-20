"""Whole unchanged original CLI versus lazy source IO and real native effects."""
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
import argparse, copy, hashlib, io, json, os, subprocess, sys, tempfile, traceback, unittest
from unittest.mock import patch
from contextlib import nullcontext

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts'), str(ROOT / 'tests')]
import test_v2_synthetic_ledger_core as reference
from lib.providers.synthetic_ledger_io import NativeIO
from lib.providers.synthetic_ledger_effects import NativeLedgerEffects
from lib.providers.synthetic_lifecycle_storage import Record, read_record
from lib.synthetic_lifecycle_context import LifecyclePaths
from lib.synthetic_ledger_context import compose, PROGRAMS
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.repository_schemas import RepositorySchemas
from lib.synthetic_ledger_io import ReplayIO
from lib.synthetic_ledger_replay_effects import ReplayLedgerEffects
from lib.requirement_validation_replay import IntegrityError

FAULT_DRIVER = r'''
import errno,importlib,os,runpy,sys
from unittest.mock import patch
target=sys.argv[1];nth=int(sys.argv[2]);script=sys.argv[3];sys.argv=sys.argv[3:];calls=[]
def fail():raise OSError(errno.EIO,'injected '+target+'-'+str(nth))
class Stream:
 def __init__(self,handle):self.handle=handle
 def __getattr__(self,name):return getattr(self.handle,name)
 def __enter__(self):return self
 def __exit__(self,*args):
  value=self.handle.__exit__(*args)
  if target=='stream-exit':fail()
  return value
 def write(self,raw):
  if target=='stream-write':self.handle.write(raw[:3]);self.handle.flush();fail()
  return self.handle.write(raw)
 def flush(self):
  value=self.handle.flush()
  if target=='stream-flush':fail()
  return value
if target.startswith('stream-'):
 native=os.fdopen
 context=patch('os.fdopen',side_effect=lambda *args,**kw:Stream(native(*args,**kw)))
else:
 module,attribute=target.rsplit('.',1);native=getattr(importlib.import_module(module),attribute)
 def inject(*args,**kw):
  calls.append(1)
  if len(calls)==nth:fail()
  return native(*args,**kw)
 context=patch(target,side_effect=inject)
with context:runpy.run_path(script,run_name='__main__')
'''


class StreamFault:
    def __init__(self, handle, target, nth): self.handle, self.target, self.nth = handle, target, nth
    def __getattr__(self, name): return getattr(self.handle, name)
    def fail(self):
        import errno
        raise OSError(errno.EIO, 'injected ' + self.target + '-' + str(self.nth))
    def __enter__(self): return self
    def __exit__(self, *args):
        value = self.handle.__exit__(*args)
        if self.target == 'stream-exit': self.fail()
        return value
    def write(self, raw):
        if self.target == 'stream-write':
            self.handle.write(raw[:3]); self.handle.flush(); self.fail()
        return self.handle.write(raw)
    def flush(self):
        value = self.handle.flush()
        if self.target == 'stream-flush': self.fail()
        return value


class WholeNativeLedgerOracle(unittest.TestCase):
    setUp = reference.WholeSyntheticLedgerCore.setUp
    selected_transaction = reference.WholeSyntheticLedgerCore.selected_transaction
    record_arguments = reference.WholeSyntheticLedgerCore.record_arguments

    def compare(self, name, args, *, expected_code=0, fault=None):
        before = reference.snapshot(self.root)
        command = [sys.executable, '-B', str(self.root / 'scripts' / PROGRAMS[name][0]), *args]
        if fault: command = [sys.executable, '-B', '-c', FAULT_DRIVER, fault[0], str(fault[1]), *command[2:]]
        original = subprocess.run(command,
            cwd=self.root, capture_output=True, timeout=90,
            env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': str(self.root / 'scripts')})
        self.assertEqual(original.returncode, expected_code, original.stderr[-2500:])
        after = reference.snapshot(self.root)
        original_pending = reference.pending_snapshot(self.root) if fault and fault[0] == 'os.unlink' else None
        reference.restore(self.root, before)
        private = Path(self.temp.name).resolve() / 'private'
        private.mkdir(mode=0o700, exist_ok=True)
        ledger = args[args.index('--ledger') + 1]
        parser = RepositoryLifecycle(ROOT, validator_class=None)
        record = Record(private / 'records', {'name': name, 'argv': args}, {'prototype': True})
        record.append({'kind': 'execution-intent'})
        inputs = NativeIO(record, mode='selected-files', cwd=str(self.root),
            private_state=private, product_root=ROOT, ledger=ledger,
            transaction_name=lambda raw: parser.kernel.transaction_name(parser.adapter.strict_json(raw)))
        paths = LifecyclePaths(str(self.root), str(self.root), inputs)
        effects = NativeLedgerEffects(inputs, ledger,
            transaction_name=lambda raw: parser.kernel.transaction_name(parser.adapter.strict_json(raw)))
        schemas = RepositorySchemas(paths.path(str(self.root)), identifier_bases=(
            'https://joku-dev.github.io/devsecops-governance-framework/schemas/',))
        context, programs = compose(paths.path(str(self.root)), validator_class=schemas,
            path_factory=paths.path, argument_parser=argparse.ArgumentParser, argv=args,
            native=effects, locking=effects, temporary=effects)
        out, err = io.StringIO(), io.StringIO()
        code, error, trace = 0, None, None
        injection = nullcontext()
        if fault:
            target, nth = fault
            if target.startswith('stream-'):
                native = os.fdopen
                injection = patch('lib.providers.synthetic_ledger_effects.os.fdopen',
                    side_effect=lambda *a, **kw: StreamFault(native(*a, **kw), target, nth))
            else:
                import errno, importlib
                module, attribute = target.rsplit('.', 1)
                native = getattr(importlib.import_module(module), attribute)
                calls = []
                def inject(*a, **kw):
                    calls.append(1)
                    if len(calls) == nth: raise OSError(errno.EIO, 'injected ' + target + '-' + str(nth))
                    return native(*a, **kw)
                injection = patch.object(effects, 'sync_descriptor', side_effect=inject) if target == 'os.fsync' else patch(target, side_effect=inject)
        with injection, redirect_stdout(out), redirect_stderr(err):
            try: programs[name].main()
            except SystemExit as failure: code = failure.code or 0
            except Exception as failure: code, error, trace = 1, failure, traceback.format_exc()
        self.assertEqual(code, original.returncode, (error, trace))
        self.assertEqual(out.getvalue().encode(), original.stdout)
        if error is None: self.assertEqual(err.getvalue().encode(), original.stderr)
        else: self.assertTrue(original.stderr.decode().endswith(type(error).__name__ + ': ' + str(error) + '\n'))
        if fault and fault[0] == 'os.unlink':
            self.assertEqual(reference.pending_snapshot(self.root), original_pending)
        else: self.assertEqual(reference.snapshot(self.root), after)
        self.assertFalse(record.capture_incomplete)
        self.assertEqual(effects.descriptors, {})
        record.finish('complete', {'exit_code': code}, {})
        self.last_replay = (record.root, args, name, ledger, effects, (code, error, out.getvalue(), err.getvalue()), inputs)
        self.replay_record(*self.last_replay)
        return context, record.root

    def replay_record(self, record, args, name, ledger, native, expected, inputs, *, events_override=None, expect_integrity=False):
        _, _, _, events, _, _ = read_record(record)
        if events_override is not None: events = events_override
        blobs = {path.name: path.read_bytes() for path in (record / 'blobs').iterdir()}
        seen = set()
        def blob(ref):
            raw = blobs[ref['sha256']]
            self.assertEqual(len(raw), ref['bytes'])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), ref['sha256'])
            seen.add(ref['sha256'])
            return raw
        parser = RepositoryLifecycle(ROOT, validator_class=None)
        name_of = lambda raw: parser.kernel.transaction_name(parser.adapter.strict_json(raw))
        replay = ReplayIO(events, blob, 'selected-files', str(self.root), ledger=ledger, transaction_name=name_of)
        effects = ReplayLedgerEffects(replay, ledger, transaction_name=name_of)
        paths = LifecyclePaths(str(self.root), str(self.root), replay)
        hidden = self.root.parent / 'temporarily-hidden-selected-source'
        self.root.rename(hidden)
        code, error, trace = 0, None, None
        out, err = io.StringIO(), io.StringIO()
        try:
            self.assertFalse(self.root.exists())
            with (patch('os.open', side_effect=AssertionError('No native file access')),
                 patch('pathlib.Path.read_bytes', side_effect=AssertionError('No source reads')),
                 patch('subprocess.Popen', side_effect=AssertionError('No programs')),
                 patch('socket.create_connection', side_effect=AssertionError('No network')),
                 redirect_stdout(out), redirect_stderr(err)):
                schemas = RepositorySchemas(paths.path(str(self.root)), identifier_bases=(
                    'https://joku-dev.github.io/devsecops-governance-framework/schemas/',))
                context, programs = compose(paths.path(str(self.root)), validator_class=schemas,
                    path_factory=paths.path, argument_parser=argparse.ArgumentParser, argv=args,
                    native=effects, locking=effects, temporary=effects)
                try: programs[name].main()
                except SystemExit as failure: code = failure.code or 0
                except Exception as failure: code, error, trace = 1, failure, traceback.format_exc()
            if expect_integrity:
                self.assertIsInstance(error, IntegrityError, trace)
                return
            self.assertEqual(code, expected[0], (error, trace))
            self.assertEqual(None if error is None else (type(error).__name__, str(error)),
                             None if expected[1] is None else (type(expected[1]).__name__, str(expected[1])))
            self.assertEqual((out.getvalue(), err.getvalue()), expected[2:])
            self.assertEqual(effects.state.observed, native.state.observed)
            self.assertEqual(replay.files, inputs.files)
            self.assertEqual(replay.touched, inputs.touched)
            self.assertEqual(effects.descriptors, {})
            replay.finish()
            self.assertEqual(seen, set(blobs), 'Every retained blob must be selected by the complete replay')
        finally: hidden.rename(self.root)

    def demo(self, name):
        args = ['--ledger', str(self.root / 'ledger'), '--output', str(self.root / 'exports/index.json')]
        if name in ('closure', 'exception'): args += ['--report', str(self.root / 'exports/report.md')]
        self.compare(name, args)
        self.compare(name, args, expected_code=1)

    def test_whole_original_synthetic_demo_and_nonempty_guard(self): self.demo('synthetic')
    def test_whole_original_action_demo_and_nonempty_guard(self): self.demo('action')
    def test_whole_original_closure_demo_and_nonempty_guard(self): self.demo('closure')
    def test_whole_original_exception_demo_and_nonempty_guard(self): self.demo('exception')

    def test_whole_original_four_record_intakes_and_duplicates(self):
        for kind, scenario in (('decision', 'synthetic-closure'), ('remediation', 'synthetic-closure'),
                               ('closure', 'synthetic-closure'), ('exception', 'synthetic-exceptions')):
            with self.subTest(kind=kind):
                args, *_ = self.record_arguments(scenario, kind, 'native-' + kind)
                self.compare('record', args)
                self.compare('record', args)

    def test_whole_original_observation_intake_and_duplicate(self):
        import base64
        _, _, row, record = self.selected_transaction('synthetic-closure', 'observation')
        inputs = self.root / 'observation-inputs'
        inputs.mkdir()
        (inputs / 'report.json').write_bytes(base64.b64decode(row['resources'][record['body']['snapshot_ref']['uri']], validate=True))
        (inputs / 'context.json').write_bytes(json.dumps(record['body']['source_context']).encode())
        (inputs / 'trust.json').write_bytes(json.dumps(record['body']['trust']).encode())
        args = ['--synthetic', '--ledger', str(self.root / 'observations'), '--report', str(inputs / 'report.json'),
                '--context', str(inputs / 'context.json'), '--trust', str(inputs / 'trust.json'),
                '--recorded-at', record['recorded_at'], '--policy-version', record['body']['policy_version'], '--expected-revision', '0']
        self.compare('observation', args)
        self.compare('observation', args)

    def failure(self, target, nth=1):
        args = ['--ledger', str(self.root / 'failed-ledger'), '--output', str(self.root / 'exports/index.json')]
        self.compare('synthetic', args, expected_code=1, fault=(target, nth))

    def test_whole_original_file_fsync_failure_replays_cleanup_without_native_effects(self): self.failure('os.fsync', 1)
    def test_whole_original_directory_fsync_failure_replays_already_published_transaction(self): self.failure('os.fsync', 2)
    def test_whole_original_link_failure_replays_finally_cleanup(self): self.failure('os.link')
    def test_whole_original_unlink_failure_replays_persistent_same_inode_pair(self): self.failure('os.unlink')
    def test_whole_original_lock_failure_replays_unlock_close_order(self): self.failure('fcntl.flock')
    def test_whole_original_partial_buffer_write_failure_replays_exact_three_bytes_before_cleanup(self): self.failure('stream-write')
    def test_whole_original_buffer_flush_failure_replays_full_bytes_then_cleanup(self): self.failure('stream-flush')
    def test_whole_original_stream_close_failure_replays_closed_resource_and_cleanup(self): self.failure('stream-exit')

    def test_whole_original_duplicate_retry_reads_persistent_pending_canonical_pair(self):
        args, ledger, *_ = self.record_arguments('synthetic-closure', 'decision', 'paired-retry')
        self.compare('record', args, expected_code=1, fault=('os.unlink', 1))
        pending = next((ledger / 'transactions').glob('.pending-*'))
        before = reference.pending_snapshot(ledger)
        self.compare('record', args)
        self.assertEqual(reference.pending_snapshot(ledger), before)
        self.assertEqual(pending.stat().st_nlink, 2)

    def test_resealed_namespace_inode_prefix_resource_publication_and_attempt_facts_are_rejected(self):
        args = ['--ledger', str(self.root / 'ledger'), '--output', str(self.root / 'exports/index.json')]
        self.compare('synthetic', args)
        record, *_ = self.last_replay
        _, _, _, events, _, _ = read_record(record)
        for change in ('namespace', 'inode', 'prefix', 'resource', 'publication', 'attempt', 'owner'):
            with self.subTest(change=change):
                rows = copy.deepcopy(events)
                action = {'namespace': 'fsync', 'inode': 'stream-write', 'prefix': 'stream-write',
                          'resource': 'stream-exit', 'publication': 'link', 'attempt': 'mkstemp', 'owner': 'stream-write'}[change]
                after = next(row for row in rows if row['kind'] == 'synthetic-ledger-effect-after' and row['action'] == action)
                if change == 'namespace':
                    directory = str(self.root / 'ledger/transactions')
                    after['files'][directory]['members'].append('forged-entry.json')
                    after['files'][directory]['members'].sort()
                elif change in ('inode', 'prefix', 'owner'):
                    value = next(value for name, value in after['files'].items() if Path(name).name.startswith('.pending-'))
                    if change == 'inode':
                        value['snapshot']['identity'][1] += 1
                        value['metadata']['identity'] = list(value['snapshot']['identity'])
                    elif change == 'prefix':
                        value['snapshot']['content'] = {'sha256': hashlib.sha256(b'null\n').hexdigest(), 'bytes': 5}
                        value['metadata']['bytes'] = 5
                    else: value['metadata']['uid'] += 1
                elif change == 'resource':
                    before = next(row for row in rows if row['kind'] == 'synthetic-ledger-effect-before' and row['action'] == 'stream-exit')
                    resource = copy.deepcopy(next(row for row in before['descriptors'] if row['role'] == 'temporary'))
                    resource['descriptor'] = 999
                    after['descriptors'].append(resource)
                elif change == 'publication':
                    for value in after['files'].values():
                        if value['snapshot']['kind'] == 'file':
                            value['metadata']['nlink'] = 1
                            value['aliases'] = []
                else: after['attempts'][-1] = str(self.root / 'outside-ledger')
                self.replay_record(*self.last_replay, events_override=rows, expect_integrity=True)


if __name__ == '__main__': unittest.main()
