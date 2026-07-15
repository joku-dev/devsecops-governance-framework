# Governance Change Impact Report

Generated: `2026-07-15T11:30:42Z`

## Inputs

- Source document register: `model/documents/source-document-register.yaml`
- Source lineage report: `generated/reports/source-lineage-report.json`

## Summary

- Registered source documents: `20`
- Source documents with lineage: `20`
- Derived artifact links: `289`

## Domain Coverage

| Domain | Source documents |
|---|---:|
| `architecture` | `12` |
| `devsecops` | `8` |
| `directive` | `2` |
| `platform` | `2` |
| `policy` | `2` |

## Release Considerations

| Consideration | Source documents |
|---|---:|
| `baseline_release_review` | `2` |
| `no_release_by_default` | `18` |

## Review Lanes

| Review lane | Source documents |
|---|---:|
| `architecture-review` | `12` |
| `devsecops-review` | `8` |
| `governance-review` | `4` |
| `platform-review` | `2` |
| `policy-as-code-review` | `2` |
| `release-review` | `2` |
| `schema-review` | `1` |
| `viewer-status-review` | `2` |

## Source Impact Details

### `DEVSECOPS-POL-SRC-001`

- Title: DevSecOps Policy Version 1 draft 3
- Source: `docs/governance/source-documents/DEVSECOPS-POL-SRC-001.public.md`
- Status: `draft`
- Owner: `governance-owners`
- Version: `1 draft 3`
- Domains: `policy, devsecops`
- Lineage artifacts: `13`
- Source state: `draft_with_lineage`
- Release consideration: `no_release_by_default`
- Review lanes: `devsecops-review, governance-review`

Derived artifact areas:

- `docs/governance/devsecops-policy.md`
- `model/documents/governance-documents.yaml`
- `model/traceability/document-to-control.yaml`

Suggested validation:

- `python3 -m unittest discover -s tests`
- `python3 scripts/validate_governance_repo.py`

Representative artifacts:

- `docs/governance/devsecops-policy.md`
- `generated/reports/architecture-source-replacement-assessment.json`
- `generated/reports/architecture-source-replacement-assessment.md`
- `generated/reports/governance-change-impact.json`
- `generated/reports/governance-change-impact.md`
- `generated/reports/source-document-intake-review-briefs.json`
- `generated/reports/source-document-intake-review-briefs.md`
- `generated/reports/source-document-intake-status.json`
- `generated/reports/source-document-intake-status.md`
- `generated/reports/source-document-requirement-delta.json`

### `DEVSECOPS-DIR-SRC-001`

- Title: DevSecOps Directive Version 0 draft 1
- Source: `docs/governance/source-documents/DEVSECOPS-DIR-SRC-001.public.md`
- Status: `draft`
- Owner: `governance-owners`
- Version: `0 draft 1`
- Domains: `directive, devsecops`
- Lineage artifacts: `13`
- Source state: `draft_with_lineage`
- Release consideration: `no_release_by_default`
- Review lanes: `devsecops-review, governance-review`

Derived artifact areas:

- `docs/governance/devsecops-directive.md`
- `model/documents/governance-documents.yaml`
- `model/traceability/document-to-control.yaml`

Suggested validation:

- `python3 -m unittest discover -s tests`
- `python3 scripts/validate_governance_repo.py`

Representative artifacts:

- `docs/governance/devsecops-directive.md`
- `generated/reports/architecture-source-replacement-assessment.json`
- `generated/reports/architecture-source-replacement-assessment.md`
- `generated/reports/governance-change-impact.json`
- `generated/reports/governance-change-impact.md`
- `generated/reports/source-document-intake-review-briefs.json`
- `generated/reports/source-document-intake-review-briefs.md`
- `generated/reports/source-document-intake-status.json`
- `generated/reports/source-document-intake-status.md`
- `generated/reports/source-document-requirement-delta.json`

### `DSCB-STD-SRC-001`

