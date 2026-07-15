# Runtime Governance Addendum

## Status

This addendum extends `docs/governance/source-documents/ARCH-SDD-SRC-001.public.md` with a machine-readable runtime governance layer.

The source document remains the normative architecture governance reference. This addendum defines how selected governance concepts are represented as structured data, evidence contracts and policy-as-code checks.

## Purpose

The SDD Architecture Governance Framework describes how Enterprise, Solution and Product Architecture should be governed. Runtime governance makes selected parts executable.

Runtime governance answers four practical questions:

| Question | Runtime governance answer |
|---|---|
| Is the architecture ready? | Critical markers are designed, owned and process-aware. |
| Is integration ready? | Interfaces, data contracts, security boundaries and deployment assumptions are explicit. |
| Is release ready? | Release-critical markers are verified or covered by valid exceptions. |
| Is operation ready? | Runtime evidence, observability and feedback loops exist. |

## Source Document Mapping

| Source concept | Source location | Runtime artifact |
|---|---|---|
| Quality marker scoring | Section 5.2 | `architecture/quality-markers.yaml` |
| BAPO alignment markers | Section 5.4, Table 53 | `architecture/quality-markers.yaml` |
| Enterprise/Solution/Product quality markers | Sections 5.5 to 5.7 | `architecture/quality-markers.yaml` |
| Runtime, platform and Edge/Fog/Cloud guardrails | Section 6.9 | `architecture/guardrails.yaml` |
| DevSecOps and continuous release guardrails | Section 6.10 | `architecture/guardrails.yaml` |
| Architecture exception process | Section 6.12 and Section 10.9 | `architecture/guardrails.yaml` and `policies/opa/architecture_release_readiness.rego` |
| Architecture quality marker reviews | Section 5.8 and Chapter 9 | `architecture/review-gates.yaml` |
| Release compatibility declaration | Section 10.10 | `policies/opa/architecture_release_readiness.rego` |

## Machine-Readable Artifacts

The first addendum version introduces these structured files:

| File | Purpose |
|---|---|
| `architecture/quality-markers.yaml` | Defines initial BAPO, Solution and Product markers with score evidence expectations. |
| `architecture/guardrails.yaml` | Defines initial runtime, DevSecOps, interface and exception guardrails. |
| `architecture/review-gates.yaml` | Defines architecture, integration, release and operation readiness gates. |
| `architecture/arch-l1.yaml` | Defines architecture minimum evidence requirements. |
| `architecture/arch-l2.yaml` | Defines integration and release readiness requirements. |
| `architecture/arch-l3.yaml` | Defines runtime and continuous improvement requirements. |
| `architecture/arch-gov.yaml` | Defines architecture governance requirements for guardrails, gates and exceptions. |
| `schemas/quality-marker.schema.json` | JSON Schema for marker catalogues. |
| `schemas/architecture-guardrail.schema.json` | JSON Schema for guardrail catalogues. |
| `schemas/review-gate.schema.json` | JSON Schema for runtime review gates. |
| `schemas/architecture-level.schema.json` | JSON Schema for architecture level requirement sets. |
| `schemas/architecture-release-candidate.schema.json` | JSON Schema for architecture release candidate policy input. |
| `schemas/architecture-exception.schema.json` | JSON Schema for reusable architecture exception records. |
| `policies/opa/architecture_release_readiness.rego` | OPA policy for release-readiness checks. |
| `policies/opa/architecture_readiness.rego` | OPA policy for architecture-readiness checks. |
| `policies/opa/architecture_integration_readiness.rego` | OPA policy for integration-readiness checks. |
| `policies/opa/architecture_operation_readiness.rego` | OPA policy for operation-readiness checks. |
| `policies/example-input.architecture-release-candidate.json` | Example policy input for an architecture release candidate. |
| `generated/csv/architecture_runtime_traceability.csv` | Generated traceability view from architecture levels to markers, guardrails, gates, evidence and policies. |

## Runtime Gate Model

The runtime gate model is derived from the framework's marker scoring model.

| Gate | Minimum expectation |
|---|---|
| Architecture readiness | BAPO markers B1-B4 and applicable critical markers are at least score 3. |
| Integration readiness | Integration-critical interface, security and deployment markers are at least score 3. |
| Release readiness | Release-critical markers are at least score 4 or covered by a valid exception. |
| Operation readiness | Operation-critical markers have runtime evidence and feedback loops. |

The first executable policy implements release readiness because it has the clearest runtime decision boundary.

## Architecture Level Model

The architecture addendum uses the same mechanics as the DevSecOps control baseline: structured YAML requirements, schema validation, evidence expectations, automation classification and policy-as-code candidates.

The architecture levels use architecture-specific semantics:

| Level | Meaning | Primary decision |
|---|---|---|
| `ARCH-L1` | Architecture minimum evidence | Is the architecture sufficiently described, owned and traceable to start implementation? |
| `ARCH-L2` | Integration and release readiness | Can products be integrated and released against a solution baseline with evidence? |
| `ARCH-L3` | Runtime and continuous improvement | Is the running capability observable, measured and improved through feedback? |
| `ARCH-GOV` | Architecture governance | Are guardrails, review gates and exceptions governed as reusable enterprise assets? |

The levels are not intended to replace Enterprise, Solution and Product Architecture. They provide a runtime governance progression across those architecture scopes.

Generate the architecture traceability view with:

```bash
python3 scripts/generate_architecture_traceability_csv.py
```

## Release Readiness Rule

A release candidate fails the first architecture release-readiness policy when:

- a release-critical marker is missing
- a release-critical marker is below score 4 and has no valid exception
- the release compatibility declaration is missing, incomplete or unapproved
- the solution baseline is missing
- compatibility evidence is missing
- security evidence is missing
- deployment evidence is missing
- an approved exception is expired or lacks owner or mitigation

The current release-critical markers are:

| Marker | Meaning |
|---|---|
| E6 | Security guardrails |
| E7 | DevSecOps guardrails |
| E8 | Platform alignment |
| S3 | Cross-product interface maturity |
| S5 | Integrated security |
| S6 | Release architecture |
| S8 | Solution resilience |
| P5 | Deployment reproducibility |
| P6 | Interface and data contract quality |
| P8 | Security implementation |
| P9 | Performance and determinism |
| P10 | Product resilience |
| P13 | Release compatibility |

## Exception Handling

Exceptions are treated as controlled architecture risk decisions, not as proof of compliance.

For runtime governance, an approved exception must have at least:

- ID
- status
- applicable marker or guardrail
- owner
- mitigation
- risk classification
- review date
- expiry date
- approval authority
- non-expired validity

Conditions, evidence and follow-up actions are optional in the current schema, but should be used for conditional approvals and release-relevant deviations.

## How To Run The First Policy

Evaluate the example release candidate with OPA:

```bash
opa eval --data policies/opa/architecture_release_readiness.rego --input policies/example-input.architecture-release-candidate.json "data.architecture.release_readiness.deny"
```

An empty result set means the example passes the current release-readiness policy.

## Next Iterations

The current addendum is intentionally small. The next useful increments are:

1. Add integration-readiness and operation-readiness OPA policies.
2. Add policy tests for passing and failing release candidates.
3. Add generated CSV/HTML traceability from source document sections to runtime governance artifacts.
4. Add scripts that validate all architecture runtime governance YAML and example policy inputs in one command.
5. Add evidence producer mappings for CI/CD, deployment, monitoring and architecture review systems.
