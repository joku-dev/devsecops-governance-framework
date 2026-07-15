# Governance Change Request: Evidence Collector Contract

## Summary

- Define the provisional Evidence Collector Contract version `0.1.0`.
- Normalize source identity, timestamps, subjects, digests, custody, and errors.
- Map both automated governance-result intake paths to the first collector
  profile.
- Preserve historical Trust records and all report-only semantics.

## Change ID

```text
GCR-2026-030
```

## Artifact Classification

| Field | Value |
|---|---|
| Artifact name | Evidence Collector Contract v0.1 |
| Artifact type | evidence model, schema, example, and operational documentation |
| Target paths | `model/evidence/`, `schemas/`, `docs/examples/`, `docs/operations/evidence/` |
| Owner | governance-maintainers |
| Source Document Intake required? | no |
| Evidence contract impact | additive internal intake contract |
| Runtime governance impact | report-only |
| Release impact | none |
| Validation required | model and record schemas, intake tests, repository validation, strict docs build |

## Governance Invariants

- Collection status is not a Trust level or governance outcome.
- A successful collection requires authoritative identity, timestamps,
  digested subjects, and custody steps.
- Missing mandatory metadata cannot silently become `collected`.
- Historical snapshots and legacy string collector identities remain valid.
- New collector metadata does not change latest-result selection.
- No Collector or Trust signal blocks delivery.
- Blocking or required downstream fields require explicit migration and
  release review.

## First Profile

| Field | Value |
|---|---|
| Profile | `github-actions-governance-result` |
| Collector | `central-governance-intake` `0.1.0` |
| Evidence type | `governance_result` |
| Domains | DevSecOps and architecture |
| Provider | GitHub Actions |
| Stored record | `trust.capture` |
| Freshness policy | `freshness-governance-result-24h` |

The existing automated intake already obtains the authoritative run, artifact,
commit, subjects, and timestamps. This change normalizes those observations as
a versioned collector record before Trust verification.

## Impact

| Area | Impact |
|---|---|
| DevSecOps intake | Emits the collector contract for newly intaken results |
| Architecture intake | Emits the same contract with architecture domain context |
| Trust schema | Accepts legacy capture and requires complete metadata for new collector objects |
| Status indexes and viewer | unchanged; current historical snapshots are not rewritten |
| Downstream producers | unchanged |
| Policies and controls | unchanged |
| Released baselines and workflow refs | unchanged |

## Deferred Decisions

- authoritative scanner and subject identity for the vulnerability-scan pilot
- persistence and viewer projection of standalone failed collection attempts
- normalized transformation identifiers
- replay-key evaluation over collector identities
- any blocking behavior

## Release Decision

- [x] No release required
- [ ] Release candidate required
- [ ] Patch baseline release required
- [ ] Minor baseline release required
- [ ] Major baseline release required

The change is internal, additive, and compatible with historical records. It
does not modify a released package or downstream producer interface.

## Validation Plan

- [x] Contract model and record schema tests
- [x] Collected and failed record examples
- [x] DevSecOps and architecture domain mapping tests
- [x] Legacy Trust record compatibility test
- [x] `./scripts/validate_all.sh`
- [x] `mkdocs build --strict`
- [x] Generated timestamp-only noise removed

## Required Review Lenses

- Governance Analyst: contract intent and independent decision signals
- DevSecOps Baseline: evidence vocabulary and downstream compatibility
- Evidence And Intake: source authority, history, and latest-state behavior
- Release Manager: no baseline mutation or producer migration
- Repo Steward: focused scope, validation, and generated-output hygiene
