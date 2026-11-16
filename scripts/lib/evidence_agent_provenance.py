"""Original report-only agent/evidence association data, not proof of agency."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

from jsonschema import Draft202012Validator
from lib.report_data import report_time
from lib.result_snapshot_store import explicit_time


def legacy_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def _legacy_record(args) -> dict:
    recorded_at = args.recorded_at
    identity = {
        "repository_id": args.repository_id,
        "evidence_type": args.evidence_type,
        "subject_id": args.subject_id,
        "subject_digest": args.subject_digest,
        "agent_id": args.agent_id,
        "dispatch_id": args.dispatch_id,
        "involvement": args.involvement,
    }
    provenance_id = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {
        "schema_version": "1.0.0",
        "record_type": "evidence-agent-provenance",
        "provenance_id": provenance_id,
        "enforcement": "report_only",
        "recorded_at": recorded_at,
        "evidence": {
            "repository_id": args.repository_id,
            "evidence_type": args.evidence_type,
            "subject_id": args.subject_id,
            "subject_digest": args.subject_digest,
            "source_file": args.source_file,
        },
        "agent": {
            "id": args.agent_id,
            "role_version": args.role_version,
            **({"skill": args.skill} if args.skill else {}),
            **({"provider": args.provider} if args.provider else {}),
            **({"model": args.model} if args.model else {}),
        },
        "involvement": args.involvement,
        "dispatch": {
            "id": args.dispatch_id,
            "run_type": args.run_type,
            "source": args.dispatch_source,
            **({"timestamp": args.dispatch_timestamp} if args.dispatch_timestamp else {}),
        },
        **({"notes": args.notes} if args.notes else {}),
    }

def build_index(records, at):
    records = deepcopy(records)
    records.sort(key=lambda item: (item.get('recorded_at', ''), item.get('provenance_id', '')))
    payload = {'schema_version': '1.0.0', 'generated_at': report_time(at), 'summary': {'record_count': len(records), 'agent_counts': dict(sorted(Counter((item.get('agent', {}).get('id', 'unknown') for item in records)).items())), 'involvement_counts': dict(sorted(Counter((item.get('involvement', 'unknown') for item in records)).items()))}, 'records': records}
    return payload


def load_subject_digest(payload: dict, subject_id: str) -> str | None:
    candidates = [
        payload.get("trust", {}).get("capture", {}).get("subjects", []),
        payload.get("capture", {}).get("subjects", []),
        payload.get("subjects", []),
    ]
    for subjects in candidates:
        for subject in subjects:
            if subject.get("id") == subject_id:
                return subject.get("digest")
    return None


def build_record(metadata, at):
    explicit_time(at)
    evidence, agent, dispatch = metadata['evidence'], metadata['agent'], metadata['dispatch']
    return _legacy_record(SimpleNamespace(repository_id=evidence['repository_id'],
        evidence_type=evidence['evidence_type'], subject_id=evidence['subject_id'],
        subject_digest=evidence['subject_digest'], source_file=evidence['source_file'],
        agent_id=agent['id'], role_version=agent.get('role_version', '1.0.0'),
        skill=agent.get('skill', ''), provider=agent.get('provider', ''), model=agent.get('model', ''),
        involvement=metadata['involvement'], dispatch_id=dispatch['id'],
        run_type=dispatch.get('run_type', 'manual'), dispatch_source=dispatch['source'],
        dispatch_timestamp=dispatch.get('timestamp', ''), recorded_at=at, notes=metadata.get('notes', '')))


def validate_record(record, schema, record_label, resolve_source):
    errors = [f'{record_label}: {error.message}' for error in Draft202012Validator(schema).iter_errors(record)]
    if not isinstance(record.get('evidence', {}), dict): return errors
    source_file = record.get('evidence', {}).get('source_file')
    if not source_file or not isinstance(source_file, str): return errors
    source = resolve_source(source_file)
    if source is None:
        return [*errors, f'{record_label}: evidence source file does not exist: {source_file}']
    try: actual = load_subject_digest(source, record.get('evidence', {}).get('subject_id', ''))
    except (AttributeError, TypeError):
        return [*errors, f'{record_label}: evidence source file has invalid subject structure: {source_file}']
    if actual is None:
        errors.append(f"{record_label}: subject is not present in source file: {record.get('evidence', {}).get('subject_id', 'unknown')}")
    elif actual != record.get('evidence', {}).get('subject_digest'):
        errors.append(f'{record_label}: subject digest does not match source file')
    return errors


def _validation_result(errors):
    return {'errors': errors, 'original_exit': 1 if errors else 0,
        'stdout': '' if errors else 'Evidence agent provenance validation passed\n',
        'stderr': ('Evidence agent provenance validation failed\n' + '\n'.join(errors) + '\n') if errors else '',
        'agent_execution_verified': False, 'human_approval_verified': False,
        'subject_authenticity_verified': False}


def validation_output(rows, schema, resolve_source):
    errors = []
    for label, record in rows: errors.extend(validate_record(record, schema, label, resolve_source))
    return _validation_result(errors)


def validation_raw_output(rows, schema, resolve_source):
    from lib.result_bytes import strict_json
    errors = []
    for label, raw in rows:
        try: record = strict_json(raw.decode('utf-8'))
        except (ValueError, UnicodeError) as error:
            errors.append(f'{label}: cannot read JSON: {error}')
            continue
        errors.extend(validate_record(record, schema, label, resolve_source))
    return _validation_result(errors)


def conflict_wire(target_label, existing, incoming):
    return {'schema_version': '1.0.0', 'conflict_type': 'append_only_snapshot_conflict',
        'enforcement': 'report_only', 'detected_at': incoming['recorded_at'], 'target_path': target_label,
        'existing_payload_sha256': legacy_digest(existing), 'incoming_payload_sha256': legacy_digest(incoming),
        'existing_evidence_identity': {'provenance_id': incoming['provenance_id']},
        'incoming_evidence_identity': {'provenance_id': incoming['provenance_id']}}


def write_record(root, payload):
    """Original append-only record/conflict wires inside one explicit data root."""
    from pathlib import Path
    from lib.identifiers import slugify_repository, sanitize_timestamp
    from lib.source_snapshot_proof import portable_source_names
    root = Path(root)
    label = 'status/evidence-agent-provenance/' + slugify_repository(payload['evidence']['repository_id']) + '/' + \
            sanitize_timestamp(payload['recorded_at']) + '-' + payload['provenance_id'][:12] + '.json'
    parts = Path(label).parts
    if any(len(p.encode()) > 255 for p in parts) or len(label.encode()) > 4096:
        raise ValueError('provenance_record_path_budget')
    existing_names = [p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()]
    portable_source_names([*existing_names, label])
    path = root / label; path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    for existing_path in sorted(path.parent.glob('*.json')):
        try: existing = json.loads(existing_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError): continue
        if not isinstance(existing, dict) or existing.get('provenance_id') != payload['provenance_id']: continue
        if legacy_digest(existing) == legacy_digest(payload):
            return {'record_path': existing_path.relative_to(root).as_posix(), 'attempted_path': label,
                    'outcome': 'recorded', 'write_decision': 'idempotent', 'conflict_path': None}
        conflict_label = 'status/intake-conflicts/evidence-agent-provenance/' + path.stem + '-conflict-' + legacy_digest(payload)[:12] + '.json'
        portable_source_names([*existing_names, label, conflict_label])
        conflict = root / conflict_label
        wire = conflict_wire(existing_path.relative_to(root).as_posix(), existing, payload)
        conflict.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        if not conflict.exists():
            with conflict.open('x', encoding='utf-8') as output: output.write(json.dumps(wire, indent=2) + '\n')
        elif json.loads(conflict.read_text()) != wire: raise ValueError('immutable_provenance_conflict_changed')
        return {'record_path': existing_path.relative_to(root).as_posix(), 'attempted_path': label,
                'outcome': 'conflict', 'write_decision': 'conflict', 'conflict_path': conflict_label}
    with path.open('x', encoding='utf-8') as output: output.write(json.dumps(payload, indent=2) + '\n')
    return {'record_path': label, 'attempted_path': label, 'outcome': 'recorded',
            'write_decision': 'created', 'conflict_path': None}
