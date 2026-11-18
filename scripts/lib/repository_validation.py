"""Original whole repository-validator decisions with explicit environment operations.

Technical reference: V1 6b557fefe295b58272d2271326576ca3a3687197.
This core never starts caller programs. Environment adapters must supply every
ordered original generator, subvalidator and native observation. An incomplete
environment must fail explicitly; it must never return synthetic success.
"""
from pathlib import Path
from collections import Counter
import hashlib
import json
import yaml
EXPECTED_COUNTS = {'L1': 16, 'L2': 14, 'L3': 11, 'GOV': 5}
SOURCE_STATUSES_ALLOWING_NO_LINEAGE = {'candidate', 'draft', 'retired'}

class RepositoryValidation:

    def __init__(self, environment):
        self.environment = environment
        self.root = environment.root
        self.model = self.root / 'model'
        self.source_document_root = self.root / 'docs/governance/source-documents'
        self.app_architecture_evidence_template_dir = self.root / 'pipeline-baseline/templates/app-architecture-evidence/.governance/architecture'

    def load_yaml(self, path: Path):
        with path.open('r', encoding='utf-8') as handle:
            return yaml.safe_load(handle)

    def load_json(self, path: Path):
        with path.open('r', encoding='utf-8') as handle:
            return json.load(handle)

    def validate_schema(self, errors, schema_path: Path, instance_path: Path):
        if self.environment.validator_class is None:
            self.environment.print(f'Warning: jsonschema is not installed; skipping schema validation for {instance_path.relative_to(self.root)}', file=self.environment.stderr)
            return
        validator = self.environment.validator_class(self.load_json(schema_path))
        instance = self.load_yaml(instance_path)
        for issue in validator.iter_errors(instance):
            location = ' -> '.join((str(part) for part in issue.absolute_path)) or '<root>'
            errors.append(f'Schema validation failed for {instance_path.relative_to(self.root)} at {location}: {issue.message}')

    def validate_typed_evidence_results(self, errors):
        results_root = self.root / 'status' / 'typed-evidence-results'
        if not results_root.exists():
            return
        trust_schema = self.load_json(self.root / 'schemas' / 'evidence-trust-record.schema.json')
        trust_validator = self.environment.validator_class(trust_schema) if self.environment.validator_class is not None else None
        for result_path in sorted(results_root.rglob('*.json')):
            self.validate_schema(errors, self.root / 'schemas' / 'typed-evidence-result.schema.json', result_path)
            if trust_validator is None:
                continue
            payload = self.load_json(result_path)
            for issue in trust_validator.iter_errors(payload.get('trust')):
                location = ' -> '.join((str(part) for part in issue.absolute_path)) or '<root>'
                errors.append(f'Trust schema validation failed for {result_path.relative_to(self.root)} at {location}: {issue.message}')

    def validate_governance_graph(self, errors):
        command = [self.environment.python, str(self.root / 'scripts' / 'generate_governance_graph.py')]
        result = self.environment.run(command, cwd=self.root, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            errors.append(f'Governance graph generation failed: {result.stderr.strip() or result.stdout.strip()}')
            return
        graph_path = self.root / 'generated' / 'graph' / 'governance-graph.json'
        if not graph_path.exists():
            errors.append('Governance graph was not generated')
            return
        self.validate_schema(errors, self.root / 'schemas' / 'governance-graph.schema.json', graph_path)
        graph = self.load_json(graph_path)
        nodes = graph.get('nodes', [])
        edges = graph.get('edges', [])
        node_ids = [node.get('id') for node in nodes]
        if len(node_ids) != len(set(node_ids)):
            errors.append('Governance graph contains duplicate node IDs')
        edge_ids = [edge.get('id') for edge in edges]
        if len(edge_ids) != len(set(edge_ids)):
            errors.append('Governance graph contains duplicate edge IDs')
        known_nodes = set(node_ids)
        dangling = [edge.get('id', 'unknown') for edge in edges if edge.get('source') not in known_nodes or edge.get('target') not in known_nodes]
        if dangling:
            errors.append(f'Governance graph contains dangling edges: {dangling[:5]}')
        summary = graph.get('summary', {})
        if summary.get('node_count') != len(nodes) or summary.get('edge_count') != len(edges):
            errors.append('Governance graph summary counts do not match graph contents')

    def validate_intake_conflicts(self, errors):
        conflicts_root = self.root / 'status' / 'intake-conflicts'
        if not conflicts_root.exists():
            return
        for conflict_path in sorted(conflicts_root.rglob('*.json')):
            self.validate_schema(errors, self.root / 'schemas' / 'intake-conflict.schema.json', conflict_path)

    def validate_intake_events(self, errors):
        events_root = self.root / 'status' / 'intake-events'
        if not events_root.exists():
            return
        for event_path in sorted(events_root.rglob('*.json')):
            self.validate_schema(errors, self.root / 'schemas' / 'intake-operation-event.schema.json', event_path)

    def validate_intake_health(self, errors):
        projection_path = self.root / 'status' / 'intake-health.json'
        if projection_path.exists():
            self.validate_schema(errors, self.root / 'schemas' / 'intake-health.schema.json', projection_path)

    def validate_multi_consumer_readiness(self, errors):
        command = [self.environment.python, str(self.root / 'scripts' / 'generate_multi_consumer_readiness.py')]
        result = self.environment.run(command, cwd=self.root, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            errors.append(f'Multi-consumer readiness generation failed: {result.stderr.strip() or result.stdout.strip()}')
            return
        report_path = self.root / 'generated' / 'reports' / 'multi-consumer-readiness.json'
        self.validate_schema(errors, self.root / 'schemas' / 'multi-consumer-readiness.schema.json', report_path)
        if not self.load_json(report_path).get('ready'):
            errors.append('Multi-consumer readiness contains failed isolation checks')

    def validate_evidence_attestation_pilot(self, errors):
        attestation_path = self.root / 'docs' / 'examples' / 'evidence-attestation.example.json'
        self.validate_schema(errors, self.root / 'schemas' / 'evidence-attestation.schema.json', attestation_path)
        self.validate_schema(errors, self.root / 'schemas' / 'evidence-trust-root-registry.schema.json', self.root / 'model' / 'evidence' / 'evidence-trust-roots.yaml')
        command = [self.environment.python, str(self.root / 'scripts' / 'verify_evidence_attestation.py'), str(attestation_path), '--output', str(self.root / 'generated' / 'reports' / 'evidence-attestation-pilot.json'), '--evaluated-at', '2026-07-17T10:01:00Z']
        result = self.environment.run(command, cwd=self.root, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            errors.append(f'Evidence attestation pilot failed: {result.stderr.strip() or result.stdout.strip()}')
            return
        report_path = self.root / 'generated' / 'reports' / 'evidence-attestation-pilot.json'
        self.validate_schema(errors, self.root / 'schemas' / 'evidence-attestation-assessment.schema.json', report_path)
        report = self.load_json(report_path)
        if report.get('status') != 'pass' or report.get('candidate_level') != 'attested':
            errors.append('Evidence attestation pilot must verify the representative signed statement')
        if report.get('enforcement') != 'report_only' or report.get('effective_level') == 'attested':
            errors.append('Evidence attestation pilot must not activate attested Trust')

    def validate_blocking_readiness(self, errors):
        self.validate_schema(errors, self.root / 'schemas' / 'blocking-readiness-model.schema.json', self.root / 'model' / 'enforcement' / 'blocking-readiness.yaml')
        command = [self.environment.python, str(self.root / 'scripts' / 'generate_blocking_readiness.py')]
        result = self.environment.run(command, cwd=self.root, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            errors.append(f'Blocking readiness generation failed: {result.stderr.strip() or result.stdout.strip()}')
            return
        report_path = self.root / 'generated' / 'reports' / 'blocking-readiness.json'
        self.validate_schema(errors, self.root / 'schemas' / 'blocking-readiness.schema.json', report_path)
        report = self.load_json(report_path)
        if report.get('enforcement_change_authorized') is not False or report.get('enforcement') != 'report_only':
            errors.append('Blocking readiness must remain a non-authorizing report-only projection')

    def validate_blocking_mode_alignment(self, errors):
        self.validate_schema(errors, self.root / 'schemas' / 'blocking-mode-alignment-model.schema.json', self.root / 'model' / 'enforcement' / 'blocking-mode-alignment.yaml')
        command = [self.environment.python, str(self.root / 'scripts' / 'generate_blocking_mode_alignment.py')]
        result = self.environment.run(command, cwd=self.root, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            errors.append(f'Blocking mode alignment generation failed: {result.stderr.strip() or result.stdout.strip()}')
            return
        report_path = self.root / 'generated' / 'reports' / 'blocking-mode-alignment.json'
        self.validate_schema(errors, self.root / 'schemas' / 'blocking-mode-alignment.schema.json', report_path)
        report = self.load_json(report_path)
        if report.get('enforcement_change_authorized') is not False or report.get('enforcement') != 'report_only':
            errors.append('Blocking mode alignment must never authorize an enforcement change')
        if report.get('alignment_status') != 'controlled':
            errors.append('Blocking mode alignment requires review before repository validation can pass')
        if report.get('summary', {}).get('unsafe_blocking', 0):
            errors.append('Blocking mode alignment contains unsafe blocking registrations')

    def validate_governance_repository_security(self, errors):
        model_path = self.model / 'controls' / 'governance-repository-security.yaml'
        report_path = self.root / 'generated' / 'reports' / 'governance-repository-security.json'
        release_policy_path = self.model / 'governance' / 'release-signing-policy.yaml'
        release_manifest_path = self.root / 'releases' / 'release-tag-integrity.json'
        self.validate_schema(errors, self.root / 'schemas' / 'governance-repository-security-model.schema.json', model_path)
        self.validate_schema(errors, self.root / 'schemas' / 'release-signing-policy.schema.json', release_policy_path)
        self.validate_schema(errors, self.root / 'schemas' / 'release-tag-integrity.schema.json', release_manifest_path)
        try:
            verify_release_integrity = self.environment.verify_release_integrity
            release_integrity = verify_release_integrity(self.root, release_policy_path)
            if not isinstance(release_integrity.get('unverified_release_tags'), list):
                errors.append('Governance release integrity did not return a reportable tag result')
        except Exception as exc:
            errors.append(f'Governance release integrity validation failed: {exc}')
        if not report_path.exists():
            errors.append('Governance repository self-security report is missing')
            return
        self.validate_schema(errors, self.root / 'schemas' / 'governance-repository-security-report.schema.json', report_path)
        report = self.load_json(report_path)
        if report.get('enforcement') != 'report_only':
            errors.append('Governance repository self-security must remain report-only')
        if report.get('enforcement_change_authorized') is not False:
            errors.append('Governance repository self-security must not authorize enforcement changes')
        if report.get('decision_boundary', {}).get('changes_repository_settings') is not False:
            errors.append('Governance repository self-security assessment must not mutate repository settings')

    def validate_replay_triage(self, errors):
        command = [self.environment.python, str(self.root / 'scripts' / 'generate_replay_triage_report.py')]
        result = self.environment.run(command, cwd=self.root, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            errors.append(f'Replay triage generation failed: {result.stderr.strip() or result.stdout.strip()}')
            return
        report_path = self.root / 'generated' / 'reports' / 'replay-triage.json'
        self.validate_schema(errors, self.root / 'schemas' / 'replay-triage.schema.json', report_path)
        report = self.load_json(report_path)
        boundary = report.get('decision_boundary', {})
        if report.get('enforcement') != 'report_only' or any(boundary.values()):
            errors.append('Replay triage must not rewrite evidence, Trust, latest selection, or enforcement')

    def validate_harmonized_requirements_candidate(self, errors, source_document_register):
        model_path = self.model / 'requirements' / 'harmonized-devsecops-requirements.yaml'
        mapping_path = self.model / 'traceability' / 'standards-to-harmonized-requirements.yaml'
        maturity_mapping_path = self.model / 'traceability' / 'harmonized-requirements-to-maturity-levels.yaml'
        report_path = self.root / 'generated' / 'reports' / 'harmonized-requirements-coverage.json'
        maturity_report_path = self.root / 'generated' / 'reports' / 'harmonized-requirements-maturity.json'
        self.validate_schema(errors, self.root / 'schemas' / 'harmonized-requirements.schema.json', model_path)
        self.validate_schema(errors, self.root / 'schemas' / 'standards-requirement-mapping.schema.json', mapping_path)
        self.validate_schema(errors, self.root / 'schemas' / 'harmonized-requirements-coverage.schema.json', report_path)
        self.validate_schema(errors, self.root / 'schemas' / 'harmonized-requirements-maturity-mapping.schema.json', maturity_mapping_path)
        self.validate_schema(errors, self.root / 'schemas' / 'harmonized-requirements-maturity-report.schema.json', maturity_report_path)
        model = self.load_yaml(model_path)
        mapping = self.load_yaml(mapping_path)
        report = self.load_json(report_path)
        maturity_mapping = self.load_yaml(maturity_mapping_path)
        maturity_report = self.load_json(maturity_report_path)
        requirements = model.get('requirements', [])
        requirement_ids = [item.get('id') for item in requirements]
        if len(requirement_ids) != len(set(requirement_ids)):
            errors.append('Harmonized requirements candidate contains duplicate IDs')
        known_requirements = set(requirement_ids)
        mapped_counts = {requirement_id: 0 for requirement_id in known_requirements}
        mapping_ids = []
        for item in mapping.get('mappings', []):
            mapping_ids.append(item.get('id'))
            for requirement_id in item.get('harmonized_requirement_ids', []):
                if requirement_id not in known_requirements:
                    errors.append(f'Candidate source mapping references unknown requirement: {requirement_id}')
                else:
                    mapped_counts[requirement_id] += 1
            forbidden_keys = {'source_text', 'original_text', 'description', 'title'} & set(item)
            if forbidden_keys:
                errors.append(f'Candidate source mapping exposes source-text fields: {sorted(forbidden_keys)}')
            if item.get('review_status') != 'human_review_required':
                errors.append(f"Candidate mapping is not held for human review: {item.get('id')}")
        if len(mapping_ids) != len(set(mapping_ids)):
            errors.append('Candidate source mapping contains duplicate mapping IDs')
        unmapped_requirements = sorted((key for key, value in mapped_counts.items() if value == 0))
        if unmapped_requirements:
            errors.append(f'Harmonized requirements have no candidate source mapping: {unmapped_requirements}')
        summary = mapping.get('summary', {})
        if summary.get('unique_source_requirements') != len(mapping.get('mappings', [])):
            errors.append('Candidate mapping summary does not match mapping count')
        if summary.get('mapped_source_requirements') != len(mapping.get('mappings', [])):
            errors.append('Candidate mapping does not report every source requirement as mapped')
        if summary.get('unmapped_source_requirements') != 0:
            errors.append('Candidate mapping contains unmapped source requirements')
        if mapping.get('public_source_text_included') is not False:
            errors.append('Candidate mapping must never include public source requirement text')
        report_summary = report.get('summary', {})
        coverage_counts = Counter((item.get('coverage', {}).get('status') for item in requirements))
        if report_summary.get('harmonized_requirements') != len(requirements):
            errors.append('Harmonized coverage report requirement count is stale')
        for status in ('covered', 'partial', 'gap'):
            if report_summary.get(status) != coverage_counts.get(status, 0):
                errors.append(f'Harmonized coverage report {status} count is stale')
        if report_summary.get('source_requirements') != len(mapping.get('mappings', [])):
            errors.append('Harmonized coverage report source count is stale')
        if any(report.get('decision_boundary', {}).values()):
            errors.append('Harmonized candidate must not authorize governance or compliance changes')
        if model.get('normative') is not False or model.get('enforcement') != 'none':
            errors.append('Harmonized requirements candidate must remain non-normative and non-enforcing')
        maturity_assignments = maturity_mapping.get('mappings', [])
        maturity_ids = [item.get('requirement_id') for item in maturity_assignments]
        if len(maturity_ids) != len(set(maturity_ids)):
            errors.append('Harmonized maturity candidate contains duplicate requirement assignments')
        if set(maturity_ids) != known_requirements:
            missing = sorted(known_requirements - set(maturity_ids))
            unknown = sorted(set(maturity_ids) - known_requirements)
            errors.append(f'Harmonized maturity assignment mismatch; missing={missing}, unknown={unknown}')
        expected_paths = {'L1': ['L1', 'L2', 'L3'], 'L2': ['L2', 'L3'], 'L3': ['L3'], 'GOV': ['GOV']}
        for item in maturity_assignments:
            requirement_id = item.get('requirement_id')
            minimum_level = item.get('minimum_level')
            if item.get('maturity_path') != expected_paths.get(minimum_level):
                errors.append(f'Harmonized maturity path is not cumulative for {requirement_id}')
            if item.get('governance_overlay') != (minimum_level == 'GOV'):
                errors.append(f'Harmonized GOV overlay is inconsistent for {requirement_id}')
            if item.get('review_status') != 'human_review_required':
                errors.append(f'Harmonized maturity assignment is not held for human review: {requirement_id}')
        if any(maturity_mapping.get('decision_boundary', {}).values()):
            errors.append('Harmonized maturity candidate must not authorize governance changes')
        maturity_items = maturity_report.get('maturity_by_requirement', [])
        if {item.get('requirement_id') for item in maturity_items} != known_requirements:
            errors.append('Harmonized maturity report requirement set is stale')
        maturity_summary = maturity_report.get('summary', {})
        if maturity_summary.get('harmonized_requirements') != len(requirements):
            errors.append('Harmonized maturity report requirement count is stale')
        minimum_counts = Counter((item.get('minimum_level') for item in maturity_assignments))
        for level in ('L1', 'L2', 'L3', 'GOV'):
            if maturity_summary.get('minimum_level_counts', {}).get(level) != minimum_counts.get(level, 0):
                errors.append(f'Harmonized maturity report minimum {level} count is stale')
            expected_cumulative = sum((level in item.get('maturity_path', []) for item in maturity_assignments))
            if maturity_summary.get('cumulative_level_counts', {}).get(level) != expected_cumulative:
                errors.append(f'Harmonized maturity report cumulative {level} count is stale')
        if maturity_summary.get('human_review_required') != len(maturity_assignments):
            errors.append('Harmonized maturity report must hold every assignment for human review')
        if any(maturity_report.get('decision_boundary', {}).values()):
            errors.append('Harmonized maturity report must not authorize governance changes')
        source_entry = next((item for item in source_document_register.get('documents', []) if item.get('id') == 'CISO-REQ-SRC-001'), None)
        if not source_entry:
            errors.append('Harmonized requirements source is not registered')
        elif source_entry.get('status') != 'candidate' or source_entry.get('derived_artifact_areas'):
            errors.append('Harmonized requirements source must remain a non-deriving candidate')

    def run_opa_check(self, errors):
        opa = self.environment.which('opa')
        if not opa:
            errors.append('OPA CLI not found on PATH.')
            return
        result = self.environment.run([opa, 'check', str(self.root / 'policies' / 'opa')], capture_output=True, text=True, check=False)
        if result.returncode != 0:
            details = result.stderr.strip() or result.stdout.strip() or 'unknown OPA error'
            errors.append(f'OPA policy validation failed: {details}')

    def validate_source_lineage_report(self, errors):
        command = [self.environment.python, str(self.root / 'scripts' / 'generate_source_lineage_report.py')]
        result = self.environment.run(command, cwd=self.root, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            errors.append(f'Source lineage report generation failed: {result.stderr.strip() or result.stdout.strip()}')
            return
        report_path = self.root / 'generated' / 'reports' / 'source-lineage-report.json'
        if not report_path.exists():
            errors.append('Source lineage report JSON was not generated')
            return
        report = self.load_json(report_path)
        if report.get('summary', {}).get('missing_derived_artifacts', 0):
            errors.append('Source lineage report contains missing derived artifacts')
        return report

    def validate_governance_change_impact_report(self, errors):
        command = [self.environment.python, str(self.root / 'scripts' / 'generate_governance_change_impact_report.py')]
        result = self.environment.run(command, cwd=self.root, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            errors.append(f'Governance change impact report generation failed: {result.stderr.strip() or result.stdout.strip()}')
            return
        report_path = self.root / 'generated' / 'reports' / 'governance-change-impact.json'
        if not report_path.exists():
            errors.append('Governance change impact report JSON was not generated')
            return
        report = self.load_json(report_path)
        registered = report.get('summary', {}).get('registered_source_documents')
        if registered != len(self.load_yaml(self.model / 'documents' / 'source-document-register.yaml').get('documents', [])):
            errors.append('Governance change impact report source document count does not match register')

    def validate_architecture_source_replacement_assessment(self, errors):
        command = [self.environment.python, str(self.root / 'scripts' / 'generate_architecture_source_replacement_assessment.py')]
        result = self.environment.run(command, cwd=self.root, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            errors.append(f'Architecture source replacement assessment generation failed: {result.stderr.strip() or result.stdout.strip()}')
            return
        report_path = self.root / 'generated' / 'reports' / 'architecture-source-replacement-assessment.json'
        if not report_path.exists():
            errors.append('Architecture source replacement assessment JSON was not generated')
            return
        report = self.load_json(report_path)
        if report.get('decision', {}).get('runtime_governance_changed') is not False:
            errors.append('Architecture source replacement assessment must not change runtime governance behavior')

    def validate_source_document_intake_status(self, errors, source_document_register):
        command = [self.environment.python, str(self.root / 'scripts' / 'generate_source_document_intake_status.py')]
        result = self.environment.run(command, cwd=self.root, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            errors.append(f'Source document intake status generation failed: {result.stderr.strip() or result.stdout.strip()}')
            return
        report_path = self.root / 'generated' / 'reports' / 'source-document-intake-status.json'
        if not report_path.exists():
            errors.append('Source document intake status JSON was not generated')
            return
        report = self.load_json(report_path)
        registered = report.get('summary', {}).get('registered_source_documents')
        if registered != len(source_document_register.get('documents', [])):
            errors.append('Source document intake status source document count does not match register')
        if report.get('decision', {}).get('runtime_governance_changed') is not False:
            errors.append('Source document intake status must not change runtime governance behavior')
        if report.get('decision', {}).get('stricter_rules_enabled') is not False:
            errors.append('Source document intake status must not enable stricter rules')
        open_items = len(report.get('open_items', []))
        if open_items != report.get('summary', {}).get('open_review_items'):
            errors.append('Source document intake status open item count does not match item list')

    def validate_source_document_intake_review_briefs(self, errors, source_document_register):
        command = [self.environment.python, str(self.root / 'scripts' / 'generate_source_document_intake_review_briefs.py')]
        result = self.environment.run(command, cwd=self.root, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            errors.append(f'Source document intake review brief generation failed: {result.stderr.strip() or result.stdout.strip()}')
            return
        report_path = self.root / 'generated' / 'reports' / 'source-document-intake-review-briefs.json'
        if not report_path.exists():
            errors.append('Source document intake review briefs JSON was not generated')
            return
        report = self.load_json(report_path)
        if report.get('decision', {}).get('autonomous_decisions_enabled') is not False:
            errors.append('Source document intake review briefs must not enable autonomous decisions')
        if report.get('decision', {}).get('runtime_governance_changed') is not False:
            errors.append('Source document intake review briefs must not change runtime governance behavior')
        if report.get('decision', {}).get('stricter_rules_enabled') is not False:
            errors.append('Source document intake review briefs must not enable stricter rules')
        review_briefs = report.get('review_briefs', [])
        if report.get('summary', {}).get('review_briefs') != len(review_briefs):
            errors.append('Source document intake review brief count does not match item list')
        registered_source_ids = {document.get('id') for document in source_document_register.get('documents', [])}
        for brief in review_briefs:
            source_id = brief.get('source_document', {}).get('id')
            if source_id not in registered_source_ids:
                errors.append(f'Source document intake review brief references unknown source document: {source_id}')
            if brief.get('autonomous_decision') is not False:
                errors.append(f'Source document intake review brief must not make autonomous decisions: {source_id}')

    def validate_source_document_requirement_delta(self, errors):
        command = [self.environment.python, str(self.root / 'scripts' / 'generate_source_document_requirement_delta.py')]
        result = self.environment.run(command, cwd=self.root, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            errors.append(f'Source document requirement delta generation failed: {result.stderr.strip() or result.stdout.strip()}')
            return
        report_path = self.root / 'generated' / 'reports' / 'source-document-requirement-delta.json'
        if not report_path.exists():
            errors.append('Source document requirement delta JSON was not generated')
            return
        report = self.load_json(report_path)
        if report.get('decision', {}).get('runtime_governance_changed') is not False:
            errors.append('Source document requirement delta must not change runtime governance behavior')
        if report.get('decision', {}).get('candidate_promoted') is not False:
            errors.append('Source document requirement delta must not promote candidate sources')
        if report.get('decision', {}).get('stricter_rules_enabled') is not False:
            errors.append('Source document requirement delta must not enable stricter rules')
        pairs = report.get('requirement_delta_pairs', [])
        if report.get('summary', {}).get('replacement_pairs') != len(pairs):
            errors.append('Source document requirement delta replacement pair count does not match item list')
        for pair in pairs:
            status_counts = pair.get('summary', {}).get('status_counts', {})
            if sum(status_counts.values()) != len(pair.get('deltas', [])):
                errors.append('Source document requirement delta pair counts do not match deltas')
            if not pair.get('deltas') and (pair.get('summary', {}).get('candidate_requirements', 0) or pair.get('summary', {}).get('target_requirements', 0)):
                errors.append(f"Source document requirement delta pair has no classified statements: {pair.get('candidate_id')} versus {pair.get('target_id')}")

    def validate_source_document_process_status(self, errors, source_document_register):
        command = [self.environment.python, str(self.root / 'scripts' / 'generate_source_document_process_status.py')]
        result = self.environment.run(command, cwd=self.root, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            errors.append(f'Source document process status generation failed: {result.stderr.strip() or result.stdout.strip()}')
            return
        report_path = self.root / 'generated' / 'reports' / 'source-document-process-status.json'
        if not report_path.exists():
            errors.append('Source document process status JSON was not generated')
            return
        self.validate_schema(errors, self.root / 'schemas' / 'source-document-process-status.schema.json', report_path)
        report = self.load_json(report_path)
        if report.get('summary', {}).get('registered_sources') != len(source_document_register.get('documents', [])):
            errors.append('Source document process status source count does not match register')
        if report.get('authorized_source_baseline', {}).get('final_source_baseline_approval') != 'not_recorded':
            errors.append('Generated source baseline readiness must not record human approval')
        if report.get('authorized_source_baseline', {}).get('status') == 'ready_for_human_approval' and report.get('authorized_source_baseline', {}).get('blocking_reasons'):
            errors.append('Source baseline cannot be ready while blocking reasons remain')

    def validate_authorized_source_baselines(self, errors, source_document_register):
        records_root = self.model / 'documents' / 'authorized-source-baselines'
        schema_path = self.root / 'schemas' / 'authorized-source-baseline.schema.json'
        records = {}
        for path in sorted(records_root.glob('source-baseline-*.json')) if records_root.exists() else []:
            self.validate_schema(errors, schema_path, path)
            try:
                record = self.load_json(path)
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f'Could not read authorized source baseline {path.relative_to(self.root)}: {exc}')
                continue
            baseline_id = record.get('baseline_id')
            if baseline_id in records:
                errors.append(f'Duplicate authorized source baseline ID: {baseline_id}')
            records[baseline_id] = record
        for baseline_id, record in records.items():
            supersedes = record.get('supersedes')
            if supersedes and supersedes not in records:
                errors.append(f'Authorized source baseline {baseline_id} supersedes an unknown record: {supersedes}')
            if record.get('status') != 'approved':
                continue
            sources = record.get('sources', [])
            source_ids = [item.get('source_id') for item in sources]
            if len(source_ids) != len(set(source_ids)):
                errors.append(f'Authorized source baseline {baseline_id} contains duplicate source IDs')
            canonical_sources = sorted(sources, key=lambda item: item.get('source_id', ''))
            canonical = json.dumps(canonical_sources, sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            if hashlib.sha256(canonical.encode('utf-8')).hexdigest() != record.get('authorized_source_set_sha256'):
                errors.append(f'Authorized source baseline {baseline_id} has a mismatched source-set hash')
            decision = record.get('decision', {})
            if not decision.get('decided_by') or not decision.get('decided_at') or (not decision.get('record')):
                errors.append(f'Approved source baseline {baseline_id} lacks a named, dated decision record')
            register_by_id = {item.get('id'): item for item in source_document_register.get('documents', [])}
            for source in sources:
                registered = register_by_id.get(source.get('source_id'))
                source_path = self.root / source.get('path', '')
                if not registered or registered.get('status') != 'approved' or registered.get('source_path') != source.get('path'):
                    errors.append(f"Approved source baseline {baseline_id} has a source that is not currently approved: {source.get('source_id')}")
                elif not source_path.is_file() or hashlib.sha256(source_path.read_bytes()).hexdigest() != source.get('sha256'):
                    errors.append(f"Approved source baseline {baseline_id} is stale for source {source.get('source_id')}")
            if set(source_ids) != {item.get('id') for item in source_document_register.get('documents', []) if item.get('status') == 'approved'}:
                errors.append(f'Approved source baseline {baseline_id} does not bind the exact currently approved source set')

    def validate_app_architecture_evidence_templates(self, errors):
        if not self.app_architecture_evidence_template_dir.exists():
            errors.append(f'App architecture evidence template directory missing: {self.app_architecture_evidence_template_dir.relative_to(self.root)}')
            return
        template_paths = sorted(self.app_architecture_evidence_template_dir.glob('*.json'))
        if not template_paths:
            errors.append(f'App architecture evidence template directory contains no JSON templates: {self.app_architecture_evidence_template_dir.relative_to(self.root)}')
            return
        schema_path = self.root / 'schemas' / 'app-architecture-evidence.schema.json'
        for template_path in template_paths:
            self.validate_schema(errors, schema_path, template_path)

    def validate_source_document_path(self, errors, source_path: str, source_label: str):
        if not source_path:
            errors.append(f'Missing source document path in {source_label}')
            return
        path = self.root / source_path
        if not path.exists():
            errors.append(f'Source document path missing in {source_label}: {source_path}')
            return
        try:
            path.relative_to(self.source_document_root)
        except ValueError:
            errors.append(f'Source document path in {source_label} must be under {self.source_document_root.relative_to(self.root)}: {source_path}')

    def validate_source_document_register(self, errors, source_document_register, source_lineage_report):
        registered_sources = []
        seen_ids = set()
        seen_paths = set()
        for document in source_document_register.get('documents', []):
            document_id = document.get('id')
            source_path = document.get('source_path')
            if document_id in seen_ids:
                errors.append(f'Duplicate source document register id: {document_id}')
            seen_ids.add(document_id)
            if source_path in seen_paths:
                errors.append(f'Duplicate source document register path: {source_path}')
            seen_paths.add(source_path)
            registered_sources.append(source_path)
            self.validate_source_document_path(errors, source_path, f'model/documents/source-document-register.yaml {document_id}')
        source_files = sorted((str(path.relative_to(self.root)) for path in self.source_document_root.iterdir() if path.is_file()))
        missing_from_register = sorted(set(source_files) - set(registered_sources))
        if missing_from_register:
            errors.append(f'Source documents missing from register: {missing_from_register}')
        registered_but_missing_file = sorted(set(registered_sources) - set(source_files))
        if registered_but_missing_file:
            errors.append(f'Registered source documents not found in source directory: {registered_but_missing_file}')
        known_source_ids = {document.get('id') for document in source_document_register.get('documents', [])}
        for document in source_document_register.get('documents', []):
            document_id = document.get('id')
            supersedes = document.get('supersedes')
            superseded_by = document.get('superseded_by')
            if supersedes and supersedes not in known_source_ids:
                errors.append(f'Source document {document_id} supersedes unknown source id: {supersedes}')
            if superseded_by and superseded_by not in known_source_ids:
                errors.append(f'Source document {document_id} is superseded_by unknown source id: {superseded_by}')
            for candidate_id in document.get('candidate_replacement_for', []):
                if candidate_id not in known_source_ids:
                    errors.append(f'Source document {document_id} candidate_replacement_for unknown source id: {candidate_id}')
        lineage_sources = {item.get('source_document') for item in source_lineage_report.get('lineage', [])}
        lineage_required_sources = {document.get('source_path') for document in source_document_register.get('documents', []) if document.get('status') not in SOURCE_STATUSES_ALLOWING_NO_LINEAGE}
        missing_lineage = sorted(lineage_required_sources - lineage_sources)
        if missing_lineage:
            errors.append(f'Registered non-draft source documents missing lineage entries: {missing_lineage}')

    def validate_waiver_authority(self, errors, waiver, waiver_authorities, source_label: str):
        risk = waiver.get('risk_classification')
        expected_authority = waiver_authorities.get(risk, {}).get('approval_authority')
        actual_authority = waiver.get('approval_authority')
        if expected_authority and actual_authority and (expected_authority != actual_authority):
            errors.append(f"Waiver authority mismatch in {source_label} for risk {risk}: expected '{expected_authority}', got '{actual_authority}'")

    def main(self) -> int:
        errors = []
        lifecycle_check = self.environment.run([self.environment.python, str(self.root / 'scripts/validate_governance_lifecycle_contracts.py')], cwd=self.root, capture_output=True, text=True, check=False)
        if lifecycle_check.returncode:
            errors.append('Lifecycle contract validation failed: ' + (lifecycle_check.stderr or lifecycle_check.stdout).strip())
        lifecycle_ledger = self.environment.run([self.environment.python, str(self.root / 'scripts/validate_governance_lifecycle_ledger.py')], cwd=self.root, capture_output=True, text=True, check=False)
        if lifecycle_ledger.returncode:
            errors.append('Lifecycle ledger validation failed: ' + (lifecycle_ledger.stderr or lifecycle_ledger.stdout).strip())
        controls = []
        capabilities = self.load_yaml(self.model / 'platform' / 'platform-capabilities.yaml')
        evidence_catalog = self.load_yaml(self.model / 'evidence' / 'evidence-types.yaml')
        governance_documents = self.load_yaml(self.model / 'documents' / 'governance-documents.yaml')
        source_document_register = self.load_yaml(self.model / 'documents' / 'source-document-register.yaml')
        document_traceability = self.load_yaml(self.model / 'traceability' / 'document-to-control.yaml')
        waiver_authorities = self.load_yaml(self.model / 'waivers' / 'waiver-authorities.yaml').get('authorities', {})
        governance_run_input_example = self.load_json(self.root / 'docs' / 'examples' / 'governance-run-input.example.json')
        waiver_example = self.load_yaml(self.model / 'waivers' / 'waiver-example.yaml')
        self.validate_schema(errors, self.root / 'schemas' / 'control.schema.json', self.model / 'controls' / 'dscb-l1.yaml')
        self.validate_schema(errors, self.root / 'schemas' / 'control.schema.json', self.model / 'controls' / 'dscb-l2.yaml')
        self.validate_schema(errors, self.root / 'schemas' / 'control.schema.json', self.model / 'controls' / 'dscb-l3.yaml')
        self.validate_schema(errors, self.root / 'schemas' / 'control.schema.json', self.model / 'controls' / 'dscb-gov.yaml')
        self.validate_schema(errors, self.root / 'schemas' / 'control-coverage.schema.json', self.model / 'controls' / 'control-coverage.yaml')
        self.validate_schema(errors, self.root / 'schemas' / 'evidence-trust-model.schema.json', self.model / 'evidence' / 'evidence-trust-model.yaml')
        self.validate_schema(errors, self.root / 'schemas' / 'evidence-collector-contract.schema.json', self.model / 'evidence' / 'evidence-collector-contract.yaml')
        self.validate_schema(errors, self.root / 'schemas' / 'evidence-collector-record.schema.json', self.root / 'docs' / 'examples' / 'evidence-collector-record.example.json')
        self.validate_schema(errors, self.root / 'schemas' / 'evidence-agent-provenance.schema.json', self.root / 'docs' / 'examples' / 'evidence-agent-provenance.example.json')
        self.validate_schema(errors, self.root / 'schemas' / 'evidence-collection-attempt.schema.json', self.root / 'docs' / 'examples' / 'evidence-collection-attempt.example.json')
        self.validate_schema(errors, self.root / 'schemas' / 'intake-operation-event.schema.json', self.root / 'docs' / 'examples' / 'intake-operation-event.example.json')
        self.validate_schema(errors, self.root / 'schemas' / 'vulnerability-scan-input.schema.json', self.root / 'docs' / 'examples' / 'vulnerability-scan-input.example.json')
        self.validate_schema(errors, self.root / 'schemas' / 'evidence-freshness-policies.schema.json', self.model / 'evidence' / 'evidence-freshness-policies.yaml')
        self.validate_schema(errors, self.root / 'schemas' / 'evidence-trust-record.schema.json', self.root / 'docs' / 'examples' / 'evidence-trust-record.example.json')
        self.validate_schema(errors, self.root / 'schemas' / 'governance-document-catalog.schema.json', self.model / 'documents' / 'governance-documents.yaml')
        self.validate_schema(errors, self.root / 'schemas' / 'source-document-register.schema.json', self.model / 'documents' / 'source-document-register.yaml')
        self.validate_schema(errors, self.root / 'schemas' / 'document-control-traceability.schema.json', self.model / 'traceability' / 'document-to-control.yaml')
        self.validate_schema(errors, self.root / 'schemas' / 'governance-document-rendering.schema.json', self.model / 'documents' / 'governance-document-rendering.yaml')
        self.validate_schema(errors, self.root / 'schemas' / 'governance-compliance-result.schema.json', self.root / 'docs' / 'examples' / 'governance-compliance-result.example.json')
        self.validate_schema(errors, self.root / 'schemas' / 'governance-run-input.schema.json', self.root / 'docs' / 'examples' / 'governance-run-input.example.json')
        self.validate_schema(errors, self.root / 'schemas' / 'waiver.schema.json', self.model / 'waivers' / 'waiver-example.yaml')
        architecture_index_path = self.root / 'status' / 'architecture-results-index.json'
        if architecture_index_path.exists():
            self.validate_schema(errors, self.root / 'schemas' / 'architecture-results-index.schema.json', architecture_index_path)
        repository_index_path = self.root / 'status' / 'repository-results-index.json'
        if repository_index_path.exists():
            self.validate_schema(errors, self.root / 'schemas' / 'governance-results-index.schema.json', repository_index_path)
        typed_evidence_index_path = self.root / 'status' / 'typed-evidence-results-index.json'
        if typed_evidence_index_path.exists():
            self.validate_schema(errors, self.root / 'schemas' / 'typed-evidence-results-index.schema.json', typed_evidence_index_path)
        self.validate_typed_evidence_results(errors)
        load_snapshots = self.environment.load_measured_security_snapshots
        try:
            load_snapshots(self.root / 'status/measured-security-results')
        except Exception as exc:
            errors.append(f'Measured security snapshot validation: {exc}')
        load_l1_snapshots = self.environment.load_measured_l1_snapshots
        try:
            load_l1_snapshots(self.root / 'status/measured-l1-results')
        except Exception as exc:
            errors.append(f'Measured L1 assessment validation: {exc}')
        load_assurance_profile = self.environment.load_assurance_profile
        load_assurance_snapshots = self.environment.load_assurance_snapshots
        validate_assurance_source = self.environment.validate_assurance_source
        try:
            load_assurance_profile()
            for assurance in load_assurance_snapshots(self.root / 'status/control-evidence-assurance'):
                validate_assurance_source(assurance)
        except Exception as exc:
            errors.append(f'Control evidence assurance validation: {exc}')
        load_staging_deployment_snapshots = self.environment.load_staging_deployment_snapshots
        try:
            load_staging_deployment_snapshots(self.root / 'status/staging-deployment-results')
        except Exception as exc:
            errors.append(f'Staging deployment result validation: {exc}')
        load_consolidated_l1_snapshots = self.environment.load_consolidated_l1_snapshots
        validate_consolidated_l1_sources = self.environment.validate_consolidated_l1_sources
        try:
            for consolidated in load_consolidated_l1_snapshots(self.root / 'status/consolidated-l1-results'):
                validate_consolidated_l1_sources(consolidated)
        except Exception as exc:
            errors.append(f'Consolidated L1 assessment validation: {exc}')
        self.validate_intake_conflicts(errors)
        self.validate_intake_events(errors)
        self.validate_intake_health(errors)
        self.validate_multi_consumer_readiness(errors)
        self.validate_evidence_attestation_pilot(errors)
        self.validate_blocking_readiness(errors)
        self.validate_blocking_mode_alignment(errors)
        self.validate_governance_repository_security(errors)
        self.validate_replay_triage(errors)
        self.validate_harmonized_requirements_candidate(errors, source_document_register)
        for path in sorted((self.model / 'controls').glob('dscb-*.yaml')):
            data = self.load_yaml(path)
            level = data.get('level')
            for requirement in data.get('requirements', []):
                requirement['_source_file'] = str(path.relative_to(self.root))
                requirement['_level_file'] = level
                controls.append(requirement)
        ids = [item['id'] for item in controls]
        duplicates = sorted({item for item in ids if ids.count(item) > 1})
        if duplicates:
            errors.append(f'Duplicate control IDs: {duplicates}')
        for level, expected in EXPECTED_COUNTS.items():
            actual = sum((1 for item in controls if item.get('_level_file') == level))
            if actual != expected:
                errors.append(f'Unexpected {level} count: expected {expected}, got {actual}')
        traceability = self.load_yaml(self.model / 'traceability' / 'control-to-platform.yaml')
        control_coverage = self.load_yaml(self.model / 'controls' / 'control-coverage.yaml')
        traced = {item['control'] for item in traceability.get('mappings', [])}
        known = set(ids)
        coverage_controls = {item['control_id'] for item in control_coverage.get('coverage', [])}
        known_capabilities = {item['id'] for item in capabilities.get('capabilities', [])}
        known_evidence = {item['id'] for item in evidence_catalog.get('evidence_types', [])}
        known_documents = {item['id'] for item in governance_documents.get('documents', [])}
        missing_traceability = sorted(known - traced)
        if missing_traceability:
            errors.append(f'Controls missing traceability: {missing_traceability}')
        unknown_traceability = sorted(traced - known)
        if unknown_traceability:
            errors.append(f'Traceability references unknown controls: {unknown_traceability}')
        missing_coverage = sorted(known - coverage_controls)
        if missing_coverage:
            errors.append(f'Controls missing coverage status: {missing_coverage}')
        unknown_coverage = sorted(coverage_controls - known)
        if unknown_coverage:
            errors.append(f'Coverage status references unknown controls: {unknown_coverage}')
        coverage_ids = [item['control_id'] for item in control_coverage.get('coverage', [])]
        duplicate_coverage = sorted({item for item in coverage_ids if coverage_ids.count(item) > 1})
        if duplicate_coverage:
            errors.append(f'Duplicate coverage status entries: {duplicate_coverage}')
        for item in controls:
            policy = item.get('policy_as_code', {})
            rule = policy.get('rule')
            if policy.get('candidate') and rule and (not (self.root / rule).exists()):
                errors.append(f"Policy rule missing for {item['id']}: {rule}")
            for capability in item.get('platform_capabilities', []):
                if capability not in known_capabilities:
                    errors.append(f"Unknown platform capability on {item['id']}: {capability}")
            for evidence in item.get('evidence', []):
                if evidence not in known_evidence:
                    errors.append(f"Unknown evidence type on {item['id']}: {evidence}")
        for document in governance_documents.get('documents', []):
            document_path = self.root / document['repository_path']
            if not document_path.exists():
                errors.append(f"Governance document path missing for {document['id']}: {document['repository_path']}")
            source_documents = document.get('source_documents', [])
            if not source_documents:
                errors.append(f"Governance document missing source_documents for {document['id']}")
            for source_document in source_documents:
                self.validate_source_document_path(errors, source_document, f"model/documents/governance-documents.yaml {document['id']}")
        for architecture_path in sorted((self.root / 'architecture').glob('*.yaml')):
            payload = self.load_yaml(architecture_path)
            if isinstance(payload, dict) and 'source_document' in payload:
                self.validate_source_document_path(errors, payload.get('source_document', ''), str(architecture_path.relative_to(self.root)))
        self.validate_source_document_requirement_delta(errors)
        self.validate_source_document_intake_review_briefs(errors, source_document_register)
        self.validate_source_document_intake_status(errors, source_document_register)
        self.validate_source_document_process_status(errors, source_document_register)
        self.validate_authorized_source_baselines(errors, source_document_register)
        source_lineage_report = self.validate_source_lineage_report(errors) or {}
        self.validate_governance_graph(errors)
        self.validate_source_document_register(errors, source_document_register, source_lineage_report)
        self.validate_governance_change_impact_report(errors)
        self.validate_architecture_source_replacement_assessment(errors)
        self.validate_app_architecture_evidence_templates(errors)
        provenance_validation = self.environment.run([self.environment.python, str(self.root / 'scripts' / 'validate_evidence_agent_provenance.py')], capture_output=True, text=True, check=False)
        if provenance_validation.returncode != 0:
            errors.append('Evidence agent provenance validation failed: ' + (provenance_validation.stderr.strip() or provenance_validation.stdout.strip()))
        document_review_operations = self.environment.run([self.environment.python, str(self.root / 'scripts' / 'validate_document_consistency_review_operations.py')], capture_output=True, text=True, check=False)
        if document_review_operations.returncode != 0:
            errors.append('Document consistency review operations validation failed: ' + (document_review_operations.stderr.strip() or document_review_operations.stdout.strip()))
        for mapping in traceability.get('mappings', []):
            control_id = mapping['control']
            for capability in mapping.get('platform_capabilities', []):
                if capability not in known_capabilities:
                    errors.append(f'Unknown traceability platform capability on {control_id}: {capability}')
            for evidence in mapping.get('evidence', []):
                if evidence not in known_evidence:
                    errors.append(f'Unknown traceability evidence on {control_id}: {evidence}')
        for mapping in document_traceability.get('mappings', []):
            document_id = mapping['document_id']
            if document_id not in known_documents:
                errors.append(f'Document traceability references unknown document: {document_id}')
            for control_id in mapping.get('control_ids', []):
                if control_id not in known:
                    errors.append(f'Document traceability references unknown control: {control_id}')
        self.validate_waiver_authority(errors, waiver_example, waiver_authorities, 'model/waivers/waiver-example.yaml')
        for index, waiver in enumerate(governance_run_input_example.get('waivers', [])):
            self.validate_waiver_authority(errors, waiver, waiver_authorities, f'docs/examples/governance-run-input.example.json waiver[{index}]')
        self.run_opa_check(errors)
        if errors:
            self.environment.print('Validation failed:')
            for error in errors:
                self.environment.print(f'- {error}')
            return 1
        self.environment.print('Validation passed')
        self.environment.print(f'- controls: {len(controls)}')
        for level in ['L1', 'L2', 'L3', 'GOV']:
            self.environment.print(f"- {level}: {sum((1 for item in controls if item.get('_level_file') == level))}")
        self.environment.print(f'- traceability mappings: {len(traced)}')
        self.environment.print(f"- registered source documents: {len(source_document_register.get('documents', []))}")
        self.environment.print(f"- policy candidates: {sum((1 for item in controls if item.get('policy_as_code', {}).get('candidate')))}")
        return 0
