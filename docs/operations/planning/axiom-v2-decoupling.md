# AXIOM V2 decoupling: implementation record

The maintainer authorized the V2 version break and autonomous implementation on
15 November 2026. The root `AXIOM_V2_Decoupling_Codex_Goal.md` and
[GCR-2026-185](../../governance/change-requests/GCR-2026-185-axiom-v2-decoupling.md)
define its acceptance criteria. This page records implementation progress, not a
completed V2 release or operating acceptance.

## Provider boundary increment

The shared runtime evaluates unchanged policies. Context, native transport,
discovery, SCM proposals, native draft creation and publication live under
`scripts/lib/providers/`. Applications use `lib/provider_ports.py`; transport
failures and source fingerprints have neutral modules. The former portable
adapter import locations are compatibility aliases for V1 source tests, with
one implementation each. Runtime/verifier digests bind the new implementation
files. Prior receipts or shadow windows do not acquire the changed source pin.

The architecture check resolves local imports transitively from the reviewed
core roots. It rejects provider SDK/direct HTTP/legacy-client imports, native
API paths, hosts, environment variables and CLI commands in that closure.
Concrete provider selection is restricted to the composition/adapter boundary.
Browser links use the explicitly returned instance origin. The check is a
regression safeguard; source review and target-system tests remain necessary.

```sh
python scripts/validate_axiom_v2.py
python -m unittest discover -s tests -p 'test_axiom_v2_boundary.py'
python -m unittest discover -s tests -p 'test_provider_workbench.py'
```

## Explicit Workbench publication

Direct publication needs a private profile conforming to
`schemas/workbench-publication-v2.schema.json`. The
[GitLab-shaped example](../../examples/portable-runtime/workbench-publication-v2.example.json)
contains no credentials or live target. Replace its identity and paths with the
actual reviewed repository and provision the credential files privately. The
profile itself and its credential files must pass the ordinary private-file
validator; no token value belongs in Git, URLs or command arguments.

```sh
python scripts/serve_governance_workbench.py --port 8875 \
  --enable-pr --publication-profile /private/operator/workbench.json
```

Without `--enable-pr` the Workbench continues to prepare local review packets.
The V2 publication path has no implicit authenticated-CLI fallback. Reader,
publisher and Git credentials are explicit and independently referenced. The
adapter independently resolves the configured native repository and target,
checks the native clone URL, prepares an isolated private checkout and posts a
draft proposal through the selected SCM implementation. It never merges it.
The native response must confirm draft state; missing confirmation holds the
operation for reconciliation instead of retrying the mutation or claiming a
successful draft. Bitbucket's [8.19 API contract](https://developer.atlassian.com/server/bitbucket/rest/v819/api-group-pull-requests/)
includes the draft field; older or unspecified target versions are not certified
by the fixture test.

The packet scope permits only the exact draft change request and candidate
source/register additions, or unchanged registered source bytes for review.
Existing register entries cannot be rewritten. Binary source bytes survive
staging exactly; hooks, ambient Git config, redirects and interactive prompts
are disabled. Dirty source, changed remote base, conflicting prior attempts and
unknown mutation outcomes remain visible. No lost reply authorizes duplication.

