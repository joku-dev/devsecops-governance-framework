# How Other Repositories Use This Governance Repo

## Recommended GitHub Integration

An application repository produces its own build and evidence and calls the
released reusable governance workflows. It does not need to clone the whole
governance repository in an application-authored job for the standard GitHub
integration; the reusable implementation obtains the governance code it needs.

Start with the [public quickstart](public-repo-quickstart.md) and the current
reviewed `adoption-package/`. Use the released DevSecOps and Architecture
references, with explicit report-only pilot inputs. Record the template commit
separately from the baseline release pin.

## Responsibilities And Flow

| Application repository | Central governance repository |
|---|---|
| Build application artifacts | Maintain controls, policy, schemas and released baselines |
| Generate real SBOM, scan and context evidence | Evaluate the contracted evidence through reusable workflows |
| Own findings and release decisions | Normalize results and preserve provenance/history |
| Review application PRs | Review operational intake PRs and publish accepted state |

The end-to-end path is:

1. Application workflow uploads evidence and calls the pinned baseline.
2. The baseline produces reports and machine-readable artifacts.
3. The application team reviews findings even when report-only CI succeeds.
4. A central manual intake or configured producer dispatch collects a result.
5. The collector creates a reviewed bot PR; merge updates official indexes and
   the published viewer. Branch/manual contexts cannot replace an available
   official mainline result.
6. The daily operating report identifies stale evidence, execution problems,
   review backlog and security observation gaps.

See [intake and viewer usage](../operations/evidence/governance-result-intake-and-viewer-usage.md)
and the [operations handbook](../operations/guides/governance-repository-operations-handbook.md).

## Other Platforms And Local Evaluation

For Bamboo, Jenkins, GitLab or a local evaluation, an adapter may explicitly
obtain a reviewed governance checkout or released package. Pin the intended
revision, validate evidence contracts and use the matching platform adapter.
This is an alternate integration method, not a requirement for the standard
GitHub reusable-workflow path.

Read the [adapter strategy](../operations/adapters/cicd-platform-adapter-strategy.md)
for platform-specific capabilities and limitations. Copying rules into each
application would create independently maintained policy copies and is not the
recommended consumption model.

## Adoption And Enforcement

New pilots remain report-only for all trigger types. Stable integration and
green jobs alone do not authorize blocking. Follow the
[pilot runbook](pilot-runbook.md) and, only after readiness and accountable
approval, the [blocking migration procedure](../operations/processes/blocking-enforcement-migration-guide.md).
Historical release examples and existing consumer exceptions are not new-pilot defaults.
