# Automation Coverage Report

## Summary

- Total requirements: 46
- Blocking gates: 15
- Automation-supported requirements: 45
- Review-led requirements: 1
- Automation-supported coverage: 97.8%
- Blocking-gate coverage: 32.6%

## By Automation Type

| Type | Count |
|---|---:|
| `blocking_gate` | 15 |
| `warning_gate` | 0 |
| `evidence_check` | 30 |
| `review_check` | 1 |

## By Maturity

| Maturity | Count |
|---|---:|
| `immediate` | 19 |
| `tool_integration_required` | 22 |
| `future` | 5 |

## By Check Type

| Check Type | Count |
|---|---:|
| `presence` | 10 |
| `linkage` | 8 |
| `threshold` | 2 |
| `configuration` | 14 |
| `approval` | 4 |
| `review` | 1 |
| `integrity` | 5 |
| `provenance` | 2 |

## By Level

| Level | Blocking Gate | Warning Gate | Evidence Check | Review Check |
|---|---:|---:|---:|---:|
| L1 | 6 | 0 | 10 | 0 |
| L2 | 6 | 0 | 8 | 0 |
| L3 | 1 | 0 | 10 | 0 |
| GOV | 2 | 0 | 2 | 1 |

## Governance Requirements

- Policy requirements: 21
- Directive requirements: 22
- Total Policy/Directive requirements: 43

| Source | Blocking Gate | Evidence Check | Review Check | Warning Gate |
|---|---:|---:|---:|---:|
| DevSecOps Policy | 5 | 15 | 1 | 0 |
| DevSecOps Directive | 3 | 18 | 1 | 0 |

## Requirement Classification

| ID | Level | Title | Type | Maturity |
|---|---|---|---|---|
| `DSCB-GOV-REQ-001` | GOV | Applicability | `evidence_check` | `immediate` |
| `DSCB-GOV-REQ-002` | GOV | Compliance Verification | `review_check` | `tool_integration_required` |
| `DSCB-GOV-REQ-003` | GOV | Compliance Verification | `blocking_gate` | `immediate` |
| `DSCB-GOV-REQ-004` | GOV | Deviations | `evidence_check` | `immediate` |
| `DSCB-GOV-REQ-005` | GOV | Deviations | `blocking_gate` | `immediate` |
| `DSCB-L1-REQ-001` | L1 | Traceability | `evidence_check` | `tool_integration_required` |
| `DSCB-L1-REQ-002` | L1 | Source Code Integrity | `evidence_check` | `immediate` |
| `DSCB-L1-REQ-003` | L1 | Source Code Integrity | `blocking_gate` | `immediate` |
| `DSCB-L1-REQ-004` | L1 | Secure Coding Practices | `evidence_check` | `tool_integration_required` |
| `DSCB-L1-REQ-005` | L1 | Software Supply Chain Transparency | `evidence_check` | `immediate` |
| `DSCB-L1-REQ-006` | L1 | Software Supply Chain Transparency | `blocking_gate` | `immediate` |
| `DSCB-L1-REQ-007` | L1 | Controlled Build Process | `evidence_check` | `immediate` |
| `DSCB-L1-REQ-008` | L1 | Controlled Build Process | `evidence_check` | `immediate` |
| `DSCB-L1-REQ-009` | L1 | Vulnerability Identification | `blocking_gate` | `immediate` |
| `DSCB-L1-REQ-010` | L1 | Vulnerability Identification | `blocking_gate` | `tool_integration_required` |
| `DSCB-L1-REQ-011` | L1 | Artifact Integrity | `blocking_gate` | `immediate` |
| `DSCB-L1-REQ-012` | L1 | Artifact Integrity | `evidence_check` | `immediate` |
| `DSCB-L1-REQ-013` | L1 | Release Authorization | `evidence_check` | `tool_integration_required` |
| `DSCB-L1-REQ-014` | L1 | Release Authorization | `blocking_gate` | `tool_integration_required` |
| `DSCB-L1-REQ-015` | L1 | Pipeline Evidence Generation | `evidence_check` | `immediate` |
| `DSCB-L1-REQ-016` | L1 | Operational Traceability | `evidence_check` | `tool_integration_required` |
| `DSCB-L2-REQ-001` | L2 | Secure Development Environments | `evidence_check` | `tool_integration_required` |
| `DSCB-L2-REQ-002` | L2 | Secure Development Environments | `evidence_check` | `tool_integration_required` |
| `DSCB-L2-REQ-003` | L2 | DevSecOps Platform Access Control | `evidence_check` | `tool_integration_required` |
| `DSCB-L2-REQ-004` | L2 | DevSecOps Platform Access Control | `blocking_gate` | `tool_integration_required` |
| `DSCB-L2-REQ-005` | L2 | Dependency Source Control | `blocking_gate` | `tool_integration_required` |
| `DSCB-L2-REQ-006` | L2 | Dependency Source Control | `blocking_gate` | `immediate` |
| `DSCB-L2-REQ-007` | L2 | Artifact Signing | `blocking_gate` | `tool_integration_required` |
| `DSCB-L2-REQ-008` | L2 | Artifact Signing | `evidence_check` | `tool_integration_required` |
| `DSCB-L2-REQ-009` | L2 | Infrastructure as Code | `evidence_check` | `tool_integration_required` |
| `DSCB-L2-REQ-010` | L2 | Infrastructure as Code | `evidence_check` | `immediate` |
| `DSCB-L2-REQ-011` | L2 | Pipeline Security Gates | `blocking_gate` | `immediate` |
| `DSCB-L2-REQ-012` | L2 | Pipeline Security Gates | `blocking_gate` | `immediate` |
| `DSCB-L2-REQ-013` | L2 | Security Monitoring | `evidence_check` | `tool_integration_required` |
| `DSCB-L2-REQ-014` | L2 | Security Monitoring | `evidence_check` | `tool_integration_required` |
| `DSCB-L3-REQ-001` | L3 | Deterministic Builds | `evidence_check` | `future` |
| `DSCB-L3-REQ-002` | L3 | Deterministic Builds | `evidence_check` | `immediate` |
| `DSCB-L3-REQ-003` | L3 | Build Environment Isolation | `evidence_check` | `tool_integration_required` |
| `DSCB-L3-REQ-004` | L3 | Build Environment Isolation | `evidence_check` | `tool_integration_required` |
| `DSCB-L3-REQ-005` | L3 | Dependency Provenance | `evidence_check` | `future` |
| `DSCB-L3-REQ-006` | L3 | Dependency Provenance | `evidence_check` | `future` |
| `DSCB-L3-REQ-007` | L3 | Trusted Artifact Signing | `blocking_gate` | `tool_integration_required` |
| `DSCB-L3-REQ-008` | L3 | Trusted Artifact Signing | `evidence_check` | `tool_integration_required` |
| `DSCB-L3-REQ-009` | L3 | End-to-End Traceability | `evidence_check` | `future` |
| `DSCB-L3-REQ-010` | L3 | Runtime Integrity Verification | `evidence_check` | `future` |
| `DSCB-L3-REQ-011` | L3 | Continuous Compliance Evidence | `evidence_check` | `tool_integration_required` |

