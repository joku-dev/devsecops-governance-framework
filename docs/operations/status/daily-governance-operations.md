# Daily Governance Operations

## Purpose And Entry Point

The daily report combines workflow execution, accepted consumer evidence,
intake recovery, the review queue, and live repository self-security. It provides
an observation and a next action for each check, with an accountable role.
It is report-only and does not approve PRs, create issues, send messages, change
consumer enforcement, or update official indexes and the status viewer.

Open [Daily Governance Operations](https://github.com/joku-dev/devsecops-governance-framework/actions/workflows/governance-operations.yml),
select the latest scheduled run, and read its job summary. Download the
`governance-operations` artifact for:

- `governance-operations.md`: human-readable report;
- `governance-operations.json`: schema-validated checks, owners, actions, and thresholds;
- `operations-observation.json`: captured API observations and local inputs,
  including the self-security assessment and collection errors.

The schedule is daily at 06:43 UTC. Manual dispatch is available. PR runs are
previews based on the proposed checkout; only scheduled/main runs are the daily
operating observation. Both the checkout SHA and observed remote main SHA are
recorded so a preview cannot be mistaken for accepted evidence.

## Reading Status

| State | Meaning | Response |
|---|---|---|
| `ok` | This check meets its operational threshold | Continue routine observation; a young PR can still need review |
| `attention` | A known condition needs investigation or action | Assign a person and follow the recorded action |
| `unknown` | Missing access, incomplete results, or invalid data prevents an assessment | Restore observation before claiming a pass |

An overall `attention` takes precedence over `unknown`; the separate counters
and rows always preserve both. A successful report workflow means the report
was produced, not that all governance criteria passed. Self-security criteria
retain their original conservative fail semantics; API observation gaps are
also shown separately. An API 404 can mean an absent control or an inaccessible
setting, so its interpretation requires the recorded context.

Accountable owners come from the consumer registry or established Repository
Owner, Governance Platform Lead, and Security roles. They are not invented
individual assignments: the duty maintainer must name the person handling each
open action in the existing PR or agreed tracking system.

## Operational Warning Thresholds

Configuration: `.github/operations-report.json`.

| Signal | Initial rule |
|---|---|
| Governance CI | Latest observed push run for the current remote main commit must succeed |
| Documentation publication | Latest observed main run must succeed; path filters mean it need not match every main commit |
| Portfolio and self-security schedules | Successful scheduled run within 36 hours |
| CodeQL schedule | Successful scheduled run within 192 hours (8 days) |
| Running/queued intake | Investigate after 2 hours |
| Intake execution failures | Inspect failures, cancellations, skipped or overdue runs in the last 24 hours |
| Consumer evidence | Source result no older than 30 days, with a passing official mainline result |
| Open PRs | Review/merge queue warning after 24 elapsed hours; conflicts, requested changes and unhealthy checks require earlier attention |

These are adjustable operational warning thresholds, not approved business SLAs.
PR age includes drafts and approved PRs waiting for merge; it measures queue age,
not an individual's review performance. Governance and scheduled jobs still in
progress appear as attention until completion; the report identifies when the
2-hour execution/queue threshold is exceeded.

A manual success does not satisfy a missed scheduled heartbeat. A new intake or
index generation does not refresh an old source evaluation. The report reads
`latest_result` without changing selection: branch/manual fallbacks remain
visible as diagnostic evidence, not an official passing mainline result.
DevSecOps is checked for every registered consumer. Optional architecture and
typed-evidence domains are checked where already represented in their indexes;
this does not establish their mandatory scope for additional consumers.

Intake recovery is recomputed in memory from existing append-only events,
collection attempts and snapshots, including resolved versus open/permanent
attempts. No shared JSON is regenerated on disk. An old successful snapshot does
not become fresh just because collection succeeded today. The 30-day observation
sample is informational and does not grant blocking readiness.

## Daily Triage

1. Confirm the latest scheduled report exists. If it is missing, inspect the
   schedule, workflow enablement, runner availability and Actions incidents.
2. Assign the `unknown` rows: check credentials, endpoint access, malformed data
   and API result limits. Keep missing evidence visible; do not relabel it as pass.
3. For failed or stuck runs, open the linked workflow, identify the failing step,
   correct the cause and rerun. Check whether publication already created a PR
   before retrying; preserve failed attempts and historical snapshots.
4. For stale or missing consumer results, ask the consumer owner to produce a
   new mainline evaluation. Intake the new result and review its operational PR.
5. Review pending PRs and their checks. Reconcile conflicting operational PRs
   against current main, regenerate projections and rerun checks before approval.
   Maintainer-authored PRs require another authorized reviewer.
6. Route security findings to Repository Owner / Security. Use scoped verification
   for inaccessible settings; a green assessment job alone is not evidence that
   the settings are secure.
7. Record the named action owner and next action in the agreed tracker or PR.
   Rerun the report after remediation to verify the observed condition changed.

Routine triage does not authorize new blocking modes, waivers, changes to released
baselines, or branch-protection bypasses. The existing blocking-risk review date
remains governed by GCR-2026-050.

## Access, Retention And Limits

The workflow uses GITHUB_TOKEN with contents, Actions and pull-request **read**
permissions. It cannot publish commits or approve/merge PRs. Some security or
administrative endpoints remain inaccessible with that token; these gaps are
retained rather than hidden. Local execution can use an already authenticated
GitHub CLI account for comparison without changing workflow permissions.

API requests read up to 100 recent runs per workflow/query and 1,000 open main
PRs. Reaching a cap is explicitly `unknown`, not a claim of complete coverage.
Event-driven intake has no fixed heartbeat; absence is investigated through
consumer evidence age and telemetry, not an invented per-consumer cadence.

Artifacts are retained for 30 days and are operational diagnostics, not a
long-term audit archive. A workflow cannot independently alert when its own
scheduler stops. The duty maintainer must verify its daily presence; an external
heartbeat/notification channel is a separate integration decision. The existing
static viewer continues to show accepted governance evidence; it does not embed
this live operating report.

## Local Run And Reproduction

```bash
./scripts/bootstrap_validation_env.sh
.venv-validation/bin/python scripts/generate_operations_report.py \
  --output-dir /tmp/governance-operations
```

To re-evaluate captured inputs without GitHub requests, use the corresponding
implementation/configuration revision and the downloaded observation:

```bash
.venv-validation/bin/python scripts/generate_operations_report.py \
  --observation /tmp/governance-operations/operations-observation.json \
  --output-dir /tmp/governance-operations-replay
```

Replay uses the captured observation timestamp by default. `--as-of` explicitly
changes the evaluation time; it does not recollect GitHub data. The output SHA
always records the checkout actually executing the report.

Validation includes schema checks and regression cases for old evidence after
new intake, diagnostic context, observation failures, missed schedules, review
age, unresolved attempts, and successful jobs with security findings.
