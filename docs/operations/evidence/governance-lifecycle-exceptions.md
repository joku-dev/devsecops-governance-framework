# Governance Lifecycle Exceptions — CLG-05

13 September 2026. Synthetic technical continuation after #79, classified in
[GCR-2026-066](../../governance/change-requests/GCR-2026-066-governance-lifecycle-exceptions.md).
The [limited GitHub pilot acceptance](../status/governance-lifecycle-current-state.md)
excludes live waivers; this exception adapter remains synthetic. This implementation does not activate a live waiver or change a
repository rule, OPA result, released baseline or consumer's enforcement.

The exception intake binds temporary risk acceptance to explicit accepted
failing observations. Coverage, expiry and withdrawal are projected separately
from finding state, evidence result, conflict state and remediation progress.
Even full coverage leaves an unremediated finding open. Only the existing
remediation/PASS/closure approval chain can close it.

## Bounded coverage and time — ADR-CLG-005

**Context:** The current GRS-002 adapter supplies one atomic criterion for
`refs/heads/main`. It cannot identify fictional sub-resources or infer which
parts of a branch were waived. Existing waiver records contain risk, authority,
justification, compensating controls and dates, but do not bind lifecycle
revisions or prove consent.

**Decision:** Add a synthetic exception envelope around an immutable resource
validated against `schemas/waiver.schema.json`. It binds the original finding,
profile, expected revision, full waiver digest, coverage references, start and
expiry instant. Its separate approval binds that complete content, authority,
all required test subjects, disposition, time and versioned exception profile.
The caller supplies exactly the waiver and consent fixture resources.

Coverage units are **accepted failing observations in the current finding
episode**. A reference contains the observation ID and content digest. The
waiver's `object_id` must equal the finding ID, `scope` must equal
`refs/heads/main`, and `affected_requirements` must be exactly `[GRS-002]`.
This is an observation-bounded risk acceptance, not a general waiver of the
rule, resource, all future failures or the entire repository.

| Projection | Meaning |
|---|---|
| `none` | No outstanding accepted failure observation is currently covered |
| `partial` | Some outstanding observations are covered; explicit residual references remain |
| `full` | Every currently outstanding observation is covered; finding state is independent |
| `not_applicable` | No outstanding observations remain in this episode after genuine closure |

Active overlapping grants form a set union, so overlapping observations are
counted once. A new independent failure is uncovered until new consent names
it. Duplicates do not add an observation. Previous episodes are excluded using
the last closure's accepted PASS time; an old grant cannot cover a recurrence.
Quarantined input never becomes eligible coverage, and a conflict remains
`needs_clarification` even if all accepted observations have coverage.

The synthetic adapter interprets the waiver's date-only `expiry` as inclusive
through that UTC date: `expires_at` is the following midnight, **exclusive**.
For example, expiry `2026-09-13` ends at `2026-09-14T00:00:00Z`. This is an
explicit test-adapter convention, not a change to existing OPA/consumer date
semantics or an approved production timezone. `valid_from` is explicit and
cannot grant retroactive coverage. Scheduled grants are inactive before it.
The recording time cannot precede the ledger head, and consent cannot precede
the signed finding revision.

Status is derived at explicit `as_of`: `scheduled`, `active`, `expired`,
`revoked`, `rejected` or `withdrawal_recorded`. The legacy waiver's stored
`expired` boolean is an intake consistency field, not the runtime clock. An
approved immutable waiver can retain `expired: false` while the projection
correctly reports expiry. No wall-clock lookup or automatic expiry write occurs.

## Existing authority and consent boundary

`model/governance/lifecycle/synthetic-exception-profile.json` preserves an exact,
digest-bound snapshot of `model/waivers/waiver-authorities.yaml`. It records only
test subjects; it does not appoint actual people or alter the authority model.

| Explicit waiver risk | Existing authority | Required synthetic subjects |
|---|---|---|
| low / medium | DevSecOps Governance Board | `test-human:waiver-board` |
| high_cybersecurity | CISO | `test-human:ciso` |
| high_safety | Safety Authority | `test-human:safety-authority` |
| critical | CDO and CSCSO jointly | Both `test-human:cdo` and `test-human:cscso` |

Finding severity does not choose the waiver risk class. The packet explicitly
provides it. The approved authority and `approved_by` must match the profile's
exact subjects. The critical fixture contains both distinct subjects; a single
subject or duplicated subject fails. This checks fixture consistency, not two
real authenticated approvals. A remediation approver has no implied waiver
role. A bot-generated fixture, GitHub merge or `subject_type: human` assertion
cannot establish live authority.

The preserved authority snapshot has its own immutable profile reference.
Accepted-prefix validation prevents in-place profile edits after acceptance.
A future approved authority change needs a versioned migration; historical
waivers must not be reinterpreted through a silently replaced mapping.

`schemas/architecture-exception.schema.json` is intentionally not accepted by
this GRS-002 DevSecOps adapter. Its architecture targets, scope and authority
mapping need a separate domain adapter. This package neither maps architecture
risk classes by inference nor changes architecture exception enforcement.

