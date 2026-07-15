# CI/CD Platform Adapter Strategy

This document defines how the governance baseline can run across multiple CI/CD platforms without rewriting the governance core for every tool.

The target platforms are:

- GitHub Actions
- Bitbucket and Bamboo
- Jenkins
- GitLab CI

For the concrete company target path with Bitbucket, Bamboo, and Mistral, see:

```text
docs/operations/adapters/company-bitbucket-bamboo-mistral-target-path.md
```

## Goal

The governance system should keep one platform-neutral core and expose platform-specific adapters around it.

The platform-neutral core owns:

- evidence contracts
- JSON schemas
- OPA/Rego policies
- Python collectors and report generators
- DevSecOps and architecture baseline rules
- normalized result snapshots
- documentation and MkDocs publication

The platform adapters own:

- CI syntax
- environment variable mapping
- artifact upload and download
- branch and pull request metadata lookup
- build status publication
- result intake from platform APIs

## Design Principle

Do not copy governance logic into every CI/CD tool.

Each platform should do only three things:

1. Produce or collect evidence.
2. Call the shared governance scripts.
3. Publish artifacts and build status in the platform-native way.

```text
Application repository
        |
        v
Platform adapter
  GitHub Actions / Bamboo / Jenkins / GitLab CI
        |
        v
Platform-neutral governance core
  schemas, collectors, OPA policies, report generators
        |
        v
Normalized JSON evidence and reports
```

## Current GitHub-Specific Surfaces

The current implementation is strongest for GitHub Actions. The following areas are platform-specific:

| Area | Current GitHub implementation | Adapter responsibility |
|---|---|---|
| Pipeline entrypoint | `.github/workflows/*.yml` | Provide equivalent Bamboo, Jenkins and GitLab entrypoints. |
| Reuse model | `workflow_call` reusable workflows | Provide shared scripts, Bamboo Specs, Jenkins shared library or copy-paste templates. |
| Artifacts | `actions/upload-artifact` and `actions/download-artifact` | Map to platform artifact archive and retrieval APIs. |
| Run metadata | `GITHUB_RUN_ID`, `GITHUB_SHA`, `GITHUB_EVENT_NAME` | Map platform variables to normalized metadata. |
| Repository metadata | GitHub repository and branch APIs | Map Bitbucket, Bamboo or Jenkins SCM metadata APIs. |
| Branch protection | GitHub Branch Protection API | Map Bitbucket Branch Permissions, merge checks or Jenkins SCM policy evidence. |
| Pull request metadata | GitHub PR context | Map Bitbucket PR context or Jenkins multibranch PR metadata. |
| Result intake | `intake_github_actions_run.py` | Add Bamboo and Jenkins intake adapters. |
| Status reporting | GitHub Checks and Actions status | Map to Bitbucket Build Status, Bamboo build result and Jenkins build result. |

## Platform-Neutral Evidence Model

All platforms should produce the same logical evidence, even if the platform-specific mechanics differ.

The shared starter generator for DevSecOps pipeline evidence is:

```text
scripts/generate_pipeline_evidence.py
```

It maps native CI variables for supported platforms into the normalized evidence shape and writes:

```text
generated/evidence/pipeline-evidence.json
generated/evidence/baseline-gate-result.json
```

Adapters can generate the normalized platform metadata separately with:

```text
scripts/generate_platform_context.py
```

The output path is:

```text
generated/evidence/platform-context.json
```

The schema is:

```text
schemas/platform-context.schema.json
```

### DevSecOps Evidence

Minimum evidence:

```text
dist/application-source.tar.gz
security/sbom.cyclonedx.json
security/vulnerability-scan.json
generated/evidence/pipeline-evidence.json
generated/evidence/baseline-gate-result.json
```

Optional richer evidence:

```text
governance/governance-run-input.json
generated/evidence/governance-run-input.json
generated/control-evaluation-report.json
```

### Architecture Evidence

Minimum architecture evidence:

```text
.governance/architecture/*.json
docs/ARCHITECTURE.md
docs/DEPLOYMENT.md
```

Generated outputs:

