# Governance Change Request: New Artifact Intake Preparation

## Summary

- Add a process for classifying new artifacts before they enter the governed
  repository structure.
- Update navigation, AI/official entrypoints, AGENTS, PR template and GCR
  template so future artifact intake is visible and repeatable.
- Keep the change documentation- and process-only without changing runtime
  governance behavior, schemas, policies, source documents or baselines.

## Change ID

```text
GCR-2026-023
```

## Artifact Intake Classification

| Field | Value |
|---|---|
| Artifact name | New Artifact Intake Process |
| Artifact type | documentation |
| Target path | `docs/operations/processes/new-artifact-intake-process.md` |
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
| Reviewed non-source path | `docs/operations/processes/new-artifact-intake-process.md` |
| Register updated? | no |
| Supersedes existing source? | no |
| Possible duplicate or replacement candidate? | no |
| Similarity assessment | not_relevant |
| Source status | not applicable |

## Why This Change Is Needed

The repository now has a clearer documentation and process structure, but new
artifacts still need an explicit front-door classification step before they are
added, moved or consumed.

Without that step, maintainers could accidentally add source material as
ordinary documentation, hand-edit generated outputs, place examples in the
wrong folder, or derive runtime behavior from unreviewed candidate material.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | None |
| DevSecOps controls | None |
| Platform model | None |
| Architecture governance | None |
| OPA policies | None |
| Schemas and evidence contracts | None |
| Viewer, status indexes or intake | Documentation of existing intake boundaries only |
| Release package or baseline | None |
| Downstream repositories | None |

## Replacement Review

| Existing source ID | Similarity | Notes |
|---|---|---|
| not applicable | unknown | This is a process/documentation preparation, not a source-document replacement. |

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

- `docs/operations/processes/new-artifact-intake-process.md`
- `docs/operations/processes/index.md`
- `docs/governance/governance-change-lifecycle.md`
- `docs/governance/change-requests/TEMPLATE.md`
- `.github/pull_request_template.md`
- `docs/official-entrypoints.md`
- `docs/ai-index.md`
- `AGENTS.md`
- `mkdocs.yml`

## Governance Behavior

Choose one:

- [x] Documentation-only
- [ ] Report-only governance behavior
- [ ] Blocking governance behavior
- [ ] Release packaging only

Notes:

- The process prepares artifact classification only.
- It does not alter source-document intake, policies, controls, architecture
  markers, schemas, OPA policies, workflows, status indexes or releases.

## Release Decision

Choose one:

- [x] No release required
- [ ] Release candidate required
- [ ] Patch baseline release required
- [ ] Minor baseline release required
- [ ] Major baseline release required

Release notes:

- No baseline release is required because this is a documentation and process
  preparation only.

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

- Review whether the classification matrix covers source documents, evidence,
  examples, generated outputs, releases, documentation and executable
  governance artifacts.
- Review whether the templates make new artifact intake visible without
  introducing blocking behavior.
