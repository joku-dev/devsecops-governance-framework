"""Original parser behavior is retained without an eager ledger selection."""
from pathlib import Path
from types import SimpleNamespace
import sys, tempfile, unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'scripts')]
from lib.synthetic_ledger_execution import execute
from lib.synthetic_ledger_context import PROGRAMS
from lib.synthetic_lifecycle_application import closed_validator


class LedgerExecutionTests(unittest.TestCase):
    def test_all_six_help_and_parser_errors_need_no_selected_source_or_port_binding(self):
        for name in PROGRAMS:
            for args, code in ((['--help'], 0), (['--unknown'], 2), ([], 2)):
                with self.subTest(program=name, argv=args):
                    def forbidden(binding): raise AssertionError('No ports before successful original parsing')
                    with (patch('os.open', side_effect=AssertionError('No filesystem')),
                          patch('pathlib.Path.read_bytes', side_effect=AssertionError('No source data'))):
                        value = execute('/missing-source', '/missing-source', name, args,
                            port_factory=forbidden, validator_factory=lambda io: closed_validator(io, {'resources': []}))
                    self.assertEqual(value['kernel_result']['exit_code'], code)
                    self.assertEqual(value['kernel_result']['original_exit_signal'], {'type': 'SystemExit', 'value': code})
                    self.assertIsNone(value['binding'])
                    self.assertIsNone(value['effects'])
                    self.assertEqual(value['io'].files, {})
                    if code == 0: self.assertIn(PROGRAMS[name][0], value['kernel_result']['stdout'])

    def test_original_abbreviation_equals_and_last_ledger_options_bind_normalized_unicode_context(self):
        for args, path, label in ((['--led', 'first', '--output', 'index.json'], '/source/first', 'first'),
            (['--ledger=first', '--ledger', '../Ü ledger', '--output=index.json'], '/Ü ledger', '../Ü ledger')):
            with self.subTest(argv=args):
                bindings, reads = [], []
                class Inputs:
                    files, writes, touched, projected_changes = {}, [], {}, {}
                    def probe(self, *args): return False
                    def read(self, path, label):
                        reads.append(path)
                        raise FileNotFoundError(2, 'No such file or directory', label)
                def factory(value):
                    bindings.append(value)
                    return Inputs(), SimpleNamespace()
                value = execute('/source', '/source', 'synthetic', args, port_factory=factory,
                    validator_factory=lambda io: closed_validator(io, {'resources': []}))
                self.assertEqual(bindings, [{'path': path, 'label': label}])
                self.assertEqual(value['binding'], bindings[0])
                self.assertEqual(value['kernel_result']['exit_code'], 1)
                self.assertEqual(value['kernel_result']['kernel_exception']['type'], 'FileNotFoundError')
                self.assertTrue(reads)


if __name__ == '__main__': unittest.main()
