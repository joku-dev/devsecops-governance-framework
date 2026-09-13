# Governance Lifecycle Closure and Reopening — CLG-04

13 September 2026. Technical synthetic implementation following PR #78.
See [GCR-2026-065](../../governance/change-requests/GCR-2026-065-governance-lifecycle-closure.md)
and the [pilot runbook](../../demos/demo-governance-lifecycle-pilot.md).
**Live activation and accountable operational acceptance remain pending.**

The kernel accepts a closure only after the accepted history proves the complete
synthetic chain. An accepted closure emits `finding_closed`. A genuinely newer
accepted failure emits `finding_reopened` for the same finding and retains the
original closure. A replay of the old closure is an idempotent no-op and cannot
close a reopened finding.

## Closure acceptance — ADR-CLG-004

**Decision:** Introduce an additive synthetic closure record 0.2.0, closure
transaction 0.3.0 and closure-aware index 0.3.0. Existing observation, action and
event contracts retain their versions. Old projections are unchanged before
the first closure appears. All record references remain digest-bound.

Closure accepts only the `remediated` reason and approval disposition `approve`.
Its approval must come from the fixed synthetic `closure_approver` binding and
bind the complete closure, finding, revision, role, subject and time. Fixture
consistency is not authentication of a real human or conscious consent.
Rejection, claimed revocation, old-contract and live closure packets cannot
create a closure. Post-closure withdrawal/correction is not an implemented
transition; do not rewrite a closure to simulate one. Live activation must
resolve that operating procedure in the accountable acceptance review.

| Required check | Acceptance rule |
|---|---|
| Finding head | Caller revision, signed revision and accepted head agree; finding is open and has no quarantined conflict |
| Time | `as_of` equals closure recording time; recording is no earlier than the ledger head; consent is no earlier than the finding head and no later than recording |
| Remediation | Exact latest revision of the case, `completed`, with the still-active approved decision |
| Decision | Same finding/profile, bound original failing observation and action; after reopening, a new decision is required |
| Evidence | Latest accepted observation is criterion-level PASS in the same scope, with exact compatible schema/profile/policy versions |
| Causality | Remediation follows every accepted failure; PASS follows remediation and every accepted failure; evidence precedes closure consent |
| Trust | All nine synthetic profile checks, accepted context and source bindings, fixture integrity and explicit 24-hour freshness bound |
| Resources | Caller supplies only the closure consent proof; referenced work, observations and proofs are taken from accepted history |

An arbitrary completed ticket, overall PASS, supplied replacement snapshot or
changed consent field cannot satisfy these checks. The checker verifies the
whole ledger, including transactions after an `as_of` projection cutoff. A
historical projection therefore cannot hide a corrupt later transaction.

**Closed-state behavior:** New decision/remediation writes are rejected while
the finding is closed; exact already-accepted retries remain no-ops. A later
accepted FAIL whose observation time is newer than the closure's PASS reopens
it. Older FAILs remain historical occurrences without undoing closure. A
conflict after closure becomes `needs_clarification`, suppresses the projected
active closure and retains closure history. Conflict resolution is still an
explicit future operation; PASS never silently resolves a quarantine.

**Reclosure:** A new remediation decision, fresh case and completed work after
the new failure, newer accepted PASS and new closure consent can close a reopened
finding. Prior closures and the reopening count remain visible. Tests exercise
two complete cycles and prevent reusing old completed work.

## History and scenario separation

The original nine CLG-02/03 transactions in
`governance/lifecycle/synthetic/` and their current index remain unchanged.
They intentionally contain an unresolved conflict and withdrawn remediation
approval. A separate `governance/lifecycle/synthetic-closure/` scenario uses the
same immutable test profile to exercise successful closure without pretending
that the original conflict was resolved. These are separate test ledgers, not
two official sources of finding state.

The new index is `status/governance-lifecycle-closure-index.json`; the small
Markdown report is `generated/reports/governance-lifecycle-pilot.md`. Both are
generated from the second ledger at an explicit instant. The JSON index adds
closure references, an active closure reference and reopening count. Closure
history remains visible after reopening. No consumer index or viewer consumes
this synthetic output.

Accepted-prefix validation protects both ledger namespaces and the shared
profile. Local writers use the existing atomic publication and POSIX lock.
Closure and new-failure requests competing for one revision cannot both append;
merged Git branches are revalidated as one ordered chain. Required CI checks
and up-to-date branch protection remain deployment assumptions, not independent
human approval.

## Bounded publication

`publish_operational_update.py --scope lifecycle-synthetic` permits only:

- new files in `governance/lifecycle/synthetic-closure/transactions/`;
- `status/governance-lifecycle-closure-index.json`;
- `generated/reports/governance-lifecycle-pilot.md`.

The publisher rejects modifications/deletions of accepted evidence, changes to
the profile, scripts, original scenario or consumer indexes, and symlink paths.
After fetching main it checks ancestry, the accepted prefix, complete replay,
current index and report equality before creating its branch or pushing.
Publication produces an `automation/lifecycle-synthetic/<run>-<attempt>` review
PR and dispatches the existing required workflows. It never approves, merges,
changes main or authenticates fixture consent. If main advances during this
process, the existing merged-chain/strict CI check still governs acceptance.

No new scheduled or live intake workflow is enabled. The existing CLI requires
protected-main workflow context. The new scope is tested against a local bare
Git remote with a fake API, so its tests do not create external PRs.

## Release and acceptance boundary

This package changes only the synthetic pilot. It does not mutate a released
baseline, change consumer contracts or justify a runtime release. CLG-04's
technical preparation is reviewable; package completion still needs its PR
merge and the documented accountable acceptance for any live portion. LD-01–05
and LD-07 remain open. Confirm role appointments, authenticated consent, Trust
sources, freshness/replay limits and withdrawal handling before live use.
CLG-05 waiver integration remains a subsequent package.
