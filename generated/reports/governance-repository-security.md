# Governance Repository Self-Security Assessment

Observed: `2026-07-18T16:20:29Z`

## Executive Assessment

The repository has active scanning, dependency, permission, ownership, and private-reporting controls, but it is not yet a protected governance authority because main remains unprotected, automation can write directly to main, and release authenticity is not enforced.

This is a point-in-time, report-only assessment of the repository that defines and
distributes governance. It is not a security certification or an authorization to
switch consumer or repository enforcement to blocking mode.

## Decision State

- Overall status: `findings`
- Enforcement: `report_only`
- Enforcement change authorized: `false`
- Criteria: `16`
- Passed: `7`
- Failed: `9`
- Critical failures: `5`
- High failures: `4`

## Controls Currently Evidenced

- `GRS-006`: Secret scanning enabled
- `GRS-007`: Secret push protection enabled
- `GRS-008`: Dependency alerts and security updates enabled
- `GRS-009`: Code scanning configured
- `GRS-011`: Default and explicit workflow permissions restricted
- `GRS-012`: Critical governance paths have explicit owners
- `GRS-015`: Private vulnerability reporting is enabled

## Open Findings

| ID | Severity | Finding | Current observation |
|---|---|---|---|
| `GRS-001` | `critical` | Default branch protected | `branch_protected=false` |
| `GRS-002` | `critical` | Pull request and approving review required | `required_approving_reviews=0` |
| `GRS-003` | `critical` | Governance CI is a required status check | `required_status_checks=[]` |
| `GRS-004` | `critical` | Force pushes and branch deletion blocked | `force_push_blocked=false, deletion_blocked=false` |
| `GRS-005` | `high` | Signed changes required on the default branch | `signed_changes_required=false` |
| `GRS-010` | `high` | Third-party GitHub Actions pinned to full commit SHAs | `unpinned_refs=0, sha_pinning_required=false` |
| `GRS-013` | `critical` | Automation cannot push operational data directly to the default branch | `direct_main_write_workflows=[".github/workflows/intake-architecture-result.yml", ".github/workflows/intake-evidence-trust.yml", ".github/workflows/intake-governance-result.yml", ".github/workflows/portfolio-status.yml"]` |
| `GRS-014` | `high` | Governance release tags are cryptographically verified | `unverified_release_tags=["architecture-baseline-l1-v0.1.0", "l1-baseline-v1.1.3", "v0.1.0-public-adoption"]` |
| `GRS-016` | `high` | GitHub Actions restricted to approved sources | `allowed_actions=all` |

## Recommended Next Steps

### 1. Migrate automated writes away from direct main pushes (`P0`)

- Addresses: `GRS-013`
- Prerequisites: none
- Action: Replace intake and portfolio git pushes with reviewed bot pull requests or a separately protected operational evidence store. Keep normative governance outside the automation write authority.
- Acceptance criteria: No active workflow combines contents: write with git push to the default branch.

### 2. Enforce immutable GitHub Action references (`P0`)

- Addresses: `GRS-010`, `GRS-016`
- Prerequisites: none
- Action: Verify all active workflow references remain pinned to reviewed full commit SHAs, restrict Actions to approved publishers, then enable repository-level SHA pinning.
- Acceptance criteria: The workflow scan has no mutable third-party references, allowed_actions is selected, and GitHub reports sha_pinning_required as true.

### 3. Protect the default branch as the governance authority (`P1`)

- Addresses: `GRS-001`, `GRS-002`, `GRS-003`, `GRS-004`
- Prerequisites: `GRS-013`
- Action: Activate a main ruleset requiring pull requests, at least one approving review, Governance CI, resolved conversations, and protection from deletion and force push.
- Acceptance criteria: A non-bypass test pull request cannot merge without approval and required checks, and direct force push or branch deletion is rejected.

### 4. Require signed changes on main (`P2`)

- Addresses: `GRS-005`
- Prerequisites: `GRS-013`
- Action: Register accountable human and automation signing identities, validate recovery, and add the signed-commit rule to the protected default branch.
- Acceptance criteria: Unsigned commits are rejected from main and authorized signed changes remain operable.

### 5. Introduce verified release publication (`P2`)

- Addresses: `GRS-014`
- Prerequisites: `GRS-005`
- Action: Publish future baseline tags through an accountable signed release process with verification evidence; do not rewrite historical released tags in place.
- Acceptance criteria: New governance baseline tags verify cryptographically and their release packages retain valid checksums and provenance.

## Complete Criteria

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
| `GRS-016` | `high` | `fail` | GitHub Actions restricted to approved sources | `false` |

## Evidence Quality And Limitations

- GitHub repository settings are collected live through the authenticated GitHub API.
- Workflow pinning, CODEOWNERS, direct writes, and release tags are inspected from the checkout.
- GitHub `404` responses for branch protection or required signatures corroborate a missing
  root control in this assessment; they are retained in the JSON observation for auditability.
- A passing workflow configuration criterion confirms configuration presence, not absence of
  every implementation vulnerability.

## Release And Consumer Impact

- Released DevSecOps and architecture baseline packages are unchanged.
- Consumer evidence contracts and enforcement modes are unchanged.
- Report schema `0.2.0` additively introduces a structured remediation plan.
- No baseline release is required for this reporting improvement.

## Decision Boundary

This assessment is report-only. It does not edit GitHub settings, block pull requests,
change released baselines, or authorize automated bypass. Missing evidence is reported
as a failed criterion.