- Title: DevSecOps Control Baseline Standard aligned with Platform Levels
- Source: `docs/governance/source-documents/DSCB-STD-SRC-001.public.md`
- Status: `intake`
- Owner: `devsecops-owners`
- Version: `public-placeholder`
- Domains: `devsecops`
- Lineage artifacts: `33`
- Source state: `active_source`
- Release consideration: `baseline_release_review`
- Review lanes: `devsecops-review, policy-as-code-review, release-review`

Derived artifact areas:

- `model/controls`
- `model/evidence`
- `policies/opa`
- `releases/l1`
- `generated/reports`

Suggested validation:

- `python3 -m unittest discover -s tests`
- `python3 scripts/validate_governance_repo.py`
- `verify release package metadata and checksums`

Representative artifacts:

- `docs/governance/source-documents/DSCB-STD-SRC-001.public.md`
- `generated/reports/architecture-source-replacement-assessment.json`
- `generated/reports/architecture-source-replacement-assessment.md`
- `generated/reports/governance-change-impact.json`
- `generated/reports/governance-change-impact.md`
- `generated/reports/source-document-intake-review-briefs.json`
- `generated/reports/source-document-intake-review-briefs.md`
- `generated/reports/source-document-intake-status.json`
- `generated/reports/source-document-intake-status.md`
- `generated/reports/source-document-requirement-delta.json`

### `PRA-STD-SRC-001`

- Title: DevSecOps Platform Reference Architecture Standard aligned with Control Baseline
- Source: `docs/governance/source-documents/PRA-STD-SRC-001.public.md`
- Status: `intake`
- Owner: `platform-owners`
- Version: `public-placeholder`
- Domains: `platform, devsecops`
- Lineage artifacts: `29`
- Source state: `active_source`
- Release consideration: `no_release_by_default`
- Review lanes: `devsecops-review, platform-review, viewer-status-review`

Derived artifact areas:

- `model/platform`
- `pipeline-baseline`
- `model/traceability`
- `generated/reports`
- `generated/viewer`

Suggested validation:

- `python3 -m unittest discover -s tests`
- `python3 scripts/generate_status_viewer.py`
- `python3 scripts/validate_governance_repo.py`

Representative artifacts:

- `docs/governance/source-documents/PRA-STD-SRC-001.public.md`
- `generated/reports/architecture-source-replacement-assessment.json`
- `generated/reports/architecture-source-replacement-assessment.md`
- `generated/reports/control-coverage-report.md`
- `generated/reports/document-control-matrix.md`
- `generated/reports/governance-change-impact.json`
- `generated/reports/governance-change-impact.md`
- `generated/reports/source-document-intake-review-briefs.json`
- `generated/reports/source-document-intake-review-briefs.md`
- `generated/reports/source-document-intake-status.json`

### `ARCH-SDD-SRC-001`

- Title: SDD Architecture Governance Framework
- Source: `docs/governance/source-documents/ARCH-SDD-SRC-001.public.md`
- Status: `intake`
- Owner: `architecture-owners`
- Version: `public-placeholder`
- Domains: `architecture`
- Lineage artifacts: `36`
- Source state: `active_source`
- Release consideration: `baseline_release_review`
- Review lanes: `architecture-review, policy-as-code-review, release-review, schema-review, viewer-status-review`

Derived artifact areas:

- `architecture`
- `policies/opa/architecture_*.rego`
- `schemas/architecture-*.json`
- `releases/architecture`
- `status/architecture-results-index.json`
- `generated/viewer`

Suggested validation:

- `python3 -m unittest discover -s tests`
- `python3 scripts/generate_status_viewer.py`
- `python3 scripts/validate_governance_repo.py`
- `python3 scripts/validate_runtime_governance.py`
- `verify release package metadata and checksums`

Representative artifacts:

