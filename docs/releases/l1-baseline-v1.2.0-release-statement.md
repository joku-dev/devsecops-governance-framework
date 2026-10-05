# Release Statement: L1 Baseline v1.2.0

## Publication status

Released on 2026-10-05 as the directly SSH-signed tag `l1-baseline-v1.2.0`. The tag object `90aefb65b5cca8bc2141840eb4078582f4f99a5d` resolves to main commit `bdc993d49d82c4a1fa4cdcabb572011896de17c2`. `git verify-tag` validated the signature against the active signer configured in the repository release-signing policy.

## Release identity

- Version: v1.2.0
- Tag: `l1-baseline-v1.2.0`
- Type: minor, backward-compatible
- Reusable workflow implementation: `df15833e0dea51b6415a0ce416243698c656f6ca`
- Release commit: `bdc993d49d82c4a1fa4cdcabb572011896de17c2`

## Change summary

This release packages the optional evidence-contract changes merged in PR #212. Pipeline evidence distinguishes gate evaluation from merge blocking through `security_gates.enforced` and `security_gates.blocks_merge`. It also identifies the build artifact path, allowing central intake to verify the declared build digest against the actual downloaded bytes.

No control baseline, OPA rule, required evidence field, or enforcement default changes. The existing v1.1.3 release remains byte-for-byte and tag-for-tag unchanged.

## Validation boundary

The governance PR and post-merge main workflows passed. Fresh report-only pull-request runs in the private cJSON and go-httpbin pilot consumers completed central intake. Their baseline gate results were failures with successful report-only workflow jobs, and Trust reached `provenance_verified` for the governance-result artifacts. This confirms result identity and custody; it does not establish trust in application source or binaries, or a clean security result.

The producer run-input and pipeline-evidence values agree on gate evaluation and merge behavior. They continue to differ on `external_direct_downloads_detected`; central intake preserves the two source-labelled values and does not measure consumer egress. The consumer PRs remain open, and ECV-01 remains open until the evidence-source discrepancy and adoption decision are resolved. ECV-12 and ECV-13 remain blocked.
