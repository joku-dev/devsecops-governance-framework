# Governance Change Request: Evidence Trust Verification Projection

## Summary

- Implement the report-only Phase 3 Trust verifier for newly intaken evidence.
- Derive `integrity_verified` only when subject identity is complete and every
  captured digest matches a fresh recomputation over the collected bytes.
- Project Trust separately into both result indexes and the status viewer.
- Keep unresolved provenance, freshness, replay, custody, and attestation
  checks visible as `not_evaluated`.

## Change ID

```text
GCR-2026-028
```

## Classification

| Field | Value |
|---|---|
| Change type | evidence verification and internal status projection |
| Source Document Intake required? | no |
| Enforcement | report-only |
| Historical snapshots | unchanged |
| Latest-result selection | unchanged |
| Downstream producer contract | unchanged |
| Baseline release | none |

## Governance Invariants

- Governance outcome and evidence Trust remain independent.
- Missing historical Trust records project as `unverified/not_available`.
- A digest mismatch produces a failed check and prevents
  `integrity_verified`.
- `provenance_verified` remains unreachable until all required checks pass.
- Freshness, replay, complete custody, and attestation are not inferred.
- No Trust result blocks delivery or changes an OPA finding.

## Impact

| Area | Impact |
|---|---|
| DevSecOps intake | Recomputes captured-subject hashes and records verification checks |
| Architecture intake | Same verifier and derivation rules |
| Result indexes | Additive Trust projection in latest and history records |
| Viewer | Shows evidence Trust independently beside governance status |
| Current demo | Existing official snapshots remain `pass` and project as `unverified` |
| Policies and controls | unchanged |
| Released baselines and workflow refs | unchanged |

## Deferred Decisions

- evidence-type freshness windows
- replay-key conflict policy
- verified architecture baseline resolution
- normalized snapshot digest and transformation model
- issuer registry and attestation envelope
- any Trust-based enforcement

Freshness policy blocks completion of Phase 3. This change establishes the
projection safely without choosing those human governance rules implicitly.

## Release Decision

- [x] No release required
- [ ] Release candidate required
- [ ] Patch baseline release required
- [ ] Minor baseline release required
- [ ] Major baseline release required

The official downstream run-input contract, released packages, policies, and
reusable baseline workflows do not change.

## Validation Plan

- [x] Positive integrity verification test
- [x] Digest-tamper downgrade test
- [x] Historical snapshot compatibility test
- [x] Index schema and latest-result selection tests
- [x] Viewer separation test
- [x] `./scripts/validate_all.sh`
- [x] `python3 scripts/run_demo.py`
- [x] `mkdocs build --strict`
- [x] Generated timestamp-only noise removed

## Required Review Lenses

- Governance Analyst: independent outcome and Trust semantics
- Evidence And Intake: context, history, latest-state, and viewer projection
- Demo Readiness: current ha-CPsWMS status remains consistent
- Release Manager: no consumer migration or baseline mutation
- Repo Steward: validation and focused generated-output scope
