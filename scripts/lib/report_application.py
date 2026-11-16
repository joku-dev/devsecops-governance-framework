"""Finite private reporting from committed product data, with exact replay."""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import tempfile

from jsonschema import Draft202012Validator, FormatChecker, ValidationError
import yaml

from lib import report_outputs, report_sources
from lib.candidate_workspace import private_directory
from lib.ci_bundle_storage import reserve
from lib.consumer_intake_store import atomic_json
from lib.functional_parity import git_read
from lib.portable.contracts import ROOT, canonical_digest
from lib.portable.runtime import read_json, source_digest
from lib.result_assessments import identity
from lib.result_bytes import safe_bytes, strict_json
from lib.result_snapshot_store import explicit_time
from lib.supplement_application import write_lock
from lib.v2_boundary import safe_source

MAX_RECORD = 4 * 1024**2
MAX_OUTPUT = 64 * 1024**2
MAX_TOTAL = 128 * 1024**2
MAX_FILES = 32


def file_descriptors(files):
    if (not files or len(files) > MAX_FILES or any(len(raw) > MAX_OUTPUT for raw in files.values())
            or sum(map(len, files.values())) > MAX_TOTAL):
        raise ValueError('derived_report_output_budget_exhausted')
    return {name: {'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)}
            for name, raw in files.items()}


class ReportContext:
    def __init__(self, instance_root, settings):
        self.instance_root = Path(instance_root).resolve()
        private_directory(self.instance_root / 'state')
        self.root = private_directory(self.instance_root / 'state/reports')
        self.sources = private_directory(self.root / 'sources')
        self.artifacts = private_directory(self.root / 'artifacts')
        self.assessments = private_directory(self.root / 'assessments')
        self.binding = {'node_id': settings['node_id'], 'runtime_source_digest': source_digest(),
            'source_revision': git_read(ROOT, 'rev-parse', 'HEAD').decode().strip()}
        self.clean = not bool(git_read(ROOT, 'status', '--porcelain', '--untracked-files=all').strip())

    def assert_current(self):
        if (self.binding['runtime_source_digest'] != source_digest()
                or self.binding['source_revision'] != git_read(ROOT, 'rev-parse', 'HEAD').decode().strip()):
            raise ValueError('report_product_changed_during_operation')

    def source_data(self):
        revision = self.binding['source_revision']; target = self.sources / revision
        if target.is_symlink(): raise ValueError('unsafe_report_source_cache')
        if not target.exists():
            with tempfile.TemporaryDirectory(prefix='.incoming-sources-', dir=self.sources) as temporary:
                staged = Path(temporary) / 'snapshot'
                report_sources.capture(ROOT, revision, staged)
                self.assert_current()
                with write_lock(self.root):
                    if target.is_symlink(): raise ValueError('unsafe_report_source_cache')
                    if not target.exists(): os.rename(staged, target)
        manifest = report_sources.verify(ROOT, revision, target)
        return target / 'data', manifest

    def validate(self, value):
        try:
            Draft202012Validator(read_json(ROOT / 'schemas/axiom-v2-report-assessment.schema.json'),
                                 format_checker=FormatChecker()).validate(value)
        except ValidationError:
            raise ValueError('invalid_report_assessment_contract') from None
        if any(value[key] != expected for key, expected in self.binding.items()):
            raise ValueError('report_node_runtime_or_source_changed')
        explicit_time(value['assessed_at'])
        if len((json.dumps(value, sort_keys=True, indent=2) + '\n').encode()) > MAX_RECORD:
            raise ValueError('derived_report_record_budget_exhausted')

    def create(self, kind, at):
        explicit_time(at)
        data, manifest = self.source_data()
        files = report_outputs.build(data, kind, membership=manifest['membership'], at=at)
        descriptors = file_descriptors(files)
        value = {'schema_version': 1, 'kind': 'committed-product-data-reports', **self.binding,
            'source_worktree_clean': self.clean, 'report_kind': kind, 'assessed_at': at,
            'input_id': canonical_digest(manifest), 'input_tree': manifest['tree'], 'files': descriptors,
            'source_scope': report_sources.SOURCE_SCOPE, 'working_tree_used': False,
            'mode': 'report-only', 'official_acceptance': False, 'production_approval': False,
            'risk_acceptance': False, 'authority_transferred': False, 'operating_acceptance_inherited': False,
            'provider_invoked': False, 'published': False}
        self.validate(value); assessment_id = canonical_digest(value)
        reserve(self.root, sum(map(len, files.values())) + MAX_RECORD)
        with tempfile.TemporaryDirectory(prefix='.incoming-reports-', dir=self.artifacts) as temporary:
            staged = Path(temporary) / 'data'; staged.mkdir(mode=0o700)
            for name, raw in files.items():
                path = safe_source(staged, name); path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                path.write_bytes(raw); path.chmod(0o600)
            report_sources.verify(ROOT, self.binding['source_revision'], data.parent)
            self.assert_current()
            with write_lock(self.root):
                target = self.artifacts / assessment_id
                record = self.assessments / (assessment_id + '.json')
                if target.is_symlink() or record.is_symlink(): raise ValueError('unsafe_report_store')
                if record.exists():
                    if strict_json(safe_bytes(record, limit=MAX_RECORD)) != value:
                        raise ValueError('immutable_report_record_conflict')
                    self.inspect(assessment_id)
                elif target.exists():
                    raise ValueError('incomplete_report_generation_requires_recovery')
                else:
                    os.rename(staged, target); atomic_json(record, value)
        return assessment_id, deepcopy(value)

    def inspect(self, assessment_id):
        assessment_id = identity(assessment_id)
        value = strict_json(safe_bytes(self.assessments / (assessment_id + '.json'), limit=MAX_RECORD))
        if canonical_digest(value) != assessment_id: raise ValueError('derived_report_record_changed')
        self.validate(value)
        data, manifest = self.source_data()
        if canonical_digest(manifest) != value['input_id'] or manifest['tree'] != value['input_tree']:
            raise ValueError('derived_report_input_binding_changed')
        files = report_outputs.build(data, value['report_kind'], membership=manifest['membership'], at=value['assessed_at'])
        if file_descriptors(files) != value['files']: raise ValueError('derived_report_differs_from_sources')
        root = self.artifacts / assessment_id
        actual = set()
        for path in root.rglob('*'):
            if path.is_symlink(): raise ValueError('unsafe_report_artifact')
            if not path.is_dir(): actual.add(path.relative_to(root).as_posix())
            if len(actual) > MAX_FILES: raise ValueError('derived_report_output_budget_exhausted')
        if actual != set(files): raise ValueError('derived_report_artifact_membership_changed')
        for name, raw in files.items():
            if safe_bytes(safe_source(root, name), limit=MAX_OUTPUT) != raw:
                raise ValueError('derived_report_output_changed')
        self.assert_current()
        return value


def _run(arguments, instance_root, settings):
    parser = argparse.ArgumentParser(prog='axiom-v2 reports', allow_abbrev=False)
    commands = parser.add_subparsers(dest='command', required=True)
    build = commands.add_parser('build')
    build.add_argument('--kind', choices=(*report_outputs.KINDS, 'all'), required=True)
    build.add_argument('--at', required=True)
    inspect = commands.add_parser('inspect'); inspect.add_argument('--id', required=True)
    args = parser.parse_args(arguments); context = ReportContext(instance_root, settings)
    if args.command == 'build':
        assessment_id, value = context.create(args.kind, args.at)
        print(json.dumps({'assessment_id': assessment_id, 'report_kind': value['report_kind'],
            'artifact_directory': str(context.artifacts / assessment_id), 'files': value['files'],
            'source_revision': value['source_revision'], 'source_scope': value['source_scope'],
            'official_acceptance': False, 'published': False}, sort_keys=True))
    else:
        value = context.inspect(args.id)
        print(json.dumps({'assessment_id': args.id, 'assessment': value,
            'original_sources_and_complete_outputs_reverified': True,
            'native_metadata_rechecked': False}, sort_keys=True))
    return 0


def run(arguments, instance_root, settings):
    try:
        return _run(arguments, instance_root, settings)
    except yaml.YAMLError:
        raise ValueError('invalid_report_source_yaml') from None
