# Governance Change Request

## Summary

- Add a report-only Blocking Mode Alignment registry and projection.
- Record the preexisting `ha-CPsWMS` blocking mode as an acknowledged risk,
  without approving or changing it.
- Fail repository validation for new unsafe Blocking registrations, incomplete
  legacy claims, expired reviews, and orphaned records.

## Change ID

```text
GCR-2026-043
```

## Classification

This is an internal governance validation and evidence change. It introduces no
new source document, control, architecture marker, OPA behavior, consumer
workflow, branch rule, or released baseline behavior.

## Governance Intent

Blocking activation under the new model requires both technical readiness and
accountable approval. A mode that demonstrably predates the model may remain
visible under a time-bounded risk review, but that record is not approval and
does not make the activation valid retroactively.

## Current Risk Record

| Field | Value |
|---|---|
| Repository | `joku-dev/ha-CPsWMS` |
| Mode | `block-on-error` |
| Historical evidence | commit `38abeba851a964a428a2e4a4ea2cfac414a33862`, 15 July 2026 |
| Disposition | preserve without new approval |
| Review due | 18 August 2026 |
| Enforcement change authorized | no |

Open gaps are minimum Trust, replay verification, current Typed Evidence,
representative intake observation, and accountable approval.

## Impact

| Area | Impact |
|---|---|
| OPA and runtime policy | unchanged |
| Current consumer modes | unchanged |
| New blocking registrations | repository validation rejects unsafe state |
| Existing result and evidence history | unchanged |
| Released baselines | unchanged |
| Viewer | unchanged |

## Roles

- Governance Analyst: intent, risks, and unresolved decision recorded.
- Policy-as-Code: enforcement behavior classified as unchanged.
- Release Manager: no release required; future consumer activation needs a
  separate migration and release decision when applicable.
- Repo Steward: schemas, projection, negative tests, documentation, and full
  validation reviewed.

## Validation Plan

- [x] current projection is controlled and schema-valid
- [x] new blocking without readiness and approval fails alignment
- [x] post-cutoff legacy claim cannot bypass validation
- [x] incomplete and expired risk records fail alignment
- [x] ready and approved blocking is distinguishable from legacy risk
- [x] full repository validation
- [x] strict documentation build

## Open Decision

The named accountable reviewers must decide the future `ha-CPsWMS` mode by the
review due date. This GCR does not make that decision.