- `architecture/arch-gov.yaml`
- `architecture/arch-l1.yaml`
- `architecture/arch-l2.yaml`
- `architecture/arch-l3.yaml`
- `architecture/guardrails.yaml`
- `architecture/quality-markers.yaml`
- `architecture/remediation-actions.yaml`
- `architecture/review-gates.yaml`
- `generated/csv/architecture_runtime_traceability.csv`
- `generated/reports/architecture-source-replacement-assessment.json`

### `ARCH-TPL-SRC-001`

- Title: SDD Architecture Template and Checklists
- Source: `docs/governance/source-documents/ARCH-TPL-SRC-001.public.md`
- Status: `candidate`
- Owner: `architecture-owners`
- Version: `public-placeholder`
- Domains: `architecture`
- Lineage artifacts: `11`
- Source state: `candidate_pending_similarity_review`
- Release consideration: `no_release_by_default`
- Review lanes: `architecture-review`

Derived artifact areas:


Replacement and similarity:

- Similarity assessment: `not_assessed`

Suggested validation:

- `python3 -m unittest discover -s tests`
- `python3 scripts/validate_governance_repo.py`
- `python3 scripts/validate_runtime_governance.py`

Representative artifacts:

- `generated/reports/architecture-source-replacement-assessment.json`
- `generated/reports/architecture-source-replacement-assessment.md`
- `generated/reports/governance-change-impact.json`
- `generated/reports/governance-change-impact.md`
- `generated/reports/source-document-intake-review-briefs.json`
- `generated/reports/source-document-intake-review-briefs.md`
- `generated/reports/source-document-intake-status.json`
- `generated/reports/source-document-intake-status.md`
- `generated/reports/source-document-requirement-delta.json`
- `generated/reports/source-document-requirement-delta.md`

### `ARCH-EA-SRC-001`

- Title: SDD Enterprise Architecture Guidelines
- Source: `docs/governance/source-documents/ARCH-EA-SRC-001.public.md`
- Status: `candidate`
- Owner: `architecture-owners`
- Version: `public-placeholder`
- Domains: `architecture`
- Lineage artifacts: `11`
- Source state: `candidate_pending_similarity_review`
- Release consideration: `no_release_by_default`
- Review lanes: `architecture-review`

Derived artifact areas:


Replacement and similarity:

- Similarity assessment: `not_assessed`

Suggested validation:

- `python3 -m unittest discover -s tests`
- `python3 scripts/validate_governance_repo.py`
- `python3 scripts/validate_runtime_governance.py`

Representative artifacts:

- `generated/reports/architecture-source-replacement-assessment.json`
- `generated/reports/architecture-source-replacement-assessment.md`
- `generated/reports/governance-change-impact.json`
- `generated/reports/governance-change-impact.md`
- `generated/reports/source-document-intake-review-briefs.json`
- `generated/reports/source-document-intake-review-briefs.md`
- `generated/reports/source-document-intake-status.json`
- `generated/reports/source-document-intake-status.md`
- `generated/reports/source-document-requirement-delta.json`
- `generated/reports/source-document-requirement-delta.md`

### `ARCH-SA-SRC-001`

- Title: SDD Solution Architecture Guidelines
- Source: `docs/governance/source-documents/ARCH-SA-SRC-001.public.md`
- Status: `candidate`
- Owner: `architecture-owners`
- Version: `public-placeholder`
- Domains: `architecture`
- Lineage artifacts: `11`
- Source state: `candidate_pending_similarity_review`
- Release consideration: `no_release_by_default`
- Review lanes: `architecture-review`

Derived artifact areas:


Replacement and similarity:

- Similarity assessment: `not_assessed`

Suggested validation:

- `python3 -m unittest discover -s tests`
- `python3 scripts/validate_governance_repo.py`
- `python3 scripts/validate_runtime_governance.py`

Representative artifacts:

- `generated/reports/architecture-source-replacement-assessment.json`
- `generated/reports/architecture-source-replacement-assessment.md`
- `generated/reports/governance-change-impact.json`
- `generated/reports/governance-change-impact.md`
- `generated/reports/source-document-intake-review-briefs.json`
- `generated/reports/source-document-intake-review-briefs.md`
- `generated/reports/source-document-intake-status.json`
- `generated/reports/source-document-intake-status.md`
- `generated/reports/source-document-requirement-delta.json`
- `generated/reports/source-document-requirement-delta.md`

