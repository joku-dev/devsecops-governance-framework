# Governance Change Request

## Summary

- Move the DevSecOps Governance Organisational Role Model from the repository root into the controlled governance documentation structure.
- Add the role model to the MkDocs navigation, official entrypoints and AI index.
- Keep the change documentation-only with no changes to controls, schemas, OPA policies, releases or source-document registration.

## Change ID

```text
GCR-2026-003
```

## Source Document Intake

| Question | Answer |
|---|---|
| Full source-document intake required? | no |
| New or updated source document? | no |
| Source document path | not applicable |
| Reviewed non-source path | `docs/governance/devsecops-governance-organisational-role-model.md` |
| Intake classification | explanatory organisational documentation |
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

- The document is accepted as explanatory organisational documentation.
- The document is not a formal governance document in the Policy, Directive or
  Standard sense.
- The document is not a normative source document.
- The document does not belong under `docs/governance/source-documents/`.
- The source document register remains unchanged.
- The document describes organisational responsibilities and role boundaries; it
  does not introduce new authoritative governance requirements by itself.
- No controls, architecture markers, policies, schemas, evidence contracts,
  workflows, releases or baselines may be derived from this document without a
  separate approved governance change request.
- Runtime governance behavior remains unchanged.

Classification record references:

- `docs/governance/devsecops-governance-organisational-role-model.md`
- `docs/governance/change-requests/GCR-2026-003-devsecops-organisational-role-model.md`
- `docs/operations/source-document-intake-process.md`
- `model/documents/source-document-register.yaml`

Human review decision:

- Accept the change as an organisational role model and responsibility
  explanation.
- Keep source-document registration unchanged.
- Keep release decision as `No release required`.
- Keep governance behavior as `Documentation-only`.

## Why This Change Is Needed

The organisational role model was present at repository root as an untracked working document. Because it defines organisational responsibilities for DevSecOps Governance-as-Code, the appropriate repository location is under `docs/governance/` alongside the operating model and integrated ADO / DevSecOps governance model.

This keeps governance role material discoverable through the normal documentation structure and avoids leaving controlled governance content as a loose root-level file.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | None. |
| DevSecOps controls | None. |
| Platform model | None. |
| Architecture governance | Documentation alignment only. |
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

- This change moves a working role model into the governance documentation structure. It does not replace authoritative source documents.
- No candidate source exists and no retirement action is required.

## Derived Artifacts

- `docs/governance/devsecops-governance-organisational-role-model.md`
- `mkdocs.yml` navigation entry
- `docs/official-entrypoints.md` entry
- `docs/ai-index.md` orientation entry

## Governance Behavior

Choose one:

- [x] Documentation-only
- [ ] Report-only governance behavior
- [ ] Blocking governance behavior
- [ ] Release packaging only

Notes:

- No executable governance behavior is changed.

## Release Decision

Choose one:

- [x] No release required
- [ ] Release candidate required
- [ ] Patch baseline release required
- [ ] Minor baseline release required
- [ ] Major baseline release required

Release notes:

- No baseline release is required because this is a documentation-only structure change.

## Validation Plan

Confirm what must pass before merge.

- [x] `python3 scripts/validate_runtime_governance.py`
- [x] `python3 scripts/validate_governance_repo.py`
- [x] `python3 -m unittest discover -s tests`
- [ ] Source lineage regenerated or confirmed unchanged
- [ ] Viewer regenerated if status or presentation changed
- [ ] Downstream example checked if consumer behavior changed

For this documentation-only change, repository validation is sufficient unless reviewers request the full suite.

MkDocs build validation was attempted with `python3 -m mkdocs build --strict`, but the local environment does not have the `mkdocs` module installed.

## Reviewer Notes

- Confirm that the role model belongs under governance documentation and not under source documents.
- Confirm that the document remains non-executable and does not imply a baseline, schema or policy change.
