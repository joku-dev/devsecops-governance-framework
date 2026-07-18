# Source Document Intake Status

Generated: `2026-07-18T10:45:05Z`

## Decision State

- Current state: `report_only`
- Runtime governance changed: `false`
- Stricter rules enabled: `false`

## Summary

- Registered source documents: `21`
- Open review items: `11`
- Replacement review items: `1`
- Documents with operational artifacts: `5`
- Documents without operational artifacts: `16`

## Status Counts

| Status | Count |
|---|---:|
| `candidate` | `6` |
| `draft` | `2` |
| `intake` | `10` |
| `review` | `3` |

## Review State Counts

| Review state | Count |
|---|---:|
| `accepted_intake` | `10` |
| `active_review_in_progress` | `3` |
| `candidate_related_source_review_required` | `1` |
| `candidate_replacement_review_required` | `1` |
| `candidate_similarity_review_required` | `4` |
| `draft_source_of_truth_decision_required` | `2` |

## Domain Counts

| Domain | Count |
|---|---:|
| `architecture` | `13` |
| `devsecops` | `9` |
| `directive` | `2` |
| `platform` | `3` |
| `policy` | `2` |

## Open Intake Items

| Source ID | Status | Owner | Review state | Next action |
|---|---|---|---|---|
| `DEVSECOPS-POL-SRC-001` | `draft` | `governance-owners` | `draft_source_of_truth_decision_required` | Confirm source-of-truth and approval path before treating the draft as a baseline source. |
| `DEVSECOPS-DIR-SRC-001` | `draft` | `governance-owners` | `draft_source_of_truth_decision_required` | Confirm source-of-truth and approval path before treating the draft as a baseline source. |
| `ARCH-TPL-SRC-001` | `candidate` | `architecture-owners` | `candidate_similarity_review_required` | Complete similarity review and decide whether the source is new, duplicate, replacement, or not relevant. |
| `ARCH-EA-SRC-001` | `candidate` | `architecture-owners` | `candidate_similarity_review_required` | Complete similarity review and decide whether the source is new, duplicate, replacement, or not relevant. |
| `ARCH-SA-SRC-001` | `candidate` | `architecture-owners` | `candidate_similarity_review_required` | Complete similarity review and decide whether the source is new, duplicate, replacement, or not relevant. |
| `ARCH-PA-SRC-001` | `candidate` | `architecture-owners` | `candidate_similarity_review_required` | Complete similarity review and decide whether the source is new, duplicate, replacement, or not relevant. |
| `ARCH-GOV-SRC-002` | `candidate` | `architecture-owners` | `candidate_replacement_review_required` | Review replacement decision before promoting the source or moving lineage. |
| `DEVSECOPS-POL-REQ-001` | `review` | `governance-owners` | `active_review_in_progress` | Complete review and record the intake decision. |
| `DEVSECOPS-DIR-REQ-001` | `review` | `governance-owners` | `active_review_in_progress` | Complete review and record the intake decision. |
| `ARCH-SDD-REQ-001` | `review` | `architecture-owners` | `active_review_in_progress` | Complete review and record the intake decision. |
| `CISO-REQ-SRC-001` | `candidate` | `governance-owners` | `candidate_related_source_review_required` | Confirm coexistence, scope boundaries, and approved derivation before promoting the related source. |

## Replacement Review Items

| Candidate source | Replaces | Owner | Classification | Next action |
|---|---|---|---|---|
| `ARCH-GOV-SRC-002` | `ARCH-SDD-SRC-001` | `architecture-owners` | `registered_replacement_candidate` | Review replacement decision before promoting the source or moving lineage. |

## Source Documents

| Source ID | Status | Domains | Review state | Operational artifacts |
|---|---|---|---|---:|
| `DEVSECOPS-POL-SRC-001` | `draft` | `policy, devsecops` | `draft_source_of_truth_decision_required` | `2` |
| `DEVSECOPS-DIR-SRC-001` | `draft` | `directive, devsecops` | `draft_source_of_truth_decision_required` | `2` |
| `DSCB-STD-SRC-001` | `intake` | `devsecops` | `accepted_intake` | `71` |
| `PRA-STD-SRC-001` | `intake` | `platform, devsecops` | `accepted_intake` | `18` |
| `ARCH-SDD-SRC-001` | `intake` | `architecture` | `accepted_intake` | `25` |
| `ARCH-TPL-SRC-001` | `candidate` | `architecture` | `candidate_similarity_review_required` | `0` |
| `ARCH-EA-SRC-001` | `candidate` | `architecture` | `candidate_similarity_review_required` | `0` |
| `ARCH-SA-SRC-001` | `candidate` | `architecture` | `candidate_similarity_review_required` | `0` |
| `ARCH-PA-SRC-001` | `candidate` | `architecture` | `candidate_similarity_review_required` | `0` |
| `ARCH-GOV-SRC-002` | `candidate` | `architecture` | `candidate_replacement_review_required` | `0` |
| `DEVSECOPS-POL-REQ-001` | `review` | `policy, devsecops` | `active_review_in_progress` | `0` |
| `DEVSECOPS-DIR-REQ-001` | `review` | `directive, devsecops` | `active_review_in_progress` | `0` |
| `DSCB-STD-REQ-001` | `intake` | `devsecops` | `accepted_intake` | `0` |
| `PRA-STD-REQ-001` | `intake` | `platform, devsecops` | `accepted_intake` | `0` |
| `ARCH-SDD-REQ-001` | `review` | `architecture` | `active_review_in_progress` | `0` |
| `ARCH-TPL-REQ-001` | `intake` | `architecture` | `accepted_intake` | `0` |
| `ARCH-EA-REQ-001` | `intake` | `architecture` | `accepted_intake` | `0` |
| `ARCH-SA-REQ-001` | `intake` | `architecture` | `accepted_intake` | `0` |
| `ARCH-PA-REQ-001` | `intake` | `architecture` | `accepted_intake` | `0` |
| `ARCH-GOV-REQ-001` | `intake` | `architecture` | `accepted_intake` | `0` |
| `CISO-REQ-SRC-001` | `candidate` | `devsecops, platform, architecture` | `candidate_related_source_review_required` | `0` |

## Process Notes

- Candidate and draft source documents remain non-blocking until a separate governance change confirms promotion.
- This report is informational and does not promote source documents or alter runtime governance.
- Operational artifact counts exclude intake bookkeeping and impact-report artifacts.
