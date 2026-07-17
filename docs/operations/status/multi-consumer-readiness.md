# Multi-Consumer Readiness

## Purpose

The Multi-Consumer Readiness report proves that the central governance
repository can keep several consumer repositories isolated while combining
their accepted status into shared projections.

The report is deterministic and report-only. It validates repository structure
and current registered data; it does not modify a consumer, accept evidence,
promote an adoption state, or change enforcement.

## Artifacts

| Artifact | Location |
|---|---|
| Generator and readiness validator | `scripts/generate_multi_consumer_readiness.py` |
| Schema | `schemas/multi-consumer-readiness.schema.json` |
| Machine-readable report | `generated/reports/multi-consumer-readiness.json` |
| Human-readable report | `generated/reports/multi-consumer-readiness.md` |
| Consumer registry | `status/application-repository-integrations.yaml` |

Run:

```bash
python3 scripts/generate_multi_consumer_readiness.py
python3 scripts/validate_governance_repo.py
```

Repository validation regenerates the report and fails if an isolation check
fails.

## Validated Boundaries

The report checks:

1. at least two distinct consumers are registered
2. registry identifiers and declared count are consistent
3. the DevSecOps index covers exactly the registered consumers
4. DevSecOps, Architecture, and Typed Evidence result paths remain isolated by
   repository slug
5. the portfolio projection covers exactly the registry
6. all three intake workflow concurrency groups include consumer repository
   and downstream run and do not cancel a distinct pending run
7. intake telemetry IDs are unique and stored below the matching consumer path
8. every repository dimension in Intake Health is registered

## Current Result

The current report passes all nine checks:

| Metric | Current value |
|---|---:|
| Registered consumers | 3 |
| Consumers with DevSecOps results | 3 |
| Consumers with Architecture results | 2 |
| Consumers with Typed Evidence results | 1 |
| Consumers with post-instrumentation telemetry | 1 |
| Isolation checks | 9 pass / 0 fail |

Current consumers are:

- `joku-dev/ha-CPsWMS`
- `joku-dev/ai-native-engineering-factory`
- `joku-dev/governance-framework-demo-consumer`

Different coverage per evidence domain is valid. Architecture and Typed
Evidence are optional consumer capabilities; readiness does not fabricate
missing domains. All registered consumers currently have an isolated accepted
DevSecOps latest-state projection.

Only the demo consumer has Intake Operation Events because telemetry was added
after the older consumer results were captured. Historical events are not
backfilled. A second live telemetry-producing consumer remains useful future
operational evidence, but it is not required to prove that storage, indexes,
portfolio reporting, workflow concurrency, and identifiers are multi-consumer
safe.

## Failure Interpretation

A failed readiness check means the central repository has an inconsistent or
cross-consumer projection. It fails repository validation but does not rewrite
historical evidence or convert a consumer workflow from report-only to
blocking. Repair the registry, path, index, workflow scoping, or projection and
regenerate the report.
