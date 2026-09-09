# Maintainer Path

For current pilot and central operations, start with the
[operations handbook](../operations/guides/governance-repository-operations-handbook.md).
It links the [daily report](../operations/status/daily-governance-operations.md),
[access maintenance](../operations/security/github-access-and-token-maintenance.md),
and [backup and recovery](../operations/processes/governance-repository-backup-and-recovery.md).
Dated reference runs and released documentation remain historical evidence.

## Who This Is For

Use this path if you maintain the governance repository itself.

## Goal

After following this path, you should understand:

- how source documents propagate into controls and releases
- how to change the evidence contract safely
- how to prepare and publish releases
- how to keep the repository validated and reviewable

## Recommended Reading Order

### Step 1: Understand The Source Of Truth

- `docs/governance/source-of-truth.md`
- `docs/governance/operating-model.md`
- `docs/operations/guides/how-to-use-this-repo.md`

### Step 2: Understand Change Propagation

- `docs/operations/guides/how-to-update-baseline-input-documents.md`
- `docs/governance/policy-directive-baseline-verification-and-governance-as-code-explained.md`

### Step 3: Understand Schema And Evidence Evolution

- `docs/operations/evidence/governance-evidence-contract.md`
- `docs/operations/evidence/governance-evidence-schema-versioning.md`
- `schemas/governance-run-input.schema.json`

### Step 4: Understand Release Discipline

- `docs/releases/release-and-migration-model.md`
- `docs/releases/release-publication-checklist.md`
- `.github/pull_request_template.md`
- `.github/CODEOWNERS`

### Step 5: Understand Operational Outputs

- `docs/operations/evidence/governance-result-intake-and-viewer-usage.md`
- `docs/operations/status/current-governance-platform-state.md`
- `docs/operations/guides/mkdocs-and-github-pages-step-by-step.md`

## Maintainer Responsibilities Supported By This Path

- updating Policy and Directive inputs
- updating controls and traceability
- evolving schemas and workflows
- publishing revision-safe releases
- maintaining documentation quality
