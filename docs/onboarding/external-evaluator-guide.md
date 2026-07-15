# External Evaluator Guide

## Purpose

This guide gives an external reviewer a short, repeatable evaluation path for the public DevSecOps Governance Framework.

The goal is to decide whether the framework can be understood, cloned, reviewed, and consumed by an application repository without private context.

## Evaluation Scope

Use this guide to check:

| Area | Expected result |
| --- | --- |
| Repository access | The public repository can be cloned without special access. |
| Documentation entry points | README, Pages, quickstart, and release notes are understandable. |
| Adoption package | The workflow and evidence examples can be copied into an application repository. |
| Reusable baselines | The published GitHub Actions baselines are referenced by immutable tags. |
| Demo consumer | A neutral consumer repository demonstrates successful public usage. |
| Governance mode | First adoption starts in `report-only`; blocking mode is explicit. |

## Ten-Minute Review Path

1. Open the repository README.
2. Open the public Pages site.
3. Read the external review brief.
4. Read the public repository quickstart.
5. Inspect `adoption-package/README.md`.
6. Check the validated demo consumer.
7. Confirm that reusable workflow references use release tags instead of `main`.
8. Confirm that first adoption runs in `report-only`.
9. Review known limitations before recommending production usage.
10. Record findings and open questions.

## Public Entry Points

| Purpose | Entry point |
| --- | --- |
| Repository | `https://github.com/joku-dev/devsecops-governance-framework` |
| Pages site | `https://joku-dev.github.io/devsecops-governance-framework/` |
| Review brief | `docs/onboarding/external-review-brief.md` |
| Pilot runbook | `docs/onboarding/pilot-runbook.md` |
| Quickstart | `docs/onboarding/public-repo-quickstart.md` |
| Adoption package | `adoption-package/README.md` |
| Demo consumer | `https://github.com/joku-dev/governance-framework-demo-consumer` |
| Public release | `docs/releases/v0.1.0-public-adoption.md` |

## What To Verify

### Repository And Documentation

- The repository can be cloned from GitHub.
- The README clearly identifies the framework purpose.
- The Pages site builds and exposes the public onboarding pages.
- The public quickstart can be followed without private repositories or internal names.

### Baseline Consumption

- The DevSecOps baseline uses a released workflow tag:

```text
joku-dev/devsecops-governance-framework/.github/workflows/devsecops-baseline-l1-v1.1.3.yml@l1-baseline-v1.1.3
```

- The Architecture baseline uses a released workflow tag:

```text
joku-dev/devsecops-governance-framework/.github/workflows/architecture-baseline-l1-v0.1.0.yml@architecture-baseline-l1-v0.1.0
```

- A consuming repository provides its own evidence and does not copy framework logic.
- `report-only` is used before any blocking release governance.

### Evidence Model

Check that first adoption produces or uploads:

| Evidence | Expected first-adoption state |
| --- | --- |
| Application artifact | Present or represented by package metadata. |
| SBOM | Placeholder allowed only for wiring tests. |
| Vulnerability scan | Placeholder allowed only for wiring tests. |
| Governance run input | Present and machine-readable. |
| Architecture evidence | Optional for first adoption; draft state must not be treated as approved evidence. |

### Demo Consumer

Use the neutral demo consumer to verify that public consumption has already been exercised.

Expected successful workflows:

- CI
- DevSecOps Baseline
- Architecture Governance

## Acceptance Criteria

An external evaluation can be considered successful when:

- The framework repository and Pages site are reachable.
- The reviewer can identify the intended public release.
- The quickstart and adoption package are internally consistent.
- The reusable workflow references use stable tags.
- The demo consumer shows successful public workflow runs.
- Limitations are visible and do not imply production readiness without application-specific evidence.

## Findings Template

Use this short template for evaluation notes:

```markdown
# External Evaluation Notes

## Evaluated Version

- Repository:
- Commit or release:
- Date:

## Result

- Repository access:
- Documentation clarity:
- Adoption package usability:
- Baseline references:
- Demo consumer status:
- Open limitations:

## Recommendation

- [ ] Suitable for report-only pilot
- [ ] Suitable for controlled blocking pilot
- [ ] Not ready; blocking issues listed below

## Findings

1.
2.
3.
```

## Boundaries

- This guide does not replace legal, security, or procurement review.
- A successful framework evaluation does not certify an application repository.
- Application teams remain responsible for evidence quality, branch protection, scanner configuration, waiver handling, and release decisions.
