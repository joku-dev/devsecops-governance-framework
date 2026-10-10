# GCR-2026-148: Golden Path PRA capability workpackage

## Summary

Create a planning baseline for assessing the 18 PRA proposals deferred by
GCR-2026-147 against the Golden Path under development. The maintainer confirmed
on 10 October 2026 that the Golden Path is intended to support all applicable
DSCB requirements.

The workpackage separates the PRA capabilities the Golden Path should provide
from program responsibilities to select, configure, use, and evidence them.
It records proposed design/implementation evidence without asserting current
conformance or activating any deferred requirement.

## Artifact intake classification

| Field | Value |
|---|---|
| Artifact name | Golden Path PRA Capability Workpackage |
| Artifact type | Planning documentation |
| Target path | `docs/operations/planning/golden-path-pra-capability-workpackage.md`; this change request; MkDocs planning navigation |
| Owner | Platform Owner / Golden Path Engineering; DevSecOps Baseline review |
| Source Document Intake required? | No; uses the approved PRA source and GCR-2026-147. No candidate source is promoted or used. |
| Evidence contract impact | None; proposed evidence remains a planning acceptance basis. |
| Runtime governance impact | None; no policy, enforcement, or consumer behavior changes. |
| Release impact | None; no baseline or release package changes. |
| Validation required | Documentation link/navigation review and the repository's documentation validation before merge. |

## Scope

- Map the 12 partial and six not-confirmed PRA proposals to Golden Path design
  capabilities and candidate closure evidence.
- Keep every proposal open until real implementation and evidence are reviewed.
- Resolve owners, required levels, variants, tests, and evidence responsibilities
  as part of implementation planning.

## Out of scope

- Promoting `TOOLCHAIN-ARCH-CAND-001` or deriving requirements from it while it
  remains a candidate.
- Changing PRA source history, the accepted first-wave decision, current
  requirement authority, platform mappings, controls, schemas, OPA policies,
  evidence contracts, workflows, or enforcement mode.
- Claiming that Golden Path or any program is already compliant.

## Affected artifacts

- `docs/operations/planning/golden-path-pra-capability-workpackage.md`
- `mkdocs.yml`
- No model, status, generated report, policy, schema, baseline, or release
  artifact is changed by this planning work.

## Governance intent

- [x] Documentation/planning only
- [ ] Report-only runtime behavior
- [ ] Blocking behavior
- [ ] Baseline or release change

The workpackage is not an implementation authorization. A later change request
must classify and review model or runtime changes individually. Requirement or
platform mappings remain subject to a new versioned decision based on evidence.

## Validation

- [ ] Review the 18-row mapping against the approved PRA source and GCR-2026-147.
- [ ] Build documentation with strict MkDocs validation.
- [ ] Run repository documentation/governance validation before merge.
