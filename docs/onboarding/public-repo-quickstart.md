# Public Repository Quickstart

## Purpose

This quickstart shows how an application repository can consume the public DevSecOps Governance Framework without copying governance logic into the application repository.

Use this repository as the central baseline:

```text
joku-dev/devsecops-governance-framework
```

The application repository remains responsible for building its own artifact, producing evidence, and deciding when governance should become blocking.

## Recommended Adoption Path

1. Start with `report-only` on pull requests and manual runs.
2. Keep `block-on-error` only for protected `main` release or integration runs.
3. Upload evidence as GitHub Actions artifacts.
4. Review generated reports before making the workflow a required check.
5. Replace placeholder evidence with real SBOM, vulnerability, static-analysis, traceability, and architecture evidence.

## Minimal DevSecOps Baseline Workflow

Create this file in the application repository:

```text
.github/workflows/devsecops-baseline.yml
```

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
  prepare-evidence:
    name: Prepare Evidence
    runs-on: ubuntu-latest
    steps:
      - name: Checkout application repository
        uses: actions/checkout@v4

      - name: Build artifact and evidence
        run: |
          mkdir -p dist security governance
          echo "replace with real build output" > dist/application-artifact.txt

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

          cat > governance/governance-run-input.json <<'JSON'
          {
            "release_candidate": true,
            "required_platform_level": "PRA-Level 1"
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
            governance/governance-run-input.json

  devsecops-baseline:
    name: Central DevSecOps Baseline
    needs: prepare-evidence
    uses: joku-dev/devsecops-governance-framework/.github/workflows/devsecops-baseline-l1-v1.1.3.yml@l1-baseline-v1.1.3
    with:
      governance_mode: ${{ github.event_name == 'push' && github.ref == 'refs/heads/main' && 'block-on-error' || 'report-only' }}
      max_allowed_severity: high
      artifact_path: dist/application-artifact.txt
      sbom_path: security/sbom.cyclonedx.json
      vulnerability_scan_path: security/vulnerability-scan.json
      governance_run_input_path: governance/governance-run-input.json
      application_evidence_artifact_name: application-evidence
      generate_demo_evidence: false
```

## Minimal Architecture Governance Workflow

Create this file in the application repository when architecture runtime evidence should also be evaluated:

```text
.github/workflows/architecture-governance.yml
```

```yaml
name: Architecture Governance

on:
  pull_request:
  push:
    branches:
      - main
  workflow_dispatch:

permissions:
  contents: read

jobs:
  architecture-governance:
    name: Architecture L1 Baseline
    uses: joku-dev/devsecops-governance-framework/.github/workflows/architecture-baseline-l1-v0.1.0.yml@architecture-baseline-l1-v0.1.0
    with:
      release_id: ${{ github.sha }}
      solution_baseline: demo-solution-baseline
      application_path: .
      upload_evidence: true
      fail_on_findings: false
```

## Evidence Files

The first DevSecOps baseline run needs these files in the uploaded `application-evidence` artifact:

| File | Purpose |
| --- | --- |
| `dist/application-artifact.txt` | Build artifact or package metadata. |
| `security/sbom.cyclonedx.json` | Machine-readable SBOM. |
| `security/vulnerability-scan.json` | Vulnerability scan summary with `max_severity`. |
| `governance/governance-run-input.json` | Optional structured control-evaluation input. |

For production adoption, replace placeholders with real tool output.

## Expected Result

A successful first integration should produce:

- `application-evidence`
- `devsecops-pipeline-evidence`
- optional architecture governance evidence
- a GitHub Actions job summary with governance status

Pull requests should normally run `report-only` first. After evidence is stable and branch protection is configured, make the baseline a required check and keep `block-on-error` for `main`.

## Working Reference

The `joku-dev/ha-CPsWMS` repository is the current working reference consumer. Its governance workflows demonstrate the public baseline consumption pattern.
