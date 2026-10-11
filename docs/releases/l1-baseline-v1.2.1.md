# L1 Baseline v1.2.1 — Published

## Status

Published on 2026-10-06 under signed tag `l1-baseline-v1.2.1`, targeting merge commit `901d06d0c2f5ff62bb9aff987d04fbd9d35e8235`. The tag object `23224bfaaa27001ad43de024e2c5c6f89de81d51` verifies against the active release-signing policy. Downstream report-only validation continues. The existing v1.2.0 package and tag remain unchanged.

## Release classification

Patch release with no control, OPA, schema, enforcement, or blocking-mode changes. The release corrects how the reusable workflow transfers an existing producer-declared direct-download observation from `governance-run-input.json` into `pipeline-evidence.json`.

## Change

When `governance_run_input_path` is configured, the reusable workflow reads `pipeline.external_direct_downloads_detected` from that file, requires the value to be a boolean, and writes the same value into pipeline evidence. Missing or malformed configured input fails evidence collection. When the path is not configured, the existing environment-variable fallback is retained.

Both fields remain producer-declared. The central intake does not observe consumer network traffic, and matching values do not constitute independent measurement.

## Package and consumer reference

The immutable package is under `releases/l1/v1.2.1/`. Its reusable workflow source is frozen at implementation commit `43490ec9d0490e67cf6b05b4a28110d2a7d683e0`.

Consumers may opt in with:

    uses: joku-dev/devsecops-governance-framework/.github/workflows/devsecops-baseline-l1-v1.2.1.yml@l1-baseline-v1.2.1

## Validation and remaining decisions

The implementation includes a regression fixture for true, false, missing, and invalid producer declarations. cJSON run 37467713254, go-httpbin run 37467832720, and Gson run 37467911213 all used the signed tag; local-only central intake assessments reached `provenance_verified` for each. Their report-only governance decisions remain `fail` because the pilots declare direct pushes allowed. ECV-01 remains open until those findings and remaining controls are reviewed. All three private pilots stay outside the official consumer registry, and no run was added to official status. Their independent CI failures, branch-protection posture, and the ECV-12/13 blockers remain separate decisions. Release files inside the tagged package are frozen; publication state is recorded here, outside the package.
