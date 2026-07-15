# DevSecOps Governance Framework

This documentation space is the entry point for the public DevSecOps Governance Framework: reusable DevSecOps and architecture governance baselines, machine-readable evidence, released baselines, onboarding guidance, and CI/CD platform integration.

Application repositories can consume this framework from CI/CD without copying the governance logic into every project.

## Role-Based Paths

- Start with `lesekompass.md` if you are new and want the shortest route through the repository.
- Start with `paths/index.md` if you want a guided route by role.
- New readers should use `paths/beginner-path.md`.
- Operators should use `paths/operator-path.md`.
- Auditors should use `paths/auditor-path.md`.
- Maintainers should use `paths/maintainer-path.md`.

## Start Here

- If you want a quick reading compass for new team members, read `lesekompass.md`.
- If you want the official entrypoint overview, read `official-entrypoints.md`.
- If you are reviewing the public adoption state, begin with `onboarding/external-review-brief.md`.
- If you want to try it in an application repository, begin with `onboarding/public-repo-quickstart.md`.
- If you want a validated neutral example, read `onboarding/validated-demo-consumer.md`.
- If you want the operational flow, read `operations/guides/beginner-step-by-step-operations-guide.md`.
- If you want the downstream evidence contract, read `operations/evidence/governance-evidence-contract.md`.
- If you want to change upstream governance documents safely, read `operations/guides/how-to-update-baseline-input-documents.md`.
- If you want the evidence contract evolution rules, read `operations/evidence/governance-evidence-schema-versioning.md`.
- If you want the formal waiver standard, read `operations/processes/waiver-management-standard.md`.
- If you want to record downstream runs and understand the viewer, read `operations/evidence/governance-result-intake-and-viewer-usage.md`.
- If you want the current overall situation, read `operations/status/current-governance-platform-state.md`.
- If you want a concrete rollout retrospective, read `operations/status/ha-cpswms-governance-lessons-learned.md`.
- If you want the documentation publishing flow, read `operations/guides/mkdocs-and-github-pages-step-by-step.md`.
- If you want the governance logic, read `governance/policy-directive-baseline-verification-and-governance-as-code-explained.md`.
- If you want the platform relationship, read `platform/control-baseline-and-platform-architecture-relationship-explained.md`.
- If you want the release gate checklist, read `releases/release-publication-checklist.md`.
- If you want the control automation status and prioritization, read `controls/index.md`.
- If you want the CI/CD adapter strategy, read `operations/adapters/cicd-platform-adapter-strategy.md`.

## Documentation Areas

- `governance/` explains Policy, Directive, source-of-truth, and governance operating model.
- `onboarding/` explains how application repositories consume this baseline.
- `operations/` explains validation, generation, and day-to-day usage.
- `operations/` also explains change control, evidence evolution, and result intake.
- `platform/` explains how platform architecture implements baseline controls.
- `pipeline-baseline/` contains reusable CI/CD baseline guidance and related release-facing workflow documentation.
- `operations/adapters/cicd-platform-adapter-strategy.md` explains how the governance core can be used from GitHub Actions, Bamboo/Bitbucket, Jenkins, and GitLab CI.
- `releases/` contains published baseline package documentation.
- `.github/` contains collaboration guardrails such as workflow automation, PR structure, and ownership rules.

## Repository Model

- `model/` is the machine-readable governance source of truth.
- `generated/` contains rendered documents, reports, and the static status viewer.
- `policies/opa/` contains executable policy rules for automated checks.
- `.github/workflows/` contains repo validation and reusable pipeline workflow automation.
