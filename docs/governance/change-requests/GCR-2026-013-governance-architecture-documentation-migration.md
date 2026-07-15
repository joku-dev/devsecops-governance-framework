# Governance Change Request: Governance Architecture Documentation Migration

## Summary

- Move explanatory governance architecture documents into
  `docs/governance/architecture/`.
- Group ADO integration, software industrialisation capability mapping and
  central repository architecture comparison under one MkDocs navigation node.
- Keep the change structural and documentation-focused without changing policy,
  directive, controls, architecture markers, workflows or release baselines.

## Change ID

```text
GCR-2026-013
```

## Source Document Intake

| Question | Answer |
|---|---|
| Full source-document intake required? | no |
| New or updated source document? | no |
| Source document path | not applicable |
| Reviewed non-source path | `docs/governance/architecture/` |
| Register updated? | no |
| Supersedes existing source? | no |
| Possible duplicate or replacement candidate? | no |
| Similarity assessment | not_relevant |
| Source status | not applicable |

## Why This Change Is Needed

The governance documentation contains both core governance documents and
explanatory architecture documents.

Moving ADO/DevSecOps integration, software industrialisation capability mapping
and governance repository architecture comparison into
`docs/governance/architecture/` makes the relationship between Enterprise
Architecture and DevSecOps-as-Code easier to read as one coherent capability
area while keeping policy, directive, source documents and change requests
separate.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | None |
| DevSecOps controls | None |
| Platform model | None |
| Architecture governance | Documentation paths only; no marker or rule change |
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

- `docs/governance/architecture/ado-devsecops-integrated-governance-model.md`
- `docs/governance/architecture/software-industrialisation-problem-capability-map.md`
- `docs/governance/architecture/governance-repository-architecture-comparison.md`
- `mkdocs.yml`
- `docs/official-entrypoints.md`
- `docs/ai-index.md`
- active cross-document references

## Governance Behavior

Choose one:

- [x] Documentation-only
- [ ] Report-only governance behavior
- [ ] Blocking governance behavior
- [ ] Release packaging only

Notes:

- The change does not alter policy, directive, controls, architecture quality
  markers, review gates, schemas, OPA policies, workflows or baseline release
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
  official entrypoints, AI index and cross-document links.
- Historical governance change request references were not rewritten because
  they record the path context at the time of the original decision.
- `python3 -m mkdocs build --strict` was attempted but could not run in the
  local environment because the `mkdocs` Python module is not installed.
