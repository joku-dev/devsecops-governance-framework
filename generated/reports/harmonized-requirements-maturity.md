# Harmonized Requirements Candidate Maturity Assignment

This report is non-normative decision support. It assigns proposed minimum maturity levels but does not change controls, baselines, evidence contracts, policy, enforcement, releases, or consumer compliance state.

## Level Model

| Level | Name | Intent | Introduced | Cumulative active |
|---|---|---|---:|---:|
| `L1` | Foundational | Establish repeatable minimum security practices and evidence for all applicable software. | 22 | 22 |
| `L2` | Managed | Add centrally managed capabilities, standardized verification, monitoring, and enforceable gates. | 17 | 39 |
| `L3` | High Assurance | Add isolation, provenance, continuous verification, and machine-readable high-assurance evidence. | 1 | 40 |
| `GOV` | Governance Overlay | Govern applicability, accountability, review, deviations, and lifecycle decisions across all maturity levels. | 4 | 4 |

Levels are cumulative: an L1 requirement remains active at L2 and L3; an L2 requirement remains active at L3. GOV is a cross-level overlay and is counted separately. Applicability remains an independent decision, so a capability-based requirement applies only when the relevant capability exists.

## Routing Lanes

| Routing lane | Requirements |
|---|---:|
| `architecture` | 5 |
| `devsecops_baseline` | 15 |
| `evidence` | 3 |
| `governance` | 4 |
| `operations` | 4 |
| `platform` | 2 |
| `product_security` | 11 |

## Proposed Assignments

