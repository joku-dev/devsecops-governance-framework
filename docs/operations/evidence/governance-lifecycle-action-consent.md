# GitHub Action Consent Validation

The personal channel test proved one explicit statement from the appointed
account. This implementation now binds each individual decision, progress update,
closure and withdrawal to its own complete request and the current pilot state.
[GCR-2026-076](../../governance/change-requests/GCR-2026-076-lifecycle-action-consent.md)
records the additive scope. Action records retain their **pilot validation**
labels. Since PRs #92/#93, effective LD-07 acceptance permits the separate
[official pilot projection](../status/governance-lifecycle-current-state.md).
Each action still needs its own personal statement and independent checks.

## Current result

The retained real GRS-002 observation is PASS. The generated action index therefore
has no finding and no action records. No personal action is requested merely to
populate a demonstration. The complete failure/action/closure sequence is covered
by injected transport fixtures in temporary test stores, separately from actual
provider captures.

- Index: `status/governance-lifecycle-pilot-actions.json`.
- Report: `generated/reports/governance-lifecycle-pilot-actions.md`.
- Immutable validation actions: `governance/lifecycle/pilot-actions/transactions/`.

## Bound requests

A request contains the exact operating-profile and role-binding digests, the
repository/GRS-002/main scope, the expected evidence and action heads, a pilot
revision, creation time, PR discussion, appointed account and action body.
The pilot revision counts retained receipts and action transactions; it protects
the complete single-resource context, including a new PASS or a rejected proposal.

| Body kind | Required role | Bound content and prerequisite |
|---|---|---|
| `decision` | `remediation_decider` | Latest eligible FAIL, plan action, appointed owner, deadline, work issue/PR URL and active predecessor |
| `progress` | `remediation_decider` | Active decision, next progress state (`in_progress`, then `completed`) and personal evidence note |
| `closure` | `closure_approver` | Active decision, latest completed progress and latest eligible PASS after the completion and all failures |
| `withdrawal` | Role of the target decision or closure | Exact target record and correction reason; valid also after closure |
| `role_withdrawal` | `role_registry_owner` | Withdrawal reason; removes effective pilot authority without rewriting the original appointment |

A work URL and progress note are personally attested references, not independently
verified issue completion or executed remediation. Actual remediation is outside
this intake command. Closure additionally requires the separately verified,
fresh GRS-002 PASS after completion. A completed issue or note alone cannot close.
Role withdrawal cannot be reversed by replaying an old approval; restoring roles
requires a separately authorized binding/profile migration.

## Prepare, personally issue, then intake

Create an action body matching `schemas/governance-lifecycle-pilot-action-request.schema.json`.
Prepare the request using an existing PR discussion number:

```bash
.venv-validation/bin/python scripts/prepare_lifecycle_pilot_action.py --body /tmp/action-body.json --discussion-number PR_NUMBER --output /tmp/action-request.json
```

The preparation command validates current prerequisites and prints the statement.
The appointed person reviews the **complete request**, then posts the printed
statement themselves in the named discussion. Codex may prepare the request but
does not issue the personal assertion. Never reuse the channel-test digest or
substitute a PR merge for the person's statement.

```bash
.venv-validation/bin/python scripts/intake_lifecycle_pilot_action.py --request /tmp/action-request.json --expected-sequence 0
.venv-validation/bin/python scripts/generate_lifecycle_pilot_actions.py
```

Use the actual current action sequence. Intake only fetches GitHub; it does not
post comments, change repository protection or execute the remediation. The
transaction embeds the complete request, raw comment captures and disposition.
A local candidate remains provisional until the required PR check independently
retrieves its personal proof and verifies the relevant active prerequisites.

For the accepted workflow path, commit the prepared request under
`model/governance/lifecycle/action-requests/` through a checked PR, then run
**Lifecycle Pilot Update**, branch `main`, operation `action`, with that path.
The request's evidence/action heads must still match at intake; if they changed,
prepare a new request and obtain a new personal statement. The workflow verifies
operating consent, appends the action proof and proposes the resulting state in
a separate publication PR. The local commands above prepare candidates only.

## Withdrawal and correction

The person may issue a new `revoke` statement for the original request digest,
referencing the original statement's latest comment ID. Intake the same request
again with the new action sequence. Withdrawal remains possible after newer
observations or a closure; it does not require a fresh approval of the old plan.
An explicit `withdrawal` request provides an alternative with its own reason.

Edited/deleted previously retained statements produce a retained
`needs_clarification` record and invalidate the affected approval. Withdrawal of
a decision or completed progress also invalidates its dependent closure. The old
closure remains in history. Later reapproval requires a new request bound to the
current state; redelivery of an old capture is a no-op and cannot restore authority.

The current projection describes the last retained captures. Provider changes are
not monitored continuously. Before granting new progress or closure, required PR
CI rechecks the active prerequisite statements. A changed or withdrawn prerequisite
blocks publication of the new grant and must be captured as a correction first.

## Acceptance and validation boundaries

The existing evidence policy applies: exact producer/profile, immutable source,
24-hour freshness and zero future skew for decision/closure evidence. Quarantined
receipts prevent grants. A newer FAIL reopens a closed validation finding; a late
older FAIL preserves a later closure. A new failure cycle needs a new decision.

Local append locks both evidence and action ledgers in a fixed order, checks the
expected sequence, and publishes atomically without overwriting. Replay validates
both complete histories and their causal receipt-head references. Required PR CI
protects existing bytes, checks new grants against the merged evidence head and
independently fetches the GitHub statements. It cannot accept injected test
transports as a new published personal proof.

The GitHub API proves account identity; personal presence remains explicitly
self-attested. Offline replay demonstrates consistency and does not authenticate
provider claims. Existing synthetic histories, released baselines, consumer
results and enforcement are unchanged.

Next: prepare the bounded operational publisher and the concrete LD-07 acceptance
packet. This implementation does not silently turn eligibility into official
lifecycle state or activate a background writer.
