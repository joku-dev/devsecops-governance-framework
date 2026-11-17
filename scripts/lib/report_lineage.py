"""Pure source reporting extracted from frozen V1 6b557fe; explicit data and clock."""
from __future__ import annotations
from collections import Counter
from lib.report_data import report_time

def load_yaml(data, path): return data.yaml(path)
def rel(data, path): return data.relative(path)

def registered_source_records(data) -> tuple[list[dict], dict[str, dict]]:
    """Return source inventory from the register, retaining filesystem checks."""
    register_path = data.root / 'model' / 'documents' / 'source-document-register.yaml'
    register = load_yaml(data, register_path)
    records = []
    by_path = {}
    for document in register.get('documents', []):
        path = document['source_path']
        item = {'id': document['id'], 'title': document['title'], 'status': document['status'], 'governance_domains': document.get('governance_domains', []), 'path': path, 'exists': data.is_file(data.root / path)}
        records.append(item)
        by_path[path] = item
    return (records, by_path)

def add_lineage(lineage: dict, source_path: str, artifact_path: str, artifact_type: str, role: str) -> None:
    lineage.setdefault(source_path, []).append({'artifact_path': artifact_path, 'artifact_type': artifact_type, 'role': role})

def architecture_lineage(data, lineage: dict) -> None:
    architecture_paths = sorted(data.glob(data.root / 'architecture', '*.yaml'))
    for path in architecture_paths:
        payload = load_yaml(data, path)
        source_path = payload.get('source_document')
        if source_path:
            add_lineage(lineage, source_path, rel(data, path), 'architecture_model', 'working_model')
    release_root = data.root / 'releases' / 'architecture' / 'l1' / 'v0.1.0'
    release_metadata = release_root / 'release-metadata.json'
    if data.exists(release_metadata):
        metadata = data.json(release_metadata)
        for asset in metadata.get('included_assets', []):
            asset_path = release_root / asset
            if data.exists(asset_path) and 'source/architecture/' in asset:
                payload = load_yaml(data, asset_path)
                source_path = payload.get('source_document')
                if source_path:
                    add_lineage(lineage, source_path, rel(data, asset_path), 'release_snapshot', metadata['release_id'])
        add_lineage(lineage, 'docs/governance/source-documents/ARCH-SDD-SRC-001.requirements.md', rel(data, release_metadata), 'release_metadata', metadata.get('release_id', 'architecture-release'))
        add_lineage(lineage, 'docs/governance/source-documents/ARCH-SDD-SRC-001.requirements.md', rel(data, release_root / 'baseline-package.md'), 'release_document', metadata.get('release_id', 'architecture-release'))
    for path in sorted(data.glob(data.root / 'policies' / 'opa', 'architecture_*.rego')):
        add_lineage(lineage, 'docs/governance/source-documents/ARCH-SDD-SRC-001.requirements.md', rel(data, path), 'policy_as_code', 'architecture_runtime_governance')
    for path in [data.root / 'schemas' / 'architecture-release-candidate.schema.json', data.root / 'schemas' / 'app-architecture-evidence.schema.json', data.root / 'schemas' / 'architecture-results-index.schema.json', data.root / 'generated' / 'csv' / 'architecture_runtime_traceability.csv', data.root / 'status' / 'architecture-results-index.json', data.root / 'generated' / 'viewer' / 'status-viewer.html']:
        add_lineage(lineage, 'docs/governance/source-documents/ARCH-SDD-SRC-001.requirements.md', rel(data, path), 'derived_artifact', 'architecture_runtime_governance')

