"""Read only the public projection; never follow paths into private collector state."""
import json
from pathlib import Path


def read_projection(directory):
    if directory is None:
        return {'configured': False}
    path = Path(directory) / 'consumers.json'
    if not path.exists():
        return {'configured': False}
    if path.is_symlink() or path.stat().st_size > 2 * 1024 * 1024:
        raise ValueError('Consumer projection is invalid')
    value = json.loads(path.read_text())
    if value.get('schema_version') != 1 or not isinstance(value.get('jobs'), list):
        raise ValueError('Consumer projection version is unsupported')
    return value
