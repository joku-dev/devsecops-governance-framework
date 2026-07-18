# Blocking Readiness

## Current Result

The Blocking Readiness projection is a decision aid, not an enforcement
switch. Its current result is:

| Measure | Current value |
|---|---:|
| Registered repositories assessed | 3 |
| Technically ready | 0 |
| Not ready | 3 |
| Already blocking but below the new readiness bar | 1 |

`joku-dev/ha-CPsWMS` is the existing `block-on-error` integration that does not
yet satisfy the stronger new bar. This is a visible migration risk, not an
automatic rollback or mode change. Its current integration remains unchanged.

The demo consumer is also correctly `not_ready`: its latest DevSecOps result,
three-run mainline sample, Trust checks, and replay check pass. Its Trust level
remains `integrity_verified`, Typed Evidence has not yet been re-collected for
the newest commit, Architecture has 25 report-only findings, the observation
sample contains only four intake events, and two retained conflicts remain
visible.

## Criteria

The generator evaluates each registered repository against:

- released baseline pinning
- a clean latest DevSecOps result
- three consecutive successful mainline samples
- minimum Trust level `provenance_verified`
- no failed Trust checks and a passing replay check
- current, collected, Freshness-valid, integrity-valid Typed Evidence
- a clean Architecture result when that domain is present
- at least ten intake events with at least 99 percent success
- no repository intake conflicts and no globally open collection attempts
- defined waiver and rollback paths
- an explicit accountable approval

The thresholds are provisional and versioned in
`model/enforcement/blocking-readiness.yaml`. They may be changed later through
a new GCR. Existing reports must not be reinterpreted silently.

## Decision Semantics

`technical_ready: true` only means every automated prerequisite passed.
`ready_for_approval` still requires the accountable manual decision. Even an
approved model entry does not itself edit branch protection, workflows, OPA,
or an integration mode. Activation is a separate consumer-scoped change.

`already_blocking_but_not_ready` identifies an existing enforcement mode that
predates this stronger model. Operators must review it; the projection never
weakens or strengthens enforcement automatically.

The companion Blocking Mode Alignment projection now prevents that state from
remaining an unstructured warning. It records the preexisting `ha-CPsWMS` mode
as a time-bounded risk and rejects new unsafe Blocking registrations during
repository validation. See
`docs/operations/status/blocking-mode-alignment.md`.

## Generate And Validate

```bash
python3 scripts/generate_blocking_readiness.py
python3 scripts/validate_governance_repo.py
```

Every central intake path regenerates and commits the projection after updating
its domain index and Intake Health. This keeps readiness criteria synchronized
when Evidence closes or opens a technical gap.

The source is `generated/reports/blocking-readiness.json` and conforms to
`schemas/blocking-readiness.schema.json`.
