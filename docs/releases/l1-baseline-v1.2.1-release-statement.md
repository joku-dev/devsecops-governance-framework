# Prepared Release Statement: L1 Baseline v1.2.1

## Publication status

Prepared for review; not released. No `l1-baseline-v1.2.1` tag has been created. Publication requires a reviewed merge, a directly SSH-signed annotated tag from an active signer, verification against repository policy, and a fresh downstream pilot run.

## Intended release identity

- Version: v1.2.1
- Intended tag: `l1-baseline-v1.2.1`
- Type: patch, backward-compatible
- Reusable workflow implementation: `43490ec9d0490e67cf6b05b4a28110d2a7d683e0`

## Change summary

When a consumer supplies `governance_run_input_path`, the reusable workflow now copies the boolean `pipeline.external_direct_downloads_detected` from the configured run-input file into `pipeline-evidence.json`. A missing or malformed configured input fails closed. The declared value remains producer-supplied; intake does not measure consumer egress.

No control, OPA policy, schema, blocking default, released v1.2.0 package, or tag is changed.

## Validation boundary

The regression fixture exercises true, false, missing-file, and invalid-type cases. Full repository validation is required for this candidate. cJSON and go-httpbin must run the published signed tag in report-only mode before ECV-01 can be reassessed. Neither private pilot repository is admitted to the official consumer registry by this release candidate.
