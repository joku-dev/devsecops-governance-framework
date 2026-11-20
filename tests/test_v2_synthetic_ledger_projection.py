"""Whole store publication in a private inode model; no native-effect claims."""
from pathlib import Path, PurePosixPath
from types import SimpleNamespace
import errno, hashlib, sys, unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts')]
from lib.synthetic_ledger_projection import LedgerProjection, PrivateLedgerEffects
from lib.synthetic_ledger_store import SyntheticLedgerStore
from lib.requirement_validation_replay import IntegrityError
from lib.requirement_validation_budget import InputAdmissionError


class PrivateLedgerProjectionTests(unittest.TestCase):
    def setUp(self):
        self.blobs = {}
        self.events = []
        self.tree = LedgerProjection(lambda ref: self.blobs[ref['sha256']])
        self.tree.load_one('/', {'kind': 'directory', 'mode': 0o700, 'identity': [90, 1]})
        self.tree.load_membership('/', [])
        self.tree.mkdir('/ledger', 0o777, True, True, '/ledger')
        self.tree.mkdir('/ledger/transactions', 0o777, True, True, '/ledger/transactions')
        self.effects = PrivateLedgerEffects(self.tree, self.store,
            absolute=lambda path: str(path if path.is_absolute() else PurePosixPath('/') / path),
            emit=self.events.append)

    def store(self, raw):
        ref = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
        self.blobs[ref['sha256']] = raw
        return ref

    def path(self, name):
        from lib.synthetic_lifecycle_context import LifecyclePaths
        case = self
        class IO:
            def mkdir(self, path, mode, parents, exist_ok, label):
                return case.tree.mkdir(path, mode, parents, exist_ok, label)
            def probe(self, path, kind, label): return case.tree.probe(path, kind)
        return LifecyclePaths('/', '/', IO()).path(name)

    def store_context(self):
        def require(ok, message):
            if not ok: raise ValueError(message)
        context = SimpleNamespace(contracts=SimpleNamespace(require=require),
            adapter=SimpleNamespace(json_bytes=lambda transaction: b'{"a":1}\n'),
            kernel=SimpleNamespace(transaction_name=lambda transaction: '0001.json'))
        return SyntheticLedgerStore(context, path_factory=lambda value: value,
            native=self.effects, locking=self.effects, temporary=self.effects)

    def publish(self):
        self.store_context().publish_transaction(self.path('/ledger/transactions'), {'a': 1})

    def test_whole_original_store_sequence_private_publication_and_resource_cleanup(self):
        self.store(b'')
        self.publish()
        path = '/ledger/transactions/0001.json'
        self.assertEqual(self.tree.read(path, path), b'{"a":1}\n')
        self.assertEqual(self.tree.state(path)['mode'], 0o600)
        self.assertEqual(self.tree.entries('/ledger/transactions', '/ledger/transactions'), ['0001.json'])
        self.assertEqual(self.effects.descriptors, {})
        self.assertTrue(all(row['native_effect'] is False for row in self.events))
        self.assertEqual([row['action'] for row in self.events],
            ['mkstemp', 'fdopen', 'stream-write', 'stream-flush', 'fsync',
             'stream-flush', 'close', 'link', 'open', 'fsync', 'close', 'unlink'])

    def test_directory_fsync_failure_preserves_published_history_and_cleans_temporary(self):
        self.store(b'')
        fsync = self.effects.fsync
        def fail(descriptor):
            if self.effects.descriptor(descriptor)['kind'] == 'directory':
                raise OSError(errno.EIO, 'directory fsync failed')
            return fsync(descriptor)
        with patch.object(self.effects, 'fsync', side_effect=fail):
            with self.assertRaisesRegex(OSError, 'directory fsync failed'): self.publish()
        self.assertEqual(self.tree.entries('/ledger/transactions', ''), ['0001.json'])
        self.assertEqual(self.effects.descriptors, {})

    def test_unlink_failure_retains_known_two_name_inode_with_published_transaction(self):
        self.store(b'')
        with patch.object(self.effects, 'unlink', side_effect=OSError(errno.EIO, 'unlink failed')):
            with self.assertRaisesRegex(OSError, 'unlink failed'): self.publish()
        value = self.tree.state('/ledger/transactions/0001.json')
        names = self.tree.aliases(value['identity'])
        self.assertEqual(len(names), 2)
        self.assertEqual([self.tree.read(n, n) for n in names], [b'{"a":1}\n'] * 2)
        self.assertTrue(any(PurePosixPath(n).name.startswith('.pending-private-') for n in names))
        self.assertEqual(self.effects.descriptors, {})

    def test_exclusive_target_failure_keeps_original_bytes_and_identity(self):
        self.store(b'')
        self.publish()
        original = dict(self.tree.state('/ledger/transactions/0001.json'))
        with self.assertRaises(FileExistsError): self.publish()
        self.assertEqual(self.tree.state('/ledger/transactions/0001.json'), original)
        self.assertEqual(self.tree.entries('/ledger/transactions', ''), ['0001.json'])

    def test_buffer_flush_and_shared_inode_bytes_are_explicit_before_publication(self):
        self.store(b'')
        fd, name = self.effects.mkstemp(prefix='.pending-', dir='/ledger/transactions')
        handle = self.effects.fdopen(fd, 'wb')
        self.assertEqual(handle.write(b'abc'), 3)
        self.assertEqual(self.tree.read(name, name), b'')
        self.effects.link(name, '/ledger/transactions/alias.json')
        handle.flush()
        self.assertEqual(self.tree.read('/ledger/transactions/alias.json', ''), b'abc')
        self.effects.unlink(name)
        handle.write(b'def')
        handle.close()
        self.assertEqual(self.tree.read('/ledger/transactions/alias.json', ''), b'abcdef')
        self.assertEqual(self.tree.aliases(self.tree.state('/ledger/transactions/alias.json')['identity']),
                         ['/ledger/transactions/alias.json'])

    def test_writer_lock_finally_releases_and_closes_after_original_body_error(self):
        self.store(b'')
        with self.assertRaisesRegex(ValueError, 'body failed'):
            with self.store_context().writer_lock(self.path('/ledger')):
                self.assertEqual(len(self.effects.locks), 1)
                raise ValueError('body failed')
        self.assertEqual(self.effects.locks, {})
        self.assertEqual(self.effects.descriptors, {})
        self.assertEqual(self.tree.state('/ledger/.append.lock')['mode'], 0o600)
        self.assertEqual([row['action'] for row in self.events], ['open', 'flock', 'flock', 'close'])

    def test_no_unobserved_directory_membership_is_assumed_empty(self):
        tree = LedgerProjection(lambda ref: b'')
        tree.load_one('/', {'kind': 'directory', 'mode': 0o700, 'identity': [90, 1]})
        with self.assertRaisesRegex(IntegrityError, 'unobserved_path'): tree.state('/unknown')
        with self.assertRaisesRegex(IntegrityError, 'membership_missing'): tree.entries('/', '/')
        tree.load_membership('/', ['retained'])
        with self.assertRaisesRegex(IntegrityError, 'unobserved_path'): tree.state('/retained')
        self.assertEqual(tree.state('/missing'), {'kind': 'missing'})
        self.assertEqual(tree.state('/missing/child/grandchild'), {'kind': 'missing'})
        self.assertEqual(tree.entries('/', '/'), ['retained'])
        with self.assertRaisesRegex(IntegrityError, 'unobserved_path'): tree.state('/retained')

    def test_reservation_failure_precedes_open_creation_and_persists_no_lock(self):
        self.effects.emit = lambda row: (_ for _ in ()).throw(InputAdmissionError('journal full'))
        with self.assertRaisesRegex(InputAdmissionError, 'journal full'):
            self.effects.open('/ledger/.append.lock', 7, 0o600)
        self.assertEqual(self.tree.state('/ledger/.append.lock'), {'kind': 'missing'})
        self.assertEqual(self.effects.descriptors, {})

    def test_invalid_and_closed_descriptors_cannot_be_reused_and_stream_close_is_idempotent(self):
        self.store(b'')
        fd, name = self.effects.mkstemp(prefix='.pending-', dir='/ledger/transactions')
        handle = self.effects.fdopen(fd, 'wb')
        handle.close()
        count = len(self.events)
        handle.close()
        self.assertEqual(len(self.events), count)
        with self.assertRaises(ValueError): handle.write(b'x')
        with self.assertRaises(OSError): self.effects.fsync(fd)
        with self.assertRaises(OSError): self.effects.close(True)
        with self.assertRaises(InputAdmissionError): self.effects.open('/ledger/x', 128, 0o600)


if __name__ == '__main__': unittest.main()
