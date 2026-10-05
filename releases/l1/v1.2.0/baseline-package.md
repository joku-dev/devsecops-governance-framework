# L1 Baseline Release Package v1.2.0

## Status

Prepared release candidate. Publication requires review, merge to main, a directly SSH-signed tag, and downstream validation. This package does not replace or modify l1-baseline-v1.1.3.

## Classification and purpose

This is a minor, backward-compatible L1 release. It packages the merged, reviewed evidence-contract additions from PR #212 so consumers can adopt them through a new immutable workflow reference.

## What is new in v1.2.0

- security_gates.blocks_merge is an additive optional field that states whether the configured run blocks merging.
- security_gates.enforced describes that the gate executed and evaluated; it does not mean findings block merging.
- The reusable workflow includes the build artifact path in pipeline evidence so central intake can verify the declared SHA-256 against downloaded bytes.
- No controls, OPA policy behavior, blocking mode, or required evidence fields change.

## Consumer reference

After the release tag is published, consumers may opt into it with:

    uses: joku-dev/devsecops-governance-framework/.github/workflows/devsecops-baseline-l1-v1.2.0.yml@l1-baseline-v1.2.0

Keep new consumers in report-only until their measured evidence and governance outcome have been reviewed. The declaration for external direct downloads remains producer-supplied; this release does not measure consumer egress.

## Validation and migration

The central intake fix passed a full local central-intake replay against retained ECV-001 artifacts. That replay used artifacts produced by v1.1.3 and does not prove that a consumer has adopted this release. Fresh report-only runs from the private cJSON and go-httpbin pilot repositories, followed by normal central intake, remain required before ECV-01 can close.

The versioned wrapper pins the reusable workflow to immutable governance commit df15833e0dea51b6415a0ce416243698c656f6ca. Consumers must update the wrapper reference and run their workflow again. Do not move or rewrite l1-baseline-v1.1.3.
