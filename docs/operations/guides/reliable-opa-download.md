# Reliable pinned OPA installation

The OPA transport follow-up is [GCR-2026-157](../../governance/change-requests/GCR-2026-157-reliable-opa-download.md).
OPA version and checksums still come exclusively from
`scripts/validation-toolchain.env`. Linux uses the static binary. No released
baseline, OPA policy or enforcement mode is changed.

## Local use and shared CI setup

```bash
python3 scripts/install_validation_opa.py
./scripts/bootstrap_validation_env.sh
./scripts/validate_all.sh
```

Python 3.11+ and curl are required. The installer prepares only OPA; the preserved
bootstrap prepares the Python environment. OPA is installed to
`.venv-validation/bin/opa` by default. It checks an existing installation, then a
local cache, then downloads. Every candidate must match the pinned SHA-256 before
it is made executable and its version is checked. Installation/cache writes are
atomic; a failed download never replaces an existing file. Cache content is data,
not authority. Symlinked cache entries/directories are rejected.

`.github/actions/setup-opa-verified` shares this implementation. It restores only
an exact cache identity containing version, platform asset and SHA-256. Restored
bytes are checked again. A cache-service failure can fall back to downloading;
installer verification failure fails the job. Only a verified binary is saved.
If an immutable GitHub cache entry is corrupt, delete that exact cache key in
Actions → Caches after investigation; the next successful installation repopulates
it. A cache miss or cache eviction does not change the expected bytes.

For a local offline installation:

```bash
python3 scripts/install_validation_opa.py --offline
```

This succeeds only with an already verified installation/cache entry. The default
local cache is ignored `.local/tool-cache/axiom-opa/`; CI uses
`RUNNER_TOOL_CACHE/axiom-opa/`.

## Transport order, limits and recovery

The installer tries these sources in order:

1. An optional configured HTTPS mirror.
2. The exact public OPA GitHub release asset.
3. The exact public GitHub release-asset API endpoint with octet-stream delivery.

The asset IDs in `scripts/opa-download-sources.json` were checked against the
[official v1.18.2 release metadata](https://api.github.com/repos/open-policy-agent/opa/releases/tags/v1.18.2).
This file selects transports; it cannot override the version or SHA-256 authority.
Version updates need coordinated source metadata and checksum review.

Defaults are three attempts per source, a ten-second connection timeout, at most
120 seconds per attempt, bounded exponential waits and a 128 MiB download limit.
`--attempts` accepts 1–5 and `--timeout` accepts 1–300 seconds. Partial files are
removed before retrying. A checksum mismatch skips to the next source; mismatching
bytes are never executed or cached. All transports enforce HTTPS redirects.
The installer sends no GitHub token or mirror credential and avoids printing URLs
or proxy-response bodies. A failed final installation fails closed.

The two official routes share GitHub infrastructure. They are alternative
transports, **not independent providers**. GitHub caches can also be evicted.
No independent internal mirror was available when this change was prepared, so
this implementation does not promise operation through a complete GitHub outage.

An administrator can later set repository variable `AXIOM_OPA_MIRROR_URL` to an
HTTPS base serving `/v1.18.2/opa_linux_amd64_static` and other needed assets. For
example, `https://artifacts.example.invalid/approved/opa` is a placeholder, not a
configured endpoint. Mirror bytes must pass the same repository SHA-256; inline
credentials, query strings and fragments are rejected. Provisioning a mirror,
its access controls and backup/availability is a separate infrastructure task.

After a transient failure, Actions → failed workflow run → **Re-run failed jobs**
retries the same revision. Inspect the failed step first: retrying transport errors
does not grant permission to ignore a model, policy or integrity failure.

## Accepted pilot and CI migration

`governance-ci.yml`, `bootstrap_validation_env.sh`, `validation-toolchain.env` and
all other fingerprinted implementation files remain byte-identical. The existing
GRS-002 and consumer operating-acceptance records retain their effective meaning.
The legacy CI still uses its accepted installer, and can still fail on that
external transport while this migration is under review.

`governance-ci-v2.yml` is a parallel, versioned candidate with its own workflow
name, job (`validate-and-report-v2`) and artifact (`governance-reports-v2`). It
prepares OPA with the shared installer, delegates Python setup to the unchanged
bootstrap, and runs the full pinned validation, lifecycle history checks and
strict documentation build. Its results do not replace required legacy checks,
accepted operating evidence or provider workflows. The Docs publication workflow,
which is outside both acceptance manifests, uses the shared installer directly.

Before replacing/disabling the accepted CI or changing required check names,
prepare and personally approve the versioned operating-acceptance migration.
Keep its source history and provider proof; do not rewrite old acceptance hashes
or self-issue a personal acceptance. This transport PR prepares the successor
without changing that authority. See the
[existing operating runbook](../evidence/governance-lifecycle-live-operation.md).

## Validation

```bash
python3 -m unittest discover -s tests -p test_opa_download.py
./scripts/bootstrap_validation_env.sh
./scripts/validate_all.sh
mkdocs build --strict
```

Tests cover platform pins, transient errors, partial files, alternate transport,
offline cache reuse, corrupt caches/sources, wrong versions, symlinks, mandatory
verification and unchanged accepted implementation manifests. Live transport checks
use exact upstream artifacts and compare their full digests; fixtures never issue
an operating approval or modify canonical governance state.
