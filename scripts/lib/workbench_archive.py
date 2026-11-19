"""Closed, reproducible draft-only backup bytes; no key or operating authority."""
import hashlib
import io
import json
import re
from pathlib import PurePosixPath
import zipfile
from jsonschema import Draft202012Validator
from lib.result_bytes import strict_json

MAX_FILE = 16 * 1024**2
MAX_TOTAL = 128 * 1024**2
MAX_FILES = 10000
MAX_MANIFEST = 4 * 1024**2
FLAGS = {'authority_transferred': False, 'official_acceptance': False,
         'publication_enabled': False, 'sessions_restored': False, 'keys_included': False}
BINDING_KEYS = {'source_revision', 'runtime_source_digest', 'application_source_digest', 'node_id'}


def member_name(name):
    if not isinstance(name, str) or not re.fullmatch(
            r'[a-f0-9]{32}/(?:draft\.json|source\.(?:md|markdown|pdf|docx))', name):
        raise ValueError('invalid_workbench_backup_member')
    return name


def source_destination(source):
    if not isinstance(source, dict): raise ValueError('invalid_workbench_source_metadata')
    identifier = source.get('id'); name = source.get('source_path')
    if not isinstance(identifier, str) or not re.fullmatch('[A-Z0-9]+(?:-[A-Z0-9]+)*-[0-9]{3}', identifier):
        raise ValueError('invalid_workbench_source_identifier')
    if (not isinstance(name, str) or not name.startswith('docs/governance/source-documents/')
            or PurePosixPath(name).as_posix() != name or PurePosixPath(name).is_absolute()
            or '..' in PurePosixPath(name).parts or '\\' in name or ':' in name
            or any(ord(c) < 32 for c in name)):
        raise ValueError('unsafe_workbench_source_destination')
    return name


def checked_draft(draft, directory, schema):
    if not Draft202012Validator(schema).is_valid(draft) or draft['draft_id'] != directory:
        raise ValueError('invalid_workbench_backup_draft')
    if draft['kind'] in ('source_candidate', 'source_review'):
        name = source_destination(draft['source'])
        if draft['kind'] == 'source_candidate':
            expected = 'docs/governance/source-documents/' + draft['source']['id'] + PurePosixPath(draft['upload_name']).suffix
            if name != expected: raise ValueError('unsafe_workbench_source_destination')
    if draft.get('target'):
        source_destination(draft['target'].get('source'))
    if draft['kind'] == 'review_package':
        for row in draft['manifest']:
            source_destination({'id':row['source_id'], 'source_path':row['source_path']})
    return draft


def checked_files(files, directories, schema):
    if (not isinstance(files, dict) or not isinstance(directories, list)
            or len(files) + len(directories) > MAX_FILES
            or any(not isinstance(d, str) or not re.fullmatch('[a-f0-9]{32}', d) for d in directories)
            or sorted(set(directories)) != directories):
        raise ValueError('invalid_workbench_backup_inventory')
    total = 0
    for name, raw in files.items():
        member_name(name)
        if (name.split('/')[0] not in directories or not isinstance(raw, bytes)
                or len(raw) > MAX_FILE):
            raise ValueError('invalid_workbench_backup_file')
        total += len(raw)
    if total > MAX_TOTAL:
        raise ValueError('workbench_backup_byte_budget')
    for directory in directories:
        names = {name for name in files if name.startswith(directory + '/')}
        if not names: continue  # Retain an interrupted empty preparation directory.
        if directory + '/draft.json' not in names:
            raise ValueError('workbench_backup_draft_missing')
        draft = strict_json(files[directory + '/draft.json'].decode('utf-8'))
        checked_draft(draft, directory, schema)
        expected = {directory + '/draft.json'}
        if draft['kind'] == 'source_candidate':
            upload = directory + '/' + draft['upload_name']; expected.add(upload)
            raw = files.get(upload)
            if (raw is None or not 0 < len(raw) <= 5 * 1024**2
                    or hashlib.sha256(raw).hexdigest() != draft['sha256']):
                raise ValueError('workbench_backup_upload_binding_mismatch')
        if names != expected:
            raise ValueError('unexpected_workbench_backup_draft_files')
    return files