### `ARCH-PA-SRC-001`

- Title: SDD Product Architecture Guidelines
- Source: `docs/governance/source-documents/ARCH-PA-SRC-001.public.md`
- Status: `candidate`
- Owner: `architecture-owners`
- Version: `public-placeholder`
- Domains: `architecture`
- Lineage artifacts: `11`
- Source state: `candidate_pending_similarity_review`
- Release consideration: `no_release_by_default`
- Review lanes: `architecture-review`

Derived artifact areas:


Replacement and similarity:

- Similarity assessment: `not_assessed`

Suggested validation:

- `python3 -m unittest discover -s tests`
- `python3 scripts/validate_governance_repo.py`
- `python3 scripts/validate_runtime_governance.py`

Representative artifacts:

- `generated/reports/architecture-source-replacement-assessment.json`
- `generated/reports/architecture-source-replacement-assessment.md`
- `generated/reports/governance-change-impact.json`
- `generated/reports/governance-change-impact.md`
- `generated/reports/source-document-intake-review-briefs.json`
- `generated/reports/source-document-intake-review-briefs.md`
- `generated/reports/source-document-intake-status.json`
- `generated/reports/source-document-intake-status.md`
- `generated/reports/source-document-requirement-delta.json`
- `generated/reports/source-document-requirement-delta.md`

### `ARCH-GOV-SRC-002`

- Title: SDD Architecture Governance Framework
- Source: `docs/governance/source-documents/ARCH-GOV-SRC-002.public.md`
- Status: `candidate`
- Owner: `architecture-owners`
- Version: `public-placeholder`
- Domains: `architecture`
- Lineage artifacts: `11`
- Source state: `candidate_pending_similarity_review`
- Release consideration: `no_release_by_default`
- Review lanes: `architecture-review`

Derived artifact areas:


Replacement and similarity:

- Candidate replacement for: `ARCH-SDD-SRC-001`
- Similarity assessment: `replacement_candidate`

Suggested validation:

- `python3 -m unittest discover -s tests`
- `python3 scripts/validate_governance_repo.py`
- `python3 scripts/validate_runtime_governance.py`

Representative artifacts:

- `generated/reports/architecture-source-replacement-assessment.json`
- `generated/reports/architecture-source-replacement-assessment.md`
- `generated/reports/governance-change-impact.json`
- `generated/reports/governance-change-impact.md`
- `generated/reports/source-document-intake-review-briefs.json`
- `generated/reports/source-document-intake-review-briefs.md`
- `generated/reports/source-document-intake-status.json`
- `generated/reports/source-document-intake-status.md`
- `generated/reports/source-document-requirement-delta.json`
- `generated/reports/source-document-requirement-delta.md`

### `DEVSECOPS-POL-REQ-001`

- Title: DevSecOps Policy Requirements Extract
- Source: `docs/governance/source-documents/DEVSECOPS-POL-SRC-001.requirements.md`
- Status: `review`
- Owner: `governance-owners`
- Version: `requirements-only-sanitized`
- Domains: `policy, devsecops`
- Lineage artifacts: `11`
- Source state: `active_source`
- Release consideration: `no_release_by_default`
- Review lanes: `devsecops-review, governance-review`

Derived artifact areas:

- `docs/governance/source-documents`

Suggested validation:

- `python3 -m unittest discover -s tests`
- `python3 scripts/validate_governance_repo.py`

Representative artifacts:

- `generated/reports/architecture-source-replacement-assessment.json`
- `generated/reports/architecture-source-replacement-assessment.md`
- `generated/reports/governance-change-impact.json`
- `generated/reports/governance-change-impact.md`
- `generated/reports/source-document-intake-review-briefs.json`
- `generated/reports/source-document-intake-review-briefs.md`
- `generated/reports/source-document-intake-status.json`
- `generated/reports/source-document-intake-status.md`
- `generated/reports/source-document-requirement-delta.json`
- `generated/reports/source-document-requirement-delta.md`

