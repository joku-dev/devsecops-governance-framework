# GitHub Actions Reference Mapping

This folder contains GitHub Actions templates for consuming the public DevSecOps Governance Framework from application repositories.

The workflow is intentionally minimal. It shows where baseline checks belong, not a complete enterprise implementation.

## Templates

| Workflow | Purpose |
|---|---|
| `devsecops-baseline.yml` | Minimal application-repository workflow that calls the public L1 DevSecOps baseline. |
| `architecture-governance.yml` | Runs the architecture runtime governance collector and OPA readiness policies against an application repository. |
| `app-repo-architecture-governance.yml` | Minimal copy-paste workflow for application repositories. |

See `docs/onboarding/public-repo-quickstart.md` and `ADOPTION.md` for application repository onboarding guidance.

## Architecture Governance Workflow

`architecture-governance.yml` is intended to be copied into an application repository, for example:

```text
.github/workflows/architecture-governance.yml
```

The workflow checks out the application repository, checks out this governance repository as tooling, generates an architecture release-readiness input, validates it against the schema and evaluates the architecture readiness, integration readiness, operation readiness and release readiness policies.

By default, release-readiness findings are reported but do not fail the workflow. Set `fail_on_release_findings` to `"true"` for blocking behavior.
