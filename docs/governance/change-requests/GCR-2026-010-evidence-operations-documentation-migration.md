# Governance Change Request: Evidence Operations Documentation Migration

## Summary

- Move evidence and result-handling operations documentation into
  `docs/operations/evidence/`.
- Update navigation, AI index, role paths, onboarding references, agent routing,
  tests, scripts and active templates to the new paths.
- Keep the change structural and documentation-focused without changing
  evidence schemas, evidence contracts, result intake behavior or release
  baselines.

## Change ID

```text
GCR-2026-010
```

## Source Document Intake

| Question | Answer |
|---|---|
| Full source-document intake required? | no |
| New or updated source document? | no |
| Source document path | not applicable |
| Reviewed non-source path | `docs/operations/evidence/` |
| Register updated? | no |
| Supersedes existing source? | no |
| Possible duplicate or replacement candidate? | no |
| Similarity assessment | not_relevant |
| Source status | not applicable |

## Why This Change Is Needed

The operations documentation includes several related evidence, result intake,
viewer and architecture evidence documents. Keeping them at the root of
`docs/operations/` makes the operations area harder to scan and weakens the
reader journey from evidence contract to downstream result handling.

Moving these documents into `docs/operations/evidence/` is the next documented
migration package from the documentation structure model. It makes evidence
handling visible as a coherent operational capability while preserving source
lineage, release packages and runtime behavior.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | None |
| DevSecOps controls | None |
| Platform model | None |
| Architecture governance | None |
| OPA policies | None |
| Schemas and evidence contracts | None |
| Viewer, status indexes or intake | Documentation links only; no intake behavior change |
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

- `docs/operations/evidence/application-repo-architecture-evidence-flow.md`
- `docs/operations/evidence/application-repo-evidence-flow.md`
- `docs/operations/evidence/architecture-evidence-ea-decision-brief.md`
- `docs/operations/evidence/architecture-evidence-ea-package.md`
- `docs/operations/evidence/architecture-evidence-taxonomy-mapping.md`
- `docs/operations/evidence/architecture-evidence-type-taxonomy.md`
- `docs/operations/evidence/detailed-architecture-evidence-adoption-guide.md`
- `docs/operations/evidence/governance-evidence-contract.md`
- `docs/operations/evidence/governance-evidence-schema-versioning.md`
- `docs/operations/evidence/governance-result-intake-and-viewer-usage.md`
- `docs/operations/evidence/governance-results-storage-model.md`
- `docs/operations/evidence/how-to-read-control-evaluation-status.md`
- `mkdocs.yml`
- `docs/official-entrypoints.md`
- `docs/ai-index.md`
- role paths, onboarding references, active templates, agent routing and tests

## Governance Behavior

Choose one:

- [x] Documentation-only
- [ ] Report-only governance behavior
- [ ] Blocking governance behavior
- [ ] Release packaging only

Notes:

- The change does not alter evidence schemas, result intake behavior, viewer
  semantics, OPA policy, architecture governance markers or baseline release
  content.

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
  official entrypoints, AI index, role paths, onboarding documents, active
  templates, agent routing and tests.
- Historical release package references were not rewritten because released
  baseline packages should remain stable.
- `python3 -m mkdocs build --strict` was attempted but could not run in the
  local environment because the `mkdocs` Python module is not installed.
