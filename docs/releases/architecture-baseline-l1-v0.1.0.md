# Architecture L1 Baseline v0.1.0

This page describes the first released Architecture Runtime Governance `L1` baseline.

## Purpose

`architecture-baseline-l1-v0.1.0` turns the architecture runtime governance model into a versioned baseline that downstream repositories can pin in CI/CD.

The baseline defines the minimum architecture evidence, review gates and policy checks required to evaluate product and solution architecture readiness.

## Baseline Scope

The release covers:

- Architecture L1 requirements from `architecture/arch-l1.yaml`
- Architecture readiness, integration readiness, operation readiness and release readiness gates
- Quality marker and guardrail snapshots used by the runtime model
- OPA policies for architecture runtime governance
- Schemas for architecture release candidate evidence and architecture evidence files
- Collector and report generator scripts
- A reusable GitHub Actions workflow wrapper

## Baseline Identity

- Baseline ID: `architecture-baseline-l1-v0.1.0`
- Level: `ARCH-L1`
- Model version: `0.1.0`
- Intended tag: `architecture-baseline-l1-v0.1.0`

## Consumer Workflow

Downstream repositories can consume the released architecture baseline with:

```yaml
jobs:
  architecture-baseline:
    uses: joku-dev/devsecops-governance-framework/.github/workflows/architecture-baseline-l1-v0.1.0.yml@architecture-baseline-l1-v0.1.0
    with:
      solution_baseline: example-solution-baseline
      fail_on_findings: false
```

`solution_baseline` is the product or solution architecture baseline of the consuming repository.

`architecture-baseline-l1-v0.1.0` is the governance baseline that defines what is checked.

## Release Package

- `releases/architecture/l1/v0.1.0/baseline-package.md`
- `releases/architecture/l1/v0.1.0/release-metadata.json`
- `releases/architecture/l1/v0.1.0/checksums.sha256`

## Migration Notes

Existing Architecture Runtime Governance users can keep their current product or solution baseline names.

For status reporting and viewer consistency, new architecture runs should identify the governance baseline as `architecture-baseline-l1-v0.1.0` while keeping the product or solution baseline in the collected architecture release input.
