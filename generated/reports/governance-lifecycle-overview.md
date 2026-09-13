# CLG-06.1 Synthetic Lifecycle Overview

As of: `2026-09-14T00:10:00Z`

Environment: **synthetic**; **report-only**; official state: **false**.
These are separate test histories sharing a finding identity, not three portfolio repositories.
No cross-scenario totals or production performance claims are calculated.
Live acceptance remains pending LD-01–05 and LD-07; fixture consent is not authenticated human approval.

| Scenario | Open | Closed | Clarification | Accepted FAIL / PASS | Quarantines | Closure events | Reopen events |
|---|---:|---:|---:|---:|---:|---:|---:|
| synthetic | 0 | 0 | 1 | 3 / 1 | 1 | 0 | 0 |
| synthetic-closure | 1 | 0 | 0 | 3 / 1 | 0 | 1 | 1 |
| synthetic-exceptions | 1 | 0 | 0 | 3 / 0 | 0 | 0 | 0 |

Historical closure events remain counted after reopening. PASS, completed work and waiver coverage do not themselves close findings.

| Scenario | Work cases: planned / in progress / completed | Overdue cases | Coverage by finding | Renewed decision needed |
|---|---|---:|---|---:|
| synthetic | 0 / 1 / 0 | 0 | not_evaluated: 1 | 0 |
| synthetic-closure | 0 / 0 / 1 | 0 | not_evaluated: 1 | 0 |
| synthetic-exceptions | 1 / 0 / 0 | 0 | full: 1 | 0 |

Work counts include retained cases with withdrawn authorization; each case's authorization is visible in the JSON projection.
Coverage concerns explicit accepted failing observations. `not_evaluated` means this projection has no exception treatment dimension.
Expiry and overdue status are evaluated at `as_of`; they do not invent ledger events.

## synthetic

Ledger: `governance/lifecycle/synthetic`
Evaluated head: `transaction:04b2daf556f0a9fd472aeb44e22b0fb73b5f9d8fca4593e142588299b774efab`

| Revision | Event | Recorded at | Effective at |
|---:|---|---|---|
| 1 | finding_opened | 2026-09-13T10:00:00Z | 2026-09-13T10:00:00Z |
| 2 | observation_added | 2026-09-13T10:10:00Z | 2026-09-13T10:10:00Z |
| 3 | observation_added | 2026-09-13T11:00:00Z | 2026-09-13T11:00:00Z |
| 4 | observation_added | 2026-09-13T11:10:00Z | 2026-09-13T10:05:00Z |
| 5 | clarification_required | 2026-09-13T11:20:00Z | 2026-09-13T11:00:00Z |
| 6 | decision_recorded | 2026-09-13T11:40:00Z | 2026-09-13T11:40:00Z |
| 7 | remediation_recorded | 2026-09-13T11:50:00Z | 2026-09-13T11:50:00Z |
| 8 | remediation_recorded | 2026-09-13T12:00:00Z | 2026-09-13T12:00:00Z |
| 9 | decision_recorded | 2026-09-13T12:10:00Z | 2026-09-13T12:10:00Z |

The JSON overview binds each event to its immutable event and transaction digests and embeds the verified finding projection.

## synthetic-closure

Ledger: `governance/lifecycle/synthetic-closure`
Evaluated head: `transaction:b66f44dec649cc8710e31797838a1ace8734439c69c12f6e7682026157c33d8a`

| Revision | Event | Recorded at | Effective at |
|---:|---|---|---|
| 1 | finding_opened | 2026-09-13T13:00:00Z | 2026-09-13T13:00:00Z |
| 2 | decision_recorded | 2026-09-13T13:10:00Z | 2026-09-13T13:10:00Z |
| 3 | remediation_recorded | 2026-09-13T13:20:00Z | 2026-09-13T13:20:00Z |
| 4 | remediation_recorded | 2026-09-13T13:30:00Z | 2026-09-13T13:30:00Z |
| 5 | remediation_recorded | 2026-09-13T13:40:00Z | 2026-09-13T13:40:00Z |
| 6 | observation_added | 2026-09-13T13:50:00Z | 2026-09-13T13:50:00Z |
| 7 | finding_closed | 2026-09-13T14:00:00Z | 2026-09-13T14:00:00Z |
| 8 | observation_added | 2026-09-13T14:10:00Z | 2026-09-13T13:05:00Z |
| 9 | finding_reopened | 2026-09-13T14:20:00Z | 2026-09-13T14:20:00Z |

The JSON overview binds each event to its immutable event and transaction digests and embeds the verified finding projection.

## synthetic-exceptions

Ledger: `governance/lifecycle/synthetic-exceptions`
Evaluated head: `transaction:402749bbe4008ea7f935d5b385e650510858fb28e48fc491b7f4545f92211373`

| Revision | Event | Recorded at | Effective at |
|---:|---|---|---|
| 1 | finding_opened | 2026-09-13T15:00:00Z | 2026-09-13T15:00:00Z |
| 2 | observation_added | 2026-09-13T15:10:00Z | 2026-09-13T15:10:00Z |
| 3 | decision_recorded | 2026-09-13T15:20:00Z | 2026-09-13T15:20:00Z |
| 4 | remediation_recorded | 2026-09-13T15:30:00Z | 2026-09-13T15:30:00Z |
| 5 | exception_recorded | 2026-09-13T16:00:00Z | 2026-09-13T16:00:00Z |
| 6 | exception_recorded | 2026-09-13T16:10:00Z | 2026-09-13T16:10:00Z |
| 7 | observation_added | 2026-09-13T16:20:00Z | 2026-09-13T16:20:00Z |
| 8 | exception_recorded | 2026-09-13T16:30:00Z | 2026-09-13T16:30:00Z |
| 9 | exception_recorded | 2026-09-14T00:10:00Z | 2026-09-14T00:10:00Z |

The JSON overview binds each event to its immutable event and transaction digests and embeds the verified finding projection.
