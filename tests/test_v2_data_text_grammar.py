"""Compare inert V2 readers with actual frozen original UTF-8 reader functions."""
import ast
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
import shutil

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from lib.functional_parity import V1_REFERENCE, git_read
from lib.report_data import ReportData
from lib.repository_report_operations import OriginalReportData


def frozen_readers(path):
    raw = git_read(ROOT, 'show', V1_REFERENCE+':'+path)
    tree = ast.parse(raw)
    selected = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                and node.name in ('load_json', 'load_yaml')]
    if {node.name for node in selected} != {'load_json', 'load_yaml'}:
        raise AssertionError('Frozen source reader contract changed')
    namespace = {'Path': Path, 'json': json, 'yaml': yaml}
    # Only the two unchanged functions from the fixed trusted V1 object execute;
    # no original module-level program, model scan or native process runs.
    exec(compile(ast.Module(body=selected, type_ignores=[]),
                 'frozen/'+path, 'exec'), namespace)
    return namespace


class DataTextGrammarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_report = frozen_readers('scripts/generate_governance_change_impact_report.py')
        cls.original_repository = frozen_readers('scripts/validate_governance_repo.py')

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()

    def readers(self, suffix, raw):
        path = self.root/('input.'+suffix); path.write_bytes(raw)
        membership = {path.name: {'mode': '100644'}}
        return path, ReportData(self.root, membership), OriginalReportData(self.root, membership)

    def test_complete_literal_unicode_objects_and_newline_conventions_match_original(self):
        for suffix, text in [('json', '{\n"value": "Größe",\n"number": 7\n}\n'),
                             ('yaml', 'value: Größe\nnumber: 7\n')]:
            for newline in ('\n', '\r\n', '\r'):
                with self.subTest(suffix=suffix, newline=repr(newline)):
                    raw = text.replace('\n', newline).encode('utf-8')
                    path, report, repository = self.readers(suffix, raw)
                    expected = self.original_report['load_'+suffix](path)
                    self.assertEqual(getattr(report, suffix)(path), expected)
                    self.assertEqual(getattr(repository, suffix)(path), expected)
                    self.assertEqual(path.read_bytes(), raw)

    def test_all_utf16_and_utf32_variants_retain_original_rejection_and_error_class(self):
        for suffix, text in [('json', '{"value":"Größe"}'), ('yaml', 'value: Größe\n')]:
            for encoding in ('utf-16', 'utf-16-le', 'utf-16-be', 'utf-32', 'utf-32-le', 'utf-32-be'):
                with self.subTest(suffix=suffix, encoding=encoding):
                    path, report, repository = self.readers(suffix, text.encode(encoding))
                    try: self.original_report['load_'+suffix](path)
                    except (UnicodeError, ValueError, yaml.YAMLError) as error:
                        expected_error = type(error)
                    else: self.fail('Fixed original unexpectedly accepts this non-UTF-8 input')
                    for data in (report, repository):
                        with self.assertRaises(expected_error): getattr(data, suffix)(path)

    def test_utf8_bom_keeps_distinct_original_json_and_yaml_rules(self):
        for suffix, text in [('json', '{"value":"Größe"}'), ('yaml', 'value: Größe\n')]:
            path, report, repository = self.readers(suffix, text.encode('utf-8-sig'))
            if suffix == 'json':
                with self.assertRaises(json.JSONDecodeError): self.original_report['load_json'](path)
                for data in (report, repository):
                    with self.assertRaises(json.JSONDecodeError): data.json(path)
            else:
                expected = self.original_report['load_yaml'](path)
                self.assertEqual(report.yaml(path), expected)
                self.assertEqual(repository.yaml(path), expected)

    def test_invalid_utf8_stays_a_decode_error_before_json_or_yaml_can_accept_it(self):
        for suffix, raw in [('json', b'{"value":"\xff"}'), ('yaml', b'value: \xff\n')]:
            path, report, repository = self.readers(suffix, raw)
            for read in (self.original_report['load_'+suffix],
                         getattr(report, suffix), getattr(repository, suffix)):
                with self.assertRaises(UnicodeDecodeError): read(path)

    def test_raw_repository_yaml_keeps_original_null_false_scalar_and_sequence_values(self):
        for text in ('', 'null\n', 'false\n', '0\n', '[]\n', '- Größe\n', 'value: 1\n'):
            with self.subTest(text=text):
                path, report, repository = self.readers('yaml', text.encode('utf-8'))
                raw = OriginalReportData(self.root, {path.name: {'mode': '100644'}}, raw_yaml=True)
                expected = self.original_repository['load_yaml'](path)
                self.assertEqual(raw.yaml(path), expected)
                self.assertEqual(report.yaml(path), self.original_report['load_yaml'](path))
                self.assertEqual(repository.yaml(path), self.original_report['load_yaml'](path))

    def test_existing_strict_report_json_guards_and_original_repository_grammar_are_preserved(self):
        for text in ('{"value":1,"value":2}', '{"value":NaN}', '[1,2]', 'null'):
            with self.subTest(text=text):
                path, report, repository = self.readers('json', text.encode('utf-8'))
                expected = self.original_repository['load_json'](path)
                self.assertEqual(json.dumps(repository.json(path), sort_keys=True),
                                 json.dumps(expected, sort_keys=True))
                with self.assertRaises(ValueError): report.json(path)

    @unittest.skipUnless(shutil.which('git'), 'Local Git required for real captured-memory dataset')
    def test_real_captured_memory_report_reader_keeps_the_same_original_text_grammar(self):
        import test_v2_repository_capture as fixture_module
        from lib.repository_dataset import RepositoryDataset
        from lib.repository_report_data import RepositoryReportData
        fixture = fixture_module.RepositoryCaptureTests(methodName='runTest')
        fixture.setUp(); self.addCleanup(fixture.doCleanups)
        inputs = {}
        for encoding in ('utf-8', 'utf-8-sig', 'utf-16', 'utf-16-le', 'utf-16-be',
                         'utf-32', 'utf-32-le', 'utf-32-be'):
            inputs['model/encoding-'+encoding+'.yaml'] = 'value: Größe\n'.encode(encoding)
        inputs.update({'model/empty.yaml': b'', 'model/false.yaml': b'false\n',
                       'model/list.yaml': b'- value\n'})
        for name, raw in inputs.items(): (fixture.source/name).write_bytes(raw)
        fixture.commit()
        manifest, files, commit = fixture.capture()
        effects = []
        dataset = RepositoryDataset(manifest, files, commit, append_effect=effects.append)
        for raw_yaml, original in ((False, self.original_report), (True, self.original_repository)):
            reader = RepositoryReportData(dataset, raw_yaml=raw_yaml)
            for name, raw in inputs.items():
                with self.subTest(raw_yaml=raw_yaml, name=name):
                    try: expected = original['load_yaml'](fixture.source/name)
                    except (UnicodeError, ValueError, yaml.YAMLError) as error:
                        with self.assertRaises(type(error)): reader.yaml(dataset.root/name)
                    else: self.assertEqual(reader.yaml(dataset.root/name), expected)
                    self.assertEqual((fixture.source/name).read_bytes(), raw)
        self.assertEqual(effects, [])


if __name__ == '__main__': unittest.main()
