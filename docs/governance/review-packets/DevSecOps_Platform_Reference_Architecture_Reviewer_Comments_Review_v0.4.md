| Standard |
| --- |
|  **DevSecOps Platform Stack Reference Architecture Standard** |

**Table of Contents**

1	General	4

1.1	Aim and Purpose	4

1.2	Responsibilities	4

1.3	Applicable Documents	4

1.4	Referenced Documents	4

1.5	Definition of Terms	4

1.6	Abbreviations	5

2	Scope	5

3	DevSecOps Platform Stack Architecture Overview Strategic Authority	5

4	Platform Stack Capability Requirements	6

4.1	Developer Workspace Layer	6

4.2	Source Control Layer	6

4.3	Pipeline Execution Layer	7

4.4	Security and Compliance Control Layer	7

4.5	Artifact and Dependency Management Layer	7

4.6	Deployment and Environment Management Layer	8

4.7	Evidence and Traceability Layer	8

4.8	Operational Monitoring Layer	8

5	Platform Reference Architecture Levels	9

5.1	PRA-Level 1: Basic DevSecOps Platform	9

5.2	PRA-Level 2: Secure Managed DevSecOps Platform	9

5.3	PRA-Level 3: Trusted SDD Platform	10

5.4	Mapping to Control Baseline Levels	10

5.5	Minimum Capability Matrix	11

5.6	Traceability Between Control Baseline and Platform Capabilities	11

5.7	Applicability of Domain-Specific Variants	13

6	Domain-Specific Platform Variants	13

7	Platform Stack Governance	13

8	Compliance Verification	13

9	Relationship to Other DevSecOps Documents	14

10	Entry into Force	14

General

Aim and Purpose

This Standard defines the enterprise DevSecOps Platform Reference Architecture used to implement the DevSecOps lifecycle and the Control Baseline.

The objective is to ensure that software development, integration, and deployment processes are executed through secure, standardized, and auditable platform capabilities.

The DevSecOps platform shall enable a controlled and repeatable software delivery across all programs.

Responsibilities

The Chief Digitalisation Office

Applicable Documents

The following publications form a part of this document to the extent specified herein. In case no version is quoted for a document the current version is deemed to apply. When a version is quoted, this version shall be used.

- Policy
- Directive

-

Referenced Documents

The following publications contain further input and background information relating the subject addressed. In case no version is quoted for a document the current version is deemed to apply. When a version is quoted, this version shall be used.

- DeVSecOps Policy
- Lin
- Internal reference: [removed]

-

Definition of Terms

The terms and definitions established for the Business Management System are listed in the common “BMS Glossary”. The following terms are specific to this document.

| Term | Explanation |
| --- | --- |
|  |  |

Abbreviations

| Abbreviation | Term |
| --- | --- |
| PRA | Platform Reference Architecture |
| IAM | Identity and Access Management |
| MFA | Multi-Factor Authentication |
| IaC | Infrastructure as Code |
| SBOM | Software Bill of Materials |

Scope

This Standard applies to:

- all DevSecOps platforms operated within the COMPANY Group
- all software factories used for SDD-relevant development
- all DevSecOps pipelines and supporting infrastructure
- all security domains

Domain-specific variants (e.g., classified environments) shall conform to this reference architecture.

DevSecOps Platform Stack Architecture Overview Strategic Authority

The enterprise DevSecOps platform shall implement the following logical architecture layers:

- Developer Workspace Layer
- Source Control Layer
- Pipeline Execution Layer
- Security and Compliance Control Layer
- Artifact and Dependency Management Layer
- Deployment and Environment Management Layer
- Evidence and Traceability Layer
- Operational Monitoring Layer

These layers together constitute the enterprise platform.

[PRA-COMP-001 | L1] A conformant DevSecOps platform MAY be composed of approved enterprise shared, division or federated, and programme-local services. An individual service is responsible only for its allocated capabilities; the approved composition SHALL provide all capabilities required by the programme's assigned PRA level.

[PRA-COMP-002 | L1] Each programme SHALL maintain a service allocation record identifying the provider, owner, service instance, security domain, supported PRA requirement IDs, integration interface and evidence location for every applicable layer. Shared services MAY satisfy several programmes when access and domain constraints are met.

