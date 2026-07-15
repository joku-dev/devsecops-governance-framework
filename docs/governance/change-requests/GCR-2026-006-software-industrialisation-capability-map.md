# Governance Change Request

## Summary

- Add a strategic Software Industrialisation Problem and Capability Map.
- Explain the repository as a coherent answer to software industrialisation
  problems across governance, architecture, DevSecOps, evidence, platform
  adapters, releases and result intake.
- Keep the change documentation-only with no control, schema, policy, source
  register, release package or runtime behavior change.

## Change ID

```text
GCR-2026-006
```

## Source Document Intake

| Question | Answer |
|---|---|
| Full source-document intake required? | no |
| New or updated source document? | no |
| Source document path | not applicable |
| Reviewed non-source path | `docs/governance/software-industrialisation-problem-capability-map.md` |
| Intake classification | explanatory governance documentation |
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

- The document is accepted as explanatory governance documentation.
- The document is not a normative source document.
- The document does not belong under `docs/governance/source-documents/`.
- The source document register remains unchanged.
- The document summarizes and connects existing repository capabilities; it does
  not introduce new authoritative requirements.
- No controls, architecture markers, policies, schemas, evidence contracts,
  workflows, templates, releases or baselines may be derived from this document
  without a separate approved change request.
- Runtime governance behavior remains unchanged.

Classification record references:

- `docs/governance/software-industrialisation-problem-capability-map.md`
- `docs/governance/change-requests/GCR-2026-006-software-industrialisation-capability-map.md`
- `docs/operations/source-document-intake-process.md`
- `docs/operations/source-document-intake-review-operating-model.md`
- `model/documents/source-document-register.yaml`

Human review decision:

- Accept the document as a strategic explanation of the existing repository
  capability space.
- Keep source-document registration unchanged.
- Keep release decision as `No release required`.
- Keep governance behavior as `Documentation-only`.

## Why This Change Is Needed

The repository contains many strong individual documents and capabilities, but
it needed one connected narrative that explains the industrialisation problem
space and how the repository capability space answers it.

The new document is intended for Enterprise Architecture, DevSecOps Governance,
Platform, Security, Audit and management stakeholders who need to understand
why this repository is more than a documentation repository or CI template
collection.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | None. |
| DevSecOps controls | None. |
| Platform model | None. |
| Architecture governance | Documentation-only strategic explanation. |
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

- The change adds a strategic capability map. It does not add, replace,
  promote, supersede or retire any registered source document.
- No candidate source exists and no retirement action is required.

## Derived Artifacts

- `docs/governance/software-industrialisation-problem-capability-map.md`
- Updates to MkDocs navigation, official entrypoints and AI index.

## Governance Behavior

Choose one:

- [x] Documentation-only
- [ ] Report-only governance behavior
- [ ] Blocking governance behavior
- [ ] Release packaging only

Notes:

- The document explains existing capabilities and target-state value. It does
  not enable new runtime governance behavior.

## Release Decision

Choose one:

- [x] No release required
- [ ] Release candidate required
- [ ] Patch baseline release required
- [ ] Minor baseline release required
- [ ] Major baseline release required

Release notes:

- No baseline release is required because this is a documentation-only strategic
  explanation with no executable governance changes.

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

- Confirm that the document accurately represents current repository
  capabilities and does not imply unimplemented blocking behavior.
- Confirm that the narrative is suitable for Enterprise Architecture and
  Software Industrialisation discussions.
