# Releases

This section contains repository release statements and baseline package documentation.

The current adoption/operations release line is
[Operational Assurance v0.3.0](v0.3.0-public-adoption.md), tagged
`v0.3.0-public-adoption`. Its signed tag and published GitHub Release establish
publication; a preparation branch or draft alone does not. This repository
release keeps DevSecOps L1 `l1-baseline-v1.2.0` and Architecture L1
`architecture-baseline-l1-v0.1.0` as the separate supported baseline pins.

The intended release model is:

- each baseline release gets its own versioned folder under `releases/`
- the package contains the approved model snapshot, generated artifacts, schemas, and policy rules
- consuming teams can pin a known governance version in their CI/CD integration

The repository now contains formal released baseline packages for DevSecOps `L1` and Architecture `L1`.
It also contains a public adoption release for first external application-repository onboarding.

The currently documented release set in the repository is:

- `L1 baseline v1.0.0`
- `L1 baseline v1.1.0`
- `L1 baseline v1.1.1`
- `L1 baseline v1.1.2`
- `L1 baseline v1.1.3`
- `L1 baseline v1.2.0`
- `L1 baseline v1.2.1` (prepared release candidate; unpublished)
- `Architecture L1 baseline v0.1.0`
- `Public adoption release v0.1.0`
- `Operational pilot repository release v0.2.0`
- `Operational assurance repository release v0.3.0`

The latest packages by release line are:

- `L1 baseline v1.2.0` (`l1-baseline-v1.2.0`, directly SSH-signed and published)
- `Architecture L1 baseline v0.1.0`
- `Operational assurance repository release v0.3.0`

The prepared next DevSecOps patch candidate is
[L1 baseline v1.2.1](l1-baseline-v1.2.1.md), with its
[release statement](l1-baseline-v1.2.1-release-statement.md). The supported
published baseline remains v1.2.0 until the candidate is reviewed, merged,
signed, and validated downstream.

The working source still remains in `model/`, while approved frozen release packages are published under `releases/`.

The current operational-assurance tag and the preceding operational-pilot tag
are directly SSH-signed. The three older
unsigned baseline/adoption tags are preserved under their original identities
and covered by the signed retrospective release-integrity statement. Future
release tags require direct signatures. See the
[release and migration model](release-and-migration-model.md) for the assurance
boundary.

To understand how releases should evolve and how downstream repositories should migrate, read:

- `release-and-migration-model.md`

## Available Release Packages

- `Release publication checklist`: `release-publication-checklist.md`
- [Operational assurance repository release v0.3.0](v0.3.0-public-adoption.md)
- [Operational pilot repository release v0.2.0](v0.2.0-public-adoption.md)
- `Public adoption release v0.1.0`: `v0.1.0-public-adoption.md`
- `L1 baseline v1.0.0`: `l1-baseline-v1.0.0.md`
- `L1 baseline v1.0.0 release statement`: `l1-baseline-v1.0.0-release-statement.md`
- `L1 baseline v1.1.0`: `l1-baseline-v1.1.0.md`
- `L1 baseline v1.1.0 release statement`: `l1-baseline-v1.1.0-release-statement.md`
- `L1 baseline v1.1.1`: `l1-baseline-v1.1.1.md`
- `L1 baseline v1.1.1 release statement`: `l1-baseline-v1.1.1-release-statement.md`
- `L1 baseline v1.1.2`: `l1-baseline-v1.1.2.md`
- `L1 baseline v1.1.2 release statement`: `l1-baseline-v1.1.2-release-statement.md`
- `L1 baseline v1.1.3`: `l1-baseline-v1.1.3.md`
- `L1 baseline v1.1.3 release statement`: `l1-baseline-v1.1.3-release-statement.md`
- `L1 baseline v1.2.0`: `l1-baseline-v1.2.0.md`
- `L1 baseline v1.2.0 release statement`: `l1-baseline-v1.2.0-release-statement.md`
- `Prepared L1 baseline v1.2.1 candidate`: `l1-baseline-v1.2.1.md`
- `Prepared L1 baseline v1.2.1 release statement`: `l1-baseline-v1.2.1-release-statement.md`
- `Architecture L1 baseline v0.1.0`: `architecture-baseline-l1-v0.1.0.md`
- `Architecture L1 baseline v0.1.0 release statement`: `architecture-baseline-l1-v0.1.0-release-statement.md`
