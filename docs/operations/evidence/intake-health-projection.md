# Intake Health Projection

## Purpose

The Intake Health projection turns append-only central intake telemetry into a
deterministic operational read model. It answers how often intake completed,
how long collection took, which consumers and collectors were involved, and
whether operational failures or append-only conflicts require attention.

The projection is report-only. It does not define an SLO, approve a threshold,
change Evidence Trust, select `latest_result`, or block delivery.

## Contract And Output

| Artifact | Location |
|---|---|
| Projection schema | `schemas/intake-health.schema.json` |
| Generator | `scripts/generate_intake_health.py` |
| Current projection | `status/intake-health.json` |
| Event source | `status/intake-events/` |
| Collection lifecycle source | `status/collection-attempts/` and successful snapshots |
| Conflict source | `status/intake-conflicts/` |
| Latest-result sources | the three result indexes under `status/` |

The three central intake workflows regenerate the projection after recording
an operation event, validate the result and propose it on an automation branch
through `scripts/publish_operational_update.py`. Review and merge make the
change official. When concurrent proposals overlap, reconcile and regenerate
their projections from the combined accepted history before merging.

## Observation Window

Event success, failure, and duration metrics use an explicit rolling window.
The default is 30 days and is recorded as `window.started_at` and
`window.ended_at`. Historical events are never deleted; events outside the
window simply do not contribute to the current metrics.

For deterministic tests or historical reconstruction, provide `--as-of`:

```bash
python3 scripts/generate_intake_health.py \
  --window-days 30 \
  --as-of 2026-07-17T21:56:30Z
```

Without `--as-of`, the generator uses the current UTC time.

## Metrics

`summary.events` contains:

- total, successful, partial, and failed executions
- success rate
- combined partial-or-failed rate
- minimum, nearest-rank p50, nearest-rank p95, and maximum collection duration

The same event metrics are broken down by:

- consumer repository
- collector ID and version
- intake type
- evidence type

The projection also contains all-time operational context:

- `open`, `resolved`, and `permanent` Collection Attempt counts
- total append-only intake conflict records
- the age of each accepted latest result at projection time

Collection-attempt lifecycle is derived from immutable attempts and matching
successful snapshots. It uses the same shared lifecycle function as the static
viewer, so operational counts cannot drift between projections.

## Interpretation

`observation_status: observed` means at least one event exists inside the
window. `no_data` means the metric window has no events; it does not mean the
intake system is healthy or unhealthy.

A 100% success rate from three smoke-test events is evidence that those three
runs succeeded, not a production SLO baseline. Thresholds, alerts, retry
budgets, and blocking effects require a separate governance decision after a
representative operating period.

At the committed observation of **11 September 2026, 14:34:14 UTC**, the
30-day window records six successes, no failed or partial accepted events,
p50 3 seconds, p95 4 seconds, no Collection Attempts, and two retained
report-only conflicts. Telemetry covers ha-CPsWMS and the neutral demo;
Factory's manual intake is not converted into synthetic telemetry. These
accepted records do not include every Actions execution: Daily Operations
can still show a failed workflow attempt that produced no accepted event.
See [current platform state](../status/current-governance-platform-state.md).

## Viewer

The static status viewer contains a dedicated `Intake Health` section with:

- observation count and explicit window
- success rate without a health verdict or approved SLO
- p50 and p95 collection duration
- partial and failed execution count
- Collection Attempt and conflict context
- breakdowns by repository, collector, intake type, and evidence type
- age of each accepted latest result at projection time

The section reads `status/intake-health.json`; it does not calculate a second
set of metrics. `Intake Conflicts` and `Collection Attempts` remain available
as separate detail sections for the underlying append-only records.

## Validation

```bash
python3 scripts/generate_intake_health.py
python3 scripts/generate_status_viewer.py
python3 scripts/validate_governance_repo.py
python3 -m unittest tests.test_generate_intake_health
./scripts/validate_all.sh
mkdocs build --strict
```
