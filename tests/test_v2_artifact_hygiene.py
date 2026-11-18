"""Complete real original wires, Office decoding and explicit new resource guards."""
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import os
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import patch
import warnings
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from lib import artifact_hygiene as core
from lib import artifact_hygiene_application as application
from lib.providers import artifact_hygiene as adapter
import axiom_v2


class ArtifactHygieneTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        original = ROOT/'scripts/check_public_artifact_hygiene.py'
        self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(),
                         '1b1e08f31533374d3fe4ba9b3ad9ca7ae478dfe7e2843eb009074e5525ebe53a')
        # Only the test oracle executes the unchanged frozen original.
        self.original = runpy.run_path(str(original))

    def file(self, name, data):
        path = self.root/name
        path.write_bytes(data)
        return path

    def office(self, name, members):
        path = self.root/name
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with ZipFile(path, 'w') as archive:
                for member, raw in members:
                    archive.writestr(member, raw)
        return path

    def wires(self, paths, terms=(), environment='', product=False):
        args = [str(path) for path in paths]
        for term in terms:
            args.extend(['--forbidden-term', term])
        out, err = io.StringIO(), io.StringIO()
        with patch.dict(os.environ, {adapter.ENVIRONMENT: environment}), redirect_stdout(out), redirect_stderr(err):
            if product:
                code = application.run(['check', '--profile', application.PROFILE, *args], self.root, {})
            else:
                with patch.object(sys, 'argv', ['original', *args]):
                    try:
                        code = self.original['main']()
                    except SystemExit as error:
                        if not isinstance(error.code, str):
                            raise
                        err.write(error.code+'\n')
                        code = 1
        return code, out.getvalue(), err.getvalue()

    def equal_original(self, paths, terms=(), environment=''):
        expected = self.wires(paths, terms, environment)
        self.assertEqual(self.wires(paths, terms, environment, True), expected)
        return expected

    def test_clean_text_and_original_path_count_includes_missing_directories_duplicates(self):
        clean = self.file('clean.txt', b'public text')
        code, out, err = self.equal_original([clean, self.root/'missing', self.root, clean], ['private'])
        self.assertEqual((code, out, err), (0, 'Public artifact hygiene passed for 4 paths\n', ''))

    def test_ordered_findings_and_duplicate_paths_are_preserved(self):
        a = self.file('a.txt', b'SECRET')
        b = self.file('b.txt', b'secret')
        self.assertEqual(self.equal_original([b, a, b], ['secret'])[1].splitlines()[1:],
                         [f'- {b}', f'- {a}', f'- {b}'])

    def test_unicode_casefold_env_trimming_and_literal_cli_whitespace(self):
        source = self.file('text.txt', 'Straße\nterm'.encode())
        for terms, environment in [(['STRASSE'], ''), ([], ' , STRASSE , ,'), ([' term '], ''), ([''], 'term')]:
            with self.subTest(terms=terms, environment=environment):
                self.equal_original([source], terms, environment)

    def test_plain_invalid_utf8_is_ignored_and_newlines_are_universal(self):
        source = self.file('text.txt', b'a\r\nb\rc\xffd')
        for term in ['a\nb', 'b\nc', 'cd', 'c\ufffdd']:
            with self.subTest(term=term):
                self.equal_original([source], [term])

    def test_all_office_extensions_preserve_members_order_and_binary_skip(self):
        for extension in ['docx', 'xlsx', 'pptx', 'DOCX']:
            with self.subTest(extension=extension):
                source = self.office('office.'+extension, [('z.xml', b'SECRET'), ('binary', b'\xffSECRET'), ('a.xml', b'secret')])
                self.assertEqual(self.equal_original([source], ['secret'])[1].splitlines()[1:],
                                 [f'- {source}:z.xml', f'- {source}:a.xml'])

    def test_office_member_newlines_are_not_universal(self):
        source = self.office('office.docx', [('x', b'a\r\nb\rc')])
        for term in ['a\nb', 'a\r\nb', 'b\rc']:
            with self.subTest(term=term):
                self.equal_original([source], [term])

    def test_duplicate_office_names_select_last_entry_each_time(self):
        source = self.office('duplicates.docx', [('same.xml', b'clean'), ('same.xml', b'secret')])
        self.assertEqual(self.equal_original([source], ['secret'])[1].count(f'- {source}:same.xml\n'), 2)

    def test_invalid_office_zip_falls_back_to_plain_text(self):
        source = self.file('broken.pptx', b'SECRET\r\nnext\xff')
        self.equal_original([source], ['secret\nnext'])

    def test_crc_failure_retains_earlier_members_then_falls_back(self):
        source = self.office('crc.docx', [('first', b'secret FIRST'), ('last', b'secret LAST')])
        raw = source.read_bytes().replace(b'secret LAST', b'secret FAIL')
        source.write_bytes(raw)
        out = self.equal_original([source], ['secret'])[1]
        self.assertIn(f'- {source}:first\n- {source}\n', out)

    def test_no_terms_returns_original_error_before_any_path_read(self):
        with patch.object(application, 'artifact_hygiene_capture', side_effect=AssertionError('must not acquire')):
            self.assertEqual(self.equal_original([self.root/'missing']), (1, '', 'No forbidden terms configured\n'))

    def test_non_office_zip_is_plain_file_as_in_original(self):
        source = self.office('archive.zip', [('x', b'secret')])
        self.equal_original([source], ['secret'])

    def test_product_resource_rejections_are_separate_from_original_results(self):
        source = self.file('text.txt', b'longer than budget')
        with patch.object(adapter, 'MAX_FILE', 4), self.assertRaises(ValueError):
            adapter.capture([source])
        with patch.object(adapter, 'MAX_PATHS', 1), self.assertRaisesRegex(ValueError, 'path_budget'):
            adapter.capture([source, source])
        with self.assertRaisesRegex(ValueError, 'matching_budget'):
            core.assess(1, [('x', 'a'*270000)], ['b']*1024)
        with patch.object(adapter, 'MAX_TOTAL', 4), self.assertRaises(ValueError):
            adapter.capture([source])

    def test_office_expansion_member_count_and_location_guards(self):
        source = self.office('office.docx', [('a', b'x'*40), ('b', b'x')])
        with patch.object(adapter, 'MAX_MEMBERS', 1), self.assertRaisesRegex(ValueError, 'member_budget'):
            adapter.capture([source])
        with patch.object(adapter, 'MAX_TOTAL', source.stat().st_size+10), self.assertRaisesRegex(ValueError, 'zip_byte_budget'):
            adapter.capture([source])
        source = self.office('names.docx', [('unsafe\nname', b'secret')])
        with self.assertRaisesRegex(ValueError, 'member_label'):
            adapter.capture([source])

    def test_links_nonregular_sources_and_unsafe_labels_rejected_without_reads(self):
        source = self.file('source', b'secret')
        link = self.root/'link'
        link.symlink_to(source)
        with self.assertRaisesRegex(ValueError, 'symlink'):
            adapter.capture([link])
        fifo = self.root/'fifo'
        os.mkfifo(fifo)
        with self.assertRaises(ValueError):
            adapter.capture([fifo])
        with self.assertRaisesRegex(ValueError, 'path_label'):
            adapter.capture([self.root/'unsafe\nlabel'])

    def test_encrypted_member_is_an_explicit_product_error(self):
        source = self.office('encrypted.docx', [('x', b'secret')])
        raw = bytearray(source.read_bytes())
        # Real ZIP flags, not a mocked decompressor or manufactured successful result.
        raw[6] |= 1
        central = raw.index(b'PK\x01\x02')
        raw[central+8] |= 1
        source.write_bytes(raw)
        with self.assertRaises(RuntimeError):
            list(self.original['file_texts'](source))
        with self.assertRaisesRegex(ValueError, 'unsupported_zip_member'):
            adapter.capture([source])

    def test_term_budget_precedes_acquisition(self):
        with patch.object(application, 'artifact_hygiene_capture', side_effect=AssertionError('must not acquire')):
            with self.assertRaisesRegex(ValueError, 'term_budget'):
                self.wires([self.root/'missing'], ['x'*4097], product=True)
            with self.assertRaisesRegex(ValueError, 'term_budget'):
                self.wires([self.root/'missing'], environment=','.join(['x']*1025), product=True)

    def test_public_command_routes_and_preserves_whole_original_wire(self):
        source = self.file('text.txt', b'SECRET')
        before = source.read_bytes()
        out, err = io.StringIO(), io.StringIO()
        # Admission is independently covered by instance tests; exercise the real CLI/router.
        with patch('lib.v2_application.instance', return_value=(self.root, {})), patch.dict(os.environ, {adapter.ENVIRONMENT: ''}), redirect_stdout(out), redirect_stderr(err):
            code = axiom_v2.main(['--instance', str(self.root), 'artifact-hygiene', 'check', '--profile', application.PROFILE, str(source), '--forbidden-term', 'secret'])
        self.assertEqual((code, out.getvalue(), err.getvalue()), self.wires([source], ['secret']))
        self.assertEqual(source.read_bytes(), before)
        self.assertEqual(set(p.name for p in self.root.iterdir()), {'text.txt'})


if __name__ == '__main__':
    unittest.main()
