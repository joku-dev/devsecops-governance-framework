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

The repository explicitly uses `report-only` for all pilot triggers. Its main
branch has review protection; a successful report-only workflow can still
contain governance findings.

## Accepted Mainline Validation On 11 September 2026

| Check | Result | Run |
| --- | --- | --- |
| CI | `success` | `https://github.com/joku-dev/governance-framework-demo-consumer/actions/runs/34606820033` |
| DevSecOps Baseline | `success` | `https://github.com/joku-dev/governance-framework-demo-consumer/actions/runs/34606820493` |
| Architecture Governance | `success` | `https://github.com/joku-dev/governance-framework-demo-consumer/actions/runs/34606820390` |

Validated commit:

```text
7d6a4f67c5e8441e1067405cc2da17218dc256fd
```

The accepted DevSecOps result is `pass`, represented by a one-gate fallback
summary rather than the full control catalog. Architecture has **25 findings**
across four gates despite technical workflow success. Typed vulnerability
evidence from the same DevSecOps run has zero scanner findings, passing recorded
integrity/Freshness checks and Trust `integrity_verified`. Both source and
central accepted state bind to the commit above. Blocking Readiness remains
`not_ready`; these are dated observations, not a production approval.

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
3. Adapt evidence generation to your application. The reference includes a real
   Trivy scan; a minimal/example SBOM must be replaced with application-specific
   tool output before claiming coverage.
4. Add or approve application-specific architecture evidence.
5. Enable blocking only after the current [readiness assessment](../operations/status/blocking-readiness.md), accountable approval and a separate consumer change.

## Related Entry Points

- Public Quickstart: `docs/onboarding/public-repo-quickstart.md`
- Adoption Package: `adoption-package/README.md`
- First Adoption Checklist: `adoption-package/checklists/first-adoption-checklist.md`
