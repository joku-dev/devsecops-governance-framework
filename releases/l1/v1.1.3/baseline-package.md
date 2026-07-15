# L1 Baseline Release Package v1.1.3

## Purpose

This package is a patch release of the versioned DevSecOps `L1` baseline for downstream repositories.

Its purpose is to introduce run-context-aware governance evaluation while preserving backward compatibility with the `v1.1.x` governance run input contract.

## What Is New In v1.1.3

- optional `run_context` support in governance run input
- optional `pipeline.event` support in pipeline evidence
- release-only controls are not applicable outside release context
- released wrapper pinned to the governance implementation that includes run-context handling

## Consumer Reference

Use:

```yaml
uses: joku-dev/devsecops-governance-as-code/.github/workflows/devsecops-baseline-l1-v1.1.3.yml@l1-baseline-v1.1.3
```

## Included Assets

- released reusable workflow wrapper
- reusable baseline workflow snapshot
- `L1` controls snapshot
- evidence catalog snapshot
- OPA policy snapshot
- schema snapshot
- downstream GitHub Actions example
- release metadata
- checksums
