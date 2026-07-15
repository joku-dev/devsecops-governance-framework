# Governance Change Request: Provisional Evidence Freshness Policies

## Summary

- Define versioned, provisional Freshness rules for six evidence types.
- Evaluate the 24-hour governance-result rule during both automated intake
  paths.
- Keep all Freshness findings report-only and independent from governance
  outcomes.
- Preserve historical assessments when a later policy version changes a rule.

## Change ID

```text
GCR-2026-029
```

## Classification

| Field | Value |
|---|---|
| Change type | evidence validity policy and internal intake verification |
| Source Document Intake required? | no |
| Policy status | provisional |
| Enforcement | report-only |
| Historical snapshots | unchanged; no retrospective reclassification |
| Latest-result selection | unchanged |
| Downstream producer contract | unchanged |
| Baseline release | none |

## Provisional Rules

| Evidence type | Rule |
|---|---|
| Governance result | maximum age 24 hours |
| Vulnerability scan | maximum age 24 hours |
| Runtime evidence | maximum age 30 minutes |
| Architecture review | maximum age 180 days |
| SBOM | exact evaluated-subject binding |
| Release approval | exact release-candidate binding |

Only the governance-result rule has authoritative timestamps available in the
current intake contract and is evaluated now. The other rules are configured
but remain `not_evaluated` until typed timestamps or subject bindings are
captured.

## Governance Invariants

- Freshness and governance outcome remain independent.
- Missing or invalid timestamp metadata does not count as verified.
- Future-dated and expired governance results produce a visible failed check.
- A Freshness finding does not block delivery or change an OPA finding.
- A policy change requires a new GCR and policy version.
- Existing stored assessments retain the policy version under which they were
  evaluated and are not silently recalculated.
- Blocking remains gated by explicit release and migration review.

## Impact

| Area | Impact |
|---|---|
| DevSecOps intake | Evaluates workflow-update age against the 24-hour rule |
| Architecture intake | Uses the same policy and verifier |
| Trust records | Add policy identity, timestamps, age, limit, and reason to the Freshness check |
| Result indexes and viewer | Existing Trust summary can expose a failed check; selection is unchanged |
| Current demo | Existing official snapshots are not rewritten |
| Policies and controls | unchanged |
| Released baselines and workflow refs | unchanged |

## Change Procedure

To change a window or binding rule later:

1. create a new GCR with the reason and affected evidence types
2. increment the policy-set version
3. update schema examples, evaluator tests, and operational guidance
4. validate representative fresh, expired, future-dated, and missing metadata
5. preserve existing snapshots and their recorded policy version
6. perform release review before considering any blocking behavior

## Release Decision

- [x] No release required
- [ ] Release candidate required
- [ ] Patch baseline release required
- [ ] Minor baseline release required
- [ ] Major baseline release required

The released baselines, reusable workflows, producer contract, and
report-only enforcement semantics do not change.

## Validation Plan

- [x] Policy model schema validation
- [x] Boundary, expired, future, and missing timestamp tests
- [x] Report-only outcome-independence test
- [x] Both automated intake paths use the shared policy
- [x] `./scripts/validate_all.sh`
- [x] `mkdocs build --strict`
- [x] Generated timestamp-only noise removed

## Required Review Lenses

- Governance Analyst: provisional rule intent and explicit approval gap
- DevSecOps Baseline: typed evidence and control-model consistency
- Evidence And Intake: timestamp authority, history, and latest-state behavior
- Release Manager: no baseline mutation and future blocking gate
- Repo Steward: focused scope, validation, and generated-output hygiene
