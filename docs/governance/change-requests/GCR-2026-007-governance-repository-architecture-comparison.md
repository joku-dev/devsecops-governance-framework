# Governance Change Request

## Summary

- Add an English architecture and operating model comparison for the central
  governance repository model versus a non-repository governance approach.
- Clarify when the repository model is stronger and where a non-repository
  model may be sufficient.
- Keep the change documentation-only with no control, schema, policy, source
  register, release package or runtime behavior change.

## Change ID

```text
GCR-2026-007
```

## Source Document Intake

| Question | Answer |
|---|---|
| Full source-document intake required? | no |
| New or updated source document? | no |
| Source document path | not applicable |
| Reviewed non-source path | `docs/governance/governance-repository-architecture-comparison.md` |
| Intake classification | explanatory architecture and operating model comparison |
| Register updated? | no |
| Supersedes existing source? | no |
| Possible duplicate or replacement candidate? | no |
| Similarity assessment | not_relevant |
| Source status | not applicable |

## Non-Source Change Classification

This change is outside full Source Document Intake because it does not add or
update a file under `docs/governance/source-documents/` and does not update the
source document register.

Classification decision:

- The document is accepted as explanatory architecture and operating model
  comparison documentation.
- The document is not a normative source document.
- The document does not belong under `docs/governance/source-documents/`.
- The source document register remains unchanged.
- The document compares existing operating model options; it does not introduce
  new authoritative governance requirements by itself.
- No controls, architecture markers, policies, schemas, evidence contracts,
  workflows, releases or baselines may be derived from this document without a
  separate approved governance change request.
- Runtime governance behavior remains unchanged.

Classification record references:

- `docs/governance/governance-repository-architecture-comparison.md`
- `docs/governance/change-requests/GCR-2026-007-governance-repository-architecture-comparison.md`
- `docs/operations/source-document-intake-process.md`
- `model/documents/source-document-register.yaml`

## Why This Change Is Needed

The repository already contains several documents that explain its current
state, capability space, onboarding model and adapter strategy. It did not yet
contain one focused English document that compares the central governance
repository architecture with an alternative governance approach without a
central repository.

This comparison helps Enterprise Architecture, DevSecOps Governance, Platform
Engineering, Security, Audit and Software Industrialisation stakeholders
understand the architectural trade-offs.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | None. |
| DevSecOps controls | None. |
| Platform model | None. |
| Architecture governance | Documentation-only architecture comparison. |
| OPA policies | None. |
| Schemas and evidence contracts | None. |
| Viewer, status indexes or intake | None. |
| Release package or baseline | None. |
| Downstream repositories | None. |

## Replacement Review

Skipped because this change does not add or update a source document.

| Existing source ID | Similarity | Notes |
|---|---|---|
| not applicable | unknown | This is not a source-document replacement. |

Decision:

- [ ] New independent source
- [ ] Possible duplicate, keep as candidate
- [ ] Replacement candidate, review required
- [ ] Replacement confirmed
- [ ] Not relevant, retire candidate
- [x] Not a source-document replacement review item

Replacement notes:

- The new document is an explanatory comparison. It does not replace
  authoritative source documents.
- No candidate source exists and no retirement action is required.

## Derived Artifacts

- `docs/governance/governance-repository-architecture-comparison.md`
- Updates to MkDocs navigation, official entrypoints and AI index.

## Governance Behavior

Choose one:

- [x] Documentation-only
- [ ] Report-only governance behavior
- [ ] Blocking governance behavior
- [ ] Release packaging only

Notes:

- The document compares architecture and operating model options. It does not
  enable new runtime governance behavior.

## Release Decision

Choose one:

- [x] No release required
- [ ] Release candidate required
- [ ] Patch baseline release required
- [ ] Minor baseline release required
- [ ] Major baseline release required

Release notes:

- No baseline release is required because this is a documentation-only
  comparison with no executable governance changes.

## Validation Plan

Confirm what must pass before merge.

- [x] `python3 scripts/validate_runtime_governance.py`
- [x] `python3 scripts/validate_governance_repo.py`
- [x] `python3 -m unittest discover -s tests`
- [x] Source lineage regenerated or confirmed unchanged
- [ ] Viewer regenerated if status or presentation changed
- [ ] Downstream example checked if consumer behavior changed

MkDocs build validation should be run where `mkdocs` is installed. The current
local environment may not include that module.

## Reviewer Notes

- Confirm that the document accurately compares the repository model against a
  non-repository approach without implying new governance requirements.
- Confirm that the document remains non-source and documentation-only.
