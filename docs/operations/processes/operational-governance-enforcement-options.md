# Operational Governance Enforcement Options

## Goal

If this repository becomes the enterprise governance baseline, other software repositories must not only know about it, but must actually use it in their CI/CD pipelines.

## Recommended Enforcement Layers

## Repository Governance Modes

Each downstream repository should declare an explicit governance mode in:

- `status/application-repository-integrations.yaml`

Recommended modes:

| Mode | Meaning | Merge behavior |
| --- | --- | --- |
| `readiness` | Repository is being assessed before central workflow integration. | No central merge impact. |
| `report-only` | Central governance workflow runs and records evidence, but is not a required merge gate. | Does not block merge. |
| `warn-on-error` | Governance failures are visible and tracked, but still allow merge during transition. | Does not block merge by default. |
| `block-on-error` | Governance failures block merge or mainline promotion. | Blocks merge. |
| `waiver-required` | Governance failures block unless approved structured waiver evidence exists. | Blocks without waiver. |
| `disabled` | Integration is intentionally paused or disabled with a documented reason. | No active governance signal. |

The mode should be accompanied by structured enforcement flags:

```yaml
governance_mode: report-only
enforcement:
  blocks_merge: false
  records_result: true
  requires_waiver_on_failure: false
  mode_reason: Candidate repository is being onboarded before mainline enforcement.
```

Use `report-only` for new repositories until at least one branch or pull-request run has produced usable evidence. Move to `block-on-error` or `waiver-required` only after the repository has stable evidence generation and an agreed operating model.

Before either blocking mode is introduced, use the stronger report-only
Blocking Readiness assessment and migration runbook:

- `docs/operations/status/blocking-readiness.md`
- `docs/operations/processes/blocking-enforcement-migration-guide.md`

A technically ready result is necessary but not sufficient. Accountable human
approval and a separate consumer-scoped activation change remain mandatory.

The central validator also generates
`generated/reports/blocking-mode-alignment.json`. A new Blocking registration
without both conditions fails validation. Preexisting Blocking can only be
represented by a traceable, time-bounded risk record that predates the model;
such a record is not an approval.

### 1. Shared Pipeline Template

The strongest operational pattern is to provide a central CI template and require teams to import it.

Examples:

- `templates/ci/github-actions-governance-check.yml`
- `templates/ci/gitlab-ci-governance-check.yml`

### 2. Standardized Compliance Artifact

Each target repository should produce a machine-readable result file such as:

- `governance-compliance-result.json`

The schema for that result is defined in:

- `schemas/governance-compliance-result.schema.json`

An example is provided in:

- `docs/examples/governance-compliance-result.example.json`
- `docs/examples/governance-compliance-result.extended.example.json`

An extended result can be generated with:

```bash
python3 scripts/generate_governance_compliance_result.py \
  --target-repo /path/to/target-repo \
  --input-file /path/to/release-candidate.json \
  --output-file governance-compliance-result.json
```

### 3. Integration Scanner

This repository provides a scanner script that can check whether a target repository appears to use the governance pipeline integration:

```bash
python3 scripts/check_repo_governance_integration.py \
  --target-repo /path/to/target-repo \
  --output-file governance-compliance-result.json
```

### 4. Required Status Checks

If GitHub or GitLab is used, the governance job should be configured as a required merge condition.

That means:

- no merge to `main` without a successful governance check
- no silent bypass of the governance stage

### 5. Standardized Waiver Evidence

If a repository needs an exception, it should not pass ad hoc waiver text through comments or ticket links alone.

Instead, it should provide a structured waiver record using the standard format described in:

- `schemas/waiver.schema.json`
- `docs/operations/processes/waiver-management-standard.md`

This makes it possible to check:

- whether an expiry date exists
- whether an approver is named
- whether a justification exists
- whether compensating controls are documented

## Practical Rollout Sequence

1. publish the central pipeline template
2. make target repositories consume the template
3. make target repositories produce a standardized compliance result
4. make target repositories use standardized waiver evidence where exceptions are needed
5. make the governance check a required merge gate
6. later build central compliance monitoring across repositories
