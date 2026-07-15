# Application Repo Onboarding For DevSecOps Baseline

This guide explains how an application team connects its repository to the central DevSecOps governance baseline.

## Target Model

The governance repository owns the baseline logic.
The application repository only produces evidence and calls the central baseline.

```text
Application repository
  build artifact
  SBOM
  vulnerability scan result
  pipeline metadata

Governance repository
  central reusable workflow
  control baseline
  evidence validation
  gate decision
```

Do not copy the full governance repository into application repositories.

## What Every Application Repository Must Provide

Each application repository must provide these evidence files during CI/CD:

| Evidence | Default Path | Purpose |
|---|---|---|
| Build or source artifact | `dist/application-source.tar.gz` | Object that is checked and released |
| SBOM | `security/sbom.cyclonedx.json` | Software bill of materials |
| Vulnerability scan result | `security/vulnerability-scan.json` | Machine-readable security scan result |

The exact paths may be changed, but they must match the values passed to the central baseline workflow.

## Required Application Repo Change

Each application repository needs one workflow file:

```text
.github/workflows/devsecops-baseline.yml
```

This workflow must:

1. Build or package the application artifact.
2. Generate or provide SBOM evidence.
3. Generate or provide vulnerability scan evidence.
4. Upload the evidence as a GitHub Actions artifact.
5. Call the central reusable DevSecOps baseline workflow.

## Minimal Workflow Template

Use this for the first integration test:

```yaml
name: DevSecOps Baseline

on:
  pull_request:
  push:
    branches:
      - main
  workflow_dispatch:

permissions:
  contents: read
  actions: read
  pull-requests: read

jobs:
  prepare-devsecops-evidence:
    name: Prepare DevSecOps Evidence
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Build source artifact
        run: |
          mkdir -p dist security
          tar --exclude='.git' -czf dist/application-source.tar.gz .

      - name: Generate placeholder SBOM
        run: |
          cat > security/sbom.cyclonedx.json <<'JSON'
          {
            "bomFormat": "CycloneDX",
            "specVersion": "1.5",
            "version": 1,
            "components": []
          }
          JSON

      - name: Generate placeholder vulnerability scan
        run: |
          cat > security/vulnerability-scan.json <<'JSON'
          {
            "scanner": "placeholder",
            "max_severity": "none",
            "findings": []
          }
          JSON

      - name: Upload application evidence
        uses: actions/upload-artifact@v4
        with:
          name: application-evidence
          path: |
            dist/application-source.tar.gz
            security/sbom.cyclonedx.json
            security/vulnerability-scan.json

  devsecops-baseline:
    name: Central DevSecOps Baseline
    needs: prepare-devsecops-evidence
    uses: joku-dev/devsecops-governance-framework/.github/workflows/devsecops-baseline-l1-v1.1.3.yml@l1-baseline-v1.1.3
    with:
      level: L1
      max_allowed_severity: high
      artifact_path: dist/application-source.tar.gz
      sbom_path: security/sbom.cyclonedx.json
      vulnerability_scan_path: security/vulnerability-scan.json
      application_evidence_artifact_name: application-evidence
      generate_demo_evidence: false
      signature_path: ''
```

## Step-By-Step Onboarding

### Step 1: Create A Branch

In the application repository:

```bash
git checkout -b devsecops/add-baseline-gate
```

### Step 2: Add The Workflow

Create:

```text
.github/workflows/devsecops-baseline.yml
```

Use the minimal workflow template above.

If the repository also wants to provide richer machine-readable governance evidence, start from:

- `examples/github-actions/workflows/application-devsecops-baseline-with-governance-input-template.yml`

### Step 3: Adjust Artifact Paths

Decide what the repository should provide as the application artifact.

Examples:

| Repository Type | Suggested Artifact |
|---|---|
| Python service | `dist/application-source.tar.gz` or built wheel |
| Docker service | image digest evidence plus source bundle |
| Java service | built JAR/WAR |
| Node.js service | package tarball or build output |
| Infrastructure repo | rendered IaC package or validated plan |

Update:

```yaml
artifact_path: dist/application-source.tar.gz
```

### Step 4: Run The Workflow

Open a pull request against the protected target branch.