### `DEVSECOPS-DIR-REQ-001`

- Title: DevSecOps Directive Requirements Extract
- Source: `docs/governance/source-documents/DEVSECOPS-DIR-SRC-001.requirements.md`
- Status: `review`
- Owner: `governance-owners`
- Version: `requirements-only-sanitized`
- Domains: `directive, devsecops`
- Lineage artifacts: `11`
- Source state: `active_source`
- Release consideration: `no_release_by_default`
- Review lanes: `devsecops-review, governance-review`

Derived artifact areas:

- `docs/governance/source-documents`

Suggested validation:

- `python3 -m unittest discover -s tests`
- `python3 scripts/validate_governance_repo.py`

Representative artifacts:

- `generated/reports/architecture-source-replacement-assessment.json`
- `generated/reports/architecture-source-replacement-assessment.md`
- `generated/reports/governance-change-impact.json`
- `generated/reports/governance-change-impact.md`
- `generated/reports/source-document-intake-review-briefs.json`
- `generated/reports/source-document-intake-review-briefs.md`
- `generated/reports/source-document-intake-status.json`
- `generated/reports/source-document-intake-status.md`
- `generated/reports/source-document-requirement-delta.json`
- `generated/reports/source-document-requirement-delta.md`

### `DSCB-STD-REQ-001`

- Title: DevSecOps Control Baseline Requirements Extract
- Source: `docs/governance/source-documents/DSCB-STD-SRC-001.requirements.md`
- Status: `intake`
- Owner: `devsecops-owners`
- Version: `requirements-only-sanitized`
- Domains: `devsecops`
- Lineage artifacts: `11`
- Source state: `active_source`
- Release consideration: `no_release_by_default`
- Review lanes: `devsecops-review`

Derived artifact areas:

- `docs/governance/source-documents`

Suggested validation:

- `python3 -m unittest discover -s tests`
- `python3 scripts/validate_governance_repo.py`

Representative artifacts:

- `generated/reports/architecture-source-replacement-assessment.json`
- `generated/reports/architecture-source-replacement-assessment.md`
- `generated/reports/governance-change-impact.json`
- `generated/reports/governance-change-impact.md`
- `generated/reports/source-document-intake-review-briefs.json`
- `generated/reports/source-document-intake-review-briefs.md`
- `generated/reports/source-document-intake-status.json`
- `generated/reports/source-document-intake-status.md`
- `generated/reports/source-document-requirement-delta.json`
- `generated/reports/source-document-requirement-delta.md`

### `PRA-STD-REQ-001`

- Title: Platform Reference Architecture Requirements Extract
- Source: `docs/governance/source-documents/PRA-STD-SRC-001.requirements.md`
- Status: `intake`
- Owner: `platform-owners`
- Version: `requirements-only-sanitized`
- Domains: `platform, devsecops`
- Lineage artifacts: `11`
- Source state: `active_source`
- Release consideration: `no_release_by_default`
- Review lanes: `devsecops-review, platform-review`

Derived artifact areas:

- `docs/governance/source-documents`

Suggested validation:

- `python3 -m unittest discover -s tests`
- `python3 scripts/validate_governance_repo.py`

Representative artifacts:

- `generated/reports/architecture-source-replacement-assessment.json`
- `generated/reports/architecture-source-replacement-assessment.md`
- `generated/reports/governance-change-impact.json`
- `generated/reports/governance-change-impact.md`
- `generated/reports/source-document-intake-review-briefs.json`
- `generated/reports/source-document-intake-review-briefs.md`
- `generated/reports/source-document-intake-status.json`
- `generated/reports/source-document-intake-status.md`
- `generated/reports/source-document-requirement-delta.json`
- `generated/reports/source-document-requirement-delta.md`

