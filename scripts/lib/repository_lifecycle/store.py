"""Original lifecycle consistency over an explicit retained data context.

Technical reference: V1 6b557f. Original records remain declared historical
facts; these checks never grant this node live approval, identity or consent.
"""
class LifecycleStore:

    def __init__(self, root, context, *, validator_class, path_factory):
        self.root = root
        self.context = context
        self.validator_class = validator_class
        self.path_factory = path_factory

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
