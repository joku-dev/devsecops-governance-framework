# L1 Baseline v1.1.0

This page points to the second versioned `L1` baseline package with explicit support for the governance run input contract.

## Release Package

- `releases/l1/v1.1.0/baseline-package.md`
- `releases/l1/v1.1.0/release-metadata.json`
- `releases/l1/v1.1.0/checksums.sha256`

## Consumer Workflow

Other repositories can consume this package through:

- `.github/workflows/devsecops-baseline-l1-v1.1.0.yml`

The intended reference model is:

- pin the workflow by release tag
- or pin it by full commit SHA

## Main Improvement Over v1.0.0

This package adds the officially versioned consumer path for:

- `governance/governance-run-input.json`

That allows downstream repositories to provide richer machine-readable evidence for control evaluation, while keeping the baseline integration stable.
