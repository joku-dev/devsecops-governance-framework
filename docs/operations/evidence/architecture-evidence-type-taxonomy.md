# Architecture Evidence Type Taxonomy

Status: draft / proposal

## Purpose

This document proposes a neutral taxonomy for architecture evidence types.

It is intended as a discussion document for Enterprise Architecture, Solution Architecture, Product Architecture, Security, Operations, and Governance stakeholders.

It does not currently change schemas, collectors, OPA policies, workflows, or release baselines.

## Core Principle

An evidence type is not the same as a tool mandate.

For example, a model repository or exported architecture model can be strong evidence for model-based architecture, but the governance model should first define the evidence expectation:

```text
model_based_architecture
```

Then a specific organization, system class, assurance level, or architecture maturity level can decide whether acceptable evidence must be:

```text
sysml_model
uml_model
model_export
architecture_review_record
```

This keeps the governance model stable while allowing the company to define stricter notation, repository, export, or review requirements where needed.

## Current State

Architecture evidence is currently identified from two sources.

Structured application evidence:

```text
.governance/architecture/*.json
```

Current schema evidence types:

```text
solution_baseline
release_compatibility_declaration
security_evidence
deployment_evidence
resilience_evidence
operation_evidence
review_evidence
exception_evidence
feedback_evidence
```

Repository signals:

```text
docs/ARCHITECTURE.md
docs/DEPLOYMENT.md
docker-compose.yml
**/Dockerfile
tests/**/*.py
**/schemas/*.json
benchmark/reports/*benchmark.json
```

This is useful for onboarding and early runtime governance, but it is intentionally broad.

For a proposed mapping from existing architecture input evidence names to this neutral taxonomy, see:

```text
docs/operations/evidence/architecture-evidence-taxonomy-mapping.md
```

For an Enterprise Architecture decision brief based on this taxonomy, see:

```text
docs/operations/evidence/architecture-evidence-ea-decision-brief.md
```

For the complete Enterprise Architecture discussion package, see:

```text
docs/operations/evidence/architecture-evidence-ea-package.md
```

## Proposed Categories

| Category | Purpose |
|---|---|
| Architecture description | Explain structure, responsibility, context, and decisions. |
| Model-based architecture | Provide formal or semi-formal architecture models. |
| Interface and contract evidence | Prove interface ownership, compatibility, versioning, and tests. |
| Baseline and compatibility evidence | Prove a release is compatible with a solution or product baseline. |
| Security architecture evidence | Prove trust zones, threats, controls, crypto, identity, and security reviews. |
| Deployment and runtime evidence | Prove deployability, runtime assumptions, observability, and operations readiness. |
| Resilience and recovery evidence | Prove failover, degraded mode, restart, recovery, and DIL behavior where relevant. |
| Review and approval evidence | Prove architecture review, ownership, approval, and decision records. |
| Exception and waiver evidence | Prove controlled deviations, risk decisions, mitigation, ownership, and expiry. |
| Feedback and improvement evidence | Prove operational findings and review findings feed back into architecture improvement. |

## Proposed Evidence Types

### Architecture Description

| Evidence type | Description | Example refs |
|---|---|---|
| `architecture_document` | Human-readable architecture description. | `docs/ARCHITECTURE.md` |
| `context_view` | System context, external dependencies, users, missions, or capabilities. | C4 context, mission thread diagram |
| `building_block_view` | Components, services, modules, containers, or deployment units. | Component diagram, service map |
| `architecture_decision_record` | Decision and rationale record. | ADR file, decision log |
| `architecture_ownership_record` | Owner, reviewer, RACI, or responsibility evidence. | owner list, RACI |

### Model-Based Architecture

| Evidence type | Description | Example refs |
|---|---|---|
| `model_based_architecture` | Generic evidence that a controlled architecture model exists. | model repository, model package |
| `sysml_model` | SysML model evidence independent of vendor. | SysML export, model repository |
| `uml_model` | UML model evidence independent of vendor. | UML export, model repository |
| `model_export` | Reviewable model export, usually easier to inspect in CI. | PDF, HTML, XMI, generated report |
| `model_baseline_record` | Versioned model baseline and release relation. | baseline id, tag, checksum |
| `model_review_record` | Review and approval of the model. | review minutes, approval record |

### Interface And Contract Evidence

