# GCR-2026-057: September operational evidence refresh

## Request and classification

The maintainer requested completion of the presentation PR, fresh consumer
evaluations and reviewed result intake, merged-branch cleanup, and clarification
of the open repository security observations on 11 September 2026.

| Field | Value |
| --- | --- |
| Artifact type | Downstream result snapshots, generated projections, operational reference record, legacy-risk gap metadata |
| Target paths | `status/`, `generated/`, `docs/operations/reference-runs/`, `model/enforcement/blocking-mode-alignment.yaml` |
| Owner | Governance Platform Lead; maintainer operational review |
| Source Document Intake required | No; these are runtime results and operational observations |
| Evidence contract impact | None |
| Runtime governance impact | Existing report-only assessment and latest-result selection retained |
| Release impact | None |
| Validation | Pinned full validation, schema checks, append-only and context checks, strict MkDocs build |

## Scope and provenance

Use the existing authenticated intake scripts to collect real GitHub Actions
runs. Preserve source commit, event, run attempt, baseline reference and artifact
digests. A manual run stays diagnostic; only an actual `main` push result updates
an available official mainline result. No historical snapshot is modified.

The private Factory is collected from the authenticated maintainer workstation
because the central workflow has no producer-read credential. Only normalized
result metadata and digests enter this public repository; application source
archives and credential values are excluded. This local intake is not represented
as a central GitHub Actions execution or counted through fabricated intake events.

Regenerate result indexes, Trust/replay and readiness projections, portfolio,
graph and viewer using repository scripts. Refresh the self-security assessment
with administrative read access to distinguish inaccessible workflow observations
from the actual settings.
Correct the report's explanatory footer: a legacy protection endpoint returning
404 does not invalidate an effective ruleset. Collection and assessment logic
remain unchanged.

Two validation assertions assumed the previous fixture state: a literal checkout
directory name and an always-present unverified latest-result badge. Check the
actual checkout name and the indexed latest Trust levels instead, retaining
explicit coverage of the viewer's projected evidence status after fresh intake.

## Decision boundaries

The new ha-CPsWMS mainline result has one failed Trust check: replay uniqueness.
That existing unresolved replay risk also fails the aggregate
`trust_checks_clean` readiness criterion. Record this additional criterion ID
alongside `replay_check_clean` so the legacy record accurately names both
projections of the same observed finding. This is an explicit amendment from
five to six recorded gap IDs. It does not clear either check, confer provenance
verification or add an approval; `acknowledged_pending_review`, the original
mode provenance and the 12 December deadline are retained. Review this metadata
amendment together with the actual snapshot before accepting the PR.

The automatic DevSecOps intake run `34602095451` failed repository validation
because the original five-ID record omitted this aggregate criterion. Preserve
that failed run as diagnostic history and retry after the reviewed amendment is
accepted. Do not disable the validator or alter the replay result to force intake.

The linked [operational reference record](../../operations/reference-runs/2026-09-11-operational-evidence-refresh.md)
records the runs, findings and remaining work. The refresh does not promote new
blocking, waive findings, change source authority, or rewrite released tags.
The existing `ha-CPsWMS` legacy-blocking review deadline remains 12 December 2026.

Self-authored PRs remain subject to the live review rules. Any separately approved
one-off administrative exception must identify its PR and restore the saved
protection immediately; this GCR grants no standing exception.
