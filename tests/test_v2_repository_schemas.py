"""Offline schema closure, lazy parsing and bounded historical contracts."""
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator, ValidationError
from referencing import Registry

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from lib.repository_schemas import RepositorySchemas
from lib.repository_lifecycle.context import RepositoryLifecycle
from lib.providers.repository_lifecycle_capture import LegacyRepositoryLifecycleCapture
from lib.providers.repository_data_io import RepositoryDataIO
from lib.repository_paths import RepositoryPaths
from lib import dcr_operations

BASE = 'https://joku-dev.github.io/devsecops-governance-framework/schemas/'


class RepositorySchemaTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve() / 'data'
        self.root.mkdir(mode=0o700)
        for name in ('model', 'schemas', 'tests', 'docs', 'status', 'governance', 'generated', 'scripts', '.github'):
            shutil.copytree(ROOT / name, self.root / name, ignore=shutil.ignore_patterns('__pycache__', '.DS_Store'))
        shutil.copyfile(ROOT / 'requirements-validation.txt', self.root / 'requirements-validation.txt')
        namespace = RepositoryPaths(str(self.root), RepositoryDataIO(self.root))
        self.root_path = namespace.root
        self.path_factory = namespace.path
        self.factory = RepositorySchemas(self.root_path, identifier_bases=(BASE,))

    def test_known_retained_contract_references_resolve_without_network_or_ambient_file_io(self):
        schema = {'$ref': BASE + 'evidence-trust-record.schema.json'}
        record = json.loads((self.root / 'docs/examples/evidence-trust-record.example.json').read_bytes())
        self.factory(schema).validate(record)
        changed = dict(record); changed['schema_version'] = 'invalid'
        with self.assertRaises(ValidationError): self.factory(schema).validate(changed)

    def test_arbitrary_http_file_relative_and_unlisted_schema_ids_cannot_be_retrieved(self):
        for identifier in ('https://example.invalid/remote.schema.json', 'file:///etc/passwd',
                           '../outside.schema.json', BASE + '../outside.schema.json',
                           BASE + 'missing.schema.json', 'urn:arbitrary:resource'):
            with self.subTest(identifier=identifier):
                with patch('urllib.request.urlopen', side_effect=AssertionError('network forbidden')):
                    with self.assertRaises(Exception) as caught:
                        self.factory({'$ref': identifier}).validate({})
                    self.assertNotIsInstance(caught.exception, AssertionError)

    def test_unused_invalid_schema_is_not_parsed_ahead_of_original_check(self):
        (self.root / 'schemas/unused.schema.json').write_bytes(b'{')
        factory = RepositorySchemas(self.root_path, identifier_bases=(BASE,))
        factory({'type': 'integer'}).validate(1)
        with self.assertRaises(Exception): factory({'$ref': BASE + 'unused.schema.json'}).validate({})

    def test_schema_created_after_membership_capture_is_not_automatically_admitted(self):
        (self.root / 'schemas/new.schema.json').write_text('{"type":"integer"}')
        with self.assertRaises(Exception): self.factory({'$ref': BASE + 'new.schema.json'}).validate(1)

    def test_bounded_link_replacement_cannot_supply_foreign_schema_bytes(self):
        path = self.root / 'schemas/evidence-trust-record.schema.json'
        path.unlink(); path.symlink_to('/etc/passwd')
        with self.assertRaises(Exception): self.factory({'$ref': BASE + path.name}).validate({})

    def test_dcr_whole_existing_projection_keeps_original_validator_behavior(self):
        self.assertEqual(dcr_operations.validate(self.root_path, validator_class=self.factory),
                         dcr_operations.validate(self.root, validator_class=Draft202012Validator))

    def test_all_default_lifecycle_checks_work_with_closed_factory_and_explicit_capture_profile(self):
        current = RepositoryLifecycle(self.root_path, validator_class=self.factory,
                                      path_factory=self.path_factory, provider_factory=LegacyRepositoryLifecycleCapture)
        ordinary = RepositoryLifecycle(self.root, validator_class=Draft202012Validator,
                                       provider_factory=LegacyRepositoryLifecycleCapture)
        self.assertEqual(current.validate_examples(), ordinary.validate_examples())
        actual, expected = [], []
        current.validate_default_ledger(print_line=actual.append)
        ordinary.validate_default_ledger(print_line=expected.append)
        self.assertEqual(actual, expected)

    def test_supplied_trusted_registry_stays_closed_and_format_options_are_preserved(self):
        record = {'type': 'string', 'format': 'axiom-test-format'}
        from jsonschema import FormatChecker
        checker = FormatChecker()
        checker.checks('axiom-test-format')(lambda value: value == 'valid')
        validator = self.factory(record, format_checker=checker, registry=Registry())
        self.assertIs(validator.format_checker, checker)
        with self.assertRaises(ValidationError):
            validator.validate('invalid')
        with self.assertRaises(Exception):
            self.factory({'$ref': BASE + 'evidence-trust-record.schema.json'}, registry=Registry()).validate({})
        self.factory.check_schema(record)

    def test_identifier_namespace_must_be_explicit_and_unique(self):
        for value in ((), [], ('',), (BASE, BASE), ('urn:missing-trailing-delimiter',)):
            with self.assertRaises(ValueError): RepositorySchemas(self.root_path, identifier_bases=value)


if __name__ == '__main__':
    unittest.main()
