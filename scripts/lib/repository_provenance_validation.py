"""Original provenance-validator decisions with explicit retained inputs."""
import json
from pathlib import Path

_DEFAULT_RECORDS = object()


class RepositoryProvenanceValidation:
    def __init__(self, root, *, validator_class):
        self.root = root
        self.validator_class = validator_class
        self.schema_path = root / 'schemas/evidence-agent-provenance.schema.json'
        self.record_root = root / 'status/evidence-agent-provenance'

    @staticmethod
    def load_subject_digest(payload: dict, subject_id: str) -> str | None:
        candidates = [
            payload.get('trust', {}).get('capture', {}).get('subjects', []),
            payload.get('capture', {}).get('subjects', []),
            payload.get('subjects', []),
        ]
        for subjects in candidates:
            for subject in subjects:
                if subject.get('id') == subject_id:
                    return subject.get('digest')
        return None

    def validate_record(self, path: Path, schema: dict) -> list[str]:
        errors = []
        try:
            record = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as error:
            return [f'{path}: cannot read JSON: {error}']
        errors.extend(f'{path}: {error.message}' for error in self.validator_class(schema).iter_errors(record))
        source_file = record.get('evidence', {}).get('source_file')
        if not source_file:
            return errors
        source_path = self.root / source_file
        if not source_path.is_file():
            errors.append(f'{path}: evidence source file does not exist: {source_file}')
            return errors
        try:
            source_payload = json.loads(source_path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as error:
            errors.append(f'{path}: evidence source file is not valid JSON: {error}')
            return errors
        subject = record.get('evidence', {})
        actual_digest = self.load_subject_digest(source_payload, subject.get('subject_id', ''))
        if actual_digest is None:
            errors.append(f"{path}: subject is not present in source file: {subject.get('subject_id', 'unknown')}")
        elif actual_digest != subject.get('subject_digest'):
            errors.append(f'{path}: subject digest does not match source file')
        return errors

    def validate_records(self, root: Path=_DEFAULT_RECORDS) -> list[str]:
        if root is _DEFAULT_RECORDS:
            root = self.record_root
        schema = json.loads(self.schema_path.read_text(encoding='utf-8'))
        errors = []
        if not root.exists():
            return errors
        for path in sorted(root.rglob('*.json')):
            errors.extend(self.validate_record(path, schema))
        return errors

    def run(self):
        errors = self.validate_records()
        if errors:
            return {'returncode': 1, 'stdout': '',
                    'stderr': 'Evidence agent provenance validation failed\n' + '\n'.join(errors) + '\n'}
        return {'returncode': 0, 'stdout': 'Evidence agent provenance validation passed\n', 'stderr': ''}
