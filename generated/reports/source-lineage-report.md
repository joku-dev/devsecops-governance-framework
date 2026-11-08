# Source Lineage Report

Generated: `2026-10-11T11:20:42Z`

## Summary

- Source documents: `15`
- Source paths with direct lineage entries: `16`
- Direct derived artifact links: `147`
- Missing derived artifacts: `0`
- Registered sources missing from disk: `0`
- Unregistered source files: `0`
- Unresolved source references: `1`

Intake and impact reports are shared register-wide outputs. They are listed separately and are not counted as direct derivations from every source.

## Source Documents

| ID | Status | Source document | Exists | Direct artifacts |
|---|---|---|---:|---:|
| `ARCH-EA-REQ-001` | `approved` | `docs/governance/source-documents/ARCH-EA-SRC-001.requirements.md` | `true` | `0` |
| `ARCH-GOV-REQ-001` | `candidate` | `docs/governance/source-documents/ARCH-GOV-SRC-002.requirements.md` | `true` | `0` |
| `ARCH-PA-REQ-001` | `approved` | `docs/governance/source-documents/ARCH-PA-SRC-001.requirements.md` | `true` | `0` |
| `ARCH-SA-REQ-001` | `approved` | `docs/governance/source-documents/ARCH-SA-SRC-001.requirements.md` | `true` | `0` |
| `ARCH-SDD-REQ-001` | `review` | `docs/governance/source-documents/ARCH-SDD-SRC-001.requirements.md` | `true` | `20` |
| `ARCH-TPL-REQ-001` | `approved` | `docs/governance/source-documents/ARCH-TPL-SRC-001.requirements.md` | `true` | `0` |
| `CISO-REQ-SRC-001` | `candidate` | `docs/governance/source-documents/CISO-REQ-SRC-001.candidate-intake.md` | `true` | `0` |
| `DEVSECOPS-DIR-REQ-001` | `review` | `docs/governance/source-documents/DEVSECOPS-DIR-SRC-001.requirements.md` | `true` | `2` |
| `DEVSECOPS-POL-REQ-001` | `review` | `docs/governance/source-documents/DEVSECOPS-POL-SRC-001.requirements.md` | `true` | `2` |
| `DSCB-STD-REQ-001` | `approved` | `docs/governance/source-documents/DSCB-STD-SRC-001.requirements.md` | `true` | `88` |
| `DEVSECOPS-POL-CAND-002` | `candidate` | `docs/governance/source-documents/DevSecOps_Policy_Review_Integrated_v2_CHANGE_MARKED.md` | `true` | `0` |
| `TOOLCHAIN-ARCH-CAND-001` | `candidate` | `docs/governance/source-documents/Enterprise_SDLC_Toolchain_Reference_Architecture_v0.3.md` | `true` | `0` |
| `PRA-STD-REQ-001` | `approved` | `docs/governance/source-documents/PRA-STD-SRC-001.requirements.md` | `true` | `30` |
| `SDLC-PROC-CAND-001` | `candidate` | `docs/governance/source-documents/Software_Development_Process_DevSecOps_V5_Activity_RACI_Artifacts.md` | `true` | `0` |
| `SW-INDUSTRIALISATION-OM-CAND-001` | `candidate` | `docs/governance/source-documents/Software_Industrialisation_Enterprise_Operating_Model_revised_extended_scope_polished.md` | `true` | `0` |

## Shared Intake And Impact Outputs

- `generated/reports/architecture-source-replacement-assessment.json` (exists: `true`)
- `generated/reports/architecture-source-replacement-assessment.md` (exists: `true`)
- `generated/reports/governance-change-impact.json` (exists: `true`)
- `generated/reports/governance-change-impact.md` (exists: `true`)
- `generated/reports/source-document-intake-status.json` (exists: `true`)
- `generated/reports/source-document-intake-status.md` (exists: `true`)
- `generated/reports/source-document-intake-review-briefs.json` (exists: `true`)
- `generated/reports/source-document-intake-review-briefs.md` (exists: `true`)
- `generated/reports/source-document-requirement-delta.json` (exists: `true`)
- `generated/reports/source-document-requirement-delta.md` (exists: `true`)

