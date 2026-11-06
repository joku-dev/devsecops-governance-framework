---
name: source-document-intake
description: Register and classify incoming governance source documents, prepare human decision briefs, and prevent candidate-source derivation before review.
---

# Source Document Intake Workflow

## Workflow

1. Read `docs/governance/governance-roles-and-agent-profiles.md`, `.agents/roles/source-document-intake.yaml`, and `docs/operations/processes/source-document-intake-review-operating-model.md`.
2. Inspect changed files under `docs/governance/source-documents/` and `model/documents/`; use `docs/governance/change-requests/` only as supporting decision context.
3. If no source document or source-document register change exists, report that full Source Document Intake is not required and use only the change-request classification.
4. Classify each source as new, duplicate, replacement candidate, superseding source, or retired source.
5. Require `candidate` status for possible replacements until review confirms promotion.
6. Generate or review `generated/reports/source-document-intake-status.md`.
7. Prepare review briefs with decision options using `generated/reports/source-document-intake-review-briefs.md` and the intake review packet model.
8. For likely replacement candidates, generate requirement-level deltas using `generated/reports/source-document-requirement-delta.md`.
9. Extract only explicitly labelled requirement declarations such as `DSCB-L1-REQ-001`. Do not infer requirements from prose, SHALL/MUST keywords, headings, version history, reference-only mentions or synthetic extraction row IDs. Classify explicit identifiers as `author_identified`/`p1` only when the register verifies author-provided provenance; otherwise use `explicit_identifier`/`unassigned`.
10. Verify that no controls, architecture markers, OPA policies, schemas, or release packages were derived from a candidate before review.
11. Escalate the final source decision to the documented owner or change-request reviewer.

## Decision Boundaries

The agent may prepare:

- source classification evidence
- likely review focus
- decision options
- register update candidates
- requirement-level added, changed, removed, and equivalent summaries
- explicit requirement identification and priority, with verified `author_identified`/`p1` and unverified `explicit_identifier`/`unassigned` separated; no prose-derived candidates
- validation and release considerations
- change-request text snippets

The agent must not:

- promote a candidate source
- retire a source
- confirm a replacement
- change `supersedes` or `superseded_by`
- derive runtime governance from an unreviewed candidate

## Validation

Run or request:

```bash
python3 scripts/generate_source_document_intake_status.py
python3 scripts/generate_source_document_intake_review_briefs.py
python3 scripts/generate_source_document_requirement_delta.py
python3 scripts/generate_governance_change_impact_report.py
python3 scripts/validate_governance_repo.py
```

## Output

Report source classification, review brief, decision options, requirement delta summary for replacement candidates, requirement identification classes and intake priority, human decision requirement, required change request, derivation status, and validation results. Use `author_identified`/`p1` only for source identifiers whose author-provided provenance is recorded; use `explicit_identifier`/`unassigned` when that provenance is not recorded. Do not generate requirements from prose or synthetic row identifiers. Preserve historical decisions and source text. An identifier does not itself confer normative status; keep source approval status separate from intake priority and delta review priority.
