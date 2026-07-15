# Governance Change Request: Examples Documentation Migration

## Summary

- Move schema-backed JSON examples from the `docs/` root into
  `docs/examples/`.
- Add an examples index page to make the examples discoverable in MkDocs.
- Update validation, CODEOWNERS and active documentation references to the new
  example paths.
- Keep the change structural and compatibility-aware without changing schemas,
  policies, source documents or runtime governance behavior.

## Change ID

```text
GCR-2026-019
```

## Source Document Intake

| Question | Answer |
|---|---|
| Full source-document intake required? | no |
| New or updated source document? | no |
| Source document path | not applicable |
| Reviewed non-source path | `docs/examples/` |
| Register updated? | no |
| Supersedes existing source? | no |
| Possible duplicate or replacement candidate? | no |
| Similarity assessment | not_relevant |
| Source status | not applicable |

## Why This Change Is Needed

The `docs/` root still contained schema-backed JSON examples after the first
documentation migration wave.

Moving the examples into `docs/examples/` creates a clearer separation between
official entrypoints, governance documentation, operational runbooks and
machine-readable example payloads.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | None |
| DevSecOps controls | None |
| Platform model | None |
| Architecture governance | None |
| OPA policies | None |
| Schemas and evidence contracts | None |
| Validation scripts | Path references updated only |
| Viewer, status indexes or intake | None |
| Release package or baseline | None |
| Downstream repositories | Low; active documentation now points to `docs/examples/` |

## Replacement Review

| Existing source ID | Similarity | Notes |
|---|---|---|
| not applicable | unknown | This is a documentation/example move, not a source-document replacement. |

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

- `docs/examples/index.md`
- `docs/examples/governance-run-input.example.json`
- `docs/examples/governance-compliance-result.example.json`
- `docs/examples/governance-compliance-result.extended.example.json`
- `scripts/validate_governance_repo.py`
- `.github/CODEOWNERS`
- `mkdocs.yml`
- active cross-document references

## Governance Behavior

Choose one:

- [x] Documentation/example-path only
- [ ] Report-only governance behavior
- [ ] Blocking governance behavior
- [ ] Release packaging only

Notes:

- The change does not alter source-document intake, policies, controls,
  architecture markers, schemas, OPA policies, workflows, status indexes or
  release content.
- Validation continues to check the same example contracts from their new
  location.

## Release Decision

Choose one:

- [x] No release required
- [ ] Release candidate required
- [ ] Patch baseline release required
- [ ] Minor baseline release required
- [ ] Major baseline release required

Release notes:

- No baseline release is required because this is a documentation structure and
  example-path migration only.

## Validation Plan

Confirm what must pass before merge.

- [x] `python3 scripts/validate_runtime_governance.py`
- [x] `python3 scripts/validate_governance_repo.py`
- [x] `python3 -m unittest discover -s tests`
- [x] `.venv-docs/bin/mkdocs build --strict`
- [x] Source lineage regenerated or confirmed unchanged
- [x] Viewer regeneration not required; no status or presentation artifact changed
- [x] Downstream example checked; no consumer behavior changed

## Reviewer Notes

- Review whether the moved example paths are correctly reflected in validation,
  MkDocs navigation, official entrypoints, consumer onboarding guidance and
  operational evidence documentation.
- Historical governance change request references were not rewritten because
  they record the path context at the time of the original decision.
