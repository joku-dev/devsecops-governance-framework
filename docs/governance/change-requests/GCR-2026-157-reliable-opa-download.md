# GCR-2026-157 — Reliable checksum-pinned OPA transport

## Request and incident

The maintainer authorizes both retrying failed jobs and preparing a durable
transport improvement. After the approved Workbench PR #336 merged as `7a00a13`,
Governance CI and Docs publication repeatedly failed with HTTP 504 during OPA
installation, before their validation/build steps. The exact approved PR passed
CI; local pinned validation on the merged tree passed 841 tests and MkDocs strict.
The separate Lifecycle Guard recovered when retried.

## Artifact intake classification

| Field | Classification |
|---|---|
| Owner and type | Governance Platform Maintainers; operational downloader, shared CI action, versioned validation successor, tests and guide |
| New artifacts | `scripts/install_validation_opa.py`, transport asset metadata, `.github/actions/setup-opa-verified/`, `governance-ci-v2.yml`, tests and operational guide |
| Source intake | No normative document, source registration or requirements derivation |
| Enforcement/evidence | Validation fails on installation/integrity errors; no OPA semantics, consumer enforcement or accepted evidence changes |
| Release | Tooling follow-up; no baseline package/tag changes |
| Operating acceptance | Preserve every file in both accepted implementation manifests; legacy CI/required checks and personal approval stay unchanged |

## Implemented behavior

1. Read version/platform SHA-256 from the preserved toolchain file. Linux uses
   static OPA. Cache, mirror, direct release and API delivery all require the
   same SHA-256 before execution, then the exact version before atomic installation.
2. Use bounded retries, timeouts and partial-file cleanup. A bad checksum moves
   to another source without executing or caching it. Exhausted transports fail
   the installer/job and retain any existing destination file.
3. Reuse exact GitHub/local cache identities, revalidate restored bytes, and use
   the exact public release-asset API as another transport. No credentials are
   forwarded. Reject unsafe mirror URLs and symlinked cache entries/directories.
4. No internal artifact store currently exists. Expose an optional HTTPS mirror
   variable and document its required path/digest contract. Alternative GitHub
   routes and cache do not create an independent provider or an availability SLA.
5. Use the shared setup in Docs publication. Prepare a parallel CI v2 that runs
   the preserved bootstrap and complete validators. The accepted CI file is not
   edited, disabled, reclassified or silently replaced by a similarly named check.

## Versioned migration and limits

The accepted operating pilot fingerprints the existing Governance CI, bootstrap
and toolchain. Both operating-acceptance manifests and every bound file remain
unchanged. The v2 workflow has a distinct name/job/artifact; it is reviewable
technical preparation, not a personal operating acceptance or a replacement for
required legacy CI. Activating it as the accepted successor requires its own
versioned personal acceptance and explicit required-check migration. The agent
must not publish that personal statement or alter old acceptance history.
The legacy downloader may continue to encounter the upstream incident until
recovery or the separately accepted migration. This PR does not conceal that gap.

The user deferred VM/team-server installation; no artifact server or credential
store is provisioned. Public Workbench/Viewer semantics and released baselines
are unchanged. Existing local tools continue to work with the original bootstrap.

## Validation and delivery

Behavioral tests inject transport failures and synthetic binaries. They verify
fallback, byte/version gates, offline cache reuse, poisoned/partial files,
symlink boundaries and unchanged accepted implementation fingerprints. Pinned
bootstrap/full repository validation, MkDocs strict, a real full artifact hash
check and revision-bound role reviews precede signed commit/PR. Delivery records
actual remote retry outcomes and any remaining external dependency failure.

## Local verification

Pinned bootstrap and full `validate_all.sh` passed **858 tests**, including
**17 new downloader regressions**. MkDocs strict and composite shell/YAML syntax
checks passed. A complete Linux static OPA download through the official asset
API matched the existing pinned SHA-256. Native macOS installation from the cache
and reuse of the installed binary both passed in offline mode. All files in both
accepted implementation manifests remain byte-identical. Generated validation
noise is excluded. Exact signed revision, declared role review and remote CI
outcomes are recorded in the PR. Legacy retry failures remain an explicit
transport incident, not a successful validation claim.
