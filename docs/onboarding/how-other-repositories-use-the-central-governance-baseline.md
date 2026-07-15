# How To Use The Central Governance Baseline

## Purpose

This guide explains step by step how another application repository can use the central repository `joku-dev/devsecops-governance-as-code`.

The goal is to help repository owners integrate a shared DevSecOps baseline without copying the governance repository into every project.

## What The Central Governance Repository Does

The central governance repository provides:

- the reusable GitHub Actions governance workflow
- the baseline decision logic
- the evidence model
- the machine-readable pipeline evidence format

Application repositories remain responsible for producing their own evidence and calling the central baseline.

## What The Application Repository Must Do

Each application repository must:

1. build or package an application artifact
2. generate or provide an SBOM
3. generate or provide vulnerability scan evidence
4. upload the evidence as a GitHub Actions artifact
5. call the reusable governance workflow from the central repository

## Step-By-Step Instructions

### Step 1: Open The Application Repository

Go to the repository that should be governed.

Examples:

- `my-org/my-service`
- `my-org/my-frontend`
- `my-org/my-data-pipeline`

## Step 2: Create A Workflow File

Create this file in the application repository:

```text
.github/workflows/devsecops-baseline.yml
```

This file is the connection point between the application repository and the central governance repository.

## Step 3: Add The Baseline Workflow

Use the following structure:

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

jobs:
  prepare-devsecops-evidence:
    name: Prepare DevSecOps Evidence
    runs-on: ubuntu-latest

    steps:
      - name: Checkout
        uses: actions/checkout@v4

      - name: Build artifact and evidence
        run: |
          mkdir -p dist security
          echo "replace this with a real artifact build" > dist/application-artifact.txt

          cat > security/sbom.cyclonedx.json <<'JSON'
          {
            "bomFormat": "CycloneDX",
            "specVersion": "1.5",
            "version": 1,
            "components": []
          }
          JSON

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
            dist/application-artifact.txt
            security/sbom.cyclonedx.json
            security/vulnerability-scan.json

  devsecops-baseline:
    name: Central DevSecOps Baseline
    needs: prepare-devsecops-evidence
    uses: joku-dev/devsecops-governance-as-code/.github/workflows/devsecops-baseline-reusable.yml@528bee5fd067ab7f65c3030863ca338e0553cfdf
    with:
      level: L1
      max_allowed_severity: high
      artifact_path: dist/application-artifact.txt
      sbom_path: security/sbom.cyclonedx.json
      vulnerability_scan_path: security/vulnerability-scan.json
      application_evidence_artifact_name: application-evidence
      generate_demo_evidence: false
```

If the repository also wants to provide the official governance run input contract, use the richer template in:

- `examples/github-actions/workflows/application-devsecops-baseline-with-governance-input-template.yml`

## Step 4: Replace The Placeholder Artifact

The example above uses a simple placeholder file.

Replace it with the real output of the application repository.

Examples:

- Python service: wheel, source package, or build output
- Java service: JAR or WAR
- Node.js service: build output or package artifact
- Docker-based service: source bundle or signed image metadata
- Infrastructure repository: validated plan or rendered package

The important rule is:

- the artifact path in the workflow must match the uploaded artifact path

## Step 5: Replace The Placeholder SBOM

The placeholder SBOM is enough for the first technical test, but not for long-term operational governance.

Replace it with a real SBOM generator.

Typical tools:

- Syft
- CycloneDX generators
- Trivy SBOM
- build-system-native SBOM tooling

The output should remain machine-readable and should still be uploaded to:

```text
security/sbom.cyclonedx.json
```

or to another path that is passed correctly via `sbom_path`.

## Step 6: Replace The Placeholder Vulnerability Scan

The example scan file is only for initial onboarding.

Replace it with a real scanner.

Typical tools:

- Trivy
- Grype
- CodeQL
- Snyk
- GitHub Dependabot-based export

The output should remain machine-readable and should still be uploaded to:

```text
security/vulnerability-scan.json
```

or to another path that is passed correctly via `vulnerability_scan_path`.

## Step 7: Commit And Push The Workflow

Commit the workflow file into the application repository.

Example:

```bash
git checkout -b devsecops/add-baseline
git add .github/workflows/devsecops-baseline.yml
git commit -m "Add DevSecOps baseline workflow"
git push origin devsecops/add-baseline
```

## Step 8: Open A Pull Request

Open a pull request against the main branch.

This should trigger the workflow automatically.

Expected jobs:

- `Prepare DevSecOps Evidence`
- `Central DevSecOps Baseline`

## Step 9: Inspect The Workflow Result

Go to GitHub Actions and open the workflow run.

If the integration works, both jobs should be green.

You should also see these artifacts:

- `application-evidence`
- `devsecops-pipeline-evidence`

## Step 10: Review The Machine-Readable Governance Evidence

Download the artifact:

```text
devsecops-pipeline-evidence
```

Inside it, inspect:

```text
generated/evidence/pipeline-evidence.json
```

This file is the central machine-readable proof that the governance baseline was executed.

If the application repository wants richer control-level evaluation, it can additionally produce:

```text
governance/governance-run-input.json
```

That payload should follow:

- `docs/operations/evidence/governance-evidence-contract.md`
- `schemas/governance-run-input.schema.json`
- `docs/examples/governance-run-input.example.json`

## Step 11: Interpret The Result

For a successful L1 integration, you usually want to see:

- pipeline status is `success`
- security gates are enforced
- an artifact exists
- an SBOM exists
- a vulnerability scan evidence file exists
- no waiver is needed
- no threshold exceedance is reported

## Step 12: Make The Check Operational

Once the workflow is stable, make it part of normal repository operations.

Recommended next actions:

1. require the baseline workflow in pull requests
2. stop using placeholder SBOM generation
3. stop using placeholder vulnerability scan evidence
4. define who reviews failures
5. define who can approve exceptions

## Step 13: Move To Higher Maturity Levels Later

L1 is the initial integration level.

Higher levels require more controls.

Typical next steps:

- L2: branch protection and review enforcement
- L3: artifact signing and stronger release controls

Do not move to higher levels before L1 is stable.

## Common Mistakes

Do not:

- copy the full governance repository into the application repository
- use `@main` for the reusable governance workflow in long-lived setups
- leave placeholder evidence in place forever
- upload evidence under paths that do not match the workflow inputs
- assume a green run means L2 or L3 are automatically satisfied

## Recommended Operational Pattern

Use this model:

1. application repository produces evidence
2. application repository uploads evidence
3. application repository calls central governance workflow
4. central governance repository evaluates the evidence
5. GitHub Actions stores machine-readable compliance evidence

## Example Outcome Statement

After a successful run, an application repository can state:

> This repository has successfully executed the central DevSecOps baseline and produced machine-readable pipeline evidence for the evaluated commit.

## References

- Central governance repository: `joku-dev/devsecops-governance-as-code`
- Onboarding guide in this repository: `docs/onboarding/application-repo-onboarding.md`
- Example application repository workflow: `examples/github-actions/workflows/application-devsecops-baseline-template.yml`
