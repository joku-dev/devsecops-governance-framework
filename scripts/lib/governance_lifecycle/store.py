"""Atomic append-only file transactions on a local POSIX filesystem."""
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import tempfile

from .adapter import json_bytes, strict_json
from .contracts import require
from .kernel import prepare_transaction, replay, transaction_name, transaction_ref


@contextmanager
def writer_lock(root):
    root = Path(root)
    require(not root.is_symlink(), "Ledger root must not be a symlink")
    root.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(root / ".append.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def load_transactions(root):
    directory = Path(root) / "transactions"
    require(not Path(root).is_symlink() and not directory.is_symlink(), "Ledger paths must not be symlinks")
    if Path(root).exists():
        require(all(p.name in ("transactions", ".append.lock") and not p.is_symlink()
                    for p in Path(root).iterdir()), "Unexpected file in ledger root")
    if not directory.exists():
        return []
    entries = sorted(directory.iterdir())
    transactions = []
    for path in entries:
        if path.name.startswith(".pending-"):
            require(not path.is_symlink(), "Pending entry must not be a symlink")
            continue  # May disappear during publication; never part of the accepted chain.
        require(path.is_file() and not path.is_symlink(), "Unexpected ledger entry or symlink")
        require(path.suffix == ".json", "Unexpected transaction filename")
        transaction = strict_json(path.read_bytes())
        require(path.name == transaction_name(transaction), "Transaction filename does not bind content identity")
        transactions.append(transaction)
    return transactions


def publish_transaction(directory, transaction):
    """Hard-link a fully fsynced file into place without overwriting an existing entry."""
    directory.mkdir(parents=True, exist_ok=True)
    require(not directory.is_symlink(), "Transaction directory must not be a symlink")
    descriptor, temporary = tempfile.mkstemp(prefix=".pending-", dir=directory)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(json_bytes(transaction))
            handle.flush()
            os.fsync(handle.fileno())
        target = directory / transaction_name(transaction)
        os.link(temporary, target)  # Atomic visibility, exclusive creation, no replacement.
        directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        os.unlink(temporary)


def append_observation(root, observation, resources, profile, *, expected_revision):
    with writer_lock(root):
        transactions = load_transactions(root)
        state = replay(transactions, profile)
        transaction = prepare_transaction(observation, resources, profile, state,
                                          expected_revision=expected_revision)
        if transaction is None:
            return {"outcome": "duplicate", "transaction_ref": None}
        publish_transaction(Path(root) / "transactions", transaction)
        return {"outcome": transaction["outcome"], "transaction_ref": transaction_ref(transaction)}


def append_action(root, record, resources, profile, *, expected_revision):
    from .decisions import prepare_action_transaction
    with writer_lock(root):
        state = replay(load_transactions(root), profile)
        transaction = prepare_action_transaction(record, resources, profile, state,
                                                  expected_revision=expected_revision)
        if transaction is None:
            return {"outcome": "duplicate", "transaction_ref": None}
        publish_transaction(Path(root) / "transactions", transaction)
        return {"outcome": transaction["outcome"], "transaction_ref": transaction_ref(transaction)}
