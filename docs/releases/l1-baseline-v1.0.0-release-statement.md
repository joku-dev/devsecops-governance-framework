# Official Release Statement: L1 Baseline v1.0.0

## Release Identification

- Release name: `L1 Baseline v1.0.0`
- Release tag: `l1-baseline-v1.0.0`
- Repository: `joku-dev/devsecops-governance-as-code`
- Release commit: `311afe077297c055da70456371cf772666e2888a`
- Release status: `approved for downstream consumption`

## Statement

This release establishes the first versioned and revision-protected package of the DevSecOps `L1` baseline.

It is intended to serve as a stable governance reference for downstream repositories that need to consume a controlled baseline through GitHub Actions and Git-based revision control.

## Scope Of This Release

The release contains the frozen `L1` baseline package, including:

- the `L1` control snapshot
- the supporting evidence model snapshot
- the OPA rules used by the baseline gate
- the relevant validation schemas
- a versioned reusable workflow wrapper for downstream repositories
- a downstream GitHub Actions consumption example
- release metadata and package checksums

## Governance Meaning

This release means that downstream repositories can now integrate against a baseline that is:

- versioned
- reviewable
- checksum-documented
- traceable to a Git tag
- protected from untracked drift when pinned correctly

## Required Consumption Rule

Downstream repositories should consume this baseline only by:

- the release tag `l1-baseline-v1.0.0`
- or a full commit SHA

They should not consume the baseline from `main` when revision protection, auditability, or formal governance traceability is required.

## Recommended Consumer Reference

Recommended reusable workflow reference:

- `joku-dev/devsecops-governance-as-code/.github/workflows/devsecops-baseline-l1-v1.0.0.yml@l1-baseline-v1.0.0`

## Validation Basis

This release is based on the following successful governance conditions:

- repository validation completed successfully
- unit and integration tests completed successfully
- the governance repository was successfully exercised against `ha-CPsWMS`
- protected-branch governance gating was verified in a real PR-based flow

## Release Artifacts

Primary release package artifacts:

- `releases/l1/v1.0.0/baseline-package.md`
- `releases/l1/v1.0.0/release-metadata.json`
- `releases/l1/v1.0.0/checksums.sha256`
- `releases/l1/v1.0.0/examples/github-actions/devsecops-baseline-l1-v1.0.0.yml`

## Operational Use

This release can be used by:

- application repositories onboarding to the DevSecOps baseline
- platform teams standardizing repository controls
- governance teams defining a stable minimum control package
- auditors and reviewers who need a frozen baseline reference

## Release Intent

This release is intended as the initial stable publication layer for `L1`.

Future releases should follow the same model and publish new frozen packages such as:

- `l1-baseline-v1.0.1`
- `l1-baseline-v1.1.0`
- `l2-baseline-v1.0.0`

## Approval Note

This statement documents that `L1 Baseline v1.0.0` is now available as a controlled baseline package for downstream use under Git-based revision protection.
