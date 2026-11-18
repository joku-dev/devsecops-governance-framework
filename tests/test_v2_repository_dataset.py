"""Captured-path execution, complete effect bytes and original parser behavior."""
import base64
from contextlib import redirect_stdout
import copy
import errno
import io
import json
import os
from pathlib import Path
import shutil
import sys
import unittest
from types import MethodType
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.repository_dataset import RepositoryDataset
from lib.repository_report_data import RepositoryReportData
from lib.source_document_text import extract_source_document, extract_source_document_bytes, SourceDocumentExtractionError
from lib import repository_capture as contract
from lib.v2_boundary import violations


@unittest.skipUnless(shutil.which('git'), 'local Git not present')
class RepositoryDatasetTests(unittest.TestCase):
    def setUp(self):
        import test_v2_repository_capture as fixture
        for name in ('command', 'commit', 'journal', 'port', 'capture'):
            setattr(self, name, MethodType(getattr(fixture.RepositoryCaptureTests, name), self))
        fixture.RepositoryCaptureTests.setUp(self)
        (self.source / 'generated').mkdir()
        (self.source / 'generated/existing.json').write_bytes(b'{}\n')
        (self.source / 'generated/file-parent').write_bytes(b'not a directory')
        self.commit()
        self.manifest, self.files, self.raw_commit = self.capture()
        self.effects = []
        self.dataset = self.new()

    def new(self, **options):
        return RepositoryDataset(self.manifest, self.files, self.raw_commit,
            append_effect=options.get('append_effect', lambda value:self.effects.append(copy.deepcopy(value))))

    @staticmethod
    def outcome(callback):
        try: return {'result': callback()}
        except OSError as error: return {'type':type(error).__name__, 'errno':error.errno, 'filename':error.filename}

    def test_complete_dataset_bytes_modes_and_paths_match_the_capture(self):
        self.assertEqual(self.dataset.files, self.files)
        self.assertEqual(self.dataset.directories, self.manifest['directories'])
        for name, raw in self.files.items():
            self.assertEqual((self.dataset.root / name).read_bytes(), raw)
            self.assertTrue((self.dataset.root / name).is_file())
            self.assertFalse((self.dataset.root / name).is_symlink())
        self.assertEqual([p.name for p in self.dataset.root.iterdir()], self.manifest['directories'][''])

    def test_whole_retained_reads_and_markdown_extraction_work_after_source_deletion(self):
        expected = extract_source_document(self.source / 'README.md')
        shutil.rmtree(self.source)
        with patch('os.open', side_effect=AssertionError('no caller files may reopen')):
            for name, raw in self.files.items(): self.assertEqual((self.dataset.root / name).read_bytes(), raw)
            data = RepositoryReportData(self.dataset)
            self.assertEqual(data.extract(data.root / 'README.md'), expected)
            self.assertEqual(data.json(data.root / 'model/catalog.json'), {'version':1})

    def test_failed_reads_retain_native_errno_and_original_display_paths(self):
        for name in ('model/missing.json', 'model/catalog.json/child', 'model'):
            self.assertEqual(self.outcome(lambda:(self.dataset.root/name).read_bytes()),
                             self.outcome(lambda:(self.source/name).read_bytes()))

    def test_mkdir_write_content_and_new_directory_order_are_journaled_before_effects(self):
        before = dict(self.dataset.files)
        def record(row):
            if row['phase'] == 'intent' and row['effect']['operation'] == 'write-bytes':
                self.assertNotIn(row['effect']['path'], self.dataset.files)
            self.effects.append(copy.deepcopy(row))
        self.dataset.append_effect = record
        self.dataset.mkdir('generated/reports')
        self.dataset.write('generated/reports/new.json', b'{"new":true}\n')
        self.assertEqual((self.dataset.root/'generated/reports/new.json').read_bytes(), b'{"new":true}\n')
        self.assertEqual([r['phase'] for r in self.effects], ['intent','completed','content','intent','completed'])
        payload = self.effects[2]
        self.assertEqual(base64.b64decode(payload['base64']), b'{"new":true}\n')
        self.assertEqual(self.dataset.directories['generated'], ['existing.json','file-parent','reports'])
        self.assertEqual(self.dataset.files.keys() - before.keys(), {'generated/reports/new.json'})
        self.assertFalse((self.source/'generated/reports').exists())

    def test_content_is_retained_once_and_output_overwrites_keep_file_order(self):
        self.dataset.write('generated/existing.json', b'new')
        self.dataset.write('generated/other.json', b'new')
        self.assertEqual(sum(row['phase']=='content' for row in self.effects),1)
        self.assertEqual(self.dataset.directories['generated'], ['existing.json','file-parent','other.json'])
        self.assertEqual(self.dataset.contents[self.effects[0]['sha256']], b'new')

    def test_mkdir_and_write_errors_keep_native_type_errno_and_target_path(self):
        cases = [
            ('mkdir', 'generated/file-parent', {}),
            ('mkdir', 'generated/file-parent/child', {'parents':True,'exist_ok':True}),
            ('mkdir', 'generated/missing/child', {'parents':False,'exist_ok':True}),
            ('mkdir', 'generated', {'parents':True,'exist_ok':False}),
            ('write', 'generated/missing/child', {}),
            ('write', 'generated/file-parent/child', {}),
            ('write', 'generated', {})]
        for operation,name,options in cases:
            with self.subTest(operation=operation,name=name):
                if operation=='mkdir':
                    actual=self.outcome(lambda:self.dataset.mkdir(name,**options))
                    expected=self.outcome(lambda:(self.source/name).mkdir(**options))
                else:
                    actual=self.outcome(lambda:self.dataset.write(name,b'new'))
                    expected=self.outcome(lambda:(self.source/name).write_bytes(b'new'))
                self.assertEqual(actual,expected)
                self.assertEqual(self.effects[-1]['phase'],'incomplete')

    def test_mkdir_recursive_creates_only_the_original_missing_parent_chain(self):
        self.dataset.mkdir('generated/one/two', parents=True)
        self.assertEqual(self.effects[-1]['result']['directories_created'], ['generated/one','generated/one/two'])
        self.assertEqual(self.dataset.directories['generated/one'], ['two'])
        self.assertEqual(self.dataset.directories['generated/one/two'], [])

    def test_model_baseline_official_status_and_private_input_paths_are_not_output_scopes(self):
        for name in ('model/new.json','status/latest.json','releases/package.json','../outside','generated/.env'):
            with self.assertRaises(ValueError): self.dataset.write(name,b'new')
        self.assertEqual(self.effects,[])
        for name in ('.git/config','.aws/credentials','unknown/input.json'):
            with self.assertRaisesRegex(ValueError,'outside_capture_scope'): self.dataset.stat(name)

    def test_input_scope_errors_are_visible_and_never_silently_missing_findings(self):
        data=RepositoryReportData(self.dataset)
        for action in (data.raw,data.is_file,data.exists):
            with self.assertRaisesRegex(ValueError,'outside_capture_scope'): action(data.root/'.git/config')

    def test_intent_failure_prevents_mutation_and_finish_failure_stays_incomplete(self):
        def fail_intent(row):
            if row['phase']=='intent': raise OSError('controlled intent failure')
        dataset=self.new(append_effect=fail_intent)
        with self.assertRaisesRegex(OSError,'controlled intent'): dataset.write('generated/existing.json',b'new')
        self.assertEqual(dataset.files['generated/existing.json'],b'{}\n')
        def fail_finish(row):
            if row['phase']=='completed':raise OSError('controlled completion failure')
        dataset=self.new(append_effect=fail_finish)
        with self.assertRaisesRegex(OSError,'controlled completion'):dataset.write('generated/existing.json',b'new')
        self.assertEqual(dataset.files['generated/existing.json'],b'new')
        self.assertIn(b'new',dataset.contents.values())

    def test_transport_dictionary_order_cannot_change_the_captured_file_traversal(self):
        original=list(self.dataset.files)
        reordered=dict(reversed(list(self.files.items())))
        dataset=RepositoryDataset(self.manifest,reordered,self.raw_commit,append_effect=lambda row:None)
        self.assertEqual(list(dataset.files),original)

    def test_capture_is_copied_and_later_caller_dictionary_changes_cannot_replace_it(self):
        self.files['README.md']=b'forged'
        self.manifest['directories'][''].clear()
        self.assertEqual((self.dataset.root/'README.md').read_bytes(),b'# Controlled data\n')
        self.assertTrue(self.dataset.directories[''])

    def test_original_json_and_yaml_grammars_are_not_silently_strengthened(self):
        self.dataset.write('generated/existing.json', b'{"duplicate":1,"duplicate":2,"n":NaN}')
        data=RepositoryReportData(self.dataset)
        value=data.json(data.root/'generated/existing.json')
        self.assertEqual(value['duplicate'],2)
        self.assertNotEqual(value['n'],value['n'])
        self.dataset.write('generated/empty.yaml',b'')
        self.assertEqual(RepositoryReportData(self.dataset).yaml(self.dataset.root/'generated/empty.yaml'),{})
        self.assertIsNone(RepositoryReportData(self.dataset,raw_yaml=True).yaml(self.dataset.root/'generated/empty.yaml'))

    def test_report_membership_refreshes_at_each_new_data_context(self):
        data=RepositoryReportData(self.dataset)
        self.dataset.write('generated/new.json',b'{}')
        self.assertNotIn('generated/new.json',data.files)
        current=RepositoryReportData(self.dataset)
        self.assertIn('generated/new.json',current.files)
        self.assertEqual([p.name for p in current.glob(current.root/'generated','*.json')],['existing.json','new.json'])

    def test_dataset_and_report_data_are_neutral_with_no_native_provider_import(self):
        for name in ('scripts/lib/repository_dataset.py','scripts/lib/repository_report_data.py'):
            self.assertEqual(violations(name,(ROOT/name).read_text()),[])


