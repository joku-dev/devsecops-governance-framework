# PRA-2026-001: Requirement-to-Platform Review

## Decision brief

This packet tracks the moderated review of all 56 PRA source requirements. Recorded decisions and effective platform mappings are read from the governed lifecycle case and Requirement-to-Artifact Register. It does not change runtime enforcement.

The source is pinned to `730f3a1f5875ec76f3d032c9f620630fc68846d4722c28803b16c8ab50902d3b`. Existing control-to-platform allocation and capability metadata are primary review evidence; text similarity is advisory only.

| Measure | Value |
|---|---:|
| Source requirements | 56 |
| With platform candidates | 55 |
| Without platform candidates | 1 |
| With explicit DSCB references | 2 |
| Requirements decided | 38 |
| Effective platform mappings | 11 |
| Lowest top similarity | 0.3094 |
| Highest top similarity | 0.5631 |

## Required decisions

For every row, the Platform Owner must record two independent decisions:

1. Requirement disposition and classification: approve or reject with `new`, `duplicate`, `extend`, `change`, `supersede`, or `conflict`.
2. Platform equivalence: `equivalent`, `partial`, `missing`, or `not_equivalent` for each adopted capability mapping.

Rows marked `correct_or_reject` are incomplete or context-dependent statements in the sanitized extract. Rows marked `reject_non_requirement` are headings or table headers. Neither category should be activated without correction or explicit contrary evidence.

## Review table

