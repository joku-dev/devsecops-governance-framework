# Personal GitHub Channel Probe

The confirmed pilot channel now has a read-only verifier and a concrete request
for `joku-dev` (`github-user:81616324`). The first real GET check on
13 September 2026 returned `waiting_for_personal_statement`.
[GCR-2026-074](../../governance/change-requests/GCR-2026-074-lifecycle-personal-channel-probe.md)
classifies this bounded implementation.

## Personal step

Open [PR #87](https://github.com/joku-dev/devsecops-governance-framework/pull/87)
and personally post the entire text from the
[generated statement](https://github.com/joku-dev/devsecops-governance-framework/blob/main/generated/reports/lifecycle-personal-channel-statement.md)
as a new ordinary comment under `joku-dev`. This is possible on the merged PR;
no self-approval of a PR review is required.

The request binds the confirmed role assignment and operating profile to the
first durable receipt head. Its digest also binds its challenge, purpose and
creation time. The statement tests only the personal channel. Even `confirmed`
authorizes no remediation, closure, role change or live activation. Codex may
prepare this text but cannot issue its personal self-attestation for the person.

Do not edit or delete an issued statement. A subsequent statement uses the same
request digest and personal assertion, sets `disposition` to `reject` or `revoke`,
and references the previous statement's numeric GitHub comment ID in
`supersedes_comment_id`. Revocation requires an active confirmation. A later
explicit `approve` can confirm again by referencing that predecessor.

## Capture and recheck

Run from the repository root with authenticated read access to GitHub:

```bash
.venv-validation/bin/python scripts/check_lifecycle_personal_channel.py --output generated/reports/lifecycle-personal-channel/001.json
.venv-validation/bin/python scripts/check_lifecycle_personal_channel.py --replay generated/reports/lifecycle-personal-channel/001.json
.venv-validation/bin/python scripts/check_lifecycle_personal_channel.py --previous-capture generated/reports/lifecycle-personal-channel/001.json --output generated/reports/lifecycle-personal-channel/002.json
```

Retain every capture and always pass the latest one to a recheck. The command
carries earlier statement identities forward, so deletion or alteration remains
visible across subsequent captures. Without a prior capture, the provider cannot
prove that a previously issued comment was deleted. Captures cannot be overwritten.
These diagnostic files are not an accepted consent ledger; publishing the first
actual result requires a focused change with validation and provider recheck.

The verifier fetches all supported comment pages twice and rejects a changing
snapshot. It checks stable account ID, user type, absence of a reported GitHub app,
request digest, discussion, timestamps, unedited content and explicit predecessor
references. Known bots/apps cannot confirm. Invalid statements or changed/deleted
previous statements produce `needs_clarification`. Unrelated comments do not
supply consent. The request must still reference the current durable receipt head
when a fresh provider capture is made. Historical requests remain immutable and
validatable after a newer receipt is added.

## Trust and remaining acceptance

GitHub authenticates an account. It does not attest physical human presence or
whether a personal token was used by automation. The result therefore records
`human_presence: explicitly_self_attested_not_provider_attested`; identity alone
is insufficient. Offline replay verifies consistency of retained bytes and the
projection, not their independent provider authenticity.

The ten targeted tests cover valid confirmation, wrong account/app/bot, missing
personal assertion, changed digest, edited or misplaced comments, chronology,
rejection/revocation/reconfirmation, deleted history and provider metadata races.
The real positive channel test still requires the person's comment. Subsequent
work must integrate retained consent evidence with action-specific decision and
closure revisions, role withdrawal and the live acceptance flow. A channel probe
cannot substitute for that implementation or the separate LD-07 operating
acceptance. The [decision brief](governance-lifecycle-live-decision-brief.md)
remains the entry point for the outstanding live prerequisites.
