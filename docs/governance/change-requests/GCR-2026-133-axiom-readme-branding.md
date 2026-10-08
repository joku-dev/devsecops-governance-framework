# GCR-2026-133: AXIOM README Branding

## Summary

- Introduce the maintainer-selected AXIOM logo in the repository README.
- Use a local `<picture>` element with a dark-theme variant and an accessible image description.
- Preserve the existing repository title, technical identity, navigation and operational descriptions.

## Change ID

`GCR-2026-133`

## Artifact Intake Classification

| Field | Value |
|---|---|
| Artifact name | AXIOM logo and dark-theme display variant |
| Artifact type | documentation / publishing communication asset |
| Target path | `docs/publishing/branding/axiom-logo.png`, `docs/publishing/branding/axiom-logo-dark.png`; referenced from `README.md` |
| Owner | Repository Owner / Governance Platform Lead |
| Source Document Intake required? | no |
| Evidence contract impact | none |
| Runtime governance impact | none |
| Release impact | none |
| Validation required | Pinned governance validation, strict MkDocs build, README image-path and visual checks |

## Source Document Intake

These are presentation assets requested by the maintainer on 8 October 2026.
They do not define policy, controls, architecture guardrails, evidence contracts
or governance decisions. Full Source Document Intake and a source-register
update are not required. Replacement review is not applicable.

## Why This Change Is Needed

The maintainer selected AXIOM as the repository brand and requested that the
generated logo be included in the README. The approved light-interface logo is
retained as supplied. A near-white wordmark on a dark background supports
GitHub's dark theme. Both images are versioned in the repository rather than
linked to an external image service.

## Impact Analysis

| Area | Impact |
|---|---|
| README presentation | AXIOM logo, tagline and brand introduction |
| Policy, directive, controls and platform model | none |
| Architecture governance, OPA policies and schemas | none |
| Evidence contracts, source register and lineage | none |
| Viewer, status indexes and intake | none |
| Release packages, baseline pins and downstream contracts | none |
| Repository name, workflow references and published URLs | none |

## Governance Behavior

- [x] Documentation-only
- [ ] Report-only governance behavior
- [ ] Blocking governance behavior
- [ ] Release packaging only

## Release Decision

- [x] No release required

## Validation Plan

- Run `./scripts/bootstrap_validation_env.sh` and `./scripts/validate_all.sh`.
- Run `.venv-docs/bin/mkdocs build --strict`.
- Confirm the README's local image paths resolve and both PNGs load.
- Inspect both display variants for readable branding and exact text.
- Run `git diff --check` and keep the commit limited to the README, two logo assets and this intake record.

## Reviewer Notes

The logo is a presentation asset, not a compliance badge or an evidence-trust
indicator. The README retains its existing heading and all original content.
