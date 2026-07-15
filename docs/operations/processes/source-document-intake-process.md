# Source Document Intake Process

## Purpose

This process applies only to upstream governance source documents that live
under `docs/governance/source-documents/` or are intentionally being introduced
there.

It keeps those source documents visible before they are used to change
controls, policies, schemas, baselines, or architecture runtime governance.

The current implementation is intentionally report-only. It does not promote
candidate documents, enable stricter gates, or change runtime governance
behavior.

Use `docs/operations/processes/source-document-intake-review-operating-model.md` when an
intake item needs a formal human review path across ADO architecture and
DevSecOps-as-Code.

## Applicability Rule

Use the full Source Document Intake process only when a change does at least one
of the following:

- adds or updates a file under `docs/governance/source-documents/`
- moves a document into `docs/governance/source-documents/`
- updates `model/documents/source-document-register.yaml`
- changes source-document status, replacement, supersession, retirement,
  similarity, lineage or derivation decisions

Do not run the full Source Document Intake process for ordinary documentation,
implementation notes, role models, runbooks, adapter templates, onboarding
guides, management readouts or generated reports unless they are intentionally
being promoted into `docs/governance/source-documents/`.

## Intake Data Sources

- Source files: `docs/governance/source-documents/`
- Source document register: `model/documents/source-document-register.yaml`
- Source document register schema: `schemas/source-document-register.schema.json`
- Lineage report: `generated/reports/source-lineage-report.md`
- Change impact report: `generated/reports/governance-change-impact.md`
- Architecture replacement assessment: `generated/reports/architecture-source-replacement-assessment.md`
- Intake status report: `generated/reports/source-document-intake-status.md`
- Intake review briefs: `generated/reports/source-document-intake-review-briefs.md`
- Requirement delta report: `generated/reports/source-document-requirement-delta.md`

## Non-Source Change Classification

Some repository documents explain, summarize, connect or operationalize
existing governance material without becoming new normative source documents.
Examples include strategic capability maps, operating-model explanations,
organisational role models, adapter guidance, implementation descriptions,
onboarding guides and management readouts.

For these documents, do not perform full Source Document Intake. Record a
lightweight classification in the change request instead, and do not add the
document to the source document register unless it is intentionally being made
an authoritative source for controls, architecture markers, policies, schemas,
evidence contracts or released baselines.

Use this classification when the document is explanatory:

| Intake field | Decision |
|---|---|
| Full source-document intake? | no |
| Source document? | no |
| Source document register update? | no |
| Intake classification | explanatory governance documentation, organisational documentation or technical implementation documentation |
| Source status | not applicable |
| Similarity assessment | not_relevant |
| Derivation allowed? | no new derivation from this document |
| Runtime behavior impact | none |
| Release impact | none unless a separate approved change modifies released artifacts |

The change request should still record:

- reviewed document path
- reason the document is not a source document
- whether the document is also not a formal governance document, where relevant
- whether the document summarizes existing approved or working material
- confirmation that no controls, architecture markers, policies, schemas,
  evidence contracts, workflows, templates, releases or baselines were derived
  from the document
- validation results

If a later review decides that text from the explanatory document should become
normative, create a separate change request and either move/register the
relevant source under `docs/governance/source-documents/` or update the approved
source that carries the normative authority.

## Status Model

| Status | Meaning |
|---|---|
| `candidate` | Received and registered, but not yet accepted as a source for derived governance behavior. |
| `draft` | Draft source material that needs a source-of-truth or approval decision before baseline use. |
| `intake` | Accepted into the repository intake model and linked to derived or operational artifacts. |
| `review` | Under active governance review. |
| `approved` | Accepted as an approved source. |
| `superseded` | Replaced by another registered source. |
| `retired` | Preserved for history, but no longer used for new derivation. |

## Stage 1 Status Report

Generate the source-document intake status report:

```bash
python3 scripts/generate_source_document_intake_status.py
```

The generator writes:

- `generated/reports/source-document-intake-status.json`
- `generated/reports/source-document-intake-status.md`

The report answers:

- how many source documents are registered by status, owner, and domain
- which candidate or draft documents still need review
- which documents are likely replacement candidates
- which documents have operational derived artifacts
- which next action is recommended per open item

Operational artifact counts intentionally exclude intake bookkeeping and impact
reports, so maintainers can see whether a source has actually influenced runtime
or release-facing governance.

## Agent-Assisted Review Briefs

The `source-document-intake` agent may prepare decision-support briefs for open
intake items:

```bash
python3 scripts/generate_source_document_intake_review_briefs.py
```

The generator writes:

- `generated/reports/source-document-intake-review-briefs.json`
- `generated/reports/source-document-intake-review-briefs.md`

The briefs are not decisions. They prepare:

- review focus per source document
- decision options
- required owner or architecture review input
- possible register updates
- release and validation considerations
- change-request decision fields

The final decision remains with the documented owner or reviewer and should be
recorded in a change request.

For formal reviews, treat the review brief as one input in the intake review
packet described in
`docs/operations/processes/source-document-intake-review-operating-model.md`.

## Requirement Delta Review

When a candidate may replace an existing source document, generate the
requirement-level delta:

```bash
python3 scripts/generate_source_document_requirement_delta.py
```

The generator writes:

- `generated/reports/source-document-requirement-delta.json`
- `generated/reports/source-document-requirement-delta.md`

The report extracts normative-looking statements from the candidate and current
source, then classifies them as:

- `added`
- `changed`
- `removed`
- `equivalent`

This helps reviewers see where requirements, review gates, evidence
expectations, quality markers or runtime-governance concerns may differ. The
classification is review support only. It does not replace architecture-owner
judgment and does not change source status, lineage, runtime governance,
policies, schemas or releases.

## Review Rules

- A `candidate` document must not be used to change runtime governance until a
  change request records the review decision.
- A likely replacement must be reviewed before moving lineage, changing
  `supersedes` or `superseded_by`, or planning a new baseline release.
- The agent may create decision templates, but must not promote, retire,
  supersede, or approve source documents autonomously.
- Draft policy or directive material should remain draft until the source of
  truth and approval path are confirmed.
- Promotion from `candidate` to `intake`, `review`, or `approved` should happen
  together with impact analysis and validation.

## Validation

The repository validator now checks that the intake status report can be
generated, that review briefs stay decision-support-only, and that requirement
deltas stay review-support-only:

```bash
python3 scripts/validate_governance_repo.py
python3 -m unittest discover -s tests
```

The validator fails if the intake status document count does not match the
source document register, or if the report claims to change runtime governance
or enable stricter rules. It also fails if review briefs enable autonomous
decisions or reference unknown source documents.

## Current Non-Goals

- no automatic promotion of source documents
- no mandatory Rhapsody, GitHub, Bitbucket, Bamboo, Codex, or Mistral dependency
- no stricter runtime gates
- no automatic release creation from candidate sources
