# Current Governance Platform State

## Observation Scope

This page describes the implemented operating model as checked on 11 September
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

The live main ruleset was read back on 11 September 2026: active, no bypass,
one approving review, stale approval dismissal, resolved conversations, strict
required checks, and prohibited force pushes/deletion. The required GitHub
Actions checks are `validate-and-report`, `Analyze Python`, and
`Governance Repository Security`. Configuration is versioned in
`.github/main-ruleset.json`; changing that file alone does not change GitHub.

The one-off review exceptions, including central PRs #64 and #67 on
11 September, were restored and audited in their PRs. They are not standing
operating permission.
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

## Accepted Results On 11 September 2026

Observation baseline: `4abe88294f299d7f801c74ff0161df234960c092`.
The accepted indexes contain new consumer evaluations from 11 September 2026:

| Consumer | Domain | Producer run | Recorded outcome |
|---|---|---|---|
| `ha-CPsWMS` | DevSecOps L1 | `34602002201` | `pass`; 16/16 applicable controls, 30 not applicable |
| `ha-CPsWMS` | Architecture L1 | `34602001140` | `pass`; 4/4 gates, zero findings |
| `ai-native-engineering-factory` | DevSecOps | `34503074356`, attempt 2 | `fail`; baseline gate reports direct pushes allowed |
| `governance-framework-demo-consumer` | DevSecOps L1 | `34606820493` | `pass`; one-gate fallback summary |
| `governance-framework-demo-consumer` | Architecture L1 | `34606820390` | `findings`; 25 findings across four gates |
| `governance-framework-demo-consumer` | Typed vulnerability evidence | `34606820493` | integrity and Freshness pass at verification; `integrity_verified` |

The Factory and demo-consumer DevSecOps snapshots summarize a baseline gate,
not a full control-catalog evaluation. Factory pins implementation commit
`31914e88b0669e0f6caed5bb9d0db71f762c2126`; the other two consumers use
`l1-baseline-v1.1.3`. Both architecture integrations use
`architecture-baseline-l1-v0.1.0`.

The accepted consumer commits are `6976bb2af2b9d47d2934273c444b6c9b62a81ea2`
for ha-CPsWMS, `371251fe17c6923a810ab437a6c27fc7bfb624ed` for Factory, and
`7d6a4f67c5e8441e1067405cc2da17218dc256fd` for the neutral demo consumer.

Sources are the committed `status/repository-results-index.json`,
`status/architecture-results-index.json`, `status/typed-evidence-results-index.json`
and their immutable snapshots. The portfolio report at 14:37:35 UTC contains
three consumers and zero stale or missing results in its assessed scope.
These timestamps describe the observation, not a permanent freshness guarantee.

Trust remains separate from outcome: ha-CPsWMS DevSecOps has an open replay
finding despite its passing controls. All three consumers remain below the
Blocking Readiness bar. The neutral consumer now has current Typed Evidence
for its accepted mainline commit; that previously open gap is closed.

## Central Operations And Remaining Findings

Governance CI `34611502655`, CodeQL `34611502609`, self-security `34611502768`
and Pages `34611502982` succeeded for the observation baseline. Manual daily
report [34611935724](https://github.com/joku-dev/devsecops-governance-framework/actions/runs/34611935724)
recorded `22 ok`, `11 attention`, `2 unknown` at 14:44:41 UTC. Success means
report generation worked. The report retains the earlier failed intake within
its observation window even though a later retry succeeded. It also exposes
an API result cap and administrative settings unavailable to the workflow token.

An authenticated administrative observation on 11 September distinguished
four confirmed self-security gaps: signed changes are not required, the
repository-level SHA-pinning switch is off, the three historical release tags
are unsigned, and Actions sources are unrestricted. Active workflow references
are SHA-pinned. Secret scanning, push protection, Dependabot security updates,
private vulnerability reporting and read-only default workflow permissions were
verified enabled. Unknown scheduled-token observations must not be represented
as proof that those controls are disabled. See the
[maintenance record](../reference-runs/2026-09-11-operational-evidence-refresh.md)
and [self-security procedure](../security/governance-repository-self-security.md).

No permanent review bypass remains. Intake PRs #68–71 and portfolio PR #72 were
reviewed and merged normally after the explicitly scoped exceptions were restored.
Historical producer results, failed collection records and released packages remain
available. Regenerating a report cannot turn those records into a new evaluation.

## Remaining Pilot Work

The [handbook](../guides/governance-repository-operations-handbook.md) provides
concrete setup, daily triage and acceptance tests. Before accepting a test
operation, record named owners and reviewers, maintain fresh real consumer
results, verify credential recovery, and rehearse the selected backup scope.
The September evidence refresh completed collection and acceptance for the
existing three consumers; it does not by itself complete the organisational
pilot acceptance tests.

Procedures now exist for token maintenance and recovery. Their existence does
not mean an off-site backup, individual assignments or recovery targets have
already been commissioned. Independent missing-heartbeat alerting, stronger
release signing, broader platform validation and new L2/L3 releases remain
separate changes. Source replacement candidates still require recorded review.