## Verification Requirements

| ID | Check Type | Verification Requirement |
|---|---|---|
| `DSCB-GOV-REQ-001` | `presence` | Program governance records SHALL identify the applicable Control Baseline level for each program. |
| `DSCB-GOV-REQ-002` | `review` | Compliance verification evidence SHALL include maturity assessment, audit, architecture review, or program lifecycle review records as applicable. |
| `DSCB-GOV-REQ-003` | `approval` | Non-compliance records SHALL reference an approved waiver before a release, deployment, or governance decision is accepted. |
| `DSCB-GOV-REQ-004` | `linkage` | Deviation records SHALL reference the defined waiver process and waiver registry entry. |
| `DSCB-GOV-REQ-005` | `approval` | Each deviation SHALL provide machine-readable waiver evidence containing justification, documentation reference, risk classification, and expiry date. |
| `DSCB-L1-REQ-001` | `linkage` | Each release candidate SHALL provide machine-readable traceability records linking software components to defined system or software requirements and corresponding test cases or reports. |
| `DSCB-L1-REQ-002` | `configuration` | Each repository SHALL provide machine-readable commit and author metadata showing that source code changes are maintained in an approved version control system and attributable to an identifiable author. |
| `DSCB-L1-REQ-003` | `configuration` | Protected branch configuration SHALL show that direct pushes are disabled and changes require the defined integration workflow. |
| `DSCB-L1-REQ-004` | `presence` | Each releasable software change SHALL provide secure coding evidence, including configured static analysis results and code review records for the applicable technology stack. |
| `DSCB-L1-REQ-005` | `presence` | Each release candidate SHALL provide a machine-readable dependency inventory or SBOM covering the software dependencies included in the artifact. |
| `DSCB-L1-REQ-006` | `linkage` | Each release candidate SHALL provide a machine-readable SBOM linked to the releasable artifact identifier. |
| `DSCB-L1-REQ-007` | `presence` | Each release candidate SHALL provide pipeline execution evidence showing that build activities were executed through controlled automated pipelines. |
| `DSCB-L1-REQ-008` | `presence` | Each build output SHALL provide artifact metadata containing a unique artifact identifier, version, digest, or equivalent repository identifier. |
| `DSCB-L1-REQ-009` | `presence` | Each build or release candidate SHALL provide machine-readable vulnerability scan evidence from the build or test stage. |
| `DSCB-L1-REQ-010` | `threshold` | Each release candidate SHALL provide vulnerability assessment evidence showing that identified vulnerabilities were evaluated or covered by an approved waiver before release. |
| `DSCB-L1-REQ-011` | `integrity` | Each releasable artifact SHALL provide integrity evidence such as checksum, digest, repository integrity metadata, or signature linked to the artifact identifier. |
| `DSCB-L1-REQ-012` | `presence` | Each artifact SHALL provide repository metadata proving a unique and stable artifact identity. |
| `DSCB-L1-REQ-013` | `approval` | Each deployment or release candidate SHALL provide approval evidence linked to the artifact, release, or deployment record. |
| `DSCB-L1-REQ-014` | `approval` | Deployment evidence SHALL show that only artifacts with approved release status were deployed. |
| `DSCB-L1-REQ-015` | `presence` | Each pipeline execution SHALL produce a machine-readable evidence bundle covering the implemented controls applicable to the pipeline stage. |
| `DSCB-L1-REQ-016` | `linkage` | Each operational deployment SHALL provide records linking deployed software versions to deployment records and relevant security or incident events. |
| `DSCB-L2-REQ-001` | `configuration` | Platform inventory or configuration management evidence SHALL show that development environments are centrally managed. |
| `DSCB-L2-REQ-002` | `configuration` | Development environment evidence SHALL show compliance with the applicable enterprise security configuration baseline. |
| `DSCB-L2-REQ-003` | `configuration` | Platform configuration evidence SHALL show that DevSecOps platform access is integrated with centralized identity management. |
| `DSCB-L2-REQ-004` | `configuration` | Privileged access evidence SHALL show that multi-factor authentication is enforced for privileged DevSecOps platform roles. |
| `DSCB-L2-REQ-005` | `configuration` | Build and dependency configuration SHALL show that software dependencies are retrieved from approved repositories. |
| `DSCB-L2-REQ-006` | `configuration` | Pipeline, build, or dependency logs SHALL show that direct downloads from non-approved external sources are not used. |
| `DSCB-L2-REQ-007` | `integrity` | Each releasable artifact SHALL provide signature evidence created before release. |
| `DSCB-L2-REQ-008` | `configuration` | Signing infrastructure evidence SHALL show that signing keys are protected and managed according to enterprise security policy. |
| `DSCB-L2-REQ-009` | `linkage` | Deployment evidence SHALL reference version-controlled Infrastructure as Code definitions for the deployed infrastructure. |
| `DSCB-L2-REQ-010` | `configuration` | Infrastructure definition evidence SHALL show that IaC sources are maintained in version control with change history. |
| `DSCB-L2-REQ-011` | `presence` | Pipeline execution evidence SHALL show that required security gates were executed for the relevant lifecycle stage. |
| `DSCB-L2-REQ-012` | `threshold` | Release decision evidence SHALL show that releases are blocked when security thresholds are exceeded unless an approved waiver exists. |
| `DSCB-L2-REQ-013` | `presence` | Operational system evidence SHALL show that defined security-relevant events are generated. |
| `DSCB-L2-REQ-014` | `configuration` | Monitoring configuration or telemetry evidence SHALL show that security events are forwarded to approved monitoring systems. |
| `DSCB-L3-REQ-001` | `integrity` | Rebuild verification evidence SHALL show that the same source code and build configuration can reproduce the expected build output within defined tolerance. |
| `DSCB-L3-REQ-002` | `linkage` | Build configuration evidence SHALL show that build definitions are maintained in version control and linked to the build execution. |
| `DSCB-L3-REQ-003` | `configuration` | Pipeline evidence SHALL show that builds are executed in isolated build environments. |
| `DSCB-L3-REQ-004` | `configuration` | Pipeline environment evidence SHALL show that build environments are recreated for each controlled pipeline execution. |
| `DSCB-L3-REQ-005` | `provenance` | Dependency metadata SHALL provide verifiable provenance information for dependencies used in the build. |
| `DSCB-L3-REQ-006` | `provenance` | Build evidence SHALL record dependency provenance metadata during the build process. |
| `DSCB-L3-REQ-007` | `integrity` | Artifact signature evidence SHALL show that released artifacts are signed using enterprise signing infrastructure. |
| `DSCB-L3-REQ-008` | `configuration` | Trust infrastructure evidence SHALL show that signing keys are centrally managed. |
| `DSCB-L3-REQ-009` | `linkage` | Each release candidate SHALL provide end-to-end traceability evidence linking requirements, source code, verification results, build artifacts, deployment metadata, and deployed software. |
| `DSCB-L3-REQ-010` | `integrity` | Runtime evidence SHALL show integrity verification results for deployed software artifacts. |
| `DSCB-L3-REQ-011` | `linkage` | The DevSecOps platform SHALL provide machine-readable compliance evidence covering lifecycle activities and linked control identifiers. |
