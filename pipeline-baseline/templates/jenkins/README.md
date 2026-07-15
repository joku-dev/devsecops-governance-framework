# Jenkins Reference Mapping

This folder contains a Jenkins-oriented reference mapping for the tool-agnostic CI/CD Pipeline Control Baseline.

The Jenkins path should use the same governance evidence contracts as GitHub Actions, Bamboo and GitLab CI.

## Target Model

```text
Application repository
        |
        v
Jenkinsfile
        |
        v
Evidence files and generated JSON reports
        |
        v
Archived Jenkins artifacts
        |
        v
Optional central intake into the governance repository
```

## Jenkins Variable Mapping

| Normalized field | Jenkins source |
|---|---|
| `repository_id` | `GIT_URL` parsed or configured variable |
| `branch` | `BRANCH_NAME` |
| `commit_id` | `GIT_COMMIT` |
| `pipeline_run_id` | `BUILD_TAG` or `BUILD_NUMBER` |
| `pipeline_url` | `BUILD_URL` |
| `event` | `CHANGE_ID`, branch build or manual build context |
| `status` | Jenkins build result |

## Recommended Evidence Artifacts

Archive at least:

```text
generated/evidence/pipeline-evidence.json
generated/evidence/baseline-gate-result.json
dist/application-source.tar.gz
security/sbom.cyclonedx.json
security/vulnerability-scan.json
```

For architecture governance, archive:

```text
generated/app/architecture-release-input.json
generated/app/architecture-governance-report.json
generated/app/architecture-governance-report.md
```

## Templates

| File | Purpose |
|---|---|
| `Jenkinsfile` | DevSecOps pipeline evidence reference pipeline. |
| `ArchitectureJenkinsfile` | Architecture Runtime Governance reference pipeline. |

## Implementation Notes

Use Jenkins stages to mirror the platform-neutral baseline stages:

1. Code checks
2. Controlled build
3. Test and security gates
4. Package and evidence
5. Governance evaluation
6. Release decision

For Bitbucket-hosted repositories, Jenkins should publish build status back to Bitbucket after the gate result is known.

Keep gate enforcement configurable during onboarding. Start in report-only mode, then switch to blocking once evidence quality is stable.

The reference Jenkinsfile calls the shared generator:

```bash
python3 scripts/generate_platform_context.py --platform jenkins
python3 scripts/generate_pipeline_evidence.py --platform jenkins
```

The architecture Jenkinsfile uses the shared architecture collector and report generator:

```bash
python3 governance/scripts/collect_architecture_release_input.py
python3 governance/scripts/generate_architecture_governance_report.py
```

## Central Intake

Before a Jenkins REST API adapter exists, archive or download Jenkins artifacts and intake them through the platform-neutral bundle reader:

```bash
python3 scripts/validate_ci_artifact_bundle.py \
  --type devsecops \
  --bundle path/to/jenkins-artifacts

python3 scripts/intake_ci_artifact_bundle.py \
  --type devsecops \
  --bundle path/to/jenkins-artifacts \
  --repository-id PROJECT/repository \
  --governance-baseline-ref l1-baseline-v1.1.3
```

For architecture artifacts:

```bash
python3 scripts/validate_ci_artifact_bundle.py \
  --type architecture \
  --bundle path/to/jenkins-architecture-artifacts

python3 scripts/intake_ci_artifact_bundle.py \
  --type architecture \
  --bundle path/to/jenkins-architecture-artifacts \
  --repository-id PROJECT/repository \
  --architecture-baseline-ref architecture-baseline-l1-v0.1.0
```