Expected jobs:

```text
prepare-devsecops-evidence
devsecops-baseline
```

Both jobs must pass.

### Step 5: Inspect Evidence

Open the GitHub Actions run and download:

```text
application-evidence
devsecops-pipeline-evidence
```

The key output is:

```text
generated/evidence/pipeline-evidence.json
```

This file is the machine-readable compliance evidence for the pipeline run.

If the repository wants richer control coverage beyond the default pipeline evidence, it should also generate:

```text
governance/governance-run-input.json
```

The official contract for that file is defined in:

- `docs/operations/evidence/governance-evidence-contract.md`
- `schemas/governance-run-input.schema.json`
- `docs/examples/governance-run-input.example.json`

### Step 6: Replace Placeholders

The placeholder SBOM and vulnerability scan are allowed only for initial technical onboarding.

Replace them with approved tools.

Recommended examples:

| Evidence | Tool Examples |
|---|---|
| SBOM | Syft, CycloneDX, Trivy SBOM, build-system SBOM |
| Vulnerability scan | Trivy, Grype, CodeQL, Snyk, GitHub Dependabot |
| Artifact signing | cosign, Sigstore, internal signing service |

### Step 7: Make It A Required Check

After the workflow is stable:

1. Go to the application repository settings.
2. Open branch protection rules for `main`.
3. Require pull request checks.
4. Add `Central DevSecOps Baseline` as required status check.

Do this only after the workflow has been green on multiple pull requests.

## Definition Of Done For L1 Onboarding

An application repository is onboarded to L1 when:

| Check | Required |
|---|---|
| `.github/workflows/devsecops-baseline.yml` exists | yes |
| Application artifact is generated | yes |
| SBOM evidence is generated | yes |
| Vulnerability scan evidence is generated | yes |
| Central baseline workflow is called | yes |
| `generated/evidence/pipeline-evidence.json` is uploaded | yes |
| DevSecOps baseline job passes on pull requests | yes |

## What Not To Do

Do not:

- copy the complete governance repository into application repositories
- let every team invent different evidence names and paths
- use placeholder scans as permanent compliance evidence
- enable L2 or L3 before L1 is stable
- make the check mandatory before the workflow is proven on real pull requests

## Common Problems

| Problem | Likely Cause | Fix |
|---|---|---|
| Reusable workflow cannot be found | Governance repo unavailable or wrong path | Check the pinned `uses:` reference to the governance workflow |
| Baseline job cannot find artifact | Artifact paths do not match workflow inputs | Align uploaded artifact paths with `artifact_path`, `sbom_path`, and `vulnerability_scan_path` |
| Vulnerability gate fails | Scan result severity exceeds threshold | Fix findings or use an approved waiver process |
| L2 fails on branch protection | Target branch is not protected or pull request reviews are not enforced | Enable branch protection and required PR reviews before moving to L2 |
| L2 fails because direct push status is unknown | Workflow could not read branch protection details | Confirm the repository exposes branch protection metadata to Actions and retry |
| L3 fails on signature | Artifact signature missing | Generate a signature file and pass `signature_path` before enabling L3 |

## Rollout Recommendation

Use this rollout order:

1. Pilot one repository with L1.
2. Replace placeholder evidence with real SBOM and vulnerability tooling.
3. Stabilize the workflow on several pull requests.
4. Make the baseline check required for the pilot repository.
5. Roll out the same pattern to additional repositories.
6. Only then increase strictness to L2 and L3.

## Ownership

| Responsibility | Owner |
|---|---|
| Central baseline workflow | DevSecOps governance team |
| Evidence generation in application repo | Application team |
| Tool selection and approved scanners | DevSecOps governance team |
| Fixing findings | Application team |
| Waiver approval | Defined waiver authority |
| Required check enforcement | Repository owner with governance approval |

## Pinning Requirement

Application repositories should pin the reusable governance workflow to a release tag or a commit SHA.

Recommended example:

```yaml
uses: joku-dev/devsecops-governance-framework/.github/workflows/devsecops-baseline-l1-v1.1.3.yml@l1-baseline-v1.1.3
```

Do not use `@main` for long-lived production onboarding because the effective governance gate could change without review in the application repository.
