# Governance Change Request

## Summary

- Add a deterministic, report-only Replay Triage projection.
- Preserve recorded replay results while distinguishing the current
  interpretation and the recommended operator action.
- Surface the official-latest triage in the viewer and document its operating
  boundary.

## Change ID

```text
GCR-2026-044
```

## Classification

This is an internal evidence interpretation, validation, viewer, and
documentation change. It introduces no source document, control, architecture
marker, OPA behavior, consumer workflow requirement, or released baseline.

## Governance Intent

Historical Evidence is immutable, but replay logic can become more precise.
Operators need a transparent way to distinguish an original recorded finding
from its interpretation under current rules, without retrospective rewriting
or accidental enforcement.

## Current Finding

| Field | Value |
|---|---|
| Repository | `joku-dev/governance-framework-demo-consumer` |
| Domain and run | DevSecOps, `29603835297` |
| Classification | `cross_commit_reuse` |
| Cause | normalized control-report digest reused across commits without an accepted `artifact_digest` |
| Action | produce fresh Evidence with artifact-digest binding |
| Enforcement | report-only |

Of three stored failures, two remain immutable but are explained as
`legacy_assessment_superseded` under the current hardened rules. One remains a
current official-latest finding.

## Impact

| Area | Impact |
|---|---|
| Historical snapshots and Trust | unchanged |
| Latest-result selection | unchanged |
| OPA and runtime policy | unchanged |
| Consumer contracts and released baselines | unchanged |
| Repository validation | regenerates and validates the derived projection |
| Viewer | adds official-latest Replay Triage |

## Roles

- Governance Analyst: intent, classifications, action routing, and non-goals.
- Evidence and Intake: chronology, current replay evaluation, schema, and
  immutable-history boundary.
- Demo Readiness: viewer and demo interpretation.
- Repo Steward: tests, validation, documentation, and commit scope.

## Validation Plan

- [x] deterministic projection generated from stored Trust-bearing snapshots
- [x] projection schema validated
- [x] recorded and recalculated results remain distinguishable
- [x] historical mutation, Trust change, latest selection, and enforcement are prohibited
- [x] cross-context and legacy-supersession tests
- [x] viewer projection and documentation
- [x] full repository validation
- [x] strict documentation build

## Release Decision

No release is required. Any future use of replay classification as a blocking
gate requires a separate approval, migration, exception, and release decision.
