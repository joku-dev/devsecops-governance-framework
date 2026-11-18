"""Finite architecture-validation native requests over inert file bytes."""
import hashlib
from pathlib import Path

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
        if name not in files.files:
            raise FileNotFoundError('validation_opa_input_missing')
    return {'policy': policy, 'input': source, 'query': tail[4], 'format_json': formatted,
        'policy_sha256': hashlib.sha256(files.files[policy]).hexdigest(),
        'input_sha256': hashlib.sha256(files.files[source]).hexdigest()}
