# GCR-2026-183 — Current system architecture organized with arc42

Date: 2026-11-15. Status: documentation update for review.

## Request and artifact classification

The maintainer requests implementation of the proposed arc42 documentation
structure and reconciliation of the technical as-built description. The existing
entry point, heading anchors and operating guide responsibilities are retained.

| Artifact-intake field | Classification |
|---|---|
| Owner | Governance Platform Maintainers |
| Artifact | Explanatory technical architecture, two source SVG views and navigation/status links |
| Target | Existing system-architecture page and diagrams; current platform readback; README/AI/official entrypoints; MkDocs |
| Source Document Intake | Not required; no normative source, source register or requirement change |
| Governance/evidence behavior | Unchanged |
| Release impact | No release; no frozen baseline/tag/consumer pin mutation |

## Scope

The page follows all twelve arc42 sections, preserves old section anchors and
explains the shared runtime, independent SCM/CI boundaries, portable verifier,
private durable collector, accepted Git history, Workbench, exact-source VM
update/recovery and static publication. Static accessible SVG diagrams retain
Mermaid source and need no new renderer. Existing procedures are linked.

Implementation, local/isolated engineering proof and actual operating activation
remain separate. The dated Mac/VM alignment at adc4643 and private diagnostic
replay of eleven unchanged ha-CPsWMS producer files are summarized without
publishing private credentials, paths, reports or uploads. The original 2 October
evidence is not refreshed; portable preflight rejection is kept explicit.

This reorganizes the technical description. It does not resume normative
architecture-governance work, derive new markers/controls, alter enforcement,
activate a portable collector/publisher or install a new host revision. Foundation
and operating-acceptance fingerprints remain unchanged.

## Validation and review

Pinned bootstrap/full validation, strict MkDocs, local target/anchor audit,
old heading-anchor compatibility, SVG XML/render inspection, protected hashes
and full diff hygiene. Prepare revision-bound routed reviews with final Repo
Steward synthesis; coordinator role lenses are declared accurately. Publish only
allowlisted review metadata. CODEOWNER approval and provider CI remain separate.
