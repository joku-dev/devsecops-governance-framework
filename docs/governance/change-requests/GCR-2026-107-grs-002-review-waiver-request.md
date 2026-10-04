# GCR-2026-107: GRS-002 Time-Bound Review Waiver Request

## Decision Status

**Approved by the CISO on 2 October 2026; CSCSO authority delegated for this
waiver on 4 October 2026; effective from 4 October through 12 December 2026.**
The delegation is limited to this waiver. Its approval accepts the time-bound
residual risk described here. It does not change GitHub protection or the
GRS-002 evaluator.

## Approved Waiver Terms

| Field | Approved value |
|---|---|
| Waiver ID | `waiver-2026-grs-002-review-count` |
| Scope | `joku-dev/devsecops-governance-framework`, `refs/heads/main` only |
| Object | GRS-002, `pull_request_review_required` |
| Affected requirement | Two independent approving reviews for changes merged to `main` |
| Approved deviation | Permit one independent approving review instead of two for in-scope pull requests |
| Risk classification | `high_cybersecurity` |
| Approval authority | CISO under `model/waivers/waiver-authorities.yaml` |
| Named approver / approval date | `joku-dev` (acting as CISO), 2 October 2026 |
| Delegation | `joku-dev` (acting as CSCSO) delegated approval authority to the CISO for this waiver only on 4 October 2026 |
| Effective date | 4 October 2026; no retroactive effect |
| Expiry | 12 December 2026, 23:59:59 Europe/Berlin (`2026-12-12T22:59:59Z`) |
| Status | `approved` |

The approval is motivated by the expected recurrence of technical changes in
the coming weeks and the operational burden and security-report noise caused by
repeatedly changing and restoring review protections. The approved exception
reduces the second-review requirement only. It does not authorize merging a
pull request without an independent approving reviewer.

## Required Compensating Controls

For the waiver period, retain all of the following:

- At least one approval from a reviewer other than the pull-request author.
- Required CODEOWNER review and approval of the latest push.
- Dismissal of stale approvals and resolution of review conversations.
- All five currently required checks: `validate-and-report`, `Analyze Python`,
  `Governance Repository Security`, `Consumer Lifecycle Guard`, and
  `Dependency Review`.
- Active protection against branch deletion and non-fast-forward updates.
- No bypass actors and no change to other repository or consumer protections.
- Review of this waiver before expiry; revoke it earlier if any compensating
  control becomes unavailable or the risk changes.

## Scope Boundary And Current State

The live GitHub ruleset currently requires one approving review plus CODEOWNER,
last-push, conversation-resolution and CI requirements. It has no bypass actors.
The repository's GRS-002 target is two independent approvals, so this waiver
accepts the gap between that target and the current one-approval rule for a
limited period. It does not disable the current one-review minimum or the other
live rules.

Accordingly, PRs with no independent approval remain outside this request. The
temporary zero-approval configuration used during earlier merge exceptions is
not covered here. The request does not apply to `ha-CPsWMS`, other repositories,
other controls, personal lifecycle decisions, or any released baseline.

GRS-002 findings must continue to reflect the observed configuration. This
waiver records accepted residual risk; it must not rewrite a `FAIL` observation
as `PASS` or close a lifecycle finding by itself. The current
manual report-only lifecycle pilot does not implement live waiver intake; adding
such integration would require a separate reviewed, versioned change.

## Approval Record

On 2 October 2026, `joku-dev` approved this waiver in the role of CISO. On
4 October 2026, `joku-dev`, acting as CSCSO, delegated approval authority to the
CISO for this waiver only. The decision has no retroactive effect and is
effective from 4 October 2026. The risk class is `high_cybersecurity`; the
approval authority is CISO under this scoped delegation. Its corresponding
waiver record is `model/waivers/waiver-2026-grs-002-review-count.yaml`. This
document preserves the rationale and decision history.

## Artifact Intake Classification

| Field | Value |
|---|---|
| Artifact | Approved time-bound GRS-002 waiver |
| Artifact type | Governance waiver and change record |
| Target path | `docs/governance/change-requests/GCR-2026-107-grs-002-review-waiver-request.md` |
| Owner | Repository Owner / Governance Platform Lead |
| Source Document Intake required? | No; no source document is added or changed |
| Evidence contract impact | None |
| Runtime governance impact | Accepted residual risk is recorded; the GRS-002 evaluator remains unchanged |
| Release impact | None |
| Validation required | Documentation and repository validation before any merge |

## Decision And Validation Boundary

No GitHub ruleset, policy, evaluator, lifecycle acceptance, or status index is
changed by this approval. The live ruleset already requires one independent
review and the listed compensating controls. The waiver records acceptance of
the residual risk from the second-review gap; it does not make GRS-002 findings
pass or close a lifecycle finding. The current manual report-only lifecycle
pilot does not implement live-waiver intake, so that integration would require
a separate reviewed, versioned change. Repository validation is required for
this record update before merge.