## Unresolved Source References

These references occur in model or release artifacts but do not match a registered source path.

- `docs/governance/source-documents/ARCH-SDD-SRC-001.public.md` (exists: `false`; referenced by: `releases/architecture/l1/v0.1.0/source/architecture/arch-l1.yaml`, `releases/architecture/l1/v0.1.0/source/architecture/guardrails.yaml`, `releases/architecture/l1/v0.1.0/source/architecture/quality-markers.yaml`, `releases/architecture/l1/v0.1.0/source/architecture/remediation-actions.yaml`, `releases/architecture/l1/v0.1.0/source/architecture/review-gates.yaml`)


## Lineage Details

### `docs/governance/source-documents/ARCH-EA-SRC-001.requirements.md`

No derived artifacts recorded.

### `docs/governance/source-documents/ARCH-GOV-SRC-002.requirements.md`

No derived artifacts recorded.

### `docs/governance/source-documents/ARCH-PA-SRC-001.requirements.md`

No derived artifacts recorded.

### `docs/governance/source-documents/ARCH-SA-SRC-001.requirements.md`

No derived artifacts recorded.

### `docs/governance/source-documents/ARCH-SDD-SRC-001.public.md`

| Artifact | Type | Role | Exists |
|---|---|---|---:|
| `releases/architecture/l1/v0.1.0/source/architecture/arch-l1.yaml` | `release_snapshot` | `architecture-baseline-l1-v0.1.0` | `true` |
| `releases/architecture/l1/v0.1.0/source/architecture/guardrails.yaml` | `release_snapshot` | `architecture-baseline-l1-v0.1.0` | `true` |
| `releases/architecture/l1/v0.1.0/source/architecture/quality-markers.yaml` | `release_snapshot` | `architecture-baseline-l1-v0.1.0` | `true` |
| `releases/architecture/l1/v0.1.0/source/architecture/remediation-actions.yaml` | `release_snapshot` | `architecture-baseline-l1-v0.1.0` | `true` |
| `releases/architecture/l1/v0.1.0/source/architecture/review-gates.yaml` | `release_snapshot` | `architecture-baseline-l1-v0.1.0` | `true` |

### `docs/governance/source-documents/ARCH-SDD-SRC-001.requirements.md`

| Artifact | Type | Role | Exists |
|---|---|---|---:|
| `architecture/arch-gov.yaml` | `architecture_model` | `working_model` | `true` |
| `architecture/arch-l1.yaml` | `architecture_model` | `working_model` | `true` |
| `architecture/arch-l2.yaml` | `architecture_model` | `working_model` | `true` |
| `architecture/arch-l3.yaml` | `architecture_model` | `working_model` | `true` |
| `architecture/guardrails.yaml` | `architecture_model` | `working_model` | `true` |
| `architecture/quality-markers.yaml` | `architecture_model` | `working_model` | `true` |
| `architecture/remediation-actions.yaml` | `architecture_model` | `working_model` | `true` |
| `architecture/review-gates.yaml` | `architecture_model` | `working_model` | `true` |
| `generated/csv/architecture_runtime_traceability.csv` | `derived_artifact` | `architecture_runtime_governance` | `true` |
| `generated/viewer/status-viewer.html` | `derived_artifact` | `architecture_runtime_governance` | `true` |
| `schemas/app-architecture-evidence.schema.json` | `derived_artifact` | `architecture_runtime_governance` | `true` |
| `schemas/architecture-release-candidate.schema.json` | `derived_artifact` | `architecture_runtime_governance` | `true` |
| `schemas/architecture-results-index.schema.json` | `derived_artifact` | `architecture_runtime_governance` | `true` |
| `status/architecture-results-index.json` | `derived_artifact` | `architecture_runtime_governance` | `true` |
| `policies/opa/architecture_integration_readiness.rego` | `policy_as_code` | `architecture_runtime_governance` | `true` |
| `policies/opa/architecture_operation_readiness.rego` | `policy_as_code` | `architecture_runtime_governance` | `true` |
| `policies/opa/architecture_readiness.rego` | `policy_as_code` | `architecture_runtime_governance` | `true` |
| `policies/opa/architecture_release_readiness.rego` | `policy_as_code` | `architecture_runtime_governance` | `true` |
| `releases/architecture/l1/v0.1.0/baseline-package.md` | `release_document` | `architecture-baseline-l1-v0.1.0` | `true` |
| `releases/architecture/l1/v0.1.0/release-metadata.json` | `release_metadata` | `architecture-baseline-l1-v0.1.0` | `true` |

