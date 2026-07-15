# Official Release Statement: L1 Baseline v1.1.0

## Release Identification

- Release name: `L1 Baseline v1.1.0`
- Intended release tag: `l1-baseline-v1.1.0`
- Repository: `joku-dev/devsecops-governance-as-code`
- Release status: `prepared in repository`

## Statement

This package extends the released `L1` baseline line with a versioned downstream workflow interface for the official governance run input contract.

It is intended to make downstream reuse easier, more explicit, and more auditable.

## Scope Of This Release

The package contains:

- the frozen `L1` control snapshot
- the supporting evidence model snapshot
- the OPA rules used by the baseline gate
- the relevant validation schemas
- the governance run input schema snapshot
- a versioned reusable workflow wrapper for downstream repositories
- a downstream GitHub Actions example that includes governance run input evidence

## Governance Meaning

This package prepares the repository for a more mature downstream consumption model:

- baseline gate execution remains centralized
- richer evidence can now be generated consistently by consumer repositories
- the additional evidence is tied to an explicit schema and release package

## Required Consumption Rule

Downstream repositories should consume this package only by:

- the release tag `l1-baseline-v1.1.0`
- or a full commit SHA

They should not consume the baseline from `main` when revision protection or auditability is required.
