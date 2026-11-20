"""Own fixed product inputs stay bound to the admitted source-byte map."""
import hashlib
from pathlib import PurePosixPath


def product_label(source, paths, kind):
    relative = paths[kind]
    if (not isinstance(relative, str) or PurePosixPath(relative).is_absolute()
            or str(PurePosixPath(relative)) != relative or '..' in PurePosixPath(relative).parts):
        raise ValueError('operations_product_input_contract_invalid')
    return str(PurePosixPath(source['source_root']) / relative)


def check_labels(request, source, paths):
    if request['schema_label'] != product_label(source, paths, 'schema'):
        raise ValueError('operations_product_schema_label_changed')


def check_bytes(kind, label, raw, source, paths):
    if kind not in paths:
        return
    expected = product_label(source, paths, kind)
    if kind == 'schema' and label != expected:
        raise ValueError('operations_product_schema_label_changed')
    # An explicit external configuration is a selected input, while the fixed
    # schema and own default configuration are part of the product generation.
    if label == expected and hashlib.sha256(raw).hexdigest() != source['active_fingerprints'][paths[kind]]:
        raise ValueError('operations_product_input_bytes_changed')
