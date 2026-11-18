"""Lazy schema resources confined to an explicit retained-data namespace.

Schema identifiers are contract names, never permission to retrieve a URL or
open an arbitrary file. Unused resources are not parsed ahead of V1's checks.
"""
import json

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.exceptions import NoSuchResource
from referencing.jsonschema import DRAFT202012


class RepositorySchemas:
    def __init__(self, root, *, identifier_bases):
        if (type(identifier_bases) is not tuple or not identifier_bases
                or any(type(base) is not str or not base or not base.endswith('/') for base in identifier_bases)
                or len(set(identifier_bases)) != len(identifier_bases)):
            raise ValueError('explicit_repository_schema_identifier_bases_required')
        self.root = root
        resources = {}
        for path in (root / 'schemas').glob('*.schema.json'):
            if path.is_file() and not path.is_symlink():
                for base in identifier_bases:
                    resources[base + path.name] = path
        self.resources = resources
        self.registry = Registry(retrieve=self.retrieve)

    def retrieve(self, uri):
        try:
            path = self.resources[uri]
        except KeyError:
            raise NoSuchResource(ref=uri) from None
        return Resource.from_contents(json.loads(path.read_text(encoding='utf-8')), default_specification=DRAFT202012)

    @staticmethod
    def check_schema(schema, **options):
        return Draft202012Validator.check_schema(schema, **options)

    def __call__(self, schema, **options):
        options.setdefault('registry', self.registry)
        return Draft202012Validator(schema, **options)
