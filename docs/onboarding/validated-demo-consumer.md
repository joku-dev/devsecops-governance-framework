# Validated Demo Consumer

## Purpose

This page records a neutral public consumer repository that proves the public DevSecOps Governance Framework can be consumed from a fresh application repository.

Consumer repository:

```text
joku-dev/governance-framework-demo-consumer
```

Repository URL:

```text
https://github.com/joku-dev/governance-framework-demo-consumer
```

## What The Consumer Uses

The consumer repository calls the public governance framework directly:

| Workflow | Public baseline |
| --- | --- |
| `DevSecOps Baseline` | `joku-dev/devsecops-governance-framework/.github/workflows/devsecops-baseline-l1-v1.1.3.yml@l1-baseline-v1.1.3` |
| `Architecture Governance` | `joku-dev/devsecops-governance-framework/.github/workflows/architecture-baseline-l1-v0.1.0.yml@architecture-baseline-l1-v0.1.0` |

The repository intentionally starts in `report-only` mode. This demonstrates first adoption without requiring production branch protection or mature evidence on day one.

## Validation Run

| Check | Result | Run |
| --- | --- | --- |
| CI | `success` | `https://github.com/joku-dev/governance-framework-demo-consumer/actions/runs/29410866381` |
| DevSecOps Baseline | `success` | `https://github.com/joku-dev/governance-framework-demo-consumer/actions/runs/29410867001` |
| Architecture Governance | `success` | `https://github.com/joku-dev/governance-framework-demo-consumer/actions/runs/29410866951` |

Validated commit:

```text
d8f35c68da909ad7471c0350427e5be80b2d3a67
```

## Produced Artifacts

The successful DevSecOps baseline run produced:

- `application-evidence`
- `devsecops-pipeline-evidence`
- `devsecops-governance-run-input`

The successful architecture governance run produced:

- `architecture-governance-evidence`

## How To Use This Example

Use this repository as a minimal reference when onboarding another application repository:

1. Copy the workflow structure.
2. Keep first runs in `report-only`.
3. Replace placeholder SBOM and vulnerability evidence with real tool output.
4. Add or approve application-specific architecture evidence.
5. Enable blocking behavior only after branch protection and evidence quality are stable.

## Related Entry Points

- Public Quickstart: `docs/onboarding/public-repo-quickstart.md`
- Adoption Package: `adoption-package/README.md`
- First Adoption Checklist: `adoption-package/checklists/first-adoption-checklist.md`
