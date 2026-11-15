"""Node/source-bound private assessments for declared CI and manual results."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from lib import ci_bundle_results as mappings
from lib import ci_bundle_storage as storage
from lib.candidate_workspace import private_directory
from lib.consumer_intake_store import atomic_json
from lib.functional_parity import git_read
from lib.portable.contracts import ROOT, canonical_digest, endpoint, repository_key
from lib.portable.runtime import read_json, source_digest
from lib.result_snapshot_store import explicit_time
from lib.supplement_application import safe_bytes, write_lock

MAX_METADATA = 4 * 1024**2
MAX_ASSESSMENT = 16 * 1024**2
MAX_CACHE = 64 * 1024**2


def identity(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value):
        raise ValueError('invalid_result_source_id')
    return value


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


def operator_bytes(path, limit=MAX_METADATA):
    path = Path(path)
    if path.is_symlink(): raise ValueError('unsafe_result_input_file')
    # Explicit operator input may use the system's /tmp or /var aliases. Retained
    # state always uses the resolved private instance path instead.
    return safe_bytes(path.resolve(), limit=limit)


def require_schema(value, name):
    try:
        Draft202012Validator(read_json(ROOT / 'schemas' / name), format_checker=FormatChecker()).validate(value)
    except ValidationError:
        raise ValueError('invalid_result_input_contract') from None


def metadata_value(raw):
    value = strict_json(raw)
    require_schema(value, 'axiom-v2-result-metadata.schema.json')
    repository = value['repository']
    repository_key(repository)
    parsed = urlsplit(repository['url'])
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment):
        raise ValueError('invalid_result_repository_url')
    endpoint(repository['instance'])
    return value


def mapped_snapshot(metadata, material, summary, at):
    parameters = SimpleNamespace(**metadata['parameters'])
    if metadata['input_kind'] == 'manual':
        snapshot = mappings.manual_snapshot(parameters, governance_repository=metadata['governance_repository'],
                                            at=at, control_summary=summary)
    else:
        errors = []
        validator = mappings.validate_devsecops if metadata['domain'] == 'devsecops' else mappings.validate_architecture
        validator(material, errors, schema_root=ROOT)
        if errors: raise ValueError('invalid_ci_artifact_bundle')
        builder = mappings.devsecops_snapshot if metadata['domain'] == 'devsecops' else mappings.architecture_snapshot
        snapshot = builder(material, parameters, governance_repository=metadata['governance_repository'], at=at)
    require_schema(snapshot, 'axiom-v2-result-snapshot.schema.json')
    explicit_time(snapshot['generated_at'])
    if snapshot['repository_id'] != metadata['repository']['path']:
        raise ValueError('result_repository_declaration_mismatch')
    return {metadata['domain']: snapshot}


class ResultContext:
    def __init__(self, instance_root, settings):
        self.instance_root = Path(instance_root).resolve()
        private_directory(self.instance_root / 'state')
        self.root = private_directory(self.instance_root / 'state/results')
        self.raw = private_directory(self.root / 'raw')
        self.assessments = private_directory(self.root / 'assessments')
        self.binding = {'node_id': settings['node_id'], 'runtime_source_digest': source_digest(),
                        'source_revision': git_read(ROOT, 'rev-parse', 'HEAD').decode().strip()}
        self.clean = not bool(git_read(ROOT, 'status', '--porcelain', '--untracked-files=all').strip())
        self.loaded = {}
        self.loaded_sizes = {}
        self.loaded_bytes = 0

    def remember(self, assessment_id, value):
        if assessment_id in self.loaded:
            self.loaded.pop(assessment_id)
            self.loaded_bytes -= self.loaded_sizes.pop(assessment_id)
        size = len(json.dumps(value, sort_keys=True).encode())
        while self.loaded and self.loaded_bytes + size > MAX_CACHE:
            oldest = next(iter(self.loaded))
            self.loaded.pop(oldest)
            self.loaded_bytes -= self.loaded_sizes.pop(oldest)
        if size <= MAX_CACHE:
            self.loaded[assessment_id] = deepcopy(value)
            self.loaded_sizes[assessment_id] = size
            self.loaded_bytes += size

    def assert_current(self):
        if (self.binding['runtime_source_digest'] != source_digest()
                or self.binding['source_revision'] != git_read(ROOT, 'rev-parse', 'HEAD').decode().strip()):
            raise ValueError('result_source_changed_during_operation')

    def validate(self, value):
        require_schema(value, 'axiom-v2-result-assessment.schema.json')
        if any(value[key] != expected for key, expected in self.binding.items()):
            raise ValueError('result_node_runtime_or_source_changed')
        explicit_time(value['assessed_at'])
        if len((json.dumps(value, sort_keys=True, indent=2) + '\n').encode()) > MAX_ASSESSMENT:
            raise ValueError('result_assessment_record_limit')
        if canonical_digest(value['raw_manifest']) != value['input_id']:
            raise ValueError('result_raw_manifest_identity_changed')

    def raw_sources(self, value, *, root=None):
        self.validate(value)
        raw = self.raw / identity(value['input_id']) if root is None else Path(root)
        manifest = strict_json(safe_bytes(raw / 'manifest.json', limit=MAX_ASSESSMENT))
        if manifest != value['raw_manifest']: raise ValueError('result_retained_manifest_changed')
        metadata_raw = safe_bytes(raw / 'metadata.json', limit=MAX_METADATA)
        if hashlib.sha256(metadata_raw).hexdigest() != manifest['metadata_sha256']:
            raise ValueError('result_retained_metadata_changed')
        metadata = metadata_value(metadata_raw)
        if metadata['repository'] != value['repository'] or metadata['input_kind'] != manifest['input_kind']:
            raise ValueError('result_retained_scope_changed')
        summary = None
        metadata_size = len(metadata_raw)
        if manifest['summary_sha256'] is not None:
            summary_raw = safe_bytes(raw / 'summary.json', limit=MAX_METADATA)
            metadata_size += len(summary_raw)
            if hashlib.sha256(summary_raw).hexdigest() != manifest['summary_sha256']:
                raise ValueError('result_retained_summary_changed')
            summary = strict_json(summary_raw)
        if metadata['input_kind'] == 'manual':
            if manifest['bundle'] is not None: raise ValueError('result_manual_source_changed')
            if metadata_size > value['storage_budget_bytes']:
                raise ValueError('result_input_storage_budget_exhausted')
            return metadata, summary, None
        if summary is not None or manifest['bundle'] is None: raise ValueError('result_bundle_source_changed')
        descriptor = manifest['bundle']; material = raw / 'bundle/material'
        if storage.inventory(material) != descriptor['files']:
            raise ValueError('result_retained_material_changed')
        if (sum(item['bytes'] for item in descriptor['files'].values()) != descriptor['material_bytes']
                or metadata_size + descriptor['raw_bytes'] + descriptor['material_bytes'] > value['storage_budget_bytes']):
            raise ValueError('result_retained_storage_accounting_changed')
        if descriptor['kind'] == 'directory':
            if descriptor['raw_bytes'] != 0: raise ValueError('result_retained_storage_accounting_changed')
            storage.verify_directory(material, descriptor)
        else:
            archive = raw / 'bundle/source.zip'
            actual = storage.hash_file(archive, storage.MAX_ARCHIVE)
            if actual != {'sha256': descriptor['input_sha256'], 'bytes': descriptor['raw_bytes']}:
                raise ValueError('result_retained_archive_changed')
        return metadata, summary, material

    def replay(self, value, *, root=None):
        metadata, summary, material = self.raw_sources(value, root=root)
        descriptor = value['raw_manifest']['bundle']
        if descriptor is not None and descriptor['kind'] == 'zip':
            raw = self.raw / value['input_id'] if root is None else Path(root)
            # Re-extract original ZIP bytes; a resealed material directory cannot
            # substitute a different report while retaining the original archive.
            with tempfile.TemporaryDirectory(prefix='.result-replay-', dir=self.root) as temporary:
                fresh = Path(temporary) / 'material'; fresh.mkdir(mode=0o700)
                files = storage.extract_archive(raw / 'bundle/source.zip', fresh,
                    raw_bytes=descriptor['raw_bytes'], budget=value['storage_budget_bytes'])
                if files != descriptor['files']: raise ValueError('result_archive_material_mismatch')
                snapshots = mapped_snapshot(metadata, fresh, summary, value['assessed_at'])
        else:
            snapshots = mapped_snapshot(metadata, material, summary, value['assessed_at'])
        if snapshots != value['snapshots']:
            raise ValueError('result_assessment_differs_from_exact_sources')
        return value

    def load(self, assessment_id):
        assessment_id = identity(assessment_id)
        if assessment_id not in self.loaded:
            value = strict_json(safe_bytes(self.assessments / (assessment_id + '.json'), limit=MAX_ASSESSMENT))
            if canonical_digest(value) != assessment_id: raise ValueError('result_assessment_identity_changed')
            value = self.replay(value)
            self.remember(assessment_id, value)
            return deepcopy(value)
        return deepcopy(self.loaded[assessment_id])

    def create(self, *, metadata_path, at, bundle=None, sha256=None, summary_path=None, budget=storage.DEFAULT_BUDGET):
        explicit_time(at)
        if type(budget) is not int or not 0 < budget <= storage.MAX_BUDGET:
            raise ValueError('invalid_result_storage_budget')
        metadata_raw = operator_bytes(metadata_path)
        metadata = metadata_value(metadata_raw)
        if metadata['input_kind'] == 'bundle' and (bundle is None or sha256 is None or summary_path is not None):
            raise ValueError('explicit_result_bundle_required')
        if metadata['input_kind'] == 'manual' and (bundle is not None or sha256 is not None):
            raise ValueError('manual_result_has_unexpected_bundle')
        summary_raw = operator_bytes(summary_path) if summary_path is not None else None
        summary = strict_json(summary_raw) if summary_raw is not None else None
        metadata_bytes = len(metadata_raw) + (len(summary_raw) if summary_raw is not None else 0)
        if metadata_bytes >= budget:
            raise ValueError('result_input_storage_budget_exhausted')
        storage.reserve(self.root, metadata_bytes)
        with tempfile.TemporaryDirectory(prefix='.incoming-', dir=self.raw) as temporary:
            staged = Path(temporary) / 'data'; staged.mkdir(mode=0o700)
            for name, raw in [('metadata.json', metadata_raw), ('summary.json', summary_raw)]:
                if raw is not None:
                    path = staged / name; path.write_bytes(raw); path.chmod(0o600)
            descriptor = storage.copy_bundle(bundle, identity(sha256), staged / 'bundle',
                budget=budget - metadata_bytes) if bundle is not None else None
            snapshots = mapped_snapshot(metadata, staged / 'bundle/material' if descriptor is not None else None, summary, at)
            manifest = {'schema_version': 1, 'input_kind': metadata['input_kind'],
                'metadata_sha256': hashlib.sha256(metadata_raw).hexdigest(),
                'summary_sha256': hashlib.sha256(summary_raw).hexdigest() if summary_raw is not None else None,
                'bundle': descriptor}
            input_id = canonical_digest(manifest)
            storage.reserve(self.root, len((json.dumps(manifest, sort_keys=True, indent=2) + '\n').encode()))
            atomic_json(staged / 'manifest.json', manifest)
            value = {'schema_version': 1, 'kind': 'v1-compatible-general-result-assessment', **self.binding,
                'source_worktree_clean': self.clean, 'assessed_at': at, 'input_origin': 'operator_bundle',
                'input_id': input_id, 'raw_manifest': manifest, 'repository': metadata['repository'],
                'snapshots': snapshots, 'storage_budget_bytes': budget, 'mode': 'report-only',
                'evidence_trust': 'unverified', 'official_acceptance': False, 'production_approval': False,
                'risk_acceptance': False, 'authority_transferred': False}
            self.validate(value); self.assert_current()
            with write_lock(self.root):
                target = self.raw / input_id
                if target.is_symlink(): raise ValueError('unsafe_result_raw_store')
                if target.exists():
                    self.replay(value)
                else:
                    os.rename(staged, target)
                assessment_id = canonical_digest(value); path = self.assessments / (assessment_id + '.json')
                if path.is_symlink(): raise ValueError('unsafe_result_assessment_store')
                if path.exists():
                    if strict_json(safe_bytes(path, limit=MAX_ASSESSMENT)) != value:
                        raise ValueError('immutable_result_assessment_conflict')
                else:
                    storage.reserve(self.root, len((json.dumps(value, sort_keys=True, indent=2) + '\n').encode()))
                    atomic_json(path, value)
            self.remember(assessment_id, value)
            return assessment_id, deepcopy(value)
