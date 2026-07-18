# Replay Triage

## Purpose

Replay Triage turns stored replay checks into an operational, report-only work
queue. It answers three separate questions without changing their meaning:

1. What result was recorded in the immutable Evidence snapshot?
2. How does the current replay logic interpret the same history?
3. What action, if any, should an operator take?

The generated projection is available as
`generated/reports/replay-triage.json`, its readable companion is
`generated/reports/replay-triage.md`, and official-latest assessments appear in
the status viewer.

## Decision Boundary

Replay Triage does not:

- rewrite historical snapshots or their recorded `replay_key_unique` check
- change Evidence Trust levels or governance outcomes
- change `latest_result` selection
- authorize or activate blocking enforcement

The JSON projection records all four boundaries explicitly as `false`. The
repository validator rejects a projection that violates them.

## How The Projection Is Built

Run:

```bash
python3 scripts/generate_replay_triage_report.py
```

The generator reads Trust-bearing snapshots from DevSecOps, Architecture, and
Typed Evidence history. In chronological order it re-evaluates each replay
relationship with the current ledger rules. It writes a new derived report; it
never writes back to the source snapshots.

The report timestamp is deterministic: it uses the newest stored snapshot time,
not the local execution time.

All three central intake workflows regenerate Replay Triage before generating
the viewer and commit both report formats with the accepted status projection.
Tests validate report invariants rather than requiring a particular finding to
remain open, so successful remediation can reduce the current finding count to
zero without weakening the decision boundaries.

## Classifications

| Classification | Meaning | Normal action |
|---|---|---|
| `new_evidence` | No earlier matching subject digest exists. | none |
| `idempotent_reintake` | The same replay identity was delivered again. | none |
| `compatible_reuse` | Digest reuse stays within a compatible repository, commit, and artifact context. | none |
| `deterministic_report_reuse` | A normalized report digest was reused, but an artifact digest proves a newly bound artifact. | none |
| `legacy_assessment_superseded` | A stored failure is still preserved, but later compatibility hardening makes the current interpretation pass. | retain the historical result; no rewrite |
| `cross_commit_reuse` | The same subject digest crosses commits without enough artifact binding. | reverify with an artifact digest |
| `cross_repository_reuse` | A subject digest appears in another repository context. | investigate provenance and subject binding |
| `cross_artifact_reuse` | A digest crosses incompatible artifact identities. | investigate artifact identity |
| `cross_subject_conflict` | A digest is associated with incompatible subject identifiers. | quarantine and investigate subject binding |
| `same_context_content_conflict` | One decision context carries inconsistent content. | quarantine and investigate integrity |
| `not_evaluated` | Required Trust or replay metadata is absent. | collect the missing context |

The detailed assessment also retains related source file, repository, commit,
run, artifact, and shared subject identifiers where a relationship exists.

## Current Repository Interpretation

The current projection reviews 18 Trust-bearing snapshots. Three immutable
snapshots contain a recorded replay failure. Under the current rules, two are
classified as `legacy_assessment_superseded`; one remains an actionable
official-latest finding.

That finding is the DevSecOps result for
`joku-dev/governance-framework-demo-consumer`, run `29603835297`. The same
normalized control-report digest crossed commits, but the accepted snapshot has
no `artifact_digest`. The recommended remediation is to produce a fresh run
whose collected artifact includes that digest. The existing snapshot must not
be edited or deleted.

## Operator Workflow

1. Open the viewer's **Replay Triage** section.
2. Compare **Recorded** with **Current Interpretation**.
3. Prioritize rows where the current interpretation is `fail` and
   `official_latest` is true.
4. Follow the recommended action and create new Evidence through the normal
   producer and intake path.
5. Regenerate and validate the projection.
6. Preserve the old snapshot as audit history.

For investigations, use the JSON report because it contains the complete
chronology and relationship details. The viewer intentionally shows only the
official-latest operational slice.

## Validation

```bash
python3 scripts/generate_replay_triage_report.py
python3 scripts/validate_governance_repo.py
python3 -m unittest tests.test_replay_triage_report
```

The schema is `schemas/replay-triage.schema.json`. Tests cover schema validity,
decision boundaries, cross-commit reuse without an artifact digest, legacy
assessment supersession, cross-repository reuse, and cross-subject conflict.

## Release Impact

This is an internal derived projection and viewer enhancement. It introduces no
mandatory consumer field, released baseline change, OPA behavior, or workflow
enforcement change. A future blocking use of replay classification requires a
separate governance decision, migration plan, and release assessment.
