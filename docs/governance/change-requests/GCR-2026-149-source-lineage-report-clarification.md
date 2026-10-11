# GCR-2026-149 — Source Lineage Report Clarification

## Summary

- Count direct source-to-artifact lineage separately from register-wide intake and impact reports.
- Build the source inventory from the source document register and check the register against files on disk.
- Report unresolved source paths referenced by model or release artifacts without editing released packages.
- Document the current source dependency groups and the no-deletion disposition.

## Change ID

```text
GCR-2026-149
```

## Artifact Intake Classification

| Field | Value |
|---|---|
| Artifact name | Source-lineage report clarification |
| Artifact type | generator/script, tests, documentation, generated report |
| Target path | `scripts/`, `tests/`, `docs/operations/guides/`, `generated/reports/` |
| Owner | repository maintainers |
| Source Document Intake required? | no |
| Evidence contract impact | none |
| Runtime governance impact | none; report-only visibility |
| Release impact | none |
| Validation required | source-lineage tests, governance repository validation, runtime validation |

| Question | Answer |
|---|---|
| Full source-document intake required? | no |
| New or updated source document? | no |
| Reviewed non-source path | lineage generator, validator, tests, dependency guide, generated lineage and impact reports |
| Register updated? | no |
| Supersedes existing source? | no |
| Possible duplicate or replacement candidate? | no |
| Similarity assessment | not relevant |
| Source status | unchanged |

## Why This Change Is Needed

The previous lineage report counted the same ten shared intake and impact
reports as direct derivations from every registered source. It also did not
surface a missing source path embedded in the released architecture package.
This obscured which source files currently have direct model or release links.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | none |
| DevSecOps controls | none |
| Platform model | none |
| Architecture governance | no runtime change; one historical missing source reference is made visible |
| OPA policies | none |
| Schemas and evidence contracts | none |
| Viewer, status indexes or intake | lineage and change-impact reports clarify direct versus shared report relationships |
| Release package or baseline | none; released package files remain unchanged |
| Downstream repositories | none |

## Derived Artifacts

- `generated/reports/source-lineage-report.{json,md}`
- `generated/reports/governance-change-impact.{json,md}`
- `docs/operations/guides/source-document-dependency-map.md`

## Governance Behavior

- [x] Report-only governance behavior

The change does not promote or retire sources, derive new controls or markers,
or change enforcement behavior.

## Release Decision

- [x] No release required

## Validation Plan

- [x] `python3 -m unittest tests.test_source_lineage_report`
- [x] `python3 scripts/validate_runtime_governance.py`
- [x] `python3 scripts/validate_governance_repo.py`
- [x] `mkdocs build --strict`
- [x] Full unit test suite; 783 tests covered, two skipped. The sandboxed
  loopback bind test passed in a separate non-sandboxed run.
- [x] Source lineage and governance change impact reports regenerated
- [x] `git diff --check`

## Reviewer Notes

- Confirm that the distinction between direct lineage and register-wide reports
  is useful for maintainers.
- The released architecture package still refers to the removed
  `ARCH-SDD-SRC-001.public.md` path in five historical files. Resolve its
  provenance through a separately reviewed follow-up; this change deliberately
  leaves the released package untouched.