**DECISION REQUIRED SERVICE CATALOGUE**Approve the enterprise shared-service catalogue, service ownership, permitted division or programme instances, and trust-domain allocation. The logical architecture cannot by itself name the approved source code repository service, CI, artifact, IAM, monitoring or signing instances for every programme.

Platform Stack Capability Requirements

Each platform instance shall implement the following mandatory capabilities. 'Platform instance' in this chapter denotes the approved service composition for a programme and security domain. The ID and minimum PRA level assigned to each requirement indicate its applicability; a single component is not required to implement all eight layers.

**DECISION REQUIRED A04**Approve the proposed PRA identifiers, minimum level of each layer contract, and exact control-to-platform mapping before this draft becomes a controlled standard. Chapter 5 lists incremental level profiles; its bullets and the minimum-capability matrix must be read with the linked Section 4 IDs, not as disconnected parallel requirements.

Developer Workspace Layer

**Objective**

Provide controlled development environments for software engineers.

**Requirements**

- [PRA-DW-001 | PRA-Level 1] Developers shall use approved development environments.
- [PRA-DW-002 | PRA-Level 2] Access to development environments shall be authenticated via enterprise identity management.
- [PRA-DW-003 | PRA-Level 2] Access rights shall follow role-based access control.

[PRA-DW-004 | PRA-Level 1] Developer access SHALL be authenticated by an approved identity mechanism; enterprise-wide identity integration under PRA-DW-002 applies at Level 2.

**Capabilities**

- Integrated development environments (IDE)
- Developer authentication and identity integration
- Secure access to repositories and pipelines

Source Control Layer

**Objective**

Maintain integrity and traceability of source code.

**Requirements**

- [PRA-SC-001 | PRA-Level 1] Source code shall be stored in enterprise-approved version control systems.
- [PRA-SC-002 | PRA-Level 1] Access shall be restricted according to defined roles.
- [PRA-SC-003 | PRA-Level 1] Code changes shall require review before integration into protected branches.

[PRA-SC-004 | PRA-Level 1] Access to source-control systems SHALL be adjusted or revoked when a person's organisational role changes or their association ends, in accordance with the approved identity lifecycle process. Evidence SHALL include access change and revocation records.

**Capabilities**

- Version control systems
- Code review mechanisms
- Branch protection rules

Identity lifecycle integration and access revocation evidence

Pipeline Execution Layer

**Objective**

Automate software build, test, and packaging processes.

**Requirements**

- [PRA-PIPE-001 | PRA-Level 1] All software builds shall be executed through automated pipelines.
- [PRA-PIPE-002 | PRA-Level 1] Pipeline execution environments shall be controlled and auditable.
- [PRA-PIPE-003 | PRA-Level 1] Pipeline definitions shall be version-controlled.

**Capabilities**

- Continuous integration pipelines
- Automated build environments
- Pipeline configuration management

Security and Compliance Control Layer

**Objective**

Ensure automated enforcement of security and compliance controls.

**Requirements**

- [PRA-SEC-001 | PRA-Level 1] Security scanning shall be integrated into pipelines.
- [PRA-SEC-002 | PRA-Level 1] Supply chain integrity controls shall be implemented.
- [PRA-SEC-003 | PRA-Level 1] Security and compliance checks shall be automated where technically feasible.

**Capabilities**

- Static code analysis
- Dependency vulnerability scanning
- Policy enforcement mechanisms

Artifact and Dependency Management Layer

**Objective**

Ensure controlled storage and integrity of software artifacts and dependencies.

**Requirements**

- [PRA-ART-001 | PRA-Level 1] Releasable artifacts shall be stored in approved artifact repositories.
- [PRA-ART-002 | PRA-Level 1] Artifact repositories shall maintain integrity protections.
- [PRA-ART-003 | PRA-Level 2] Dependency repositories shall be controlled and monitored.

**Capabilities**

- Artifact repositories
- Dependency proxy repositories
- Artifact metadata management

Deployment and Environment Management Layer

**Objective**

