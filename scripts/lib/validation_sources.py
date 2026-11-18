"""Committed product self-validation data; no executable caller source."""
import hashlib

from lib.functional_parity import git_read
from lib.portable.contracts import canonical_digest
from lib import report_sources
from lib.validation_files import ValidationFiles

SCOPES = ('architecture', 'schemas', 'policies', 'generated/demo')


def capture(source, revision):
    inventory = report_sources.inventory(source, revision)
    data = {}
    total = 0
    for name, meta in inventory['membership'].items():
        if not any(name == scope or name.startswith(scope + '/') for scope in SCOPES):
            continue
        total += meta['bytes']
        if meta['bytes'] > report_sources.MAX_FILE or total > report_sources.MAX_TOTAL:
            raise ValueError('validation_input_byte_budget')
        raw = git_read(source, 'cat-file', 'blob', meta['git_blob'])
        blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw, usedforsecurity=False).hexdigest()
        if len(raw) != meta['bytes'] or blob != meta['git_blob']:
            raise ValueError('validation_committed_input_changed')
        data[name] = raw
    # Code membership is retained only for original exists() decisions. No
    # Python, shell, or inspected application program is read into this view.
    manifest = {'schema_version': 1, 'scope': 'committed-product-runtime-validation-v1',
        'commit': revision, 'tree': inventory['tree'], 'membership': sorted(inventory['membership']),
        'files': {name: {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
                  for name, raw in data.items()}}
    ValidationFiles(data, manifest['membership'])
    return data, manifest


def digest(manifest):
    return canonical_digest(manifest)
