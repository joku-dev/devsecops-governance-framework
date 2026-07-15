# Governance Change Request

## Summary

- Add a formal Source Document Intake Review Operating Model.
- Clarify how the Intake Agent supports ADO architecture and DevSecOps-as-Code
  intake reviews as one review system.
- Keep the change documentation-only with no source promotion, runtime behavior
  change, policy change, schema change, or release package change.

## Change ID

```text
GCR-2026-005
```

## Source Document Intake

| Question | Answer |
|---|---|
| Full source-document intake required? | no |
| New or updated source document? | no |
| Source document path | not applicable |
| Reviewed non-source path | `docs/operations/source-document-intake-review-operating-model.md` |
| Intake classification | explanatory governance process documentation |
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

- The document is accepted as explanatory governance process documentation.
- The document is not a normative source document.
- The document does not belong under `docs/governance/source-documents/`.
- The source document register remains unchanged.
- The document explains how official source-document reviews are performed; it
  does not introduce new authoritative governance requirements by itself.
- No controls, architecture markers, policies, schemas, evidence contracts,
  workflows, templates, releases or baselines may be derived from this document
  without a separate approved change request.
- Runtime governance behavior remains unchanged.

Classification record references:

- `docs/operations/source-document-intake-review-operating-model.md`
- `docs/governance/change-requests/GCR-2026-005-source-document-intake-review-operating-model.md`
- `docs/operations/source-document-intake-process.md`
- `model/documents/source-document-register.yaml`

Human review decision:

- Accept the document as the operating model for human source-document intake
  reviews.
- Keep source-document registration unchanged.
- Keep release decision as `No release required`.
- Keep governance behavior as `Documentation-only`.

## Why This Change Is Needed

ADO architecture source material and DevSecOps-as-Code source material should
appear as one governed system instead of two parallel review tracks. The
repository already contains the Intake Agent role, skill, reports, and
generators, but the human operating model for intake review needed to be made
explicit.

This change documents how the Intake Agent prepares decision support while the
Enterprise Architect, Governance Owner, baseline owners, and Release Manager
retain the human decisions.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | None. |
| DevSecOps controls | None. |
| Platform model | None. |
| Architecture governance | Documentation-only clarification of review flow. |
| OPA policies | None. |
| Schemas and evidence contracts | None. |
| Viewer, status indexes or intake | Documentation-only clarification of existing intake reports. |
| Release package or baseline | None. |
| Downstream repositories | No consuming repository is changed. Bamboo/Bitbucket usage is described as report-only review support. |

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

- The change adds an operating model for the review process. It does not add,
  replace, promote, supersede, or retire any registered source document.
- No candidate source exists and no retirement action is required.

## Derived Artifacts

- `docs/operations/source-document-intake-review-operating-model.md`
- Updates to source-document intake process documentation.
- Updates to AI index, official entrypoints, MkDocs navigation, and the
  Source Document Intake Agent role and skill references.

## Governance Behavior

Choose one:

- [x] Documentation-only
- [ ] Report-only governance behavior
- [ ] Blocking governance behavior
- [ ] Release packaging only

Notes:

- The operating model describes report-only review support and possible future
  Bamboo/Bitbucket publication of review reports. It does not enable any new
  blocking behavior.

## Release Decision

Choose one:

- [x] No release required
- [ ] Release candidate required
- [ ] Patch baseline release required
- [ ] Minor baseline release required
- [ ] Major baseline release required

Release notes:

- No baseline release is required because no executable governance behavior,
  schema, policy, workflow, source register, or release package changes.

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

- Confirm that the Intake Agent remains decision-support-only.
- Confirm that ADO architecture and DevSecOps review roles are clear enough for
  a joint intake review with the Enterprise Architect.
- Confirm that candidate-source derivation remains blocked until human review.
