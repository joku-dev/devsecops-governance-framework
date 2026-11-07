# Releases

This section contains repository release statements and baseline package documentation.

## Publication readback — 7 November 2026

The latest **published GitHub repository adoption release** is
[v0.2.0](v0.2.0-public-adoption.md); v0.1.0 is also published.
[v0.3.0](v0.3.0-public-adoption.md) is a prepared release statement and assets.
There was no `v0.3.0-public-adoption` remote tag or published GitHub Release at
this readback. Its preparation is not evidence of publication.

| Release surface | Observed state |
|---|---|
| Remote DevSecOps baseline tags | `l1-baseline-v1.1.3`, `l1-baseline-v1.2.0`, `l1-baseline-v1.2.1` |
| Remote architecture baseline tag | `architecture-baseline-l1-v0.1.0` |
| Published GitHub adoption releases | `v0.1.0-public-adoption`, `v0.2.0-public-adoption` |
| Prepared repository adoption statement | `v0.3.0-public-adoption`, without a remote tag or published GitHub Release |
| Pins in retained accepted ha-CPsWMS results | DevSecOps `l1-baseline-v1.1.3`; architecture `architecture-baseline-l1-v0.1.0` |

Baseline tags, package documentation, repository adoption releases and consumer
pins are distinct. A newer baseline tag does not migrate an existing consumer.
This documentation correction creates no tag, release or consumer update.
Sources: [published GitHub Releases](https://github.com/joku-dev/devsecops-governance-framework/releases),
remote tags read with `git ls-remote --tags`, and the
[accepted-index readback](../operations/status/current-governance-platform-state.md).

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
- `L1 baseline v1.2.1` (`l1-baseline-v1.2.1`, published and directly SSH-signed)
- `Architecture L1 baseline v0.1.0`
- `Public adoption release v0.1.0`
- `Operational pilot repository release v0.2.0`
- `Operational assurance repository release v0.3.0` (prepared, unpublished)

The latest baseline packages and prepared repository statement are:

- `L1 baseline v1.2.1` (`l1-baseline-v1.2.1`, directly SSH-signed and published)
- `Architecture L1 baseline v0.1.0`
- `Operational assurance repository release v0.3.0` (prepared, unpublished)

The latest DevSecOps patch release is
[L1 baseline v1.2.1](l1-baseline-v1.2.1.md), with its
[release statement](l1-baseline-v1.2.1-release-statement.md). Downstream
report-only validation continues before ECV-01 can be reassessed.

The working source still remains in `model/`, while approved frozen release packages are published under `releases/`.

The operational-pilot tag is directly SSH-signed. The prepared
operational-assurance statement requires a directly signed tag before publication. The three older
unsigned baseline/adoption tags are preserved under their original identities
and covered by the signed retrospective release-integrity statement. Future
release tags require direct signatures. See the
[release and migration model](release-and-migration-model.md) for the assurance
boundary.

To understand how releases should evolve and how downstream repositories should migrate, read:

- `release-and-migration-model.md`

## Baseline Packages And Repository Release Statements

- `Release publication checklist`: `release-publication-checklist.md`
- [Prepared operational assurance statement v0.3.0](v0.3.0-public-adoption.md)
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
- `L1 baseline v1.2.1`: `l1-baseline-v1.2.1.md`
- `L1 baseline v1.2.1 release statement`: `l1-baseline-v1.2.1-release-statement.md`
- `Architecture L1 baseline v0.1.0`: `architecture-baseline-l1-v0.1.0.md`
- `Architecture L1 baseline v0.1.0 release statement`: `architecture-baseline-l1-v0.1.0-release-statement.md`
