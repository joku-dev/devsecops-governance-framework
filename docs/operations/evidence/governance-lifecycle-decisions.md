# Governance Lifecycle Decisions and Remediation — CLG-03

13 September 2026. Implements synthetic decision and remediation intake after
CLG-02 merged in PR #77. See the [implementation plan](../planning/closed-loop-governance-implementation-plan.md)
and [GCR-2026-064](../../governance/change-requests/GCR-2026-064-governance-lifecycle-decisions.md).

The intake verifies content, finding revision, role binding and supplied test
consent; it persists approvals, rejections, withdrawals and remediation progress
as immutable transactions. **All inputs and outputs remain synthetic and
report-only.** The fixture verifier checks consistency, not real human identity
or conscious consent. A bot can generate these test fixtures; doing so grants no
operational authority. Live intake remains disabled pending
[LD-01–05 and LD-07](governance-lifecycle-pilot-decisions.md).

## Bound plan and authorization — ADR-CLG-003

**Status:** implemented for the synthetic pilot.

**Context:** CLG-01 binds a decision's action text, but its remediation record
adds an owner and deadline separately. Accepting those fields from a later
writer would allow unapproved assignments or deadlines. CLG-03 must also retain
withdrawals and prevent stale progress from using withdrawn consent.

**Decision:** Add decision/remediation contracts 0.2.0. The decision includes the
entire `remediation_plan`: stable `remediation_id`, `owner_id`, `target_at`,
`action` and digest-bound `work_ref`. Its approval target is the canonical digest
of the complete record excluding `approval`. The supplied consent binds that
target, finding, expected revision, subject, role, versioned role binding,
disposition and time. The proof resource binds those approval fields. No
recorded field can be edited while preserving the same consent target.

An approval references an accepted FAIL for the same finding/profile. Intake
requires the signed expected revision to equal both the caller's revision and
the accepted finding head. Consent cannot predate that head's recording time;
recording cannot predate the global ledger head. A target date before consent
cannot be approved. These example deadlines are not organizational SLAs.

| Decision | Effect |
|---|---|
| First approval | Establishes one active authorization and a new remediation case ID |
| Replacement approval | Must reference the latest previously approved decision and use a fresh case ID; an active predecessor becomes `superseded` |
| Rejection | Records a rejected proposal; grants no authority and cannot supersede an existing approval |
| Withdrawal | Must reference the currently active approval and its unchanged observation/action/plan; predecessor becomes `revoked` |
| Exact accepted retry | No new transaction, event or revision; retrying a withdrawn approval never reactivates it |
| Reused record ID with changed content | Rejected, even with a new valid fixture proof |

A withdrawal can be recorded after the plan's deadline. Replacement after a
withdrawal still references the latest approved decision; the old case retains
its revoked history. Replacing a plan never transfers previous progress to the
new case. These semantics deliberately support one active remediation approval
per finding in the bounded pilot.

**Consequences:** Old 0.1.0 schemas, records, profile and accepted transaction
bytes remain unchanged. New actions use transaction schema 0.2.0 in the same
ordered ledger. Events keep the compatible 0.1.0 contract. Projections with
visible actions use index schema 0.2.0; historical projections before the first
action reproduce 0.1.0 exactly. No released baseline or consumer schema migrates.
The frozen CLG-02 index under `tests/fixtures/governance-lifecycle/` is historical
regression evidence, not a second current-state index.

## Remediation progress and concurrency

Every remediation revision must exactly match the approved plan and reference
its still-active decision. The first revision is `planned`, followed by
`in_progress`, then `completed`. Each update references the accepted latest
record for that case. A progress proof binds the complete record excluding its
own proof reference. This is synthetic work evidence, not verification of an
external ticket or a real actor. Changing owner, deadline, action or work
reference requires a replacement decision and a fresh case.

Actions use the same locked atomic append, full replay, finding revision and
Git accepted-prefix checks as [CLG-02](governance-lifecycle-kernel.md). A progress
update and withdrawal prepared on the same revision cannot both be accepted.
If progress wins, withdrawal must be prepared with new consent for the new
revision. If withdrawal wins, subsequent progress against that approval fails.
Already accepted progress stays in history. Replay rejects a forked merge even
when Git merges different transaction filenames without a textual conflict.

The projection separately shows active decision, decision history, latest
progress per case, authorization status and whether unfinished work is overdue
at the explicit `as_of` instant. `completed` does not close the finding. Neither
approval nor progress clears quarantined evidence or `needs_clarification`.
New accepted observations continue to advance the shared finding revision.
Closure, reopening, waiver treatment and live publication remain later packages.

## Reproduce and inspect

Use an empty ledger directory:

```bash
./scripts/bootstrap_validation_env.sh
.venv-validation/bin/python scripts/run_governance_lifecycle_action_demo.py \
  --ledger /tmp/clg03-demo/ledger --output /tmp/clg03-demo/index.json
.venv-validation/bin/python scripts/generate_governance_lifecycle_index.py \
  --ledger /tmp/clg03-demo/ledger --output /tmp/clg03-demo/rebuilt.json \
  --as-of 2026-09-13T12:10:00Z
cmp /tmp/clg03-demo/index.json /tmp/clg03-demo/rebuilt.json
```

The demo rebuilds the original five CLG-02 transactions unchanged, then appends
approval, planned remediation, in-progress remediation and withdrawal. An exact
approval retry is a no-op. The checked-in current index has **nine transactions,
four accepted observations, nine events, one conflict, two decision records,
two remediation revisions and one finding**. The case remains `in_progress`
with authorization `revoked`; no decision is active. The finding retains three
occurrences, latest PASS and `needs_clarification`, at revision nine.

A supplied 0.2.0 synthetic packet can be appended through:

```bash
.venv-validation/bin/python scripts/intake_governance_lifecycle_action.py \
  --synthetic --ledger /tmp/clg03-intake/ledger \
  --record /tmp/decision.json --resources /tmp/action-resources \
  --expected-revision 1
```

The target ledger must already contain the referenced accepted finding. Resource
files use the flat filename after `fixture://`; exactly the two referenced
resources are embedded in the transaction. The CLI rejects missing resources,
non-fixture references and symlink files. It does not obtain human consent or
publish changes. Regenerate the index with the existing generator and an
explicit `--as-of` after accepted writes. `synthetic_actions.py` only constructs
clearly labelled test packets.

## Acceptance and next work

Executable tests cover plan/content/role binding, missing proof, live and old
schema rejection, stale consent, rejected proposals, withdrawal and replacement,
retry idempotency, progress prerequisites, overdue evaluation, completion without
closure, historical replay, CLI intake and a real two-process withdrawal/progress
race. The existing competing-Git-proposal and accepted-prefix checks apply to
the complete mixed transaction history.

CLG-03 supplies the synthetic decision/remediation portion of P08 and P10; it
does not claim live human-authentication acceptance. CLG-04 follows with
closure/reopening, pilot reporting and the bounded publisher integration.
Confirm real role appointments, authenticated consent and the acceptance profile
before activating any live portion. Merge of this implementation PR is required
before the package is marked complete in the plan.
