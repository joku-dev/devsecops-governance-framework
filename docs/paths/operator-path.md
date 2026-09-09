# Operator Path

For current pilot and central operations, start with the
[operations handbook](../operations/guides/governance-repository-operations-handbook.md).
It links the [daily report](../operations/status/daily-governance-operations.md),
[access maintenance](../operations/security/github-access-and-token-maintenance.md),
and [backup and recovery](../operations/processes/governance-repository-backup-and-recovery.md).
Dated reference runs and released documentation remain historical evidence.

## Who This Is For

Use this path if you are integrating or operating the governance baseline in a downstream application or platform repository.

## Goal

After following this path, you should understand:

- how to onboard a repository
- which evidence must be produced
- how governance runs are interpreted
- how results flow back into the central viewer

## Recommended Reading Order

### Step 1: Understand Consumer Onboarding

- `docs/onboarding/application-repo-onboarding.md`
- `docs/onboarding/how-other-repos-use-this-governance-repo.md`

### Step 2: Understand The Reusable Baseline

- `docs/releases/l1-baseline-v1.1.3.md`
- `releases/l1/v1.1.3/examples/github-actions/devsecops-baseline-l1-v1.1.3.yml`

### Step 3: Understand Evidence Requirements

- `docs/operations/evidence/governance-evidence-contract.md`
- `docs/operations/evidence/governance-evidence-schema-versioning.md`
- `docs/examples/governance-run-input.example.json`

### Step 4: Understand Run Evaluation

- `docs/operations/evidence/how-to-read-control-evaluation-status.md`
- `docs/operations/status/current-governance-platform-state.md`

### Step 5: Understand Result Intake And History

- `docs/operations/evidence/governance-result-intake-and-viewer-usage.md`
- `docs/operations/evidence/governance-results-storage-model.md`

## Operational Questions This Path Answers

- what do we have to upload as evidence
- how do we pin a governance baseline release
- how do we interpret pass, fail, not tested, and not applicable
- how do we record results centrally
