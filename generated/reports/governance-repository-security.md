# Governance Repository Self-Security Assessment

Observed: `2026-07-18T16:07:41Z`

## Decision State

- Overall status: `findings`
- Enforcement: `report_only`
- Enforcement change authorized: `false`
- Criteria: `15`
- Passed: `7`
- Failed: `8`
- Critical failures: `5`
- High failures: `3`

## Criteria

| ID | Severity | Status | Criterion | Observed |
|---|---|---|---|---|
| `GRS-001` | `critical` | `fail` | Default branch protected | `false` |
| `GRS-002` | `critical` | `fail` | Pull request and approving review required | `false` |
| `GRS-003` | `critical` | `fail` | Governance CI is a required status check | `false` |
| `GRS-004` | `critical` | `fail` | Force pushes and branch deletion blocked | `false` |
| `GRS-005` | `high` | `fail` | Signed changes required on the default branch | `false` |
| `GRS-006` | `critical` | `pass` | Secret scanning enabled | `true` |
| `GRS-007` | `critical` | `pass` | Secret push protection enabled | `true` |
| `GRS-008` | `high` | `pass` | Dependency alerts and security updates enabled | `true` |
| `GRS-009` | `high` | `pass` | Code scanning configured | `true` |
| `GRS-010` | `high` | `fail` | Third-party GitHub Actions pinned to full commit SHAs | `false` |
| `GRS-011` | `high` | `pass` | Default and explicit workflow permissions restricted | `true` |
| `GRS-012` | `high` | `pass` | Critical governance paths have explicit owners | `true` |
| `GRS-013` | `critical` | `fail` | Automation cannot push operational data directly to the default branch | `false` |
| `GRS-014` | `high` | `fail` | Governance release tags are cryptographically verified | `false` |
| `GRS-015` | `high` | `pass` | Private vulnerability reporting is enabled | `true` |

## Current Gaps

- `GRS-001`: Default branch protected
- `GRS-002`: Pull request and approving review required
- `GRS-003`: Governance CI is a required status check
- `GRS-004`: Force pushes and branch deletion blocked
- `GRS-005`: Signed changes required on the default branch
- `GRS-010`: Third-party GitHub Actions pinned to full commit SHAs
- `GRS-013`: Automation cannot push operational data directly to the default branch
- `GRS-014`: Governance release tags are cryptographically verified

## Decision Boundary

This assessment is report-only. It does not edit GitHub settings, block pull requests,
change released baselines, or authorize automated bypass. Missing evidence is reported
as a failed criterion.
