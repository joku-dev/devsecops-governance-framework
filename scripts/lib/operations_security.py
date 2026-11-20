"""Reconstruct a complete nested security operation from retained blob trees."""
import hashlib
import json

from lib.retained_security import release, security
from lib.retained_security_tree import RetainedTree, MAX_BYTES, MAX_FILES


def unpack(value, blob):
    if (not isinstance(value, dict) or set(value) != {'label', 'directories', 'files'}
            or not isinstance(value['files'], dict) or len(value['files']) > MAX_FILES):
        raise ValueError('operations_nested_tree_invalid')
    data = {}
    total = 0
    for name, ref in value['files'].items():
        raw = blob(ref)
        total += len(raw)
        if total > MAX_BYTES:
            raise ValueError('operations_nested_tree_byte_budget')
        data[name] = raw
    return RetainedTree(value['label'], data, value['directories'])


def reconstruct(value, blob, *, binding, repository, observed_at, model_raw, source_root):
    fields = {'schema_version', 'operation', 'binding', 'security', 'release_operation', 'release'}
    if (not isinstance(value, dict) or set(value) != fields
            or type(value['schema_version']) is not int or value['schema_version'] != 1
            or value['binding'] != binding):
        raise ValueError('operations_nested_security_binding_changed')
    security_tree = unpack(value['security'], blob)
    release_tree = unpack(value['release'], blob)
    used = False

    def release_inspector(operation):
        nonlocal used
        if used or operation != value['release_operation']:
            raise ValueError('operations_nested_release_reference_changed')
        used = True
        return release(release_tree, binding, operation)

    metadata, files = security(security_tree, binding, value['operation'], release_inspector)
    if (not used or metadata['repository'] != repository or metadata['provided_observation'] is not False
            or metadata['fail_on_findings'] is not False or metadata['source_root'] != source_root
            or metadata['requested_observed_at'] != observed_at or metadata['resolved_observed_at'] != observed_at
            or metadata['exit_code'] != 0 or metadata['model_sha256'] != hashlib.sha256(model_raw).hexdigest()
            or security_tree.read('inputs/model.yaml') != model_raw):
        raise ValueError('operations_nested_security_request_changed')
    # Complete original file insertion order, rather than sorted journal JSON.
    return json.loads(files['report.json'].decode('utf-8'))