```text
generated/app/architecture-release-input.json
generated/app/architecture-governance-report.json
generated/app/architecture-governance-report.md
```

## Normalized Metadata Contract

Every platform adapter should map native CI variables into a normalized metadata shape.

| Normalized field | GitHub Actions | Bamboo | Jenkins |
|---|---|---|---|
| `repository_id` | `GITHUB_REPOSITORY` | Bitbucket project/repository slug or Bamboo linked repository | `GIT_URL` parsed or configured repository ID |
| `branch` | `GITHUB_REF_NAME` or PR base ref | `bamboo.planRepository.branchName` | `BRANCH_NAME` |
| `commit_id` | `GITHUB_SHA` | `bamboo.planRepository.revision` | `GIT_COMMIT` |
| `pipeline_run_id` | `GITHUB_RUN_ID` | `bamboo.buildResultKey` | `BUILD_TAG` or `BUILD_NUMBER` |
| `pipeline_url` | Actions run URL | Bamboo result URL | `BUILD_URL` |
| `event` | `push`, `pull_request`, `workflow_dispatch` | repository trigger, manual, scheduled | branch build, PR build, manual |
| `status` | job conclusion | Bamboo result state | Jenkins build result |

Adapters may write this metadata into an intermediate file before the shared governance scripts create the final JSON.

Recommended intermediate path:

```text
generated/evidence/platform-context.json
```

## Adapter Structure

Recommended repository structure:

```text
pipeline-baseline/templates/
  github-actions/
  bamboo/
  jenkins/
  gitlab-ci/

scripts/intake/
  github_actions.py
  bamboo.py
  jenkins.py

scripts/platform/
  github_actions_context.py
  bamboo_context.py
  jenkins_context.py
```

The existing GitHub intake scripts can remain where they are until shared helper modules are introduced. The first goal is to avoid breaking the current GitHub path.

## Bitbucket Pipelines Adapter

### Responsibility

The Bitbucket Pipelines adapter should:

- generate normalized platform context from Bitbucket environment variables
- produce the same pipeline evidence and gate result JSON as other adapters
- archive evidence as Bitbucket artifacts
- remain report-only until branch restrictions and merge checks are wired in

Reference files:

```text
pipeline-baseline/templates/bitbucket/README.md
pipeline-baseline/templates/bitbucket/bitbucket-pipelines.yml
```

The initial template uses `not_implemented_for_bitbucket_template` for branch restriction lookup until Bitbucket API integration is added.

## Bitbucket and Bamboo Adapter

### Responsibility

The Bamboo adapter should:

- check out the Bitbucket repository
- build or package the application artifact
- generate SBOM and vulnerability scan
- generate or copy `governance/governance-run-input.json`
- run the shared DevSecOps collector or equivalent script
- run architecture collection and OPA gates when enabled
- publish artifacts as Bamboo plan artifacts
- publish build status back to Bitbucket

### Required Platform Mapping

| Need | Bamboo or Bitbucket source |
|---|---|
| Commit ID | Bamboo linked repository revision |
| Branch | Bamboo linked repository branch |
| Build URL | Bamboo build result URL |
| Build number | Bamboo build number or result key |
| Pull request metadata | Bitbucket PR API or Bamboo variables from PR trigger |
| Branch permissions | Bitbucket Branch Permissions API |
| Merge checks | Bitbucket API or documented project policy |
| Artifacts | Bamboo artifact definitions |

### First Bamboo Deliverables

Initial deliverables should be:

- `pipeline-baseline/templates/bamboo/README.md`
- `pipeline-baseline/templates/bamboo/bamboo-specs/bamboo.yaml`
- documented variable mapping
- a non-blocking evidence generation example

For Bamboo Data Center 12.1.9, the recommended application repository path is:

```text
bamboo-specs/bamboo.yaml
```

See:

```text
docs/operations/adapters/bitbucket-bamboo-governance-adapter.md
```

## Jenkins Adapter

### Responsibility

The Jenkins adapter should:

- run the same shell or Python governance commands as other platforms
- archive generated evidence with `archiveArtifacts`
- publish test or gate result status through Jenkins build result
- optionally publish build status to Bitbucket
- support Jenkins multibranch pipelines

