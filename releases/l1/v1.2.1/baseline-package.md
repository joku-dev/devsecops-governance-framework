# L1 Baseline Release Package v1.2.1

## Status

Prepared release candidate. Publication requires review, merge to main, a directly SSH-signed tag, and downstream validation. This package does not replace or modify `l1-baseline-v1.1.3` or `l1-baseline-v1.2.0`.

## Classification and purpose

This is a backward-compatible patch release. It corrects how the reusable workflow projects an existing producer-declared observation into pipeline evidence. It does not change controls, OPA policy, schemas, gate modes, or enforcement defaults.

## What is new in v1.2.1

When a consumer supplies `governance_run_input_path`, the reusable workflow reads the boolean `pipeline.external_direct_downloads_detected` from that file and writes the same value to `pipeline-evidence.json`. A missing file, invalid JSON, absent pipeline object, or non-boolean value fails evidence collection. Without a configured run-input path, the prior environment-variable fallback remains available.

This preserves producer source attribution and aligns the two artifacts; it does not independently measure network traffic.

## Consumer reference

After a signed release tag is published, consumers may opt into it with:

    uses: joku-dev/devsecops-governance-framework/.github/workflows/devsecops-baseline-l1-v1.2.1.yml@l1-baseline-v1.2.1

Keep new consumers in report-only until their measured evidence and governance outcome have been reviewed.

## Validation and migration

The package includes the reusable workflow source frozen at governance commit `43490ec9d0490e67cf6b05b4a28110d2a7d683e0`. After publication, update pilot consumers through reviewed changes and run fresh report-only workflows followed by normal central intake. ECV-01 remains open until those runs demonstrate aligned source-labelled evidence and the consumer PRs are reviewed. Do not move or rewrite any published baseline tag.
