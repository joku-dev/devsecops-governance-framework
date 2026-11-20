"""Versioned contracts for the single confirmed demo-consumer architecture scope."""
from pathlib import Path
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from .adapter import strict_json
from .contracts import ROOT, FORMAT_CHECKER, require
from .live_preparation import revision_ref

MODEL = 'model/governance/lifecycle/consumer-operation'


def schema_validator(name):
    aliases = {'pilot-action-request':'action-request', 'pilot-action-receipt':'action-receipt',
               'operating-acceptance':'acceptance', 'pilot-operating':'profile', 'pilot-receipt':'receipt'}
    name = aliases.get(name, name)
    schemas = [strict_json(p.read_bytes()) for p in (ROOT/'schemas').glob('governance-consumer-*.schema.json')]
    registry = Registry().with_resources((s['$id'], Resource.from_contents(s)) for s in schemas)
    schema = next(s for s in schemas if s['$id'].endswith(f'/governance-consumer-{name}.schema.json'))
    return Draft202012Validator(schema, registry=registry, format_checker=FORMAT_CHECKER)


def load_model(repo=ROOT):
    root = Path(repo).resolve()
    for name in ('profile', 'roles'):
        path = root/MODEL/(name+'.json')
        require(not any(p.is_symlink() for p in (path, *path.parents)), 'Consumer model symlink')
    profile = strict_json((root/MODEL/'profile.json').read_bytes())
    binding = strict_json((root/MODEL/'roles.json').read_bytes())
    schema_validator('profile').validate(profile)
    schema_validator('roles').validate(binding)
    require(profile['role_binding_ref'] == revision_ref(binding), 'Consumer role binding differs')
    require(profile['scope'] == binding['scope'], 'Consumer scope differs')
    return profile, binding


def load_operating(repo=ROOT):
    return load_model(repo)[0]


def validate_preparation(repo=ROOT):
    profile, binding = load_model(repo)
    return {'profile':profile, 'binding':binding, 'assignments':binding['assignments']}
