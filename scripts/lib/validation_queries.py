"""Finite architecture-validation native requests over inert file bytes."""
import hashlib
from types import SimpleNamespace
from urllib.parse import urlsplit
from referencing import Resource, Registry
from referencing.jsonschema import DRAFT7
from lib.result_bytes import strict_json
from pathlib import Path

from lib.portable.contracts import ROOT
from lib.validation_files import WORKING_PROFILE

CAPABILITIES_SHA256 = 'a1bf991153d03bebbcece23bf90cb745a5500ea43e3898e06a2a789eb143f3f2'


def working_capabilities():
    raw = (ROOT / 'config/axiom-v2-validation-capabilities.json').read_bytes()
    if len(raw) > 256 * 1024 or hashlib.sha256(raw).hexdigest() != CAPABILITIES_SHA256:
        raise ValueError('validation_opa_capabilities_changed')
    return raw

MAX_STREAM = 8 * 1024**2
QUERIES = {
    'architecture_readiness.rego': 'data.architecture.readiness.deny',
    'architecture_integration_readiness.rego': 'data.architecture.integration_readiness.deny',
    'architecture_operation_readiness.rego': 'data.architecture.operation_readiness.deny',
    'architecture_release_readiness.rego': 'data.architecture.release_readiness.deny',
}


def request(command, files):
    if len(command) not in (7, 8) or command[:2] != ['opa', 'eval']:
        raise ValueError('unsupported_validation_opa_command')
    formatted = len(command) == 8
    tail = command[3:] if formatted else command[2:]
    if formatted and command[2] != '--format=json' or tail[::2] != ['--data', '--input', tail[-1]]:
        raise ValueError('unsupported_validation_opa_arguments')
    prefix = files.label + '/'
    if not tail[1].startswith(prefix) or not tail[3].startswith(prefix):
        raise ValueError('validation_opa_input_outside_snapshot')
    policy, source = tail[1][len(prefix):], tail[3][len(prefix):]
    expected = 'policies/opa/' + Path(policy).name
    if policy != expected or QUERIES.get(Path(policy).name) != tail[4]:
        raise ValueError('unsupported_validation_opa_policy_or_query')
    for name in (policy, source):
        files.root.__truediv__(name)
        if name not in files.files and files.native_profile != WORKING_PROFILE:
            raise FileNotFoundError('validation_opa_input_missing')
    value = {'policy': policy, 'input': source, 'query': tail[4], 'format_json': formatted,
        'policy_sha256': hashlib.sha256(files.files[policy]).hexdigest() if policy in files.files else None,
        'input_sha256': hashlib.sha256(files.files[source]).hexdigest() if source in files.files else None}
    if files.native_profile == WORKING_PROFILE:
        working_capabilities()
        value.update(execution_profile=WORKING_PROFILE, capabilities_sha256=CAPABILITIES_SHA256)
    return value


def _policy_metadata_diagnostic(raw):
    try:
        value = strict_json(raw)
        annotations = value.get('annotations', [])
        if not isinstance(annotations, list): raise ValueError('invalid annotations')
        resources = []
        for annotation in annotations:
            if not isinstance(annotation, dict): raise ValueError('invalid annotation')
            schemas = annotation.get('schemas', [])
            if not isinstance(schemas, list): raise ValueError('invalid schemas')
            for item in schemas:
                if not isinstance(item, dict): raise ValueError('invalid schema item')
                if 'definition' in item:
                    root = Resource.from_contents(item['definition'], default_specification=DRAFT7)
                    resources.append((root, Registry().resolver_with_root(root), 0))
        count = 0; seen = set()
        while resources:
            resource, resolver, depth = resources.pop(); count += 1
            schema = resource.contents
            if id(schema) in seen: continue
            seen.add(id(schema))
            if count > 100000 or depth > 100: raise ValueError('schema budget')
            if isinstance(schema, dict):
                for key in ('$ref', '$dynamicRef', '$recursiveRef'):
                    reference = schema.get(key)
                    if isinstance(reference, str) and not reference.startswith('#'):
                        return 'validation_policy_schema_reference_forbidden'
                    if isinstance(reference, str):
                        resolved = resolver.lookup(reference)
                        child = Resource.from_contents(resolved.contents, default_specification=DRAFT7)
                        resources.append((child, resolved.resolver, depth + 1))
                for key in ('$id', 'id', '$schema'):
                    identity = schema.get(key)
                    if isinstance(identity, str) and urlsplit(identity).scheme.lower() == 'file':
                        return 'validation_policy_schema_reference_forbidden'
            resources.extend((child, resolver.in_subresource(child), depth + 1) for child in resource.subresources())
        return None
    except Exception:
        return 'validation_policy_metadata_invalid_or_over_budget'


def parsed_policy_guard(result):
    """A declared parse result can reject evaluation, never invent its success."""
    if result.returncode != 0:
        return result
    diagnostic = _policy_metadata_diagnostic(result.stdout)
    if diagnostic is not None:
        return SimpleNamespace(returncode=2, stdout='', stderr=diagnostic)
    return None
