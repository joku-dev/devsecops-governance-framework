# GCR-2026-135: AXIOM Engineering Governance Runtime README Title

## Summary

The maintainer requested the README title **AXIOM — Engineering Governance
Runtime** on 8 October 2026 after the AXIOM branding change in PR #237. The
opening description now explains the broader engineering-governance scope and
identifies DevSecOps as a core application area.

## Artifact Intake Classification

| Field | Value |
|---|---|
| Artifact name | AXIOM README title and introduction |
| Artifact type | documentation |
| Target path | `README.md`; this change record |
| Owner | Repository Owner / Governance Platform Lead |
| Source Document Intake required? | no |
| Evidence contract impact | none |
| Runtime governance impact | none |
| Release impact | none |
| Validation required | Pinned governance validation, strict MkDocs build, focused README diff review |

## Scope

This change refines the README presentation. The title describes the existing
engineering-governance concept; it does not change authority, automation modes,
evidence-trust decisions or release approvals. No source-document registration
or replacement review is required.

The logo, tagline, technical repository name, URLs, workflow references,
released baseline identifiers and existing operational content are preserved.
GCR-2026-134 remains the historical record of the original logo integration.

## Validation Plan

- Run `./scripts/validate_all.sh` with the repository-pinned toolchain.
- Run `.venv-docs/bin/mkdocs build --strict`.
- Check references to the former README heading and confirm local logo paths.
- Run `git diff --check` and confirm the README diff is limited to the heading
  and introductory description.

## Release Decision

Documentation-only; no baseline or platform release is required.
