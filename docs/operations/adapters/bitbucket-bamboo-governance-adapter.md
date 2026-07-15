# Bitbucket And Bamboo Governance Adapter

## Purpose

This document describes the first concrete adapter path for running the central DevSecOps Governance-as-Code baseline from Bitbucket-hosted application repositories through Bamboo Data Center 12.1.9.

This document is technical implementation and adapter documentation. It is not
a governance document, not a registered source document and not an authority for
new controls, architecture markers, policies, schemas, evidence contracts,
workflows, releases or baselines.

The adapter does not create a separate Bamboo governance system. Bamboo is the execution platform. The governance repository remains the owner of controls, schemas, evidence contracts, OPA policies, architecture markers, reports and release packages.

## Target Version

| Component | Target |
|---|---|
| Bamboo | Data Center 12.1.9 |
| Bamboo configuration model | Bamboo YAML Specs |
| Recommended application repository path | `bamboo-specs/bamboo.yaml` |
| Governance mode at first rollout | `report-only` |
| Blocking mode after evidence stabilization | `block-on-error` or `waiver-required` |

Atlassian documents that Bamboo YAML Specs are processed from repository-stored Specs, and Bamboo looks for YAML Specs before Java Specs. The documented repository path is `bamboo-specs/bamboo.yml` or `bamboo-specs/bamboo.yaml`. Bamboo 12.x also requires Java 21 for server nodes and agents, so the adapter avoids custom Bamboo plugins and uses plain YAML Specs with shell tasks.

## Adapter Files

| File | Purpose |
|---|---|
| `pipeline-baseline/templates/bamboo/bamboo-specs/bamboo.yaml` | Bamboo 12.1.9 DevSecOps baseline reference plan for application repositories. |
| `pipeline-baseline/templates/bamboo/bamboo-specs/architecture-governance.yaml` | Optional architecture runtime governance reference plan. |
| `pipeline-baseline/templates/bamboo/README.md` | Adapter mapping, evidence contract and adoption guidance. |
| `docs/operations/adapters/company-bitbucket-bamboo-mistral-target-path.md` | Wider company target path including Mistral provider adapter. |

The older files under `pipeline-baseline/templates/bamboo/*.yml` remain reference sketches. New Bamboo 12.1.9 adoption should start from `pipeline-baseline/templates/bamboo/bamboo-specs/bamboo.yaml`.

## Execution Model

```text
Bitbucket application repository
  -> bamboo-specs/bamboo.yaml
  -> Bamboo plan on Bamboo Data Center 12.1.9
  -> checkout application source
  -> clone pinned governance repository ref
  -> package application artifact
  -> collect or generate SBOM and vulnerability scan evidence
  -> generate normalized platform context
  -> generate normalized pipeline evidence and baseline gate result
  -> archive Bamboo artifacts
  -> optionally fail build when governance mode is blocking
```

## Required Application Repository Layout

The minimum application repository layout is:

```text
bamboo-specs/bamboo.yaml
```

Recommended evidence input locations are:

```text
security/sbom.cyclonedx.json
security/vulnerability-scan.json
governance/governance-run-input.json
.governance/architecture/*.json
docs/ARCHITECTURE.md
docs/DEPLOYMENT.md
```

If `security/sbom.cyclonedx.json` or `security/vulnerability-scan.json` is missing, the reference plan creates placeholder files. That is acceptable only for first wiring tests. Product repositories should replace placeholders with real tool output before governance checks become blocking.

## Bamboo Variables

The reference plan uses Bamboo variables so each application repository can adopt the same template with minimal edits.

| Variable | Default | Purpose |
|---|---|---|
| `governance.repository` | `https://github.com/joku-dev/devsecops-governance-as-code.git` | Central governance repository URL. Replace with the internal Bitbucket mirror when available. |
| `governance.ref` | `l1-baseline-v1.1.3` | Pinned governance baseline or commit SHA. |
| `governance.mode` | `report-only` | `report-only`, `block-on-error` or `waiver-required`. |
| `governance.max.allowed.severity` | `high` | Maximum vulnerability severity accepted by the starter gate. |
| `governance.branch.protection.status` | `not_implemented_for_bamboo_12_1_9_template` | Explicit placeholder until Bitbucket branch-permission lookup is wired. |
| `bitbucket.protected.branch` | empty | Optional boolean once Bitbucket branch permissions are queried. |
| `bitbucket.direct.push.allowed` | empty | Optional boolean once Bitbucket branch permissions are queried. |
| `bitbucket.review.required` | empty | Optional boolean once Bitbucket merge checks are queried. |