| Source requirement | Form | Recommendation | Explicit controls | Control allocation | Top platform candidates |
|---|---|---|---|---|---|
| `PRA-STD-SRC-001-REQ-001` | `normative_statement` | `review_for_activation` | — | — | `checksum_or_digest_records` (0.4023), `central_development_environment_management` (0.3886), `version_controlled_build_configuration` (0.3882) |
| `PRA-STD-SRC-001-REQ-002` | `normative_statement` | `review_for_activation` | — | — | `waiver_registry` (0.3913), `reproducible_build_verification` (0.3894), `pipeline_evidence_generation` (0.3818) |
| `PRA-STD-SRC-001-REQ-003` | `normative_statement` | `review_for_activation` | — | — | `central_development_environment_management` (0.3743), `iac_validation` (0.3721), `security_threshold_enforcement` (0.3721) |
| `PRA-STD-SRC-001-REQ-004` | `incomplete_list_intro` | `correct_or_reject` | — | — | `security_event_forwarding` (0.3576), `signing_key_management` (0.3478), `operational_logging` (0.3448) |
| `PRA-STD-SRC-001-REQ-005` | `section_heading` | `reject_non_requirement` | — | — | `deployment_traceability` (0.3964), `provenance_capture` (0.3830), `evidence_graph` (0.3778) |
| `PRA-STD-SRC-001-REQ-006` | `incomplete_list_intro` | `correct_or_reject` | — | — | `iac_validation` (0.4400), `continuous_compliance_evidence` (0.4196), `compliance_reporting` (0.4118) |
| `PRA-STD-SRC-001-REQ-007` | `normative_statement` | `review_for_activation` | — | — | `release_approval_workflow` (0.5271), `release_blocking` (0.4833), `rbac` (0.4667) |
| `PRA-STD-SRC-001-REQ-008` | `normative_statement` | `review_for_activation` | — | — | `central_development_environment_management` (0.4578), `enterprise_trust_infrastructure` (0.4444), `release_approval_workflow` (0.4311) |
| `PRA-STD-SRC-001-REQ-009` | `normative_statement` | `review_for_activation` | — | — | `evidence_repository` (0.4082), `static_code_analysis` (0.3932), `compliance_evidence_repository` (0.3853) |
| `PRA-STD-SRC-001-REQ-010` | `normative_statement` | `review_for_activation` | — | — | `approved_version_control` (0.4480), `static_code_analysis` (0.4029), `secure_coding_guidance` (0.3830) |
| `PRA-STD-SRC-001-REQ-011` | `normative_statement` | `review_for_activation` | — | — | `iac_validation` (0.4062), `iac_repository` (0.4043), `access_audit_logging` (0.4000) |
| `PRA-STD-SRC-001-REQ-012` | `normative_statement` | `review_for_activation` | — | — | `code_review` (0.4561), `machine_readable_evidence_generation` (0.4000), `pipeline_evidence_generation` (0.4000) |
| `PRA-STD-SRC-001-REQ-013` | `normative_statement` | `review_for_activation` | — | — | `isolated_build_environment` (0.3934), `traceability_database` (0.3710), `recreatable_build_environment` (0.3680) |
| `PRA-STD-SRC-001-REQ-014` | `normative_statement` | `review_for_activation` | — | — | `compliance_reporting` (0.4603), `automated_pipeline_execution` (0.4355), `approved_version_control` (0.4310) |
| `PRA-STD-SRC-001-REQ-015` | `normative_statement` | `review_for_activation` | — | — | `pipeline_evidence_generation` (0.5234), `automated_pipeline_execution` (0.4860), `compliance_evidence_repository` (0.4762) |
| `PRA-STD-SRC-001-REQ-016` | `normative_statement` | `review_for_activation` | — | — | `security_event_forwarding` (0.4464), `pipeline_evidence_generation` (0.4144), `monitoring_integration` (0.4037) |
| `PRA-STD-SRC-001-REQ-017` | `normative_statement` | `review_for_activation` | — | — | `secure_coding_guidance` (0.4706), `vulnerability_scanning` (0.4706), `policy_gate_engine` (0.4696) |
| `PRA-STD-SRC-001-REQ-018` | `normative_statement` | `review_for_activation` | — | — | `policy_gate_engine` (0.4460), `static_code_analysis` (0.4397), `secure_coding_guidance` (0.4336) |
| `PRA-STD-SRC-001-REQ-019` | `normative_statement` | `review_for_activation` | — | — | `artifact_signature_logs` (0.4143), `artifact_versioning` (0.3971), `artifact_metadata_management` (0.3862) |
| `PRA-STD-SRC-001-REQ-020` | `normative_statement` | `review_for_activation` | — | — | `artifact_repository_integrity` (0.5614), `iac_repository` (0.4646), `evidence_repository` (0.4231) |
| `PRA-STD-SRC-001-REQ-021` | `normative_statement` | `review_for_activation` | — | — | `evidence_repository` (0.5631), `approved_dependency_repositories` (0.5441), `incident_record_repository` (0.5273) |
| `PRA-STD-SRC-001-REQ-022` | `normative_statement` | `review_for_activation` | — | — | `reproducible_build_verification` (0.4275), `dependency_proxy` (0.4242), `dependency_scanning` (0.4148) |
| `PRA-STD-SRC-001-REQ-023` | `normative_statement` | `review_for_activation` | — | — | `reproducible_build_verification` (0.4038), `pipeline_audit_logs` (0.3913), `version_controlled_build_configuration` (0.3784) |
| `PRA-STD-SRC-001-REQ-024` | `normative_statement` | `review_for_activation` | — | — | `release_blocking` (0.4078), `deployment_logging` (0.4000), `deployment_records` (0.4000) |
| `PRA-STD-SRC-001-REQ-025` | `normative_statement` | `review_for_activation` | — | — | `machine_readable_evidence_generation` (0.4444), `compliance_reporting` (0.3969), `traceability_database` (0.3876) |
| `PRA-STD-SRC-001-REQ-026` | `normative_statement` | `review_for_activation` | — | — | `evidence_repository` (0.4000), `incident_record_repository` (0.3725), `compliance_evidence_repository` (0.3585) |
| `PRA-STD-SRC-001-REQ-027` | `normative_statement` | `review_for_activation` | — | — | `evidence_graph` (0.4660), `evidence_and_traceability_layer` (0.4167), `dependency_scanning` (0.4103) |
| `PRA-STD-SRC-001-REQ-028` | `normative_statement` | `review_for_activation` | — | — | `recreatable_build_environment` (0.4918), `isolated_build_environment` (0.4874), `operational_logging` (0.4655) |
| `PRA-STD-SRC-001-REQ-029` | `normative_statement` | `review_for_activation` | — | — | `compliance_reporting` (0.3802), `deployment_traceability` (0.3459), `monitoring_integration` (0.3419) |
| `PRA-STD-SRC-001-REQ-030` | `normative_statement` | `review_for_activation` | — | — | `monitoring_integration` (0.4390), `automated_pipeline_execution` (0.4000), `pipeline_evidence_generation` (0.4000) |
| `PRA-STD-SRC-001-REQ-031` | `context_dependent_statement` | `correct_or_reject` | — | — | `security_threshold_enforcement` (0.3905), `static_code_analysis` (0.3600), `compliance_evidence_repository` (0.3542) |
| `PRA-STD-SRC-001-REQ-032` | `context_dependent_statement` | `correct_or_reject` | — | — | `security_threshold_enforcement` (0.3777), `vulnerability_assessment` (0.3700), `machine_readable_evidence_generation` (0.3621) |
| `PRA-STD-SRC-001-REQ-033` | `descriptive_or_traceability_row` | `review_as_supporting_model` | — | — | `enterprise_trust_infrastructure` (0.3818), `central_signing_key_management` (0.3744), `signing_key_management` (0.3507) |
| `PRA-STD-SRC-001-REQ-034` | `descriptive_or_traceability_row` | `review_as_supporting_model` | — | — | `security_event_forwarding` (0.3802), `security_event_generation` (0.3802), `security_threshold_enforcement` (0.3268) |
| `PRA-STD-SRC-001-REQ-035` | `descriptive_or_traceability_row` | `review_as_supporting_model` | — | — | — |
| `PRA-STD-SRC-001-REQ-036` | `descriptive_or_traceability_row` | `review_as_supporting_model` | — | — | `runtime_integrity_verification` (0.4455), `signature_verification` (0.4293), `end_to_end_traceability` (0.4262) |
| `PRA-STD-SRC-001-REQ-037` | `normative_statement` | `review_for_activation` | — | — | `security_threshold_enforcement` (0.4767), `incident_record_repository` (0.3867), `artifact_repository_integrity` (0.3791) |
| `PRA-STD-SRC-001-REQ-038` | `normative_statement` | `review_for_activation` | — | — | `compliance_evidence_repository` (0.3302) |
| `PRA-STD-SRC-001-REQ-039` | `table_header` | `reject_non_requirement` | — | — | `build_pipeline_logging` (0.4587), `security_event_generation` (0.3966), `monitoring_integration` (0.3894) |
| `PRA-STD-SRC-001-REQ-040` | `descriptive_or_traceability_row` | `review_as_supporting_model` | — | — | `machine_readable_evidence_generation` (0.3466), `provenance_capture` (0.3166) |
| `PRA-STD-SRC-001-REQ-041` | `descriptive_or_traceability_row` | `review_as_supporting_model` | — | — | `security_threshold_enforcement` (0.3309), `environment_configuration_management` (0.3197) |
| `PRA-STD-SRC-001-REQ-042` | `descriptive_or_traceability_row` | `review_as_supporting_model` | — | — | `vulnerability_assessment` (0.3242), `deployment_traceability` (0.3142), `deployment_records` (0.3067) |
| `PRA-STD-SRC-001-REQ-043` | `descriptive_or_traceability_row` | `review_as_supporting_model` | — | — | `deployment_traceability` (0.3529), `runtime_integrity_verification` (0.3421), `approved_dependency_repositories` (0.3172) |
| `PRA-STD-SRC-001-REQ-044` | `context_dependent_statement` | `correct_or_reject` | — | — | `artifact_repository_integrity` (0.3796), `vulnerability_scanning` (0.3784), `policy_gate_engine` (0.3611) |
| `PRA-STD-SRC-001-REQ-045` | `table_header` | `reject_non_requirement` | — | — | `version_controlled_build_configuration` (0.4026), `configuration_baselines` (0.4000), `central_signing_key_management` (0.3926) |
| `PRA-STD-SRC-001-REQ-046` | `descriptive_or_traceability_row` | `review_as_supporting_model` | `DSCB-L1-REQ-001` | `evidence_and_traceability_layer`, `pipeline_audit_logs`, `traceability_database` | `evidence_and_traceability_layer` (0.4603), `end_to_end_traceability` (0.4329), `traceability_database` (0.4192) |
| `PRA-STD-SRC-001-REQ-047` | `descriptive_or_traceability_row` | `review_as_supporting_model` | `DSCB-L3-REQ-009` | `deployment_metadata`, `end_to_end_traceability`, `evidence_graph` | `evidence_graph` (0.3431), `provenance_capture` (0.3365), `machine_readable_evidence_generation` (0.3363) |
| `PRA-STD-SRC-001-REQ-048` | `normative_statement` | `review_for_activation` | — | — | `deployment_logging` (0.4000), `security_event_forwarding` (0.3713), `release_approval_workflow` (0.3651) |
| `PRA-STD-SRC-001-REQ-049` | `normative_statement` | `review_for_activation` | — | — | `compliance_reporting` (0.3094), `evidence_and_traceability_layer` (0.3004) |
| `PRA-STD-SRC-001-REQ-050` | `incomplete_list_intro` | `correct_or_reject` | — | — | `operational_logging` (0.3759), `monitoring_integration` (0.3529), `secure_developer_workspace` (0.3504) |
| `PRA-STD-SRC-001-REQ-051` | `normative_statement` | `review_for_activation` | — | — | `security_event_generation` (0.3448), `artifact_metadata_management` (0.3375), `environment_configuration_management` (0.3187) |
| `PRA-STD-SRC-001-REQ-052` | `incomplete_list_intro` | `correct_or_reject` | — | — | `central_development_environment_management` (0.3694), `compliance_reporting` (0.3472), `approved_dependency_repositories` (0.3457) |
| `PRA-STD-SRC-001-REQ-053` | `normative_statement` | `review_for_activation` | — | — | `configuration_baselines` (0.3902), `signature_verification` (0.3371) |
| `PRA-STD-SRC-001-REQ-054` | `incomplete_list_intro` | `correct_or_reject` | — | — | `compliance_evidence_repository` (0.4107), `continuous_compliance_evidence` (0.3902), `compliance_reporting` (0.3793) |
| `PRA-STD-SRC-001-REQ-055` | `normative_statement` | `review_for_activation` | — | — | `compliance_reporting` (0.3333), `continuous_compliance_evidence` (0.3314), `compliance_evidence_repository` (0.3291) |
| `PRA-STD-SRC-001-REQ-056` | `incomplete_list_intro` | `correct_or_reject` | — | — | `static_code_analysis` (0.3670), `policy_gate_engine` (0.3551), `pipeline_audit_logs` (0.3404) |

## Source protection

- The registered PRA requirements extract is not edited by this review.
- The lifecycle case remains undecided and the authority mode remains `migration_in_progress`.
- A correction requires a new versioned source or lifecycle revision; it must not overwrite the approved source bytes.
- No GRQ activation, platform adoption, OPA change, or enforcement change is authorized by this packet.
