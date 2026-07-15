# Governance Evidence Contract

## Purpose

This document defines the official machine-readable input contract that downstream repositories can provide when they want to produce richer governance control evaluation results.

It explains:

- what the governance run input file is
- where it should live in an application repository
- which sections are required
- which sections are optional but recommended
- which controls these sections help evaluate

## Official Schema

The official schema for the governance run input is:

- `schemas/governance-run-input.schema.json`

An example payload is provided in:

- `docs/examples/governance-run-input.example.json`

The contract also supports an explicit schema marker:

- `contract_version`

Current value:

- `1.0`

## Recommended Consumer Path

A downstream repository should normally generate:

- `governance/governance-run-input.json`

This file is then uploaded together with the other governance evidence artifacts.

Typical baseline evidence bundle:

- application artifact
- SBOM
- vulnerability scan result
- governance run input

## Why This Contract Exists

Without a normalized evidence contract, each repository would have to invent its own ad hoc structure.

That would create problems:

- control evaluation logic would become repository-specific
- governance reports would not be comparable
- onboarding other repositories would be slower
- evidence reuse across projects would be harder

The contract therefore gives downstream repositories one common structure for governance-relevant facts.

## Minimum Required Sections

The following sections are currently required by the schema:

- `contract_version`
- `release_candidate`
- `required_platform_level`
- `repository`
- `evidence`
- `artifact`
- `pipeline`

These sections represent the minimum context needed for the baseline evaluator to understand:

- which evidence contract version it is interpreting
- what type of run this is
- which platform level is claimed
- whether repository governance protections exist
- whether artifact and evidence files exist
- whether the pipeline itself enforced security gates

## Contract Version Semantics

`contract_version` identifies the structure of the governance run input payload.

It does not replace the released baseline version.

Example:

- baseline version: `l1-baseline-v1.1.3`
- evidence contract version: `1.0`

## Recommended Extended Sections

The following sections are strongly recommended when a repository wants better control-level coverage:

- `traceability`
- `run_context`
- `source_control`
- `static_analysis`
- `environment`
- `release_approval`
- `operations`
- `monitoring`
- `dependencies`
- `infrastructure`

These sections reduce ambiguity and allow more controls to move from:

- `not_tested`

to:

- `pass`
- or `fail`

based on explicit proof.

## Section-By-Section Explanation

### `repository`

Purpose:

- repository governance context

Typical fields:

- `protected_branch`
- `direct_push_allowed`
- `review_required`

Typical controls supported:

- `DSCB-L1-REQ-002`
- `DSCB-L1-REQ-003`

### `run_context`

Purpose:

- distinguish real release runs from diagnostic, pull-request, and branch-validation runs

Typical fields:

- `event`
- `purpose`
- `release_context`
- `source`

Typical values:

- `event: push`, `purpose: release`, `release_context: true`
- `event: workflow_dispatch`, `purpose: diagnostic`, `release_context: false`
- `event: pull_request`, `purpose: pull_request_validation`, `release_context: false`

Typical controls affected:

- `DSCB-L1-REQ-013`
- `DSCB-L1-REQ-014`

In non-release contexts, release authorization and approved-artifact deployment controls are treated as not applicable.

### `traceability`

Purpose:

- prove structured links between requirements, tests, and reports

Typical fields:

- `requirements_linked`
- `testcases_linked`
- `reports_linked`

Typical controls supported:

- `DSCB-L1-REQ-001`

### `source_control`

Purpose:

- prove governance of version control usage and review records

Typical fields:

- `approved_vcs`
- `identifiable_authors`
- `review_records_present`

Typical controls supported:

- `DSCB-L1-REQ-002`

### `static_analysis`

Purpose:

- prove secure coding analysis was performed and reviewed

Typical fields:

- `performed`
- `findings_reviewed`

Typical controls supported:

- `DSCB-L1-REQ-004`

### `evidence`

Purpose:

- prove existence and linkage of required evidence artifacts

Typical nested sections:

- `sbom`
- `vulnerability_scan`
- `pipeline_execution`

Typical controls supported:

