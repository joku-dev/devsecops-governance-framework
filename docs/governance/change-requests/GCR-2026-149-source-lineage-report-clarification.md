# GCR-2026-149 — Source Lineage Report Clarification

## Summary

- Count direct source-to-artifact lineage separately from register-wide intake and impact reports.
- Build the source inventory from the source document register and check the register against files on disk.
- Show missing or unregistered source files in the report without making them validator failures.
- Keep missing derived artifact paths as validator failures; document the historical release reference to the intentionally retired example and its real replacement without editing the immutable package.
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
surface a historical source path embedded in the released architecture
package. That path belonged to an example placeholder intentionally removed by
PR #244 and replaced with the real `ARCH-SDD-SRC-001.requirements.md` source;
the current register and working models use that replacement. The immutable
release snapshot still contains the former path, so the report makes that
historical metadata visible. It does not indicate a missing current source or
derived artifact. Missing or unregistered source files remain report findings
and do not fail the repository validator automatically. Missing derived
artifact paths remain a validation error.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | none |
| DevSecOps controls | none |
| Platform model | none |
| Architecture governance | no runtime change; the historical reference to a retired example and its real replacement are documented |
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
- The released architecture package retains the removed example path
  `ARCH-SDD-SRC-001.public.md` in five historical files. The real replacement
  is `ARCH-SDD-SRC-001.requirements.md`, used by the register and current
  working models. The immutable release is left untouched; a future baseline
  should record the real source path.
