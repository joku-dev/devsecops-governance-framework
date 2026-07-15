# Architecture Evidence Taxonomy Mapping

Status: draft / proposal

## Purpose

This document maps the evidence names already present in the architecture input documents to the proposed neutral architecture evidence type taxonomy.

It is a compatibility bridge. It does not change schemas, collectors, OPA policies, workflows, or release baselines.

The mapping has three layers:

1. Source evidence name from architecture levels, quality markers, guardrails, or review gates.
2. Neutral taxonomy type proposed for future use.
3. Current coarse application evidence type accepted by `schemas/app-architecture-evidence.schema.json`.

## Compatibility Summary

The proposed taxonomy is compatible with the provided input documents because it refines existing evidence expectations instead of replacing them.

The current application evidence schema is intentionally broader. Until the schema and collector are extended, many detailed taxonomy types map to one of these coarse evidence types:

```text
solution_baseline
release_compatibility_declaration
security_evidence
resilience_evidence
operation_evidence
feedback_evidence
review_evidence
exception_evidence
```

Tool-specific model evidence is intentionally not mapped here. Model-based evidence remains neutral through `model_based_architecture`, `model_export`, `model_baseline_record`, and `model_review_record`.

## Architecture Description And Ownership

| Source evidence name | Neutral taxonomy type | Current coarse schema type | Source area |
|---|---|---|---|
| `product_architecture_document` | `architecture_document` | `solution_baseline` | ARCH-L1, Product Architecture |
| `product_bapo_map` | `context_view` | `solution_baseline` | ARCH-L1, Product Architecture |
| `context_diagram` | `context_view` | `solution_baseline` | Product markers |
| `solution_context_diagram` | `context_view` | `solution_baseline` | ARCH-L1, Solution Architecture |
| `building_block_view` | `building_block_view` | `solution_baseline` | ARCH-L1, Product Architecture |
| `adr_register` | `architecture_decision_record` | `solution_baseline` | ARCH-L1, Product Architecture |
| `decision_record` | `architecture_decision_record` | `solution_baseline` | Product markers |
| `owner_list` | `architecture_ownership_record` | `solution_baseline` | BAPO markers |
| `raci` | `architecture_ownership_record` | `solution_baseline` | BAPO markers |
| `owner_assignment` | `owner_assignment` | `review_evidence` | BAPO, interface, governance markers |
| `review_record` | `architecture_review_record` | `review_evidence` | BAPO markers |
| `approved_architecture_review_record` | `architecture_review_record` | `review_evidence` | BAPO markers |

## Model-Based Architecture

| Source evidence name | Neutral taxonomy type | Current coarse schema type | Source area |
|---|---|---|---|
| `model_based_architecture` | `model_based_architecture` | `solution_baseline` | Proposed taxonomy |
| `model_export` | `model_export` | `solution_baseline` | Proposed taxonomy |
| `model_baseline_record` | `model_baseline_record` | `solution_baseline` | Proposed taxonomy |
| `model_review_record` | `model_review_record` | `review_evidence` | Proposed taxonomy |
| `semantic_model` | `model_based_architecture` | `solution_baseline` | Enterprise data markers |
| `data_flow_model` | `model_based_architecture` | `solution_baseline` | Solution/Product data markers |

## Interface And Contract Evidence

| Source evidence name | Neutral taxonomy type | Current coarse schema type | Source area |
|---|---|---|---|
| `interface_catalogue` | `interface_catalogue` | `solution_baseline` | ARCH-L2, Solution markers |
| `interface_standard_catalogue` | `interface_catalogue` | `solution_baseline` | Enterprise markers |
| `interface_owner_list` | `owner_assignment` | `review_evidence` | Solution markers |
| `interface_contract` | `interface_contract` | `release_compatibility_declaration` | ARCH-L2, guardrails |
| `data_contract` | `data_contract` | `release_compatibility_declaration` | ARCH-L2, guardrails |
| `schema_catalogue` | `data_contract` | `release_compatibility_declaration` | Product markers |
| `schema_validation_result` | `contract_test_result` | `release_compatibility_declaration` | ARCH-L2, Product markers |
| `contract_test_result` | `contract_test_result` | `release_compatibility_declaration` | ARCH-L2, guardrails |
| `contract_test_evidence` | `contract_test_result` | `release_compatibility_declaration` | Enterprise markers |
| `compatibility_matrix` | `compatibility_matrix` | `release_compatibility_declaration` | ARCH-L2, guardrails |
| `release_compatibility_matrix` | `compatibility_matrix` | `release_compatibility_declaration` | DevSecOps guardrail |
| `compatibility_evidence` | `compatibility_matrix` | `release_compatibility_declaration` | Review gates |

## Baseline And Release Compatibility

