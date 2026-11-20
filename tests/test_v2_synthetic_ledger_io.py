"""Real leftover-pair IO becomes a closed replay after selected data deletion."""
from pathlib import Path
import copy, json, os, shutil, sys, tempfile, unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts')]
from lib.providers.synthetic_ledger_io import NativeIO
from lib.providers.synthetic_lifecycle_storage import Record, read_record
from lib.synthetic_ledger_io import ReplayIO
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.requirement_validation_replay import IntegrityError


class LedgerIOTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.data = self.root / 'data'
        self.data.mkdir(mode=0o700)
        self.ledger = self.data / 'ledger'
        self.transactions = self.ledger / 'transactions'
        self.transactions.mkdir(parents=True, mode=0o700)
        self.private = self.root / 'private'
        self.private.mkdir(mode=0o700)
        ctx = RepositoryLifecycle(ROOT, validator_class=None)
        self.name_of = lambda raw: ctx.kernel.transaction_name(ctx.adapter.strict_json(raw))
        self.raw = next((ROOT / 'governance/lifecycle/synthetic-closure/transactions').glob('*.json')).read_bytes()
        self.accepted = self.transactions / self.name_of(self.raw)
        self.accepted.write_bytes(self.raw)
        self.accepted.chmod(0o600)
        self.pending = self.transactions / '.pending-kept'
        os.link(self.accepted, self.pending)
        self.record = Record(self.private / 'records', {'ledger': str(self.ledger)}, {'prototype': True})
        self.record.append({'kind': 'execution-intent'})
        self.io = NativeIO(self.record, mode='selected-files', cwd=str(self.data), private_state=self.private,
            product_root=ROOT, ledger=str(self.ledger), transaction_name=self.name_of)

    def finish(self):
        self.record.finish('complete', {'exit_code': 0}, {})
        request, source, result, events, blob, closed = read_record(self.record.root)
        return events, blob, closed

    def replay(self, events, blob, ledger=None):
        return ReplayIO(events, blob, 'selected-files', str(self.data),
            ledger=str(self.ledger) if ledger is None else ledger, transaction_name=self.name_of)

    def test_pair_reads_and_probes_replay_without_selected_files_network_or_programs(self):
        accepted, pending = str(self.accepted), str(self.pending)
        self.assertTrue(self.io.probe(accepted, 'is_file', accepted))
        self.assertEqual(self.io.read(accepted, accepted), self.raw)
        self.assertFalse(self.io.probe(pending, 'is_symlink', pending))
        self.assertFalse(self.io.probe(str(self.transactions / 'missing'), 'exists', str(self.transactions / 'missing')))
        events, blob, closed = self.finish()
        shutil.rmtree(self.data)
        replay = self.replay(events, blob)
        with patch('subprocess.Popen', side_effect=AssertionError('No programs')), patch('socket.create_connection', side_effect=AssertionError('No network')):
            self.assertTrue(replay.probe(accepted, 'is_file', accepted))
            self.assertEqual(replay.read(accepted, accepted), self.raw)
            self.assertFalse(replay.probe(pending, 'is_symlink', pending))
            self.assertFalse(replay.probe(str(self.transactions / 'missing'), 'exists', str(self.transactions / 'missing')))
        replay.finish()
        self.assertTrue(closed())
        self.assertFalse(self.data.exists())

    def test_resealed_alias_or_inode_byte_count_link_count_claims_are_rejected(self):
        name = str(self.accepted)
        self.io.read(name, name)
        events, blob, _ = self.finish()
        for change in ('outside', 'third', 'identity', 'bytes', 'link-count'):
            with self.subTest(change=change):
                modified = copy.deepcopy(events)
                row = next(row for row in modified if row['kind'] == 'synthetic-ledger-read-after')['observation']
                if change == 'outside': row['aliases'][0] = str(self.data / 'outside')
                elif change == 'third': row['aliases'].append(str(self.transactions / 'third'))
                elif change == 'identity': row['metadata']['identity'][1] += 1
                elif change == 'bytes': row['metadata']['bytes'] += 1
                else: row['metadata']['nlink'] = 1
                with self.assertRaises(IntegrityError): self.replay(modified, blob).read(name, name)

    def test_wrong_ledger_context_cannot_reinterpret_a_pair_as_an_ordinary_source_file(self):
        name = str(self.accepted)
        self.io.read(name, name)
        events, blob, _ = self.finish()
        with self.assertRaises(IntegrityError): self.replay(events, blob, str(self.data / 'other')).read(name, name)

    def test_original_missing_file_error_label_is_retained_without_native_retry(self):
        name, label = str(self.transactions / 'missing'), 'ledger/transactions/missing'
        with self.assertRaises(FileNotFoundError) as original: Path(name).read_bytes()
        with self.assertRaises(FileNotFoundError) as actual: self.io.read(name, label)
        self.assertEqual(actual.exception.filename, label)
        events, blob, closed = self.finish()
        shutil.rmtree(self.data)
        replay = self.replay(events, blob)
        with self.assertRaises(FileNotFoundError) as retained: replay.read(name, label)
        self.assertEqual(str(retained.exception), str(actual.exception))
        replay.finish()
        self.assertTrue(closed())


if __name__ == '__main__': unittest.main()
