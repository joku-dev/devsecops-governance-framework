# L1 Baseline v1.2.1 — Prepared Release Candidate

## Status

Prepared for review; not published. Publication requires merge to `main`, a directly SSH-signed tag verified against the release-signing policy, and downstream pilot validation. The existing v1.2.0 package and tag remain unchanged.

## Release classification

Patch release with no control, OPA, schema, enforcement, or blocking-mode changes. The release corrects how the reusable workflow transfers an existing producer-declared direct-download observation from `governance-run-input.json` into `pipeline-evidence.json`.

## Change

When `governance_run_input_path` is configured, the reusable workflow reads `pipeline.external_direct_downloads_detected` from that file, requires the value to be a boolean, and writes the same value into pipeline evidence. Missing or malformed configured input fails evidence collection. When the path is not configured, the existing environment-variable fallback is retained.

Both fields remain producer-declared. The central intake does not observe consumer network traffic, and matching values do not constitute independent measurement.

## Package and consumer reference

The prepared package is under `releases/l1/v1.2.1/`. Its reusable workflow source is frozen at implementation commit `43490ec9d0490e67cf6b05b4a28110d2a7d683e0`.

After merge and signed-tag publication, consumers may opt in with:

    uses: joku-dev/devsecops-governance-framework/.github/workflows/devsecops-baseline-l1-v1.2.1.yml@l1-baseline-v1.2.1

## Validation and remaining decisions

The implementation includes a regression fixture for true, false, missing, and invalid producer declarations. Fresh consumer runs against the signed release and central intake are still required before ECV-01 can be closed. Both pilot repositories remain private, report-only, and outside the official consumer registry. Their independent CI findings, branch-protection posture, and the ECV-12/13 blockers remain separate decisions.