## Withdrawal, renewal and parallel remediation

A withdrawal is a new exception record referencing an accepted approval. Its
waiver resource, covered observations and validity window must remain identical
to the grant. The same authority/subject binding must consent to withdrawal.
Scheduled or expired grants can also be withdrawn for an auditable record;
already withdrawn grants cannot be withdrawn again under a different record.
An exact accepted retry is a no-op, even after expiry, withdrawal or renewal.

Rejection records a proposal without granting coverage. It cannot be withdrawn
as if it had been approved. New approvals cannot overwrite or supersede an old
grant: renewal uses a fresh waiver ID, current finding revision and new consent.
Changed content under an accepted exception record ID is rejected.

`renewed_decision_required` is true when expired or withdrawn coverage leaves
outstanding observations uncovered by any other active grant. Renewed or
overlapping active coverage removes that specific need. Residual observations
always remain explicit, including new failures that were never covered.

Remediation may proceed concurrently. Exception events consume the shared
finding revision but do not change owner, deadline or progress of approved
work. Full coverage does not increment closure/remediation counts. A genuine
closure removes that episode's outstanding observations, and expiry thereafter
does not reopen the finding. A new failure still reopens it under CLG-04 rules.

## Storage, replay and publication boundary

New exception records use schema 0.1.0, exception events use additive event
schema 0.2.0, transactions use 0.4.0, and projections with exceptions use 0.4.0.
The earlier schemas and accepted transaction bytes are preserved. The new
`exception_recorded` event has the same digest-bound predecessor/revision
semantics as existing events. The complete chain is regenerated during replay,
including records after a historical projection's cutoff.

The demo uses a third separate synthetic ledger,
`governance/lifecycle/synthetic-exceptions/`, with generated index
`status/governance-lifecycle-exception-index.json` and Markdown report
`generated/reports/governance-lifecycle-exceptions.md`. The original conflict
and closure pilot scenarios remain unchanged. The required CI accepted-prefix
check protects all three histories and both accepted profiles.

The publisher accepts closure history and its derived reports, including the
CLG-06.1 overview. Exception history remains outside its scope: it rejects
exception transactions, even if placed under its allowed transaction directory.
There is no new live/scheduled publisher workflow. Propose the exception
scenario through an ordinary reviewed implementation/evidence PR with current
prefix and projection validation; never edit already accepted transactions.

## Reproduce the synthetic sequence

```bash
./scripts/bootstrap_validation_env.sh
.venv-validation/bin/python scripts/run_governance_lifecycle_exception_demo.py \
  --ledger /tmp/clg05-demo/ledger --output /tmp/clg05-demo/index.json \
  --report /tmp/clg05-demo/report.md
.venv-validation/bin/python scripts/generate_governance_lifecycle_exceptions.py \
  --ledger /tmp/clg05-demo/ledger --as-of 2026-09-14T00:10:00Z \
  --output /tmp/clg05-demo/rebuilt.json --report /tmp/clg05-demo/rebuilt.md
cmp /tmp/clg05-demo/index.json /tmp/clg05-demo/rebuilt.json
cmp /tmp/clg05-demo/report.md /tmp/clg05-demo/rebuilt.md
```

The empty-ledger demo creates two FAIL observations, a remediation decision and
planned work, then two grants covering one observation each. A third failure
remains uncovered; one grant is withdrawn, the other expires, and a new waiver
explicitly covers all three observations. The final index has nine transactions,
three observations, nine events, one decision, one remediation revision, four
exception records and zero closures. The finding remains open with planned work.

| Explicit checkpoint | Expected coverage |
|---|---|
| 13 September 16:00 UTC | Partial: one of two observations |
| 13 September 16:10 UTC | Full for the two known observations |
| 13 September 16:20 UTC | Partial: the new third observation remains uncovered |
| 13 September 16:30 UTC | Partial after withdrawal; original grant stays revoked |
| 14 September 00:00 UTC | None; expiry exposes renewed decision need |
| 14 September 00:10 UTC | Full after fresh consent; revoked/expired history retained |

Use the generator with each `--as-of` and separate output paths to inspect the
checkpoints. Current checked-in indexes must cover all stored transactions.
`intake_governance_lifecycle_action.py --synthetic` accepts supplied exception
packets with the existing `--record`, `--resources`, `--ledger` and
`--expected-revision` arguments. Only flat `fixture://` filenames are read.

## Acceptance and next work

Tests cover observation subset/union/residual behavior, new failures, withdrawal,
expiry boundaries, scheduled starts, critical joint authority, wrong subjects,
source contract/scope mismatch, architecture rejection, content/proof binding,
renewal, closed episodes, concurrent writers, replay, prefix protection and the
publisher boundary. Run pinned `validate_all.sh` and a strict MkDocs build.

This prepares the synthetic CLG-05 technical package. It does not complete the
separate live-waiver acceptance, add real appointments or authorize a runtime
release. CLG-06 remains a prioritization backlog for additional adapters,
reporting and viewer work; select a bounded follow-up after review rather than
implicitly enabling architecture or live waiver behavior.
