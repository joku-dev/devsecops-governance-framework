# Governance Change Request: Publishing Documentation Migration

## Summary

- Move the Confluence article from the `docs/` root into `docs/publishing/`.
- Add a publishing index page and MkDocs navigation entry.
- Update the documentation structure audit and target structure model.
- Keep the change documentation-only without changing governance behavior,
  source documents, schemas, policies or baselines.

## Change ID

```text
GCR-2026-020
```

## Source Document Intake

| Question | Answer |
|---|---|
| Full source-document intake required? | no |
| New or updated source document? | no |
| Source document path | not applicable |
| Reviewed non-source path | `docs/publishing/` |
| Register updated? | no |
| Supersedes existing source? | no |
| Possible duplicate or replacement candidate? | no |
| Similarity assessment | not_relevant |
| Source status | not applicable |

## Why This Change Is Needed

The `docs/` root still contained a Confluence-oriented article after the
documentation migration wave.

Moving the article into `docs/publishing/` separates external communication
artifacts from official entrypoints, source documents, operational runbooks,
examples and architecture documentation.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | None |
| DevSecOps controls | None |
| Platform model | None |
| Architecture governance | None |
| OPA policies | None |
| Schemas and evidence contracts | None |
| Validation scripts | None |
| Viewer, status indexes or intake | None |
| Release package or baseline | None |
| Downstream repositories | None |

## Replacement Review

| Existing source ID | Similarity | Notes |
|---|---|---|
| not applicable | unknown | This is a publishing/documentation move, not a source-document replacement. |

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

- `docs/publishing/index.md`
- `docs/publishing/confluence-governance-repo-artikel.md`
- `mkdocs.yml`
- `.github/CODEOWNERS`
- `docs/operations/planning/document-structure-audit.md`
- `docs/operations/planning/document-structure-model.md`

## Governance Behavior

Choose one:

- [x] Documentation-only
- [ ] Report-only governance behavior
- [ ] Blocking governance behavior
- [ ] Release packaging only

Notes:

- The change does not alter source-document intake, policies, controls,
  architecture markers, schemas, OPA policies, workflows, status indexes or
  release content.
- The moved article remains a communication artifact. It does not become an
  authoritative governance source through this migration.

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
- [x] Viewer regeneration not required; no status or presentation artifact changed
- [x] Downstream example check not required; no consumer behavior changed

## Reviewer Notes

- Review whether the article is correctly classified as a publishing artifact
  and not as an authoritative governance source.
- Historical governance change request references were not rewritten because
  they record the path context at the time of the original decision.
