"""Closed local execution dependency fingerprints; no provider operations."""
from pathlib import Path
import hashlib


def fingerprints(root):
    """Closed dependency set. Documentation/status changes do not authorize new code."""
    root = Path(root)
    names = ['scripts', 'schemas', 'model', 'policies', 'architecture', 'releases', 'pipeline-baseline',
             '.github/workflows', '.agents', 'docs/governance/source-documents', 'docs/foundation']
    paths = [path for name in names for path in (root / name).rglob('*') if path.is_file()
             and '__pycache__' not in path.parts and path.suffix != '.pyc']
    paths += list(root.glob('requirements*'))
    result = {}
    for path in sorted(paths):
        if path.is_symlink():
            raise ValueError('Symlink in executable dependency set')
        result[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return result
