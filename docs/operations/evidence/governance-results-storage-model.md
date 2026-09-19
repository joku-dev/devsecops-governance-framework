# Governance Results Storage Model

## Purpose

This document explains how this repository can hold governance execution results from multiple downstream repositories without turning the repository itself into an unstructured dump of pipeline output.

It defines the current pilot storage contract. Measured limits and the
production target for 300 to 1,500 consumers are maintained in the
[Consumer Scale Capacity Assessment](../planning/consumer-scale-capacity-assessment.md).

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

The workflow `.github/workflows/intake-governance-result.yml` wraps this script and proposes updated snapshots, indexes and projections through a scoped bot PR. They become official on protected `main` only after review, required checks and merge.

Architecture runtime governance follows the same model with:

```bash
python3 scripts/intake_architecture_github_actions_run.py \
  --repository-id example-org/example-repo \
  --run-id 123456789 \
  --architecture-baseline-ref architecture-baseline-l1-v0.1.0
```

## Canonical Intake Procedure

Do not create or edit accepted result snapshots and central indexes by hand.
Use the repository intake workflows or the corresponding intake scripts so
that schema validation, repository/run binding, replay handling, provenance,
digests and index regeneration remain consistent. The complete operator
procedure, including retries and review PRs, is maintained in
[Governance Result Intake And Viewer Usage](governance-result-intake-and-viewer-usage.md).

The index generator commands above are useful for deterministic regeneration
and validation after an authorized intake. They are not a substitute for
accepting evidence through the intake boundary.

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

## Production Scale Boundary

At larger portfolio sizes, this repository can continue to keep:

- schemas
- normalization logic
- selected audit snapshots
- generated summary views

while a separate central store can keep:

- all raw run evidence
- long-term historical time series
- dashboards and queries

Queueing, batching, retention, viewer partitioning and intake sharding belong
to the target architecture in the
[Consumer Scale Capacity Assessment](../planning/consumer-scale-capacity-assessment.md).
