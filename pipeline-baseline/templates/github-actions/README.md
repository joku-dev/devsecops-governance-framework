# GitHub Actions Reference Mapping

This folder contains a tool-specific sketch for implementing the tool-agnostic CI/CD Pipeline Control Baseline in GitHub Actions.

The workflow is intentionally minimal. It shows where baseline checks belong, not a complete enterprise implementation.

## Templates

| Workflow | Purpose |
|---|---|
| `devsecops-baseline.yml` | Sketches where DevSecOps pipeline baseline checks belong. |
| `architecture-governance.yml` | Runs the architecture runtime governance collector and OPA readiness policies against an application repository. |
| `app-repo-architecture-governance.yml` | Minimal copy-paste workflow for application repositories. |

See `ADOPTION.md` for application repository onboarding guidance.

## Architecture Governance Workflow

`architecture-governance.yml` is intended to be copied into an application repository, for example:

```text
.github/workflows/architecture-governance.yml
```

The workflow checks out the application repository, checks out this governance repository as tooling, generates an architecture release-readiness input, validates it against the schema and evaluates the architecture readiness, integration readiness, operation readiness and release readiness policies.

By default, release-readiness findings are reported but do not fail the workflow. Set `fail_on_release_findings` to `"true"` for blocking behavior.
