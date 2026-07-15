# Governance Change Request: Evidence Trust Additive Capture

## Summary

- Implement Phase 2 of the Evidence Trust Model in both automated GitHub
  Actions intake paths.
- Capture run attempt, authoritative artifact source, SHA-256 subjects, and
  initial chain-of-custody steps.
- Keep every captured trust record explicitly `unverified` and
  `not_evaluated` until Phase 3 introduces central verification projection.

## Change ID

```text
GCR-2026-027
```

## Artifact Intake Classification

| Field | Value |
|---|---|
| Artifact type | additive internal evidence contract and intake behavior |
| Primary paths | `schemas/evidence-trust-record.schema.json`, `scripts/intake_*github_actions_run.py` |
| Owner | governance maintainers |
| Source Document Intake required? | no |
| Runtime governance impact | report-only evidence capture |
| Release impact | none |

## Governance Intent

Phase 2 captures the raw material required for later trust verification without
claiming that verification has occurred. Computing a digest during intake
records the collected bytes; it does not prove that those bytes match an
independent producer claim or approved attestation.

The following invariant is mandatory:

```text
assessment_status = not_evaluated
=> effective_level = unverified
=> verifier = null
=> verified_at = null
=> checks = []
```

## Impact Analysis

| Area | Impact |
|---|---|
| DevSecOps intake | New snapshots capture archive and extracted-content digests, run attempt, source, and custody |
| Architecture intake | New snapshots capture archive, report, and release-input digests, run attempt, source, and custody |
| Historical snapshots | Unchanged and still valid |
| Result indexes | No trust projection and no selection change |
| Viewer | No trust badge or interpretation change |
| Governance outcome | Unchanged; `pass`, `fail`, and `findings` remain independent |
| OPA and workflows | No enforcement change |
| Released baselines | Unchanged |
| Downstream producers | No new required field |

## Derived Artifacts

- `scripts/lib/evidence_trust.py`
- `schemas/evidence-trust-record.schema.json`
- `docs/examples/evidence-trust-record.example.json`
- `scripts/intake_github_actions_run.py`
- `scripts/intake_architecture_github_actions_run.py`
- `tests/test_evidence_trust_capture.py`
- updated Evidence Trust Model, operations guidance, lineage, and impact reports

## Governance Behavior

- [ ] Documentation-only
- [x] Report-only governance behavior
- [ ] Blocking governance behavior
- [ ] Release packaging only

No trust value participates in a gate or changes a governance result.

## Latest-State Decision

The existing mainline selection rule remains unchanged. A main `push` remains
the official latest result; branch, pull-request, and manual evidence remain
history. Phase 2 data is stored only inside newly created snapshots and is not
projected into the indexes or viewer.

## Release Decision

- [x] No release required
- [ ] Release candidate required
- [ ] Patch baseline release required
- [ ] Minor baseline release required
- [ ] Major baseline release required

The central intake extension is additive, historical records remain valid, and
downstream workflows do not need to produce a new contract field.

## Deferred Decisions

- authoritative producer-digest comparison
- normalized snapshot digest and transformation log
- freshness windows and replay evaluation
- trusted issuer registry and attestation format
- any trust-based enforcement

These belong to later phases and are not approved by this change.

## Validation Plan

- [x] Evidence Trust record schema and negative invariant tests
- [x] DevSecOps and architecture intake tests
- [x] `./scripts/validate_all.sh`
- [x] `mkdocs build --strict`
- [x] Source lineage regenerated with no missing artifacts
- [x] Generated timestamp-only noise removed from commit

## Required Review Lenses

- Governance Analyst: intent and deferred decisions
- Evidence And Intake: context, latest-state rule, and snapshot compatibility
- Repo Steward: validation, generated-output hygiene, and focused commit
