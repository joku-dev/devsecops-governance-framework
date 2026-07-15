# Official Release Statement: L1 Baseline v1.1.3

## Release Summary

`l1-baseline-v1.1.3` is a patch release of the released DevSecOps `L1` baseline.

It introduces run-context-aware governance evaluation so release authorization controls are evaluated only when a run represents a real release context.

## Intended Release Tag

- `l1-baseline-v1.1.3`

## Release Classification

- Type: patch release
- Compatibility: backward compatible
- Evidence contract impact: additive optional field

## Main Change

The release adds optional `run_context` evidence:

- `event`
- `purpose`
- `release_context`
- `source`

This allows the evaluator to distinguish:

- `push` release runs
- `pull_request` validation runs
- `workflow_dispatch` diagnostic runs
- branch validation runs

## Operational Effect

In release context:

- `DSCB-L1-REQ-013` is evaluated from release approval evidence
- `DSCB-L1-REQ-014` is evaluated from approved-artifact deployment evidence

Outside release context:

- these release-specific controls are reported as `not_applicable`
- diagnostic and PR runs no longer create misleading release-authorization failures

## Validation Evidence

The change was validated against `joku-dev/ha-CPsWMS`:

- PR validation run: `28302764711`
- Main release-context run: `28302814664`

The main release-context run retained:

- `16` passed controls
- `0` failed controls
- `0` not tested controls

## Consumer Guidance

Consumers should update to:

```yaml
uses: joku-dev/devsecops-governance-framework/.github/workflows/devsecops-baseline-l1-v1.1.3.yml@l1-baseline-v1.1.3
```

Consumers that provide a custom `governance/governance-run-input.json` should add `run_context` when possible.
