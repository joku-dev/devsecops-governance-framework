# Bamboo And Bitbucket Reference Mapping

This folder contains a Bamboo-oriented reference mapping for the tool-agnostic CI/CD Pipeline Control Baseline.

The current target version is Bamboo Data Center 12.1.9. New application-repository adoption should start from the repository-stored YAML Specs template under:

```text
pipeline-baseline/templates/bamboo/bamboo-specs/bamboo.yaml
```

When copied into an application repository, use the Bamboo-documented location:

```text
bamboo-specs/bamboo.yaml
```

The goal is not to fork the governance logic. Bamboo should run the same evidence collection, OPA policy evaluation and report generation commands as the GitHub Actions path.

## Target Model

```text
Bitbucket repository
        |
        v
Bamboo plan
        |
        v
Evidence files and generated JSON reports
        |
        v
Bamboo artifacts
        |
        v
Optional central intake into the governance repository
```

## Required Evidence

Minimum DevSecOps evidence:

```text
dist/application-source.tar.gz
security/sbom.cyclonedx.json
security/vulnerability-scan.json
generated/evidence/pipeline-evidence.json
generated/evidence/baseline-gate-result.json
```

Optional governance evidence:

```text
governance/governance-run-input.json
generated/control-evaluation-report.json
```

Architecture evidence:

```text
.governance/architecture/*.json
generated/app/architecture-release-input.json
generated/app/architecture-governance-report.json
generated/app/architecture-governance-report.md
```

## Templates

| File | Purpose |
|---|---|
| `bamboo-specs/bamboo.yaml` | Bamboo 12.1.9 DevSecOps baseline reference plan for application repositories. |
| `bamboo-specs/architecture-governance.yaml` | Optional Bamboo 12.1.9 architecture runtime governance reference plan. |
| `bamboo-specs.yml` | DevSecOps pipeline evidence reference plan. |
| `architecture-governance-bamboo-specs.yml` | Architecture Runtime Governance reference plan. |

The root-level `*.yml` files are retained as early sketches. Prefer the nested `bamboo-specs/*.yaml` templates for new Bamboo 12.1.9 work.

## Bamboo Variable Mapping

| Normalized field | Bamboo or Bitbucket source |
|---|---|
| `repository_id` | Bamboo linked repository or configured variable |
| `branch` | `bamboo.planRepository.branchName` |
| `commit_id` | `bamboo.planRepository.revision` |
| `pipeline_run_id` | `bamboo.buildResultKey` |
| `pipeline_url` | Bamboo result URL |
| `event` | Bamboo trigger reason or configured variable |
| `status` | Bamboo build result state |

## First Implementation Notes

The initial Bamboo 12.1.9 template is intentionally non-blocking and should be adapted to the local Bamboo Specs setup used by the organization.

Recommended first step:

1. Build the application artifact.
2. Generate SBOM and vulnerability scan.
3. Generate normalized pipeline evidence JSON.
4. Archive all evidence as Bamboo artifacts.
5. Add blocking behavior only after the evidence quality is stable.

The reference Specs sketch calls the shared generator:

```bash
python3 governance/scripts/generate_platform_context.py --platform bamboo
python3 governance/scripts/generate_pipeline_evidence.py --platform bamboo
```

The architecture Specs sketch uses the shared architecture collector and report generator:

```bash
python3 governance/scripts/collect_architecture_release_input.py
python3 governance/scripts/generate_architecture_governance_report.py
```

## Bamboo 12.1.9 Adoption Notes

Use repository-stored YAML Specs and avoid a custom Bamboo plugin for the first integration. Bamboo 12.x requires Java 21 for server nodes and agents; a YAML Specs plus shell-task adapter keeps the governance integration independent from Bamboo plugin APIs, app signing and Java package migration concerns.

The recommended DevSecOps plan:

1. Checks out the Bitbucket application repository.
2. Clones the central governance repository at a pinned ref.
3. Packages the application source.
4. Uses real SBOM and vulnerability scan evidence where available.
5. Generates `platform-context.json`, `pipeline-evidence.json` and `baseline-gate-result.json`.
6. Archives evidence as Bamboo artifacts.
7. Fails only when `governance.mode` is changed from `report-only` to a blocking mode.

For detailed adoption guidance, see:

```text
docs/operations/adapters/bitbucket-bamboo-governance-adapter.md
```

## Bitbucket Responsibilities

Bitbucket should provide:

- repository and branch identity
- pull request metadata where available
- branch permissions or merge-check context
- build status publication target

Where Bitbucket API access is not available, the adapter should mark the lookup status explicitly instead of pretending the check passed.

## Central Intake

Before a Bamboo REST API adapter exists, export or download the Bamboo artifacts and intake them through the platform-neutral bundle reader:

```bash
python3 scripts/validate_ci_artifact_bundle.py \
  --type devsecops \
  --bundle path/to/bamboo-artifacts

python3 scripts/intake_ci_artifact_bundle.py \
  --type devsecops \
  --bundle path/to/bamboo-artifacts \
  --repository-id PROJECT/repository \
  --governance-baseline-ref l1-baseline-v1.1.3
```

For architecture artifacts:

```bash
python3 scripts/validate_ci_artifact_bundle.py \
  --type architecture \
  --bundle path/to/bamboo-architecture-artifacts

python3 scripts/intake_ci_artifact_bundle.py \
  --type architecture \
  --bundle path/to/bamboo-architecture-artifacts \
  --repository-id PROJECT/repository \
  --architecture-baseline-ref architecture-baseline-l1-v0.1.0
```
