"""Private declarations linking agents to evidence; no agency or authority is inferred."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from lib import evidence_agent_provenance as mappings
from lib.candidate_workspace import CandidateWorkspace, private_directory, inventory
from lib.ci_bundle_storage import normalized_name, reserve
from lib.consumer_intake_store import atomic_json
from lib.functional_parity import git_read
from lib.portable.contracts import ROOT, canonical_digest
from lib.portable.runtime import read_json, source_digest
from lib.report_application import ReportContext
from lib.result_assessments import identity, operator_bytes
from lib.result_bytes import safe_bytes, strict_json
from lib.result_snapshot_store import explicit_time
from lib.v2_boundary import safe_source

MAX_RECORD = 4 * 1024**2
MAX_SOURCE = 16 * 1024**2
SCOPES = ('committed', 'private', 'all')
RECORD_PREFIX = 'status/evidence-agent-provenance/'
INDEX_PATH = 'status/evidence-agent-provenance-index.json'
CHECK_STDOUT = 'generated/reports/evidence-agent-provenance-validation.stdout.txt'
CHECK_STDERR = 'generated/reports/evidence-agent-provenance-validation.stderr.txt'
CONTEXT = '.provenance/context.json'
SOURCES = '.provenance/sources.json'
RULES = 'schemas/evidence-agent-provenance.schema.json'
FLAGS = {'official_acceptance': False, 'production_approval': False, 'risk_acceptance': False,
    'authority_transferred': False, 'operating_acceptance_inherited': False, 'published': False,
    'agent_execution_verified': False, 'human_approval_verified': False, 'subject_authenticity_verified': False}


def wire(value):
    return (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()


def put(root, name, raw):
    path = safe_source(root, name); path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    path.write_bytes(raw); path.chmod(0o600)


def metadata_input(raw, at):
    value = strict_json(raw)
    try:
        Draft202012Validator(read_json(ROOT / 'schemas/axiom-v2-provenance-metadata.schema.json'),
                             format_checker=FormatChecker()).validate(value)
        Draft202012Validator({'type': 'string', 'format': 'date-time', 'maxLength': 128},
                             format_checker=FormatChecker()).validate(at)
    except ValidationError:
        raise ValueError('invalid_provenance_metadata') from None
    explicit_time(at); normalized_name(value['evidence']['source_file'])
    return value


class ProvenanceWorkspace:
    def __init__(self, instance_root, settings, name):
        self.instance = Path(instance_root).resolve(); self.settings = settings
        private_directory(self.instance / 'state')
        domain = private_directory(self.instance / 'state/provenance'); private_directory(domain / 'state')
        self.workspace = CandidateWorkspace(domain, name, node_id=settings['node_id'])
        self.binding = {'node_id': settings['node_id'], 'runtime_source_digest': source_digest(),
                        'source_revision': git_read(ROOT, 'rev-parse', 'HEAD').decode().strip()}
        self.rule_hash = hashlib.sha256(safe_bytes(ROOT / RULES)).hexdigest()

    def marker(self, root):
        value = strict_json(safe_bytes(safe_source(root, CONTEXT), limit=MAX_RECORD))
        try:
            Draft202012Validator(read_json(ROOT / 'schemas/axiom-v2-provenance-context.schema.json')).validate(value)
        except ValidationError:
            raise ValueError('invalid_provenance_workspace_contract') from None
        if any(value.get(key) != expected for key, expected in self.binding.items()) or value['rules_sha256'] != self.rule_hash:
            raise ValueError('provenance_workspace_binding_changed')
        if hashlib.sha256(safe_bytes(safe_source(root, RULES))).hexdigest() != self.rule_hash:
            raise ValueError('provenance_rule_snapshot_changed')
        if source_digest() != self.binding['runtime_source_digest'] or git_read(ROOT, 'rev-parse', 'HEAD').decode().strip() != self.binding['source_revision']:
            raise ValueError('provenance_product_changed')
        self.source_map(root)
        return value

    def source_map(self, root):
        value = strict_json(safe_bytes(safe_source(root, SOURCES), limit=MAX_RECORD))
        if not isinstance(value, dict): raise ValueError('invalid_provenance_source_map')
        for label, row in value.items():
            normalized_name(label)
            if (not isinstance(row, dict) or set(row) != {'path', 'sha256', 'bytes'}
                    or row['path'] != '.provenance/sources/' + canonical_digest({'label': label, 'sha256': row['sha256']}) + '.json'
                    or type(row['bytes']) is not int or not 0 <= row['bytes'] <= MAX_SOURCE):
                raise ValueError('invalid_provenance_source_binding')
            raw = safe_bytes(safe_source(root, row['path']), limit=MAX_SOURCE)
            if len(raw) != row['bytes'] or hashlib.sha256(raw).hexdigest() != row['sha256']:
                raise ValueError('provenance_source_changed')
            if not isinstance(strict_json(raw), dict): raise ValueError('provenance_source_object_required')
        return value

    def bind_source(self, root, label, raw):
        normalized_name(label)
        if len(raw) > MAX_SOURCE or not isinstance(strict_json(raw), dict): raise ValueError('provenance_source_object_required')
        sources = self.source_map(root); sha = hashlib.sha256(raw).hexdigest()
        if label in sources:
            if sources[label]['sha256'] != sha: raise ValueError('provenance_source_label_conflict')
            return sources[label]
        name = '.provenance/sources/' + canonical_digest({'label': label, 'sha256': sha}) + '.json'
        put(root, name, raw); sources[label] = {'path': name, 'sha256': sha, 'bytes': len(raw)}
        if len(wire(sources)) > MAX_RECORD: raise ValueError('provenance_source_map_budget')
        put(root, SOURCES, wire(sources))
        return sources[label]

    def resolver(self, root):
        sources = self.source_map(root)
        def resolve(label):
            row = sources.get(label)
            return strict_json(safe_bytes(safe_source(root, row['path']), limit=MAX_SOURCE)) if row else None
        return resolve

    def initialize(self):
        report = ReportContext(self.instance, self.settings); data, manifest = report.source_data()
        selected = sorted(name for name in manifest['files'] if name.startswith(RECORD_PREFIX) and name.endswith('.json'))
        with self.workspace.lock():
            if (self.workspace.root / 'current.json').exists() or (self.workspace.root / 'current.json').is_symlink():
                raise ValueError('fresh_provenance_workspace_required')
            with tempfile.TemporaryDirectory(prefix='staged-provenance-', dir=self.workspace.root) as temporary:
                staged = Path(temporary) / 'data'; staged.mkdir(mode=0o700)
                put(staged, RULES, safe_bytes(ROOT / RULES)); put(staged, SOURCES, b'{}\n')
                for label in selected:
                    raw = safe_bytes(safe_source(data, label), limit=MAX_SOURCE); put(staged, label, raw)
                    try: value = strict_json(raw)
                    except ValueError: continue
                    evidence = value.get('evidence', {}) if isinstance(value, dict) else None
                    source = evidence.get('source_file') if isinstance(evidence, dict) else None
                    if not source: continue
                    try:
                        normalized_name(source); row = manifest['membership'].get(source)
                        if row is None or row['bytes'] > MAX_SOURCE: continue
                        source_raw = git_read(ROOT, 'cat-file', 'blob', row['git_blob'])
                        if len(source_raw) != row['bytes']: raise ValueError('provenance_seed_source_changed')
                        if isinstance(strict_json(source_raw), dict): self.bind_source(staged, source, source_raw)
                    except (ValueError, TypeError):
                        # Unknown/unreadable historical references stay visible to
                        # the compatibility check; never read beyond Git membership.
                        continue
                marker = {'schema_version': 1, 'kind': 'declared-evidence-agent-associations', **self.binding,
                    'rules_sha256': self.rule_hash, 'source_input_id': canonical_digest(manifest),
                    'seed_record_paths': selected, 'evidence_trust': 'unverified', **FLAGS}
                put(staged, CONTEXT, wire(marker)); self.marker(staged)
                return self.workspace.commit(staged)

    def record_paths(self, root, scope):
        if scope not in SCOPES: raise ValueError('unsupported_provenance_scope')
        marker = self.marker(root); seeds = set(marker['seed_record_paths'])
        paths = sorted(path.relative_to(root).as_posix() for path in (root / RECORD_PREFIX).rglob('*.json') if path.is_file())
        if any(name not in paths for name in seeds): raise ValueError('committed_provenance_record_missing')
        selected = [name for name in paths if scope == 'all' or ((name in seeds) == (scope == 'committed'))]
        return selected

    def records(self, root, scope):
        return [(name, strict_json(safe_bytes(safe_source(root, name), limit=MAX_RECORD)))
                for name in self.record_paths(root, scope)]

    def record(self, metadata_raw, source_raw, at):
        if len(metadata_raw) > MAX_RECORD: raise ValueError('provenance_metadata_budget')
        metadata = metadata_input(metadata_raw, at); incoming = mappings.build_record(metadata, at)
        if len(wire(incoming)) > MAX_RECORD: raise ValueError('provenance_record_budget')
        def operation(root):
            self.marker(root)
            self.bind_source(root, incoming['evidence']['source_file'], source_raw)
            decision = mappings.write_record(root, incoming)
            schema = strict_json(safe_bytes(root / RULES))
            errors = mappings.validate_record(incoming, schema, decision['attempted_path'], self.resolver(root))
            receipt = {'kind': 'declared-association-record', 'incoming_record': incoming,
                'record_path': decision['record_path'], 'attempted_path': decision['attempted_path'],
                'outcome': decision['outcome'], 'conflict_path': decision['conflict_path'],
                'incoming_payload_sha256': mappings.legacy_digest(incoming), 'validation_errors': errors,
                'evidence_trust': 'unverified', **FLAGS}
            put(root, '.provenance/last-record.json', wire(receipt))
            return {**receipt, 'write_decision': decision['write_decision']}
        current, _ = self.workspace.current()
        reserve(self.workspace.root, sum((current / name).stat().st_size for name in inventory(current)) + len(source_raw) + MAX_RECORD)
        return self.workspace.execute(operation, write=True)

    def import_record(self, name, record_raw, source_raw, at):
        explicit_time(at); normalized_name(name)
        if (not name.endswith('.json') or len(name.encode()) > 4096
                or any(len(part.encode()) > 255 for part in Path(name).parts)):
            raise ValueError('invalid_provenance_import_path')
        if len(record_raw) > MAX_RECORD: raise ValueError('provenance_record_budget')
        try: record = strict_json(record_raw)
        except ValueError: record = None
        label = RECORD_PREFIX + name
        def operation(root):
            from lib.source_snapshot_proof import portable_source_names
            self.marker(root)
            portable_source_names([*(p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()), label])
            source_label = record.get('evidence', {}).get('source_file') if isinstance(record, dict) and isinstance(record.get('evidence', {}), dict) else None
            if source_raw is not None:
                if not isinstance(source_label, str) or not source_label: raise ValueError('provenance_source_label_required')
                self.bind_source(root, source_label, source_raw)
            target = safe_source(root, label)
            if target.exists() and safe_bytes(target, limit=MAX_RECORD) != record_raw:
                raise ValueError('immutable_provenance_import_conflict')
            put(root, label, record_raw)
            errors = mappings.validation_raw_output([(label, record_raw)], strict_json(safe_bytes(root / RULES)), self.resolver(root))['errors']
            receipt = {'kind': 'declared-association-import', 'record_path': label, 'at': at,
                'record_sha256': hashlib.sha256(record_raw).hexdigest(), 'validation_errors': errors,
                'evidence_trust': 'unverified', **FLAGS}
            put(root, '.provenance/last-import.json', wire(receipt))
            return receipt
        current, _ = self.workspace.current()
        reserve(self.workspace.root, sum((current / name).stat().st_size for name in inventory(current)) +
                len(source_raw or b'') + len(record_raw) + MAX_RECORD)
        return self.workspace.execute(operation, write=True)

    def report(self, kind, scope, at):
        explicit_time(at)
        if kind not in ('index', 'check'): raise ValueError('unsupported_provenance_report')
        def operation(root):
            paths = self.record_paths(root, scope)
            raw_rows = [(name, safe_bytes(root / name, limit=MAX_RECORD)) for name in paths]
            selected = {name: hashlib.sha256(raw).hexdigest() for name, raw in raw_rows}
            if kind == 'index':
                files = {INDEX_PATH: wire(mappings.build_index([strict_json(raw) for _, raw in raw_rows], at))}
                original_exit = 0
            else:
                result = mappings.validation_raw_output(raw_rows, strict_json(safe_bytes(root / RULES)), self.resolver(root))
                files = {CHECK_STDOUT: result['stdout'].encode(), CHECK_STDERR: result['stderr'].encode()}
                original_exit = result['original_exit']
            if any(len(raw) > MAX_SOURCE for raw in files.values()): raise ValueError('provenance_report_budget')
            reserve(self.workspace.root, sum(map(len, files.values())) + MAX_RECORD)
            for name, raw in files.items(): put(root, name, raw)
            receipt = {'kind': kind, 'scope': scope, 'at': at, 'selected_records': selected,
                'files': {name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()},
                'original_exit': original_exit, 'rules_sha256': self.rule_hash,
                'evidence_trust': 'unverified', **FLAGS}
            if len(wire(receipt)) > MAX_RECORD: raise ValueError('provenance_report_record_budget')
            put(root, '.provenance/' + kind + '-receipt.json', wire(receipt))
            return receipt
        current, _ = self.workspace.current()
        reserve(self.workspace.root, sum((current / name).stat().st_size for name in inventory(current)) + MAX_RECORD)
        return self.workspace.execute(operation, write=True)

    def inspect(self, generation=None):
        if generation is None: root, pointer = self.workspace.current(); generation = pointer['generation']
        else:
            generation = identity(generation); root = self.workspace.generations / generation
            if canonical_digest(inventory(root)) != generation: raise ValueError('provenance_generation_changed')
        marker = self.marker(root); states = {}
        for kind in ('index', 'check'):
            path = root / ('.provenance/' + kind + '-receipt.json')
            if not path.is_file(): states[kind] = 'not_generated'; continue
            receipt = strict_json(safe_bytes(path, limit=MAX_RECORD))
            if receipt['kind'] != kind or receipt['rules_sha256'] != self.rule_hash or any(receipt.get(k) is not False for k in FLAGS):
                raise ValueError('provenance_report_receipt_changed')
            explicit_time(receipt['at'])
            selected = receipt['selected_records']; rows = []
            for name, sha in sorted(selected.items()):
                if not name.startswith(RECORD_PREFIX) or not name.endswith('.json'): raise ValueError('invalid_provenance_record_reference')
                raw = safe_bytes(safe_source(root, name), limit=MAX_RECORD)
                if hashlib.sha256(raw).hexdigest() != sha: raise ValueError('provenance_report_input_changed')
                rows.append((name, raw))
            if kind == 'index':
                expected = {INDEX_PATH: wire(mappings.build_index([strict_json(raw) for _, raw in rows], receipt['at']))}
                original_exit = 0
            else:
                result = mappings.validation_raw_output(rows, strict_json(safe_bytes(root / RULES)), self.resolver(root))
                expected = {CHECK_STDOUT: result['stdout'].encode(), CHECK_STDERR: result['stderr'].encode()}
                original_exit = result['original_exit']
            if receipt['original_exit'] != original_exit or receipt['files'] != {n: hashlib.sha256(raw).hexdigest() for n, raw in expected.items()}:
                raise ValueError('provenance_report_differs')
            for name, raw in expected.items():
                if safe_bytes(safe_source(root, name), limit=MAX_SOURCE) != raw: raise ValueError('provenance_report_output_changed')
            current = {name: hashlib.sha256(safe_bytes(root / name, limit=MAX_RECORD)).hexdigest() for name in self.record_paths(root, receipt['scope'])}
            states[kind] = 'current' if selected == current else 'stale'
        last = root / '.provenance/last-record.json'
        if last.is_file():
            value = strict_json(safe_bytes(last, limit=MAX_RECORD)); incoming = value['incoming_record']
            if (value.get('kind') != 'declared-association-record' or value.get('outcome') not in ('recorded', 'conflict')
                    or value.get('evidence_trust') != 'unverified'
                    or not value.get('record_path', '').startswith(RECORD_PREFIX)
                    or value['incoming_payload_sha256'] != mappings.legacy_digest(incoming)
                    or any(value.get(k) is not False for k in FLAGS)):
                raise ValueError('provenance_record_receipt_changed')
            errors = mappings.validate_record(incoming, strict_json(safe_bytes(root / RULES)), value['attempted_path'], self.resolver(root))
            if errors != value['validation_errors']: raise ValueError('provenance_record_validation_changed')
            target = strict_json(safe_bytes(safe_source(root, value['record_path']), limit=MAX_RECORD))
            if target['provenance_id'] != incoming['provenance_id']: raise ValueError('provenance_record_identity_changed')
            if value['outcome'] == 'recorded' and target != incoming: raise ValueError('provenance_record_wire_changed')
            if value['outcome'] == 'conflict':
                conflict = strict_json(safe_bytes(safe_source(root, value['conflict_path']), limit=MAX_RECORD))
                if conflict != mappings.conflict_wire(value['record_path'], target, incoming):
                    raise ValueError('provenance_conflict_changed')
        imported = root / '.provenance/last-import.json'
        if imported.is_file():
            value = strict_json(safe_bytes(imported, limit=MAX_RECORD)); label = value['record_path']
            if (value.get('kind') != 'declared-association-import' or value.get('evidence_trust') != 'unverified'
                    or not label.startswith(RECORD_PREFIX) or not label.endswith('.json')
                    or any(value.get(k) is not False for k in FLAGS)):
                raise ValueError('provenance_import_receipt_changed')
            raw = safe_bytes(safe_source(root, label), limit=MAX_RECORD)
            if hashlib.sha256(raw).hexdigest() != value['record_sha256']:
                raise ValueError('provenance_import_record_changed')
            errors = mappings.validation_raw_output([(label, raw)], strict_json(safe_bytes(root / RULES)), self.resolver(root))['errors']
            if errors != value['validation_errors']: raise ValueError('provenance_import_validation_changed')
        return {'generation': generation, 'data_directory': str(root), 'reports': states,
            'declared_record_count': len(self.record_paths(root, 'all')), 'evidence_trust': 'unverified', **FLAGS}


def run(arguments, instance_root, settings):
    parser = argparse.ArgumentParser(prog='axiom-v2 provenance', allow_abbrev=False)
    parser.add_argument('--workspace', required=True)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('init'); record = commands.add_parser('record')
    record.add_argument('--metadata', type=Path, required=True); record.add_argument('--source', type=Path, required=True)
    record.add_argument('--at', required=True); record.add_argument('--fail-on-findings', action='store_true')
    for kind in ('index', 'check'):
        command = commands.add_parser(kind); command.add_argument('--scope', choices=SCOPES, required=True)
        command.add_argument('--at', required=True); command.add_argument('--fail-on-findings', action='store_true')
    imported = commands.add_parser('import-record'); imported.add_argument('--name', required=True)
    imported.add_argument('--record', type=Path, required=True); imported.add_argument('--source', type=Path)
    imported.add_argument('--at', required=True); imported.add_argument('--fail-on-findings', action='store_true')
    inspect = commands.add_parser('inspect'); inspect.add_argument('--generation')
    args = parser.parse_args(arguments); workspace = ProvenanceWorkspace(instance_root, settings, args.workspace)
    if args.command == 'init':
        pointer = workspace.initialize(); print(json.dumps({**pointer, **FLAGS, 'evidence_trust': 'unverified'}, sort_keys=True)); return 0
    if args.command == 'inspect': print(json.dumps(workspace.inspect(args.generation), sort_keys=True)); return 0
    if args.command == 'import-record':
        pointer, result = workspace.import_record(args.name, operator_bytes(args.record),
            operator_bytes(args.source, limit=MAX_SOURCE) if args.source else None, args.at)
        findings = bool(result['validation_errors'])
    elif args.command == 'record':
        pointer, result = workspace.record(operator_bytes(args.metadata), operator_bytes(args.source, limit=MAX_SOURCE), args.at)
        findings = result['outcome'] == 'conflict' or bool(result['validation_errors'])
    else:
        pointer, result = workspace.report(args.command, args.scope, args.at); findings = bool(result['original_exit'])
    print(json.dumps({'generation': pointer['generation'], 'data_directory': str(workspace.workspace.generations / pointer['generation']),
        'result': result, 'finding_exit_requested': args.fail_on_findings, **FLAGS}, sort_keys=True))
    return 1 if args.fail_on_findings and findings else 0
