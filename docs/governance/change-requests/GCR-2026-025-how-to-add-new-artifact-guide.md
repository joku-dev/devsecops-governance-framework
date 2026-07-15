# Governance Change Request: How To Add A New Artifact Guide

## Summary

- Add a practical operator guide for adding new artifacts safely.
- Link the guide from the operations guides index, MkDocs navigation,
  official entrypoints and AI index.
- Keep the change documentation-only without changing runtime governance,
  source documents, schemas, policies or baselines.

## Change ID

```text
GCR-2026-025
```

## Artifact Intake Classification

| Field | Value |
|---|---|
| Artifact name | How To Add A New Artifact guide |
| Artifact type | documentation |
| Target path | `docs/operations/guides/how-to-add-a-new-artifact.md` |
| Owner | governance maintainers |
| Source Document Intake required? | no |
| Evidence contract impact | none |
| Runtime governance impact | none |
| Release impact | none |
| Validation required | Runtime validation, repo validation, unit tests, MkDocs strict build |

## Source Document Intake

| Question | Answer |
|---|---|
| Full source-document intake required? | no |
| New or updated source document? | no |
| Source document path | not applicable |
| Reviewed non-source path | `docs/operations/guides/how-to-add-a-new-artifact.md` |
| Register updated? | no |
| Supersedes existing source? | no |
| Possible duplicate or replacement candidate? | no |
| Similarity assessment | not_relevant |
| Source status | not applicable |

## Why This Change Is Needed

The repository now has a New Artifact Intake Process, classification examples
and a checklist template.

Maintainers also need a practical step-by-step guide that explains how to use
those assets when adding a real artifact to the repository.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | None |
| DevSecOps controls | None |
| Platform model | None |
| Architecture governance | None |
| OPA policies | None |
| Schemas and evidence contracts | None |
| Viewer, status indexes or intake | Documentation guidance only |
| Release package or baseline | None |
| Downstream repositories | None |

## Replacement Review

| Existing source ID | Similarity | Notes |
|---|---|---|
| not applicable | unknown | This is a guide addition, not a source-document replacement. |

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

- `docs/operations/guides/how-to-add-a-new-artifact.md`
- `docs/operations/guides/index.md`
- `docs/official-entrypoints.md`
- `docs/ai-index.md`
- `mkdocs.yml`

## Governance Behavior

Choose one:

- [x] Documentation-only
- [ ] Report-only governance behavior
- [ ] Blocking governance behavior
- [ ] Release packaging only

Notes:

- The guide explains existing processes and does not change artifact intake,
  source-document intake, evidence contracts, generated outputs, release
  packages or runtime behavior.

## Release Decision

Choose one:

- [x] No release required
- [ ] Release candidate required
- [ ] Patch baseline release required
- [ ] Minor baseline release required
- [ ] Major baseline release required

Release notes:

- No baseline release is required because this is a documentation-only guide.

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

- Review whether the guide is actionable enough for maintainers adding a real
  artifact.
- Review whether it routes source, evidence, generated output, release and
  documentation artifacts to the right existing process.
