"""Native stable alias observations preserve the original leftover pair only."""
from pathlib import Path
from types import SimpleNamespace
import hashlib, json, os, sys, tempfile, unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts')]
from lib.providers.synthetic_ledger_files import LedgerFiles
from lib.requirement_validation_budget import InputAdmissionError
from lib.repository_lifecycle.context import RepositoryLifecycle


class LedgerFilesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.ledger = self.root / 'ledger'
        self.transactions = self.ledger / 'transactions'
        self.transactions.mkdir(parents=True, mode=0o700)
        self.blobs = {}
        context = RepositoryLifecycle(ROOT, validator_class=None)
        self.context = context
        self.raw = next((ROOT / 'governance/lifecycle/synthetic-closure/transactions').glob('*.json')).read_bytes()
        self.name = context.kernel.transaction_name(context.adapter.strict_json(self.raw))
        self.accepted = self.transactions / self.name
        self.accepted.write_bytes(self.raw)
        self.accepted.chmod(0o600)
        self.owner = SimpleNamespace(check=lambda path, label: None, blob=self.blob)
        self.files = LedgerFiles(self.owner, self.ledger, transaction_name=lambda raw:
            context.kernel.transaction_name(context.adapter.strict_json(raw)))

    def blob(self, raw):
        ref = {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
        self.blobs[ref['sha256']] = raw
        return ref

    def pair(self):
        pending = self.transactions / '.pending-kept-original'
        os.link(self.accepted, pending)
        return pending

    def test_single_link_bytes_mode_identity_and_metadata_are_observed(self):
        raw, row = self.files.read(str(self.accepted), str(self.accepted))
        self.assertEqual(raw, self.raw)
        self.assertEqual(row['aliases'], [])
        self.assertEqual(row['metadata']['nlink'], 1)
        self.assertEqual(row['snapshot']['mode'], 0o600)
        self.assertEqual(self.blobs[row['snapshot']['content']['sha256']], self.raw)
        info = self.accepted.stat()
        self.assertEqual(row['snapshot']['identity'], [info.st_dev, info.st_ino])

    def test_both_pending_and_canonical_name_bind_the_same_stable_whole_transaction(self):
        pending = self.pair()
        a, left = self.files.read(str(self.accepted), str(self.accepted))
        b, right = self.files.read(str(pending), str(pending))
        self.assertEqual(a, self.raw)
        self.assertEqual(a, b)
        self.assertEqual(left, right)
        self.assertEqual(left['aliases'], sorted([str(self.accepted), str(pending)]))
        self.assertEqual(left['metadata']['nlink'], 2)
        # The complete unchanged store reader accepts this history and ignores
        # only the pending name; alias admission never grants new authority.
        observed = self.context.store.load_transactions(self.ledger)
        self.assertEqual(observed, [self.context.adapter.strict_json(self.raw)])

    def test_an_external_second_alias_is_rejected_even_with_identical_content(self):
        os.link(self.accepted, self.root / 'outside-ledger.json')
        with self.assertRaisesRegex(InputAdmissionError, 'unknown_or_external_alias'):
            self.files.read(str(self.accepted), str(self.accepted))

    def test_a_third_external_alias_is_rejected_even_when_the_expected_pair_exists(self):
        self.pair()
        os.link(self.accepted, self.root / 'outside-ledger.json')
        with self.assertRaisesRegex(InputAdmissionError, 'regular_bounded_file'):
            self.files.read(str(self.accepted), str(self.accepted))

    def test_two_canonical_or_two_pending_names_are_rejected(self):
        for pending in (False, True):
            with self.subTest(pending=pending):
                source = self.accepted
                other = self.transactions / ('other.json' if not pending else '.pending-two')
                if pending:
                    source.rename(self.transactions / '.pending-one')
                    source = self.transactions / '.pending-one'
                os.link(source, other)
                try:
                    with self.assertRaisesRegex(InputAdmissionError, 'only_pending_canonical_pair'):
                        self.files.read(str(source), str(source))
                finally:
                    other.unlink()
                    if pending: source.rename(self.accepted)

    def test_pair_outside_the_selected_transactions_directory_is_rejected(self):
        other = self.root / 'other'
        other.mkdir(mode=0o700)
        canonical = other / self.name
        self.accepted.rename(canonical)
        os.link(canonical, other / '.pending-other')
        with self.assertRaisesRegex(InputAdmissionError, 'outside_transaction_directory'):
            self.files.read(str(canonical), str(canonical))

    def test_canonical_name_must_bind_the_whole_original_transaction_identity(self):
        self.pair()
        self.accepted.rename(self.transactions / 'wrong.json')
        with self.assertRaisesRegex(InputAdmissionError, 'canonical_name_unbound'):
            self.files.read(str(self.transactions / 'wrong.json'), 'wrong.json')

    def test_symlink_shared_write_mode_and_parent_shared_write_mode_are_not_admitted(self):
        alias = self.transactions / 'symbolic.json'
        alias.symlink_to(self.accepted)
        with self.assertRaisesRegex(InputAdmissionError, 'regular_bounded_file'):
            self.files.read(str(alias), str(alias))
        alias.unlink()
        self.accepted.chmod(0o620)
        with self.assertRaisesRegex(InputAdmissionError, 'owned_unshared_file'):
            self.files.read(str(self.accepted), str(self.accepted))
        self.accepted.chmod(0o600)
        self.transactions.chmod(0o720)
        try:
            with self.assertRaisesRegex(InputAdmissionError, 'owned_unshared_parent'):
                self.files.read(str(self.accepted), str(self.accepted))
        finally: self.transactions.chmod(0o700)

    def test_alias_replacement_during_membership_capture_is_not_silently_accepted(self):
        pending = self.pair()
        real = self.files.members
        calls = []
        def replace(parent):
            names = real(parent)
            calls.append(1)
            if len(calls) == 1:
                pending.unlink()
                pending.write_bytes(self.raw)
                pending.chmod(0o600)
            return names
        with patch.object(self.files, 'members', side_effect=replace):
            with self.assertRaises(InputAdmissionError):
                self.files.read(str(self.accepted), str(self.accepted))

    def test_selected_file_replacement_between_stat_and_open_is_rejected(self):
        real = os.open
        called = []
        def replace(path, *args, **kwargs):
            if path == self.accepted.name and not called:
                called.append(1)
                replacement = self.transactions / 'replacement'
                replacement.write_bytes(self.raw)
                replacement.chmod(0o600)
                os.replace(replacement, self.accepted)
            return real(path, *args, **kwargs)
        with patch('lib.providers.synthetic_ledger_files.os.open', side_effect=replace):
            with self.assertRaisesRegex(InputAdmissionError, 'replaced_before_read'):
                self.files.read(str(self.accepted), str(self.accepted))


if __name__ == '__main__': unittest.main()
