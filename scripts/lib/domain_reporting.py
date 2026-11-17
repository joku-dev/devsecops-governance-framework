"""Private original domain report files from explicit immutable diagnostic IDs.

No public intake, native evidence verification or governance authority is granted.
Input record identity, product, OPA and assessment time must match before rendering.
"""
import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from lib.candidate_workspace import private_directory
from lib.ci_bundle_storage import reserve
from lib.consumer_intake_store import atomic_json
from lib.full_evaluation import validate as validate_input
from lib.functional_parity import git_read
from lib.portable.contracts import ROOT, canonical_digest
from lib.portable.runtime import source_digest, read_json
from lib.report_application import file_descriptors, MAX_RECORD, MAX_OUTPUT, MAX_FILES
from lib.result_assessments import identity
from lib.result_bytes import safe_bytes, strict_json
from lib.result_snapshot_store import explicit_time
from lib.supplement_application import write_lock

DEFAULT_ARCHITECTURE_REF = 'ha-cpswms-architecture-governance-report.md'
DEFAULT_DEVSECOPS_REF = 'ha-cpswms-devsecops-governance-report.md'


def reference(value):
    # Descriptive labels only; never resolve, fetch or execute these strings.
    if not isinstance(value, str) or not value or len(value) > 2048 or any(ord(c) < 32 for c in value):
        raise ValueError('invalid_domain_report_reference')
    return value


def domain_files(assessment):
    report = assessment['report']; domain = assessment['domain']
    if domain == 'architecture':
        from lib.architecture_assessment import render_markdown
        markdown = render_markdown(report['target'], report['gates'], report['detailed_evidence'], report['advisories'])
    elif domain == 'devsecops-release':
        from lib.release_assessment import render_markdown
        markdown = render_markdown({'target_repository': report['target']}, report['gate']['findings'])
    elif domain == 'controls':
        from control_evaluation import render_control_evaluation_markdown
        markdown = render_control_evaluation_markdown(report)
    else:
        raise ValueError('unsupported_domain_report')
    return {domain + '.json': assessment['report_json'].encode(),
            domain + '.md': markdown.encode()}


