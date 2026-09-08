# Governance Change Request

## Change ID

```text
GCR-2026-048
```

## Summary

- Add a report-only security profile for the governance repository itself.
- Assess GitHub root controls, workflow supply-chain controls, ownership,
  automated writes, and release integrity independently from consumer status.
- Add pinned third-party Actions, CodeQL, dependency review, Dependabot, and a
  private vulnerability-reporting path.
- Preserve released DevSecOps and architecture baselines unchanged.
- Defer blocking `main` protection until direct intake writes have a protected
  replacement path.

## Classification

| Field | Value |
|---|---|
| Change type | governance authority hardening and report-only assessment |
| Source basis | accepted DSCB and PRA source placeholders |
| Enforcement | report-only |
| Consumer contract impact | none |
| Evidence contract impact | none |
| Released baseline impact | none |
| GitHub setting impact | security features may be enabled; branch rules deferred until write-path migration |

## Problem Statement

Consumer checks cannot establish trust in the repository that defines their
controls, policies, schemas, workflows, and releases. The current repository
has strong functional validation but does not yet continuously evaluate or
enforce its own repository-security posture.

The initial live assessment identified missing default-branch protection,
disabled security features, mutable third-party Action references, unsigned
changes and release tags, and direct automated writes to `main`.

## Decision Boundary

This change does not:

- declare the governance repository secure;
- enable blocking based on its own report;
- grant an automated bypass;
- alter existing release tags or released package contents;
- treat unavailable GitHub settings as successful evidence;
- derive behavior from an unapproved candidate source.

## Safe Rollout

1. Introduce and observe report-only self-security evidence.
2. Enable non-disruptive GitHub security features.
3. Migrate automated operational writes away from direct `main` pushes.
4. Enable and verify the protected-branch ruleset.
5. Introduce signed release publication in a separate release change.
6. Consider blocking only after owner approval and stable evidence.

## Roles

- Governance Analyst: self-governance intent and decision boundary.
- DevSecOps Baseline Owner: source alignment without released-baseline mutation.
- Repo Steward: workflow, dependency, ownership, validation, and hygiene review.
- Release Manager: future signed-release change remains separate.
- Governance Owner: approves branch rules and any later blocking transition.

## Validation

- [x] self-security model schema validation
- [x] self-security report schema validation
- [x] secure and insecure observation unit tests
- [x] pinned Action reference audit
- [x] OPA and repository validation
- [x] complete unit test suite
- [x] strict documentation build
- [x] live GitHub report-only assessment

## Release Decision

No baseline release is required. Existing released packages and tags remain
immutable. Cryptographically signed replacement releases require a separate
release decision.
