# L1 Baseline Release Package v1.1.0

## Purpose

This package is the second versioned and revision-oriented release of the DevSecOps `L1` baseline for downstream repositories.

Its main improvement over `v1.0.0` is that it introduces a versioned consumer pattern for the official governance run input contract.

## What Is New In v1.1.0

- released `L1` workflow wrapper with `governance_run_input_path`
- released downstream workflow example that includes `governance/governance-run-input.json`
- frozen copy of `schemas/governance-run-input.schema.json`
- clearer downstream evidence contract for richer control evaluation

## Consumer Entry Point

Other repositories should consume this release through:

- `.github/workflows/devsecops-baseline-l1-v1.1.0.yml`

Recommended reference model:

- pin to the release tag once created
- or pin to a full commit SHA

Intended released workflow reference:

- `joku-dev/devsecops-governance-as-code/.github/workflows/devsecops-baseline-l1-v1.1.0.yml@l1-baseline-v1.1.0`

## Revision Protection Model

This release is revision-oriented because:

1. the package contents are stored in Git under `releases/l1/v1.1.0/`
2. the consumer workflow wrapper has a versioned file name
3. the wrapper pins the underlying reusable workflow to a full commit SHA
4. the release metadata and checksums are stored alongside the package

Full revision protection is achieved once the matching Git tag is created for this package.

## Included Files

- `source/model/controls/dscb-l1.yaml`
- `source/model/evidence/evidence-types.yaml`
- `source/policies/opa/`
- `source/schemas/`
- `source/workflows/devsecops-baseline-reusable.yml`
- `source/workflows/devsecops-baseline-l1-v1.1.0.yml`
- `examples/github-actions/devsecops-baseline-l1-v1.1.0.yml`
- `release-metadata.json`
- `checksums.sha256`

## Governance Run Input

This release formalizes the optional downstream evidence file:

- `governance/governance-run-input.json`

The authoritative schema in this release is:

- `source/schemas/governance-run-input.schema.json`

The repo-level explanation remains:

- `docs/operations/governance-evidence-contract.md`

## Recommended Usage Rule

Application repositories should treat this package as an approved baseline release candidate and reference it only by:

- release tag
- or full commit SHA

They should not reference `main` if revision control and auditability are required.