### `docs/governance/source-documents/ARCH-TPL-SRC-001.requirements.md`

No derived artifacts recorded.

### `docs/governance/source-documents/CISO-REQ-SRC-001.candidate-intake.md`

No derived artifacts recorded.

### `docs/governance/source-documents/DEVSECOPS-DIR-SRC-001.requirements.md`

| Artifact | Type | Role | Exists |
|---|---|---|---:|
| `docs/governance/devsecops-directive.md` | `governance_document` | `DEVSECOPS-DIR-001` | `true` |
| `model/traceability/document-to-control.yaml` | `traceability_mapping` | `DEVSECOPS-DIR-001` | `true` |

### `docs/governance/source-documents/DEVSECOPS-POL-SRC-001.requirements.md`

| Artifact | Type | Role | Exists |
|---|---|---|---:|
| `docs/governance/devsecops-policy.md` | `governance_document` | `DEVSECOPS-POL-001` | `true` |
| `model/traceability/document-to-control.yaml` | `traceability_mapping` | `DEVSECOPS-POL-001` | `true` |

### `docs/governance/source-documents/DSCB-STD-SRC-001.requirements.md`

| Artifact | Type | Role | Exists |
|---|---|---|---:|
| `docs/governance/source-documents/DSCB-STD-SRC-001.requirements.md` | `governance_document` | `DSCB-STD-001` | `true` |
| `.github/CODEOWNERS` | `governance_model` | `DSCB-STD-001` | `true` |
| `.github/dependabot.yml` | `governance_model` | `DSCB-STD-001` | `true` |
| `.github/workflows/codeql.yml` | `governance_model` | `DSCB-STD-001` | `true` |
| `.github/workflows/dependency-review.yml` | `governance_model` | `DSCB-STD-001` | `true` |
| `.github/workflows/governance-repository-security.yml` | `governance_model` | `DSCB-STD-001` | `true` |
| `SECURITY.md` | `governance_model` | `DSCB-STD-001` | `true` |
| `docs/demos/demo-consumer-typed-evidence-trust.md` | `governance_model` | `DSCB-STD-001` | `true` |
| `docs/demos/presentation-guide-typed-evidence-trust-de.md` | `governance_model` | `DSCB-STD-001` | `true` |
| `docs/examples/evidence-collector-record.example.json` | `governance_model` | `DSCB-STD-001` | `true` |
| `docs/examples/evidence-trust-record.example.json` | `governance_model` | `DSCB-STD-001` | `true` |
| `docs/examples/governance-repository-security-observation.example.json` | `governance_model` | `DSCB-STD-001` | `true` |
| `docs/examples/vulnerability-scan-input.example.json` | `governance_model` | `DSCB-STD-001` | `true` |
| `docs/governance/change-requests/GCR-2026-048-governance-repository-self-security.md` | `governance_model` | `DSCB-STD-001` | `true` |
| `docs/governance/change-requests/GCR-2026-049-current-governance-security-report.md` | `governance_model` | `DSCB-STD-001` | `true` |
| `docs/operations/evidence/evidence-collector-contract.md` | `governance_model` | `DSCB-STD-001` | `true` |
| `docs/operations/evidence/evidence-trust-model.md` | `governance_model` | `DSCB-STD-001` | `true` |
| `docs/operations/evidence/governance-result-intake-and-viewer-usage.md` | `governance_model` | `DSCB-STD-001` | `true` |
| `docs/operations/evidence/vulnerability-scan-collector-usage.md` | `governance_model` | `DSCB-STD-001` | `true` |
| `docs/operations/security/governance-repository-self-security.md` | `governance_model` | `DSCB-STD-001` | `true` |
| `docs/operations/status/governance-intelligence-graph-viewer.md` | `governance_model` | `DSCB-STD-001` | `true` |
| `generated/reports/governance-repository-security.json` | `governance_model` | `DSCB-STD-001` | `true` |
| `generated/reports/governance-repository-security.md` | `governance_model` | `DSCB-STD-001` | `true` |
| `generated/viewer/status-viewer.html` | `governance_model` | `DSCB-STD-001` | `true` |
| `model/controls/control-coverage.yaml` | `governance_model` | `DSCB-STD-001` | `true` |
| `model/controls/dscb-gov.yaml` | `governance_model` | `DSCB-STD-001` | `true` |
| `model/controls/dscb-l1.yaml` | `governance_model` | `DSCB-STD-001` | `true` |
| `model/controls/dscb-l2.yaml` | `governance_model` | `DSCB-STD-001` | `true` |
| `model/controls/dscb-l3.yaml` | `governance_model` | `DSCB-STD-001` | `true` |
| `model/controls/governance-repository-security.yaml` | `governance_model` | `DSCB-STD-001` | `true` |
| `model/evidence/evidence-collector-contract.yaml` | `governance_model` | `DSCB-STD-001` | `true` |
| `model/evidence/evidence-freshness-policies.yaml` | `governance_model` | `DSCB-STD-001` | `true` |
| `model/evidence/evidence-trust-model.yaml` | `governance_model` | `DSCB-STD-001` | `true` |
| `model/evidence/evidence-types.yaml` | `governance_model` | `DSCB-STD-001` | `true` |
| `schemas/architecture-results-index.schema.json` | `governance_model` | `DSCB-STD-001` | `true` |
| `schemas/evidence-collector-contract.schema.json` | `governance_model` | `DSCB-STD-001` | `true` |
| `schemas/evidence-collector-record.schema.json` | `governance_model` | `DSCB-STD-001` | `true` |
| `schemas/evidence-freshness-policies.schema.json` | `governance_model` | `DSCB-STD-001` | `true` |
| `schemas/evidence-trust-model.schema.json` | `governance_model` | `DSCB-STD-001` | `true` |
| `schemas/evidence-trust-record.schema.json` | `governance_model` | `DSCB-STD-001` | `true` |
| `schemas/governance-graph.schema.json` | `governance_model` | `DSCB-STD-001` | `true` |
| `schemas/governance-repository-security-model.schema.json` | `governance_model` | `DSCB-STD-001` | `true` |
| `schemas/governance-repository-security-report.schema.json` | `governance_model` | `DSCB-STD-001` | `true` |
| `schemas/governance-results-index.schema.json` | `governance_model` | `DSCB-STD-001` | `true` |
| `schemas/intake-conflict.schema.json` | `governance_model` | `DSCB-STD-001` | `true` |
| `schemas/typed-evidence-result.schema.json` | `governance_model` | `DSCB-STD-001` | `true` |
| `schemas/typed-evidence-results-index.schema.json` | `governance_model` | `DSCB-STD-001` | `true` |
| `schemas/vulnerability-scan-input.schema.json` | `governance_model` | `DSCB-STD-001` | `true` |
| `scripts/assess_governance_repository_security.py` | `governance_model` | `DSCB-STD-001` | `true` |
| `scripts/collect_vulnerability_scan_evidence.py` | `governance_model` | `DSCB-STD-001` | `true` |
| `scripts/generate_architecture_results_index.py` | `governance_model` | `DSCB-STD-001` | `true` |
| `scripts/generate_governance_graph.py` | `governance_model` | `DSCB-STD-001` | `true` |
| `scripts/generate_repository_results_index.py` | `governance_model` | `DSCB-STD-001` | `true` |
| `scripts/generate_status_viewer.py` | `governance_model` | `DSCB-STD-001` | `true` |
| `scripts/generate_typed_evidence_results_index.py` | `governance_model` | `DSCB-STD-001` | `true` |
| `scripts/intake_architecture_github_actions_run.py` | `governance_model` | `DSCB-STD-001` | `true` |
| `scripts/intake_ci_artifact_bundle.py` | `governance_model` | `DSCB-STD-001` | `true` |
| `scripts/intake_evidence_trust_github_actions_run.py` | `governance_model` | `DSCB-STD-001` | `true` |
| `scripts/intake_github_actions_run.py` | `governance_model` | `DSCB-STD-001` | `true` |
| `scripts/intake_governance_result.py` | `governance_model` | `DSCB-STD-001` | `true` |
| `scripts/lib/evidence_trust.py` | `governance_model` | `DSCB-STD-001` | `true` |
| `scripts/lib/result_ledger.py` | `governance_model` | `DSCB-STD-001` | `true` |
| `status/intake-conflicts/README.md` | `governance_model` | `DSCB-STD-001` | `true` |
| `status/typed-evidence-results-index.json` | `governance_model` | `DSCB-STD-001` | `true` |
| `tests/test_evidence_collector_contract.py` | `governance_model` | `DSCB-STD-001` | `true` |
| `tests/test_evidence_freshness_policies.py` | `governance_model` | `DSCB-STD-001` | `true` |
| `tests/test_evidence_trust_capture.py` | `governance_model` | `DSCB-STD-001` | `true` |
| `tests/test_evidence_trust_indexes.py` | `governance_model` | `DSCB-STD-001` | `true` |
| `tests/test_governance_graph.py` | `governance_model` | `DSCB-STD-001` | `true` |
| `tests/test_governance_repository_security.py` | `governance_model` | `DSCB-STD-001` | `true` |
| `tests/test_result_ledger.py` | `governance_model` | `DSCB-STD-001` | `true` |
| `tests/test_typed_evidence_intake.py` | `governance_model` | `DSCB-STD-001` | `true` |
| `tests/test_vulnerability_scan_collector.py` | `governance_model` | `DSCB-STD-001` | `true` |
| `policies/opa/access_control.rego` | `policy_as_code` | `devsecops_baseline` | `true` |
| `policies/opa/artifact_integrity.rego` | `policy_as_code` | `devsecops_baseline` | `true` |
| `policies/opa/artifact_signing.rego` | `policy_as_code` | `devsecops_baseline` | `true` |
| `policies/opa/branch_protection.rego` | `policy_as_code` | `devsecops_baseline` | `true` |
| `policies/opa/dependency_source_control.rego` | `policy_as_code` | `devsecops_baseline` | `true` |
| `policies/opa/devsecops_release_readiness.rego` | `policy_as_code` | `devsecops_baseline` | `true` |
| `policies/opa/iac_required.rego` | `policy_as_code` | `devsecops_baseline` | `true` |
| `policies/opa/pipeline_security_gates.rego` | `policy_as_code` | `devsecops_baseline` | `true` |
| `policies/opa/sbom_required.rego` | `policy_as_code` | `devsecops_baseline` | `true` |
| `policies/opa/vulnerability_gate.rego` | `policy_as_code` | `devsecops_baseline` | `true` |
| `policies/opa/waiver_validity.rego` | `policy_as_code` | `devsecops_baseline` | `true` |
| `releases/l1/v1.1.3/baseline-package.md` | `release_package` | `l1-baseline-v1.1.3` | `true` |
| `releases/l1/v1.1.3/checksums.sha256` | `release_package` | `l1-baseline-v1.1.3` | `true` |
| `releases/l1/v1.1.3/release-metadata.json` | `release_package` | `l1-baseline-v1.1.3` | `true` |
| `model/traceability/document-to-control.yaml` | `traceability_mapping` | `DSCB-STD-001` | `true` |