class DomainReports:
    def __init__(self, instance_root, settings):
        self.instance = Path(instance_root).resolve(); self.settings = settings
        private_directory(self.instance / 'state')
        self.root = private_directory(self.instance / 'state/domain-reports')
        self.artifacts = private_directory(self.root / 'artifacts')
        self.assessments = private_directory(self.root / 'assessments')
        self.binding = {'node_id': settings['node_id'], 'source_revision': settings['source_revision'],
                        'runtime_source_digest': settings['runtime_source_digest']}
        self.assert_current()

    def assert_current(self):
        if (self.binding['runtime_source_digest'] != source_digest()
                or self.binding['source_revision'] != git_read(ROOT, 'rev-parse', 'HEAD').decode().strip()):
            raise ValueError('domain_report_product_changed')

    def input(self, input_id, at, domain=None):
        input_id = identity(input_id)
        value = strict_json(safe_bytes(self.instance / 'state/assessments' / (input_id + '.json'), limit=16 * 1024**2))
        if canonical_digest(value) != input_id:
            raise ValueError('domain_report_input_changed')
        validate_input(value)
        # The immutable wire preserves original nested JSON insertion order;
        # atomic envelope storage deliberately sorts its own object keys.
        value['report'] = strict_json(value['report_json'].encode())
        if (value['source_revision'] != self.binding['source_revision']
                or value['opa_sha256'] != self.settings['opa_sha256'] or value['assessed_at'] != at
                or value['execution'] != 'complete' or (domain is not None and value['domain'] != domain)):
            raise ValueError('domain_report_input_context_mismatch')
        if value['domain'] == 'architecture':
            if any(row['status'] != ('findings' if row['findings'] else 'pass') for row in value['report']['gates']):
                raise ValueError('domain_report_gate_status_mismatch')
        return value

    def outputs(self, request):
        at = request['assessed_at']; explicit_time(at)
        if request['operation'] == 'domain':
            value = self.input(request['inputs']['assessment'], at)
            return domain_files(value)
        from lib import combined_reporting
        architecture = self.input(request['inputs']['architecture'], at, 'architecture')['report']
        devsecops = self.input(request['inputs']['devsecops'], at, 'devsecops-release')['report']
        # Reject missing identities instead of the original empty-input PASS fallthrough.
        report = combined_reporting.build(architecture, devsecops)
        refs = request['references']; reference(refs['architecture']); reference(refs['devsecops'])
        markdown = combined_reporting.render_markdown(architecture, devsecops, refs['architecture'], refs['devsecops'])
        return {'combined.json': (json.dumps(report, indent=2) + '\n').encode(), 'combined.md': markdown.encode()}

    def validate(self, value):
        try:
            Draft202012Validator(read_json(ROOT / 'schemas/axiom-v2-domain-report.schema.json'),
                                 format_checker=FormatChecker()).validate(value)
        except ValidationError:
            raise ValueError('invalid_domain_report_contract') from None
        if any(value[key] != expected for key, expected in self.binding.items()):
            raise ValueError('domain_report_binding_changed')
        if len((json.dumps(value, indent=2) + '\n').encode()) > MAX_RECORD:
            raise ValueError('domain_report_record_budget_exhausted')

    def create(self, operation, inputs, at, references=None):
        request = {'operation': operation, 'inputs': inputs, 'assessed_at': at,
                   'references': references or {}}
        # Request is checked before input paths or filenames can be interpreted.
        value = {'schema_version': 1, 'kind': 'operator-assessment-domain-reports', **self.binding,
            **request, 'source_worktree_clean': not bool(git_read(ROOT, 'status', '--porcelain', '--untracked-files=all').strip()),
            'input_origin': 'instance_operator_assessments', 'evidence_trust': 'unverified',
            'mode': 'report-only', 'official_acceptance': False, 'production_approval': False,
            'risk_acceptance': False, 'authority_transferred': False, 'operating_acceptance_inherited': False,
            'provider_invoked': False, 'published': False, 'files': {}}
        self.validate(value)
        files = self.outputs(value); value['files'] = file_descriptors(files); self.validate(value)
        report_id = canonical_digest(value); reserve(self.root, sum(map(len, files.values())) + MAX_RECORD)
        with tempfile.TemporaryDirectory(prefix='.incoming-domain-', dir=self.artifacts) as temporary:
            staged = Path(temporary) / 'files'; staged.mkdir(mode=0o700)
            for name, raw in files.items():
                path = staged / name; path.write_bytes(raw); path.chmod(0o600)
            self.assert_current()
            with write_lock(self.root):
                target = self.artifacts / report_id; record = self.assessments / (report_id + '.json')
                if target.is_symlink() or record.is_symlink(): raise ValueError('unsafe_domain_report_store')
                if record.exists():
                    if strict_json(safe_bytes(record, limit=MAX_RECORD)) != value:
                        raise ValueError('immutable_domain_report_conflict')
                    self.inspect(report_id)
                elif target.exists(): raise ValueError('incomplete_domain_report_requires_recovery')
                else:
                    os.rename(staged, target); atomic_json(record, value)
        return report_id, deepcopy(value)

    def inspect(self, report_id):
        report_id = identity(report_id)
        value = strict_json(safe_bytes(self.assessments / (report_id + '.json'), limit=MAX_RECORD))
        if canonical_digest(value) != report_id: raise ValueError('domain_report_record_changed')
        self.validate(value); files = self.outputs(value)
        if file_descriptors(files) != value['files']: raise ValueError('domain_report_derivation_changed')
        root = self.artifacts / report_id
        if root.is_symlink() or not root.is_dir(): raise ValueError('unsafe_domain_report_artifacts')
        actual = set()
        for path in root.rglob('*'):
            if path.is_symlink(): raise ValueError('unsafe_domain_report_artifacts')
            if not path.is_dir(): actual.add(path.relative_to(root).as_posix())
            if len(actual) > MAX_FILES: raise ValueError('domain_report_membership_changed')
        if actual != set(files): raise ValueError('domain_report_membership_changed')
        for name, raw in files.items():
            if safe_bytes(root / name, limit=MAX_OUTPUT) != raw: raise ValueError('domain_report_output_changed')
        self.assert_current()
        return value


def run(arguments, instance_root, settings):
    parser = argparse.ArgumentParser(prog='axiom-v2 reports', allow_abbrev=False)
    commands = parser.add_subparsers(dest='command', required=True)
    domain = commands.add_parser('domain'); domain.add_argument('--id', required=True); domain.add_argument('--at', required=True)
    pair = commands.add_parser('combine'); pair.add_argument('--architecture-id', required=True)
    pair.add_argument('--devsecops-id', required=True); pair.add_argument('--at', required=True)
    pair.add_argument('--architecture-md-ref', default=DEFAULT_ARCHITECTURE_REF)
    pair.add_argument('--devsecops-md-ref', default=DEFAULT_DEVSECOPS_REF)
    inspect = commands.add_parser('inspect-domain'); inspect.add_argument('--id', required=True)
    args = parser.parse_args(arguments); context = DomainReports(instance_root, settings)
    if args.command == 'inspect-domain':
        value = context.inspect(args.id)
        print(json.dumps({'report_id': args.id, 'report': value, 'input_records_and_complete_outputs_reverified': True,
                          'original_input_bytes_reverified': False, 'native_metadata_rechecked': False}, sort_keys=True))
    else:
        if args.command == 'domain': report_id, value = context.create('domain', {'assessment': args.id}, args.at)
        else:
            report_id, value = context.create('combined', {'architecture': args.architecture_id, 'devsecops': args.devsecops_id},
                args.at, {'architecture': args.architecture_md_ref, 'devsecops': args.devsecops_md_ref})
        print(json.dumps({'report_id': report_id, 'artifact_directory': str(context.artifacts / report_id),
            'files': value['files'], 'mode': 'report-only', 'evidence_trust': 'unverified',
            'official_acceptance': False, 'published': False}, sort_keys=True))
    return 0
