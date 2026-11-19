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

Hash-locked files are used by intake, operations, portfolio, retry and
documentation publication workflows. The bootstrap, Governance CI and
Self-Security workflow remain inside the personally accepted lifecycle
implementation manifest. Changing their install command requires a new
operating-acceptance revision; the current accepted pilot must not be silently
invalidated to improve dependency-installation coverage.

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
4. Evidence-agent provenance validation.
5. The complete unit-test suite.

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
2. Regenerate `requirements-validation.lock` and `requirements-docs.lock` with
   `pip-compile --generate-hashes`, and review the version and hash changes.
3. Update the OPA version and all four official asset checksums in
   `scripts/validation-toolchain.env`.
4. Align all governance workflows that install Python or OPA with the pinned
   requirements and version (`governance-ci`, intake workflows, and the
   architecture baseline workflow).
5. Recreate the local environment and run complete validation.
6. Review and commit only intentional source changes; omit generated
   timestamp-only noise.

Do not replace a pinned OPA version with `latest`. The bootstrap rejects a
download whose checksum differs from the reviewed value.

## Troubleshooting

If validation reports an incomplete environment, rerun the bootstrap. If the
Python interpreter changed, delete the selected validation environment first
and recreate it. If checksum verification fails, do not bypass it; verify the
official OPA release asset and update the reviewed checksum in a separate,
explicit toolchain maintenance change.

## V2 complete suite candidate

The separate V2 entry is `scripts/run_axiom_v2_validation_suite.py`. It starts
with the Python standard library, checks the selected environment, then changes
to that environment's interpreter. It shares the bootstrap writer's environment
lock as a reader; an incomplete bootstrap owner requires explicit reconciliation.
It does not install or repair dependencies. Prepare them explicitly with
`scripts/bootstrap_axiom_v2_environment.py`.

Check only the selected pinned toolchain:

```bash
python3 scripts/run_axiom_v2_validation_suite.py \
  --environment /absolute/private/validation-env --check-tools
```

Run the complete chain from a clean committed V2 source and its exact prepared
package for this host:

```bash
python3 scripts/run_axiom_v2_validation_suite.py \
  --environment /absolute/private/validation-env \
  --instance /absolute/private/validation-node \
  --package /absolute/private/prepared-runtime.zip \
  --sha256 PACKAGE_SHA256 --at 2026-11-15T12:00:00Z \
  --state-directory /absolute/private/suite-records
```

Choose separate private environment, instance and record directories outside the
product source. The package must match this exact committed source, platform,
OPA and prepared dependencies. A missing instance is initialized paused with its
own key; an existing foreign or partial instance is rejected. Full execution
does not accept development overrides or a unit-test skip. The native unit
worker needs Git, Node and OpenSSL in the operator's tool path.

The finite core preserves the original order: tool presence, OPA version, all
six dependency pins, `pip check`, readiness text, OPA compilation, runtime,
repository, provenance and complete unit discovery. Each first nonzero result
stops later work. Runtime and repository generated effects become an exact
private overlay shared with subsequent phases. Consumer programs never execute.

Every started phase has a private durable intent. Raw native outputs and final
legacy streams remain separate from the JSON summary. `--output legacy` emits
the original phase streams and shell exit convention, including `128 + signal`;
JSON output distinguishes known validation failure (1) from incomplete execution
(2). A ready-toolchain message alone does not mean full validation passed.

Use `--inspect /absolute/private/suite-records/RECORD` to check retained evidence
without repeating native validation. Inspection replays the suite decisions,
binds captured streams and component files, replays provenance and checks the
unit summary. Runtime/repository semantic replay occurs during creation; their
later inspection here checks byte closure and result binding. It does not
authenticate execution, recheck the live environment, resume an interrupted
phase or grant operating approval. Keep incomplete records for diagnosis and
start any authorized retry as a fresh operation.

The original protected shell entry remains unchanged. Its unquoted OPA expansion
fails for environment paths containing spaces; the V2 adapter invokes the exact
selected tool as an argv element. Original shell comparisons retain that
limitation explicitly. The full current-source Mac/Linux acceptance and complete
V1 parity remain separate delivery requirements; this candidate alone does not
complete the Goal.