Use `report-only` first. Switch to `block-on-error` only after the repository produces stable evidence and Bitbucket branch-permission lookup is reliable.

## Normalized Evidence Outputs

The Bamboo adapter must archive these artifacts:

```text
dist/application-source.tar.gz
security/sbom.cyclonedx.json
security/vulnerability-scan.json
generated/evidence/platform-context.json
generated/evidence/pipeline-evidence.json
generated/evidence/baseline-gate-result.json
```

Optional architecture outputs:

```text
generated/app/architecture-release-input.json
generated/app/architecture-governance-report.json
generated/app/architecture-governance-report.md
```

These artifacts are intentionally platform-neutral. Central intake should consume the same logical bundle regardless of whether the run came from GitHub Actions, Bamboo, Jenkins or another adapter.

## Bamboo To Normalized Context Mapping

| Normalized field | Bamboo source |
|---|---|
| `source` | `bamboo` |
| `repository_id` | `bamboo_planRepository_repositoryUrl` or configured `bamboo_repository_id` |
| `branch` | `bamboo_planRepository_branchName` |
| `commit_id` | `bamboo_planRepository_revision` |
| `pipeline_id` | `bamboo_planName` |
| `pipeline_run_id` | `bamboo_buildResultKey` or `bamboo_buildNumber` |
| `pipeline_url` | `bamboo_resultsUrl` |
| `event` | `bamboo_buildTriggerReason` |

Bitbucket-specific PR, branch permission and merge-check information should be added as a later API-backed enrichment step. Until then, the adapter must mark the lookup as not implemented instead of claiming that protections passed.

## Rollout Steps

1. Copy `pipeline-baseline/templates/bamboo/bamboo-specs/bamboo.yaml` into the application repository as `bamboo-specs/bamboo.yaml`.
2. Replace `governance.repository` with the internal Bitbucket governance repository URL when available.
3. Pin `governance.ref` to a released baseline tag or reviewed commit SHA.
4. Keep `governance.mode` as `report-only`.
5. Enable repository-stored Bamboo Specs for the Bitbucket repository.
6. Run the Bamboo Specs validator before relying on automatic Specs scans.
7. Execute the plan and confirm that the normalized evidence artifacts are archived.
8. Download the artifact bundle and validate it locally:

```bash
python3 scripts/validate_ci_artifact_bundle.py \
  --type devsecops \
  --bundle path/to/bamboo-artifacts
```

9. Intake the bundle only for accepted mainline runs:

```bash
python3 scripts/intake_ci_artifact_bundle.py \
  --type devsecops \
  --bundle path/to/bamboo-artifacts \
  --repository-id PROJECT/repository \
  --governance-baseline-ref l1-baseline-v1.1.3
```

10. Add Bitbucket branch-permission and merge-check lookup.
11. Replace placeholder SBOM and vulnerability evidence with real scanner outputs.
12. Move selected repositories from `report-only` to `block-on-error` or `waiver-required`.

## Safety Rules

- Do not copy controls, OPA rules or schemas into application repositories.
- Do not use a moving governance ref for governed runs.
- Do not enable blocking mode while placeholder evidence is still used.
- Do not update central latest status from pull request, branch diagnostic or manual test runs.
- Do not claim Bitbucket branch protection unless the adapter has queried Bitbucket or consumed approved policy evidence.
- Do not use a Bamboo plugin for the first adapter unless YAML Specs and script tasks cannot satisfy the requirement.

## Validation Notes

For Bamboo 12.1.9, validate on a real Bamboo instance because YAML Specs validation depends on Bamboo-linked or project-specific repository context. The local repository validation confirms that the template, scripts and docs remain consistent, but it cannot prove that a company Bamboo instance has Specs scanning, linked repositories, agent capabilities and credentials configured correctly.