- `DSCB-L1-REQ-005`
- `DSCB-L1-REQ-006`
- `DSCB-L1-REQ-009`
- `DSCB-L1-REQ-010`
- `DSCB-L1-REQ-015`

### `artifact`

Purpose:

- prove artifact identity and integrity

Typical nested sections:

- `digest`
- `signature`

Typical controls supported:

- `DSCB-L1-REQ-011`
- `DSCB-L1-REQ-012`

### `release_approval`

Purpose:

- prove authorized release and approved-artifact-only deployment

Typical fields:

- `approved`
- `approver`
- `approved_artifact_only`

Typical controls supported:

- `DSCB-L1-REQ-013`
- `DSCB-L1-REQ-014`

### `waivers`

Purpose:

- document approved, rejected, expired, or revoked exceptions in a machine-readable and auditable way

Required fields for approved waivers:

- `id`
- `scope`
- `object_id`
- `affected_requirements`
- `risk_classification`
- `justification`
- `compensating_controls`
- `approval_authority`
- `approved_by`
- `approved_on`
- `expiry`
- `expired`
- `status`

Typical controls supported:

- `DSCB-L1-REQ-010`
- `DSCB-L2-REQ-012`
- `DSCB-GOV-REQ-005`

### `environment`

Purpose:

- prove centrally managed and compliant development environments

Typical fields:

- `centrally_managed`
- `secure_workspace`
- `config_compliant`
- `configuration_baselines_defined`

Typical controls supported:

- `DSCB-L2-REQ-001`
- `DSCB-L2-REQ-002`

### `dependencies`

Purpose:

- prove repository-approved dependency sourcing

Typical fields per dependency:

- `name`
- `source_approved`

Typical controls supported:

- `DSCB-L2-REQ-005`
- `DSCB-L2-REQ-006`

### `infrastructure`

Purpose:

- prove Infrastructure-as-Code presence and version control

Typical nested section:

- `iac_repository`

Typical controls supported:

- `DSCB-L2-REQ-009`
- `DSCB-L2-REQ-010`

### `operations`

Purpose:

- prove deployed-version recording and security event recording

Typical fields:

- `deployed_versions_recorded`
- `security_events_recorded`

Typical controls supported:

- `DSCB-L1-REQ-016`

### `monitoring`

Purpose:

- prove security event generation and forwarding into monitoring systems

Typical fields:

- `security_events_generated`
- `integration_enabled`
- `forwarded_to_monitoring`

Typical controls supported:

- `DSCB-L2-REQ-013`
- `DSCB-L2-REQ-014`

## Practical File Example

An application repository can generate this file during its workflow:

```text
governance/governance-run-input.json
```

And then upload it with the other evidence artifacts.

## Step-By-Step Consumer Workflow

### Step 1

Generate the normal baseline evidence:

- artifact
- SBOM
- vulnerability scan

### Step 2

Generate `governance/governance-run-input.json` using the official schema.

### Step 3

Upload the file together with the other evidence artifacts.

### Step 4

Run the central baseline workflow.

### Step 5

Optionally run the control evaluation report generator against the uploaded governance input.

## Recommended Consumer Validation

Before using the input operationally, a downstream repository should validate its payload against:

- `schemas/governance-run-input.schema.json`

This can be done:

- in CI
- in a local pre-release workflow
- or in a dedicated governance-reporting job

## Design Rule

The governance run input should describe:

- facts the repository can defend
- facts derived from real repository or pipeline behavior
- facts that are stable enough to be audited later

It should not be treated as a convenience file for making reports artificially green.

## Relationship To The Control Evaluation Report

The governance run input is the machine-readable source.

The control evaluation report is a derived output.

In other words:

- `governance/governance-run-input.json` = input contract
- `generated/control-evaluation-report.json` = evaluated result

## Related Files

- `schemas/governance-run-input.schema.json`
- `schemas/waiver.schema.json`
- `docs/examples/governance-run-input.example.json`
- `scripts/generate_control_evaluation_report.py`
- `scripts/control_evaluation.py`
- `docs/operations/evidence/how-to-read-control-evaluation-status.md`
- `docs/operations/evidence/governance-evidence-schema-versioning.md`
- `docs/operations/processes/waiver-management-standard.md`