def devsecops_lineage(data, lineage: dict) -> None:
    document_catalog = load_yaml(data, data.root / 'model' / 'documents' / 'governance-documents.yaml')
    document_traceability = load_yaml(data, data.root / 'model' / 'traceability' / 'document-to-control.yaml')
    document_sources = {document['id']: document.get('source_documents', []) for document in document_catalog.get('documents', [])}
    for document in document_catalog.get('documents', []):
        for source_path in document.get('source_documents', []):
            add_lineage(lineage, source_path, document['repository_path'], 'governance_document', document['id'])
    for mapping in document_traceability.get('mappings', []):
        document_id = mapping['document_id']
        for source_path in document_sources.get(document_id, []):
            add_lineage(lineage, source_path, 'model/traceability/document-to-control.yaml', 'traceability_mapping', document_id)
    standards = {'DSCB-STD-001': ['model/controls/dscb-gov.yaml', 'model/controls/dscb-l1.yaml', 'model/controls/dscb-l2.yaml', 'model/controls/dscb-l3.yaml', 'model/controls/governance-repository-security.yaml', 'model/evidence/evidence-types.yaml', 'model/evidence/evidence-collector-contract.yaml', 'model/evidence/evidence-trust-model.yaml', 'model/evidence/evidence-freshness-policies.yaml', 'schemas/evidence-collector-contract.schema.json', 'schemas/evidence-collector-record.schema.json', 'schemas/vulnerability-scan-input.schema.json', 'schemas/typed-evidence-result.schema.json', 'schemas/typed-evidence-results-index.schema.json', 'schemas/evidence-trust-model.schema.json', 'schemas/evidence-freshness-policies.schema.json', 'schemas/evidence-trust-record.schema.json', 'schemas/governance-repository-security-model.schema.json', 'schemas/governance-repository-security-report.schema.json', 'docs/operations/evidence/evidence-trust-model.md', 'docs/operations/evidence/evidence-collector-contract.md', 'docs/operations/evidence/governance-result-intake-and-viewer-usage.md', 'docs/operations/evidence/vulnerability-scan-collector-usage.md', 'docs/operations/status/governance-intelligence-graph-viewer.md', 'docs/operations/security/governance-repository-self-security.md', 'docs/governance/change-requests/GCR-2026-048-governance-repository-self-security.md', 'docs/governance/change-requests/GCR-2026-049-current-governance-security-report.md', 'docs/demos/demo-consumer-typed-evidence-trust.md', 'docs/demos/presentation-guide-typed-evidence-trust-de.md', 'docs/examples/evidence-trust-record.example.json', 'docs/examples/evidence-collector-record.example.json', 'docs/examples/vulnerability-scan-input.example.json', 'docs/examples/governance-repository-security-observation.example.json', 'scripts/lib/evidence_trust.py', 'scripts/lib/result_ledger.py', 'scripts/collect_vulnerability_scan_evidence.py', 'scripts/intake_evidence_trust_github_actions_run.py', 'scripts/intake_governance_result.py', 'scripts/intake_ci_artifact_bundle.py', 'scripts/generate_typed_evidence_results_index.py', 'scripts/intake_github_actions_run.py', 'scripts/intake_architecture_github_actions_run.py', 'scripts/generate_repository_results_index.py', 'scripts/generate_architecture_results_index.py', 'scripts/generate_governance_graph.py', 'scripts/generate_status_viewer.py', 'scripts/assess_governance_repository_security.py', 'schemas/governance-graph.schema.json', 'tests/test_evidence_trust_capture.py', 'tests/test_evidence_collector_contract.py', 'tests/test_vulnerability_scan_collector.py', 'tests/test_typed_evidence_intake.py', 'tests/test_evidence_freshness_policies.py', 'tests/test_evidence_trust_indexes.py', 'tests/test_governance_graph.py', 'tests/test_governance_repository_security.py', 'tests/test_result_ledger.py', 'schemas/governance-results-index.schema.json', 'schemas/architecture-results-index.schema.json', 'schemas/intake-conflict.schema.json', 'status/typed-evidence-results-index.json', 'status/intake-conflicts/README.md', 'generated/viewer/status-viewer.html', 'generated/reports/governance-repository-security.json', 'generated/reports/governance-repository-security.md', '.github/workflows/governance-repository-security.yml', '.github/workflows/codeql.yml', '.github/workflows/dependency-review.yml', '.github/dependabot.yml', '.github/CODEOWNERS', 'SECURITY.md', 'model/controls/control-coverage.yaml'], 'PRA-STD-001': ['model/platform/platform-capabilities.yaml', 'model/platform/pra-levels.yaml', 'model/traceability/control-to-platform.yaml', 'pipeline-baseline/artifact-types.yaml', 'pipeline-baseline/control-placement.yaml', 'pipeline-baseline/evidence-contract.yaml', 'pipeline-baseline/gate-semantics.yaml', 'pipeline-baseline/minimum-metadata.yaml', 'pipeline-baseline/stages.yaml', 'pipeline-baseline/waiver-integration.yaml', 'model/controls/governance-repository-security.yaml', 'schemas/governance-repository-security-model.schema.json', 'schemas/governance-repository-security-report.schema.json', 'docs/operations/security/governance-repository-self-security.md', 'docs/examples/governance-repository-security-observation.example.json', 'scripts/assess_governance_repository_security.py', '.github/workflows/governance-repository-security.yml', '.github/workflows/codeql.yml', '.github/workflows/dependency-review.yml', '.github/dependabot.yml', '.github/CODEOWNERS', 'SECURITY.md']}
    for document_id, artifact_paths in standards.items():
        for source_path in document_sources.get(document_id, []):
            for artifact_path in artifact_paths:
                add_lineage(lineage, source_path, artifact_path, 'governance_model', document_id)
    devsecops_policy_paths = sorted((path for path in data.glob(data.root / 'policies' / 'opa', '*.rego') if not path.name.startswith('architecture_')))
    for source_path in document_sources.get('DSCB-STD-001', []):
        for path in devsecops_policy_paths:
            add_lineage(lineage, source_path, rel(data, path), 'policy_as_code', 'devsecops_baseline')
    for source_path in document_sources.get('PRA-STD-001', []):
        for path in [data.root / 'generated' / 'xlsx' / 'traceability_matrix.csv', data.root / 'generated' / 'xlsx' / 'document_control_matrix.csv', data.root / 'generated' / 'reports' / 'document-control-matrix.md', data.root / 'generated' / 'reports' / 'control-coverage-report.md', data.root / 'status' / 'repository-results-index.json', data.root / 'generated' / 'viewer' / 'status-viewer.html']:
            add_lineage(lineage, source_path, rel(data, path), 'derived_artifact', 'devsecops_baseline')
    release_root = data.root / 'releases' / 'l1' / 'v1.1.3'
    for source_path in document_sources.get('DSCB-STD-001', []):
        for path in [release_root / 'baseline-package.md', release_root / 'release-metadata.json', release_root / 'checksums.sha256']:
            add_lineage(lineage, source_path, rel(data, path), 'release_package', 'l1-baseline-v1.1.3')

