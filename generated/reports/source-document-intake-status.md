# Source Document Intake Status

Generated: `2026-10-08T20:06:50Z`

## Decision State

- Current state: `report_only`
- Runtime governance changed: `false`
- Stricter rules enabled: `false`

## Summary

- Registered source documents: `15`
- Open review items: `9`
- Replacement review items: `2`
- Documents with operational artifacts: `5`
- Documents without operational artifacts: `10`

## Status Counts

| Status | Count |
|---|---:|
| `candidate` | `6` |
| `intake` | `6` |
| `review` | `3` |

## Review State Counts

| Review state | Count |
|---|---:|
| `accepted_intake` | `6` |
| `active_review_in_progress` | `3` |
| `candidate_related_source_review_required` | `4` |
| `candidate_replacement_review_required` | `2` |

## Domain Counts

| Domain | Count |
|---|---:|
| `architecture` | `9` |
| `devsecops` | `9` |
| `directive` | `2` |
| `platform` | `4` |
| `policy` | `2` |

## Open Intake Items

| Source ID | Status | Owner | Review state | Next action |
|---|---|---|---|---|
| `DEVSECOPS-POL-REQ-001` | `review` | `governance-owners` | `active_review_in_progress` | Complete review and record the intake decision. |
| `DEVSECOPS-DIR-REQ-001` | `review` | `governance-owners` | `active_review_in_progress` | Complete review and record the intake decision. |
| `ARCH-SDD-REQ-001` | `review` | `architecture-owners` | `active_review_in_progress` | Complete review and record the intake decision. |
| `ARCH-GOV-REQ-001` | `candidate` | `architecture-owners` | `candidate_replacement_review_required` | Review replacement decision before promoting the source or moving lineage. |
| `CISO-REQ-SRC-001` | `candidate` | `governance-owners` | `candidate_related_source_review_required` | Confirm coexistence, scope boundaries, and approved derivation before promoting the related source. |
| `DEVSECOPS-POL-CAND-002` | `candidate` | `governance-owners` | `candidate_replacement_review_required` | Review replacement decision before promoting the source or moving lineage. |
| `TOOLCHAIN-ARCH-CAND-001` | `candidate` | `platform-owners` | `candidate_related_source_review_required` | Confirm coexistence, scope boundaries, and approved derivation before promoting the related source. |
| `SDLC-PROC-CAND-001` | `candidate` | `governance-owners` | `candidate_related_source_review_required` | Confirm coexistence, scope boundaries, and approved derivation before promoting the related source. |
| `SW-INDUSTRIALISATION-OM-CAND-001` | `candidate` | `governance-owners` | `candidate_related_source_review_required` | Confirm coexistence, scope boundaries, and approved derivation before promoting the related source. |

## Replacement Review Items

| Candidate source | Replaces | Owner | Classification | Next action |
|---|---|---|---|---|
| `ARCH-GOV-REQ-001` | `ARCH-SDD-REQ-001` | `architecture-owners` | `registered_replacement_candidate` | Review replacement decision before promoting the source or moving lineage. |
| `DEVSECOPS-POL-CAND-002` | `DEVSECOPS-POL-REQ-001` | `governance-owners` | `registered_replacement_candidate` | Review replacement decision before promoting the source or moving lineage. |

## Source Documents

| Source ID | Status | Domains | Review state | Operational artifacts |
|---|---|---|---|---:|
| `DEVSECOPS-POL-REQ-001` | `review` | `policy, devsecops` | `active_review_in_progress` | `2` |
| `DEVSECOPS-DIR-REQ-001` | `review` | `directive, devsecops` | `active_review_in_progress` | `2` |
| `DSCB-STD-REQ-001` | `intake` | `devsecops` | `accepted_intake` | `88` |
| `PRA-STD-REQ-001` | `intake` | `platform, devsecops` | `accepted_intake` | `30` |
| `ARCH-SDD-REQ-001` | `review` | `architecture` | `active_review_in_progress` | `20` |
| `ARCH-TPL-REQ-001` | `intake` | `architecture` | `accepted_intake` | `0` |
| `ARCH-EA-REQ-001` | `intake` | `architecture` | `accepted_intake` | `0` |
| `ARCH-SA-REQ-001` | `intake` | `architecture` | `accepted_intake` | `0` |
| `ARCH-PA-REQ-001` | `intake` | `architecture` | `accepted_intake` | `0` |
| `ARCH-GOV-REQ-001` | `candidate` | `architecture` | `candidate_replacement_review_required` | `0` |
| `CISO-REQ-SRC-001` | `candidate` | `devsecops, platform, architecture` | `candidate_related_source_review_required` | `0` |
| `DEVSECOPS-POL-CAND-002` | `candidate` | `policy, devsecops` | `candidate_replacement_review_required` | `0` |
| `TOOLCHAIN-ARCH-CAND-001` | `candidate` | `architecture, platform, devsecops` | `candidate_related_source_review_required` | `0` |
| `SDLC-PROC-CAND-001` | `candidate` | `devsecops, directive` | `candidate_related_source_review_required` | `0` |
| `SW-INDUSTRIALISATION-OM-CAND-001` | `candidate` | `devsecops, platform, architecture` | `candidate_related_source_review_required` | `0` |

## Process Notes

- Candidate and draft source documents remain non-blocking until a separate governance change confirms promotion.
- This report is informational and does not promote source documents or alter runtime governance.
- Operational artifact counts exclude intake bookkeeping and impact-report artifacts.
