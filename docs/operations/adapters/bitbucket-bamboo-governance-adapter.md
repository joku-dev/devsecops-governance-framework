# Bitbucket Data Center and Bamboo Governance Adapter

The intended company path is Bitbucket Data Center with Bamboo; installed
versions and live API/Specs compatibility remain unconfirmed. The historical
12.1.9 template assumption is not a verified deployment. Continue the accepted
GitHub integration until a separately reviewed adoption is ready.

## Portable candidate

The current `pipeline-baseline/templates/bamboo/bamboo-specs/bamboo.yaml` invokes
the [portable runtime v1](portable-governance-runtime.md). It requires a prepared,
commit-pinned runtime and tools, reviewed SCM/CI profile and real build/scanner
outputs. SCM and CI are independent axes. The documented native Bitbucket path
collects repository identity, exact branch PR-only restrictions and required
approver settings; unsupported effective rules and missing permissions stay
explicit. No synthetic security files or separate Bamboo gate are generated.

| Setting | Meaning |
|---|---|
| `axiom.runtime` | Operator-prepared exact runtime checkout |
| `axiom.python` | Python environment with hash-pinned dependencies |
| `axiom.opa` | Checksum/version-verified OPA binary |
| `axiom.profile` | Reviewed operator-owned v1 profile outside application source |
| `axiom.mode` | Defaults to `report-only` |

The application supplies its real artifact, artifact-bound CycloneDX SBOM and
normalized vulnerability scan before the evaluation task. Results, execution
state, diagnostics, unverified Trust and unverified external enforcement remain
separate. The generated result concerns pipeline-L1 scope, not full compliance.
Final tasks preserve a diagnostic when earlier setup/evaluation could not run;
Bamboo artifacts retain the result directory.

## Adoption and legacy boundary

Adopting the new mainline template is explicit. Migrate the former
`governance.*`/`bitbucket.*` template variables to runtime/profile configuration,
provide real scanner data and use the new `portable-evidence/` outputs. The old
starter generator remains callable for old pins. Released snapshots/tags and
accepted GitHub lifecycle profiles are unchanged. This adapter description is
technical guidance, not a normative source or an authority for baseline changes.

New adoption stays report-only. A later blocking switch needs accountable
approval, actual platform readiness, effective required-status checks and the
existing waiver/rollback criteria. See [Blocking Readiness](../status/blocking-readiness.md).
The GitHub GRS-002 acceptance does not authorize Bitbucket lifecycle operation.

The optional architecture template and earlier root-level sketches remain
separate historical/reference paths. Architecture governance is parked. M2's
native evidence transport/verifier, central publication and VM state migration
remain separate deliverables. Local fixtures and YAML parsing prove neither
installed-version compatibility nor a live deployment.
