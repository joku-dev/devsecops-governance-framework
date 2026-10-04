# Governance Repository Self-Security Assessment

Observed: `2026-10-04T10:41:21Z`

## Executive Assessment

2 of 16 self-security criteria are not evidenced as satisfied: GRS-002 (Pull request and two independent approvals required); GRS-005 (Signed changes required on the default branch). Review the observations and remediation steps below.

This is a point-in-time, report-only assessment of the repository that defines and
distributes governance. It is not a security certification or an authorization to
switch consumer or repository enforcement to blocking mode.

## Decision State

- Overall status: `findings`
- Enforcement: `report_only`
- Enforcement change authorized: `false`
- Criteria: `16`
- Passed: `14`
- Failed: `2`
- Critical failures: `1`
- High failures: `1`

## Controls Currently Evidenced

- `GRS-001`: Default branch protected
- `GRS-003`: Governance CI is a required status check
- `GRS-004`: Force pushes and branch deletion blocked
- `GRS-006`: Secret scanning enabled
- `GRS-007`: Secret push protection enabled
- `GRS-008`: Dependency alerts and security updates enabled
- `GRS-009`: Code scanning configured
- `GRS-010`: Third-party GitHub Actions pinned to full commit SHAs
- `GRS-011`: Default and explicit workflow permissions restricted
- `GRS-012`: Critical governance paths have explicit owners
- `GRS-013`: Automation cannot push operational data directly to the default branch
- `GRS-014`: Governance release tags are cryptographically verified
- `GRS-015`: Private vulnerability reporting is enabled
- `GRS-016`: GitHub Actions restricted to approved sources

## Open Findings

| ID | Severity | Finding | Current observation |
|---|---|---|---|
| `GRS-002` | `critical` | Pull request and two independent approvals required | `required_approving_reviews=1, code_owner_review_required=true, last_push_approval_required=true` |
| `GRS-005` | `high` | Signed changes required on the default branch | `signed_changes_required=false` |

## Recommended Next Steps

### 1. Protect the default branch as the governance authority (`P1`)

- Addresses: `GRS-001`, `GRS-002`, `GRS-003`, `GRS-004`
- Prerequisites: `GRS-013`
- Action: Activate a main ruleset requiring pull requests, two independent approving reviews, CODEOWNER and last-push approval, Governance CI, resolved conversations, and protection from deletion and force push.
- Acceptance criteria: A non-bypass test pull request cannot merge without two independent approvals, CODEOWNER and last-push approval, and required checks; direct force push or branch deletion is rejected.

### 2. Require signed changes on main (`P2`)

- Addresses: `GRS-005`
- Prerequisites: `GRS-013`
- Action: Register accountable human and automation signing identities, validate recovery, and add the signed-commit rule to the protected default branch.
- Acceptance criteria: Unsigned commits are rejected from main and authorized signed changes remain operable.

## Complete Criteria

| ID | Severity | Status | Criterion | Observed |
|---|---|---|---|---|
| `GRS-001` | `critical` | `pass` | Default branch protected | `true` |
| `GRS-002` | `critical` | `fail` | Pull request and two independent approvals required | `false` |
| `GRS-003` | `critical` | `pass` | Governance CI is a required status check | `true` |
| `GRS-004` | `critical` | `pass` | Force pushes and branch deletion blocked | `true` |
| `GRS-005` | `high` | `fail` | Signed changes required on the default branch | `false` |
| `GRS-006` | `critical` | `pass` | Secret scanning enabled | `true` |
| `GRS-007` | `critical` | `pass` | Secret push protection enabled | `true` |
| `GRS-008` | `high` | `pass` | Dependency alerts and security updates enabled | `true` |
| `GRS-009` | `high` | `pass` | Code scanning configured | `true` |
| `GRS-010` | `high` | `pass` | Third-party GitHub Actions pinned to full commit SHAs | `true` |
| `GRS-011` | `high` | `pass` | Default and explicit workflow permissions restricted | `true` |
| `GRS-012` | `high` | `pass` | Critical governance paths have explicit owners | `true` |
| `GRS-013` | `critical` | `pass` | Automation cannot push operational data directly to the default branch | `true` |
| `GRS-014` | `high` | `pass` | Governance release tags are cryptographically verified | `true` |
| `GRS-015` | `high` | `pass` | Private vulnerability reporting is enabled | `true` |
| `GRS-016` | `high` | `pass` | GitHub Actions restricted to approved sources | `true` |

## Evidence Quality And Limitations

- GitHub repository settings are collected live through the authenticated GitHub API.
- Workflow pinning, CODEOWNERS, direct writes, and release tags are inspected from the checkout.
- Current release tags require a direct trusted signature. The explicitly bounded historical
  tag set is verified against a signed retrospective integrity manifest; this does not claim
  that those historical tags carried an original publication-time signature.
- API errors are retained in the JSON observation. A `404` on a legacy branch-protection
  endpoint does not negate protection established by the effective branch rulesets;
  unavailable administrative observations are not proof that a feature is disabled.
- A passing workflow configuration criterion confirms configuration presence, not absence of
  every implementation vulnerability.

## Release And Consumer Impact

- Released DevSecOps and architecture baseline packages are unchanged.
- Consumer evidence contracts and enforcement modes are unchanged.
- Self-Security profile `0.4.0` adds structured release-integrity verification;
  report schema `0.2.0` remains compatible.
- No baseline release is required for this reporting improvement.

## Decision Boundary

This assessment is report-only. It does not edit GitHub settings, block pull requests,
change released baselines, or authorize automated bypass. Missing evidence is reported
as a failed criterion.
