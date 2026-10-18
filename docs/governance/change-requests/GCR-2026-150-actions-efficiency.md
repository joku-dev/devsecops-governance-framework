# GCR-2026-150: Preserve governance checks while reducing repeated Actions work

Status: proposed for review. Date: 18 October 2026.
Source revision: `66e40564147266ed8134a945b3152ed7b368ee54`.

## Summary

- Cancel superseded pull-request runs of CodeQL and Repository Self-Security.
- Cache pip downloads for daily operations, portfolio refresh and documentation
  refresh, keyed by their existing hash-pinned dependency lockfiles.
- Preserve every main, scheduled and manually dispatched security run.
- Preserve all check identities, scan languages, evidence uploads, retention
  and operational review publication behavior.

## Artifact intake classification

| Field | Value |
|---|---|
| Artifact type | Workflow configuration and non-normative change record |
| Target paths | Five existing files under `.github/workflows/`; this change request |
| Review owner | Repository maintainers through existing CODEOWNERS review |
| Source Document Intake required | No; no source or source register changes |
| Evidence contract / release impact | None |
| Governance impact | Execution scheduling only; no policy, enforcement or result semantics change |
| Validation | Workflow lint, structural preservation checks, pinned repository validation |

## Observed workload

The full run inventory contains 2,215 runs created from 1 October 08:55:31 UTC
through 18 October 11:42:58 UTC. All job pages were read with `filter=all`,
including earlier attempts; no response exceeded the requested 100-job page.
One cancelled CodeQL job had no runner allocation or steps; its 902 seconds
of waiting are excluded. Total observed job time is 2,211.92 minutes. The sum
rounded separately per job is 3,331 minutes, which is **not an invoice or
quota-deduction claim**.

| Workflow | Runs | Actual job minutes | Rounded job minutes |
|---|---:|---:|---:|
| Governance CI | 356 | 1,217.67 | 1,356 |
| CodeQL | 355 | 569.18 | 716 |
| Publish Docs | 78 | 106.55 | 142 |
| Consumer Lifecycle Guard | 602 | 77.92 | 299 |
| Repository Self-Security | 353 | 62.22 | 312 |
| Daily Governance Operations | 19 | 10.60 | 19 |
| Portfolio refresh | 18 | 3.73 | 18 |

The repository is **public at the time of inspection**, and its workflows use
standard Ubuntu hosted runners. Such public execution is free under
[GitHub's Actions billing rules](https://docs.github.com/en/billing/concepts/product-billing/github-actions).
Historical visibility and account billing were not available; a past private
period cannot be excluded. No monetary savings are claimed for current public
execution.

Daily operations is not the dominant workload. Eighteen scheduled reports and
one PR preview consumed only 10.60 actual minutes. Their cadence is retained.
CodeQL has 206 PR runs, 100 main pushes, 47 manual dispatches and two weekly
runs. These events have distinct review, mainline and freshness purposes.
There are no same-workflow/head-SHA push/PR matches in this inventory.

The Consumer Lifecycle Guard count includes 262 skipped `workflow_run`
executions. Those are not 262 executed runners. Its workflow-run bridge
dispatches a guard after an operational branch has passed Governance CI;
removing that bridge would weaken the existing evidence ordering.
Several daily portfolio review PRs remain open (#296–#302). Their proposals
and explicit check dispatches should be reviewed as governance work, not
silently dropped to reduce run counts. No pending PR is closed by this change.

## Exact behavior change

CodeQL and Self-Security use a concurrency group composed of workflow name,
event and PR number. Non-PR events use the unique run ID. Only PR events enable
`cancel-in-progress`. A newer run for a PR may supersede an older revision;
the current revision still needs its real successful checks.

The three pip caches contain download data only. Installation commands,
`--require-hashes`, package versions and all report/scan commands remain
unchanged. Neither security results nor governance evidence are cached.

No measured concurrency savings are claimed yet. Cache latency improvement
requires warm-cache observations and may not change rounded minutes for short
jobs. Check normal subsequent runs rather than creating artificial load.

## Protected checks and acceptance boundaries

Active ruleset `22622881`, read through the API, requires:

- `validate-and-report`
- `Analyze Python`
- `Governance Repository Security`
- `Consumer Lifecycle Guard`
- `Dependency Review`

All five identities remain unchanged. Strict required checks, CODEOWNERS,
one approving review, last-push approval and resolved review threads remain
under the existing ruleset; this change does not modify repository settings.
Classic branch-protection access returned HTTP 403, so this record does not
claim complete access to all effective settings.

The CodeQL job keeps Python and JavaScript/TypeScript analysis, including the
historical required context name `Analyze Python`. No new path filter,
draft exclusion, skip-success gate or schedule reduction is introduced.
Manual dispatches used by bot-created PRs are preserved.

Files fingerprinted by
`model/governance/lifecycle/operating-acceptance/00000001.json` are unchanged.
In particular, `governance-ci.yml`, the publication implementation, lifecycle
workflows, validation scripts and accepted records are not edited.
No source document, policy, baseline, release or accepted evidence is changed.

## Measurement and verification

Inventory endpoint: `GET /repos/joku-dev/devsecops-governance-framework/actions/runs`,
filtered by October creation date and paginated at 100. Date windows were split
until each query stayed below GitHub's filtered-result limit. Run IDs were
deduplicated. Job endpoint:
`GET /repos/joku-dev/devsecops-governance-framework/actions/runs/{run_id}/jobs?filter=all&per_page=100`.

Actual duration is summed from each non-skipped, runner-allocated job's start/end
timestamps; workflow update times, approval waits, jobs without a runner or
steps, and skipped jobs are excluded.
Rounded duration is the sum of the ceiling of each job's seconds / 60.
The public repository's run URLs and API records make these observations
reproducible; no private repository activity or personal billing export is
included in this public change record.

Validation must establish:
1. YAML and Actions expressions lint successfully.
2. Triggers, job identities, commands, permissions, artifacts and protected
   acceptance files remain unchanged except the stated cache/concurrency inputs.
3. Pinned repository/runtime validation and regression tests pass.
4. Current PR checks pass and the independent required review is obtained.

After merge, verify a normal PR update supersedes only the older PR run.
Verify the next scheduled report and CodeQL scan still run, main artifacts
remain available, and manual operational checks still complete.
Rollback is a normal revert of this PR.

## Release decision

No baseline release is required. This is a focused workflow execution change
submitted through the existing review and validation process.