Provider metadata contracts use GitHub's
[repository clone URL](https://docs.github.com/en/rest/repos/repos), GitLab's
[project HTTP repository URL](https://docs.gitlab.com/api/projects/) and
Bitbucket Data Center's native clone links. Fixture coverage is not live
compatibility acceptance of an unspecified GitLab/Atlassian edition/version.

## Fresh-instance launcher increment

`scripts/axiom_v2.py` is the explicit product entrypoint for the shared runtime,
evidence CLI, collector and Workbench. It accepts no arbitrary script name and
does not expose old migration entrypoints. Existing directories cannot be
initialized as V2 instances. Each new instance receives a distinct node ID,
private state/credentials directories and Workbench key; its source revision,
runtime digest and checksum-approved OPA are bound in a private marker.

```sh
python scripts/axiom_v2.py --instance /private/operator/new-v2 init \
  --opa /absolute/pinned/opa --port 8875
python scripts/axiom_v2.py --instance /private/operator/new-v2 collector status
python scripts/axiom_v2.py --instance /private/operator/new-v2 workbench
```

Initialization requires clean source by default. `--development` explicitly
marks a source-development instance and keeps its collector paused and Workbench
publication disabled. A changed source/tool binding requires explicit update
handling, not a silent marker rewrite. Multiple/overriding path options cannot
redirect the shared CLIs to V1 state. A requested evidence restore creates an
inactive separate candidate directory; it does not activate that state.

## Offline distribution increment

The [complete function and entrypoint inventory](axiom-v2-function-inventory.md)
maps the 22 catalogue areas and every top-level Python script. The reviewed
`config/axiom-v2-distribution.json` selects the runtime import closure, provider
adapters, installation helpers and required data. Source-authoring tools remain
in the development checkout. Former V1 execution paths and the four import
facades are physically absent from the installed working tree.

The package builder retains an exact original Git commit/tree, with checksummed
OPA and hash-locked wheels for one target OS/architecture. Admission verifies
the independently supplied package hash, every member and the reconstructed Git
identity offline. After preparing a fresh environment, non-cone sparse checkout
retains only the reviewed runtime files. Source identity stays unchanged and
Git status stays clean. Historical baseline packages remain immutable data.
Full-source and sparse-source drift checks use the same active dependency set;
historical projections and unrelated documentation do not authorize executable
changes. Instantiation binds that set, revision, tool and runtime digests.

Build on the trusted development checkout, with an exact reviewed 40-character
`REVISION`, the target OPA and a wheelhouse containing both lock sets:

```sh
python scripts/package_governance_runtime.py build --revision "$REVISION" \
  --destination /private/operator/v2-mac.zip --workbench \
  --opa /private/operator/opa-darwin-arm64 --wheelhouse /private/operator/wheels-mac \
  --system Darwin --machine arm64
# Linux uses --system Linux --machine x86_64 and its own OPA/wheels.
```

Keep the returned SHA-256 through a trusted independent channel. Transfer the
package without credentials. From the trusted reviewed installer checkout,
using the separately verified `PACKAGE_SHA256`:

```sh
python scripts/install_axiom_v2.py /private/operator/v2-mac.zip \
  --sha256 "$PACKAGE_SHA256" --prefix /private/operator/new-v2 --port 8875
/private/operator/new-v2/axiom-v2 check
/private/operator/new-v2/axiom-v2 collector status
/private/operator/new-v2/axiom-v2 workbench
```

On Linux choose a fresh user-owned prefix, for example
`/home/operator/.local/state/axiom-v2-candidate`, and an unused port. The prefix
contains `package/source`, its own `venv`, `instance` and private installation
receipt. It starts no services, imports no old key/drafts, and leaves collection
paused. The Workbench remains loopback-only; use a separate SSH tunnel for the
VM. Read its private key only through the operator's terminal; never publish it.
Do not reuse the V1 IaC service names or paths for this candidate.

An interrupted initialization writes no instance admission marker; a partial
prefix must be inspected and retained or deliberately removed by its owner
before retrying at a new path. Updates use a new package/prefix and a fresh
instance. Backup/restore is explicit and initially inactive. Rollback is stopping
the candidate process and using the preserved V1 installation; V2 never changes
its service, state or authority. A production service migration remains a
separate operating decision after the reviewable candidate.

## Candidate delivery and external acceptance

The [dated candidate acceptance record](../status/axiom-v2-candidate-readiness-2026-11-15.md)
records the actual isolated Mac/Linux installs, byte-identical rebuild and
nine-case business parity, separately from native live-provider acceptance.
The saved `tests/acceptance/axiom_v2_host_smoke.py` repeats that test against a
fresh installed prefix. Final revision-bound review/PR delivery remains part of
the Goal. Existing hosts are not switched by this candidate.
The earlier accepted personal GitHub lifecycle pilot remains bound to its V1
source and authority. No new publisher, blocking check or platform authority is
activated by this document or an implementation PR.
