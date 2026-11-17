"""Small strict JSON and private regular-file reads, without application imports."""
import json
import os
from pathlib import Path
import stat

MAX_FILE = 16 * 1024**2


def strict_json(raw):
    def unique(pairs):
        value = {}
        for key, item in pairs:
            if key in value: raise ValueError('duplicate_result_input_key')
            value[key] = item
        return value
    def finite(_):
        raise ValueError('nonfinite_result_input_number')
    try:
        value = json.loads(raw, object_pairs_hook=unique, parse_constant=finite)
    except (UnicodeError, RecursionError):
        raise ValueError('invalid_result_input_json') from None
    if not isinstance(value, dict): raise ValueError('result_input_object_required')
    return value


def safe_bytes(path, limit=MAX_FILE):
    path = Path(path).absolute()
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError('unsafe_supplement_source')
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_size > limit:
            raise ValueError('oversize_or_nonregular_supplement_source')
        with os.fdopen(descriptor, 'rb') as handle:
            descriptor = -1
            raw = handle.read(limit + 1)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(raw) > limit:
        raise ValueError('oversize_supplement_source')
    return raw
