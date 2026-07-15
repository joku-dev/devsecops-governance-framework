# Architecture Governance Adoption

## Purpose

This guide explains how an application repository can run the architecture runtime governance collector and OPA policies from this governance repository.

The application repository does not need to vendor the governance logic. It only needs a GitHub Actions workflow that checks out:

1. the application repository
2. this governance repository

The workflow then generates architecture evidence, evaluates readiness gates and uploads the report as a workflow artifact.

## Quick Start

Copy this file into the application repository:

```text
pipeline-baseline/templates/github-actions/app-repo-architecture-governance.yml
```

Target location in the application repository:

```text
.github/workflows/architecture-governance.yml
```

Then run the workflow manually through `workflow_dispatch`, or let it run on pull requests and pushes to `main`.

## What The Workflow Produces

The workflow generates:

| Artifact | Purpose |
|---|---|
| `architecture-release-input.json` | Machine-readable evidence input collected from the application repository. |
| `architecture-governance-report.json` | Machine-readable gate result report. |
| `architecture-governance-report.md` | Human-readable Markdown report for demo, review and GitHub Step Summary. |

## Optional App-Repo Evidence

To close findings deliberately, an application repository can add structured evidence files under:

```text
.governance/architecture/
```

Starter templates are available in:

```text
pipeline-baseline/templates/app-architecture-evidence/.governance/architecture/
```

The collector reads these files and treats `status: approved` as verified governance evidence.

## Gates

The generated report evaluates:

| Gate | Meaning |
|---|---|
| Architecture Readiness | Is the repository sufficiently described, owned and traceable? |
| Integration Readiness | Are interfaces, schemas, tests and deployment evidence sufficient for integration? |
| Operation Readiness | Is runtime/feedback evidence mature enough for operation governance? |
| Release Readiness | Is the repository ready for governed release against a solution baseline? |

## Demo Behavior

For early adoption, the workflow reports findings but does not fail the build.

This is intentional. The first goal is visibility:

- what evidence exists
- what evidence is missing
- which architecture markers are mature enough
- which governance gaps must be closed before release

Blocking behavior can be added later by failing the workflow when release-readiness findings exist.

## Recommended First Target

Use `ha-CPsWMS` as the first application repository demo target.

Expected current result:

```text
Architecture Readiness: PASS
Integration Readiness: PASS
Operation Readiness: FINDINGS
Release Readiness: FINDINGS
```

This creates a useful demo story: the target repository is good enough for architecture and integration work, but still needs stronger operation and release evidence before it is governed-release-ready.

## Configuration

Update these values in the copied workflow as needed:

| Field | Default | Meaning |
|---|---|---|
| `repository` | `joku-dev/devsecops-governance-framework` | Governance repository containing policies and scripts. |
| `ref` | `architecture-baseline-l1-v0.1.0` | Governance branch/tag/SHA to use. |
| `--baseline` | `app-demo-baseline` | Solution baseline identifier expected for release compatibility. |

For stable demos, use a fixed governance tag. For production use, prefer a released version tag or pinned commit SHA.
