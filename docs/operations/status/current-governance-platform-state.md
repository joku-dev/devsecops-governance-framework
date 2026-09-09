# Current Governance Platform State

## Observation Scope

This page describes the implemented operating model as checked on 9 September
2026. For daily operation use the [operations handbook](../guides/governance-repository-operations-handbook.md).
For live observations use the latest main workflow artifacts and
[daily operations report](daily-governance-operations.md). A dated document or
successful workflow is not a current compliance attestation.

## Implemented Capabilities

| Layer | Implementation and responsibility |
|---|---|
| Governance sources | Approved sources and lineage in `docs/governance/`, `model/` and `architecture/`; candidates require recorded review before derivation |
| Executable governance | OPA policies, schemas, collectors and validators translate the approved model into evaluated evidence |
| Released baselines | DevSecOps `l1-baseline-v1.1.3`; architecture `architecture-baseline-l1-v0.1.0`; frozen packages under `releases/` |
| Accepted results | Append-only snapshots and digests, manifests, domain indexes and collection-attempt records under `status/` |
| Intake telemetry | Append-only `status/intake-events/` feeds Intake Health, readiness and daily operating observations |
| Operational publication | Four intake/portfolio writers propose scoped bot PRs; accepted state changes on protected main after review and merge |
| Status viewer and graph | Script-generated `generated/viewer/status-viewer.html` and `generated/graph/governance-graph.json`; read-only projections |
| Documentation publication | `.github/workflows/publish-docs.yml` builds MkDocs strictly and deploys Pages, including generated assets |
| Self-security | Report-only assessment of this repository, independently of consumer governance results |
| Daily operations | `.github/workflows/governance-operations.yml`, daily 06:43 UTC and manual runs; summary and retained artifacts, no automatic alert delivery |

Normalized evidence is held in Git; original producer artifacts remain subject
to their retention settings and selected archival. The current pilot requires no
database. See the [storage model](../evidence/governance-results-storage-model.md)
and [backup procedure](../processes/governance-repository-backup-and-recovery.md).

## Protection And Enforcement

The live main ruleset was read back on 9 September 2026: active, no bypass,
one approving review, stale approval dismissal, resolved conversations, strict
required checks, and prohibited force pushes/deletion. The required GitHub
Actions checks are `validate-and-report`, `Analyze Python`, and
`Governance Repository Security`. Configuration is versioned in
`.github/main-ruleset.json`; changing that file alone does not change GitHub.

PR #61 used an explicitly authorized one-off review exception, then restored
the rule. That recorded exception is not a standing operating permission.
Maintainer-authored PRs need another authorized reviewer under the normal rules.
See [self-security](../security/governance-repository-self-security.md).

New consumer pilots explicitly select `governance_mode: report-only` for all
triggers and architecture `fail_on_findings: false`. The released DevSecOps
wrapper still defaults to blocking if the mode is omitted. Copy the current
reviewed [adoption guidance](../../onboarding/public-repo-quickstart.md) and record
its revision separately from the frozen baseline pin.

The preexisting `ha-CPsWMS` blocking integration remains a recorded legacy risk,
with review due 12 December 2026, 23:59:59 Europe/Berlin. It does not authorize
new blocking. [Blocking alignment](blocking-mode-alignment.md) and the
[readiness assessment](blocking-readiness.md) explain the decision boundary.

## Demonstrated Results And Their Limits

The retained `ha-CPsWMS` mainline reference evidence is from 15 July 2026:

| Domain | Recorded status | Baseline | Producer run |
|---|---|---|---|
| DevSecOps | `pass` | `l1-baseline-v1.1.3` | `29415015878` |
| Architecture | `PASS` | `architecture-baseline-l1-v0.1.0` | `29415015294` |

These results demonstrate the integration at that time. Re-intaking them or
regenerating a viewer does not produce a fresh application evaluation.
The committed readiness projection assesses three integrations and identifies
zero technically ready for new blocking; consult its timestamp and source
results before using that count in a decision.

On 9 September the real central intake run `34328381713` exercised bot-PR
publication through PR #60. Main governance validation, CodeQL, self-security
and Pages publication succeeded after PR #61. The first manual daily operations
run `34334095492` also succeeded. Its execution proves report production, not
scheduled delivery, absence of findings or complete administrative API access.
These are dated observations; use current Actions for subsequent state.

## Remaining Pilot Work

The [handbook](../guides/governance-repository-operations-handbook.md) provides
concrete setup, daily triage and acceptance tests. Before accepting a test
operation, record named owners and reviewers, collect fresh real consumer
results, verify credential recovery, and rehearse the selected backup scope.

Procedures now exist for token maintenance and recovery. Their existence does
not mean an off-site backup, individual assignments or recovery targets have
already been commissioned. Independent missing-heartbeat alerting, stronger
release signing, broader platform validation and new L2/L3 releases remain
separate changes. Source replacement candidates still require recorded review.
