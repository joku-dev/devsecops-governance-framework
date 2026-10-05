# L1 Baseline v1.2.0 — Prepared Release Candidate

## Status

Prepared, not published. The package and workflow wrapper are available for review. Publication requires merge to main, a directly SSH-signed tag verified against the repository signing policy, and downstream validation. The existing v1.1.3 package and tag remain unchanged.

## Release classification

Minor, backward compatible. The governance release model classifies additive optional evidence fields as a minor release.

## Scope

The release packages the reusable workflow implementation merged in PR #212:

- pipeline evidence reports whether the evaluated gate blocks merge as a separate optional field;
- the producer includes the declared build-artifact path so central intake can recompute its digest from downloaded bytes;
- existing control definitions, OPA policy behavior, default blocking mode, and required evidence do not change.

This package does not claim that the consumer's external downloads were centrally measured. That field remains a producer declaration.

## Consumer reference

Once the signed tag is published, the workflow reference will be:

    uses: joku-dev/devsecops-governance-framework/.github/workflows/devsecops-baseline-l1-v1.2.0.yml@l1-baseline-v1.2.0

The v1.2.0 wrapper pins the reusable workflow to immutable commit df15833e0dea51b6415a0ce416243698c656f6ca.

## Validation and migration

The central intake implementation has been exercised locally against retained ECV-001 artifacts. Both snapshots resolved SBOM, scan, build, and run-input evidence; the governance results remained failures in report-only mode. Those artifacts were produced by v1.1.3, so this is not downstream adoption evidence.

After publication, update the two private pilot workflows in a reviewed change, retain report-only mode, run both consumers, and perform normal central intake. Compare source-attributed gate semantics and verify the complete evidence and custody path. ECV-01 remains open until this fresh round trip is recorded.