| ID | Requirement | Minimum | Path | Applicability | Route | Current coverage | Existing refs |
|---|---|---|---|---|---|---|---|
| `HREQ-GOV-001` | Secure development lifecycle | `GOV` | GOV | `all_software` | `governance` | `partial` | `DEVSECOPS-POL-SRC-001-REQ-020` |
| `HREQ-GOV-002` | Risk-based applicability | `GOV` | GOV | `all_software` | `governance` | `partial` | `DEVSECOPS-POL-SRC-001-REQ-017` |
| `HREQ-GOV-003` | Roles and competence | `GOV` | GOV | `all_software` | `governance` | `partial` | `DEVSECOPS-POL-SRC-001-REQ-014` |
| `HREQ-GOV-004` | Controlled security documentation | `GOV` | GOV | `all_software` | `governance` | `partial` | `DSCB-L1-REQ-001`, `P1` |
| `HREQ-RISK-001` | Asset and threat identification | `L1` | L1 → L2 → L3 | `risk_based` | `architecture` | `partial` | `S5`, `P8`, `E6` |
| `HREQ-RISK-002` | Threat modeling | `L2` | L2 → L3 | `risk_based` | `architecture` | `partial` | `S5`, `P8` |
| `HREQ-RISK-003` | Risk treatment and reassessment | `L2` | L2 → L3 | `risk_based` | `architecture` | `partial` | `AG-EXC-001`, `RG-RELEASE-READY` |
| `HREQ-RISK-004` | Security architecture review | `L2` | L2 → L3 | `risk_based` | `architecture` | `partial` | `S5`, `P8`, `E6` |
| `HREQ-APP-001` | Authentication and authorization | `L1` | L1 → L2 → L3 | `capability_based` | `product_security` | `partial` | `S5`, `P8` |
| `HREQ-APP-002` | Session security | `L1` | L1 → L2 → L3 | `session_capable_software` | `product_security` | `gap` | - |
| `HREQ-APP-003` | Data and cryptographic protection | `L1` | L1 → L2 → L3 | `sensitive_data_processing` | `product_security` | `partial` | `S5`, `P8`, `E5` |
| `HREQ-APP-004` | Input validation and business logic | `L1` | L1 → L2 → L3 | `input_processing_software` | `product_security` | `gap` | - |
| `HREQ-APP-005` | Secure file handling | `L1` | L1 → L2 → L3 | `file_processing_software` | `product_security` | `gap` | - |
| `HREQ-APP-006` | Application logging and error handling | `L1` | L1 → L2 → L3 | `all_software` | `product_security` | `partial` | `DSCB-L2-REQ-013`, `DSCB-L2-REQ-014`, `P11` |
| `HREQ-APP-007` | Secure defaults and hardening | `L1` | L1 → L2 → L3 | `all_software` | `product_security` | `partial` | `DSCB-L2-REQ-002`, `P8` |
| `HREQ-DEV-001` | Source control and integrity | `L1` | L1 → L2 → L3 | `all_software` | `devsecops_baseline` | `covered` | `DSCB-L1-REQ-002`, `DSCB-L1-REQ-003` |
| `HREQ-DEV-002` | Secure coding practices | `L1` | L1 → L2 → L3 | `source_developed_software` | `devsecops_baseline` | `partial` | `DSCB-L1-REQ-004` |
| `HREQ-DEV-003` | Code and implementation review | `L1` | L1 → L2 → L3 | `source_developed_software` | `devsecops_baseline` | `partial` | `DSCB-L1-REQ-004` |
| `HREQ-DEV-004` | Secure development environments | `L2` | L2 → L3 | `source_developed_software` | `platform` | `partial` | `DSCB-L2-REQ-001`, `DSCB-L2-REQ-002` |
| `HREQ-DEV-005` | External component and supplier assurance | `L2` | L2 → L3 | `third_party_components` | `devsecops_baseline` | `partial` | `DSCB-L2-REQ-005`, `DSCB-L3-REQ-005` |
| `HREQ-SC-001` | Controlled build execution | `L1` | L1 → L2 → L3 | `built_software` | `devsecops_baseline` | `covered` | `DSCB-L1-REQ-007`, `DSCB-L1-REQ-008` |
| `HREQ-SC-002` | Reproducible and isolated builds | `L3` | L3 | `high_assurance_software` | `devsecops_baseline` | `covered` | `DSCB-L3-REQ-001`, `DSCB-L3-REQ-002`, `DSCB-L3-REQ-003`, `DSCB-L3-REQ-004` |
| `HREQ-SC-003` | Artifact identity and integrity | `L1` | L1 → L2 → L3 | `releasable_artifacts` | `devsecops_baseline` | `covered` | `DSCB-L1-REQ-011`, `DSCB-L1-REQ-012` |
| `HREQ-SC-004` | Artifact signing and key protection | `L2` | L2 → L3 | `baseline_level_based` | `devsecops_baseline` | `covered` | `DSCB-L2-REQ-007`, `DSCB-L2-REQ-008`, `DSCB-L3-REQ-007`, `DSCB-L3-REQ-008` |
| `HREQ-SC-005` | Trusted dependency sources and provenance | `L2` | L2 → L3 | `third_party_components` | `devsecops_baseline` | `covered` | `DSCB-L2-REQ-005`, `DSCB-L2-REQ-006`, `DSCB-L3-REQ-005`, `DSCB-L3-REQ-006` |
| `HREQ-SC-006` | SBOM generation | `L1` | L1 → L2 → L3 | `releasable_artifacts` | `devsecops_baseline` | `covered` | `DSCB-L1-REQ-005`, `DSCB-L1-REQ-006` |
| `HREQ-SC-007` | SBOM component identity and relationships | `L2` | L2 → L3 | `releasable_artifacts` | `evidence` | `partial` | `DSCB-L1-REQ-005`, `DSCB-L1-REQ-006` |
| `HREQ-SC-008` | SBOM integrity and source metadata | `L2` | L2 → L3 | `releasable_artifacts` | `evidence` | `partial` | `DSCB-L1-REQ-011`, `DSCB-L1-REQ-006` |
| `HREQ-SC-009` | SBOM license metadata | `L2` | L2 → L3 | `third_party_components` | `evidence` | `gap` | - |
| `HREQ-SC-010` | Component license compliance | `L2` | L2 → L3 | `third_party_components` | `devsecops_baseline` | `gap` | - |
| `HREQ-TEST-001` | Test strategy and acceptance | `L1` | L1 → L2 → L3 | `all_software` | `devsecops_baseline` | `partial` | `DSCB-L1-REQ-001`, `RG-RELEASE-READY` |
| `HREQ-TEST-002` | Functional, non-functional, and regression testing | `L1` | L1 → L2 → L3 | `all_software` | `devsecops_baseline` | `partial` | `DSCB-L1-REQ-001` |
| `HREQ-TEST-003` | Security requirements verification | `L1` | L1 → L2 → L3 | `risk_based` | `architecture` | `partial` | `S5`, `P8`, `RG-RELEASE-READY` |
| `HREQ-TEST-004` | Vulnerability testing | `L1` | L1 → L2 → L3 | `all_software` | `devsecops_baseline` | `covered` | `DSCB-L1-REQ-009`, `DSCB-L1-REQ-010` |
| `HREQ-TEST-005` | Penetration testing | `L2` | L2 → L3 | `high_risk_or_exposed_software` | `product_security` | `partial` | `S5`, `P8` |
| `HREQ-TEST-006` | Independent and protected testing | `L2` | L2 → L3 | `risk_based` | `product_security` | `gap` | - |
| `HREQ-OPS-001` | Security release gates | `L1` | L1 → L2 → L3 | `releasable_artifacts` | `devsecops_baseline` | `covered` | `DSCB-L1-REQ-013`, `DSCB-L1-REQ-014`, `DSCB-L2-REQ-011`, `DSCB-L2-REQ-012` |
| `HREQ-OPS-002` | Vulnerability triage and remediation | `L1` | L1 → L2 → L3 | `all_software` | `operations` | `partial` | `DSCB-L1-REQ-010`, `DSCB-GOV-REQ-003` |
| `HREQ-OPS-003` | Security update management | `L2` | L2 → L3 | `maintained_software` | `operations` | `gap` | - |
| `HREQ-OPS-004` | Security monitoring and alerting | `L2` | L2 → L3 | `operational_software` | `operations` | `partial` | `DSCB-L2-REQ-013`, `DSCB-L2-REQ-014`, `P11` |
| `HREQ-OPS-005` | Deployment and configuration verification | `L2` | L2 → L3 | `deployed_software` | `platform` | `partial` | `DSCB-L2-REQ-002`, `DSCB-L2-REQ-009` |
| `HREQ-OPS-006` | Secure operation guidance | `L1` | L1 → L2 → L3 | `distributed_or_operated_software` | `product_security` | `partial` | `P1`, `RG-OPERATION-READY` |
| `HREQ-OPS-007` | Secure decommissioning and disposal | `L1` | L1 → L2 → L3 | `all_software` | `product_security` | `gap` | - |
| `HREQ-OPS-008` | Product security response and health review | `L2` | L2 → L3 | `maintained_software` | `operations` | `gap` | - |

