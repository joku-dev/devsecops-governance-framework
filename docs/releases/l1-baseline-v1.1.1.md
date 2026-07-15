# L1 Baseline v1.1.1

This page points to the patch release of the versioned `L1` baseline package with corrected workflow wiring for the governance run input contract.

## Release Package

- `releases/l1/v1.1.1/baseline-package.md`
- `releases/l1/v1.1.1/release-metadata.json`
- `releases/l1/v1.1.1/checksums.sha256`

## Consumer Workflow

Other repositories should consume this package through:

- `.github/workflows/devsecops-baseline-l1-v1.1.1.yml`

## Why This Patch Exists

`v1.1.0` introduced `governance_run_input_path`, but the released wrapper pointed to an older reusable workflow commit that did not yet define that input.

`v1.1.1` corrects that release packaging error without rewriting the older release tag.
