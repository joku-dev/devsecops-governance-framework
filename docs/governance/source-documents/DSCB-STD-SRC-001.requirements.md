# DevSecOps Control Baseline Requirements

This file contains a sanitized requirements-only extraction from a private source document. Original source text, document metadata, personal names, organization-specific labels, document numbers, images, and distribution metadata are intentionally not included.

| ID | Strength | Context | Requirement |
|---|---|---|---|
| `DSCB-STD-SRC-001-REQ-001` | REQUIREMENT | DevSecOps Control Baseline Standard | 0.2 \| Aligned with Platform Reference Architecture Levels; clarified artifact integrity evidence and added requirement identifiers \| 3/4/5 |
| `DSCB-STD-SRC-001-REQ-002` | MUST | Aim and Purpose | The Control Baseline specifies the minimum mandatory lifecycle controls and required evidence artifacts that must be implemented for all software developed within the scope of the DevSecOps Policy. |
| `DSCB-STD-SRC-001-REQ-003` | REQUIREMENT | Aim and Purpose | compliant with cybersecurity and safety requirements. |
| `DSCB-STD-SRC-001-REQ-004` | MUST | The Chief Digitalisation Office | When a version is quoted, this version shall be used. |
| `DSCB-STD-SRC-001-REQ-005` | REQUIREMENT | ISO/IEC 27001 | These frameworks inform the definition of lifecycle security controls and software supply chain integrity requirements. |
| `DSCB-STD-SRC-001-REQ-006` | MUST | Relationship to Platform Reference Architecture Levels | The DevSecOps Platform Reference Architecture defines the minimum platform capabilities required to implement, enforce, and evidence those controls. |
| `DSCB-STD-SRC-001-REQ-007` | MUST | Relationship to Platform Reference Architecture Levels | The required platform level shall therefore be derived from the applicable Control Baseline level. |
| `DSCB-STD-SRC-001-REQ-008` | MUST | Relationship to Platform Reference Architecture Levels | Control Baseline Level \| Required Platform Level \| Purpose of Alignment |
| `DSCB-STD-SRC-001-REQ-009` | REQUIREMENT | Control Objective | Ensure traceability between requirements and implemented software and the corresponding Testcases and Reports. |
| `DSCB-STD-SRC-001-REQ-010` | MUST | Control Objective | [DSCB-L1-REQ-001]All software components SHALL be traceable to defined system or software requirements and the corresponding Testcases and Reports. |
| `DSCB-STD-SRC-001-REQ-011` | MUST | Control Objective | [DSCB-L1-REQ-002]All software source code SHALL be maintained in approved version control systems and changes SHALL be traceable to an identifiable author. |
| `DSCB-STD-SRC-001-REQ-012` | MUST | Control Objective | [DSCB-L1-REQ-003]Direct modification of protected branches SHALL be prohibited. |
| `DSCB-STD-SRC-001-REQ-013` | MUST | Control Objective | [DSCB-L1-REQ-004]Secure coding practices SHALL be applied and security-relevant coding errors SHALL be detected during development or testing. |
| `DSCB-STD-SRC-001-REQ-014` | MUST | Control Objective | [DSCB-L1-REQ-005]All software dependencies SHALL be identifiable and documented. |
| `DSCB-STD-SRC-001-REQ-015` | MUST | Control Objective | [DSCB-L1-REQ-006]A Software Bill of Materials (SBOM) SHALL be generated for releasable artifacts. |
| `DSCB-STD-SRC-001-REQ-016` | MUST | Control Objective | [DSCB-L1-REQ-007]Software builds SHALL be executed through controlled automated pipelines. |
| `DSCB-STD-SRC-001-REQ-017` | MUST | Control Objective | [DSCB-L1-REQ-008]Build outputs SHALL be uniquely identifiable. |
| `DSCB-STD-SRC-001-REQ-018` | MUST | Control Objective | [DSCB-L1-REQ-009]Automated vulnerability scanning SHALL be performed during build or test stages. |
| `DSCB-STD-SRC-001-REQ-019` | MUST | Control Objective | [DSCB-L1-REQ-010]Identified vulnerabilities SHALL be evaluated prior to release. |
| `DSCB-STD-SRC-001-REQ-020` | MUST | Control Objective | [DSCB-L1-REQ-011]Releasable software artifacts SHALL be protected against tampering by approved repository integrity controls and cryptographic integrity mechanisms such as checksums, digests, or signatures, as applicable to the required control baseline level. |
| `DSCB-STD-SRC-001-REQ-021` | MUST | Control Objective | [DSCB-L1-REQ-012]Artifacts SHALL be uniquely identifiable. |
| `DSCB-STD-SRC-001-REQ-022` | MUST | Control Objective | [DSCB-L1-REQ-013]Deployment of software artifacts SHALL require authorized approval. |
| `DSCB-STD-SRC-001-REQ-023` | MUST | Control Objective | [DSCB-L1-REQ-014]Only approved artifacts SHALL be deployed. |
| `DSCB-STD-SRC-001-REQ-024` | MUST | Control Objective | [DSCB-L1-REQ-015]DevSecOps pipelines SHALL generate machine-readable evidence artifacts for implemented controls. |
| `DSCB-STD-SRC-001-REQ-025` | MUST | Control Objective | [DSCB-L1-REQ-016]Operational environments SHALL maintain records of deployed software versions and relevant security events. |
| `DSCB-STD-SRC-001-REQ-026` | MUST | Control Objective | [DSCB-L2-REQ-001]Development environments SHALL be centrally managed. |
| `DSCB-STD-SRC-001-REQ-027` | MUST | Control Objective | [DSCB-L2-REQ-002]Development environments SHALL comply with enterprise security configuration standards. |
| `DSCB-STD-SRC-001-REQ-028` | MUST | Control Objective | [DSCB-L2-REQ-003]Access to DevSecOps platforms SHALL be controlled through centralized identity management |
| `DSCB-STD-SRC-001-REQ-029` | MUST | Control Objective | [DSCB-L2-REQ-004]Multi-factor authentication SHALL be enforced for privileged access. |
| `DSCB-STD-SRC-001-REQ-030` | MUST | Control Objective | [DSCB-L2-REQ-005]Software dependencies SHALL be retrieved from approved repositories. |
| `DSCB-STD-SRC-001-REQ-031` | MUST | Control Objective | [DSCB-L2-REQ-006]Direct downloads from external sources SHALL NOT be permitted. |
| `DSCB-STD-SRC-001-REQ-032` | MUST | Control Objective | [DSCB-L2-REQ-007]Software artifacts SHALL be cryptographically signed before release. |
| `DSCB-STD-SRC-001-REQ-033` | MUST | Control Objective | [DSCB-L2-REQ-008]Signing keys SHALL be protected and managed according to enterprise security policies. |
| `DSCB-STD-SRC-001-REQ-034` | MUST | Control Objective | [DSCB-L2-REQ-009]Infrastructure used for software deployment SHALL be defined through Infrastructure as Code. |
| `DSCB-STD-SRC-001-REQ-035` | MUST | Control Objective | [DSCB-L2-REQ-010]Infrastructure definitions SHALL be maintained in version control. |
| `DSCB-STD-SRC-001-REQ-036` | MUST | Control Objective | [DSCB-L2-REQ-011]DevSecOps pipelines SHALL enforce security gates. |
| `DSCB-STD-SRC-001-REQ-037` | MUST | Control Objective | [DSCB-L2-REQ-012]Releases SHALL NOT proceed when defined security thresholds are exceeded. |
| `DSCB-STD-SRC-001-REQ-038` | MUST | Control Objective | [DSCB-L2-REQ-013]Operational systems SHALL generate security-relevant events. |
| `DSCB-STD-SRC-001-REQ-039` | MUST | Control Objective | [DSCB-L2-REQ-014]Security events SHALL be forwarded to monitoring systems. |
| `DSCB-STD-SRC-001-REQ-040` | MUST | Control Objective | [DSCB-L3-REQ-001]Software builds SHALL be reproducible using identical source code and build configuration. |
| `DSCB-STD-SRC-001-REQ-041` | MUST | Control Objective | [DSCB-L3-REQ-002]Build configurations SHALL be version controlled. |
| `DSCB-STD-SRC-001-REQ-042` | MUST | Control Objective | [DSCB-L3-REQ-003]Software builds SHALL be executed in isolated build environments. |
| `DSCB-STD-SRC-001-REQ-043` | MUST | Control Objective | [DSCB-L3-REQ-004]Build environments SHALL be recreated for each pipeline execution. |
| `DSCB-STD-SRC-001-REQ-044` | MUST | Control Objective | [DSCB-L3-REQ-005]Software dependencies SHALL include verifiable provenance information. |
| `DSCB-STD-SRC-001-REQ-045` | MUST | Control Objective | [DSCB-L3-REQ-006]Dependency provenance SHALL be recorded during the build process. |
| `DSCB-STD-SRC-001-REQ-046` | MUST | Control Objective | [DSCB-L3-REQ-007]Software artifacts SHALL be signed using enterprise signing infrastructure. |
| `DSCB-STD-SRC-001-REQ-047` | MUST | Control Objective | [DSCB-L3-REQ-008]Signing keys SHALL be centrally managed. |
| `DSCB-STD-SRC-001-REQ-048` | MUST | Control Objective | [DSCB-L3-REQ-009]Traceability SHALL exist between requirements, source code, verification Cases / Procedures and Test result, build artifacts, and deployed software. |
| `DSCB-STD-SRC-001-REQ-049` | MUST | Control Objective | [DSCB-L3-REQ-010]Runtime environments SHALL verify the integrity of deployed software artifacts. |
| `DSCB-STD-SRC-001-REQ-050` | MUST | Control Objective | [DSCB-L3-REQ-011]DevSecOps platforms SHALL generate machine-readable compliance evidence for lifecycle activities. |
| `DSCB-STD-SRC-001-REQ-051` | MUST | Applicability | [DSCB-GOV-REQ-001]All programs SHALL implement the Level 1 Control Baseline. |
| `DSCB-STD-SRC-001-REQ-052` | MUST | Compliance Verification | [DSCB-GOV-REQ-002]Compliance with this Standard SHALL be verified through: |
| `DSCB-STD-SRC-001-REQ-053` | MUST | DevSecOps maturity assessments | [DSCB-GOV-REQ-003]Non-compliance requires an approved waiver. |
| `DSCB-STD-SRC-001-REQ-054` | MUST | Deviations | [DSCB-GOV-REQ-004]Deviations from this Standard SHALL follow the waiver process defined in the DevSecOps Directive. |
| `DSCB-STD-SRC-001-REQ-055` | MUST | Deviations | [DSCB-GOV-REQ-005]All deviations SHALL: |

## Extraction Notes

- Extraction mode: requirements-only sanitized Markdown.
- Source kind: DOCX.
- This file is suitable for controlled internal review before any public publication decision.