Provide controlled software deployment capabilities.

**Requirements**

- [PRA-DEP-001 | PRA-Level 2] Deployment processes shall verify artifact integrity prior to release.
- [PRA-DEP-002 | PRA-Level 1] Deployment authorization shall be enforced.
- [PRA-DEP-003 | PRA-Level 1] Deployment activities shall be logged.

**Capabilities**

- Deployment orchestration tools
- Environment configuration management
- Release approval mechanisms

Evidence and Traceability Layer

**Objective**

Provide automated generation and retention of compliance evidence.

**Requirements**

- [PRA-EVI-001 | PRA-Level 1] DevSecOps pipelines shall generate machine-readable evidence artifacts.
- [PRA-EVI-002 | PRA-Level 1] Evidence shall be stored in approved repositories.
- [PRA-EVI-003 | PRA-Level 1] Evidence shall support internal and external audits.

[PRA-EVI-004 | PRA-Level 1] Evidence records SHALL carry references to the authoritative requirement and verification objects identified in programme planning data; the platform SHALL support exchange of those references without replacing the authoritative ALM system of record.

**DECISION REQUIRED A05**Confirm the authoritative ALM systems of record and ownership of requirement, verification and release object identifiers. Approve the identifier and evidence exchange contract before PRA-EVI-004 is implemented across programmes.

**Capabilities**

- Evidence repositories
- Traceability databases
- Pipeline audit logs

Operational Monitoring Layer

**Objective**

Ensure visibility into operational system behavior and security posture.

**Requirements**

- [PRA-MON-001 | PRA-Level 1] Operational environments shall record relevant security events.
- [PRA-MON-002 | PRA-Level 2] Monitoring capabilities shall support incident investigation.
- [PRA-MON-003 | PRA-Level 1] Monitoring data retention shall comply with applicable regulations.

**DECISION REQUIRED A02**DSCB-L2-REQ-015 to 017 currently say 'should' despite their mandatory-section heading. Do not treat unified logs, health and configuration publication as approved L2 platform obligations until their control level and scope are formally decided. Add linked PRA IDs and P8/P9 evidence after that decision.

**DECISION REQUIRED A06**Specify permitted destinations and interfaces for event logs, service health and non-sensitive configuration per security domain, including schema, availability, sensitivity filtering, retention and offline transfer. A single always-online shared monitoring endpoint must not be assumed for isolated deployments.

**Capabilities**

- Security monitoring tools
- Logging infrastructure
- Incident response integration

Platform Reference Architecture Levels

Platform levels define the mandatory technical capability of a DevSecOps platform instance. They describe what the platform must provide in order to support programs subject to the corresponding DevSecOps Control Baseline level.

A Platform Reference Architecture Level is not a maturity label. It is a minimum architectural capability level required to implement, enforce, and evidence the applicable control baseline in a repeatable and auditable manner.

A programme's PRA level is assessed across its documented service composition. Central enterprise services may supply one or more layers to many programmes, while a security domain may require local instances; a project does not need a separate copy of every shared service.

PRA-Level 1: Basic DevSecOps Platform

PRA-Level 1 provides the minimum platform capabilities required for enterprise DevSecOps adoption and Control Baseline Level 1 implementation.

- [PRA-L1-001 -> PRA-DW-001/004] approved development environments and authenticated developer access
- [PRA-L1-002 -> PRA-SC-001/002/003] enterprise-approved source control with review and branch protection mechanisms
- [PRA-L1-003 -> PRA-PIPE-001/002] automated build, test, and package pipelines
- [PRA-L1-004 -> PRA-ART-001] approved artifact and dependency repositories

[PRA-L1-005 -> PRA-ART-001; PRA-EVI-002] SBOM generation and storage for releasable artifacts

[PRA-L1-006 -> PRA-SEC-001; PRA-EVI-002] vulnerability scan report generation and documented vulnerability assessment support

[PRA-L1-007 -> PRA-ART-002] artifact repository integrity metadata including checksums or digests

- [PRA-L1-008 -> PRA-EVI-001/002] basic pipeline-generated evidence, SBOM records, vulnerability scan reports, vulnerability assessment records, and deployment records
- [PRA-L1-009 -> PRA-MON-001; PRA-EVI-003] logging sufficient to support internal audits and program lifecycle reviews

