# L1 Baseline Release Package v1.1.1

## Purpose

This package is a patch release of the versioned DevSecOps `L1` baseline for downstream repositories.

Its purpose is to correct the released wrapper pin so the official governance run input contract works in real consumer repositories.

## What Is New In v1.1.1

- corrected released `L1` workflow wrapper pin for `governance_run_input_path`
- corrected downstream workflow example to use `l1-baseline-v1.1.1`
- preserved the governance run input contract support introduced in `v1.1.0`

## Consumer Entry Point

Other repositories should consume this release through:

- `.github/workflows/devsecops-baseline-l1-v1.1.1.yml`

Recommended reference model:

- pin to the release tag once created
- or pin to a full commit SHA

Intended released workflow reference:

- `joku-dev/devsecops-governance-as-code/.github/workflows/devsecops-baseline-l1-v1.1.1.yml@l1-baseline-v1.1.1`

## Revision Protection Model

This release is revision-oriented because:

1. the package contents are stored in Git under `releases/l1/v1.1.1/`
2. the consumer workflow wrapper has a versioned file name
3. the wrapper pins the underlying reusable workflow to a full commit SHA
4. the release metadata and checksums are stored alongside the package

## Included Files

- `source/model/controls/dscb-l1.yaml`
- `source/model/evidence/evidence-types.yaml`
- `source/policies/opa/`
- `source/schemas/`
- `source/workflows/devsecops-baseline-reusable.yml`
- `source/workflows/devsecops-baseline-l1-v1.1.1.yml`
- `examples/github-actions/devsecops-baseline-l1-v1.1.1.yml`
- `release-metadata.json`
- `checksums.sha256`

## Governance Run Input

This release supports the optional downstream evidence file:

- `governance/governance-run-input.json`

The authoritative schema in this release is:

- `source/schemas/governance-run-input.schema.json`

## Recommended Usage Rule

Application repositories should treat this package as an approved baseline release candidate and reference it only by:

- release tag
- or full commit SHA

They should not reference `main` if revision control and auditability are required.
