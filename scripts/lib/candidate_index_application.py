"""Retained candidate-only read models; never accept or publish governance results."""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile

from jsonschema import Draft202012Validator, ValidationError
from lib.candidate_workspace import private_directory
from lib.ci_bundle_storage import reserve
from lib.consumer_intake_store import atomic_json
from lib.functional_parity import git_read
from lib.portable.contracts import ROOT, canonical_digest
from lib.portable.runtime import read_json, source_digest
from lib.portable_intake.candidate_index import build_from_documents
from lib.provider_ports import (capture_candidate_source, candidate_index_destination,
    observe_candidate_index_output, replace_candidate_index_output, CANDIDATE_INDEX_PROFILE)
from lib.result_assessments import identity
from lib.result_bytes import safe_bytes, strict_json
from lib.supplement_application import write_lock
from lib.v2_boundary import safe_source

PREFIX = 'status/portable/v2/candidates/'
OUTPUT = 'generated/portable-intake/index.json'
MAX_FILES = 50000
MAX_BYTES = 128 * 1024**2
MAX_FILE = 65536
MAX_MANIFEST = 64 * 1024**2
MAX_OUTPUT = 512 * 1024**2
FLAGS = {name: False for name in ('official_acceptance', 'production_approval',
    'risk_acceptance', 'authority_transferred', 'operating_acceptance_inherited',
    'published', 'provider_invoked', 'native_verification_performed')}


