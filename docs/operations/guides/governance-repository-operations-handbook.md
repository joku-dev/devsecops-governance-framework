# Governance Repository Operations Handbook

## Start Here

This is the operating entry point for the central governance repository and its
controlled test operation. Use the [consumer pilot runbook](../../onboarding/pilot-runbook.md)
for application-team adoption and the [beginner change guide](beginner-step-by-step-operations-guide.md)
for editing this repository.

The repository is operated through Git, validated workflows, reviewed evidence
PRs, and generated reports. A database or application server is not required for
the current pilot.

The [11 September 2026 maintenance record](../reference-runs/2026-09-11-operational-evidence-refresh.md)
documents a consumer evidence refresh, administrative security observations and
branch cleanup. It is a dated reference, not a replacement for current Actions
results or the accepted indexes.

## Authority And Reading Rules

| Question | Authoritative input / operating guide |
|---|---|
| What behavior is implemented? | Current workflows, scripts and configuration; [platform state](../status/current-governance-platform-state.md) explains the as-built state |
| Which baseline does a consumer use? | Its pinned release and consumer configuration; [release model](../../releases/release-and-migration-model.md) |
| What evidence is accepted? | Committed snapshots and indexes; [intake guide](../evidence/governance-result-intake-and-viewer-usage.md) |
| What is happening now? | Latest main Actions runs and [daily operations report](../status/daily-governance-operations.md) |
| Who may change enforcement? | Recorded decisions, [blocking alignment](../status/blocking-mode-alignment.md) and [migration procedure](../processes/blocking-enforcement-migration-guide.md) |

Dated reference runs, completed GCRs and versioned release notes describe their
recorded state. They are not proof of current evidence freshness or current
GitHub settings. Do not rewrite a released package or a historical result to
make it resemble today's state. A generated report also has an observation
clock; regenerating it does not create a new consumer evaluation.

## Operating Boundaries

| Area | Current operating rule |
|---|---|
| Central repository `main` | PR required; one approving review; strict required checks; resolved conversations; force pushes and deletion blocked; no standing bypass |
| Required checks | `validate-and-report`, `Analyze Python`, `Governance Repository Security` from GitHub Actions |
| Self-security and daily reports | Findings remain report-only even when report generation succeeds |
| New consumer pilots | Explicit `governance_mode: report-only` for manual, PR and main push runs; architecture `fail_on_findings: false` |
| Released DevSecOps wrapper | Its default is `block-on-error`; new consumer templates must explicitly override it with `report-only` |
| Existing `ha-CPsWMS` mode | Preserved legacy blocking risk; accountable review due 12 December 2026, 23:59:59 Europe/Berlin; not a precedent for new blocking |
| Operational updates | Bot PRs with allowlisted paths and immutable historical records; official indexes/viewer change after merge |

The one-off administrative exception used to merge PR #61 was restored and
recorded in that PR. It is not permission to disable review on subsequent PRs.
A bot PR can be reviewed by the maintainer. A PR authored under that maintainer's
account needs another authorized reviewer under the normal rules.

## Prepare A Controlled Test Operation

Before recording the pilot start:

1. Name the central maintainer and deputy, consumer owners, and the independent
   reviewer for maintainer-authored PRs. Agree where actions and decisions are
   tracked and who checks daily when the primary maintainer is absent.
2. Record selected repositories, exact implementation commit, baseline pins,
   start/end dates and decision date in the adoption decision record. Confirm
   current modes, including any existing legacy exception.
3. Prepare the [pinned validation environment](local-validation-toolchain.md)
   and confirm current main validation and documentation publishing succeed.
4. Set up and verify [GitHub access](../security/github-access-and-token-maintenance.md)
   in both collection and producer-dispatch directions, if automatic dispatch
   is in scope. Manual intake is a valid initial pilot path.
5. Obtain new real consumer mainline results. Placeholder wiring tests and
   re-intake of July results do not meet an evidence-freshness requirement.
6. Agree a protected backup location and run the local
   [recovery drill](../processes/governance-repository-backup-and-recovery.md).
   Record incomplete coverage explicitly before proceeding.
7. Open the latest daily report, confirm it can be downloaded and name the
   person responsible for every accepted open finding or observation gap.

The suggested initial duration is two weeks with one or two consumers. This is
an operating proposal, not a production SLA or authorization for blocking.

## Daily Routine

