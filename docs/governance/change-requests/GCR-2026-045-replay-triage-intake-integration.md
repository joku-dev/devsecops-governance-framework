# Governance Change Request

## Summary

- Regenerate Replay Triage before the viewer in every central intake path.
- Commit the JSON and Markdown projections with accepted Evidence state.
- Replace state-specific tests with stable report and viewer invariants.

## Change ID

```text
GCR-2026-045
```

## Classification

This is an internal evidence-intake consistency fix. It introduces no source
document, control, architecture marker, consumer contract, released baseline,
OPA behavior, Trust change, or enforcement change.

## Root Cause

Replay Triage was generated during validation after the viewer had already
been rendered. The report was not staged by intake commits, and tests required
the repository's then-current finding count and remediation action to remain
unchanged. A successful remediation therefore correctly reduced the finding
count but caused validation to fail and left the viewer projection stale.

## Decision Boundary

- historical Evidence remains immutable
- official latest selection remains mainline-push based
- Trust and governance outcomes remain independent
- replay remains report-only
- no enforcement change is authorized

## Impact

| Area | Impact |
|---|---|
| DevSecOps, Architecture, and Typed Evidence intake | regenerate and stage Replay Triage before viewer generation |
| Tests | validate derived-summary consistency and stable viewer semantics |
| Released baselines and consumer workflows | unchanged |
| Historical status snapshots | unchanged |

## Validation Plan

- [x] focused Replay Triage and viewer tests
- [x] full runtime and repository validation
- [x] complete unit test suite
- [x] demo run and strict documentation build

## Release Decision

No release is required because only central projection consistency changes.