## Assignment Rationales

- `HREQ-GOV-001` **Secure development lifecycle** — Lifecycle governance sets the operating boundary for every adopted maturity level. Review: `human_review_required`.
- `HREQ-GOV-002` **Risk-based applicability** — Applicability determines which product, risk, and maturity obligations apply. Review: `human_review_required`.
- `HREQ-GOV-003` **Roles and competence** — Roles, competence, and reviewer independence are cross-level governance duties. Review: `human_review_required`.
- `HREQ-GOV-004` **Controlled security documentation** — Controlled documentation and evidence governance support all maturity levels. Review: `human_review_required`.
- `HREQ-RISK-001` **Asset and threat identification** — Basic asset and threat identification is foundational when the risk-based applicability rule is triggered. Review: `human_review_required`.
- `HREQ-RISK-002` **Threat modeling** — Maintained threat models require a managed design and review capability. Review: `human_review_required`.
- `HREQ-RISK-003` **Risk treatment and reassessment** — Risk treatment and reassessment require managed ownership, verification, and change triggers. Review: `human_review_required`.
- `HREQ-RISK-004` **Security architecture review** — Formal security architecture review is a managed assurance capability enhanced at L3. Review: `human_review_required`.
- `HREQ-APP-001` **Authentication and authorization** — Authentication and authorization are foundational for software that exposes identities or protected functions. Review: `human_review_required`.
- `HREQ-APP-002` **Session security** — Session protection is a foundational requirement whenever session capability exists. Review: `human_review_required`.
- `HREQ-APP-003` **Data and cryptographic protection** — Sensitive-data protection begins at L1 and gains centrally managed cryptographic assurance at higher levels. Review: `human_review_required`.
- `HREQ-APP-004` **Input validation and business logic** — Input, output, and business-rule validation are foundational for software that processes untrusted input. Review: `human_review_required`.
- `HREQ-APP-005` **Secure file handling** — Safe file handling is foundational whenever file-processing capability exists. Review: `human_review_required`.
- `HREQ-APP-006` **Application logging and error handling** — Secure error handling and security-relevant application logging start at L1 and integrate with managed monitoring at L2. Review: `human_review_required`.
- `HREQ-APP-007` **Secure defaults and hardening** — Secure defaults are foundational while centrally managed hardening and verification mature at L2 and L3. Review: `human_review_required`.
- `HREQ-DEV-001` **Source control and integrity** — Existing L1 controls already require approved version control, attributable history, and protected branches. Review: `human_review_required`.
- `HREQ-DEV-002` **Secure coding practices** — Secure coding practices are an existing foundational L1 control objective. Review: `human_review_required`.
- `HREQ-DEV-003` **Code and implementation review** — Basic code review and automated analysis extend the current L1 secure-coding objective. Review: `human_review_required`.
- `HREQ-DEV-004` **Secure development environments** — Existing L2 controls require centrally managed and hardened development environments. Review: `human_review_required`.
- `HREQ-DEV-005` **External component and supplier assurance** — Approved dependency sources start at L2 and verifiable supplier provenance strengthens at L3. Review: `human_review_required`.
- `HREQ-SC-001` **Controlled build execution** — Controlled automated builds and identifiable outputs are existing L1 objectives. Review: `human_review_required`.
- `HREQ-SC-002` **Reproducible and isolated builds** — Reproducible, isolated, and recreated build environments are existing high-assurance L3 objectives. Review: `human_review_required`.
- `HREQ-SC-003` **Artifact identity and integrity** — Artifact identity and cryptographic integrity metadata are existing L1 objectives. Review: `human_review_required`.
- `HREQ-SC-004` **Artifact signing and key protection** — Artifact signing and protected keys start at L2; enterprise signing and central key management are L3 enhancements. Review: `human_review_required`.
- `HREQ-SC-005` **Trusted dependency sources and provenance** — Approved dependency sources are L2 objectives and verifiable provenance is an L3 enhancement. Review: `human_review_required`.
- `HREQ-SC-006` **SBOM generation** — Dependency inventory and SBOM generation are existing L1 objectives. Review: `human_review_required`.
- `HREQ-SC-007` **SBOM component identity and relationships** — Detailed SBOM identity and relationship validation requires managed evidence semantics beyond basic L1 generation. Review: `human_review_required`.
- `HREQ-SC-008` **SBOM integrity and source metadata** — Component-level integrity and source metadata require managed evidence validation and stronger L3 provenance. Review: `human_review_required`.
- `HREQ-SC-009` **SBOM license metadata** — Standardized license metadata is a managed supply-chain evidence capability. Review: `human_review_required`.
- `HREQ-SC-010` **Component license compliance** — Component license compliance requires managed policy, review, and evidence rather than basic inventory alone. Review: `human_review_required`.
- `HREQ-TEST-001` **Test strategy and acceptance** — A defined test strategy and acceptance evidence are foundational release inputs. Review: `human_review_required`.
- `HREQ-TEST-002` **Functional, non-functional, and regression testing** — Functional and regression verification are foundational, with broader automated assurance at higher levels. Review: `human_review_required`.
- `HREQ-TEST-003` **Security requirements verification** — Applicable security requirements require verification from L1, with stronger traceability and evidence at higher levels. Review: `human_review_required`.
- `HREQ-TEST-004` **Vulnerability testing** — Automated vulnerability testing and release evaluation are existing L1 objectives. Review: `human_review_required`.
- `HREQ-TEST-005` **Penetration testing** — Penetration testing requires managed scope and independence for exposed or high-risk software. Review: `human_review_required`.
- `HREQ-TEST-006` **Independent and protected testing** — Independent testing and protected test data require managed assurance, strengthened for L3 products. Review: `human_review_required`.
- `HREQ-OPS-001` **Security release gates** — Release authorization is foundational; enforceable security thresholds strengthen at L2. Review: `human_review_required`.
- `HREQ-OPS-002` **Vulnerability triage and remediation** — Vulnerabilities require release evaluation at L1 and managed remediation evidence at higher levels. Review: `human_review_required`.
- `HREQ-OPS-003` **Security update management** — Security update management requires a managed lifecycle, response ownership, and delivery capability. Review: `human_review_required`.
- `HREQ-OPS-004` **Security monitoring and alerting** — Central security-event generation and forwarding are existing L2 monitoring objectives. Review: `human_review_required`.
- `HREQ-OPS-005` **Deployment and configuration verification** — Managed deployment and version-controlled configuration align with existing L2 platform objectives. Review: `human_review_required`.
- `HREQ-OPS-006` **Secure operation guidance** — Applicable software requires foundational secure installation and operation guidance. Review: `human_review_required`.
- `HREQ-OPS-007` **Secure decommissioning and disposal** — Every maintained lifecycle needs a foundational retirement and secure-disposal outcome. Review: `human_review_required`.
- `HREQ-OPS-008` **Product security response and health review** — Product security response and periodic health review require managed ownership and operational capability. Review: `human_review_required`.

## Human Review Checklist

- [ ] Confirm the minimum level for every requirement.
- [ ] Confirm that risk- and capability-based applicability remains independent of maturity.
- [ ] Confirm GOV as the cross-level overlay for lifecycle, applicability, roles, and controlled documentation.
- [ ] Confirm routing to Governance, DevSecOps Baseline, Architecture, Product Security, Platform, Evidence, or Operations.
- [ ] Confirm whether partial and gap items require new controls or only stronger evidence and verification.
- [ ] Record any authorized derivation in a separate governance change and release decision.

## Decision Boundary

Every assignment requires human review. This candidate report does not authorize changes to runtime governance or released baselines.
