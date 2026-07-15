# Pipeline Baseline

## Purpose

This section explains how downstream repositories are expected to consume the governance baseline through CI/CD workflows.

It is the operational home for:

- reusable workflow understanding
- required pipeline evidence
- baseline workflow inputs
- downstream integration examples

## Current Consumer Entry Points

The most important current files are:

- `.github/workflows/devsecops-baseline-reusable.yml`
- `.github/workflows/devsecops-baseline-l1-v1.0.0.yml`
- `.github/workflows/devsecops-baseline-l1-v1.1.0.yml`
- `.github/workflows/devsecops-baseline-l1-v1.1.1.yml`
- `.github/workflows/devsecops-baseline-l1-v1.1.2.yml`
- `.github/workflows/devsecops-baseline-l1-v1.1.3.yml`
- `releases/l1/v1.0.0/examples/github-actions/devsecops-baseline-l1-v1.0.0.yml`
- `releases/l1/v1.1.0/examples/github-actions/devsecops-baseline-l1-v1.1.0.yml`
- `releases/l1/v1.1.1/examples/github-actions/devsecops-baseline-l1-v1.1.1.yml`
- `releases/l1/v1.1.2/examples/github-actions/devsecops-baseline-l1-v1.1.2.yml`
- `releases/l1/v1.1.3/examples/github-actions/devsecops-baseline-l1-v1.1.3.yml`
- `docs/onboarding/application-repo-onboarding.md`
- `docs/onboarding/how-other-repositories-use-the-central-governance-baseline.md`
- `docs/operations/evidence/governance-evidence-contract.md`

## Two Workflow Layers

There are currently two important workflow layers.

### Layer 1: Generic Reusable Workflow

File:

- `.github/workflows/devsecops-baseline-reusable.yml`

Purpose:

- contains the actual reusable governance gate logic
- supports multiple levels through the `level` input
- collects and evaluates normalized pipeline evidence

This is the technical enforcement engine.

### Layer 2: Released L1 Wrapper

File:

- `.github/workflows/devsecops-baseline-l1-v1.1.3.yml`

Purpose:

- provides a release-stable `L1` consumer entrypoint
- fixes the level to `L1`
- allows downstream repositories to consume a released baseline instead of `main`

This is the revision-protected downstream interface.

## Why Two Layers Exist

The two-layer model solves two different needs:

- the central repository needs one flexible reusable engine
- downstream repositories need one stable released entrypoint

Without the release wrapper, downstream repositories would often point directly to:

- `main`
- or an internal reusable workflow commit

That would make controlled baseline consumption harder to govern.

## Current Recommended Consumer Reference

Downstream repositories should use:

- `joku-dev/devsecops-governance-as-code/.github/workflows/devsecops-baseline-l1-v1.1.3.yml@l1-baseline-v1.1.3`

This is the recommended revision-safe reference for the current released `L1` baseline.

Earlier release path:

- `v1.0.0` introduced the first revision-protected `L1` wrapper.
- `v1.1.0` added the optional `governance_run_input_path` consumer input.
- `v1.1.1` corrected the `v1.1.0` wrapper packaging defect.
- `v1.1.2` completed the corrected governance run input rollout.
- `v1.1.3` added explicit run-context handling for release, pull-request, branch-validation, and diagnostic runs.

Older releases remain documented for traceability and historical audits.

## What The Pipeline Must Produce

A downstream repository must usually provide:

- a build or source artifact
- an SBOM
- a vulnerability scan result
- a GitHub Actions artifact bundle containing those files

These files are used by the baseline workflow as governance evidence.

## Core Inputs Of The Released L1 Workflow

Important inputs include:

- `artifact_path`
- `sbom_path`
- `vulnerability_scan_path`
- `governance_run_input_path`
- `application_evidence_artifact_name`
- `max_allowed_severity`
- `release_candidate`
- `upload_evidence`

