# Governance Change Request: Operations Guides Documentation Migration

## Summary

- Move practical operations guide documents from the `docs/operations/` root
  into `docs/operations/guides/`.
- Add an operations guides index page and group the guides in MkDocs
  navigation.
- Update active documentation references to the new guide paths.
- Keep the change documentation-only without changing governance behavior,
  source documents, schemas, policies or baselines.

## Change ID

```text
GCR-2026-021
```

## Source Document Intake

| Question | Answer |
|---|---|
| Full source-document intake required? | no |
| New or updated source document? | no |
| Source document path | not applicable |
| Reviewed non-source path | `docs/operations/guides/` |
| Register updated? | no |
| Supersedes existing source? | no |
| Possible duplicate or replacement candidate? | no |
| Similarity assessment | not_relevant |
| Source status | not applicable |

## Why This Change Is Needed

The `docs/operations/` root still contained practical guide documents after the
documentation migration wave.

Moving these guides into `docs/operations/guides/` separates recurring how-to
guidance from governance process documents, evidence handling, platform
adapters, agent operations and status reporting.

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

- `docs/operations/guides/index.md`
- `docs/operations/guides/how-to-use-this-repo.md`
- `docs/operations/guides/beginner-step-by-step-operations-guide.md`
- `docs/operations/guides/how-to-update-baseline-input-documents.md`
- `docs/operations/guides/mkdocs-and-github-pages-step-by-step.md`
- `mkdocs.yml`
- active cross-document references

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
- Governance process documents remain in the operations root until they are
  reviewed through a separate process-document migration.

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

- Review whether the moved guide paths are correctly reflected in MkDocs
  navigation and active cross-document links.
- Historical governance change request references were not rewritten because
  they record the path context at the time of the original decision.
