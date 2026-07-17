# Governance Change Request

## Summary

- Generate a schema-valid, report-only Intake Health projection from append-only
  operation events.
- Include explicit-window success and failure rates, duration percentiles,
  dimensional counts, Collection Attempt lifecycle, conflict count, and latest
  result age.
- Regenerate the projection in all three central intake workflows.

## Change ID

```text
GCR-2026-038
```

## Source Document Intake

| Question | Answer |
|---|---|
| Full source-document intake required? | no |
| New or updated source document? | no |
| Reviewed non-source paths | telemetry events, collection attempts, conflict ledger, result indexes, central workflows, schemas, scripts, tests, operations documentation |
| Register updated? | no |
| Supersedes existing source? | no |
| Possible duplicate or replacement candidate? | no; this is a derived operational read model |
| Similarity assessment | `not_relevant` |

## Artifact Intake Classification

| Artifact | Type | Target | Impact |
|---|---|---|---|
| Intake Health schema | internal projection schema | `schemas/intake-health.schema.json` | additive |
| Intake Health generator | deterministic projection | `scripts/generate_intake_health.py` | report-only |
| Current health state | derived status projection | `status/intake-health.json` | recomputable |
| Shared attempt lifecycle | runtime library | `scripts/lib/collection_attempts.py` | behavior-preserving reuse |
| Workflow integration | central workflows | `.github/workflows/intake-*.yml` | regenerates projection after intake |
| Operations documentation | evidence operations guide | `docs/operations/evidence/` | explanatory |

Owner: Governance Platform Maintainers. Evidence event contracts are unchanged;
the new projection contract is additive. Runtime impact is report-only. Release
impact is none.

## Why This Change Is Needed

Append-only events provide a complete operational denominator, but raw records
do not directly answer how often intake succeeds, how long it takes, or which
consumer and collector combinations are active. Operators need a deterministic
read model before they can establish evidence-based objectives or alerts.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | none |
| DevSecOps controls | none |
| Platform model | none |
| Architecture governance | architecture document records the new read model |
| OPA policies | none |
| Schemas and evidence contracts | additive projection schema; event schema unchanged |
| Viewer, status indexes or intake | new status projection; viewer unchanged in this PR |
| Release package or baseline | none |
| Downstream repositories | none; producer and dispatch contracts are unchanged |

## Governance Behavior

- [x] Report-only operational behavior

Invariants:

- health metrics never change governance outcomes or Evidence Trust
- `latest_result` selection remains unchanged
- the 30-day event window is explicit in the projection
- historical events, attempts, and conflicts remain immutable
- partial and failed events jointly form the failure-rate numerator
- percentiles use the documented nearest-rank method
- `no_data` is not interpreted as healthy
- no SLO, threshold, alert, retry budget, or blocking effect is introduced
- released baseline packages remain unchanged

## Release Decision

- [x] No release required

The projection is internal central operational state and does not change a
released consumer workflow or baseline package.

## Validation Plan

- [x] targeted projection and lifecycle tests
- [x] schema validation of the committed projection
- [x] central workflow integration tests
- [x] `python3 scripts/validate_runtime_governance.py`
- [x] `python3 scripts/validate_governance_repo.py`
- [x] `python3 -m unittest discover -s tests`
- [x] `mkdocs build --strict`

## Reviewer Notes

Review focus: explicit window semantics, rate and nearest-rank calculations,
shared lifecycle behavior, dimensional determinism, report-only separation,
workflow convergence, latest-state immutability, and absence of release impact.
