# Governance Change Request: Status Documentation Migration

## Summary

- Move status and lessons-learned operation documents into
  `docs/operations/status/`.
- Group current platform state, ha-CPsWMS validation status and ha-CPsWMS
  lessons learned under one MkDocs navigation node.
- Keep the change structural and documentation-focused without changing status
  indexes, viewer semantics, evidence contracts or baselines.

## Change ID

```text
GCR-2026-017
```

## Source Document Intake

| Question | Answer |
|---|---|
| Full source-document intake required? | no |
| New or updated source document? | no |
| Source document path | not applicable |
| Reviewed non-source path | `docs/operations/status/` |
| Register updated? | no |
| Supersedes existing source? | no |
| Possible duplicate or replacement candidate? | no |
| Similarity assessment | not_relevant |
| Source status | not applicable |

## Why This Change Is Needed

The operations root still contained current state, validation status and lessons
learned documents after the first documentation migration wave.

Moving these documents into `docs/operations/status/` makes the status surface
easier to find and separates current-state reporting from runbooks, processes,
evidence handling and platform adapters.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | None |
| DevSecOps controls | None |
| Platform model | None |
| Architecture governance | None |
| OPA policies | None |
| Schemas and evidence contracts | None |
| Viewer, status indexes or intake | Documentation links only |
| Release package or baseline | None |
| Downstream repositories | Low; active documentation paths moved within MkDocs navigation |

## Replacement Review

| Existing source ID | Similarity | Notes |
|---|---|---|
| not applicable | unknown | This is a documentation move, not a source-document replacement. |

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

- `docs/operations/status/current-governance-platform-state.md`
- `docs/operations/status/ha-cpswms-governance-validation-status.md`
- `docs/operations/status/ha-cpswms-governance-lessons-learned.md`
- `mkdocs.yml`
- `docs/official-entrypoints.md`
- `docs/ai-index.md`
- `docs/operations/document-structure-audit.md`
- `docs/operations/document-structure-model.md`
- active cross-document and viewer-generator references

## Governance Behavior

Choose one:

- [x] Documentation-only
- [ ] Report-only governance behavior
- [ ] Blocking governance behavior
- [ ] Release packaging only

Notes:

- The change does not alter status indexes, viewer semantics, result intake,
  schemas, evidence contracts, OPA policies, workflows or release content.

## Release Decision

Choose one:

- [x] No release required
- [ ] Release candidate required
- [ ] Patch baseline release required
- [ ] Minor baseline release required
- [ ] Major baseline release required

Release notes:

- No baseline release is required because this is a documentation structure
  migration only.

## Validation Plan

Confirm what must pass before merge.

- [x] `python3 scripts/validate_runtime_governance.py`
- [x] `python3 scripts/validate_governance_repo.py`
- [x] `python3 -m unittest discover -s tests`
- [x] `.venv-docs/bin/mkdocs build --strict`
- [x] Source lineage regenerated or confirmed unchanged
- [x] Viewer regenerated if status or presentation changed
- [ ] Downstream example checked if consumer behavior changed

## Reviewer Notes

- Review whether the moved paths are correctly reflected in MkDocs navigation,
  official entrypoints, AI index, role paths, reading compass, index page and
  viewer-generator links.
