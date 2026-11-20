"""Complete original POSIX store sequence over explicitly injected effect ports.

Native publication, locks, streams and temporary names belong to those ports.
"""
from contextlib import contextmanager

class SyntheticLedgerStore:

    def __init__(self, context, *, path_factory, native, locking, temporary):
        self.context = context
        self.path_factory = path_factory
        self.native = native
        self.locking = locking
        self.temporary = temporary

    @contextmanager
    def writer_lock(self, root):
        root = self.path_factory(root)
        self.context.contracts.require(not root.is_symlink(), 'Ledger root must not be a symlink')
        root.mkdir(parents=True, exist_ok=True)
        descriptor = self.native.open(root / '.append.lock', self.native.O_CREAT | self.native.O_RDWR | self.native.O_NOFOLLOW, 384)
        try:
            self.locking.flock(descriptor, self.locking.LOCK_EX)
            yield
        finally:
            self.locking.flock(descriptor, self.locking.LOCK_UN)
            self.native.close(descriptor)

    def load_transactions(self, root):
        directory = self.path_factory(root) / 'transactions'
        self.context.contracts.require(not self.path_factory(root).is_symlink() and (not directory.is_symlink()), 'Ledger paths must not be symlinks')
        if self.path_factory(root).exists():
            self.context.contracts.require(all((p.name in ('transactions', '.append.lock') and (not p.is_symlink()) for p in self.path_factory(root).iterdir())), 'Unexpected file in ledger root')
        if not directory.exists():
            return []
        entries = sorted(directory.iterdir())
        transactions = []
        for path in entries:
            if path.name.startswith('.pending-'):
                self.context.contracts.require(not path.is_symlink(), 'Pending entry must not be a symlink')
                continue
            self.context.contracts.require(path.is_file() and (not path.is_symlink()), 'Unexpected ledger entry or symlink')
            self.context.contracts.require(path.suffix == '.json', 'Unexpected transaction filename')
            transaction = self.context.adapter.strict_json(path.read_bytes())
            self.context.contracts.require(path.name == self.context.kernel.transaction_name(transaction), 'Transaction filename does not bind content identity')
            transactions.append(transaction)
        return transactions

    def publish_transaction(self, directory, transaction):
        """Hard-link a fully fsynced file into place without overwriting an existing entry."""
        directory.mkdir(parents=True, exist_ok=True)
        self.context.contracts.require(not directory.is_symlink(), 'Transaction directory must not be a symlink')
        descriptor, temporary = self.temporary.mkstemp(prefix='.pending-', dir=directory)
        try:
            with self.native.fdopen(descriptor, 'wb') as handle:
                handle.write(self.context.adapter.json_bytes(transaction))
                handle.flush()
                self.native.fsync(handle.fileno())
            target = directory / self.context.kernel.transaction_name(transaction)
            self.native.link(temporary, target)
            directory_fd = self.native.open(directory, self.native.O_RDONLY | self.native.O_DIRECTORY)
            try:
                self.native.fsync(directory_fd)
            finally:
                self.native.close(directory_fd)
        finally:
            self.native.unlink(temporary)

    def append_observation(self, root, observation, resources, profile, *, expected_revision):
        with self.writer_lock(root):
            transactions = self.load_transactions(root)
            state = self.context.kernel.replay(transactions, profile)
            transaction = self.context.kernel.prepare_transaction(observation, resources, profile, state, expected_revision=expected_revision)
            if transaction is None:
                return {'outcome': 'duplicate', 'transaction_ref': None}
            self.publish_transaction(self.path_factory(root) / 'transactions', transaction)
            return {'outcome': transaction['outcome'], 'transaction_ref': self.context.kernel.transaction_ref(transaction)}

    def append_action(self, root, record, resources, profile, *, expected_revision):
        with self.writer_lock(root):
            state = self.context.kernel.replay(self.load_transactions(root), profile)
            transaction = self.context.decisions.prepare_action_transaction(record, resources, profile, state, expected_revision=expected_revision)
            if transaction is None:
                return {'outcome': 'duplicate', 'transaction_ref': None}
            self.publish_transaction(self.path_factory(root) / 'transactions', transaction)
            return {'outcome': transaction['outcome'], 'transaction_ref': self.context.kernel.transaction_ref(transaction)}

    def append_closure(self, root, record, resources, profile, *, expected_revision):
        with self.writer_lock(root):
            state = self.context.kernel.replay(self.load_transactions(root), profile)
            transaction = self.context.closure.prepare_closure_transaction(record, resources, profile, state, expected_revision=expected_revision)
            if transaction is None:
                return {'outcome': 'duplicate', 'transaction_ref': None}
            self.publish_transaction(self.path_factory(root) / 'transactions', transaction)
            return {'outcome': 'accepted', 'transaction_ref': self.context.kernel.transaction_ref(transaction)}

    def append_exception(self, root, record, resources, profile, *, expected_revision):
        with self.writer_lock(root):
            state = self.context.kernel.replay(self.load_transactions(root), profile)
            transaction = self.context.exceptions.prepare_exception_transaction(record, resources, profile, state, expected_revision=expected_revision)
            if transaction is None:
                return {'outcome': 'duplicate', 'transaction_ref': None}
            self.publish_transaction(self.path_factory(root) / 'transactions', transaction)
            return {'outcome': 'accepted', 'transaction_ref': self.context.kernel.transaction_ref(transaction)}
