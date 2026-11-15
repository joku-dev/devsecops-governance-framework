# Bamboo and Bitbucket portable pipeline candidate

`bamboo-specs/bamboo.yaml` now invokes the shared versioned
`scripts/governance_runtime.py run` evaluator. It creates no placeholder SBOM or
scan and contains no independent gate logic. Copy it into an application
repository's `bamboo-specs/bamboo.yaml` and add the application's actual build and
scanner tasks before evaluation. The job begins with a clean checkout.

Prepare a reviewed exact runtime checkout, hashed Python dependencies, verified
OPA and an operator-owned profile on the agent. Set `axiom.runtime`,
`axiom.python`, `axiom.opa`, `axiom.profile` and `axiom.mode`. The profile selects
SCM independently from Bamboo CI. Keep reader credentials in its secret
environment variable; no credential values belong to the profile or artifacts.

Real inputs are `dist/application-source.tar.gz`, `security/sbom.cyclonedx.json`
and `security/vulnerability-scan.json`. Output is under `portable-evidence/`,
including result and redacted diagnostics; final tasks retain a diagnostic if
the runtime never started. Report-only findings exit 0; incomplete evaluation or
technical failure exits 2. No required merge checks are installed.

This is an unreleased pipeline-L1 candidate. It replaces the old mainline
placeholder template; archived/tagged releases and legacy CLI entrypoints stay
unchanged. Existing adoptions must explicitly migrate agent paths, profile,
evidence bindings and output names. The old `governance.*`/`bitbucket.*` variables
are not the new interface. See the
[portable runtime guide](../../../../docs/operations/adapters/portable-governance-runtime.md).

The former 12.1.9 assumption is historical, not an installed-version claim.
Validate Specs import and native API behavior on the actual Bamboo/Bitbucket DC
versions before live adoption. Root-level `.yml` sketches and the separate
architecture template remain historical/separate paths; architecture governance
is parked for this portability work. No central VM intake, publisher activation
or operational platform acceptance is implied.