| Evidence type | Description | Example refs |
|---|---|---|
| `interface_catalogue` | List of interfaces, protocols, owners, versions, and consumers. | API catalogue |
| `interface_contract` | Machine-readable or formal contract. | OpenAPI, AsyncAPI, JSON Schema, Protobuf |
| `data_contract` | Data structures, semantic rules, compatibility guarantees. | schema, data dictionary |
| `contract_test_result` | Test result proving contract compatibility. | CI test report |
| `compatibility_matrix` | Matrix of product, interface, data, and deployment compatibility. | release matrix |

### Baseline And Compatibility Evidence

| Evidence type | Description | Example refs |
|---|---|---|
| `solution_baseline` | Baseline of participating product versions, interface versions, data contracts, and assumptions. | `.governance/architecture/solution-baseline.json` |
| `product_baseline` | Product-level architecture baseline. | product baseline record |
| `release_compatibility_declaration` | Declares release compatibility against a baseline. | `.governance/architecture/release-compatibility-declaration.json` |
| `baseline_delta_assessment` | Explains changes from previous baseline. | delta report |
| `migration_impact_assessment` | Explains downstream migration impact. | migration note |

### Security Architecture Evidence

| Evidence type | Description | Example refs |
|---|---|---|
| `security_architecture_review` | Security architecture review and decision record. | review record |
| `threat_model` | Threat model, assumptions, mitigations, and residual risks. | STRIDE, attack tree |
| `trust_zone_model` | Trust boundaries and data/control flows. | zone diagram |
| `identity_and_access_model` | Identity, authorization, service accounts, and privileged flows. | IAM model |
| `crypto_assumption_record` | Crypto usage, key ownership, algorithm constraints. | crypto review |
| `security_test_evidence` | Security test, scan, or verification evidence. | test report, scan output |

### Deployment And Runtime Evidence

| Evidence type | Description | Example refs |
|---|---|---|
| `deployment_document` | Deployment assumptions, environments, rollout, rollback. | `docs/DEPLOYMENT.md` |
| `deployment_manifest` | Concrete deployment configuration. | Helm, Compose, Kubernetes, Terraform |
| `runtime_configuration_evidence` | Runtime config and environment evidence. | config baseline |
| `observability_evidence` | Logs, metrics, health indicators, dashboards. | dashboard link, metric report |
| `operations_runbook` | Operational procedures and diagnostics. | runbook |
| `rollback_evidence` | Rollback strategy and test result. | rollback test |

### Resilience And Recovery Evidence

| Evidence type | Description | Example refs |
|---|---|---|
| `resilience_scenario` | Degraded mode, failover, recovery, or DIL scenario. | scenario description |
| `resilience_test_evidence` | Test result proving resilience behavior. | chaos test, recovery test |
| `backup_restore_evidence` | Backup and restore proof. | restore report |
| `failure_mode_evidence` | Failure modes and expected system behavior. | FMEA, test report |
| `operational_recovery_record` | Recovery event, drill, or exercise record. | recovery exercise |

### Review And Approval Evidence

| Evidence type | Description | Example refs |
|---|---|---|
| `architecture_review_record` | Architecture review result and attendees. | review minutes |
| `approval_record` | Approval with accountable role and date. | sign-off record |
| `design_authority_decision` | Decision from design authority, architecture board, or equivalent. | board decision |
| `quality_gate_result` | Gate result for architecture readiness or release readiness. | gate report |
| `owner_assignment` | Explicit owner assignment. | RACI, owner file |

### Exception And Waiver Evidence

| Evidence type | Description | Example refs |
|---|---|---|
| `architecture_exception` | Controlled deviation from architecture expectation. | exception JSON |
| `risk_acceptance_record` | Explicit risk acceptance and authority. | risk sign-off |
| `mitigation_plan` | Mitigation and follow-up plan. | mitigation record |
| `expiry_review_record` | Review record for expiring exception. | expiry review |

### Feedback And Improvement Evidence

| Evidence type | Description | Example refs |
|---|---|---|
| `operational_finding` | Finding from operations or monitoring. | incident, alert review |
| `demo_or_review_finding` | Finding from demo, inspection, or review. | demo notes |
| `technical_debt_item` | Architecture debt item with owner and priority. | backlog item |
| `improvement_backlog_item` | Owned improvement item. | work item |
| `closed_improvement_action` | Evidence that a feedback item was closed. | closed ticket, release note |

## Proposed Level Mapping

| Level | Evidence expectation |
|---|---|
| L1 | Basic architecture and deployment description, minimum ownership, minimum runtime and release-candidate evidence. |
| L2 | Interface contracts, compatibility matrix, security architecture evidence, integration evidence, and baseline alignment. |
| L3 | Verified runtime, resilience, observability, recovery, operation, and release evidence. |
| GOV | Formal reviews, decision records, exceptions, waivers, model baselines, and improvement loops. |

