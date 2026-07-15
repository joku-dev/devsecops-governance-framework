# Governance Change Request: Platform Adapter Documentation Migration

## Summary

- Move platform adapter documentation into `docs/operations/adapters/`.
- Group CI/CD, GitHub, Bitbucket, Bamboo and Mistral adapter guidance under one
  MkDocs navigation node.
- Keep the change structural and documentation-focused without changing
  pipeline templates, adapter behavior, evidence contracts or release baselines.

## Change ID

```text
GCR-2026-011
```

## Source Document Intake

| Question | Answer |
|---|---|
| Full source-document intake required? | no |
| New or updated source document? | no |
| Source document path | not applicable |
| Reviewed non-source path | `docs/operations/adapters/` |
| Register updated? | no |
| Supersedes existing source? | no |
| Possible duplicate or replacement candidate? | no |
| Similarity assessment | not_relevant |
| Source status | not applicable |

## Why This Change Is Needed

The operations area contained CI/CD adapter strategy, GitHub reference path,
Bitbucket/Bamboo adapter guidance and company-specific Bamboo/Mistral target
path documentation at the root level.

Moving these documents into `docs/operations/adapters/` makes the platform
adapter capability easier to understand as one coherent integration layer while
keeping governance logic, evidence handling and source intake separate.

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

- `docs/operations/adapters/bitbucket-bamboo-governance-adapter.md`
- `docs/operations/adapters/cicd-platform-adapter-strategy.md`
- `docs/operations/adapters/company-bitbucket-bamboo-mistral-target-path.md`
- `docs/operations/adapters/github-reference-path.md`
- `docs/operations/adapters/github-reference-validation-runbook.md`
- `mkdocs.yml`
- `docs/official-entrypoints.md`
- `docs/ai-index.md`
- active documentation and template references

## Governance Behavior

Choose one:

- [x] Documentation-only
- [ ] Report-only governance behavior
- [ ] Blocking governance behavior
- [ ] Release packaging only

Notes:

- The change does not alter pipeline template behavior, Bamboo specifications,
  GitHub workflows, schemas, evidence contracts, OPA policies or baseline
  release content.

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
  official entrypoints, AI index, README references, active templates and
  cross-document links.
- Historical governance change request references were not rewritten because
  they record the path context at the time of the original decision.
- `python3 -m mkdocs build --strict` was attempted but could not run in the
  local environment because the `mkdocs` Python module is not installed.