### `ARCH-SDD-REQ-001`

- Title: Integrated SDD Architecture Governance Requirements Extract
- Source: `docs/governance/source-documents/ARCH-SDD-SRC-001.requirements.md`
- Status: `review`
- Owner: `architecture-owners`
- Version: `requirements-only-sanitized`
- Domains: `architecture`
- Lineage artifacts: `11`
- Source state: `active_source`
- Release consideration: `no_release_by_default`
- Review lanes: `architecture-review`

Derived artifact areas:

- `docs/governance/source-documents`

Suggested validation:

- `python3 -m unittest discover -s tests`
- `python3 scripts/validate_governance_repo.py`
- `python3 scripts/validate_runtime_governance.py`

Representative artifacts:

- `generated/reports/architecture-source-replacement-assessment.json`
- `generated/reports/architecture-source-replacement-assessment.md`
- `generated/reports/governance-change-impact.json`
- `generated/reports/governance-change-impact.md`
- `generated/reports/source-document-intake-review-briefs.json`
- `generated/reports/source-document-intake-review-briefs.md`
- `generated/reports/source-document-intake-status.json`
- `generated/reports/source-document-intake-status.md`
- `generated/reports/source-document-requirement-delta.json`
- `generated/reports/source-document-requirement-delta.md`

### `ARCH-TPL-REQ-001`

- Title: Architecture Templates and Checklists Requirements Extract
- Source: `docs/governance/source-documents/ARCH-TPL-SRC-001.requirements.md`
- Status: `intake`
- Owner: `architecture-owners`
- Version: `requirements-only-sanitized`
- Domains: `architecture`
- Lineage artifacts: `11`
- Source state: `active_source`
- Release consideration: `no_release_by_default`
- Review lanes: `architecture-review`

Derived artifact areas:

- `docs/governance/source-documents`

Suggested validation:

- `python3 -m unittest discover -s tests`
- `python3 scripts/validate_governance_repo.py`
- `python3 scripts/validate_runtime_governance.py`

Representative artifacts:

- `generated/reports/architecture-source-replacement-assessment.json`
- `generated/reports/architecture-source-replacement-assessment.md`
- `generated/reports/governance-change-impact.json`
- `generated/reports/governance-change-impact.md`
- `generated/reports/source-document-intake-review-briefs.json`
- `generated/reports/source-document-intake-review-briefs.md`
- `generated/reports/source-document-intake-status.json`
- `generated/reports/source-document-intake-status.md`
- `generated/reports/source-document-requirement-delta.json`
- `generated/reports/source-document-requirement-delta.md`

### `ARCH-EA-REQ-001`

- Title: Enterprise Architecture Requirements Extract
- Source: `docs/governance/source-documents/ARCH-EA-SRC-001.requirements.md`
- Status: `intake`
- Owner: `architecture-owners`
- Version: `requirements-only-sanitized`
- Domains: `architecture`
- Lineage artifacts: `11`
- Source state: `active_source`
- Release consideration: `no_release_by_default`
- Review lanes: `architecture-review`

Derived artifact areas:

- `docs/governance/source-documents`

Suggested validation:

- `python3 -m unittest discover -s tests`
- `python3 scripts/validate_governance_repo.py`
- `python3 scripts/validate_runtime_governance.py`

Representative artifacts:

- `generated/reports/architecture-source-replacement-assessment.json`
- `generated/reports/architecture-source-replacement-assessment.md`
- `generated/reports/governance-change-impact.json`
- `generated/reports/governance-change-impact.md`
- `generated/reports/source-document-intake-review-briefs.json`
- `generated/reports/source-document-intake-review-briefs.md`
- `generated/reports/source-document-intake-status.json`
- `generated/reports/source-document-intake-status.md`
- `generated/reports/source-document-requirement-delta.json`
- `generated/reports/source-document-requirement-delta.md`

### `ARCH-SA-REQ-001`

