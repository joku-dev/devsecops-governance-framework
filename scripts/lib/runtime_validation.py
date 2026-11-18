"""Complete original runtime self-validation decisions over retained inert files.

Source: V1 6b557f / scripts/validate_runtime_governance.py. Native tools and
trusted report generation are explicit environment operations, never caller code.
"""
from pathlib import Path
import json
import jsonschema
import yaml

SCHEMA_CHECKS = [('architecture/quality-markers.yaml', 'schemas/quality-marker.schema.json', 'yaml'), ('architecture/guardrails.yaml', 'schemas/architecture-guardrail.schema.json', 'yaml'), ('architecture/review-gates.yaml', 'schemas/review-gate.schema.json', 'yaml'), ('architecture/arch-l1.yaml', 'schemas/architecture-level.schema.json', 'yaml'), ('architecture/arch-l2.yaml', 'schemas/architecture-level.schema.json', 'yaml'), ('architecture/arch-l3.yaml', 'schemas/architecture-level.schema.json', 'yaml'), ('architecture/arch-gov.yaml', 'schemas/architecture-level.schema.json', 'yaml'), ('policies/example-input.architecture-release-candidate.json', 'schemas/architecture-release-candidate.schema.json', 'json'), ('generated/demo/ha-cpswms-architecture-release-input.json', 'schemas/architecture-release-candidate.schema.json', 'json')]
EXPECTED_MARKERS = {f'B{i}' for i in range(1, 6)} | {f'E{i}' for i in range(0, 11)} | {f'S{i}' for i in range(0, 11)} | {f'P{i}' for i in range(0, 14)}
EXPECTED_ARCH_LEVEL_COUNTS = {'ARCH-L1': 4, 'ARCH-L2': 4, 'ARCH-L3': 3, 'ARCH-GOV': 3}

