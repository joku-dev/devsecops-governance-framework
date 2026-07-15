# External Review Brief

## Purpose

This brief gives reviewers, colleagues and application teams a short, neutral overview of the public DevSecOps Governance Framework and how to evaluate it.

The framework is intended to help application repositories consume shared governance baselines through CI/CD without copying governance logic into every repository.

## What The Framework Provides

| Capability | Description |
| --- | --- |
| Reusable DevSecOps baseline | Application repositories can call the public `L1` DevSecOps baseline from GitHub Actions. |
| Reusable architecture baseline | Application repositories can call the public Architecture `L1` baseline for runtime governance checks. |
| Evidence model | Pipelines produce machine-readable evidence for artifacts, SBOM, vulnerability scans, repository controls and architecture evidence. |
| Report-only adoption | Teams can start with visibility before switching to blocking governance. |
| Copyable adoption package | The `adoption-package/` folder contains workflows, evidence examples and a first-adoption checklist. |
| Public documentation | GitHub Pages publishes quickstarts, release notes, onboarding guides and a status viewer. |

## Current Validation State

The public release `v0.1.0-public-adoption` has been validated with:

- repository model validation,
- runtime governance validation,
- regression tests,
- strict MkDocs build,
- public Pages publishing,
- a neutral public demo consumer repository.

Validated public consumer:

```text
https://github.com/joku-dev/governance-framework-demo-consumer
```

The demo consumer successfully runs:

| Workflow | Result |
| --- | --- |
| CI | `success` |
| DevSecOps Baseline | `success` |
| Architecture Governance | `success` |

## How An Application Team Starts

1. Open the public quickstart.
2. Copy the DevSecOps workflow from `adoption-package/workflows/devsecops-baseline.yml`.
3. Keep the first runs in `report-only`.
4. Replace placeholder evidence with real tool output.
5. Review generated findings and artifacts.
6. Add architecture governance if runtime architecture evidence is in scope.
7. Move to blocking mode only after branch protection and evidence quality are stable.

## Review Entry Points

| Question | Start here |
| --- | --- |
| What is the fastest way to try it? | `docs/onboarding/public-repo-quickstart.md` |
| What files can I copy? | `adoption-package/README.md` |
| Has a clean consumer been validated? | `docs/onboarding/validated-demo-consumer.md` |
| What release should I evaluate? | `docs/releases/v0.1.0-public-adoption.md` |
| What does the viewer show? | `generated/viewer/status-viewer.html` |

## Boundaries And Known Limitations

- The first adoption path is intentionally `report-only`.
- Placeholder SBOM and vulnerability examples are not production evidence.
- Draft architecture evidence is not approved release evidence.
- Downstream repositories remain responsible for branch protection, review rules, scanner configuration and release decisions.
- Historical documents may describe older internal or baseline history; current public adoption starts with `v0.1.0-public-adoption`.

## Evaluation Recommendation

Use the neutral demo consumer first. Then apply the adoption package to one non-critical application repository in `report-only` mode. After findings are understood and evidence generation is stable, decide whether selected checks should become required branch-protection checks.
