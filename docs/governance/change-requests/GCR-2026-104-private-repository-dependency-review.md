# GCR-2026-104: Keep dependency review fail-closed on the private repository

## Trigger And Classification

Release PR #175 exposed a provider-plan failure unrelated to its release
content: GitHub's dependency review action stopped with `Advanced security has
not been purchased` after the repository became private.

| Field | Value |
|---|---|
| Change type | Required-check reliability and fail-closed dependency scope |
| Baseline effect | None |
| Consumer contract effect | None |
| Enforcement effect | Dependency changes remain blocked unless the pinned native review succeeds |
| Release relationship | Operational prerequisite discovered during `v0.3.0-public-adoption` preparation |

## Change

Dependency Review now determines whether a recognized dependency manifest
changed between the exact base and head revisions. If no manifest changed, the
job records that fact and succeeds without calling an unavailable licensed
service. If a manifest changed, the pinned native GitHub dependency review
remains mandatory; lack of GitHub Advanced Security therefore blocks the PR.
This does not silently accept a dependency change.

The design keeps the existing required check name and the action pin. It does
not claim that GitHub Advanced Security is enabled for the private repository.

## Acceptance

- documentation-only changes produce `changed=false` and a successful required
  Dependency Review job;
- changes to a recognized dependency manifest produce `changed=true` and
  require the pinned native review;
- workflow structure, pinning and scope-detection tests pass;
- full repository validation remains green.

Consumer Lifecycle Guard separately failed because the configured
`GH_RESULT_INTAKE_TOKEN` could no longer read the retained local provider
discussion after the repository became private. Its implementation is bound to
the existing personal operating acceptance and is intentionally not changed by
this GCR. Restore the token's read access instead.
