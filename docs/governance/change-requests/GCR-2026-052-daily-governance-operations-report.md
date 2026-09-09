# Governance Change Request

## Change ID

`GCR-2026-052`

## Decision And Classification

On 9 September 2026 the maintainer accepted the proposal to start operationalizing
the repository with a daily operating report: "dann lass uns das machen".

| Field | Value |
|---|---|
| Artifact | Read-only daily report generator, JSON schema, workflow configuration, operating guide and tests |
| Type | Generated operational observation and internal operating process |
| Owner | Governance Platform Lead; security actions Repository Owner / Security |
| Source Document Intake required | no; no new normative source or source-register change |
| Evidence contract impact | new internal report schema only; downstream evidence contracts unchanged |
| Runtime governance impact | none; no result promotion or enforcement activation |
| Viewer impact | none; report published through Actions summary/artifacts |
| Release impact | none |

## Scope

`scripts/generate_operations_report.py` combines accepted local evidence indexes,
recomputed intake recovery, main workflow observations, open PR metadata, and
live self-security findings. It preserves differences between technical job
success, findings, and unavailable observations. It does not manufacture current
evidence by refreshing intake timestamps or accept branch/manual fallbacks as
official passing mainline results.

`.github/operations-report.json` records operational warning thresholds: 30-day
evidence age, 24-hour PR queue age, 2-hour run warning, daily scheduled heartbeat
within 36 hours and weekly CodeQL within 192 hours. These are initial triage
indicators, not approved contractual SLAs or new enforcement gates.

The workflow runs daily at 06:43 UTC, supports manual execution, and produces PR
previews when its implementation changes. It only reads repository and GitHub
data and uploads a report plus captured observations with 30-day retention.
There are no direct writes, PR approvals, automatic merges, messages, issues,
new external credentials or branch-rule changes.

Owners are existing accountable roles; assigning named reviewers and action
owners remains a maintainer responsibility. Long-term archival, independent
heartbeat alerts, credential changes, and wider consumer rollout are separate
work. Missing administrative API access remains visible.

## Validation And Activation

Test deterministic reporting, freshness and queue thresholds, source context,
failed and absent jobs, incomplete observations, immutable input handling and
report-only schema invariants. Run the pinned bootstrap and full validation,
strict documentation build, a live local preview, and the GitHub PR workflow.
Merge requires the existing main reviews and checks; the new schedule becomes
active only after this PR is reviewed and merged. PR artifacts provide a
reviewable preview before activation.

No released baseline or historical evidence is modified. No baseline release is
required.