def build_report(data, at) -> dict:
    source_documents, registered_sources = registered_source_records(data)
    source_documents.sort(key=lambda item: item['path'])
    lineage: dict[str, list[dict]] = {}
    devsecops_lineage(data, lineage)
    architecture_lineage(data, lineage)
    for item in source_documents:
        lineage.setdefault(item['path'], [])
    source_files = {rel(data, path) for path in data.iterdir(data.root / 'docs/governance/source-documents') if data.is_file(path)}
    unregistered_source_files = sorted(source_files - set(registered_sources))
    shared_intake_outputs = []
    for output_path in ['generated/reports/architecture-source-replacement-assessment.json', 'generated/reports/architecture-source-replacement-assessment.md', 'generated/reports/governance-change-impact.json', 'generated/reports/governance-change-impact.md', 'generated/reports/source-document-intake-status.json', 'generated/reports/source-document-intake-status.md', 'generated/reports/source-document-intake-review-briefs.json', 'generated/reports/source-document-intake-review-briefs.md', 'generated/reports/source-document-requirement-delta.json', 'generated/reports/source-document-requirement-delta.md']:
        shared_intake_outputs.append({'path': output_path, 'exists': data.is_file(data.root / output_path)})
    unresolved_source_references = []
    for source_path, artifacts in sorted(lineage.items()):
        if source_path in registered_sources:
            continue
        unresolved_source_references.append({'path': source_path, 'exists': data.is_file(data.root / source_path), 'registered': False, 'referenced_by': sorted({item['artifact_path'] for item in artifacts})})
    missing_artifacts = []
    for source_path, artifacts in lineage.items():
        for artifact in artifacts:
            artifact_path = data.root / artifact['artifact_path']
            artifact['exists'] = data.exists(artifact_path)
            if not artifact['exists']:
                missing_artifacts.append({'source_document': source_path, **artifact})
    return {'schema_version': '1.1.0', 'generated_at': report_time(at), 'source_document_root': rel(data, data.root / 'docs/governance/source-documents'), 'source_documents': source_documents, 'unregistered_source_files': unregistered_source_files, 'shared_intake_outputs': shared_intake_outputs, 'unresolved_source_references': unresolved_source_references, 'lineage': [{'source_document': source_path, 'derived_artifacts': sorted(artifacts, key=lambda item: (item['artifact_type'], item['artifact_path']))} for source_path, artifacts in sorted(lineage.items())], 'summary': {'source_document_count': len(source_documents), 'lineage_source_count': len(lineage), 'derived_artifact_count': sum((len(items) for items in lineage.values())), 'missing_derived_artifacts': len(missing_artifacts), 'unregistered_source_file_count': len(unregistered_source_files), 'unresolved_source_reference_count': len(unresolved_source_references), 'missing_registered_source_count': sum((not item['exists'] for item in source_documents))}, 'missing_derived_artifacts': missing_artifacts}