PRA-Level 2: Secure Managed DevSecOps Platform

PRA-Level 2 extends PRA-Level 1 with centrally managed security, access control, policy enforcement, and operational monitoring capabilities required for secure DevSecOps implementation.

- [PRA-L2-001 -> PRA-DW-002/003; PRA-SC-004] centralized identity management, role-based platform access control, and multi-factor authentication for privileged access
- [PRA-L2-002 -> PRA-PIPE-002/003] controlled pipeline execution environments and centrally approved pipeline blueprints

[PRA-L2-003 -> PRA-ART-003] controlled dependency sourcing through approved repositories and prevention of direct external downloads

[PRA-L2-004 -> PRA-PIPE-003; PRA-DEP-003] version-controlled Infrastructure as Code repositories and environment configuration change history

- [PRA-L2-005 -> PRA-SEC-001/003] automated security gates for static analysis, dependency scanning, vulnerability assessment, and policy threshold enforcement
- [PRA-L2-006 -> PRA-ART-001; PRA-EVI-002] SBOM retention, evaluation, and integration with release decision evidence for releasable artifacts
- [PRA-L2-007 -> PRA-ART-002] cryptographic artifact signing and protected signing-key management
- [PRA-L2-008 -> PRA-MON-001/002] security event forwarding to monitoring capabilities and evidence retention for compliance verification

PRA-Level 3: Trusted SDD Platform

PRA-Level 3 extends PRA-Level 2 with trusted software supply chain capabilities required for mission-critical, classified, or Software Defined Defence contexts.

- [PRA-L3-001 -> PRA-PIPE-001/003] reproducible or deterministic builds based on version-controlled source code, build configuration, and dependencies
- [PRA-L3-002 -> PRA-PIPE-002] isolated and recreatable build environments for each controlled pipeline execution
- [PRA-L3-003 -> PRA-ART-003] verifiable dependency provenance and controlled dependency sourcing
- [PRA-L3-004 -> PRA-ART-002] enterprise-managed trust infrastructure for artifact signing and verification

**DECISION REQUIRED A11**Define the signed subject and verification point for payload, licensed package or both, together with approved offline key custody, signing, revocation and recovery in isolated domains. Licensing signatures do not automatically demonstrate L3 enterprise trust; the verification record must bind the approved release to deployed content.

- [PRA-L3-005 -> PRA-EVI-001/004] end-to-end traceability from requirements to source code, verification results, build artifacts, deployment, and runtime state
- [PRA-L3-006 -> PRA-MON-002; PRA-EVI-001] runtime integrity verification and machine-readable continuous compliance evidence

Mapping to Control Baseline Levels

The required platform level shall be derived from the applicable DevSecOps Control Baseline level. A platform instance may provide a higher level than required, but shall not provide a lower level for programs subject to the corresponding control baseline.

| **Control Baseline Level** | **Required Platform Level** | **Rationale** |
| --- | --- | --- |
| Level 1: Enterprise DevSecOps Baseline | PRA-Level 1 | Provides the minimum platform capabilities required to execute controlled pipelines, maintain traceability, manage artifacts, and generate baseline evidence. |
| Level 2: Secure DevSecOps | PRA-Level 2 | Adds centrally managed security controls, access control, security gates, SBOM handling, signing, and monitoring capabilities. |
| Level 3: Trusted Software Supply Chain / SDD | PRA-Level 3 | Adds trusted supply chain capabilities including reproducible builds, isolated build environments, provenance, runtime integrity, and continuous compliance evidence. |

Minimum Capability Matrix

The following matrix defines the minimum capability expectations for each Platform Reference Architecture Level. It is a derived summary of the numbered requirements in Sections 4 and 5, not a second set of independent control obligations. The Infrastructure as Code row spans Pipeline Execution and Deployment/Environment Management; it is not a ninth logical layer.

