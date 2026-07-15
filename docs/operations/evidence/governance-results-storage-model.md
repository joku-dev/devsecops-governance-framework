# Governance Results Storage Model

## Purpose

This document explains how this repository can hold governance execution results from multiple downstream repositories without turning the repository itself into an unstructured dump of pipeline output.

## Recommended Model

The repository uses a hybrid model:

1. the repository remains the source of truth for governance rules and released baselines
2. normalized result snapshots can be stored under `status/results/`
3. a generated central index summarizes the latest known state across repositories
4. large raw artifacts should remain in GitHub Actions artifacts or another evidence store

## Why This Model Is Useful

This model gives three benefits at the same time:

- auditability through Git history
- a central machine-readable registry of downstream outcomes
- a manageable repository size

## Directory Structure

Results are stored like this:

```text
status/
  repository-results-index.json
  architecture-results-index.json
  results/
    joku-dev__ha-CPsWMS/
      2026-07-02T13-05-30Z-run-28592257991.json
  architecture-results/
    joku-dev__ha-CPsWMS/
      2026-07-02T13-05-12Z-run-28592256765.json
```

## What Goes Into A Result File

Each result file should contain:

- repository identifier
- baseline level
- governance baseline reference
- pipeline run identifier
- commit identifier
- generated timestamp
- overall pass/fail result
- selected normalized evidence flags

## Example

Current examples:

- `status/results/joku-dev__ha-CPsWMS/2026-07-02T13-05-30Z-run-28592257991.json`
- `status/architecture-results/joku-dev__ha-CPsWMS/2026-07-02T13-05-12Z-run-28592256765.json`

## Central Index

The generated index lives here:

- `status/repository-results-index.json`
- `status/architecture-results-index.json`

It contains:

- summary counts
- one latest-result entry per repository
- a pointer to the stored result files

## How To Regenerate The Index

Run:

```bash
python3 scripts/generate_repository_results_index.py
python3 scripts/generate_architecture_results_index.py
```

## Automated GitHub Actions Intake

For downstream GitHub Actions runs, the preferred operational path is:

```bash
python3 scripts/intake_github_actions_run.py \
  --repository-id example-org/example-repo \
  --run-id 123456789
```

This keeps raw artifacts in GitHub Actions while storing only the normalized governance snapshot in Git.

The workflow `.github/workflows/intake-governance-result.yml` wraps this script and can commit the updated result snapshot, central index, and status viewer automatically.

Architecture runtime governance follows the same model with:

```bash
python3 scripts/intake_architecture_github_actions_run.py \
  --repository-id example-org/example-repo \
  --run-id 123456789 \
  --architecture-baseline-ref architecture-baseline-l1-v0.1.0
```

## Step-By-Step For Adding Another Repository Result

### Step 1

Create a repository-specific folder under `status/results/`.

Example:

```bash
mkdir -p status/results/example-org__example-repo
```

### Step 2

Add a normalized JSON result file.

Example file name:

```text
status/results/example-org__example-repo/2026-06-28T12-00-00Z-run-123456789.json
```

### Step 3

Populate the file with the normalized fields used by this repository.

### Step 4

Regenerate the central index:

```bash
python3 scripts/generate_repository_results_index.py
```

### Step 5

Commit the snapshot if the result should become part of the governed audit trail.

## When To Store Results In Git

Store them in Git when:

- they are milestone results
- they are release-relevant
- they are governance-significant
- they need revision protection

## When Not To Store Raw Results In Git

Do not store all raw run artifacts in Git when:

- runs happen very frequently
- raw files are large
- the data is mainly operational rather than audit-relevant

In those cases:

- store raw evidence in GitHub Actions artifacts or object storage
- store only normalized snapshots or summaries in this repository

## Long-Term Evolution

If the number of repositories grows significantly, this repository can continue to keep:

- schemas
- normalization logic
- selected audit snapshots
- generated summary views

while a separate central store can keep:

- all raw run evidence
- long-term historical time series
- dashboards and queries
