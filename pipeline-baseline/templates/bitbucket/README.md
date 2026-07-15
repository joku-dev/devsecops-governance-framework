# Bitbucket Pipelines Reference Mapping

This folder contains a Bitbucket Pipelines reference mapping for the tool-agnostic CI/CD Pipeline Control Baseline.

The Bitbucket path must use the same governance evidence contracts as GitHub Actions, Bamboo, Jenkins and GitLab CI. It is an adapter, not a fork of the governance core.

## Target Model

```text
Bitbucket repository
        |
        v
bitbucket-pipelines.yml
        |
        v
Evidence files and generated JSON reports
        |
        v
Bitbucket artifacts
        |
        v
Optional central intake into the governance repository
```

## Bitbucket Variable Mapping

| Normalized field | Bitbucket Pipelines source |
|---|---|
| `repository_id` | `BITBUCKET_REPO_FULL_NAME` or `BITBUCKET_WORKSPACE/BITBUCKET_REPO_SLUG` |
| `branch` | `BITBUCKET_BRANCH` or `BITBUCKET_PR_DESTINATION_BRANCH` |
| `commit_id` | `BITBUCKET_COMMIT` |
| `pipeline_id` | `BITBUCKET_PIPELINE_UUID` |
| `pipeline_run_id` | `BITBUCKET_BUILD_NUMBER` |
| `pipeline_url` | `BITBUCKET_PIPELINE_URL` when provided |
| `event` | `pull_request` when `BITBUCKET_PR_ID` exists, otherwise `branch_build` |

## Required Evidence

Archive at least:

```text
generated/evidence/platform-context.json
generated/evidence/pipeline-evidence.json
generated/evidence/baseline-gate-result.json
generated/app/architecture-release-input.json
generated/app/architecture-governance-report.json
generated/app/architecture-governance-report.md
dist/application-source.tar.gz
security/sbom.cyclonedx.json
security/vulnerability-scan.json
```

When architecture governance is enabled, `generated/app/architecture-release-input.json` may contain:

```text
architecture.detailed_evidence
```

Bitbucket Pipelines should archive this JSON as-is. It does not need custom logic for individual detailed evidence types.

## Reference Template

| File | Purpose |
|---|---|
| `bitbucket-pipelines.yml` | DevSecOps pipeline evidence reference pipeline. |

## Agent System Reference Note

This README can be used as a low-risk path to exercise the governance agent routing for company platform adapters.

Changing this documentation does not change Bitbucket pipeline behavior, evidence semantics, release baselines, OPA policies, schemas, or enforcement mode. It should still route through the platform-adapter governance review path because the file lives under:

```text
pipeline-baseline/templates/bitbucket/
```

The expected governance agents are:

```text
devsecops-baseline
release-manager
repo-steward
```

## Implementation Notes

Start in `report-only` mode. Switch to blocking only when the evidence quality is stable and branch restrictions or merge checks are configured.

The reference template calls:

```bash
python3 scripts/generate_platform_context.py --platform bitbucket-pipelines
python3 scripts/generate_pipeline_evidence.py --platform bitbucket-pipelines
```

Bitbucket branch restrictions and merge checks should be translated into the normalized evidence fields when API access is available. Until then, use an explicit lookup status such as:

```text
not_implemented_for_bitbucket_template
```

## Central Intake

Before a Bitbucket REST API adapter exists, download pipeline artifacts and intake them through the platform-neutral bundle reader:

```bash
python3 scripts/validate_ci_artifact_bundle.py \
  --type devsecops \
  --bundle path/to/bitbucket-artifacts

python3 scripts/intake_ci_artifact_bundle.py \
  --type devsecops \
  --bundle path/to/bitbucket-artifacts \
  --repository-id WORKSPACE/repository \
  --governance-baseline-ref l1-baseline-v1.1.3
```