class RetainedDocumentBytesTests(unittest.TestCase):
    def test_original_markdown_lines_unicode_crlf_and_invalid_encoding_are_preserved(self):
        import tempfile
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'source.md'
            for raw in (b'# Title\r\n\r\nLine\r\n', 'Änderung\nAnforderung\n'.encode()):
                path.write_bytes(raw)
                self.assertEqual(extract_source_document_bytes(path.name,raw),extract_source_document(path))
            with self.assertRaisesRegex(SourceDocumentExtractionError,'not valid UTF-8'):
                extract_source_document_bytes('source.md',b'\xff')

    def test_original_docx_paragraph_table_and_tracking_warning_results_are_preserved(self):
        import tempfile
        xml=b'''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Text</w:t></w:r><w:ins><w:r><w:t>changed</w:t></w:r></w:ins></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>Table value</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>'''
        raw=io.BytesIO()
        with zipfile.ZipFile(raw,'w') as archive:
            archive.writestr('word/document.xml',xml);archive.writestr('word/comments.xml','<comments/>')
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'source.docx';path.write_bytes(raw.getvalue())
            self.assertEqual(extract_source_document_bytes('source.docx',raw.getvalue()),extract_source_document(path))
            self.assertIn('docx_tracked_changes_present_review_required',extract_source_document(path).warnings)
            self.assertTrue(any(line.locator.startswith('table:') for line in extract_source_document(path).lines))
        with self.assertRaises(SourceDocumentExtractionError):extract_source_document_bytes('source.docx',b'not a zip')
        with self.assertRaisesRegex(SourceDocumentExtractionError,'unsupported source document format'):
            extract_source_document_bytes('source.bin',b'data')


    def test_retained_pdf_has_the_original_page_and_ocr_gap_warnings(self):
        import importlib.util,tempfile
        if importlib.util.find_spec('pypdf') is None:self.skipTest('optional pypdf is not installed')
        from pypdf import PdfWriter
        raw=io.BytesIO();writer=PdfWriter();writer.add_blank_page(width=72,height=72);writer.write(raw)
        with tempfile.TemporaryDirectory() as temporary:
            path=Path(temporary)/'source.pdf';path.write_bytes(raw.getvalue())
            expected=extract_source_document(path)
            self.assertEqual(extract_source_document_bytes('source.pdf',raw.getvalue()),expected)
            self.assertIn('pdf_contains_no_extractable_text',expected.warnings)


if __name__=='__main__':unittest.main()