def render_markdown(report: dict) -> str:
    lines = ['# Source Lineage Report', '', f"Generated: `{report['generated_at']}`", '', '## Summary', '', f"- Source documents: `{report['summary']['source_document_count']}`", f"- Source paths with direct lineage entries: `{report['summary']['lineage_source_count']}`", f"- Direct derived artifact links: `{report['summary']['derived_artifact_count']}`", f"- Missing derived artifacts: `{report['summary']['missing_derived_artifacts']}`", f"- Registered sources missing from disk: `{report['summary']['missing_registered_source_count']}`", f"- Unregistered source files: `{report['summary']['unregistered_source_file_count']}`", f"- Unresolved source references: `{report['summary']['unresolved_source_reference_count']}`", '', 'Intake and impact reports are shared register-wide outputs. They are listed separately and are not counted as direct derivations from every source.', '', '## Source Documents', '', '| ID | Status | Source document | Exists | Direct artifacts |', '|---|---|---|---:|---:|']
    counts = {item['source_document']: len(item['derived_artifacts']) for item in report['lineage']}
    for source in report['source_documents']:
        lines.append(f"| `{source['id']}` | `{source['status']}` | `{source['path']}` | `{str(source['exists']).lower()}` | `{counts.get(source['path'], 0)}` |")
    lines.extend(['', '## Shared Intake And Impact Outputs', ''])
    for output in report['shared_intake_outputs']:
        lines.append(f"- `{output['path']}` (exists: `{str(output['exists']).lower()}`)")
    if report['unregistered_source_files']:
        lines.extend(['', '## Source Files Missing From Register', ''])
        lines.extend((f'- `{path}`' for path in report['unregistered_source_files']))
    if report['unresolved_source_references']:
        lines.extend(['', '## Unresolved Source References', ''])
        lines.append('These references occur in model or release artifacts but do not match a registered source path.')
        lines.append('')
        for reference in report['unresolved_source_references']:
            referring = ', '.join((f'`{path}`' for path in reference['referenced_by']))
            lines.append(f"- `{reference['path']}` (exists: `{str(reference['exists']).lower()}`; referenced by: {referring})")
        lines.append('')
    lines.extend(['', '## Lineage Details', ''])
    for item in report['lineage']:
        lines.append(f"### `{item['source_document']}`")
        lines.append('')
        if not item['derived_artifacts']:
            lines.append('No derived artifacts recorded.')
            lines.append('')
            continue
        lines.append('| Artifact | Type | Role | Exists |')
        lines.append('|---|---|---|---:|')
        for artifact in item['derived_artifacts']:
            lines.append(f"| `{artifact['artifact_path']}` | `{artifact['artifact_type']}` | `{artifact['role']}` | `{str(artifact['exists']).lower()}` |")
        lines.append('')
    if report['missing_derived_artifacts']:
        lines.extend(['## Missing Derived Artifacts', ''])
        for missing in report['missing_derived_artifacts']:
            lines.append(f"- `{missing['artifact_path']}` from `{missing['source_document']}`")
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'
