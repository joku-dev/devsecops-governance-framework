# Governance Change Request: Artifact Intake Examples

## Summary

- Add worked examples for applying the New Artifact Intake Process.
- Add a reusable artifact intake checklist template.
- Link the examples from the examples index and MkDocs navigation.
- Keep the change documentation-only without changing runtime governance,
  source documents, schemas, policies or baselines.

## Change ID

```text
GCR-2026-024
```

## Artifact Intake Classification

| Field | Value |
|---|---|
| Artifact name | Artifact intake examples and checklist |
| Artifact type | example |
| Target path | `docs/examples/` |
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
| Reviewed non-source path | `docs/examples/` |
| Register updated? | no |
| Supersedes existing source? | no |
| Possible duplicate or replacement candidate? | no |
| Similarity assessment | not_relevant |
| Source status | not applicable |

## Why This Change Is Needed

The New Artifact Intake Process is easier to apply when maintainers have
concrete examples and a reusable checklist.

The examples show how the repository should classify typical incoming
artifacts before they enter source intake, evidence/result intake, examples,
adapter templates, publishing or schema/evidence contract review.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | None |
| DevSecOps controls | None |
| Platform model | None |
| Architecture governance | None |
| OPA policies | None |
| Schemas and evidence contracts | None |
| Viewer, status indexes or intake | Documentation examples only |
| Release package or baseline | None |
| Downstream repositories | None |

## Replacement Review

| Existing source ID | Similarity | Notes |
|---|---|---|
| not applicable | unknown | This is an example/template addition, not a source-document replacement. |

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

- `docs/examples/artifact-intake-classification.example.md`
- `docs/examples/artifact-intake-checklist.template.md`
- `docs/examples/index.md`
- `mkdocs.yml`

## Governance Behavior

Choose one:

- [x] Documentation-only
- [ ] Report-only governance behavior
- [ ] Blocking governance behavior
- [ ] Release packaging only

Notes:

- The examples do not create any runtime intake result, source document,
  schema, OPA policy, workflow behavior or release package.

## Release Decision

Choose one:

- [x] No release required
- [ ] Release candidate required
- [ ] Patch baseline release required
- [ ] Minor baseline release required
- [ ] Major baseline release required

Release notes:

- No baseline release is required because this is a documentation example
  addition only.

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

- Review whether the examples cover the most likely incoming artifact classes.
- Review whether the checklist can be copied into future GCRs or pull requests
  without changing governance behavior.
