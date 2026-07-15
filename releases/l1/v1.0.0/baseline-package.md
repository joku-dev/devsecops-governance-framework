# L1 Baseline Release Package v1.0.0

## Purpose

This package is the first versioned and revision-protected release of the DevSecOps `L1` baseline for consumption by other repositories.

## What Is Frozen In This Release

- the `L1` control baseline snapshot
- the supporting evidence model snapshot
- the OPA policy rules used by the baseline gate
- the schemas used to validate core governance structures
- a versioned reusable GitHub Actions workflow wrapper for consumers

## Consumer Entry Point

Other repositories should consume this release through:

- `.github/workflows/devsecops-baseline-l1-v1.0.0.yml`

Recommended reference model:

- pin to the release tag once created
- or pin to a full commit SHA

Current wrapper file:

- `joku-dev/devsecops-governance-as-code/.github/workflows/devsecops-baseline-l1-v1.0.0.yml@l1-baseline-v1.0.0`

## Revision Protection Model

This release is revision-protected because:

1. the package contents are stored in Git under `releases/l1/v1.0.0/`
2. the consumer workflow wrapper has a versioned file name
3. the wrapper pins the underlying reusable workflow to a full commit SHA
4. the release metadata and checksums are stored alongside the package

## Included Files

- `source/model/controls/dscb-l1.yaml`
- `source/model/evidence/evidence-types.yaml`
- `source/policies/opa/`
- `source/schemas/`
- `source/workflows/devsecops-baseline-reusable.yml`
- `source/workflows/devsecops-baseline-l1-v1.0.0.yml`
- `examples/github-actions/devsecops-baseline-l1-v1.0.0.yml`
- `release-metadata.json`
- `checksums.sha256`

## Consumption Example

See:

- `examples/github-actions/devsecops-baseline-l1-v1.0.0.yml`

## Recommended Usage Rule

Application repositories should treat this package as an approved baseline release and reference it only by:

- release tag
- or full commit SHA

They should not reference `main` if revision control and auditability are required.
