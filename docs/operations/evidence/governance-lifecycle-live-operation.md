# GRS-002 GitHub Pilot: Operating Acceptance and Runbook

Status: **prepared, inactive until personal LD-07 acceptance**.
The technical review exception permits implementation merges. It does not provide
operating acceptance or individual remediation/closure consent.
[GCR-2026-077](../../governance/change-requests/GCR-2026-077-lifecycle-operating-acceptance.md)
classifies this bounded operating path.

## Concrete decision proposed to the maintainer

Accept the first repository-local pilot for `joku-dev/devsecops-governance-framework`,
GRS-002 `pull_request_review_required`, resource `refs/heads/main`, report-only.
The named maintainer `joku-dev` personally decides this LD-07 request. The earlier
role appointment and channel test do not constitute that decision.

Approval permits manually triggered intake of verified observations, individual
personal action statements, and publication of the separate pilot state through
an allowlisted PR. It explicitly permits using the retained eligibility history
as the source for that pilot projection. Original receipts retain their diagnostic
labels and bytes; the operational view records its acceptance and promotion basis.

Approval does not permit automatic remediation, blocking on findings, direct
writes to main, waiver authority, baseline changes, other consumers or Bitbucket
operation. Every decision, progress update and closure still requires its own
personal, content-bound statement and successful evidence/state checks.

The operating request binds the exact implementation and this runbook by file
digests. A changed fingerprint disables effective operation until a new versioned
acceptance is prepared. Technical maintenance never erases accepted history.

## Evidence available for acceptance

- Roles and pilot operating values are confirmed in separate immutable records.
- Real GitHub channel proof: comment `5653982008` on PR #87, retained with original
  CRLF bytes and independently rechecked by required CI in PR #89.
- Durable provider receipt: real GRS-002 PASS, no fabricated finding or action.
- Action validation: exact role/content/state binding, decision and progress,
  evidence-bound closure, rejection, post-closure withdrawal, late observations,
  newer failure/reopening, competing append and independent prerequisite recheck.
- Failure/action/closure sequences are injected test fixtures. They demonstrate
  behavior and do not claim a real person closed a real production finding.
- Publisher checks: narrow paths, immutable history, acceptance gate, provider
  recheck and PR-only publication. The manual workflow never posts personal consent.

The first effective run on the live GitHub workflow follows personal acceptance.
Local and PR CI checks cannot claim that this post-acceptance run already occurred.

## Personal acceptance

Review this runbook and
`model/governance/lifecycle/operating-acceptance/00000001.json`. Personally post the
complete generated statement from
`generated/reports/lifecycle-operating-acceptance-statement.md` on PR #91.
It uses a different request digest from the channel test and every action request.
The agent may prepare the statement but does not issue its personal assertion.

After the comment exists, run **Lifecycle Pilot Update**, branch `main`, operation
`acceptance`. This captures the statement and prepares a PR. Required PR CI
independently checks the provider proof. Effective pilot state is published only
when that PR is merged under the applicable technical merge rules.

## Manual operations after acceptance

| Operation | Input | Result |
|---|---|---|
| `observe` | Completed permitted Self-Security mainline run ID, attempt 1 | Fresh verified receipt, replay/quarantine handling and regenerated pilot state |
| `action` | Committed JSON under `model/governance/lifecycle/action-requests/` | Fresh personal proof for the exact request; atomic action receipt and regenerated state |
| `acceptance` | No extra input | Capture or recheck the current operating acceptance, including withdrawal/deletion |
| `refresh` | No extra input | Recheck operating consent and regenerate existing state without a fabricated observation |

Every operation produces only allowlisted evidence and projections on an
automation branch. Required checks and a PR merge remain necessary. A concurrency
group serializes workflow preparations; accepted-prefix and complete replay checks
handle competing PRs. Reconcile a stale branch against current main and regenerate;
never force-push over accepted history.

Freshness remains 24 hours with zero future skew for new observation intake and
decision/closure evidence. An old retained PASS is historical evidence, not a fresh
attestation. A newer actual FAIL opens/reopens a finding; no FAIL is manufactured
to demonstrate the flow. New personal action grants are independently checked
against their active prerequisite statements before publication.

## Withdrawal, correction and rollback

Personally post a new `revoke` statement for the operating request, referencing
the latest statement's numeric comment ID. Run operation `acceptance` again and
merge its correction PR. The resulting live view becomes inactive. Provider
rechecks already prevent new operational proposals from relying on the withdrawn
statement while the correction PR is pending. Edited/deleted retained statements
also remove effective acceptance and require clarification.

For a decision or closure correction, use the action withdrawal flow in the
[action-consent guide](governance-lifecycle-action-consent.md). Withdrawal of a
decision or completed progress invalidates its dependent closure; old records stay
available. Role withdrawal removes effective pilot authority and permits publishing
the permission-reducing correction. It does not silently appoint a replacement.

The workflow has no schedule and does not monitor provider changes continuously.
Before any new operational proposal it rechecks operating acceptance; before new
action grants it rechecks the action prerequisites. A maintainer can stop all
further runs by disabling the workflow while preserving the evidence and filing a
bound withdrawal. No automatic deletion is configured. At pilot completion, the
maintainer reviews retention as already agreed.

## Separate views

`status/governance-lifecycle-live.json` and
`generated/reports/governance-lifecycle-live.md` describe this pilot only. The
original eligibility/action indexes, synthetic histories, ha-CPsWMS results,
released baselines and consumer enforcement retain their existing meaning.
