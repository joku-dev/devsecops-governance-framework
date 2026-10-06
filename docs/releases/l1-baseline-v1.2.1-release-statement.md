# Release Statement: L1 Baseline v1.2.1

## Publication status

Published on 2026-10-06 as annotated SSH-signed tag `l1-baseline-v1.2.1`. The reviewed package merge was PR #215. The tag signature verifies against the active release-signing policy and points to merge commit `901d06d0c2f5ff62bb9aff987d04fbd9d35e8235`. Its tag object is `23224bfaaa27001ad43de024e2c5c6f89de81d51`.

## Intended release identity

- Version: v1.2.1
- Published tag: `l1-baseline-v1.2.1`
- Type: patch, backward-compatible
- Reusable workflow implementation: `43490ec9d0490e67cf6b05b4a28110d2a7d683e0`

## Change summary

When a consumer supplies `governance_run_input_path`, the reusable workflow now copies the boolean `pipeline.external_direct_downloads_detected` from the configured run-input file into `pipeline-evidence.json`. A missing or malformed configured input fails closed. The declared value remains producer-supplied; intake does not measure consumer egress.

No control, OPA policy, schema, blocking default, or released v1.2.0 package was changed. The signed v1.2.1 tag is the only new release tag.

## Validation boundary

The regression fixture covers true, false, missing-file, and invalid-type cases. The release package checksum list was verified, and local release-integrity assessment verified the tag signature with the active signer. cJSON run 37467713254, go-httpbin run 37467832720, and Gson run 37467911213 all reference `refs/tags/l1-baseline-v1.2.1`. Temporary local intake assessments reached `provenance_verified` for all three. Each report-only governance decision remains `fail` because the pilot repositories declare direct pushes allowed. No pilot snapshot was copied into official status, and no pilot has been admitted to the official consumer registry. ECV-01 remains open.
