# Governance Change Request: Documentation Structure Audit

## Summary

- Add a documentation structure audit after the first documentation migration
  wave.
- Record completed migration packages, current stable zones, remaining root
  documentation and recommended next steps.
- Keep the change documentation-only without moving files or changing
  governance behavior.

## Change ID

```text
GCR-2026-015
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

The repository completed several small documentation migration packages. Before
additional moves are made, maintainers need a concise audit of:

- what changed
- which zones are now stable
- which files intentionally remain at the `docs/` root
- which future migrations are worth considering
- which compatibility decisions were made

This reduces the risk of continuing with blind cleanup after the initial
structure improvement wave.

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
| not applicable | unknown | This is an audit document, not a source-document replacement. |

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

- The change does not alter policies, controls, architecture markers, evidence
  contracts, schemas, OPA policies, workflows, status indexes or release
  packages.

## Release Decision

Choose one:

- [x] No release required
- [ ] Release candidate required
- [ ] Patch baseline release required
- [ ] Minor baseline release required
- [ ] Major baseline release required

Release notes:

- No baseline release is required because this is a documentation-only audit.

## Validation Plan

Confirm what must pass before merge.

- [x] `python3 scripts/validate_runtime_governance.py`
- [x] `python3 scripts/validate_governance_repo.py`
- [x] `python3 -m unittest discover -s tests`
- [x] Source lineage regenerated or confirmed unchanged
- [ ] Viewer regenerated if status or presentation changed
- [ ] Downstream example checked if consumer behavior changed

## Reviewer Notes

- Review whether the root-level file assessment is accurate.
- Review whether the recommended next steps are conservative enough before
  further documentation movement.
- `python3 -m mkdocs build --strict` was attempted but could not run in the
  local environment because the `mkdocs` Python module is not installed.