## Model-Based Architecture Position

Model-based architecture should be treated as a stronger evidence class, not as the only architecture evidence.

Suggested maturity approach:

| Maturity | Model evidence expectation |
|---|---|
| Early adoption | Human-readable architecture document is acceptable. |
| Stable L1 | Model export or architecture document is acceptable. |
| L2 / integration-heavy systems | Interface model, contract model, or model export is recommended. |
| L3 / release-critical systems | Reviewed model export or model baseline is expected. |
| GOV / high-assurance systems | Native model, export, review record, baseline id, checksum, and approval record may be required. |

## Tool-Specific Evidence

Tool-specific evidence is intentionally out of scope for this draft.

If Enterprise Architecture later decides that a certain modeling tool, repository, notation, or export format is required for a system class, this should be added as a company-specific refinement below the neutral evidence type.

The neutral evidence record should stay readable without requiring the governance repository to understand a vendor-native file format:

```json
{
  "evidence_type": "model_based_architecture",
  "status": "approved",
  "owner": "Solution Architect",
  "tool": "to-be-defined-by-enterprise-architecture",
  "tool_version": "to-be-defined",
  "model_file": "architecture/model/system-model.<extension>",
  "model_export": "docs/architecture/model-export.pdf",
  "baseline_id": "solution-baseline-2026.07",
  "model_version": "2026.07",
  "hash": "sha256:<to-be-calculated>",
  "approved_by": "Enterprise Architect",
  "approval_date": "2026-07-06",
  "evidence_refs": [
    "architecture/model/system-model.<extension>",
    "docs/architecture/model-export.pdf"
  ]
}
```

The governance repository should validate the reviewable export and metadata first. Native tool-file validation can be added later if company tooling supports it in CI.

## Suggested Metadata Fields

Future schema extensions could support:

| Field | Purpose |
|---|---|
| `evidence_type` | Type from the taxonomy. |
| `status` | `draft`, `reviewed`, or `approved`. |
| `owner` | Accountable owner. |
| `tool` | Tool name if tool-specific. |
| `tool_version` | Tool version if relevant. |
| `model_file` | Native model file path. |
| `model_export` | Reviewable model export path. |
| `baseline_id` | Architecture or solution baseline id. |
| `model_version` | Model version or release version. |
| `hash` | Digest of model or export artifact. |
| `approved_by` | Approver role or person. |
| `approval_date` | Approval date. |
| `evidence_refs` | Supporting repository paths or artifact refs. |
| `known_limitations` | Known gaps. |
| `follow_up_actions` | Required improvement actions. |

## Open Questions For Enterprise Architecture

1. Which systems require model-based architecture evidence?
2. Which notation, repository, export, or review format is acceptable for model-based architecture evidence?
3. Should native model files be committed to application repositories, stored in a model repository, or referenced as artifacts?
4. Which export format is reviewable and suitable for CI evidence?
5. Who approves model baselines?
6. What metadata is mandatory for a model baseline?
7. Which evidence types are required at L1, L2, L3, and GOV?
8. Which evidence types can be report-only during adoption?
9. Which missing evidence types should eventually block release candidates?
10. How should exceptions be approved, expired, and reviewed?
11. Which evidence can be auto-detected, and which must be explicitly declared?
12. How should Bitbucket and Bamboo archive and expose model artifacts?
13. How should Mistral or another provider read model evidence without accessing sensitive native files unnecessarily?

## Possible Implementation Path

1. Review this taxonomy with Enterprise Architecture.
2. Mark accepted, rejected, and missing evidence types.
3. Extend `schemas/app-architecture-evidence.schema.json` with agreed evidence types.
4. Update `scripts/collect_architecture_release_input.py` to recognize the new types.
5. Map evidence types to quality markers in `architecture/quality-markers.yaml`.
6. Add report-only OPA checks for the new evidence expectations.
7. Add fixtures for missing and approved model evidence.
8. Add Bamboo artifact handling for model exports.
9. Add Mistral review guidance for model-based evidence.
10. Decide later which checks become blocking.

## Current Recommendation

Keep the taxonomy tool-neutral.

Use the taxonomy to agree on:

- where model-based architecture is required
- which model notation, export, repository, or metadata is acceptable as CI evidence
- how model baseline approval should be represented
- when missing model evidence should become blocking
