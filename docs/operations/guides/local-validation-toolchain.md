# Local Validation Toolchain

## Purpose

Use the repository-managed validation toolchain to run governance checks with
the same pinned Python dependencies and OPA version on supported macOS and
Linux workstations.

The toolchain is operational support only. It does not change policies,
released baselines, enforcement modes, or downstream evidence contracts.

## Prerequisites

Install these host tools:

- Bash
- Python 3 with `venv` support
- `curl`
- either `sha256sum` or `shasum`

The bootstrap supports Intel and ARM64 on macOS and Linux. It installs nothing
globally.

## Prepare The Environment

From the repository root, run:

```bash
./scripts/bootstrap_validation_env.sh
```

The script creates `.venv-validation`, installs the exact versions from
`requirements-validation.txt`, downloads the OPA version declared in
`scripts/validation-toolchain.env`, and verifies the platform-specific SHA-256
checksum before installing the binary.

The directory is ignored by Git and can be deleted and recreated at any time.

## Run Complete Validation

Run:

```bash
./scripts/validate_all.sh
```

This executes, in order:

1. OPA policy syntax validation.
2. Architecture runtime governance validation.
3. Governance repository validation.
4. The complete unit-test suite.

Check only the prepared toolchain with:

```bash
./scripts/validate_all.sh --check-tools
```

## Custom Installation Location Or Python

Use environment variables when the default location or interpreter is not
suitable:

```bash
PYTHON_BIN=python3.11 \
VALIDATION_VENV=/tmp/devsecops-governance-validation \
./scripts/bootstrap_validation_env.sh

VALIDATION_VENV=/tmp/devsecops-governance-validation \
./scripts/validate_all.sh
```

Use the same `VALIDATION_VENV` value for bootstrap and validation.

## Updating The Toolchain

Treat dependency changes as an intentional maintenance change:

1. Update exact Python versions in `requirements-validation.txt`.
2. Update the OPA version and all four official asset checksums in
   `scripts/validation-toolchain.env`.
3. Align all governance workflows that install Python or OPA with the pinned
   requirements and version (`governance-ci`, intake workflows, and the
   architecture baseline workflow).
4. Recreate the local environment and run complete validation.
5. Review and commit only intentional source changes; omit generated
   timestamp-only noise.

Do not replace a pinned OPA version with `latest`. The bootstrap rejects a
download whose checksum differs from the reviewed value.

## Troubleshooting

If validation reports an incomplete environment, rerun the bootstrap. If the
Python interpreter changed, delete the selected validation environment first
and recreate it. If checksum verification fails, do not bypass it; verify the
official OPA release asset and update the reviewed checksum in a separate,
explicit toolchain maintenance change.
