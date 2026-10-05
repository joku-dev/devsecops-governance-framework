# L1 Baseline v1.2.0

## Publication status

Published on 2026-10-05 as the directly SSH-signed tag `l1-baseline-v1.2.0`. The tag resolves to governance main commit `bdc993d49d82c4a1fa4cdcabb572011896de17c2`; the tag object is `90aefb65b5cca8bc2141840eb4078582f4f99a5d`. Signature verification matched the active release signer in `model/governance/release-signing-policy.yaml`. The prior v1.1.3 package and tag remain unchanged.

## Release classification

Minor, backward compatible. The governance release model classifies additive optional evidence fields as a minor release.

## Scope

The release packages the reusable workflow implementation merged in PR #212:

- pipeline evidence reports whether the evaluated gate blocks merge as a separate optional field;
- the producer includes the declared build-artifact path so central intake can recompute its digest from downloaded bytes;
- existing control definitions, OPA policy behavior, default blocking mode, and required evidence do not change.

This package does not claim that the consumer's external downloads were centrally measured. That field remains a producer declaration.

## Consumer reference

Consumers may use the immutable release reference:

    uses: joku-dev/devsecops-governance-framework/.github/workflows/devsecops-baseline-l1-v1.2.0.yml@l1-baseline-v1.2.0

The v1.2.0 wrapper pins the reusable workflow to immutable governance commit `df15833e0dea51b6415a0ce416243698c656f6ca`.

## Validation and migration

The merged governance main commit passed all required PR checks and all post-merge workflows, including Governance CI, CodeQL, Repository Self-Security, Repository SBOM, Publish Docs, and Consumer Lifecycle Guard.

Fresh report-only pull-request runs in the private cJSON and go-httpbin pilot repositories adopted v1.2.0 and completed normal central intake. Both governance-result artifacts reached `provenance_verified`; both governance outcomes remained `fail` while the report-only workflow jobs succeeded. The run-input and pipeline-evidence gate declarations now agree (`enforced: true`, `blocks_merge: false`). The declaration for external direct downloads still differs between the two sources and remains producer-supplied rather than centrally measured. These are pilot observations, not official consumer results; ECV-01 remains open pending resolution of that declaration and consumer review/merge decisions.

The cJSON and go-httpbin consumer PRs remain open. Their separate upstream CI failures are recorded in the pilot status report. Do not move or rewrite `l1-baseline-v1.1.3` or `l1-baseline-v1.2.0`.
