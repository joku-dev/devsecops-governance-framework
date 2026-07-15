# L1 Baseline v1.0.0

This page points to the first versioned and revision-protected `L1` baseline release package.

## Release Package

- `releases/l1/v1.0.0/baseline-package.md`
- `releases/l1/v1.0.0/release-metadata.json`
- `releases/l1/v1.0.0/checksums.sha256`
- `l1-baseline-v1.0.0-release-statement.md`

## Consumer Workflow

Other repositories can consume the frozen release through:

- `.github/workflows/devsecops-baseline-l1-v1.0.0.yml`

The recommended reference model is:

- pin the workflow by release tag
- or pin it by full commit SHA

## Included Snapshot

The release contains:

- frozen `L1` controls
- frozen evidence definitions
- frozen OPA baseline rules
- frozen validation schemas
- frozen workflow example for application repositories

## Operational Rule

For revision-safe consumption, downstream repositories should not reference `main`. They should reference the released workflow file through a fixed Git tag or a full commit SHA.
