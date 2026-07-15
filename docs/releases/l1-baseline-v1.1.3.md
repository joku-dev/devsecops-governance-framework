# L1 Baseline v1.1.3

This page describes the `L1` baseline patch release that introduces explicit run-context handling for governance evaluation.

## Purpose

`v1.1.3` distinguishes real release runs from diagnostic, pull-request, and branch-validation runs.

This prevents release-only controls from being reported as failed when a workflow is intentionally executed outside a release context.

## What Changed

- added optional `run_context` support to the governance run input contract
- added `pipeline.event` support for downstream evidence
- updated the control evaluator so `DSCB-L1-REQ-013` and `DSCB-L1-REQ-014` are only evaluated in release context
- preserved full `L1` release-context coverage for main push runs
- documented diagnostic and pull-request behavior

## Release Package

- `releases/l1/v1.1.3/baseline-package.md`
- `releases/l1/v1.1.3/release-metadata.json`
- `releases/l1/v1.1.3/checksums.sha256`

## Consumer Workflow

Downstream repositories should consume:

```yaml
uses: joku-dev/devsecops-governance-as-code/.github/workflows/devsecops-baseline-l1-v1.1.3.yml@l1-baseline-v1.1.3
```

## Migration Notes

The `run_context` section is optional and backward compatible.

Recommended values:

```json
{
  "run_context": {
    "event": "push",
    "purpose": "release",
    "release_context": true,
    "source": "github-actions"
  }
}
```

For manual diagnostic runs:

```json
{
  "run_context": {
    "event": "workflow_dispatch",
    "purpose": "diagnostic",
    "release_context": false,
    "source": "github-actions"
  }
}
```
