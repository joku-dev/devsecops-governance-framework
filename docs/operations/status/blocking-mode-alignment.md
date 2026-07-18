# Blocking Mode Alignment

## Purpose

Blocking Mode Alignment compares the modes registered in
`status/application-repository-integrations.yaml` with the report-only Blocking
Readiness assessment. It prevents a new `block-on-error` or `waiver-required`
registration from appearing without technical readiness and accountable
approval.

The projection does not change a workflow, branch rule, OPA result, or consumer
mode. `enforcement_change_authorized` is fixed to `false` in both model and
report schemas.

## Current State

| State | Count |
|---|---:|
| Non-blocking integrations | 2 |
| Blocking and fully aligned | 0 |
| Preexisting blocking under active risk review | 1 |
| Unsafe blocking registrations | 0 |

`joku-dev/ha-CPsWMS` has been registered as `block-on-error` since commit
`38abeba851a964a428a2e4a4ea2cfac414a33862` on 15 July 2026. That predates the
Blocking Readiness model. The alignment registry therefore records, but does
not approve, this preexisting mode.

The time-bounded record:

- preserves the current mode without changing it
- names Repository Owner and Governance Platform Lead
- lists the five unresolved readiness gaps
- requires review by Repository Owner, Governance Platform Lead, Security, and
  Release Manager
- expires for validation purposes after 18 August 2026
- never counts as valid activation under the new model

## Alignment States

| State | Meaning | Repository validation |
|---|---|---|
| `nonblocking` | Current mode does not block. | pass |
| `aligned_blocking` | Technical readiness and accountable approval both exist. | pass |
| `legacy_risk_active` | Blocking predates the model and has a complete, current risk record. | pass with visible risk |
| `unapproved_blocking` | Blocking lacks readiness and any valid preexisting record. | fail |
| `legacy_risk_incomplete` | Record does not match mode, cutoff, or current gaps. | fail |
| `legacy_risk_expired` | The required review date passed. | fail |

An orphaned risk record also fails validation. A newly blocking repository
cannot use a record whose `mode_observed_at` is on or after the model
introduction date to disguise a new activation as legacy.

## Generate And Review

```bash
python3 scripts/generate_blocking_readiness.py
python3 scripts/generate_blocking_mode_alignment.py
```

For a reproducible historical assessment:

```bash
python3 scripts/generate_blocking_mode_alignment.py \
  --as-of 2026-07-18T00:00:00Z
```

Source and outputs:

- registry: `model/enforcement/blocking-mode-alignment.yaml`
- registry schema: `schemas/blocking-mode-alignment-model.schema.json`
- report: `generated/reports/blocking-mode-alignment.json`
- report schema: `schemas/blocking-mode-alignment.schema.json`

## Required Review Outcome

Before the review due date, accountable reviewers must choose and record one of
these outcomes through a separate GCR:

1. remediate every current gap and create an accountable approval record
2. move the consumer to a non-blocking transition mode through an authorized
   consumer change
3. replace this risk record with a formally approved, time-limited exception
   that defines compensating controls and expiry

This repository does not make that organisational decision automatically.