| Capability Area | PRA-Level 1 | PRA-Level 2 | PRA-Level 3 |
| --- | --- | --- | --- |
| Developer Workspace [PRA-DW-001..004] | Approved environments; authenticated access | Central configuration baselines; RBAC; MFA for privileged access | Domain-specific isolation; hardened workspaces for restricted contexts |
| Source Control [PRA-SC-001..004] | Approved VCS; review before protected-branch integration | Central RBAC; branch protection enforcement; audit logs | Signed commits or tags where required; traceability to controlled changes |
| Pipeline Execution [PRA-PIPE-001..003] | Automated build, test, and package pipelines | Controlled runners; approved pipeline blueprints; policy gates | Isolated and recreatable build environments; reproducible build verification |
| Security and Compliance Controls [PRA-SEC-001..003] | Static analysis, dependency scanning, vulnerability scan reports, and vulnerability assessment support | Mandatory gates for vulnerabilities, policy thresholds, and compliance checks | Continuous compliance evidence; trusted policy evaluation and release blocking |
| Artifact and Dependency Management [PRA-ART-001..003] | Approved artifact and dependency repositories; SBOM generation and storage; checksum or digest records | SBOM evaluation; approved dependency sources; prevention of direct external downloads; signing service and key protection | Verifiable provenance; trusted dependency sourcing; immutable artifact records |
| Deployment and Environment Management [PRA-DEP-001..003] | Logged deployment activities; release approval mechanism | Artifact integrity verification; controlled deployment authorization | Runtime integrity verification; deployment traceability to signed artifacts |
| Evidence and Traceability [PRA-EVI-001..004] | Pipeline logs, SBOM records, vulnerability reports, assessment records, and baseline evidence repository | Machine-readable evidence linked to controls, gates, waivers, and releases | End-to-end evidence chain from requirement to runtime state |
| Operational Monitoring [PRA-MON-001..003] | Security-relevant logs retained for audit | Event forwarding to monitoring systems; incident investigation support | Integrity and compliance monitoring for mission-critical operational contexts |
| Infrastructure as Code / Environment Configuration [PRA-L2-004] | Environment configuration records sufficient for baseline audits | Version-controlled IaC repositories; infrastructure change history; IaC validation evidence | Recreatable and isolated environment definitions linked to reproducible build and deployment evidence |

Traceability Between Control Baseline and Platform Capabilities

The following traceability view links key Control Baseline requirements to the minimum platform capabilities required to implement and evidence them. It shall be maintained together with the Control Baseline requirement identifiers. The PRA IDs inserted in the Platform Capability column provide direct references back to the level profiles and layer requirements. A04 requires validation of mapping completeness and a controlled machine-readable register before approval.

