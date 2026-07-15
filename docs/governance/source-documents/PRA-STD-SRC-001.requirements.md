# Platform Reference Architecture Requirements

This file contains a sanitized requirements-only extraction from a private source document. Original source text, document metadata, personal names, organization-specific labels, document numbers, images, and distribution metadata are intentionally not included.

| ID | Strength | Context | Requirement |
|---|---|---|---|
| `PRA-STD-SRC-001-REQ-001` | MUST | Aim and Purpose | The DevSecOps platform shall enable a controlled and repeatable software delivery across all programs. |
| `PRA-STD-SRC-001-REQ-002` | MUST | The Chief Digitalisation Office | When a version is quoted, this version shall be used. |
| `PRA-STD-SRC-001-REQ-003` | MUST | Scope | Domain-specific variants (e.g., classified environments) shall conform to this reference architecture. |
| `PRA-STD-SRC-001-REQ-004` | MUST | DevSecOps Platform Stack Architecture Overview Strategic Authority | The enterprise DevSecOps platform shall implement the following logical architecture layers: |
| `PRA-STD-SRC-001-REQ-005` | REQUIREMENT | Operational Monitoring Layer | Platform Stack Capability Requirements |
| `PRA-STD-SRC-001-REQ-006` | MUST | Operational Monitoring Layer | Each platform instance shall implement the following mandatory capabilities. |
| `PRA-STD-SRC-001-REQ-007` | MUST | Objective | Developers shall use approved development environments. |
| `PRA-STD-SRC-001-REQ-008` | MUST | Objective | Access to development environments shall be authenticated via enterprise identity management. |
| `PRA-STD-SRC-001-REQ-009` | MUST | Objective | Access rights shall follow role-based access control. |
| `PRA-STD-SRC-001-REQ-010` | MUST | Objective | Source code shall be stored in enterprise-approved version control systems. |
| `PRA-STD-SRC-001-REQ-011` | MUST | Objective | Access shall be restricted according to defined roles. |
| `PRA-STD-SRC-001-REQ-012` | MUST | Objective | Code changes shall require review before integration into protected branches. |
| `PRA-STD-SRC-001-REQ-013` | MUST | Objective | All software builds shall be executed through automated pipelines. |
| `PRA-STD-SRC-001-REQ-014` | MUST | Objective | Pipeline execution environments shall be controlled and auditable. |
| `PRA-STD-SRC-001-REQ-015` | MUST | Objective | Pipeline definitions shall be version-controlled. |
| `PRA-STD-SRC-001-REQ-016` | MUST | Objective | Security scanning shall be integrated into pipelines. |
| `PRA-STD-SRC-001-REQ-017` | MUST | Objective | Supply chain integrity controls shall be implemented. |
| `PRA-STD-SRC-001-REQ-018` | MUST | Objective | Security and compliance checks shall be automated where technically feasible. |
| `PRA-STD-SRC-001-REQ-019` | MUST | Objective | Releasable artifacts shall be stored in approved artifact repositories. |
| `PRA-STD-SRC-001-REQ-020` | MUST | Objective | Artifact repositories shall maintain integrity protections. |
| `PRA-STD-SRC-001-REQ-021` | MUST | Objective | Dependency repositories shall be controlled and monitored. |
| `PRA-STD-SRC-001-REQ-022` | MUST | Objective | Deployment processes shall verify artifact integrity prior to release. |
| `PRA-STD-SRC-001-REQ-023` | MUST | Objective | Deployment authorization shall be enforced. |
| `PRA-STD-SRC-001-REQ-024` | MUST | Objective | Deployment activities shall be logged. |
| `PRA-STD-SRC-001-REQ-025` | MUST | Objective | DevSecOps pipelines shall generate machine-readable evidence artifacts. |
| `PRA-STD-SRC-001-REQ-026` | MUST | Objective | Evidence shall be stored in approved repositories. |
| `PRA-STD-SRC-001-REQ-027` | MUST | Objective | Evidence shall support internal and external audits. |
| `PRA-STD-SRC-001-REQ-028` | MUST | Objective | Operational environments shall record relevant security events. |
| `PRA-STD-SRC-001-REQ-029` | MUST | Objective | Monitoring capabilities shall support incident investigation. |
| `PRA-STD-SRC-001-REQ-030` | MUST | Objective | Monitoring data retention shall comply with applicable regulations. |
| `PRA-STD-SRC-001-REQ-031` | MUST | Platform Reference Architecture Levels | They describe what the platform must provide in order to support programs subject to the corresponding DevSecOps Control Baseline level. |
| `PRA-STD-SRC-001-REQ-032` | MUST | Platform Reference Architecture Levels | It is a minimum architectural capability level required to implement, enforce, and evidence the applicable control baseline in a repeatable and auditable manner. |
| `PRA-STD-SRC-001-REQ-033` | MUST | Platform Reference Architecture Levels | PRA-Level 1 provides the minimum platform capabilities required for enterprise DevSecOps adoption and Control Baseline Level 1 implementation. |
| `PRA-STD-SRC-001-REQ-034` | MUST | SBOM generation and storage for releasable artifacts | PRA-Level 2 extends PRA-Level 1 with centrally managed security, access control, policy enforcement, and operational monitoring capabilities required for secure DevSecOps implementation. |
| `PRA-STD-SRC-001-REQ-035` | MUST | SBOM generation and storage for releasable artifacts | PRA-Level 3 extends PRA-Level 2 with trusted software supply chain capabilities required for mission-critical, classified, or Software Defined Defence contexts. |
| `PRA-STD-SRC-001-REQ-036` | REQUIREMENT | SBOM generation and storage for releasable artifacts | end-to-end traceability from requirements to source code, verification results, build artifacts, deployment, and runtime state |
| `PRA-STD-SRC-001-REQ-037` | MUST | Mapping to Control Baseline Levels | The required platform level shall be derived from the applicable DevSecOps Control Baseline level. |
| `PRA-STD-SRC-001-REQ-038` | MUST | Mapping to Control Baseline Levels | A platform instance may provide a higher level than required, but shall not provide a lower level for programs subject to the corresponding control baseline. |
| `PRA-STD-SRC-001-REQ-039` | MUST | Mapping to Control Baseline Levels | Control Baseline Level \| Required Platform Level \| Rationale |
| `PRA-STD-SRC-001-REQ-040` | MUST | Mapping to Control Baseline Levels | Level 1: Enterprise DevSecOps Baseline \| PRA-Level 1 \| Provides the minimum platform capabilities required to execute controlled pipelines, maintain traceability, manage artifacts, and generate baseline evidence. |
| `PRA-STD-SRC-001-REQ-041` | MUST | Minimum Capability Matrix | Source Control \| Approved VCS; review before protected-branch integration \| Central RBAC; branch protection enforcement; audit logs \| Signed commits or tags where required; traceability to controlled changes |
| `PRA-STD-SRC-001-REQ-042` | REQUIREMENT | Minimum Capability Matrix | Evidence and Traceability \| Pipeline logs, SBOM records, vulnerability reports, assessment records, and baseline evidence repository \| Machine-readable evidence linked to controls, gates, waivers, and releases \| End-to-end evidence chain from requirement to runtime state |
| `PRA-STD-SRC-001-REQ-043` | MUST | Traceability Between Control Baseline and Platform Capabilities | The following traceability view links key Control Baseline requirements to the minimum platform capabilities required to implement and evidence them. |
| `PRA-STD-SRC-001-REQ-044` | MUST | Traceability Between Control Baseline and Platform Capabilities | It shall be maintained together with the Control Baseline requirement identifiers. |
| `PRA-STD-SRC-001-REQ-045` | MUST | Traceability Between Control Baseline and Platform Capabilities | Control Baseline Requirement \| Required PRA-Level \| Platform Capability \| Expected Evidence |
| `PRA-STD-SRC-001-REQ-046` | REQUIREMENT | Traceability Between Control Baseline and Platform Capabilities | DSCB-L1-REQ-001 Traceability \| PRA-Level 1 \| Evidence and Traceability Layer; traceability database; pipeline audit logs \| requirements traceability records; configuration records |
| `PRA-STD-SRC-001-REQ-047` | REQUIREMENT | Traceability Between Control Baseline and Platform Capabilities | DSCB-L3-REQ-009 End-to-End Traceability \| PRA-Level 3 \| End-to-end evidence chain from requirement to runtime state \| traceability records; deployment metadata |
| `PRA-STD-SRC-001-REQ-048` | MUST | Applicability of Domain-Specific Variants | Domain-specific platform variants, including classified, air-gapped, or restricted operational environments, shall implement the minimum PRA-Level required by the supported programs. |
| `PRA-STD-SRC-001-REQ-049` | MUST | Applicability of Domain-Specific Variants | Additional domain-specific restrictions may be applied, but shall not remove mandatory capabilities required by the applicable Platform Reference Architecture Level unless a formal waiver has been approved. |
| `PRA-STD-SRC-001-REQ-050` | MUST | Domain-Specific Platform Variants | Where required by operational constraints, platform variants may be deployed for: |
| `PRA-STD-SRC-001-REQ-051` | MUST | Domain-Specific Platform Variants | These variants shall implement the same logical architecture defined in this Standard. |
| `PRA-STD-SRC-001-REQ-052` | MUST | Platform Stack Governance | The DevSecOps Platform Stack Lead (role not yet implemented) shall be responsible for: |
| `PRA-STD-SRC-001-REQ-053` | MUST | Platform Stack Governance | Platform modifications that affect control baselines shall require approval by the DevSecOps Governance Board. |
| `PRA-STD-SRC-001-REQ-054` | MUST | Compliance Verification | Compliance with this Standard shall be verified through: |
| `PRA-STD-SRC-001-REQ-055` | MUST | DevSecOps maturity assessments | Non-compliant platforms shall not be approved for production software delivery unless formally waived. |
| `PRA-STD-SRC-001-REQ-056` | MUST | Relationship to Other DevSecOps Documents | This Standard shall be applied together with: |

## Extraction Notes

- Extraction mode: requirements-only sanitized Markdown.
- Source kind: DOCX.
- This file is suitable for controlled internal review before any public publication decision.
