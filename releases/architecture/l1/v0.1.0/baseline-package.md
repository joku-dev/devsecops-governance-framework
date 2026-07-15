# Architecture L1 Baseline Release Package v0.1.0

## Purpose

This package is the first versioned Architecture Runtime Governance `L1` baseline for downstream repositories.

Its purpose is to make architecture governance consumable in the same general pattern as the DevSecOps baseline: versioned model, pinned workflow, repeatable evidence contract and policy-as-code checks.

## Included Assets

- `ARCH-L1` requirements snapshot
- architecture review gate snapshot
- quality marker snapshot
- architecture guardrail snapshot
- remediation action snapshot
- architecture OPA policy snapshot
- architecture release candidate schema snapshot
- application architecture evidence schema snapshot
- collector and report generator scripts
- released reusable workflow wrapper
- downstream GitHub Actions example
- release metadata
- checksums

## Consumer Reference

Use:

```yaml
uses: joku-dev/devsecops-governance-as-code/.github/workflows/architecture-baseline-l1-v0.1.0.yml@architecture-baseline-l1-v0.1.0
```

## Baseline Versus Solution Baseline

`architecture-baseline-l1-v0.1.0` is the governance baseline.

The consuming application still declares its own product or solution architecture baseline, for example `ha-CPsWMS-demo-baseline`.