| Control Baseline Requirement | Required PRA-Level | Platform Capability | Expected Evidence |
| --- | --- | --- | --- |
| DSCB-L1-REQ-001 Traceability | PRA-Level 1 | [PRA-EVI-004; PRA-L1-008] Evidence and Traceability Layer; traceability database; pipeline audit logs | requirements traceability records; configuration records |
| DSCB-L1-REQ-002/003 Source Code Integrity | PRA-Level 1 | [PRA-L1-002; PRA-SC-001/003] Approved VCS; code review; branch protection | commit history; review records; branch protection configuration |
| DSCB-L1-REQ-006 SBOM | PRA-Level 1 | [PRA-L1-005; PRA-EVI-002] SBOM generation and approved evidence repository | SBOM file; pipeline log; artifact metadata |
| DSCB-L1-REQ-009/010 Vulnerability Identification | PRA-Level 1 | [PRA-L1-006; PRA-SEC-001] Vulnerability scanning and assessment evidence support | scan reports; vulnerability assessment documentation |
| DSCB-L1-REQ-011/012 Artifact Integrity | PRA-Level 1 | [PRA-L1-007; PRA-ART-002] Artifact repository integrity metadata; checksum or digest records | checksum/digest records; artifact repository metadata |
| DSCB-L2-REQ-003/004 Platform Access Control | PRA-Level 2 | [PRA-L2-001; PRA-DW-002/003] Central IAM; RBAC; MFA for privileged access | authentication logs; access control configuration; MFA policy evidence |
| DSCB-L2-REQ-005/006 Dependency Source Control | PRA-Level 2 | [PRA-L2-003; PRA-ART-003] Approved dependency repositories; prevention of direct external downloads | repository configuration; dependency management logs |
| DSCB-L2-REQ-007/008 Artifact Signing | PRA-Level 2 | [PRA-L2-007; PRA-ART-002] Signing service; protected signing-key management | artifact signatures; signing records; key-management records |
| DSCB-L2-REQ-009/010 Infrastructure as Code | PRA-Level 2 | [PRA-L2-004; PRA-PIPE-003] Version-controlled IaC repositories and environment configuration management | infrastructure repositories; change history; validation logs |
| DSCB-L2-REQ-011/012 Pipeline Security Gates | PRA-Level 2 | [PRA-L2-005; PRA-SEC-003] Automated policy gates and release threshold enforcement | policy gate records; pipeline execution logs |
| DSCB-L2-REQ-013/014 Security Monitoring | PRA-Level 2 | [PRA-L2-008; PRA-MON-001/002] Security event forwarding and monitoring integration | security monitoring logs; security event records |
| DSCB-L3-REQ-001/002 Deterministic Builds | PRA-Level 3 | [PRA-L3-001; PRA-PIPE-001/003] Reproducible build verification and version-controlled build configuration | rebuild verification records; build configuration records |
| DSCB-L3-REQ-003/004 Build Environment Isolation | PRA-Level 3 | [PRA-L3-002; PRA-PIPE-002] Isolated and recreatable build environments | build environment configuration; pipeline execution records |
| DSCB-L3-REQ-005/006 Dependency Provenance | PRA-Level 3 | [PRA-L3-003; PRA-ART-003] Provenance capture and trusted dependency sourcing | provenance metadata; dependency records |
| DSCB-L3-REQ-007/008 Trusted Artifact Signing | PRA-Level 3 | [PRA-L3-004; PRA-ART-002] Enterprise-managed trust infrastructure | signing infrastructure records; artifact signature logs |
| DSCB-L3-REQ-009 End-to-End Traceability | PRA-Level 3 | [PRA-L3-005; PRA-EVI-004] End-to-end evidence chain from requirement to runtime state | traceability records; deployment metadata |
| DSCB-L3-REQ-010 Runtime Integrity Verification | PRA-Level 3 | [PRA-L3-006; PRA-MON-002] Runtime integrity verification and deployment traceability | runtime integrity verification logs |
| DSCB-L3-REQ-011 Continuous Compliance Evidence | PRA-Level 3 | [PRA-L3-006; PRA-EVI-001] Machine-readable continuous compliance evidence repository | compliance evidence repository; pipeline audit records |

Applicability of Domain-Specific Variants

Domain-specific platform variants, including classified, air-gapped, or restricted operational environments, shall implement the minimum PRA-Level required by the supported programs. Additional domain-specific restrictions may be applied, but shall not remove mandatory capabilities required by the applicable Platform Reference Architecture Level unless a formal waiver has been approved.

Domain-Specific Platform Variants

Where required by operational constraints, platform variants may be deployed for:

- classified environments
- air-gapped networks
- restricted operational systems

These variants shall implement the same logical architecture defined in this Standard.

Platform Stack Governance

The DevSecOps Platform Lead (role not yet implemented) shall be responsible for:

**DECISION REQUIRED GOVERNANCE**Check the current DevSecOps Directive before retaining these role and approval statements. The Directive should be the authoritative source for role, RACI and board authority; this platform standard should reference it and specify only platform service obligations. Remove any duplicated role definition in the controlled revision after the source and owner are confirmed.

- maintaining platform architecture
- providing approved pipeline blueprints
- ensuring compliance with enterprise Standards
- coordinating upgrades and lifecycle management

Platform modifications that affect control baselines shall require approval by the DevSecOps Governance Board.

Compliance Verification

Compliance with this Standard shall be verified through:

- platform architecture reviews
- DevSecOps maturity assessments
- internal audits
- program lifecycle reviews

Non-compliant platforms shall not be approved for production software delivery unless formally waived.

Relationship to Other DevSecOps Documents

This Standard shall be applied together with:

