# CLG-04 Synthetic Lifecycle Pilot

As of: `2026-09-13T14:20:00Z`

Environment: **synthetic**. Enforcement: **report-only**. Official state: **false**.
Live pilot acceptance: **pending LD-01–05 and LD-07**. Fixture consent does not authenticate a human.

Transactions: 9; observations: 4; events: 9; closures: 1; conflicts: 0.

| Finding | State | Evidence | Revision | Occurrences | Closures | Reopenings |
|---|---|---|---|---|---|---|
| `finding:7d4c5c5222557d3cad04d4e1e5ebb5a1015cb394f7862b14a8e257bfcc85b26a` | open | fail | 9 | 3 | 1 | 1 |

## Immutable event history

The index references the accepted ledger head and each closure. Replay retains completed closure history after reopening; a late older failure does not undo closure.

This separate pilot does not resolve the original CLG-02/03 conflict, change consumer results or activate live intake.
