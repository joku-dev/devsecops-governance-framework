# Governance Change Impact Report

Generated: `2026-10-08T20:06:49Z`

## Inputs

- Source document register: `model/documents/source-document-register.yaml`
- Source lineage report: `generated/reports/source-lineage-report.json`

## Summary

- Registered source documents: `15`
- Source documents with lineage: `16`
- Derived artifact links: `307`

## Domain Coverage

| Domain | Source documents |
|---|---:|
| `architecture` | `9` |
| `devsecops` | `9` |
| `directive` | `2` |
| `platform` | `4` |
| `policy` | `2` |

## Release Considerations

| Consideration | Source documents |
|---|---:|
| `baseline_release_review` | `2` |
| `no_release_by_default` | `12` |
| `release_candidate_recommended` | `1` |

## Review Lanes

| Review lane | Source documents |
|---|---:|
| `architecture-review` | `9` |
| `devsecops-review` | `9` |
| `governance-review` | `4` |
| `platform-review` | `4` |
| `policy-as-code-review` | `2` |
| `release-review` | `2` |
| `schema-review` | `3` |
| `viewer-status-review` | `3` |

## Source Impact Details

### `DEVSECOPS-POL-REQ-001`

- Title: DevSecOps Policy Requirements Extract
- Source: `docs/governance/source-documents/DEVSECOPS-POL-SRC-001.requirements.md`
- Status: `review`
- Owner: `governance-owners`
- Version: `requirements-only-sanitized`
- Domains: `policy, devsecops`
- Lineage artifacts: `13`
- Source state: `active_source`
- Release consideration: `no_release_by_default`
- Review lanes: `devsecops-review, governance-review`

Derived artifact areas:

- `docs/governance/source-documents`

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

### `DEVSECOPS-DIR-REQ-001`

- Title: DevSecOps Directive Requirements Extract
- Source: `docs/governance/source-documents/DEVSECOPS-DIR-SRC-001.requirements.md`
- Status: `review`
- Owner: `governance-owners`
- Version: `requirements-only-sanitized`
- Domains: `directive, devsecops`
- Lineage artifacts: `13`
- Source state: `active_source`
- Release consideration: `no_release_by_default`
- Review lanes: `devsecops-review, governance-review`

Derived artifact areas:

- `docs/governance/source-documents`

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

### `DSCB-STD-REQ-001`

- Title: DevSecOps Control Baseline Requirements Extract
- Source: `docs/governance/source-documents/DSCB-STD-SRC-001.requirements.md`
- Status: `intake`
- Owner: `devsecops-owners`
- Version: `requirements-only-sanitized`
- Domains: `devsecops`
- Lineage artifacts: `99`
- Source state: `active_source`
- Release consideration: `baseline_release_review`
- Review lanes: `devsecops-review, policy-as-code-review, release-review, schema-review, viewer-status-review`

Derived artifact areas:

- `docs/governance/source-documents`

Suggested validation:

- `python3 -m unittest discover -s tests`
- `python3 scripts/generate_status_viewer.py`
- `python3 scripts/validate_governance_repo.py`
- `verify release package metadata and checksums`

Representative artifacts:

- `.github/CODEOWNERS`
- `.github/dependabot.yml`
- `.github/workflows/codeql.yml`
- `.github/workflows/dependency-review.yml`
- `.github/workflows/governance-repository-security.yml`
- `SECURITY.md`
- `docs/demos/demo-consumer-typed-evidence-trust.md`
- `docs/demos/presentation-guide-typed-evidence-trust-de.md`
- `docs/examples/evidence-collector-record.example.json`
- `docs/examples/evidence-trust-record.example.json`

### `PRA-STD-REQ-001`

- Title: Platform Reference Architecture Requirements Extract
- Source: `docs/governance/source-documents/PRA-STD-SRC-001.requirements.md`
- Status: `intake`
- Owner: `platform-owners`
- Version: `requirements-only-sanitized`
- Domains: `platform, devsecops`
- Lineage artifacts: `41`
- Source state: `active_source`
- Release consideration: `release_candidate_recommended`
- Review lanes: `devsecops-review, platform-review, schema-review, viewer-status-review`

Derived artifact areas:

- `docs/governance/source-documents`

Suggested validation:

- `python3 -m unittest discover -s tests`
- `python3 scripts/generate_status_viewer.py`
- `python3 scripts/validate_governance_repo.py`

Representative artifacts:

- `.github/CODEOWNERS`
- `.github/dependabot.yml`
- `.github/workflows/codeql.yml`
- `.github/workflows/dependency-review.yml`
- `.github/workflows/governance-repository-security.yml`
- `SECURITY.md`
- `docs/examples/governance-repository-security-observation.example.json`
- `docs/governance/source-documents/PRA-STD-SRC-001.requirements.md`
- `docs/operations/security/governance-repository-self-security.md`
- `generated/reports/architecture-source-replacement-assessment.json`