- Title: Solution Architecture Requirements Extract
- Source: `docs/governance/source-documents/ARCH-SA-SRC-001.requirements.md`
- Status: `intake`
- Owner: `architecture-owners`
- Version: `requirements-only-sanitized`
- Domains: `architecture`
- Lineage artifacts: `11`
- Source state: `active_source`
- Release consideration: `no_release_by_default`
- Review lanes: `architecture-review`

Derived artifact areas:

- `docs/governance/source-documents`

Suggested validation:

- `python3 -m unittest discover -s tests`
- `python3 scripts/validate_governance_repo.py`
- `python3 scripts/validate_runtime_governance.py`

Representative artifacts:

- `generated/reports/architecture-source-replacement-assessment.json`
- `generated/reports/architecture-source-replacement-assessment.md`
- `generated/reports/governance-change-impact.json`
- `generated/reports/governance-change-impact.md`
- `generated/reports/source-document-intake-review-briefs.json`
- `generated/reports/source-document-intake-review-briefs.md`
- `generated/reports/source-document-intake-status.json`
- `generated/reports/source-document-intake-status.md`
- `generated/reports/source-document-requirement-delta.json`
- `generated/reports/source-document-requirement-delta.md`

### `ARCH-PA-REQ-001`

- Title: Product Architecture Requirements Extract
- Source: `docs/governance/source-documents/ARCH-PA-SRC-001.requirements.md`
- Status: `intake`
- Owner: `architecture-owners`
- Version: `requirements-only-sanitized`
- Domains: `architecture`
- Lineage artifacts: `11`
- Source state: `active_source`
- Release consideration: `no_release_by_default`
- Review lanes: `architecture-review`

Derived artifact areas:

- `docs/governance/source-documents`

Suggested validation:

- `python3 -m unittest discover -s tests`
- `python3 scripts/validate_governance_repo.py`
- `python3 scripts/validate_runtime_governance.py`

Representative artifacts:

- `generated/reports/architecture-source-replacement-assessment.json`
- `generated/reports/architecture-source-replacement-assessment.md`
- `generated/reports/governance-change-impact.json`
- `generated/reports/governance-change-impact.md`
- `generated/reports/source-document-intake-review-briefs.json`
- `generated/reports/source-document-intake-review-briefs.md`
- `generated/reports/source-document-intake-status.json`
- `generated/reports/source-document-intake-status.md`
- `generated/reports/source-document-requirement-delta.json`
- `generated/reports/source-document-requirement-delta.md`

### `ARCH-GOV-REQ-001`

- Title: Architecture Governance Framework Requirements Extract
- Source: `docs/governance/source-documents/ARCH-GOV-SRC-002.requirements.md`
- Status: `intake`
- Owner: `architecture-owners`
- Version: `requirements-only-sanitized`
- Domains: `architecture`
- Lineage artifacts: `11`
- Source state: `active_source`
- Release consideration: `no_release_by_default`
- Review lanes: `architecture-review`

Derived artifact areas:

- `docs/governance/source-documents`

Suggested validation:

- `python3 -m unittest discover -s tests`
- `python3 scripts/validate_governance_repo.py`
- `python3 scripts/validate_runtime_governance.py`

Representative artifacts:

- `generated/reports/architecture-source-replacement-assessment.json`
- `generated/reports/architecture-source-replacement-assessment.md`
- `generated/reports/governance-change-impact.json`
- `generated/reports/governance-change-impact.md`
- `generated/reports/source-document-intake-review-briefs.json`
- `generated/reports/source-document-intake-review-briefs.md`
- `generated/reports/source-document-intake-status.json`
- `generated/reports/source-document-intake-status.md`
- `generated/reports/source-document-requirement-delta.json`
- `generated/reports/source-document-requirement-delta.md`

## Open Questions For Change Requests

- Is the new source document a new source, possible duplicate, or replacement candidate?
- Does the source document update change governance behavior or only explanatory text?
- Is the intended rollout report-only or blocking?
- Does the change require a release candidate or a new baseline release?
- Which downstream repositories need migration or communication?
