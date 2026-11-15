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

## Remaining V2 delivery

The complete V2 launcher and entrypoint/function inventory, exclusion of V1-only
execution paths from installation, reproducible separate package/install profile,
fresh-state admission and real isolated Mac/Linux smokes are subsequent work
within the same active Goal. Existing hosts are not switched by this increment.
The earlier accepted personal GitHub lifecycle pilot remains bound to its V1
source and authority. No new publisher, blocking check or platform authority is
activated by this document or an implementation PR.
