"""Real atomic native effects retain original store order and partial states."""
from pathlib import Path
from types import SimpleNamespace
import errno, json, os, sys, tempfile, unittest
import fcntl
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts')]
from lib.synthetic_ledger_io import ReplayIO
from lib.synthetic_ledger_replay_effects import ReplayLedgerEffects
from lib.providers.synthetic_lifecycle_storage import Record, read_record
from lib.providers.synthetic_lifecycle_io import NativeIO
from lib.providers.synthetic_ledger_effects import NativeLedgerEffects
from lib.synthetic_ledger_store import SyntheticLedgerStore
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.requirement_validation_budget import InputAdmissionError


class NativeLedgerEffectsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.data = self.root / 'data'
        self.data.mkdir(mode=0o700)
        self.private = self.root / 'private'
        self.private.mkdir(mode=0o700)
        self.ledger = self.data / 'ledger'
        self.transactions = self.ledger / 'transactions'
        self.transactions.mkdir(parents=True, mode=0o700)
        self.context = RepositoryLifecycle(ROOT, validator_class=None)
        self.transaction = json.loads(next((ROOT / 'governance/lifecycle/synthetic-closure/transactions').glob('*.json')).read_bytes())
        self.name = self.context.kernel.transaction_name(self.transaction)
        self.record = Record(self.private / 'records', {'test': 'whole-native-store'}, {'declared': True})
        self.record.append({'kind': 'execution-intent'})
        self.io = NativeIO(self.record, mode='selected-files', cwd=str(self.data), private_state=self.private, product_root=ROOT)
        self.effects = NativeLedgerEffects(self.io, str(self.ledger), transaction_name=lambda raw:
            self.context.kernel.transaction_name(self.context.adapter.strict_json(raw)))
        self.store = SyntheticLedgerStore(self.context, path_factory=Path,
            native=self.effects, locking=self.effects, temporary=self.effects)

    def publish(self): self.store.publish_transaction(self.transactions, self.transaction)

    def events(self):
        return [json.loads(p.read_bytes())['value'] for p in sorted(self.record.events.glob('*.json'))]

    def test_whole_original_publication_buffers_fsyncs_links_and_cleans_real_temporary(self):
        self.publish()
        self.assertEqual((self.transactions / self.name).read_bytes(), self.context.adapter.json_bytes(self.transaction))
        self.assertEqual([p.name for p in self.transactions.iterdir()], [self.name])
        self.assertEqual(self.effects.descriptors, {})
        rows = self.events()
        before = [row for row in rows if row['kind'] == 'synthetic-ledger-effect-before']
        self.assertEqual([row['action'] for row in before],
            ['mkstemp', 'fdopen', 'stream-enter', 'stream-write', 'stream-flush',
             'fsync', 'stream-exit', 'link', 'open', 'fsync', 'close', 'unlink'])
        after_link = next(row for row in rows if row['kind'] == 'synthetic-ledger-effect-after' and row['action'] == 'link')
        self.assertEqual(len(after_link['files']), 4)
        values = [row for row in after_link['files'].values() if row['snapshot']['kind'] == 'file']
        self.assertEqual(len(values), 2)
        self.assertEqual(values[0], values[1])
        self.assertEqual(values[0]['metadata']['nlink'], 2)
        self.assertEqual(after_link['files'][str(self.transactions)]['members'], sorted([Path(n).name for n in values[0]['aliases']]))
        self.assertFalse(self.record.capture_incomplete)
        # Actual producer OS fd integers do not appear as resource tokens.
        self.assertEqual({r['descriptor'] for row in before for r in row['descriptors']}, {1, 2})

    def test_directory_fsync_failure_retains_published_transaction_and_original_error(self):
        original = os.fsync
        calls = []
        def fail(fd):
            calls.append(fd)
            if len(calls) == 2: raise OSError(errno.EIO, 'directory fsync failure')
            return original(fd)
        with patch.object(self.effects, 'sync_descriptor', side_effect=fail):
            with self.assertRaisesRegex(OSError, 'directory fsync failure'): self.publish()
        self.assertEqual([p.name for p in self.transactions.iterdir()], [self.name])
        self.assertEqual(self.effects.descriptors, {})
        failed = [r for r in self.events() if r['kind'] == 'synthetic-ledger-effect-after' and r['failure']]
        self.assertEqual(len(failed), 1)
        self.assertEqual(failed[0]['failure']['errno'], errno.EIO)
        self.assertFalse(self.record.capture_incomplete)

    def test_unlink_failure_retains_complete_same_inode_pair_and_can_be_read_again(self):
        original = os.unlink
        def fail(path, *args, **kwargs):
            if str(path).startswith('.pending-'): raise OSError(errno.EIO, 'pending unlink failure')
            return original(path, *args, **kwargs)
        with patch('lib.providers.synthetic_ledger_effects.os.unlink', side_effect=fail):
            with self.assertRaisesRegex(OSError, 'pending unlink failure'): self.publish()
        pending = next(self.transactions.glob('.pending-*'))
        accepted = self.transactions / self.name
        self.assertEqual(accepted.stat().st_ino, pending.stat().st_ino)
        self.assertEqual(accepted.stat().st_nlink, 2)
        raw, observation = self.effects.files.read(str(accepted), str(accepted))
        self.assertEqual(raw, self.context.adapter.json_bytes(self.transaction))
        self.assertEqual(len(observation['aliases']), 2)
        self.assertEqual(self.effects.descriptors, {})
        self.assertFalse(self.record.capture_incomplete)

    def test_writer_lock_closes_after_original_body_error_and_records_finally_order(self):
        with self.assertRaisesRegex(ValueError, 'body failed'):
            with self.store.writer_lock(self.ledger): raise ValueError('body failed')
        self.assertEqual(self.effects.descriptors, {})
        actions = [r['action'] for r in self.events() if r['kind'] == 'synthetic-ledger-effect-before']
        self.assertEqual(actions, ['open', 'flock', 'flock', 'close'])

    def test_admission_and_record_reservation_fail_before_native_lock_creation(self):
        with patch.object(self.io, 'append', side_effect=InputAdmissionError('journal unavailable')):
            with self.assertRaisesRegex(InputAdmissionError, 'journal unavailable'):
                self.effects.open(self.ledger / '.append.lock', 7, 0o600)
        self.assertFalse((self.ledger / '.append.lock').exists())
        self.assertTrue(self.record.capture_incomplete)
        self.assertEqual(self.effects.descriptors, {})

    def test_private_mode_foreign_path_and_unsupported_flags_cannot_execute_native_effects(self):
        for path, flags in ((self.data / 'elsewhere', 7), (self.ledger / '.append.lock', 128)):
            with self.subTest(path=path, flags=flags):
                with self.assertRaises(InputAdmissionError): self.effects.open(path, flags, 0o600)
        self.assertFalse((self.data / 'elsewhere').exists())
        with self.assertRaises(InputAdmissionError):
            NativeLedgerEffects(SimpleNamespace(mode='private-candidate'), str(self.ledger), transaction_name=lambda raw: '')

    def test_contended_native_lock_has_finite_technical_timeout_and_original_finally_cleanup(self):
        lock = self.ledger / '.append.lock'
        external = os.open(lock, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(external, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.effects.lock_seconds = 0.01
            with self.assertRaisesRegex(InputAdmissionError, 'lock_capture_timeout'):
                with self.store.writer_lock(self.ledger): self.fail('Must never enter contended body')
            self.assertEqual(self.effects.descriptors, {})
            self.assertTrue(self.record.capture_incomplete)
            # Our failed acquisition/finally did not release somebody else's
            # lock and cannot be represented as an original business verdict.
            another = os.open(lock, os.O_RDWR)
            try:
                with self.assertRaises(BlockingIOError): fcntl.flock(another, fcntl.LOCK_EX | fcntl.LOCK_NB)
            finally: os.close(another)
        finally:
            fcntl.flock(external, fcntl.LOCK_UN)
            os.close(external)

    def test_previously_read_lock_file_cannot_change_before_native_open(self):
        lock = self.ledger / '.append.lock'
        lock.write_bytes(b'old')
        lock.chmod(0o600)
        self.assertEqual(self.io.read(str(lock), str(lock)), b'old')
        lock.write_bytes(b'new original input')
        with self.assertRaisesRegex(InputAdmissionError, 'input_changed_before_effect'):
            self.effects.open(lock, 7, 0o600)
        self.assertEqual(lock.read_bytes(), b'new original input')
        self.assertEqual(self.effects.descriptors, {})
        self.assertTrue(self.record.capture_incomplete)

    def test_file_replacement_during_fsync_is_incomplete_even_with_identical_bytes(self):
        original = self.effects.sync_descriptor
        replaced = []
        def replace(fd):
            result = original(fd)
            if not replaced:
                replaced.append(1)
                temporary = next(self.transactions.glob('.pending-*'))
                replacement = self.transactions / 'replacement'
                replacement.write_bytes(temporary.read_bytes())
                replacement.chmod(0o600)
                os.replace(replacement, temporary)
            return result
        try:
            with patch.object(self.effects, 'sync_descriptor', side_effect=replace):
                with self.assertRaises(InputAdmissionError): self.publish()
            self.assertTrue(self.record.capture_incomplete)
            self.assertFalse((self.transactions / self.name).exists())
        finally:
            # Explicit test-harness fd disposal after technical abort; never
            # represented as a completed original effect or namespace rollback.
            for row in self.effects.descriptors.values():
                if row['handle'] is not None: row['handle'].close()
                else: os.close(row['fd'])

    def test_failed_temporary_open_can_leave_a_real_unpublished_file_and_replay_that_partial_state(self):
        original = os.open
        created = []
        def fail(path, *args, **kwargs):
            fd = original(path, *args, **kwargs)
            if (str(path).startswith('.pending-') and kwargs.get('dir_fd') is not None
                    and args[0] & os.O_CREAT and args[0] & os.O_EXCL):
                os.close(fd)
                created.append(str(self.transactions / path))
                raise OSError(errno.EIO, 'open failed after creating entry', path)
            return fd
        with patch('lib.providers.synthetic_ledger_effects.os.open', side_effect=fail):
            with self.assertRaisesRegex(OSError, 'open failed after creating entry') as actual:
                self.effects.mkstemp(prefix='.pending-', dir=self.transactions)
        self.assertEqual(len(created), 1)
        self.assertEqual(Path(created[0]).read_bytes(), b'')
        self.assertFalse(self.record.capture_incomplete)
        self.assertEqual(self.effects.descriptors, {})
        self.record.finish('complete', {'exit_code': 1}, {})
        _, _, _, events, blob, closed = read_record(self.record.root)
        replay = ReplayIO(events, blob, 'selected-files', str(self.data), ledger=str(self.ledger),
            transaction_name=self.effects.transaction_name)
        ports = ReplayLedgerEffects(replay, str(self.ledger), transaction_name=self.effects.transaction_name)
        with self.assertRaises(OSError) as retained: ports.mkstemp(prefix='.pending-', dir=self.transactions)
        self.assertEqual(str(retained.exception), str(actual.exception))
        self.assertEqual(ports.state.observed, self.effects.state.observed)
        replay.finish()
        self.assertTrue(closed())

    def test_exclusive_temporary_collision_retains_attempts_without_overwriting_existing_file(self):
        collision = self.transactions / '.pending-collision'
        collision.write_bytes(b'untouched prior bytes')
        collision.chmod(0o600)
        with patch('lib.providers.synthetic_ledger_effects.tempfile._get_candidate_names', return_value=iter(('collision', 'fresh'))):
            token, path = self.effects.mkstemp(prefix='.pending-', dir=self.transactions)
        self.assertEqual(collision.read_bytes(), b'untouched prior bytes')
        self.assertEqual(path, str(self.transactions / '.pending-fresh'))
        after = next(row for row in self.events() if row['kind'] == 'synthetic-ledger-effect-after')
        self.assertEqual(after['attempts'], [str(collision), path])
        self.effects.close(token)

    def test_unrelated_namespace_change_during_fsync_cannot_be_resealed_as_owned_effect(self):
        original = self.effects.sync_descriptor
        changed = []
        def inject(fd):
            result = original(fd)
            if not changed:
                changed.append(1)
                (self.transactions / 'foreign-entry').write_bytes(b'not our store effect')
            return result
        try:
            with patch.object(self.effects, 'sync_descriptor', side_effect=inject):
                with self.assertRaises(InputAdmissionError): self.publish()
            self.assertTrue(self.record.capture_incomplete)
            self.assertEqual((self.transactions / 'foreign-entry').read_bytes(), b'not our store effect')
        finally:
            for row in self.effects.descriptors.values():
                if row['handle'] is not None: row['handle'].close()
                else: os.close(row['fd'])


    def test_host_resource_release_refuses_replaced_descriptor_and_releases_only_own_binding(self):
        token = self.effects.open(self.ledger / '.append.lock',
            self.effects.O_CREAT | self.effects.O_RDWR | self.effects.O_NOFOLLOW, 0o600)
        fd = self.effects.descriptors[token]['fd']
        sequence = self.record.sequence
        first = self.effects.release_resources()
        self.assertEqual(first['released_descriptors'], 1)
        self.assertEqual(self.record.sequence, sequence, 'Teardown must not invent original journal events')
        self.assertEqual(len(self.effects.state.descriptors), 1, 'Original end facts stay unchanged')
        self.assertEqual(self.effects.release_resources()['observed_descriptors'], 0)

        # A new independently bound operation can be tested with a fresh store;
        # never change the earlier original execution's retained descriptor state.
        other_record = Record(self.private / 'other-records', {'test': 'replacement'}, {'declared': True})
        other_record.append({'kind': 'execution-intent'})
        other_io = NativeIO(other_record, mode='selected-files', cwd=str(self.data),
                            private_state=self.private, product_root=ROOT)
        owner = NativeLedgerEffects(other_io, str(self.ledger), transaction_name=lambda raw: self.name)
        token = owner.open(self.ledger / '.append.lock',
                           owner.O_CREAT | owner.O_RDWR | owner.O_NOFOLLOW, 0o600)
        fd = owner.descriptors[token]['fd']
        foreign = self.data / 'foreign.txt'; foreign.write_bytes(b'foreign descriptor must remain open')
        replacement = os.open(foreign, os.O_RDONLY)
        try:
            os.dup2(replacement, fd)
            value = owner.release_resources()
            self.assertEqual(value['released_descriptors'], 0)
            self.assertEqual(value['errors'], ['descriptor_identity_changed'])
            self.assertEqual(os.fstat(fd).st_ino, foreign.stat().st_ino)
        finally:
            os.close(replacement); os.close(fd)
            owner.descriptors.clear()


if __name__ == '__main__': unittest.main()
