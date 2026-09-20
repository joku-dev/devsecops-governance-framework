# GCR-2026-103: Publish the operational assurance repository release

## Request And Classification

The maintainer requested a release from the current reviewed repository state
after completion of GRS-014. This change prepares and publishes the next release
of the repository adoption and operations line.

| Field | Value |
|---|---|
| Artifact intake classification | Repository release statement and derived publication asset manifest |
| Target | `v0.3.0-public-adoption`, repository adoption and operations release line |
| Version impact | Minor; backward-compatible operational, evidence, viewer, security and scale capabilities were added since v0.2.0 |
| Source document intake | None; no new normative source or candidate derivation |
| Baseline effect | DevSecOps `l1-baseline-v1.1.3` and Architecture `architecture-baseline-l1-v0.1.0` remain unchanged |
| Consumer migration | Existing baseline pins remain valid; no required evidence field or enforcement default changes |
| Publication owner | Repository maintainer; publication explicitly requested on 20 September 2026 |

## Release Scope

Publish the current repository state as `v0.3.0-public-adoption`. The release
records the capabilities introduced after v0.2.0:

- closed-loop governance lifecycle contracts, decisions, actions, exceptions,
  metrics, candidates and guarded operational publication;
- the Governance Workspace with integrated technical results, Evidence Trust,
  replay, measured-control and repository-security views;
- typed vulnerability and SBOM intake plus conservative control-level assurance;
- real ha-CPsWMS staging deployment evidence and consolidated L1 measurement;
- repository hardening, CodeQL remediation, Self-Security and cryptographic
  release-tag verification;
- capacity simulation and operating guidance for 300 to 1,500 consumer
  repositories.

The release reuses the four publication binaries from v0.2.0 byte-for-byte and
publishes a new manifest and checksum file for the new release identity. The
signed tag binds the complete repository revision, including the updated
release statement and current documentation.

## Compatibility And Decision Boundary

This repository release does not create a new control baseline, change the
consumer workflow pins, authorize production operation or enable new blocking.
New consumer pilots remain report-only. The historical baseline packages and
tags remain immutable.

The release retains visible limitations: GRS-002 and GRS-005 remain open,
ha-CPsWMS retains a replay finding, scanner findings require risk assessment,
and production-scale operation still requires the measures in the capacity
assessment.

## Publication Gate

- [x] release statement, navigation and asset manifest are complete
- [x] publication asset hashes match the tracked files
- [x] pinned full validation (623 tests) and strict MkDocs build pass
- [ ] preparation PR checks pass and the reviewed state is merged to `main`
- [ ] mainline Governance CI, CodeQL, Self-Security and Pages pass
- [ ] annotated tag is directly SSH-signed by the active registered signer
- [ ] local release-integrity verification recognizes the new tag
- [ ] GitHub Release is published with manifest, checksums and publication assets
- [ ] downloaded release assets match `SHA256SUMS`

The signed retrospective integrity manifest is not extended. It remains limited
to the three historical tags already named by GCR-2026-102.
