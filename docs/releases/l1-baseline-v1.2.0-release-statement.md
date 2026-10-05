# Prepared Release Statement: L1 Baseline v1.2.0

## Publication status

Prepared for review; not yet released. The tag does not exist. Do not describe v1.2.0 as a supported published baseline until the release PR is merged, the tag is directly SSH-signed by the registered active signer and verified, and the release is published.

## Intended release identity

- Version: v1.2.0
- Intended tag: l1-baseline-v1.2.0
- Type: minor, backward-compatible
- Reusable workflow implementation: df15833e0dea51b6415a0ce416243698c656f6ca

## Change summary

This release packages the optional evidence-contract changes merged in PR #212. Pipeline evidence distinguishes gate evaluation from merge blocking through security_gates.enforced and security_gates.blocks_merge. It also identifies the build artifact path, allowing central intake to verify the declared build digest against the actual downloaded bytes.

No control baseline, OPA rule, required evidence field, or enforcement default changes. The existing v1.1.3 release remains byte-for-byte and tag-for-tag unchanged.

## Validation boundary

Local full central-intake replay against the retained v1.1.3 pilot artifacts succeeded for cJSON and go-httpbin. Both remained governance failures with successful report-only workflow jobs; central Trust reached provenance_verified for the governance-result artifacts. This does not establish that either consumer has adopted v1.2.0.

Fresh report-only consumer runs and central intake remain required before ECV-01 closes. The consumer evidence, their disagreement about gate semantics and external downloads, the go-httpbin vulnerability finding, and the open ECV-12/13 decisions remain visible.