| Source evidence name | Neutral taxonomy type | Current coarse schema type | Source area |
|---|---|---|---|
| `solution_release_baseline` | `solution_baseline` | `solution_baseline` | ARCH-L2, Solution markers |
| `solution_baseline_mapping` | `solution_baseline` | `solution_baseline` | BAPO markers |
| `product_compatibility_matrix` | `compatibility_matrix` | `release_compatibility_declaration` | Solution markers |
| `release_compatibility_declaration` | `release_compatibility_declaration` | `release_compatibility_declaration` | ARCH-L2, review gates |
| `product_release_compatibility_declaration` | `release_compatibility_declaration` | `release_compatibility_declaration` | Enterprise markers |
| `compatibility_assessment` | `baseline_delta_assessment` | `release_compatibility_declaration` | BAPO markers |
| `migration_notes` | `migration_impact_assessment` | `release_compatibility_declaration` | Release declaration source document |

## Security Architecture Evidence

| Source evidence name | Neutral taxonomy type | Current coarse schema type | Source area |
|---|---|---|---|
| `security_guardrail_catalogue` | `security_architecture_review` | `security_evidence` | ARCH-L2, Enterprise markers |
| `solution_threat_model` | `threat_model` | `security_evidence` | ARCH-L2, Solution markers |
| `threat_model` | `threat_model` | `security_evidence` | Product markers |
| `trust_zone_model` | `trust_zone_model` | `security_evidence` | ARCH-L2, Solution markers |
| `security_boundary_model` | `trust_zone_model` | `security_evidence` | Review gates |
| `identity_and_access_model` | `identity_and_access_model` | `security_evidence` | Proposed taxonomy |
| `product_security_concept` | `security_architecture_review` | `security_evidence` | ARCH-L2, Product markers |
| `security_architecture_review` | `security_architecture_review` | `security_evidence` | Solution markers |
| `security_test_evidence` | `security_test_evidence` | `security_evidence` | ARCH-L2, markers |
| `security_scan_result` | `security_test_evidence` | `security_evidence` | DevSecOps guardrail |
| `vulnerability_scan_result` | `security_test_evidence` | `security_evidence` | Product markers |

## Deployment And Runtime Evidence

| Source evidence name | Neutral taxonomy type | Current coarse schema type | Source area |
|---|---|---|---|
| `deployment_view` | `deployment_document` | `deployment_evidence` | ARCH-L2, Product markers |
| `deployment_manifest` | `deployment_manifest` | `deployment_evidence` | ARCH-L2, guardrails |
| `deployment_pipeline_evidence` | `deployment_manifest` | `deployment_evidence` | ARCH-L2, Product markers |
| `deployment_evidence` | `deployment_manifest` | `deployment_evidence` | Review gates |
| `environment_assumption_record` | `runtime_configuration_evidence` | `deployment_evidence` | Product markers |
| `environment_compatibility_evidence` | `runtime_configuration_evidence` | `deployment_evidence` | ARCH-L2 |
| `environment_compatibility_matrix` | `runtime_configuration_evidence` | `deployment_evidence` | Runtime guardrail |
| `runtime_standard` | `runtime_configuration_evidence` | `deployment_evidence` | ARCH-L2, Enterprise markers |
| `runtime_reference_architecture` | `runtime_configuration_evidence` | `deployment_evidence` | Guardrails |
| `runtime_evidence` | `observability_evidence` | `operation_evidence` | ARCH-L3, Product markers |
| `runtime_metrics` | `observability_evidence` | `operation_evidence` | Review gates |
| `runtime_metric` | `observability_evidence` | `operation_evidence` | Remediation actions |
| `logging_concept` | `observability_evidence` | `operation_evidence` | ARCH-L3 |
| `metrics_definition` | `observability_evidence` | `operation_evidence` | ARCH-L3 |
| `health_indicator_definition` | `observability_evidence` | `operation_evidence` | ARCH-L3 |
| `monitoring_dashboard` | `observability_evidence` | `operation_evidence` | ARCH-L3 |
| `rollback_evidence` | `rollback_evidence` | `deployment_evidence` | ARCH-L2, Product markers |
| `update_and_rollback_evidence` | `rollback_evidence` | `deployment_evidence` | Runtime guardrail |

## Resilience And Recovery Evidence

| Source evidence name | Neutral taxonomy type | Current coarse schema type | Source area |
|---|---|---|---|
| `degraded_mode_scenario` | `resilience_scenario` | `resilience_evidence` | Solution/Product markers |
| `failure_mode_scenario` | `failure_mode_evidence` | `resilience_evidence` | Product markers |
| `recovery_scenario` | `resilience_scenario` | `resilience_evidence` | Solution/Product markers |
| `resilience_test_result` | `resilience_test_evidence` | `resilience_evidence` | ARCH-L2, markers |
| `recovery_test_result` | `resilience_test_evidence` | `resilience_evidence` | Product markers |
| `dil_test_evidence` | `resilience_test_evidence` | `resilience_evidence` | Solution markers |
| `degraded_connectivity_test_evidence` | `resilience_test_evidence` | `resilience_evidence` | Runtime guardrail |
| `backup_restore_evidence` | `backup_restore_evidence` | `resilience_evidence` | Proposed taxonomy |
| `operational_recovery_record` | `operational_recovery_record` | `resilience_evidence` | Proposed taxonomy |

