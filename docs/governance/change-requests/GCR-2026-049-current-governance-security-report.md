# Governance Change Request

## Change ID

```text
GCR-2026-049
```

## Summary

- Refresh the governance repository self-security assessment from live GitHub
  settings and the current checkout.
- Add a management-readable executive assessment, explicit observations,
  prioritized remediation steps, prerequisites, and acceptance criteria.
- Add report-only criterion `GRS-016` for restriction of GitHub Actions to
  approved sources.
- Bump the internal self-security report schema from `0.1.0` to `0.2.0`.

## Classification

| Field | Value |
|---|---|
| Change type | report-only security assessment improvement |
| Governance intent | make governance-authority risk and remediation transparent |
| Enforcement | unchanged, `report_only` |
| Consumer contract impact | none |
| Released baseline impact | none |
| Report schema impact | additive internal version `0.2.0` |

## Current Assessment

The point-in-time assessment records 16 criteria: 7 pass and 9 fail. The
repository has active scanning, dependency, permission, ownership, and private
reporting controls, but is not yet a protected governance authority.

The principal unresolved risks are:

- unprotected `main` without required reviews or Governance CI;
- four operational workflows with direct write access to `main`;
- repository-wide Action source and SHA enforcement not enabled;
- signed changes and verified release tags not required.

## Remediation Order

1. Migrate direct automated `main` writes and enable Action source/SHA
   restrictions.
2. Protect `main` with pull requests, approvals, required checks, and
   destructive-change protection.
3. Require signed changes and introduce verified future release publication.

Default-branch protection must not be activated before the automated write
path has a protected replacement.

## Decision Boundary

This change does not:

- enable blocking enforcement;
- edit GitHub repository settings;
- certify the repository as secure;
- modify released baseline packages or historical release tags;
- change consumer evidence contracts;
- authorize automation bypass.

## Roles

- Governance Analyst: risk interpretation and sequencing.
- DevSecOps Baseline Owner: confirms no consumer baseline impact.
- Release Manager: confirms no baseline release and no historical tag rewrite.
- Repo Steward: live evidence, generated-output, validation, and scope review.

## Validation

- [x] live self-security assessment generated
- [x] self-security report schema validation
- [x] focused self-security tests
- [x] complete runtime and repository validation
- [x] complete unit test suite
- [x] strict documentation build
- [x] diff and repository hygiene review

## Release Decision

No DevSecOps or architecture baseline release is required. The report schema is
an internal, report-only contract and advances additively to `0.2.0`.
