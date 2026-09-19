# GCR-2026-102: GRS-014 Release Integrity Verification

## Intent

Close the report-only `GRS-014` finding without rewriting historical release
tags. Verify current direct tag signatures against an approved SSH signer and
bind the fixed set of older unsigned tags to a signed retrospective integrity
manifest containing their tag objects, target commits and release-artifact
digests.

## Artifact Classification

| Field | Decision |
|---|---|
| Artifact | Release-signing policy, signed legacy integrity statement, verifier and security projection |
| Type | Governance repository security hardening and release-integrity evidence |
| Target | `model/governance/`, `releases/`, `schemas/`, `scripts/`, tests, generated reports and documentation |
| Owner | Governance owners and Release Manager |
| Source Document Intake required | no; this implements the existing `GRS-014` criterion |
| Evidence contract impact | additive self-security observation detail only; no consumer evidence change |
| Enforcement impact | none; Self-Security remains report-only |
| Release impact | no DevSecOps or architecture baseline release; existing tags and packages remain unchanged |

## Decisions

1. `v0.2.0-public-adoption` is verified as a directly signed tag against the
   registered `joku-dev` SSH signing key.
2. The three older unsigned release tags remain byte-for-byte unchanged. Their
   exact tag-object IDs, target commits and release-artifact digests are covered
   by `releases/release-tag-integrity.json` and its SSH signature.
3. Retrospective verification is labeled separately and does not claim that an
   older tag carried a publication-time signature.
4. The legacy set is closed. Every new baseline or public-adoption tag requires
   a direct signature from an active signer; an unknown unsigned tag fails
   `GRS-014`.
5. `GRS-005` remains a separate finding. A verified release tag binds its target
   commit without claiming that every default-branch commit is signed.
6. The self-security profile moves to `0.4.0`; its report remains schema `0.2.0`
   because the additional release-integrity observation is additive.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | none |
| DevSecOps controls | `GRS-014` evaluation gains direct and retrospective verification modes |
| Architecture governance | none |
| OPA policies | none |
| Schemas | new release-signing policy and integrity-statement schemas |
| Viewer and generated reports | Repository Security shows `GRS-014` as passed and retains verification detail |
| Released baselines | no mutation and no new release |
| Downstream repositories | none; existing pins and workflow contracts remain valid |

## Validation Plan

- [x] direct SSH tag verification succeeds for `v0.2.0-public-adoption`
- [x] the signed manifest matches all three approved historical tag identities
- [x] release package checksums and bound release-document digests verify
- [x] tampered manifest, artifact, tag target and new unsigned tag tests fail closed
- [x] focused Self-Security and Viewer tests pass
- [x] `./scripts/bootstrap_validation_env.sh`
- [x] `./scripts/validate_all.sh` (`623` tests passed)
- [x] `.venv-docs/bin/mkdocs build --strict`

## Release Decision

No baseline release is required. Future release publication must use direct
signing; the historical manifest is a bounded migration record, not a reusable
exception path.