def binding(value):
    if not isinstance(value, dict) or set(value) != BINDING_KEYS:
        raise ValueError('invalid_workbench_backup_source')
    for name in BINDING_KEYS:
        pattern = '[a-f0-9]{32}' if name == 'node_id' else '[a-f0-9]{40}' if name == 'source_revision' else '[a-f0-9]{64}'
        if not isinstance(value[name], str) or not re.fullmatch(pattern, value[name]):
            raise ValueError('invalid_workbench_backup_source')
    return value


def create(files, directories, source, schema):
    checked_files(files, directories, schema); binding(source)
    manifest = {'schema_version': 1, 'kind': 'workbench-draft-backup', 'source': source,
        'directories': directories, 'files': {name: {'sha256': hashlib.sha256(raw).hexdigest(),
        'bytes': len(raw)} for name, raw in sorted(files.items())}, **FLAGS}
    encoded = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
    if len(encoded) > MAX_MANIFEST: raise ValueError('workbench_backup_manifest_budget')
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_STORED) as archive:
        for name, raw in [('manifest.json', encoded), *sorted(files.items())]:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3; info.external_attr = 0o100600 << 16
            archive.writestr(info, raw)
    return output.getvalue(), manifest


def inspect(raw, schema, expected, *, allow_source_change=False):
    binding(expected)
    if type(allow_source_change) is not bool: raise ValueError('explicit_workbench_source_import_choice_required')
    if not isinstance(raw, bytes) or len(raw) > MAX_TOTAL + 16 * 1024**2:
        raise ValueError('workbench_backup_archive_budget')
    try:
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            if (not 1 <= len(entries) <= MAX_FILES + 1
                    or len({e.filename for e in entries}) != len(entries)):
                raise ValueError('invalid_workbench_backup_members')
            files = {}; total = 0; manifest_raw = None
            for entry in entries:
                if (entry.is_dir() or entry.flag_bits & 1 or entry.compress_type != zipfile.ZIP_STORED
                        or entry.external_attr >> 16 != 0o100600):
                    raise ValueError('invalid_workbench_backup_member_type')
                if entry.filename != 'manifest.json': member_name(entry.filename)
                limit = MAX_MANIFEST if entry.filename == 'manifest.json' else MAX_FILE
                total += entry.file_size
                if not 0 <= entry.file_size <= limit or total > MAX_TOTAL + MAX_MANIFEST:
                    raise ValueError('workbench_backup_byte_budget')
                value = archive.read(entry)
                if len(value) != entry.file_size: raise ValueError('invalid_workbench_backup_length')
                if entry.filename == 'manifest.json': manifest_raw = value
                else: files[entry.filename] = value
    except (zipfile.BadZipFile, RuntimeError, NotImplementedError, EOFError):
        raise ValueError('invalid_workbench_backup_archive') from None
    if manifest_raw is None: raise ValueError('workbench_backup_manifest_missing')
    manifest = strict_json(manifest_raw.decode('utf-8'))
    if (set(manifest) != {'schema_version', 'kind', 'source', 'directories', 'files', *FLAGS}
            or type(manifest['schema_version']) is not int or manifest['schema_version'] != 1
            or manifest['kind'] != 'workbench-draft-backup'
            or any(manifest[k] is not False for k in FLAGS)):
        raise ValueError('invalid_workbench_backup_manifest')
    binding(manifest['source'])
    if not allow_source_change and any(manifest['source'][k] != expected[k] for k in BINDING_KEYS - {'node_id'}):
        raise ValueError('workbench_backup_product_mismatch')
    if not isinstance(manifest['files'], dict): raise ValueError('invalid_workbench_backup_descriptors')
    for name, row in manifest['files'].items():
        member_name(name)
        if (not isinstance(row, dict) or set(row) != {'bytes', 'sha256'}
                or type(row['bytes']) is not int or not 0 <= row['bytes'] <= MAX_FILE
                or not isinstance(row['sha256'], str) or not re.fullmatch('[a-f0-9]{64}', row['sha256'])):
            raise ValueError('invalid_workbench_backup_descriptors')
    checked_files(files, manifest['directories'], schema)
    if manifest['files'] != {name: {'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
                              for name, data in files.items()}:
        raise ValueError('workbench_backup_content_mismatch')
    return manifest, files
