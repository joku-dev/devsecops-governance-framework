# Governance Lifecycle Kernel — CLG-02

13 September 2026. Implements the synthetic finding/event package from the
[closed-loop plan](../planning/closed-loop-governance-implementation-plan.md),
using the [CLG-01 record contracts](governance-lifecycle-contract.md).
Change: [GCR-2026-063](../../governance/change-requests/GCR-2026-063-governance-lifecycle-kernel.md).

The kernel persists accepted **synthetic** observations and derived events,
quarantines conflicting packets, and rebuilds one finding index from immutable
transactions. It does not accept live evidence, human decisions, remediation,
closure or waivers. A PASS updates the latest evidence result; the finding stays
open until a later package implements the complete approved closure chain.

## Storage and identity

| Artifact | Location and meaning |
|---|---|
| Immutable synthetic history | `governance/lifecycle/synthetic/transactions/` |
| Current synthetic projection | `status/governance-lifecycle-synthetic-index.json` |
| Test profile | `model/governance/lifecycle/synthetic-grs002-profile.json`; remains disabled for live use |
| Transaction/index contracts | `schemas/governance-lifecycle-{transaction,index}.schema.json`, version 0.1.0 |
| Core and adapter | `scripts/lib/governance_lifecycle/{adapter,kernel,store}.py` |
| Deliberately fabricated packets | `scripts/lib/governance_lifecycle/synthetic.py`; test/demo use only |

These concrete paths refine the planning proposals. The synthetic index has
`environment: synthetic`, `official_state: false` and `enforcement: report_only`.
It is not connected to the existing consumer indexes or viewer. No official
`status/governance-lifecycle-index.json` or live lifecycle store is introduced.

Each file contains one complete transaction: profile reference, sequence,
previous transaction digest, expected finding revision, observation, its raw
snapshot and acceptance proof (base64-encoded bytes), outcome/reason and optional
event. Encoding preserves exact snapshot/proof bytes. Snapshot and proof are
resolved only within their containing transaction, so identical resource names
in different packets cannot silently replace earlier resources.

The transaction ID hashes every field except `transaction_id`, using the
CLG-01 canonical serialization. Its filename binds sequence and ID. References
to prior transactions hash their complete contents, including the ID. Event
IDs similarly hash the event excluding its own `record_id`. All event records
still satisfy the unchanged CLG-01 schema. Replay regenerates every transaction
and event from the preceding state and requires exact equality.

A single global sequence serializes this small pilot. A finding has its own
event revision. PASS observations before the first FAIL are retained without
creating a finding or consuming a finding revision. The first accepted FAIL
creates `finding_opened`; subsequent accepted observations create
`observation_added`. Conflicts on an existing finding create
`clarification_required`. No arbitrary event or decision record can be appended
through the observation intake API.

## GRS-002 adapter boundary

The adapter consumes the existing self-security report schema 0.2.0, exact raw
bytes, a separate source context, supplied synthetic Trust assertions, recorded
time and policy version. It requires exactly one GRS-002 criterion and the
expected key. It preserves the repository, observation time, security profile
version and individual criterion result; the report's overall summary is not a
substitute for the criterion.

Only repository `synthetic/governance-lifecycle`, context `test`, the allowed
synthetic producer and an explicitly synthetic report are supported. The raw
report digest/size, subject, source context and producer must match the supplied
Trust record. The adapter constructs a bound **synthetic** acceptance statement
and runs the CLG-01 test-profile checks. It does not authenticate a provider,
fetch real run metadata, verify a human or manufacture operational provenance.

`synthetic.py` deliberately fabricates all test evidence from the existing
CLG-01 fixtures, including passing Trust assertions. It is isolated from the
adapter and clearly named for that purpose. Live activation needs a reviewed
profile and verifiers after the open decisions in the
[pilot decision sheet](governance-lifecycle-pilot-decisions.md) are confirmed.

## Delivery, conflict and ordering rules

The delivery identity is the CLG-01 finding/source-context digest. Producer
content includes snapshot digest, observation time, criterion/result and
source/profile/policy versions. Receipt time and the local acceptance statement
are not producer content.

| Input | Stored outcome |
|---|---|
| Same delivery, producer content and Trust assertions | Duplicate: return success without changing files, events, revisions or occurrences; retain the first acceptance proof |
| New independent matching-context failure | Accepted observation on the existing finding; increment occurrence count once |
| Same delivery, changed producer content | Quarantined as `producer_conflict`; original observation remains intact |
| Same producer payload, changed Trust assessment | Quarantined as `reassessment_required`; retain the proposed assessment with its own provenance |
| Incompatible source/profile/policy version | Quarantined as `incompatible_version`; no inferred version compatibility |
| Different results with equal observation time | Quarantined as `ambiguous_time`; no arrival-time tie breaker for contradictory evidence |
| Identical repeated quarantined packet | No second quarantine transaction or clarification event |
| Invalid schema, missing resource, wrong context or stale revision | Reject before publication with an error; caller must address the failure |

Quarantined packets are retained inside immutable transactions but do not enter
the accepted observation map or occurrence count. Their transaction references
appear in the index even if no finding has yet opened. An existing finding
becomes `needs_clarification`; later PASS does not clear that condition. Conflict
resolution is intentionally not invented in this package.

The latest evidence is selected by **observation time**, with record ID as a
stable tie breaker only where results are consistent. A delayed older FAIL
contributes to history and occurrence count but cannot replace newer PASS
coverage. A genuinely newer FAIL becomes the latest evidence. Neither is called
“reopening” in CLG-02 because operational closure is not yet implemented.

