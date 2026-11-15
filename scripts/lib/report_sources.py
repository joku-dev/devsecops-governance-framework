"""Exact committed data snapshots for read-only product reporting.

The fixed product Git revision supplies data, never executable source. Current
working files and an enclosing checkout cannot reinterpret the selected commit.
"""
import hashlib
import json
from pathlib import Path
import re

from lib.ci_bundle_storage import names_are_portable, reserve
from lib.consumer_intake_store import atomic_json
from lib.functional_parity import git_read
from lib.result_bytes import safe_bytes, strict_json
from lib.v2_boundary import safe_source

SCOPES = ('model', 'architecture', 'governance', 'status',
          'generated/reports/source-lineage-report.json')
MAX_FILES = 10000
MAX_FILE = 16 * 1024**2
MAX_TOTAL = 128 * 1024**2
MAX_MANIFEST = 4 * 1024**2


def inventory(source, revision):
    source = Path(source).resolve()
    if (not isinstance(revision, str) or not re.fullmatch('[0-9a-f]{40}', revision)
            or Path(git_read(source, 'rev-parse', '--show-toplevel').decode().strip()).resolve() != source
            or git_read(source, 'rev-parse', '--verify', revision + '^{commit}').decode().strip() != revision):
        raise ValueError('explicit_report_product_revision_required')
    rows = git_read(source, 'ls-tree', '-r', '-l', '-z', revision, '--', *SCOPES)
    files = {}; size = 0
    for row in filter(None, rows.split(b'\0')):
        meta, raw_name = row.split(b'\t', 1)
        mode, kind, blob, length = meta.decode().split(); name = raw_name.decode()
        safe_source(source, name)
        if kind != 'blob' or mode not in ('100644', '100755') or '.git' in Path(name).parts:
            raise ValueError('unsafe_committed_report_source')
        length = int(length); size += length
        if length > MAX_FILE or size > MAX_TOTAL or len(files) >= MAX_FILES:
            raise ValueError('report_source_budget_exhausted')
        files[name] = {'mode': mode, 'git_blob': blob, 'bytes': length}
    if not files: raise ValueError('report_source_data_missing')
    names_are_portable(files)
    return {'schema_version': 1, 'scope': 'committed-governance-data-v1', 'commit': revision,
            'tree': git_read(source, 'rev-parse', revision + '^{tree}').decode().strip(), 'files': files}


def capture(source, revision, destination):
    destination = Path(destination)
    if destination.exists() or destination.is_symlink(): raise ValueError('fresh_report_source_copy_required')
    value = inventory(source, revision)
    reserve(destination.parent, sum(row['bytes'] for row in value['files'].values()) + MAX_MANIFEST)
    destination.mkdir(mode=0o700); data = destination / 'data'; data.mkdir(mode=0o700)
    for name, row in value['files'].items():
        raw = git_read(source, 'cat-file', 'blob', row['git_blob'])
        if len(raw) != row['bytes']: raise ValueError('committed_report_source_changed')
        path = safe_source(data, name); path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        path.write_bytes(raw); path.chmod(0o600)
        row['sha256'] = hashlib.sha256(raw).hexdigest()
    manifest_size = len((json.dumps(value, sort_keys=True, indent=2) + '\n').encode())
    if manifest_size > MAX_MANIFEST:
        raise ValueError('report_source_manifest_budget_exhausted')
    reserve(destination, manifest_size)
    atomic_json(destination / 'manifest.json', value)
    verify(source, revision, destination)
    return value


def verify(source, revision, destination):
    destination = Path(destination)
    value = strict_json(safe_bytes(destination / 'manifest.json', limit=MAX_MANIFEST))
    expected = inventory(source, revision)
    if (set(value) != set(expected) or any(value.get(key) != expected[key] for key in expected if key != 'files')
            or set(value.get('files', {})) != set(expected['files'])):
        raise ValueError('report_source_manifest_changed')
    data = destination / 'data'
    if data.is_symlink() or not data.is_dir(): raise ValueError('unsafe_retained_report_source')
    actual = set()
    for path in data.rglob('*'):
        if path.is_symlink(): raise ValueError('unsafe_retained_report_source')
        if not path.is_dir(): actual.add(path.relative_to(data).as_posix())
        if len(actual) > MAX_FILES: raise ValueError('report_source_budget_exhausted')
    if actual != set(expected['files']): raise ValueError('report_source_membership_changed')
    for name, row in value['files'].items():
        meta = expected['files'][name]
        if set(row) != {*meta, 'sha256'} or any(row.get(k) != v for k, v in meta.items()):
            raise ValueError('report_source_git_binding_changed')
        raw = safe_bytes(safe_source(data, name), limit=MAX_FILE)
        # SHA-1 here is Git object identity, independently accompanied by SHA-256.
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw, usedforsecurity=False).hexdigest()
        if (len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']
                or blob != row['git_blob']):
            raise ValueError('retained_report_source_bytes_changed')
    return value
