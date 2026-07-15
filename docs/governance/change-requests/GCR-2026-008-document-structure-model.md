# Governance Change Request: Documentation Structure Model

## Summary

- Add an English documentation structure model for the `docs/` tree.
- Define stable documentation zones, document classes and migration rules.
- Clarify that future documentation restructuring should be incremental and
  should not change source intake or release baselines by accident.

## Change ID

```text
GCR-2026-008
```

## Source Document Intake

| Question | Answer |
|---|---|
| Full source-document intake required? | no |
| New or updated source document? | no |
| Source document path | not applicable |
| Reviewed non-source path | `docs/operations/document-structure-model.md` |
| Register updated? | no |
| Supersedes existing source? | no |
| Possible duplicate or replacement candidate? | no |
| Similarity assessment | not_relevant |
| Source status | not applicable |

## Why This Change Is Needed

The documentation set has grown across governance, operations, onboarding,
platform, releases, demos and generated-report references.

The repository now needs a lightweight structure model so future documentation
changes can improve navigation without destabilising:

- source document lineage
- governance change records
- release references
- MkDocs navigation
- AI and human entrypoints
- downstream repository links

This change establishes guidance before any larger file movement happens.

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
| Downstream repositories | None; documentation-only guidance |

## Replacement Review

| Existing source ID | Similarity | Notes |
|---|---|---|
| not applicable | unknown | This change does not add or replace a source document. |

Decision:

- [ ] New independent source
- [ ] Possible duplicate, keep as candidate
- [ ] Replacement candidate, review required
- [ ] Replacement confirmed
- [ ] Not relevant, retire candidate
- [x] Not a source-document replacement review item

Replacement notes:

- The new document complements
  `docs/operations/repository-target-structure-and-migration-plan.md` and does
  not replace a source document.

## Derived Artifacts

- `docs/operations/document-structure-model.md`
- `mkdocs.yml`
- `docs/official-entrypoints.md`
- `docs/ai-index.md`

## Governance Behavior

Choose one:

- [x] Documentation-only
- [ ] Report-only governance behavior
- [ ] Blocking governance behavior
- [ ] Release packaging only

Notes:

- No policy, control, architecture marker, schema, OPA rule, release package or
  operational workflow behavior is changed.

## Release Decision

Choose one:

- [x] No release required
- [ ] Release candidate required
- [ ] Patch baseline release required
- [ ] Minor baseline release required
- [ ] Major baseline release required

Release notes:

- No baseline release is required because this is a documentation-only
  structure model.

## Validation Plan

Confirm what must pass before merge.

- [x] `python3 scripts/validate_runtime_governance.py`
- [x] `python3 scripts/validate_governance_repo.py`
- [x] `python3 -m unittest discover -s tests`
- [x] Source lineage regenerated or confirmed unchanged
- [ ] Viewer regenerated if status or presentation changed
- [ ] Downstream example checked if consumer behavior changed

## Reviewer Notes

- Review whether the proposed document classes are clear enough for future AI
  agents and human maintainers.
- Review whether the first migration packages are appropriately small and safe.
- `python3 -m mkdocs build --strict` was attempted but could not run in the
  local environment because the `mkdocs` Python module is not installed.
