# Governance Change Request: Demo Documentation Migration

## Summary

- Move demo and ha-CPsWMS result explanation documents into `docs/demos/`.
- Add a dedicated MkDocs `Demos` navigation section.
- Keep the change structural and documentation-focused without changing demo
  behavior, status indexes, evidence contracts, workflows or baselines.

## Change ID

```text
GCR-2026-012
```

## Source Document Intake

| Question | Answer |
|---|---|
| Full source-document intake required? | no |
| New or updated source document? | no |
| Source document path | not applicable |
| Reviewed non-source path | `docs/demos/` |
| Register updated? | no |
| Supersedes existing source? | no |
| Possible duplicate or replacement candidate? | no |
| Similarity assessment | not_relevant |
| Source status | not applicable |

## Why This Change Is Needed

Demo runbooks, historical demo guidance and ha-CPsWMS result explanations were
split between the `docs/` root and `docs/operations/`.

Moving them into `docs/demos/` makes the demo surface easier to find while
keeping operational runbooks, governance documents and evidence handling
separate.

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

- `docs/demos/demo-end-to-end-governance.md`
- `docs/demos/demo-ha-cpswms-runtime-governance.md`
- `docs/demos/ha-cpswms-architecture-governance-results.md`
- `docs/demos/demo-guide-2026-07-02-ha-cpswms.md`
- `mkdocs.yml`
- demo-readiness role and skill references
- active documentation, AI index, README and test scenario references

## Governance Behavior

Choose one:

- [x] Documentation-only
- [ ] Report-only governance behavior
- [ ] Blocking governance behavior
- [ ] Release packaging only

Notes:

- The change does not alter demo workflows, status indexes, evidence schemas,
  evidence contracts, OPA policies or baseline release content.

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
- [x] Source lineage regenerated or confirmed unchanged
- [x] Viewer regenerated if status or presentation changed
- [ ] Downstream example checked if consumer behavior changed

## Reviewer Notes

- Review whether the moved paths are correctly reflected in MkDocs navigation,
  AGENTS, AI index, demo-readiness role metadata, demo-readiness skill guidance,
  README references and test scenarios.
- `python3 -m mkdocs build --strict` was attempted but could not run in the
  local environment because the `mkdocs` Python module is not installed.
