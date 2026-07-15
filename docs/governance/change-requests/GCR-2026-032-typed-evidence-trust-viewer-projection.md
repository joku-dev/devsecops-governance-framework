# Governance Change Request: Typed Evidence Trust Viewer Projection

## Summary

- Add central intake and re-verification for typed vulnerability evidence.
- Preserve typed evidence as a separate report-only history and index.
- Project scanner, integrity, Freshness, Trust, and subject binding into the
  governance status viewer.
- Record the validated demo-consumer mainline run without changing governance
  outcomes or released baselines.

## Change ID

```text
GCR-2026-032
```

## Artifact Intake Classification

| Field | Value |
|---|---|
| Artifact name | Typed Evidence Trust result and index |
| Artifact type | evidence, schema, workflow, generated status, documentation |
| Target paths | `status/typed-evidence-results/`, `schemas/`, `scripts/`, `.github/workflows/`, `generated/viewer/`, `docs/` |
| Owner | governance-maintainers |
| Source Document Intake required? | no |
| Evidence contract impact | additive |
| Runtime governance impact | report-only |
| Release impact | none |
| Validation required | schema, intake tamper detection, latest selection, viewer generation, full repository validation, strict docs build |

The incoming GitHub Actions artifact is operational evidence, not a governance
source document. No source-document registration or replacement review is
required.

## Why This Change Is Needed

The vulnerability collector pilot already creates typed Trust records in a
downstream pipeline. A central demo needs to show that governance independently
verifies those bytes and can present evidence quality without treating it as a
control decision or accepting a producer assertion on Trust.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy, directive, controls and OPA | unchanged |
| Evidence contracts | additive typed snapshot and index schemas |
| Intake | downloads the complete artifact and centrally recomputes subject digests |
| Viewer | adds a separate Typed Evidence Trust section |
| Governance result indexes | unchanged |
| Downstream repositories | optional `application-evidence` producer; no required contract change |
| Released baselines | unchanged |

## Governance Invariants

- Producer-side Trust is not authoritative; central intake re-verifies the
  downloaded scan and evaluated artifact.
- Typed evidence history is separate from DevSecOps and architecture result
  history.
- A `main` branch `push` is preferred as the latest typed result; later manual
  diagnostics remain history and do not replace it.
- Typed Trust, scan findings, and governance outcomes remain independent.
- Freshness and integrity failures remain visible and report-only.
- Historical snapshots are not rewritten or reclassified.
- The current `co_collected` binding is not presented as scanner attestation.

## Derived Artifacts

- `status/typed-evidence-results-index.json`
- `generated/viewer/status-viewer.html`
- `docs/demos/presentation-guide-typed-evidence-trust-de.md`
- source-lineage and governance-impact reports

## Validated Demo State

| Field | Value |
|---|---|
| Repository | `joku-dev/governance-framework-demo-consumer` |
| Mainline run | `29432884108` |
| Commit | `4ec2b2bd53560e010ebb1c078c4d3bd41b0bfcc6` |
| Scanner | Trivy `v0.70.0` |
| Findings | `0`, maximum severity `none` |
| Content integrity | `pass` |
| Freshness | `pass` |
| Effective Trust | `integrity_verified` |
| Enforcement | `report_only` |

## Governance Behavior

- [ ] Documentation-only
- [x] Report-only governance behavior
- [ ] Blocking governance behavior
- [ ] Release packaging only

## Release Decision

- [x] No release required
- [ ] Release candidate required
- [ ] Patch baseline release required
- [ ] Minor baseline release required
- [ ] Major baseline release required

The producer contract remains optional, existing snapshots remain valid, and
no released package, reusable baseline ref, control, or enforcement behavior
changes.

## Validation Plan

- [x] Typed snapshot and index schema validation
- [x] Central-verifier replacement and tamper-detection tests
- [x] Mainline-over-manual latest selection test
- [x] Intake of the real demo-consumer run
- [x] `python3 scripts/validate_runtime_governance.py`
- [x] `python3 scripts/validate_governance_repo.py`
- [x] `python3 -m unittest discover -s tests`
- [x] Source lineage regenerated
- [x] Viewer regenerated
- [x] `mkdocs build --strict`

## Required Review Lenses

- Governance Analyst: separation of evidence quality and governance decision
- Evidence And Intake: authoritative metadata, custody, re-verification, and latest selection
- Demo Readiness: coherent two-repository story and visible validated run
- Release Manager: additive compatibility and no baseline release
- Repo Steward: scope, validation evidence, generated-output hygiene, and commit readiness
