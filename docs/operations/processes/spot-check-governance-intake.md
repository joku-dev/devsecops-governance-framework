# Spot Check Strategy for Governance Intake

## Purpose

This document describes a practical spot-check strategy for the governance intake process.
It explains how to verify that downstream governance evidence is real, not simulated, and how to validate the intake pipeline step by step.
It also includes automation ideas that can turn manual spot checks into repeatable verification workflows.

## Why Spot Checks Matter

A governance intake pipeline can appear to work by simply collecting flags or placeholder results.
Spot checks make the evidence concrete by verifying the actual artifacts, metadata, and data integrity of downstream runs.

Spot checks are especially important when:

- a downstream repository claims to have published `governance-control-evaluation` artifacts
- the intake snapshot data is used as trusted history for the central viewer or audit reports
- the pipeline must distinguish real governance evidence from test data, partial artifacts, or stale placeholders

## Spot Check Strategy Overview

The spot check strategy covers three levels:

1. Artifact presence and artifact metadata
2. Evidence file integrity and governance run input consistency
3. Intake snapshot validation and central result propagation

Each step is designed to increase confidence before accepting a downstream result into `status/results/`.

## Step 1: Verify Downstream Artifacts

### What to check

- the downstream run created a `governance-control-evaluation` artifact
- the artifact uploaded successfully and is downloadable
- the artifact contains a `control-evaluation-report.json`
- the repository also delivered `governance-run-input.json` when expected

### How to perform it manually

1. Identify the downstream repository and workflow run ID.
2. Download the artifact using GitHub Actions artifact tooling or `scripts/intake_github_actions_run.py`.
3. Confirm the archive extracts cleanly and the file layout matches expected structure.
4. Confirm the artifact names in the run include `governance-control-evaluation` and optionally `governance-run-input`.

### Why it catches bad cases

This step catches cases where the run claims to be complete but the artifact upload failed, or the artifact is missing the expected JSON payload.

## Step 2: Validate Artifact Metadata and Checksums

### What to check

- the downloaded artifact size is plausible and recorded
- the downloaded `control-evaluation-report.json` has a valid JSON structure
- the governance run input file is present and parseable
- the intake script computes SHA-256 hashes for both files
- the intake result includes artifact metadata and checksum fields

### How the current repo supports this

`docs/operations/processes/spot-check-governance-intake.md` should document that the intake snapshot now stores:

- `artifact_metadata.artifact_names`
- `artifact_metadata.artifact_sizes`
- `downloaded_artifact.control_evaluation_report_sha256`
- `downloaded_artifact.governance_run_input_sha256`

This means the spot-checker can verify not only presence, but also file integrity.

### How to perform it manually

1. Run `python3 scripts/intake_github_actions_run.py ...` for the target downstream run.
2. Inspect the generated `status/results/<repo>/<timestamp>-run-<run-id>.json` file.
3. Verify `artifact_metadata.artifact_sizes` is non-zero and matches the downloaded artifact.
4. Verify `downloaded_artifact.*_sha256` fields exist.
5. Optionally recompute the SHA-256 of the extracted JSON files and compare them to the stored values.

### Why it catches bad cases

Checksums catch cases where the artifact content changed after intake, or where intake claimed to download a file but actually recorded a stub.

## Step 3: Verify Governance Run Input and Evidence Flags

### What to check

- `governance_run_input` exists and is parseable
- evidence flags are derived from actual governance input values, not only from artifact names
- the governance run input contains traceability, operations evidence, SBOM, vulnerability scan, or artifact metadata fields where expected
- evidence status in the result snapshot reflects the actual input payload

### How to perform it manually

1. Inspect the `governance_run_input` section of the intake snapshot.
2. Confirm the presence of `traceability`, `operations`, `evidence`, and `artifact` metadata keys when required.
3. Compare the intake `evidence` flags against the actual run input values.
4. If the downstream workflow published an explicit `governance-run-input` artifact, confirm that artifact is the source of the intake values.

### Why it catches bad cases

This step catches false positives where the intake snapshot reports `governance_run_input: true`, but the actual input file is missing or incomplete.

## Step 4: Review Central Intake Snapshot and Viewer Impact

### What to check

- the snapshot is written under `status/results/<owner>__<repo>/`
- the `absolute_status` and `overall_status` fit the run conclusion and control evaluation summary
- the `pipeline` metadata matches the downstream run URL, branch, commit, and event
- the `notes` field records why the snapshot was accepted
- the viewer or status index is updated only for mainline push results when intended

### How to perform it manually

1. Locate the generated snapshot file in `status/results/`.
2. Confirm the `repository_id`, `baseline_level`, and `governance_baseline_ref` values are correct.
3. Confirm `pipeline.pipeline_url` points to the actual workflow run and `pipeline.status` reflects the run conclusion.
4. Inspect the central viewer or repository index if it was regenerated after intake.

### Why it catches bad cases

This step catches intake normalization errors, wrong repository mapping, or snapshots that were accepted from the wrong branch/event type.

## Example Spot-Check Workflow

1. Identify a downstream mainline governance run that should be ingested.
2. Run the intake script:

```bash
python3 scripts/intake_github_actions_run.py \
  --repository-id joku-dev/ha-CPsWMS \
  --run-id 28314109954 \
  --baseline-level L1 \
  --governance-baseline-ref l1-baseline-v1.1.3 \
  --notes "Spot check: verify actual governance artifact and metadata."
```

3. Open the generated snapshot in `status/results/joku-dev__ha-CPsWMS/`.
4. Verify the downloaded artifact metadata and checksums are present.
5. Recompute checksums locally if needed.
6. Confirm the `governance_run_input` artifact contents match reported evidence flags.
7. Regenerate the viewer if necessary and review the resulting file.

## Automation Ideas

### 1. Automated Spot-Check Job

Create a reusable workflow or job that performs the full spot check automatically for a selected upstream run.
It can:

- call `scripts/intake_github_actions_run.py`
- validate the generated snapshot JSON schema
- compare stored checksums to recomputed checksums
- verify required artifact names and sizes
- fail if any of the checks are missing or inconsistent

### 2. Spot-Check Regression Test

Add a test in `tests/` that simulates a real intake run and validates the new checksum and metadata fields.
This is already supported by the updated `tests/test_intake_github_actions_run.py`.

### 3. Scheduled Spot-Check Sweep

Run a scheduled workflow that selects one or more recent downstream governance runs from each important repository and re-intakes them.
The sweep should verify:

- the artifact is still downloadable
- the checksum metadata remains valid
- the governance run input still exists and is consistent

If any check fails, the workflow should create an issue or alert the governance team.

### 4. Cross-Repository Data Validation

Combine spot checks with a second-level verification job that compares the intake snapshot against the downstream repository state.
For example:

- verify the downstream branch/commit still exists
- verify the run event matches the expected release semantics
- verify the downstream repository owns the claimed artifact names

## Recommended Spot-Check Policy

- perform a manual spot check for every new repository onboarding or baseline intake change
- perform a second manual check whenever the intake logic changes
- automate regular spot checks for critical repositories and mainline intake paths
- treat checksum and artifact metadata validation as mandatory for any accepted intake snapshot

## Summary

Spot checks should not be a one-time audit.
They are a repeatable validation pattern that ensures the governance intake pipeline remains trustworthy.

The key idea is simple:

- confirm the artifact exists
- verify the artifact metadata and file hashes
- validate the governance run input payload
- ensure the central snapshot matches the downstream runtime evidence

When these checks are automated, the repository can detect placeholder evidence, missing artifacts, and intake normalization drift before they reach central status history.
