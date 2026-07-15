# Governance Evidence Schema Versioning

## Purpose

This guide defines how the machine-readable governance evidence contract evolves over time.

The goal is to keep downstream repositories:

- compatible
- comparable
- auditable

while still allowing the governance baseline to improve.

## Official Contract

The official machine-readable contract is the governance run input schema:

- `schemas/governance-run-input.schema.json`

The canonical example payload is:

- `docs/examples/governance-run-input.example.json`

## Version Identifier

The governance run input supports:

- `contract_version`

Current value:

- `1.0`

## Compatibility Rules

### Patch-Compatible Change

Examples:

- documentation clarification
- tighter descriptions without changing field structure
- optional example improvements

### Minor-Compatible Change

Examples:

- new optional field
- new optional section
- broader accepted enum where evaluation remains compatible

### Breaking Change

Examples:

- existing field renamed
- optional field becomes required
- meaning of an existing field changes
- workflow interface requires a new mandatory evidence element

## Recommended Evolution Policy

Prefer:

- additive changes first
- optional fields before required fields
- migration periods before enforcement

Avoid:

- silent semantic changes
- repurposing existing field names
- introducing mandatory fields without a release note and migration guide

## Required Maintainer Actions When The Contract Changes

When the schema changes, update all of these together:

- `schemas/governance-run-input.schema.json`
- `docs/examples/governance-run-input.example.json`
- `docs/operations/evidence/governance-evidence-contract.md`
- release notes in `docs/releases/`
- versioned release package content under `releases/` when consumers are affected

If the reusable workflow emits pipeline evidence automatically, update that generator too.

## Contract Version Versus Baseline Version

### Contract Version

Meaning:

- structure of the machine-readable governance evidence payload

Example:

- `contract_version: 1.0`

### Baseline Version

Meaning:

- released governance package used by downstream repositories

Example:

- `l1-baseline-v1.1.2`

## Example Decision Table

| Change | Contract Impact | Release Impact |
| --- | --- | --- |
| New optional monitoring field | minor-compatible | usually minor baseline release |
| New optional `run_context` field | minor-compatible | usually minor baseline release |
| Rename `review_required` | breaking | new baseline release plus migration |
| Clarify docs only | none | patch or no release |
| Make `release_approval.approver` mandatory | breaking | new baseline release plus migration |

## Example Payload Snippet

```json
{
  "contract_version": "1.0",
  "release_candidate": true,
  "required_platform_level": "PRA-Level 2"
}
```

## Recommended Downstream Practice

Every consuming repository should:

- emit `contract_version`
- pin a released baseline version
- update both only through a controlled change

## Related Documents

- `docs/operations/evidence/governance-evidence-contract.md`
- `docs/releases/release-and-migration-model.md`
- `docs/onboarding/application-repo-onboarding.md`
