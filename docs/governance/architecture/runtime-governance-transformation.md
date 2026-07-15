# Runtime Governance Transformation

## Purpose

The input document `docs/governance/source-documents/ARCH-SDD-SRC-001.public.md` is a strong normative architecture governance framework, but it is not yet optimized for runtime governance.

Runtime governance requires the framework to be expressed as:

- structured governance data
- evidence contracts
- machine-checkable policy rules
- lifecycle gates
- exception handling
- feedback from delivery and operation

The target is not to replace the architecture framework. The target is to make it executable.

## Current Strengths

The document already contains the most important concepts for runtime governance:

| Area | Runtime governance relevance |
|---|---|
| BAPO alignment | Provides traceability from business intent to architecture, process, and ownership. |
| Enterprise/Solution/Product levels | Provides natural policy scopes and decision boundaries. |
| Quality marker model | Provides a maturity model that can become readiness scoring. |
| Evidence-based architecture | Provides the basis for automated evidence collection and review. |
| Runtime and platform guardrails | Provides deployability, operability, observability, update, and rollback concerns. |
| DevSecOps guardrails | Provides CI/CD, security scan, release evidence, and pipeline control concerns. |
| Exception process | Provides the controlled deviation model needed for waivers. |
| Release compatibility declaration | Provides the core artifact for independent product releases and solution baselines. |

## Main Gap

The document currently describes governance mainly in prose and review language. Runtime governance needs deterministic data and rules.

The most important missing elements are:

- stable IDs for every guardrail, marker, evidence requirement, and review gate
- explicit criticality per marker or guardrail
- machine-readable evidence requirements
- clear score thresholds for architecture readiness, release readiness, and operation readiness
- policy inputs for product, solution, release, deployment, and runtime evidence
- explicit mapping between exceptions and the rules they waive
- feedback rules for recurring findings, expired exceptions, low marker scores, and operational incidents

## Recommended Refactoring

The framework should be adapted from a document-first structure to a model-first structure.

Recommended source structure:

```text
architecture/
  bap-o-markers.yaml
  quality-markers.yaml
  guardrails.yaml
  review-gates.yaml
  release-compatibility.yaml
  runtime-evidence.yaml
```

Recommended generated views:

```text
generated/
  html/
  csv/
  reports/
```

Recommended policy implementation:

```text
policies/opa/
  architecture_marker_readiness.rego
  bap_o_traceability.rego
  release_compatibility.rego
  runtime_deployment_guardrails.rego
  architecture_exception_validity.rego
```

## Runtime Governance Model

The runtime model should evaluate architecture governance at four decision points.

| Gate | Purpose | Typical decision |
|---|---|---|
| Architecture readiness | Checks whether design, ownership, process, and evidence plan exist. | Can implementation proceed? |
| Integration readiness | Checks whether interfaces, data contracts, security boundaries, and deployment assumptions are aligned. | Can products be integrated? |
| Release readiness | Checks whether required evidence exists and compatibility is declared. | Can the product or solution release? |
| Operation readiness | Checks whether runtime evidence, observability, incident feedback, and improvement loops exist. | Can the capability operate and improve? |

## Marker Scoring Interpretation

The existing score model should be retained, but converted into gate thresholds.

| Score | Runtime interpretation |
|---|---|
| 0 | Missing; must fail if marker is applicable and critical. |
| 1 | Mentioned; insufficient for architecture readiness. |
| 2 | Described; may be acceptable for early concept review only. |
| 3 | Designed and owned; minimum for architecture readiness. |
| 4 | Verified; minimum for release-critical markers. |
| 5 | Continuously measured and improved; target for operation-critical markers. |

Recommended default thresholds:

| Gate | Minimum threshold |
|---|---|
| Architecture readiness | Applicable critical markers must be at least score 3. |
| Integration readiness | Applicable interface, data, security, deployment, and BAPO markers must be at least score 3; integration-critical markers should have evidence for score 4 where available. |
| Release readiness | Release-critical markers must be at least score 4 or covered by a valid exception. |
| Operation readiness | Operation-critical markers should reach score 5 or have explicit improvement actions. |

## Policy Input Domains

Runtime governance needs input data from several domains.

| Domain | Example evidence |
|---|---|
| Architecture | Architecture document, ADR register, BAPO map, marker assessment. |
| Interface | API contracts, schema versions, topic definitions, contract tests. |
| Data | Data contracts, semantic mapping, classification, ownership. |
| Security | Threat model, vulnerability scan, crypto review, trust-zone model. |
| DevSecOps | Build record, test result, SBOM, artifact digest, signature, pipeline status. |
| Deployment | Deployment manifest, environment compatibility matrix, rollback evidence. |
| Runtime | Logs, metrics, traces, health indicators, monitoring dashboard. |
| Release | Solution baseline, compatibility declaration, release approval. |
| Governance | Review record, exception, waiver, technical debt item, follow-up action. |

## First Automation Candidates

The first runtime governance policies should be deliberately narrow and objective.

Recommended first policies:

1. Release candidates must have a current release compatibility declaration.
2. Release-critical quality markers must be score 4 or have a valid exception.
3. Every exception must have an owner, mitigation, review date, expiry date, and approval authority.
4. Cross-product interfaces must have owner, version, contract, and test evidence.
5. Runtime deployment evidence must include deployment manifest, environment compatibility, observability, and rollback evidence.
6. DevSecOps evidence must include build, test, security scan, artifact integrity, and release evidence.
7. BAPO markers B1-B4 must be at least score 3 before architecture readiness.
8. BAPO marker B5 must be present before release readiness and measurable for operation readiness.

## Required Change To The Framework Document

The document should be adjusted in five ways:

1. Add a dedicated chapter `Runtime Governance Model`.
2. Add stable identifiers to guardrails, markers, review gates, templates, and evidence types.
3. Convert narrative marker tables into structured marker definitions.
4. Define readiness gates and default score thresholds.
5. Treat the Markdown/PDF as a generated or reviewable view, not as the only source of governance truth.

## Recommended Next Step

Create the first structured architecture governance data set from the input document:

```text
architecture/quality-markers.yaml
architecture/guardrails.yaml
architecture/review-gates.yaml
schemas/quality-marker.schema.json
schemas/architecture-guardrail.schema.json
```

Then implement a first OPA rule for release readiness:

```text
policies/opa/architecture_release_readiness.rego
```

This would turn the framework from a readable governance document into an executable governance baseline.
