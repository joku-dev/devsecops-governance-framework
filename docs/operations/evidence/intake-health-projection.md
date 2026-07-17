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

The three central intake workflows regenerate and commit the projection after
recording an operation event. Concurrent workflows recalculate it from the
complete Git-backed event history after rebasing on `main`.

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

The committed projection currently records the validated three-path smoke
test: three successes, no failed or partial events, p50 2 seconds, p95 3
seconds, no Collection Attempts, and two retained report-only conflicts.

## Validation

```bash
python3 scripts/generate_intake_health.py
python3 scripts/validate_governance_repo.py
python3 -m unittest tests.test_generate_intake_health
./scripts/validate_all.sh
mkdocs build --strict
```