## Step-By-Step: How Another Repository Uses The Baseline

### Step 1

The repository creates or collects the required evidence files.

Typical examples:

- `dist/example-app.txt`
- `security/sbom.cyclonedx.json`
- `security/vulnerability-scan.json`

### Step 2

The repository uploads those files as a GitHub Actions artifact.

Typical artifact name:

- `application-evidence`

### Step 3

The repository calls the released `L1` workflow.

Example:

```yaml
jobs:
  devsecops-baseline-l1:
    name: Central DevSecOps L1 Baseline
    needs: prepare-devsecops-evidence
    uses: joku-dev/devsecops-governance-as-code/.github/workflows/devsecops-baseline-l1-v1.1.3.yml@l1-baseline-v1.1.3
    with:
      artifact_path: dist/example-app.txt
      sbom_path: security/sbom.cyclonedx.json
      vulnerability_scan_path: security/vulnerability-scan.json
      application_evidence_artifact_name: application-evidence
```

### Step 4

The reusable baseline gate downloads the evidence and evaluates it.

### Step 5

The pipeline either:

- passes
- or fails with governance-relevant reasons

## Step-By-Step: Read The Current Example

Open the current released downstream example:

```bash
sed -n '1,220p' releases/l1/v1.1.3/examples/github-actions/devsecops-baseline-l1-v1.1.3.yml
```

Then inspect the versioned wrapper:

```bash
sed -n '1,220p' .github/workflows/devsecops-baseline-l1-v1.1.3.yml
```

Then inspect the generic reusable engine:

```bash
sed -n '1,360p' .github/workflows/devsecops-baseline-reusable.yml
```

## What The Baseline Gate Actually Checks

At a practical level, the gate checks things like:

- pipeline identity
- artifact existence
- digest existence
- SBOM existence
- vulnerability scan existence
- vulnerability threshold compliance
- branch governance context
- direct push expectations

Some requirements are stricter at higher levels such as `L2` or `L3`.

## Example Operational Meaning

### Example: Protected Branches

If the governance context shows that direct pushes are still allowed where they should not be, the gate fails.

### Example: Missing SBOM

If the expected SBOM file is missing, the gate fails.

### Example: Vulnerability Threshold Exceeded

If the reported maximum severity is above the allowed threshold, the gate fails unless an approved waiver model allows otherwise.

## Placeholder Evidence Versus Real Evidence

For technical onboarding, placeholder evidence may be enough to prove the workflow wiring.

But operationally, the repository should move to real evidence such as:

- real SBOM generation
- real vulnerability scanning
- real build artifacts

This distinction is important:

- placeholder evidence proves integration
- real evidence proves governance execution

## How This Connects To Releases

The pipeline baseline should be consumed through released workflow entrypoints whenever possible.

Current released entrypoint:

- `.github/workflows/devsecops-baseline-l1-v1.1.3.yml`

Current release tag:

- `l1-baseline-v1.1.3`

Current consumer example:

- `releases/l1/v1.1.3/examples/github-actions/devsecops-baseline-l1-v1.1.3.yml`

## How This Connects To Results Storage

Successful or governance-significant downstream outcomes can later be normalized into:

- `status/results/`
- `status/repository-results-index.json`

This creates a central record of which downstream repositories passed which baseline and when.

## Recommended Reading Order

1. `docs/onboarding/application-repo-onboarding.md`
2. `docs/onboarding/how-other-repositories-use-the-central-governance-baseline.md`
3. `releases/l1/v1.1.3/examples/github-actions/devsecops-baseline-l1-v1.1.3.yml`
4. `.github/workflows/devsecops-baseline-l1-v1.1.3.yml`
5. `.github/workflows/devsecops-baseline-reusable.yml`

## Recommended Next Document

After this page, read:

- `docs/operations/evidence/governance-results-storage-model.md`

That document explains how downstream results can be brought back into the central repository in a normalized way.
