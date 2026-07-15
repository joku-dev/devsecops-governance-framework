# Governance Change Request: MkDocs Validation Confirmation

## Summary

- Confirm local MkDocs validation using the existing `requirements-docs.txt`.
- Update the documentation structure audit with the reproducible local MkDocs
  command sequence.
- Record that `mkdocs build --strict` now passes in the local `.venv-docs/`
  environment.

## Change ID

```text
GCR-2026-016
```

## Source Document Intake

| Question | Answer |
|---|---|
| Full source-document intake required? | no |
| New or updated source document? | no |
| Source document path | not applicable |
| Reviewed non-source path | `docs/operations/document-structure-audit.md` |
| Register updated? | no |
| Supersedes existing source? | no |
| Possible duplicate or replacement candidate? | no |
| Similarity assessment | not_relevant |
| Source status | not applicable |

## Why This Change Is Needed

The documentation structure audit originally recorded that MkDocs could not be
run in the local environment because the `mkdocs` module was not installed.

The repository already contains `requirements-docs.txt`, and `.venv-docs/` is
ignored by Git. Installing the documentation requirements into that local
environment makes `mkdocs build --strict` reproducible without changing runtime
governance behavior.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | None |
| DevSecOps controls | None |
| Platform model | None |
| Architecture governance | None |
| OPA policies | None |
| Schemas and evidence contracts | None |
| Viewer, status indexes or intake | None |
| Release package or baseline | None |
| Downstream repositories | None |

## Replacement Review

| Existing source ID | Similarity | Notes |
|---|---|---|
| not applicable | unknown | This is a validation documentation update, not a source-document replacement. |

Decision:

- [ ] New independent source
- [ ] Possible duplicate, keep as candidate
- [ ] Replacement candidate, review required
- [ ] Replacement confirmed
- [ ] Not relevant, retire candidate
- [x] Not a source-document replacement review item

Replacement notes:

- No files under `docs/governance/source-documents/` are added, moved or
  changed.

## Derived Artifacts

- `docs/operations/document-structure-audit.md`

## Governance Behavior

Choose one:

- [x] Documentation-only
- [ ] Report-only governance behavior
- [ ] Blocking governance behavior
- [ ] Release packaging only

Notes:

- This change records validation capability only. It does not alter any
  governance behavior, schemas, policies, workflows or release package content.

## Release Decision

Choose one:

- [x] No release required
- [ ] Release candidate required
- [ ] Patch baseline release required
- [ ] Minor baseline release required
- [ ] Major baseline release required

Release notes:

- No baseline release is required because this is a documentation-only
  validation status update.

## Validation Plan

Confirm what must pass before merge.

- [x] `python3 scripts/validate_runtime_governance.py`
- [x] `python3 scripts/validate_governance_repo.py`
- [x] `python3 -m unittest discover -s tests`
- [x] `.venv-docs/bin/mkdocs build --strict`
- [x] Source lineage regenerated or confirmed unchanged
- [ ] Viewer regenerated if status or presentation changed
- [ ] Downstream example checked if consumer behavior changed

## Reviewer Notes

- The local `.venv-docs/` environment is intentionally not committed.
- `mkdocs build --strict` may emit informational messages for source documents
  and pages that are intentionally outside navigation, but the build passed.