- DevSecOps Control Baseline Standard
- DevSecOps Directive
- DevSecOps Waiver Process ( to be established)

Entry into Force

This Standard enters into force upon approval by the DevSecOps Governance Board and remains valid until revised or superseded.

**Reviewer comment disposition and architecture decisions**

Informative review record. Highlighted Word insertions mark proposed wording and provisional PRA IDs. Orange notes require a decision and do not impose new controls. All six original comments are retained. Approval of stable IDs, service allocation, ALM references and monitoring status is required before this becomes a controlled standard.

| **Comment** | **Location** | **Proposed disposition** | **Status** |
| --- | --- | --- | --- |
| 22 | Sec. 4 | Numbered 24 existing layer requirements and proposed additional IDs for source-control offboarding, L1 authentication and ALM links. | A04: approve IDs |
| 23 | Secs. 4-6 | Assigned minimum PRA levels, numbered the 23 level profile entries and linked profiles, matrix and crosswalk to layer IDs. | A04: validate map |
| 26 | Source control | Added access change/revocation on leaver or mover events, with revocation evidence. | Proposed control |
| 34 | Secs. 3, 5 | Defined platform conformance as a shared and local service composition; programme allocation record required. | Service catalogue open |
| 40 | Sec. 6 | Added direct PRA ID references to the existing Control Baseline crosswalk; matrix is identified as a derived view. | A04: complete map |
| 44 | Governance | Flagged duplicate role/approval definition for alignment to the Directive before deletion or redrafting. | Governance open |

**Decisions required for controlled approval**

| **Decision** | **Proposed owners** | **Acceptance decision** |
| --- | --- | --- |
| A02 | Control Baseline, Security, Process | Confirm whether unified logs, health and configuration become L2 or L3 SHALL controls, or remain guidance; then map IDs and evidence. |
| A04 | Platform and Control Baseline owners | Approve stable PRA IDs, level assignments, direct control links and the maintained source of truth for the crosswalk. |
| A05 | ALM, Process and Platform owners | Approve authoritative object ownership and system-of-record references for requirements, verification and release evidence. |
| A06 | Platform, Operations, Security | Approve domain destinations, schemas, sensitivity filtering, retention, availability and offline monitoring interfaces. |
| A11 | Platform trust service and Security | Approve signed subject, offline key lifecycle, and verification across licensing or enclaving boundaries. |
| Services | Enterprise Platform and divisions | Approve shared service catalogue, programme allocation, provider ownership and domain-specific instances. |
| Governance | Directive owner and Board | Confirm authority and role definitions in the Directive, then remove duplication in this Standard. |

These proposals show the intended target structure. Controlled publication should accept or revise the redlines and publish one authoritative register of PRA IDs, level applicability, control mappings and evidence contracts.

## Reviewer-Kommentare

- **Reviewer**: - hier fehlen alle requirement ids in dem dokument
- **Reviewer**: - ich würde die Struktur so umbauen , dass sie genauso wie das andere Dokument fungiert - requirement den PRA Level direkt zuordnen statt sie in Stichpunkten zu wiederholen ohne rückverlinkung.
- **Reviewer**: - Source Code system shall follow the enterprise leaver process (heißt wenn jemand wechselt oder verlässt müssen die berechtigungen entzogen werden)
- **Reviewer**: - muss einen DevSecOps Platform alle relevanten tools beinhalten?Beispiel ein git Repository Service (source code repository service) - jetzt müsste ja jedes Projekt sich sein eigenen Service hochziehen um die anforderungen zu erfüllen. Das ist nicht zweckdienlich. Oder ist die Platform definiert durch eine summe an Projektspezischen Services sowie zentralen Services (Enterprise)Dann wiederrum müsste man die Enterprise Services einzeln auflisten und ihnen Requirements verpassen
- **Reviewer**: also das Kapitel würde ich auflösen durch einen ordentliche Dokumentenstruktur und direkte Requirement verlinkung. Das check ja keiner.
- **Reviewer**: das haben wir schon doppelt irgendwo drin - hab ich heute schonmal gelesen - glaube in der directive!keine doppelte Definition!
