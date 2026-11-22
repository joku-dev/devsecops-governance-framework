"""Complete original consumer lifecycle functions over explicit data/effect ports.

Retained source history is not this node's operating authority.
"""
from __future__ import annotations
from copy import deepcopy
from referencing import Registry, Resource
import base64, hashlib
_OMITTED = object()
_DEFAULT_FETCH = object()
MODEL = 'model/governance/lifecycle/consumer-operation'

class ConsumerContracts:

    def __init__(self, root, context, *, path_factory, profile, process=None, temporary=None, clock=None, validator_class=None, default_fetch=None, architecture=None, argument_parser=None, argv=(), description=None):
        self.root, self.context, self.Path, self.profile = (root, context, path_factory, profile)
        self.process, self.temporary, self.clock = (process, temporary, clock)
        self.validator_class, self.default_fetch, self.architecture = (validator_class, default_fetch, architecture)
        self.argument_parser, self.argv, self.description = (argument_parser, list(argv), description)
        self.positive_id = profile.positive_id
        self.MODEL = MODEL

    def schema_validator(self, name):
        aliases = {'pilot-action-request': 'action-request', 'pilot-action-receipt': 'action-receipt', 'operating-acceptance': 'acceptance', 'pilot-operating': 'profile', 'pilot-receipt': 'receipt'}
        name = aliases.get(name, name)
        schemas = [self.context.adapter.strict_json(p.read_bytes()) for p in (self.root / 'schemas').glob('governance-consumer-*.schema.json')]
        registry = Registry().with_resources(((s['$id'], Resource.from_contents(s)) for s in schemas))
        schema = next((s for s in schemas if s['$id'].endswith(f'/governance-consumer-{name}.schema.json')))
        return self.validator_class(schema, registry=registry, format_checker=self.context.contracts.format_checker)

    def load_model(self, repo=_OMITTED):
        if repo is _OMITTED:
            repo = self.root
        root = self.Path(repo).resolve()
        for name in ('profile', 'roles'):
            path = root / self.MODEL / (name + '.json')
            self.context.contracts.require(not any((p.is_symlink() for p in (path, *path.parents))), 'Consumer model symlink')
        profile = self.context.adapter.strict_json((root / self.MODEL / 'profile.json').read_bytes())
        binding = self.context.adapter.strict_json((root / self.MODEL / 'roles.json').read_bytes())
        self.schema_validator('profile').validate(profile)
        self.schema_validator('roles').validate(binding)
        self.context.contracts.require(profile['role_binding_ref'] == self.context.preparation.revision_ref(binding), 'Consumer role binding differs')
        self.context.contracts.require(profile['scope'] == binding['scope'], 'Consumer scope differs')
        return (profile, binding)

    def load_operating(self, repo=_OMITTED):
        if repo is _OMITTED:
            repo = self.root
        return self.load_model(repo)[0]

    def validate_preparation(self, repo=_OMITTED):
        if repo is _OMITTED:
            repo = self.root
        profile, binding = self.load_model(repo)
        return {'profile': profile, 'binding': binding, 'assignments': binding['assignments']}
