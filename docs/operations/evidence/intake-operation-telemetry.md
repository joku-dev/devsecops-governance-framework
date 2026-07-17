# Intake Operation Telemetry

## Purpose

Intake operation telemetry records every central DevSecOps, architecture, and
typed-evidence intake execution. It provides the event history needed to
calculate reliable operational indicators such as success rate, failure rate,
and intake duration in a later health projection.

The telemetry is additive, append-only, and report-only. It does not change a
governance outcome, Evidence Trust, `latest_result`, portfolio status, or
delivery enforcement.

## Why A Separate Event Is Needed

The existing stores answer different questions:

| Store | Question |
|---|---|
| Result snapshot | What governance or Evidence result was accepted? |
| Collection attempt | Which failed or partial collection requires operator attention or retry? |
| Intake operation event | Did a central intake execution succeed, fail, or remain partial, and how long did it take? |

A success rate needs both successful and unsuccessful events. Result snapshots
alone are not a safe denominator because idempotent intake can succeed without
creating a new snapshot, while failed collection attempts contain only failure
history.

## Contract And Storage

| Artifact | Location |
|---|---|
| Schema | `schemas/intake-operation-event.schema.json` |
| Schema-valid example | `docs/examples/intake-operation-event.example.json` |
| Recorder | `scripts/record_intake_event.py` |
| Event ledger | `status/intake-events/` |
| Conflict quarantine | `status/intake-conflicts/intake-events/` |

Each event records:

- consumer repository and downstream run
- intake type: DevSecOps governance, architecture governance, or typed evidence
- evidence type, collector, and artifact
- central intake workflow, run, and run attempt
- trigger event
- start and completion timestamps
- duration in milliseconds
- `success`, `partial`, or `failed`
- a structured error for partial or failed events

## Event Identity And Append-Only Behavior

The event identity binds:

```text
consumer repository
+ intake and evidence type
+ collector id and version
+ downstream run and artifact
+ central workflow, run and run attempt
```

Re-running the recorder with an identical event is idempotent. A different
payload with the same event identity does not overwrite history; it creates a
report-only conflict under `status/intake-conflicts/intake-events/`.

A retry started through `Retry Collection Attempt` creates a new central
workflow run and therefore a new telemetry event. The original failure remains
available for audit.

## Workflow Integration

Telemetry is integrated into:

- `.github/workflows/intake-governance-result.yml`
- `.github/workflows/intake-architecture-result.yml`
- `.github/workflows/intake-evidence-trust.yml`

Each workflow captures a start timestamp immediately before collection, runs
the existing intake, then records the operation outcome before regeneration,
validation, and commit. The commit step includes `status/intake-events/`.

If collection fails, the workflow records both:

1. a collection attempt for recovery and lifecycle handling
2. an intake operation event for operational measurement

The workflow still ends as failed after those report-only records have been
persisted. A telemetry recorder failure also makes the workflow fail visibly.

## Manual Recorder Example

```bash
python3 scripts/record_intake_event.py \
  --repository-id owner/repo \
  --run-id 42 \
  --evidence-type governance_result \
  --collector-id central-governance-intake \
  --artifact-name governance-control-evaluation \
  --intake-type devsecops_governance \
  --status success \
  --started-at 2026-07-17T12:00:00Z \
  --completed-at 2026-07-17T12:00:03Z \
  --intake-repository-id governance/framework \
  --intake-workflow-name "Intake Downstream Governance Result" \
  --intake-run-id 84 \
  --intake-run-attempt 1 \
  --trigger-event repository_dispatch
```

For a failed or partial event, add `--error-code` and `--message`. Successful
events cannot contain errors. Completion cannot precede start, and timestamps
must include a timezone.

In GitHub Actions, repository, workflow, intake run, run attempt, and trigger
event default from the standard `GITHUB_*` environment variables.

## Current Limits

- Telemetry begins when the instrumented workflows are merged; historical
  snapshots are not converted into synthetic events.
- No SLO or alert threshold is defined by this contract.
- No viewer or portfolio status is changed in this first increment.
- Duration currently measures the central collection step boundary established
  by the workflow, not downstream evidence production time.
- Events are stored in Git and therefore share the repository's current write
  throughput and concurrency limits.

## Next Increment

The next PR can create a deterministic intake-health projection using these
events. Initial report-only indicators should include:

- success and failure rate over an explicit window
- duration percentiles
- event counts by consumer, collector, and evidence type
- open and permanent collection failures
- append-only conflict count
- age of the last accepted mainline result

Thresholds and alerts should be approved only after enough real events exist to
establish a useful baseline.

## Validation

```bash
python3 scripts/validate_governance_repo.py
python3 -m unittest tests.test_record_intake_event
python3 -m unittest tests.test_result_ledger
python3 -m unittest tests.test_intake_workflow_concurrency
./scripts/validate_all.sh
mkdocs build --strict
```