## Review, Approval, Exception, And Waiver Evidence

| Source evidence name | Neutral taxonomy type | Current coarse schema type | Source area |
|---|---|---|---|
| `architecture_review_record` | `architecture_review_record` | `review_evidence` | Review gates, Product markers |
| `enterprise_architecture_review_record` | `architecture_review_record` | `review_evidence` | Enterprise markers |
| `portfolio_architecture_review_record` | `architecture_review_record` | `review_evidence` | Enterprise markers |
| `product_architecture_review_record` | `architecture_review_record` | `review_evidence` | Product markers |
| `solution_review_record` | `architecture_review_record` | `review_evidence` | Solution markers |
| `approval_record` | `approval_record` | `review_evidence` | Guardrails, BAPO markers |
| `design_authority_decision` | `design_authority_decision` | `review_evidence` | Proposed taxonomy |
| `quality_gate_result` | `quality_gate_result` | `review_evidence` | Proposed taxonomy |
| `exception_record` | `architecture_exception` | `exception_evidence` | Guardrails, ARCH-GOV |
| `architecture_exception` | `architecture_exception` | `exception_evidence` | Proposed taxonomy |
| `risk_assessment` | `risk_acceptance_record` | `exception_evidence` | ARCH-GOV |
| `mitigation_plan` | `mitigation_plan` | `exception_evidence` | ARCH-GOV, debt markers |
| `review_date` | `expiry_review_record` | `exception_evidence` | ARCH-GOV |
| `expiry_date` | `expiry_review_record` | `exception_evidence` | ARCH-GOV |

## Feedback And Improvement Evidence

| Source evidence name | Neutral taxonomy type | Current coarse schema type | Source area |
|---|---|---|---|
| `feedback_process` | `improvement_backlog_item` | `feedback_evidence` | BAPO markers |
| `demo_or_review_finding` | `demo_or_review_finding` | `feedback_evidence` | ARCH-L3, BAPO markers |
| `operational_finding_trend` | `operational_finding` | `feedback_evidence` | ARCH-L3, BAPO markers |
| `technical_debt_item` | `technical_debt_item` | `feedback_evidence` | ARCH-L3, BAPO markers |
| `improvement_backlog_item` | `improvement_backlog_item` | `feedback_evidence` | ARCH-L3 |
| `closed_improvement_action` | `closed_improvement_action` | `feedback_evidence` | ARCH-L3, BAPO markers |
| `guardrail_improvement_action` | `closed_improvement_action` | `feedback_evidence` | Enterprise markers |
| `architecture_improvement_action` | `closed_improvement_action` | `feedback_evidence` | Product markers |
| `technical_debt_trend` | `technical_debt_item` | `feedback_evidence` | ARCH-L3 |
| `closed_debt_reduction_action` | `closed_improvement_action` | `feedback_evidence` | Debt markers |

## Adoption Notes

This mapping should be used before changing validation behavior.

Recommended adoption sequence:

1. Review the mappings with Enterprise Architecture.
2. Mark each row as accepted, renamed, merged, or rejected.
3. Add accepted neutral types to the schema in report-only mode.
4. Update the collector so it can emit both coarse and detailed evidence types.
5. Update reports to show missing detailed evidence without blocking releases.
6. Promote selected evidence types to blocking gates only after teams have templates and examples.

## Open Mapping Questions

| Question | Reason |
|---|---|
| Should `contract_test_result` be represented as release compatibility evidence or as its own contract evidence class? | Contract evidence is central for L2 integration readiness. |
| Should model-based evidence be required at L2/L3 only for integration-heavy or high-assurance systems? | This keeps tool-neutral adoption practical. |

## Resolved Mapping Decisions

| Decision | Reason |
|---|---|
| `deployment_document`, `deployment_manifest`, `runtime_configuration_evidence`, and `rollback_evidence` map to `deployment_evidence`. | Deployment readiness is tracked separately from runtime/operations evidence in the architecture release input. Observability and runbook evidence remain under `operation_evidence`. |
| `architecture_review_record`, `model_review_record`, `approval_record`, `design_authority_decision`, `quality_gate_result`, and `owner_assignment` map to `review_evidence`. | Review and approval evidence is tracked separately from feedback and improvement loops. |
| `architecture_exception`, `risk_acceptance_record`, `mitigation_plan`, and `expiry_review_record` map to `exception_evidence`. | Exception and waiver evidence is tracked separately from feedback and improvement loops, without changing release gates. |