### `ARCH-SDD-REQ-001`

- Title: Integrated SDD Architecture Governance Requirements Extract
- Source: `docs/governance/source-documents/ARCH-SDD-SRC-001.requirements.md`
- Status: `review`
- Owner: `architecture-owners`
- Version: `requirements-only-sanitized`
- Domains: `architecture`
- Lineage artifacts: `31`
- Source state: `active_source`
- Release consideration: `baseline_release_review`
- Review lanes: `architecture-review, policy-as-code-review, release-review, schema-review, viewer-status-review`

Derived artifact areas:

- `docs/governance/source-documents`

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
- Status: `candidate`
- Owner: `architecture-owners`
- Version: `requirements-only-sanitized`
- Domains: `architecture`
- Lineage artifacts: `11`
- Source state: `candidate_replacement_review`
- Release consideration: `no_release_by_default`
- Review lanes: `architecture-review`

Derived artifact areas:


Replacement and similarity:

- Candidate replacement for: `ARCH-SDD-REQ-001`
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

### `CISO-REQ-SRC-001`

- Title: CISO Standards Requirements Catalog Candidate
- Source: `docs/governance/source-documents/CISO-REQ-SRC-001.candidate-intake.md`
- Status: `candidate`
- Owner: `governance-owners`
- Version: `0.1`
- Domains: `devsecops, platform, architecture`
- Lineage artifacts: `11`
- Source state: `candidate_related_source_review`
- Release consideration: `no_release_by_default`
- Review lanes: `architecture-review, devsecops-review, platform-review`

Derived artifact areas:


Replacement and similarity:

- Similarity assessment: `related_source`

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

### `DEVSECOPS-POL-CAND-002`

- Title: DevSecOps Policy Integrated v2 Change-Marked Candidate
- Source: `docs/governance/source-documents/DevSecOps_Policy_Review_Integrated_v2_CHANGE_MARKED.md`
- Status: `candidate`
- Owner: `governance-owners`
- Version: `v2-change-marked`
- Domains: `policy, devsecops`
- Lineage artifacts: `11`
- Source state: `candidate_replacement_review`
- Release consideration: `no_release_by_default`
- Review lanes: `devsecops-review, governance-review`

Derived artifact areas:


Replacement and similarity:

- Candidate replacement for: `DEVSECOPS-POL-REQ-001`
- Similarity assessment: `replacement_candidate`

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

### `TOOLCHAIN-ARCH-CAND-001`

- Title: Enterprise SDLC Toolchain Reference Architecture v0.3
- Source: `docs/governance/source-documents/Enterprise_SDLC_Toolchain_Reference_Architecture_v0.3.md`
- Status: `candidate`
- Owner: `platform-owners`
- Version: `v0.3`
- Domains: `architecture, platform, devsecops`
- Lineage artifacts: `11`
- Source state: `candidate_related_source_review`
- Release consideration: `no_release_by_default`
- Review lanes: `architecture-review, devsecops-review, platform-review`

Derived artifact areas:


Replacement and similarity:

- Similarity assessment: `related_source`

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

### `SDLC-PROC-CAND-001`

- Title: Software Development Process DevSecOps V5 Activity RACI and Artifacts
- Source: `docs/governance/source-documents/Software_Development_Process_DevSecOps_V5_Activity_RACI_Artifacts.md`
- Status: `candidate`
- Owner: `governance-owners`
- Version: `V5-candidate`
- Domains: `devsecops, directive`
- Lineage artifacts: `11`
- Source state: `candidate_related_source_review`
- Release consideration: `no_release_by_default`
- Review lanes: `devsecops-review, governance-review`

Derived artifact areas:


Replacement and similarity:

- Similarity assessment: `related_source`

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

### `SW-INDUSTRIALISATION-OM-CAND-001`

- Title: Software Industrialisation Enterprise Operating Model Proposal
- Source: `docs/governance/source-documents/Software_Industrialisation_Enterprise_Operating_Model_revised_extended_scope_polished.md`
- Status: `candidate`
- Owner: `governance-owners`
- Version: `revised-extended-scope-polished-proposal`
- Domains: `devsecops, platform, architecture`
- Lineage artifacts: `11`
- Source state: `candidate_related_source_review`
- Release consideration: `no_release_by_default`
- Review lanes: `architecture-review, devsecops-review, platform-review`

Derived artifact areas:


Replacement and similarity:

- Similarity assessment: `related_source`

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
