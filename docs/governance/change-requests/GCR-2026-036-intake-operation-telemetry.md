# Governance Change Request

## Summary

- Record every central governance, architecture, and typed-evidence intake as
  an append-only operational event.
- Capture success, failure, duration, consumer, collector, downstream run, and
  central workflow identity.
- Establish the event denominator required for a later report-only Intake
  Health and SLO projection.

## Change ID

```text
GCR-2026-036
```

## Source Document Intake

| Question | Answer |
|---|---|
| Full source-document intake required? | no |
| New or updated source document? | no |
| Reviewed non-source paths | central intake workflows, schemas, scripts, tests, status operations, evidence documentation |
| Register updated? | no |
| Supersedes existing source? | no |
| Possible duplicate or replacement candidate? | no; this is runtime operational telemetry |
| Similarity assessment | `not_relevant` |

## Artifact Intake Classification

| Artifact | Type | Target | Impact |
|---|---|---|---|
| Intake operation event | internal evidence schema | `schemas/`, `docs/examples/` | additive |
| Intake event ledger | operational evidence | `status/intake-events/` | append-only, report-only |
| Intake recorder | runtime implementation | `scripts/` | report-only instrumentation |
| Intake workflow integration | central workflow | `.github/workflows/intake-*.yml` | records outcome for every execution |
| Operations documentation | evidence operations guide | `docs/operations/evidence/` | explanatory |

Owner: Governance Platform Maintainers. Evidence-contract impact is additive
and internal to central operations. Runtime impact is report-only. Release
impact is none.

## Why This Change Is Needed

Successful snapshots and failed collection attempts do not form a complete set
of intake executions. Without a uniform event for success, partial completion,
and failure, the system cannot calculate a defensible intake success rate or
latency distribution.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | none |
| DevSecOps controls | none |
| Platform model | none |
| Architecture governance | none |
| OPA policies | none |
| Schemas and evidence contracts | additive internal event schema |
| Viewer, status indexes or intake | central intake instrumentation; viewer and latest indexes unchanged |
| Release package or baseline | none |
| Downstream repositories | none; producer contracts are unchanged |

## Derived Artifacts

- future workflow executions create append-only events under `status/intake-events/`
- no historical backfill
- no current viewer regeneration required
- source-document lineage is unchanged

## Governance Behavior

- [x] Report-only operational behavior

Invariants:

- telemetry does not change governance outcomes or Evidence Trust
- telemetry does not update `latest_result`
- identical events are idempotent
- conflicting event payloads do not overwrite history
- failed collection remains separately retryable through Collection Attempts
- released baseline packages remain unchanged

## Release Decision

- [x] No release required

The change instruments central repository workflows and does not alter a
released consumer workflow or downstream payload.

## Validation Plan

- [x] schema-valid success and failure records
- [x] append-only and conflict tests
- [x] all three intake workflows instrumented
- [x] `python3 scripts/validate_runtime_governance.py`
- [x] `python3 scripts/validate_governance_repo.py`
- [x] `python3 -m unittest discover -s tests`
- [x] `mkdocs build --strict`

## Reviewer Notes

Review focus: complete event identity, accurate duration semantics, visibility
of recorder failure, append-only behavior, separation from Collection Attempts,
unchanged latest-state selection, and absence of baseline or blocking impact.
