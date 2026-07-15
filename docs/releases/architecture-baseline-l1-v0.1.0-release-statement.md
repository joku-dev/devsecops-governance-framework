# Official Release Statement: Architecture L1 Baseline v0.1.0

## Release Summary

`architecture-baseline-l1-v0.1.0` is the first prepared release of the Architecture Runtime Governance `L1` baseline.

It packages the architecture requirements, gates, policies, schemas and runtime evidence collection scripts needed to evaluate downstream repositories in a repeatable way.

## Intended Release Tag

- `architecture-baseline-l1-v0.1.0`

## Release Classification

- Type: initial architecture baseline release
- Compatibility: additive
- Evidence contract impact: formalizes the existing architecture release candidate input

## Baseline Content

The baseline includes:

- `ARCH-L1` minimum architecture evidence requirements
- architecture readiness gate
- integration readiness gate
- operation readiness gate
- release readiness gate
- architecture evidence and release candidate schemas
- OPA policies for all four runtime gates
- architecture collector and report generator
- reusable GitHub Actions workflow wrapper

## Operational Effect

Downstream repositories can now distinguish:

- the released architecture governance baseline: `architecture-baseline-l1-v0.1.0`
- the repository-specific product or solution baseline, for example `ha-CPsWMS-demo-baseline`

This makes Architecture Runtime Governance align more closely with the DevSecOps baseline model while preserving solution-level architecture autonomy.

## Validation Evidence

The baseline model has been validated against `joku-dev/ha-CPsWMS`.

The current mainline Architecture Runtime Governance result is:

- Run: `28591158065`
- Commit: `e39c1c0b2ff2007e3a0324212e79e05942f932a2`
- Result: `PASS`
- Gates passed: `4/4`
- Findings: `0`

## Consumer Guidance

Consumers should pin the released architecture workflow:

```yaml
uses: joku-dev/devsecops-governance-as-code/.github/workflows/architecture-baseline-l1-v0.1.0.yml@architecture-baseline-l1-v0.1.0
```

For onboarding and demos, keep `fail_on_findings: false`.

For required architecture gates, set `fail_on_findings: true` once evidence quality and ownership are mature enough.
