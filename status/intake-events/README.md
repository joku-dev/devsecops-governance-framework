# Intake Operation Events

This directory contains append-only, report-only telemetry for central
governance, architecture, and typed-evidence intake operations.

Unlike `status/collection-attempts/`, which records failed or partial evidence
collection for operator retry, this ledger records every central intake
execution, including success. It supplies the denominator required for later
success-rate, failure-rate, and latency projections.

Events validate against `schemas/intake-operation-event.schema.json` and are
written by `scripts/record_intake_event.py`. Event identity binds the consumer,
intake type, downstream run, collector, artifact, and central workflow run attempt.
Identical delivery is idempotent. A changed payload for an existing event ID is
quarantined under `status/intake-conflicts/intake-events/`.

These events do not change a governance outcome, Evidence Trust, `latest_result`,
or enforcement. Do not edit or delete historical events manually.
