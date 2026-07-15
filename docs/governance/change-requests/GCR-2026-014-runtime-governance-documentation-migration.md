# Governance Change Request: Runtime Governance Documentation Migration

## Summary

- Move runtime governance explanatory documents into
  `docs/governance/architecture/`.
- Add runtime governance addendum and transformation documents to the Governance
  Architecture navigation group.
- Keep the change structural and documentation-focused without changing
  architecture markers, guardrails, review gates, schemas, policies or release
  baselines.

## Change ID

```text
GCR-2026-014
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

Runtime governance documents describe how architecture governance concepts are
made executable through structured data, evidence contracts and policy checks.

Keeping them at the `docs/` root makes them look separate from the Enterprise
Architecture and DevSecOps-as-Code integration story. Moving them into
`docs/governance/architecture/` makes runtime governance part of the same
architecture capability area as ADO integration, software industrialisation and
repository architecture comparison.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | None |
| DevSecOps controls | None |
| Platform model | None |
| Architecture governance | Documentation paths only; no marker, guardrail or gate change |
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

- `docs/governance/architecture/runtime-governance-addendum.md`
- `docs/governance/architecture/runtime-governance-transformation.md`
- `mkdocs.yml`
- `docs/official-entrypoints.md`
- `docs/ai-index.md`
- `README.md`

## Governance Behavior

Choose one:

- [x] Documentation-only
- [ ] Report-only governance behavior
- [ ] Blocking governance behavior
- [ ] Release packaging only

Notes:

- The change does not alter architecture YAML, quality markers, guardrails,
  review gates, schemas, OPA policies, workflows or baseline release content.

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
  official entrypoints, AI index and README references.
- `python3 -m mkdocs build --strict` was attempted but could not run in the
  local environment because the `mkdocs` Python module is not installed.