1. Open [Daily Governance Operations](https://github.com/joku-dev/devsecops-governance-framework/actions/workflows/governance-operations.yml)
   and confirm that the latest scheduled observation exists. It runs at 06:43
   UTC; a manual run is available for investigation but does not prove schedule
   delivery.
2. Read `attention` and `unknown` rows. Distinguish failed jobs, stale results,
   actual governance findings and inaccessible administrative settings.
3. Assign a named person and next action in the agreed tracker. The report's
   role names identify accountability; they are not individual assignments.
4. Review operational PRs and checks. A PR younger than 24 hours may be within
   the warning window and still need review. Failed collector runs may already
   have created a PR containing their failure records.
5. After merge, verify the appropriate main checks and Pages publication; then
   inspect the accepted indexes/viewer. The daily operations artifact is a
   separate observation and is not embedded in the static viewer.

Use the [daily report runbook](../status/daily-governance-operations.md) for
thresholds, reproduction, API limits and detailed triage. The report does not
create issues or send alerts. Until an external heartbeat is introduced, the
maintainer/deputy must notice a missing report.

## End-To-End Intake Check

Select a real producer mainline run from GitHub, rather than copying a historic
run ID from a demo page. From an authenticated workstation:

```bash
CONSUMER_REPO='owner/application'
PRODUCER_RUN_ID='REPLACE_WITH_ACTUAL_RUN_ID'
gh workflow run intake-governance-result.yml \
  --repo joku-dev/devsecops-governance-framework --ref main \
  -f repository_id="$CONSUMER_REPO" -f run_id="$PRODUCER_RUN_ID"
```

The placeholders must be replaced before execution. The collector infers the
baseline where available; provide an override only when it matches the producer.

Verify the workflow summary links to its operational PR. Inspect run identity,
source commit and artifact provenance, status/context, new records and derived
projections. Approve only the reviewed revision, merge through normal rules and
verify Pages. A repeated intake of the same result must preserve the existing
snapshot; a new operation event can still be recorded.

If main advances or projections conflict, reconcile the branch, preserve all
accepted records, regenerate the affected projections using the intake guide,
and rerun checks before the final review. Never resolve a conflict by silently
replacing historical evidence.

## Pilot Test And Exit Record

Record a run/PR link and expected versus actual outcome for each test:

| Test | Expected outcome |
|---|---|
| New real mainline result | Correct consumer, run, commit and baseline; review PR; accepted state after merge |
| Diagnostic branch/manual result | Visible context; cannot overwrite an available official mainline result |
| Same producer result collected twice | Existing snapshot unchanged; separate intake telemetry allowed |
| Missing artifact or denied collection access | Failure visible with its identity; preserved attempt/event; no false success |
| Retry after correcting the cause | Recovery visible, historical failure retained |
| Two distinct concurrent results | Separate proposals, no lost events; shared projection conflicts reconciled |
| Stale evidence and denied report access | Explicit attention/unknown; technical workflow success does not clear findings |
| Recovery drill | Git, evidence and generated projections recoverable within the agreed scope |

Run deliberate failure/concurrency tests in an agreed disposable consumer or
fixture context. Do not mislabel simulated artifacts as genuine production
evidence or edit production ledgers to manufacture test results.

At the end, record what passed, open findings, named owners, deadlines and a
continue/stop decision. Stop if evidence is lost or misattributed, access cannot
be restored, required reviews cannot be obtained, or failures become invisible.
A successful pilot supports continued report-only operation. New blocking
requires the separate readiness, approval and migration procedure.

## Escalation And Maintenance

| Condition | Responsible role | First action |
|---|---|---|
| Access/secret problem | Repository Owner + credential owner | Follow token recovery procedure; preserve failed runs |
| Intake or projection inconsistency | Governance Platform Lead | Stop affected merges, preserve records, reconcile and validate |
| Security finding | Repository Owner / Security | Verify evidence and assign remediation; do not infer approval from green CI |
| Reviewer unavailable | Repository Owner | Arrange an authorized independent reviewer; no standing bypass |
| Evidence ageing | Consumer owner | Produce new real evidence and review its intake |
| Backup/recovery failure | Governance Platform Lead | Preserve the last verified backup and investigate in isolation |

Review the action queue and access/backup inventory weekly during the pilot.
Revisit warning thresholds after observing actual workload. Any new external
alerting, archival service or enforcement change needs its own scoped decision.