class RuntimeValidation:

    def __init__(self, environment):
        self.environment = environment
        self.root = environment.root

    def load_data(self, path: Path, kind: str):
        text = path.read_text(encoding='utf-8')
        if kind == 'json':
            return json.loads(text)
        return yaml.safe_load(text)

    def validate_schema(self, data_path: str, schema_path: str, kind: str, errors: list[str]) -> None:
        try:
            data = self.load_data(self.root / data_path, kind)
            schema = json.loads((self.root / schema_path).read_text(encoding='utf-8'))
            jsonschema.validate(data, schema)
        except Exception as exc:
            errors.append(f'{data_path} failed schema validation against {schema_path}: {exc}')

    def validate_marker_catalogue(self, errors: list[str]) -> None:
        try:
            data = yaml.safe_load((self.root / 'architecture' / 'quality-markers.yaml').read_text(encoding='utf-8'))
        except Exception as exc:
            errors.append(f'Could not load architecture/quality-markers.yaml: {exc}')
            return
        markers = data.get('markers', [])
        ids = [marker.get('id') for marker in markers]
        duplicates = sorted({marker_id for marker_id in ids if ids.count(marker_id) > 1})
        missing = sorted(EXPECTED_MARKERS - set(ids))
        unknown = sorted(set(ids) - EXPECTED_MARKERS)
        if duplicates:
            errors.append(f'Duplicate architecture marker IDs: {duplicates}')
        if missing:
            errors.append(f'Missing architecture marker IDs: {missing}')
        if unknown:
            errors.append(f'Unknown architecture marker IDs: {unknown}')

    def validate_opa_policy(self, errors: list[str]) -> None:
        if not self.environment.which('opa'):
            errors.append('OPA executable not found; cannot validate architecture release-readiness policy')
            return
        command = ['opa', 'eval', '--data', str(self.root / 'policies' / 'opa' / 'architecture_release_readiness.rego'), '--input', str(self.root / 'policies' / 'example-input.architecture-release-candidate.json'), 'data.architecture.release_readiness.deny']
        result = self.environment.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            errors.append(f'OPA evaluation failed: {result.stderr.strip() or result.stdout.strip()}')
            return
        try:
            payload = json.loads(result.stdout)
            value = payload['result'][0]['expressions'][0]['value']
        except Exception as exc:
            errors.append(f'Could not parse OPA evaluation result: {exc}')
            return
        if value:
            errors.append(f'Example architecture release candidate failed policy: {value}')
        readiness_command = ['opa', 'eval', '--data', str(self.root / 'policies' / 'opa' / 'architecture_readiness.rego'), '--input', str(self.root / 'policies' / 'example-input.architecture-release-candidate.json'), 'data.architecture.readiness.deny']
        readiness_result = self.environment.run(readiness_command, capture_output=True, text=True, check=False)
        if readiness_result.returncode != 0:
            errors.append(f'OPA architecture-readiness evaluation failed: {readiness_result.stderr.strip() or readiness_result.stdout.strip()}')
        integration_command = ['opa', 'eval', '--data', str(self.root / 'policies' / 'opa' / 'architecture_integration_readiness.rego'), '--input', str(self.root / 'policies' / 'example-input.architecture-release-candidate.json'), 'data.architecture.integration_readiness.deny']
        integration_result = self.environment.run(integration_command, capture_output=True, text=True, check=False)
        if integration_result.returncode != 0:
            errors.append(f'OPA integration-readiness evaluation failed: {integration_result.stderr.strip() or integration_result.stdout.strip()}')
        operation_command = ['opa', 'eval', '--data', str(self.root / 'policies' / 'opa' / 'architecture_operation_readiness.rego'), '--input', str(self.root / 'policies' / 'example-input.architecture-release-candidate.json'), 'data.architecture.operation_readiness.deny']
        operation_result = self.environment.run(operation_command, capture_output=True, text=True, check=False)
        if operation_result.returncode != 0:
            errors.append(f'OPA operation-readiness evaluation failed: {operation_result.stderr.strip() or operation_result.stdout.strip()}')

    def validate_generated_traceability(self, errors: list[str]) -> None:
        command = [self.environment.python, str(self.root / 'scripts' / 'generate_architecture_traceability_csv.py')]
        result = self.environment.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            errors.append(f'Architecture traceability generation failed: {result.stderr.strip() or result.stdout.strip()}')
            return
        output = self.root / 'generated' / 'csv' / 'architecture_runtime_traceability.csv'
        if not output.exists():
            errors.append('Architecture traceability CSV was not generated')

    def validate_generated_demo_report(self, errors: list[str]) -> None:
        input_path = self.root / 'generated' / 'demo' / 'ha-cpswms-architecture-release-input.json'
        if not input_path.exists():
            return
        command = [self.environment.python, str(self.root / 'scripts' / 'generate_architecture_governance_report.py'), '--input', str(input_path), '--output-json', str(self.root / 'generated' / 'demo' / 'ha-cpswms-architecture-governance-report.json'), '--output-md', str(self.root / 'generated' / 'demo' / 'ha-cpswms-architecture-governance-report.md')]
        result = self.environment.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            errors.append(f'Architecture governance report generation failed: {result.stderr.strip() or result.stdout.strip()}')

    def validate_generated_end_to_end_demo_report(self, errors: list[str]) -> None:
        architecture_report = self.root / 'generated' / 'demo' / 'ha-cpswms-architecture-governance-report.json'
        devsecops_report = self.root / 'generated' / 'demo' / 'ha-cpswms-devsecops-governance-report.json'
        if not architecture_report.exists() or not devsecops_report.exists():
            return
        command = [self.environment.python, str(self.root / 'scripts' / 'generate_end_to_end_governance_report.py'), '--architecture-json', str(architecture_report), '--devsecops-json', str(devsecops_report), '--output-json', str(self.root / 'generated' / 'demo' / 'ha-cpswms-end-to-end-governance-report.json'), '--output-md', str(self.root / 'generated' / 'demo' / 'ha-cpswms-end-to-end-governance-report.md')]
        result = self.environment.run(command, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            errors.append(f'End-to-end governance report generation failed: {result.stderr.strip() or result.stdout.strip()}')

    def validate_architecture_levels(self, errors: list[str]) -> None:
        marker_ids = {marker['id'] for marker in yaml.safe_load((self.root / 'architecture' / 'quality-markers.yaml').read_text(encoding='utf-8')).get('markers', [])}
        guardrail_ids = {guardrail['id'] for guardrail in yaml.safe_load((self.root / 'architecture' / 'guardrails.yaml').read_text(encoding='utf-8')).get('guardrails', [])}
        review_gate_ids = {gate['id'] for gate in yaml.safe_load((self.root / 'architecture' / 'review-gates.yaml').read_text(encoding='utf-8')).get('review_gates', [])}
        requirement_ids: list[str] = []
        level_counts: dict[str, int] = {}
        for path in sorted((self.root / 'architecture').glob('arch-*.yaml')):
            data = yaml.safe_load(path.read_text(encoding='utf-8'))
            level = data.get('level')
            requirements = data.get('requirements', [])
            level_counts[level] = level_counts.get(level, 0) + len(requirements)
            for requirement in requirements:
                requirement_ids.append(requirement.get('id'))
                unknown_markers = sorted(set(requirement.get('source_markers', [])) - marker_ids)
                unknown_guardrails = sorted(set(requirement.get('source_guardrails', [])) - guardrail_ids)
                unknown_review_gates = sorted(set(requirement.get('source_review_gates', [])) - review_gate_ids)
                if unknown_markers:
                    errors.append(f"{requirement.get('id')} references unknown markers: {unknown_markers}")
                if unknown_guardrails:
                    errors.append(f"{requirement.get('id')} references unknown guardrails: {unknown_guardrails}")
                if unknown_review_gates:
                    errors.append(f"{requirement.get('id')} references unknown review gates: {unknown_review_gates}")
                rule = requirement.get('policy_as_code', {}).get('rule')
                if requirement.get('policy_as_code', {}).get('candidate') and rule and (not (self.root / rule).exists()):
                    if rule.endswith('architecture_release_readiness.rego') or rule.endswith('validate_runtime_governance.py'):
                        errors.append(f"{requirement.get('id')} references missing policy rule: {rule}")
        duplicates = sorted({requirement_id for requirement_id in requirement_ids if requirement_ids.count(requirement_id) > 1})
        if duplicates:
            errors.append(f'Duplicate architecture requirement IDs: {duplicates}')
        for level, expected in EXPECTED_ARCH_LEVEL_COUNTS.items():
            actual = level_counts.get(level, 0)
            if actual != expected:
                errors.append(f'Unexpected {level} architecture requirement count: expected {expected}, got {actual}')

    def main(self) -> int:
        errors: list[str] = []
        for data_path, schema_path, kind in SCHEMA_CHECKS:
            self.validate_schema(data_path, schema_path, kind, errors)
        for schema_path in ['schemas/architecture-exception.schema.json']:
            try:
                json.loads((self.root / schema_path).read_text(encoding='utf-8'))
            except Exception as exc:
                errors.append(f'{schema_path} is not valid JSON: {exc}')
        try:
            remediation_payload = yaml.safe_load((self.root / 'architecture' / 'remediation-actions.yaml').read_text(encoding='utf-8'))
            if not remediation_payload.get('remediations'):
                errors.append('architecture/remediation-actions.yaml contains no remediations')
        except Exception as exc:
            errors.append(f'Could not load architecture/remediation-actions.yaml: {exc}')
        self.validate_marker_catalogue(errors)
        self.validate_architecture_levels(errors)
        self.validate_generated_traceability(errors)
        self.validate_generated_demo_report(errors)
        self.validate_generated_end_to_end_demo_report(errors)
        self.validate_opa_policy(errors)
        if errors:
            self.environment.print('Runtime governance validation failed:')
            for error in errors:
                self.environment.print(f'- {error}')
            return 1
        self.environment.print('Runtime governance validation passed')
        self.environment.print(f'- expected markers: {len(EXPECTED_MARKERS)}')
        self.environment.print(f'- schema checks: {len(SCHEMA_CHECKS)}')
        self.environment.print(f'- architecture requirements: {sum(EXPECTED_ARCH_LEVEL_COUNTS.values())}')
        self.environment.print('- OPA release-readiness example: passed')
        return 0
