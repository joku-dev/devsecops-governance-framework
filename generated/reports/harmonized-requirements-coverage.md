# Harmonized Requirements Candidate Coverage

This report is non-normative decision support. It does not authorize controls, policy, releases, enforcement, or consumer compliance claims.

## Summary

| Measure | Value |
|---|---:|
| Harmonized requirements | 44 |
| Covered | 9 |
| Partial | 26 |
| Gap | 9 |
| Unique source requirements | 233 |
| Source requirements mapped to covered requirements | 45 |
| Source requirements mapped to partial requirements | 145 |
| Source requirements mapped to gap requirements | 43 |
| Weighted preliminary design coverage | 50.4% |

The weighted value counts covered as 1.0, partial as 0.5, and gap as 0.0. It is not an operational compliance percentage.

## Harmonized Requirements

| ID | Area | Coverage | Source mappings | Gap |
|---|---|---|---:|---|
| `HREQ-GOV-001` Secure development lifecycle | `policy` | `partial` | 9 | Lifecycle exit and retirement criteria require explicit treatment. |
| `HREQ-GOV-002` Risk-based applicability | `policy` | `partial` | 14 | A machine-readable applicability decision is not yet defined. |
| `HREQ-GOV-003` Roles and competence | `directive` | `partial` | 10 | Competence and reviewer independence are not consistently evidenced. |
| `HREQ-GOV-004` Controlled security documentation | `evidence` | `partial` | 35 | Required document content and currency are not evaluated uniformly. |
| `HREQ-RISK-001` Asset and threat identification | `architecture` | `partial` | 6 | Runtime evidence does not require a structured asset and risk register. |
| `HREQ-RISK-002` Threat modeling | `architecture` | `partial` | 5 | Threat-model currency and review evidence are not machine-validated. |
| `HREQ-RISK-003` Risk treatment and reassessment | `architecture` | `partial` | 3 | A structured risk-treatment evidence contract is missing. |
| `HREQ-RISK-004` Security architecture review | `architecture` | `partial` | 9 | Detailed review outcomes are not consistently captured as typed evidence. |
| `HREQ-APP-001` Authentication and authorization | `product_architecture` | `partial` | 9 | Application-level verification is not part of the current DevSecOps baseline. |
| `HREQ-APP-002` Session security | `product_architecture` | `gap` | 2 | No explicit session-security requirement exists. |
| `HREQ-APP-003` Data and cryptographic protection | `product_architecture` | `partial` | 11 | Detailed data-protection verification is not represented in the current baseline. |
| `HREQ-APP-004` Input validation and business logic | `product_architecture` | `gap` | 4 | No atomic validation and business-logic requirement exists. |
| `HREQ-APP-005` Secure file handling | `product_architecture` | `gap` | 2 | No atomic secure file-handling requirement exists. |
| `HREQ-APP-006` Application logging and error handling | `product_architecture` | `partial` | 10 | Application error behavior and log protection are not fully evaluated. |
| `HREQ-APP-007` Secure defaults and hardening | `product_architecture` | `partial` | 12 | Product-level default-setting verification is missing. |
| `HREQ-DEV-001` Source control and integrity | `control_baseline` | `covered` | 3 | - |
| `HREQ-DEV-002` Secure coding practices | `control_baseline` | `partial` | 9 | Language-specific applicability and training evidence are not defined. |
| `HREQ-DEV-003` Code and implementation review | `control_baseline` | `partial` | 6 | Review scope and independence are not consistently evidenced. |
| `HREQ-DEV-004` Secure development environments | `platform` | `partial` | 4 | Periodic cryptographic integrity verification is not defined. |
| `HREQ-DEV-005` External component and supplier assurance | `control_baseline` | `partial` | 10 | Supplier assurance and contractual verification are not explicit. |
| `HREQ-SC-001` Controlled build execution | `control_baseline` | `covered` | 5 | - |
| `HREQ-SC-002` Reproducible and isolated builds | `control_baseline` | `covered` | 3 | - |
| `HREQ-SC-003` Artifact identity and integrity | `control_baseline` | `covered` | 3 | - |
| `HREQ-SC-004` Artifact signing and key protection | `control_baseline` | `covered` | 9 | - |
| `HREQ-SC-005` Trusted dependency sources and provenance | `control_baseline` | `covered` | 2 | - |
| `HREQ-SC-006` SBOM generation | `control_baseline` | `covered` | 62 | - |
| `HREQ-SC-007` SBOM component identity and relationships | `evidence` | `partial` | 13 | SBOM presence is checked but detailed component fields are not. |
| `HREQ-SC-008` SBOM integrity and source metadata | `evidence` | `partial` | 9 | Component-level digest and source metadata are not validated. |
| `HREQ-SC-009` SBOM license metadata | `evidence` | `gap` | 11 | License metadata is not part of the current SBOM evidence contract. |
| `HREQ-SC-010` Component license compliance | `control_baseline` | `gap` | 2 | No component-license control or evidence type exists. |
| `HREQ-TEST-001` Test strategy and acceptance | `control_baseline` | `partial` | 2 | Test planning and acceptance artifacts are not standardized. |
| `HREQ-TEST-002` Functional, non-functional, and regression testing | `control_baseline` | `partial` | 6 | Test-category evidence and minimum expectations are not defined. |
| `HREQ-TEST-003` Security requirements verification | `architecture` | `partial` | 5 | Security test evidence is not typed at requirement level. |
| `HREQ-TEST-004` Vulnerability testing | `control_baseline` | `covered` | 5 | - |
| `HREQ-TEST-005` Penetration testing | `architecture` | `partial` | 5 | Scope, frequency, independence, and evidence are not defined. |
| `HREQ-TEST-006` Independent and protected testing | `directive` | `gap` | 2 | No unified testing-independence and test-data requirement exists. |
| `HREQ-OPS-001` Security release gates | `control_baseline` | `covered` | 16 | - |
| `HREQ-OPS-002` Vulnerability triage and remediation | `control_baseline` | `partial` | 1 | Remediation timelines and closure evidence are not modeled. |
| `HREQ-OPS-003` Security update management | `control_baseline` | `gap` | 14 | No complete security-update lifecycle control exists. |
| `HREQ-OPS-004` Security monitoring and alerting | `control_baseline` | `partial` | 11 | Log protection, retention, and alert-response evidence are incomplete. |
| `HREQ-OPS-005` Deployment and configuration verification | `platform` | `partial` | 4 | Deployment verification evidence is not standardized. |
| `HREQ-OPS-006` Secure operation guidance | `product_architecture` | `partial` | 2 | Required secure-operation content is not defined. |
| `HREQ-OPS-007` Secure decommissioning and disposal | `product_architecture` | `gap` | 3 | No end-to-end decommissioning requirement exists. |
| `HREQ-OPS-008` Product security response and health review | `directive` | `gap` | 3 | Product security response is not represented as a complete governed capability. |

## Decision Boundary

All mappings require human review. Candidate material must not change runtime governance or released baselines before approval.