def wire(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def descriptors(files):
    return {name: {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
            for name, raw in files.items()}


def source_name(name, *, directory=False):
    if not isinstance(name, str): raise ValueError('invalid_candidate_source_name')
    path = PurePosixPath(name)
    if (not name.startswith(PREFIX) or path.is_absolute() or str(path) != name
            or '..' in path.parts or '\\' in name or any(ord(c) < 32 for c in name)
            or (not directory and path.suffix != '.json')):
        raise ValueError('invalid_candidate_source_name')
    return name


def project(files):
    if len(files) > MAX_FILES or sum(map(len, files.values())) > MAX_BYTES:
        raise ValueError('candidate_index_budget_exceeded')
    def documents():
        for name, raw in files.items():
            source_name(name)
            if len(raw) > MAX_FILE: raise ValueError('candidate_index_budget_exceeded')
            # The original reader decodes UTF-8 text before parsing JSON.
            # json.loads(bytes) would additionally accept UTF-16/32 and a BOM.
            yield name, strict_json(raw.decode('utf-8'))
    try:
        raw = wire(build_from_documents(documents()))
    except (ValidationError, UnicodeError, json.JSONDecodeError, RecursionError, OverflowError):
        raise ValueError('invalid_candidate_index_payload') from None
    if len(raw) > MAX_OUTPUT: raise ValueError('candidate_index_output_budget')
    return raw


class CandidateIndexContext:
    def __init__(self, instance_root, settings):
        self.instance_root = Path(instance_root).resolve()
        private_directory(self.instance_root / 'state')
        self.root = private_directory(self.instance_root / 'state/candidate-index')
        self.inputs = private_directory(self.root / 'inputs')
        self.artifacts = private_directory(self.root / 'artifacts')
        self.assessments = private_directory(self.root / 'assessments')
        self.exports = private_directory(self.root / 'exports')
        self.binding = {'node_id': settings['node_id'], 'runtime_source_digest': source_digest(),
                        'source_revision': git_read(ROOT, 'rev-parse', 'HEAD').decode().strip()}
        self.clean = not bool(git_read(ROOT, 'status', '--porcelain', '--untracked-files=all').strip())

    def current(self):
        if (source_digest() != self.binding['runtime_source_digest']
                or git_read(ROOT, 'rev-parse', 'HEAD').decode().strip() != self.binding['source_revision']):
            raise ValueError('candidate_index_product_changed')

    def manifest(self, value, input_id):
        if (not isinstance(value, dict) or set(value) != {'schema_version', 'profile', 'origin', 'files'}
                or type(value['schema_version']) is not int or value['schema_version'] != 1
                or value['profile'] != CANDIDATE_INDEX_PROFILE or canonical_digest(value) != input_id):
            raise ValueError('invalid_candidate_index_manifest')
        origin = value['origin']
        if (not isinstance(origin, dict) or set(origin) != {'mode', 'root', 'revision', 'directories'}
                or origin['mode'] not in ('working', 'committed')
                or not isinstance(origin['root'], str) or not Path(origin['root']).is_absolute()
                or not isinstance(origin['directories'], list)
                or len(origin['directories']) > 3*MAX_FILES+4
                or len(set(origin['directories'])) != len(origin['directories'])):
            raise ValueError('invalid_candidate_index_origin')
        if origin['mode'] == 'working':
            if origin['revision'] is not None: raise ValueError('invalid_candidate_index_origin')
        elif (not isinstance(origin['revision'], str) or len(origin['revision']) not in (40, 64)
              or any(c not in '0123456789abcdef' for c in origin['revision'])):
            raise ValueError('invalid_candidate_index_origin')
        for name in origin['directories']: source_name(name, directory=True)
        rows = value['files']
        if not isinstance(rows, dict) or len(rows) > MAX_FILES:
            raise ValueError('invalid_candidate_index_members')
        total = 0
        for name, row in rows.items():
            source_name(name)
            if (not isinstance(row, dict) or set(row) != {'sha256', 'bytes'}
                    or type(row['bytes']) is not int or not 0 <= row['bytes'] <= MAX_FILE):
                raise ValueError('invalid_candidate_index_member')
            identity(row['sha256']); total += row['bytes']
            if total > MAX_BYTES: raise ValueError('candidate_index_budget_exceeded')

    def input_data(self, input_id):
        root = self.inputs / identity(input_id)
        if root.is_symlink() or not root.is_dir() or root.stat().st_mode & 0o077:
            raise ValueError('private_candidate_index_input_required')
        value = strict_json(safe_bytes(root / 'manifest.json', limit=MAX_MANIFEST))
        self.manifest(value, input_id)
        actual = set()
        for visited, path in enumerate(root.rglob('*'), 1):
            if visited > 5*MAX_FILES+32: raise ValueError('candidate_index_retained_member_budget')
            if path.is_symlink() or path.stat().st_mode & 0o077:
                raise ValueError('private_candidate_index_material_required')
            if not path.is_dir(): actual.add(path.relative_to(root).as_posix())
        if actual != {'manifest.json', *('data/' + name for name in value['files'])}:
            raise ValueError('candidate_index_retained_members_changed')
        files = {name: safe_bytes(safe_source(root / 'data', name), limit=MAX_FILE)
                 for name in value['files']}
        if descriptors(files) != value['files']: raise ValueError('candidate_index_retained_input_changed')
        return files, value

    def capture(self, source, revision=None):
        origin, files = capture_candidate_source(source, revision)
        # Validate complete payloads before retaining any input or output.
        project(files)
        value = {'schema_version': 1, 'profile': CANDIDATE_INDEX_PROFILE,
                 'origin': origin, 'files': descriptors(files)}
        raw = wire(value)
        if len(raw) > MAX_MANIFEST: raise ValueError('candidate_index_manifest_budget')
        input_id = canonical_digest(value); self.manifest(value, input_id)
        reserve(self.root, sum(map(len, files.values())) + len(raw))
        with tempfile.TemporaryDirectory(prefix='.capture-', dir=self.inputs) as temporary:
            staged = Path(temporary) / 'snapshot'; staged.mkdir(mode=0o700)
            for name, content in files.items():
                path = safe_source(staged / 'data', name)
                path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                for parent in path.parents:
                    if parent == staged: break
                    parent.chmod(0o700)
                path.write_bytes(content); path.chmod(0o600)
            atomic_json(staged / 'manifest.json', value)
            self.current()
            with write_lock(self.root):
                target = self.inputs / input_id
                if target.is_symlink(): raise ValueError('unsafe_candidate_index_input')
                if not target.exists(): os.rename(staged, target)
                observed, recorded = self.input_data(input_id)
                if observed != files or recorded != value:
                    raise ValueError('immutable_candidate_index_input_conflict')
        return input_id, files

    def validate(self, value):
        try:
            Draft202012Validator(read_json(ROOT / 'schemas/axiom-v2-candidate-index.schema.json')).validate(value)
        except ValidationError:
            raise ValueError('invalid_candidate_index_assessment') from None
        if any(value.get(key) != expected for key, expected in self.binding.items()):
            raise ValueError('candidate_index_node_runtime_or_product_changed')

    def create(self, source=ROOT, revision=None):
        input_id, files = self.capture(source, revision)
        output = project(files)
        value = {'schema_version': 1, 'kind': 'private-candidate-index', **self.binding,
            'profile': CANDIDATE_INDEX_PROFILE, 'source_worktree_clean': self.clean,
            'input_id': input_id, 'output': descriptors({OUTPUT: output})[OUTPUT],
            'candidate_count': strict_json(output)['candidate_count'], 'evidence_trust': 'unverified',
            'mode': 'report-only', **FLAGS}
        self.validate(value); assessment_id = canonical_digest(value)
        reserve(self.root, len(output) + 65536)
        with tempfile.TemporaryDirectory(prefix='.index-', dir=self.artifacts) as temporary:
            staged = Path(temporary) / 'data'; staged.mkdir(mode=0o700)
            (staged / 'index.json').write_bytes(output); (staged / 'index.json').chmod(0o600)
            self.current()
            with write_lock(self.root):
                target = self.artifacts / assessment_id
                record = self.assessments / (assessment_id + '.json')
                if target.is_symlink() or record.is_symlink(): raise ValueError('unsafe_candidate_index_artifact')
                if record.exists():
                    if strict_json(safe_bytes(record, limit=65536)) != value:
                        raise ValueError('immutable_candidate_index_conflict')
                    self.inspect(assessment_id)
                elif target.exists(): raise ValueError('incomplete_candidate_index_requires_recovery')
                else:
                    os.rename(staged, target); atomic_json(record, value)
        return assessment_id, deepcopy(value)

    def inspect(self, assessment_id):
        assessment_id = identity(assessment_id)
        value = strict_json(safe_bytes(self.assessments / (assessment_id + '.json'), limit=65536))
        if canonical_digest(value) != assessment_id: raise ValueError('candidate_index_assessment_changed')
        self.validate(value)
        files, _ = self.input_data(value['input_id']); expected = project(files)
        if descriptors({OUTPUT: expected})[OUTPUT] != value['output']:
            raise ValueError('candidate_index_projection_changed')
        if strict_json(expected)['candidate_count'] != value['candidate_count']:
            raise ValueError('candidate_index_count_changed')
        root = self.artifacts / assessment_id
        if root.is_symlink() or not root.is_dir() or root.stat().st_mode & 0o077:
            raise ValueError('private_candidate_index_artifact_required')
        if {path.name for path in root.iterdir()} != {'index.json'}:
            raise ValueError('candidate_index_output_members_changed')
        if safe_bytes(root / 'index.json', limit=MAX_OUTPUT) != expected:
            raise ValueError('candidate_index_output_changed')
        self.current()
        return value

    def export(self, assessment_id, destination):
        value = self.inspect(assessment_id)
        _, manifest = self.input_data(value['input_id'])
        raw = safe_bytes(self.artifacts / assessment_id / 'index.json', limit=MAX_OUTPUT)
        destination = candidate_index_destination(destination, manifest['origin']['root'],
                                                   excluded=(ROOT, self.instance_root))
        with write_lock(self.root):
            before, metadata = observe_candidate_index_output(destination)
            reserve(self.root, len(raw) + len(before or b'') + 65536)
            transaction = Path(tempfile.mkdtemp(prefix='export-', dir=self.exports))
            if before is not None:
                descriptor = os.open(transaction / 'before.bin', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, 'wb') as stream:
                    stream.write(before); stream.flush(); os.fsync(stream.fileno())
            intent = {'schema_version': 1, **self.binding, 'assessment_id': assessment_id,
                'destination': str(destination), 'before': descriptors({'output': before})['output'] if before is not None else None,
                'before_metadata': metadata, 'after': descriptors({'output': raw})['output'],
                'phase': 'prepared', **FLAGS}
            atomic_json(transaction / 'intent.json', intent)
            descriptor = os.open(transaction, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
            try: os.fsync(descriptor)
            finally: os.close(descriptor)
            self.current()
            replace_candidate_index_output(destination, raw, before, metadata)
            atomic_json(transaction / 'receipt.json', {**intent, 'phase': 'completed'})
        return destination


def run(arguments, instance_root, settings):
    parser = argparse.ArgumentParser(prog='axiom-v2 candidate-index', allow_abbrev=False)
    commands = parser.add_subparsers(dest='command', required=True)
    create = commands.add_parser('generate', allow_abbrev=False)
    create.add_argument('--profile', choices=(CANDIDATE_INDEX_PROFILE,), required=True)
    create.add_argument('--source-root', '--root', dest='root', type=Path)
    create.add_argument('--revision')
    create.add_argument('--output', type=Path)
    create.add_argument('--format', choices=('receipt', 'legacy'), default='receipt')
    inspect = commands.add_parser('inspect', allow_abbrev=False); inspect.add_argument('--id', required=True)
    export = commands.add_parser('export', allow_abbrev=False)
    export.add_argument('--id', required=True); export.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(arguments); context = CandidateIndexContext(instance_root, settings)
    if args.command == 'inspect':
        print(json.dumps({'assessment_id': args.id, 'assessment': context.inspect(args.id),
                          'retained_sources_and_complete_original_output_reverified': True}, sort_keys=True))
        return 0
    if args.command == 'export':
        destination = context.export(args.id, args.output)
        print(json.dumps({'assessment_id': args.id, 'output': str(destination),
                          'official_acceptance': False, 'published': False}, sort_keys=True))
        return 0
    revision = args.revision
    if args.root is None and revision is None: revision = context.binding['source_revision']
    assessment_id, value = context.create(args.root if args.root is not None else ROOT, revision)
    if args.output is not None: context.export(assessment_id, args.output)
    if args.format != 'legacy':
        print(json.dumps({'assessment_id': assessment_id, 'assessment': value,
                          'artifact_directory': str(context.artifacts / assessment_id)}, sort_keys=True))
    return 0