### Required Platform Mapping

| Need | Jenkins source |
|---|---|
| Commit ID | `GIT_COMMIT` |
| Branch | `BRANCH_NAME` |
| Build URL | `BUILD_URL` |
| Build number | `BUILD_NUMBER` |
| Job name | `JOB_NAME` |
| Pull request ID | `CHANGE_ID` |
| Pull request target | `CHANGE_TARGET` |
| Repository URL | `GIT_URL` |

### First Jenkins Deliverables

Initial deliverables should be:

- strengthen `pipeline-baseline/templates/jenkins/Jenkinsfile`
- add `pipeline-baseline/templates/jenkins/README.md`
- archive the same evidence files as GitHub and Bamboo
- keep gate enforcement configurable

## Intake Strategy

The current result intake is GitHub-specific:

```text
scripts/intake_github_actions_run.py
scripts/intake_architecture_github_actions_run.py
```

The target state is adapter-specific intake with a shared normalized writer.

```text
Platform API
        |
        v
Adapter intake
  GitHub / Bamboo / Jenkins
        |
        v
Normalized result snapshot
  status/results/...
  status/architecture-results/...
```

### Bamboo Intake

The Bamboo intake should:

- read Bamboo build result metadata
- download or locate Bamboo artifacts
- read `pipeline-evidence.json`, `baseline-gate-result.json`, `architecture-release-input.json` or `architecture-governance-report.json`
- read Bitbucket branch permissions when a token is available
- write the same normalized `status/results/...json` or `status/architecture-results/...json`

As an initial API-independent path, Bamboo can export or download a build artifact bundle and pass it to:

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

### Jenkins Intake

The Jenkins intake should:

- read Jenkins build metadata through the Jenkins API or a provided build artifact bundle
- download archived artifacts
- read the same generated JSON files
- optionally query Bitbucket for branch permission context
- write the same normalized status snapshots

As an initial API-independent path, Jenkins can archive or download a build artifact bundle and pass it to:

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

## Migration Plan

### Phase 1: Strategy and Templates

Deliver:

- adapter strategy documentation
- Bamboo template skeleton
- Jenkins template documentation
- no changes to the existing GitHub path

### Phase 2: Platform Context Normalization

Deliver:

- `platform-context.json` convention
- shared helper for normalizing CI metadata
- GitHub path still compatible

### Phase 3: Bamboo DevSecOps Adapter

Deliver:

- Bamboo DevSecOps baseline template
- Bamboo artifact publishing
- Bamboo/Bitbucket metadata mapping
- first Bamboo evidence bundle

### Phase 4: Jenkins DevSecOps Adapter

Deliver:

- Jenkinsfile with real evidence collection
- archived artifacts
- optional Bitbucket build status publication

### Phase 5: Architecture Adapter Support

Deliver:

- Bamboo architecture governance steps
- Jenkins architecture governance steps
- same `architecture-governance-evidence` artifact contents

Initial reference templates:

```text
pipeline-baseline/templates/bamboo/architecture-governance-bamboo-specs.yml
pipeline-baseline/templates/jenkins/ArchitectureJenkinsfile
```

For new Bamboo 12.1.9 architecture work, prefer:

```text
pipeline-baseline/templates/bamboo/bamboo-specs/architecture-governance.yaml
```

### Phase 6: Intake Adapters

Deliver:

- Bamboo result intake
- Jenkins result intake
- shared snapshot writer

## Non-Goals For The First Branch

The first adapter branch should not:

- rewrite existing GitHub Actions workflows
- move all scripts into a new package
- introduce a new runtime service
- make Bamboo or Jenkins blocking by default
- change released baseline semantics

## Acceptance Criteria

The first branch is useful when:

- the platform-neutral core is clearly separated from platform adapters
- GitHub remains unchanged and green
- Bamboo has a documented starter template
- Jenkins has a documented target path
- future intake adapters have a clear normalized output contract

## Decision

Use a platform adapter model.

Do not create separate governance implementations per CI/CD tool.

The governance core remains shared. CI/CD tools provide thin adapters for execution, metadata, artifacts and status publication.
