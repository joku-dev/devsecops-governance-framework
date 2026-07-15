# Release And Migration Model

## Purpose

This guide explains how released baseline packages should evolve and how downstream repositories should migrate safely.

## Core Principle

The repository contains two different states:

- working source of truth
- released baseline packages

Released packages are the controlled integration surface for downstream repositories.

## Where Releases Live

Published release packages live under:

- `releases/`

Release-facing documentation lives under:

- `docs/releases/`

## Recommended Versioning Model

Use semantic versioning for released baseline packages.

### Patch Release

Use for:

- editorial corrections
- non-breaking workflow fixes
- documentation clarifications
- viewer or reporting improvements that do not change the consumer contract

### Minor Release

Use for:

- additional controls
- new optional evidence fields
- stronger evaluation coverage without breaking existing consumers
- onboarding improvements with backward compatibility

### Major Release

Use for:

- breaking workflow interface changes
- required new evidence fields
- changed gate semantics
- renamed or removed consumer-facing fields

## Recommended Release Decision Flow

1. identify the changed governance behavior
2. determine whether downstream repositories are affected
3. classify the change as patch, minor, or major
4. update release docs and package content
5. validate with at least one consuming repository
6. publish the new version

## Downstream Upgrade Checklist

When a downstream repository upgrades a pinned baseline:

1. read the release statement
2. read the migration notes
3. update the workflow reference
4. update evidence generation if required
5. run the governance workflow on a branch
6. inspect the control evaluation artifact
7. merge only after the new result is understood

## Example

Example upgrade:

- from `l1-baseline-v1.1.1`
- to `l1-baseline-v1.1.2`

Typical consumer action:

```yaml
uses: joku-dev/devsecops-governance-as-code/.github/workflows/devsecops-baseline-l1-v1.1.2.yml@main
```

## Required Release Documentation

Every released baseline should ideally provide:

- release statement
- baseline package overview
- migration notes
- example consumer workflow
- evidence contract notes when relevant

## Relationship To Viewer History

The status viewer shows operational outcome history.

Release documentation explains:

- what changed in the baseline
- why the outcome might change
- what consumers must do to adopt the release safely

## Related Documents

- `docs/releases/index.md`
- `docs/operations/guides/how-to-update-baseline-input-documents.md`
- `docs/operations/evidence/governance-evidence-schema-versioning.md`
- `docs/onboarding/application-repo-onboarding.md`
