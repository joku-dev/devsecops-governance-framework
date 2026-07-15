# Automation Classification

The control library distinguishes between executable policy gates and broader automation support.

## Types

| Type | Meaning |
|---|---|
| `blocking_gate` | Objective automated check that may block merge, release, deployment, or governance approval. |
| `warning_gate` | Objective automated check that reports a deviation but does not block in the initial rollout. |
| `evidence_check` | Automated check for required evidence presence, linkage, completeness, or freshness. |
| `review_check` | Human judgment remains primary; automation can route, track, and verify that the review happened. |

## Maturity

| Maturity | Meaning |
|---|---|
| `immediate` | Can be implemented with basic repository, CI/CD, artifact, or governance metadata. |
| `tool_integration_required` | Requires integration with specific enterprise tools such as ALM, IAM, artifact repositories, logging, or monitoring systems. |
| `future` | Requires advanced capabilities such as provenance, reproducible build infrastructure, evidence graph, or runtime attestation. |

## Check Types

| Check Type | Meaning |
|---|---|
| `presence` | Required evidence or configuration exists. |
| `linkage` | Evidence is linked to the correct requirement, artifact, release, deployment, or runtime object. |
| `threshold` | A numeric, severity, maturity, or risk threshold is evaluated. |
| `configuration` | Repository, platform, IAM, pipeline, or tool configuration is checked. |
| `approval` | Approval or waiver state is checked. |
| `review` | Review evidence and decision status are checked. |
| `integrity` | Checksum, digest, signature, reproducibility, or runtime integrity is checked. |
| `provenance` | Origin, dependency provenance, or build provenance metadata is checked. |

## Interpretation

`policy_as_code.candidate` should be used for controls that can become executable rules. `automation.type` is broader and includes evidence-based checks. This allows the automation coverage to increase without pretending that every requirement is a hard deny rule.

Every control should also define a `verification_requirement`. This is the machine-checkable version of the normative requirement. It does not replace the normative statement; it defines how evidence, linkage, configuration, threshold, approval, integrity, provenance, or review status can be verified.
