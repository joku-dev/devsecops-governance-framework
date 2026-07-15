# Release Publication Checklist

## Purpose

This checklist defines the minimum publication gate for a new governance baseline release.

It is intended to reduce release drift and make every released baseline:

- understandable
- reproducible
- reviewable
- safe for downstream adoption

## When To Use This Checklist

Use this checklist when:

- a new baseline version is prepared
- a released workflow is updated
- the evidence contract changes
- a release statement is published

## Step 1: Confirm The Release Scope

- confirm the target baseline version
- confirm whether the release is patch, minor, or major
- confirm which downstream repositories are affected
- confirm whether migration guidance is required

## Step 2: Confirm Source Changes

- Policy or Directive source changes are merged if the release depends on them
- control updates are merged
- traceability updates are merged
- verification logic changes are merged
- release-facing examples are updated

## Step 3: Confirm Contract Changes

- `schemas/governance-run-input.schema.json` is current
- `docs/examples/governance-run-input.example.json` is current
- `contract_version` is correct
- `docs/operations/evidence/governance-evidence-contract.md` is aligned
- `docs/operations/evidence/governance-evidence-schema-versioning.md` is aligned

## Step 4: Confirm Release Package Content

- the versioned release folder under `releases/` is complete
- workflow sources are frozen into the release package
- examples are present
- policy rules are present when applicable
- checksums or release metadata are refreshed when used

## Step 5: Confirm Documentation

- release overview is updated
- release statement is updated
- migration notes are updated when needed
- onboarding docs still reflect the supported consumer path
- official entrypoints link to the new release content

## Step 6: Confirm Operational Validation

Run:

```bash
python3 scripts/validate_governance_repo.py
python3 -m unittest discover -s tests
```

If the release changes viewer or generated artifacts, also refresh the derived outputs before publishing.

## Step 7: Confirm Consumer Impact

- at least one realistic consumer scenario has been reviewed
- any new required evidence is documented
- any workflow interface changes are documented
- any migration step is written in a way that a downstream team can follow directly

## Step 8: Confirm Governance Review

- release owner reviewed the release package
- governance owner reviewed the policy and baseline effect
- platform/security reviewers checked workflow or enforcement changes if applicable

## Step 9: Publish

- commit the release package and documentation
- push to the protected mainline
- publish or reference the release tag if used
- announce the baseline version for downstream adoption

## Short Maintainer Checklist

- scope classified
- source updates merged
- evidence contract aligned
- release package complete
- docs updated
- validation green
- downstream impact understood
- reviewers aligned

## Related Documents

- `docs/releases/release-and-migration-model.md`
- `docs/operations/guides/how-to-update-baseline-input-documents.md`
- `docs/operations/evidence/governance-evidence-schema-versioning.md`
