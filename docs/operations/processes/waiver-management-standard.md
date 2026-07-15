# Waiver Management Standard

## Purpose

This document defines the standard waiver format and the minimum governance expectations for approved exceptions.

The goal is to ensure that waivers are:

- explicit
- time-limited
- approved by the right authority
- justified
- linked to compensating controls

## Standard Waiver Fields

Every approved waiver should contain at least these fields:

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

## Why Each Field Matters

### `id`

Provides a stable reference for audit, reporting, and revocation.

### `scope`

Explains the business or technical scope of the exception.

### `object_id`

Links the waiver to the concrete object being waived, for example:

- a vulnerability id
- a dependency name
- an artifact identifier
- a repository control exception id

### `affected_requirements`

Makes it clear which controls or governance requirements are being deviated from.

### `risk_classification`

Determines which authority may approve the waiver.

### `justification`

Explains why the exception is necessary and why normal compliance is temporarily not possible.

### `compensating_controls`

Documents what is done to reduce risk while the exception remains open.

### `approval_authority`

Documents the formal authority level that is allowed to approve the waiver.

### `approved_by`

Documents the named approver for accountability.

### `approved_on`

Documents when the waiver became effective.

### `expiry`

Defines the last date on which the waiver may still be relied on.

### `expired`

Provides an operational boolean for machine validation.

### `status`

Captures the current lifecycle state:

- `requested`
- `approved`
- `rejected`
- `expired`
- `revoked`

## Example

Example record:

```yaml
id: waiver-demo-001
scope: release-candidate-exception
object_id: CVE-2099-0001
affected_requirements:
  - DSCB-L1-REQ-010
  - DSCB-GOV-REQ-005
risk_classification: medium
justification: Temporary exception until vendor fix is released and validated.
compensating_controls:
  - Temporary network restriction applied
  - Daily monitoring review enabled
approval_authority: DevSecOps Governance Board
approved_by: governance-board-chair
approved_on: 2026-06-20
expiry: 2026-07-20
expired: false
status: approved
```

The example source file is:

- `model/waivers/waiver-example.yaml`

## Operating Rules

- waivers must not be open-ended
- expired waivers must not be accepted by governance checks
- high-risk waivers must follow the defined authority model
- every approved waiver must include justification and compensating controls
- revocation should be recorded instead of silently deleting old waivers

## Relationship To Machine Validation

The waiver structure is enforced through:

- `schemas/waiver.schema.json`
- `schemas/governance-run-input.schema.json`
- `policies/opa/waiver_validity.rego`

## Related Documents

- `docs/governance/devsecops-directive.md`
- `docs/operations/evidence/governance-evidence-contract.md`
- `docs/operations/processes/operational-governance-enforcement-options.md`
