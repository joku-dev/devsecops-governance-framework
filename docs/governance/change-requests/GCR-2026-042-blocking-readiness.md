# Governance Change Request

## Summary

- Add a versioned, report-only Blocking Readiness model and projection.
- Assess every registered consumer against evidence, Trust, stability,
  operations, waiver, rollback, and approval criteria.
- Document staged activation and rollback without enabling blocking.

## Change ID

```text
GCR-2026-042
```

## Impact

| Area | Impact |
|---|---|
| Governance source documents | none |
| Controls, markers, OPA | none |
| Evidence and result indexes | read-only inputs; unchanged |
| New schemas and report | additive internal decision projection |
| Consumer repositories | none |
| Integration modes and branch rules | unchanged |
| Released baselines | unchanged |

## Current Decision

All three consumers are `not_ready` against the stronger provisional criteria.
One existing `block-on-error` integration is explicitly flagged as already
blocking but below the new bar. No automatic change follows from that finding.

## Safety Invariants

- `enforcement_change_authorized` is schema-locked to `false`
- manual approval is separate from technical readiness
- generation cannot edit workflows, integration modes, branch rules, or OPA
- historical conflicts and failed results remain visible
- activation and rollback are consumer-scoped reviewed changes

## Release Decision

- [x] No release required

The change adds an internal report-only assessment. A later consumer workflow,
policy package, or required-field change needs its own release and migration
decision.

## Validation Plan

- [x] current-state schema and safety test
- [x] technically ready fixture remains pending human approval
- [x] conflict and Architecture-finding negative test
- [x] full repository validation
- [x] strict documentation build