### `docs/governance/source-documents/DevSecOps_Policy_Review_Integrated_v2_CHANGE_MARKED.md`

No derived artifacts recorded.

### `docs/governance/source-documents/Enterprise_SDLC_Toolchain_Reference_Architecture_v0.3.md`

No derived artifacts recorded.

### `docs/governance/source-documents/PRA-STD-SRC-001.requirements.md`

| Artifact | Type | Role | Exists |
|---|---|---|---:|
| `generated/reports/control-coverage-report.md` | `derived_artifact` | `devsecops_baseline` | `true` |
| `generated/reports/document-control-matrix.md` | `derived_artifact` | `devsecops_baseline` | `true` |
| `generated/viewer/status-viewer.html` | `derived_artifact` | `devsecops_baseline` | `true` |
| `generated/xlsx/document_control_matrix.csv` | `derived_artifact` | `devsecops_baseline` | `true` |
| `generated/xlsx/traceability_matrix.csv` | `derived_artifact` | `devsecops_baseline` | `true` |
| `status/repository-results-index.json` | `derived_artifact` | `devsecops_baseline` | `true` |
| `docs/governance/source-documents/PRA-STD-SRC-001.requirements.md` | `governance_document` | `PRA-STD-001` | `true` |
| `.github/CODEOWNERS` | `governance_model` | `PRA-STD-001` | `true` |
| `.github/dependabot.yml` | `governance_model` | `PRA-STD-001` | `true` |
| `.github/workflows/codeql.yml` | `governance_model` | `PRA-STD-001` | `true` |
| `.github/workflows/dependency-review.yml` | `governance_model` | `PRA-STD-001` | `true` |
| `.github/workflows/governance-repository-security.yml` | `governance_model` | `PRA-STD-001` | `true` |
| `SECURITY.md` | `governance_model` | `PRA-STD-001` | `true` |
| `docs/examples/governance-repository-security-observation.example.json` | `governance_model` | `PRA-STD-001` | `true` |
| `docs/operations/security/governance-repository-self-security.md` | `governance_model` | `PRA-STD-001` | `true` |
| `model/controls/governance-repository-security.yaml` | `governance_model` | `PRA-STD-001` | `true` |
| `model/platform/platform-capabilities.yaml` | `governance_model` | `PRA-STD-001` | `true` |
| `model/platform/pra-levels.yaml` | `governance_model` | `PRA-STD-001` | `true` |
| `model/traceability/control-to-platform.yaml` | `governance_model` | `PRA-STD-001` | `true` |
| `pipeline-baseline/artifact-types.yaml` | `governance_model` | `PRA-STD-001` | `true` |
| `pipeline-baseline/control-placement.yaml` | `governance_model` | `PRA-STD-001` | `true` |
| `pipeline-baseline/evidence-contract.yaml` | `governance_model` | `PRA-STD-001` | `true` |
| `pipeline-baseline/gate-semantics.yaml` | `governance_model` | `PRA-STD-001` | `true` |
| `pipeline-baseline/minimum-metadata.yaml` | `governance_model` | `PRA-STD-001` | `true` |
| `pipeline-baseline/stages.yaml` | `governance_model` | `PRA-STD-001` | `true` |
| `pipeline-baseline/waiver-integration.yaml` | `governance_model` | `PRA-STD-001` | `true` |
| `schemas/governance-repository-security-model.schema.json` | `governance_model` | `PRA-STD-001` | `true` |
| `schemas/governance-repository-security-report.schema.json` | `governance_model` | `PRA-STD-001` | `true` |
| `scripts/assess_governance_repository_security.py` | `governance_model` | `PRA-STD-001` | `true` |
| `model/traceability/document-to-control.yaml` | `traceability_mapping` | `PRA-STD-001` | `true` |

### `docs/governance/source-documents/Software_Development_Process_DevSecOps_V5_Activity_RACI_Artifacts.md`

No derived artifacts recorded.

### `docs/governance/source-documents/Software_Industrialisation_Enterprise_Operating_Model_revised_extended_scope_polished.md`

No derived artifacts recorded.