`recorded_at` must be nondecreasing across published transactions, and the
contract requires observation/verification/acceptance times to be consistent.
The `as_of` projection includes only transactions recorded by that instant,
while still verifying the entire stored chain. It never consults the current
clock. The current checked-in index must cover the latest transaction;
historical projections can be exported to a separate file.

## Atomic append and local concurrency

The supported storage boundary is a **single local POSIX filesystem** with
advisory `flock` and atomic hard-link creation. It is not a distributed database,
a network-filesystem locking protocol or a power-loss recovery certification.
All local writers must use the supplied append API.

An append holds an exclusive `.append.lock`, rereads and validates the accepted
chain, classifies the packet and compares its expected finding revision with
the current revision. Identical retries may return a no-op even with the
original expected revision. New writes with stale revisions fail.

The writer serializes the whole transaction into a private `.pending-*` file,
flushes and fsyncs it, then publishes it with an exclusive atomic hard link and
fsyncs the directory. It never overwrites a published file. A crash before
publication leaves at most an ignored pending file; a retry after publication
finds the already accepted delivery and does not duplicate it. Lock and pending
files are ignored by Git and never treated as accepted history. Symlink entries
and unexpected files are rejected.

Tests exercise two actual spawned processes competing for revision zero,
failure before publication, error after publication, partial unpublished bytes
and retry idempotency. Plain replay cannot detect a deleted *tail* without a
trusted prior head. Git prefix validation below supplies that comparison for
tracked accepted history; the file store is not a tamper-proof storage service.

## Git acceptance and competing PRs — ADR-CLG-002

**Status:** implemented for synthetic history. This resolves the technical
CLG-02 portion of LD-06; live deployment remains a separate decision.

**Context:** A filesystem lock does not coordinate two Git clones. Two PRs can
both pass branch checks while each proposes the next event from the same base.
Git may cleanly merge their distinct transaction filenames even though both
claim the same sequence and finding revision.

**Decision:** Validate both the full merged transaction chain and the immutable
accepted prefix in the existing required `validate-and-report` job. Checkout
fetches history; PR validation uses the GitHub event's immutable base SHA, and
push validation uses its before SHA. Every accepted transaction blob must still
exist with unchanged bytes. The accepted profile cannot be edited in place;
future profile changes require an explicit versioned migration.

The current repository rules require `validate-and-report` and up-to-date
branches. The PR checkout is GitHub's proposed merge tree. After one competing
PR merges, the second must incorporate the new base and pass again. Its merged
union fails chain/revision validation. It must remove its own unaccepted
proposal, reprepare against the accepted head and regenerate the index. Deleting
or editing the already accepted competitor to force a clean replay is rejected
by the prefix check. A unit test performs this clean Git merge and verifies both
the rejection and the correctly reprepared result.

**Consequences and assumptions:** This is semantic merge validation, not a new
permission system. It relies on the existing required-check and strict-update
rules being enforced, and on review of changes to the validator/workflow itself.
A successful check is not independent human approval. Admin bypass, disabling
required checks or directly rewriting trusted Git history defeats that boundary.
No repository settings or approval requirements are changed by this PR.
A future protected publisher or merge queue must preserve the same accepted-head
check; live production acceptance is not inferred from this synthetic pilot.

## Reproduce the demo

Use an empty directory; the demo refuses to reset existing history:

```bash
./scripts/bootstrap_validation_env.sh
.venv-validation/bin/python scripts/run_governance_lifecycle_synthetic_demo.py \
  --ledger /tmp/clg02-demo/ledger --output /tmp/clg02-demo/index.json
.venv-validation/bin/python scripts/generate_governance_lifecycle_index.py \
  --ledger /tmp/clg02-demo/ledger --output /tmp/clg02-demo/rebuilt.json \
  --as-of 2026-09-13T11:30:00Z
cmp /tmp/clg02-demo/index.json /tmp/clg02-demo/rebuilt.json
```

The deterministic seven deliveries produce **five transactions, four accepted
observations, five events, one quarantined conflict and one finding**. The
finding has three occurrences, revision five, latest evidence PASS and state
`needs_clarification`. Two duplicate deliveries create no records. The late
FAIL does not replace the newer PASS. This deliberately unresolved synthetic
finding is not a finding against the actual governance repository.

To append a supplied synthetic packet, use
`scripts/intake_governance_lifecycle_observation.py --synthetic --ledger ...`
with `--report`, `--context`, `--trust`, `--recorded-at`, `--policy-version` and
`--expected-revision`. These inputs are mandatory; the CLI does not derive
missing provenance or time from the current environment. Run `--help` for the
full interface. It does not publish to GitHub or update an index automatically.

Validate checked-in state and accepted history:

```bash
.venv-validation/bin/python scripts/validate_governance_lifecycle_ledger.py
.venv-validation/bin/python scripts/validate_governance_lifecycle_ledger.py \
  --base-ref <full-accepted-base-commit-sha>
./scripts/validate_all.sh
.venv-docs/bin/mkdocs build --strict
```

The base parameter is a concrete trusted Git commit, not a mutable branch name.
The normal repository validator verifies ledger/index equality; the CI step
adds the accepted-prefix check. Tests rebuild the demo into a temporary directory
and compare both transactions and index with the committed generated artifacts.

## Acceptance achieved and next package

CLG-02 now exercises durable duplicate handling, independent occurrence counts,
quarantine, revision conflicts, atomic publication, competing Git proposals,
late observation ordering and deterministic replay. P02, P03 and the observation
portion of P10 have executable persistence tests. P04/P05 cover ordering and
latest-evidence selection, not post-closure reopening.

CLG-03 is next: intake of content-bound human decisions, role/consent verification
and remediation assignment. CLG-04 supplies operational closure/reopening and
live pilot acceptance; CLG-05 supplies exceptions. None of those authorities or
transitions is implied by the synthetic index.
