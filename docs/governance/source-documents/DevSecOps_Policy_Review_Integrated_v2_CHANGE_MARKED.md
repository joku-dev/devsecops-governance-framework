| Policy |
| --- |
|  **DevSecOps Policy – Software Defined Defence (SDD)**  |

Contents

1	General	4

1.1	Aim and Purpose	4

1.2	Responsibilities	4

1.3	Applicable Documents	5

1.4	Referenced Documents	5

1.5	Definition of Terms	5

1.6	Abbreviations	5

2	Scope	6

3	Fundamental Principles (Mandatory)	7

4	Mandatory Minimum Requirements (Normative)	8

4.1	DevSecOps Control Stages	8

4.2	DevSecOps Controls (Outcome-Based)	8

4.3	Evidence	9

4.4	Maturity & Applicability	9

4.5	Governance & Responsibilities	10

5	Deviations (Waivers)	10

6	Compliance, Reporting, and Enforcement	10

7	Entry into Force	11

General

Aim and Purpose

This policy defines the mandatory DevSecOps foundations for the development, operation, and evolution of software-enabled capabilities in the context of Software Defined Defence within the Group.

It establishes DevSecOps as an enabling capability for agile and iterative engineering by making cybersecurity, quality, traceability, and compliance evidence executable, repeatable, and auditable. Product and project deliverables remain governed by the applicable CMS and product lifecycle processes; this policy defines how DevSecOps supports those processes through approved tooling, controls, and evidence.

Responsibilities

**Chief Digitalisation Officer (CDO)**

The CDO is accountable for:

Enterprise-wide implementation of DevSecOps.

Establishment and funding of the DevSecOps platform capability.

Alignment of DevSecOps capabilities with applicable safety lifecycle requirements and evidence needs.

Reporting adoption and maturity status to Executive Management.

**Cyber Security Function (CSCSO)**

The Cyber Security Function is accountable for cybersecurity governance within its assigned organizational scope, including product, project, platform, and enterprise cybersecurity responsibilities where applicable:

Definition of mandatory cybersecurity control baselines.

Security domain classification and cybersecurity applicability criteria.

Cybersecurity risk acceptance within delegated authority.

Approval of high-risk cybersecurity deviations.

Audit rights regarding cybersecurity compliance.

**Safety Authority**

The responsible Safety Authority is accountable for the safety interface to DevSecOps and for:

Definition of safety-related lifecycle and evidence requirements that must be supported by DevSecOps where applicable.

Approval of safety-critical deviations within delegated authority.

Oversight that DevSecOps automation and evidence do not conflict with applicable safety processes, approvals, or certification constraints.

**DevSecOps Governance Board (as defined in the DevSecOps Directive)**

The DevSecOps Governance Board shall:

Define and maintain mandatory DevSecOps rules and control baselines.

Define maturity targets and applicability criteria.

Evaluate and approve waivers within delegated authority.

Monitor enterprise-wide compliance and maturity progress.

**Divisions, Programs, and Engineering Organizations**

Divisions, programs, and responsible engineering organizations are accountable for:

Applying approved DevSecOps requirements, platforms, and control rules within their delegated scope.

Using approved DevSecOps platforms or formally approved equivalents that conform to defined requirements.

Achieving and maintaining the defined DevSecOps maturity level applicable to their scope.

Reporting compliance status as required.

Failure to comply constitutes a policy violation.

Applicable Documents

The following publications form a part of this document to the extent specified herein. In case no version is quoted for a document the current version is deemed to apply. When a version is quoted, this version shall be used.

[AD01] NA

[AD02] TBD

Referenced Documents

The following publications contain further input and background information relating to the subject addressed. In case no version is quoted for a document the current version is deemed to apply. When a version is quoted, this version shall be used.

[RD01] DevSecOps Directive

[RD02] DevSecOps Control Baseline Standard (to be established)

[RD03] DevSecOps Platform Reference Architecture Standard (in progress)

[RD04] Security Certification Guideline

Definition of Terms

The terms and definitions established for the Business Management System are listed in the common BMS Glossary. The following terms are specific to this document.

| **Term** | **Explanation** |
| --- | --- |
| Lifecycle Phase | A governance-level segment of the product or project lifecycle as defined by applicable CMS, program, or certification processes. Lifecycle phases are not identical to DevSecOps control stages or CI/CD pipeline stages. |
| Phase Gate | A formal management decision point between lifecycle phases. Phase gates review accumulated deliverables and evidence and may approve, reject, or conditionally approve continuation. |
| DevSecOps Control Stage | A technical and operational segment of the DevSecOps toolchain used to produce, verify, release, deploy, monitor, or evolve software and documentation artifacts with defined controls and evidence. |
| Pipeline Stage | An execution step within a CI/CD or software factory workflow. Pipeline stages may execute automatically or be invoked manually in a controlled manner. |
| Policy Gate | A rule-based verification or enforcement point within a control or pipeline stage. A policy gate evaluates predefined compliance criteria and may block continuation or release until the criteria are met or an approved waiver exists. |
| Evidence | Human-readable or machine-readable proof that a control has been executed, reviewed, approved, or waived as required. |
| Waiver | A formally approved, time-limited deviation from a mandatory requirement, including risk classification, compensating controls, owner, and expiry date. |

Abbreviations

| **Abbreviation** | **Term** |
| --- | --- |
| CDO | Chief Digitalisation Officer |
| CI/CD | Continuous Integration / Continuous Delivery or Deployment |
| CSCSO | Chief Security / Cyber Security Function as assigned by organizational governance |
| DAST | Dynamic Application Security Testing |
| FOSS | Free and Open Source Software |
| CMS | COMPANY Management System |
| IM | Information Management |
| KPI | Key Performance Indicator |
| SBOM | Software Bill of Materials |
| SAST | Static Application Security Testing |
| SCA | Software Composition Analysis |
| SDD | Software Defined Defence |
| SLA | Service Level Agreement |
| VDD | Version Description Document |

Scope

This Policy applies to:

DevSecOps capabilities, toolchains, pipelines, automation, and evidence generation supporting SDD-relevant systems, products, and platforms.

All organizational units that develop, integrate, verify, release, deploy, operate, or maintain SDD-relevant software-enabled capabilities.

All relevant development, integration, verification, release, deployment, operation, maintenance, and evolution activities where DevSecOps controls or evidence are applicable.

Internally developed and externally sourced software where integration into company systems requires DevSecOps-controlled build, verification, release, or evidence generation.

All security domains, including classified and non-classified environments.

IM developments with public customer-facing properties where cybersecurity, traceability, release, or operational evidence is required.

Product and project outcomes remain subject to the applicable CMS, customer, regulatory, safety, security, and certification processes. DevSecOps requirements apply to the engineering automation, control, evidence, and release-support layer that enables those outcomes.

The following cases may be exempted or handled with a reduced DevSecOps control set, subject to risk-based justification:

Non-security-relevant office IT applications without SDD relevance.

Software developed only for showcases, proof of concepts, or non-operational demonstrations.

Early exploration activities before operational, contractual, or release-relevant use is intended.

One-off or exceptional activities for which automation would be economically disproportionate, provided the mandatory control objective is fulfilled by a controlled manual procedure.

Any exemption or reduced control set shall be formally justified and approved via the defined waiver process unless explicitly covered by a pre-approved applicability rule.

Fundamental Principles (Mandatory)

The implementation of DevSecOps within the Group shall comply with the following binding principles. These principles are intended to enable fast, iterative, and evidence-based software engineering without bypassing applicable CMS, security, safety, or product lifecycle obligations.

**Security by Design and by Default**

Cybersecurity requirements shall be defined, implemented, verified, and evidenced across architecture, development, verification, release, and operations. Automated enforcement shall be used where appropriate, but the underlying control objective and verification method shall remain understandable and executable independently of a specific CI/CD implementation.

**Safety Interface**

Where applicable, DevSecOps shall support safety-related requirements, verification activities, and evidence needs without replacing the authority, methods, or approvals of the applicable safety lifecycle. Security and safety conflicts shall be identified, assessed, and resolved through the competent safety and cybersecurity authorities.

**Manual Executability before Automation**

Mandatory controls shall be defined so that they can be executed manually in a controlled and repeatable manner where necessary. Automation shall be implemented after the control objective, input, output, evidence, and decision criteria are understood.

**Automation First where Feasible and Proportionate**

Security, safety, quality, and compliance controls shall be automated where technically feasible, economically proportionate, and justified by risk, repetition, auditability, or cycle-time reduction. Automation shall not make simple or exceptional activities dependent on a CI/CD pipeline when manual execution is justified and controlled. Those Automations should follow Policy-as-Code principles where this improves consistency, reviewability, traceability, and evidence generation

**Documentation as an Engineering Artifact**

Documentation should follow Doc-as-Code principles where this improves consistency, reviewability, traceability, and evidence generation. Documentation remains subject to the applicable BMS/CMS document-control rules.

**Lifecycle Ownership**

Responsible teams shall maintain accountability for the DevSecOps activities and evidence within their scope, from design and implementation through release, operation, monitoring, and controlled evolution.

**Federated Execution under Central Governance**

Implementation may be decentralized across divisions, programs, and engineering organizations but shall operate within centrally defined governance, rules, and control baselines.

**Evidence-Based Compliance**

Compliance evidence should be generated automatically from approved development and operational pipelines where feasible and retained in a controlled evidence repository or equivalent system of record.

**Domain-Aware Application**

DevSecOps implementation shall consider security domain, system criticality, operational context, and applicable customer or regulatory constraints while maintaining mandatory baseline controls.

Mandatory Minimum Requirements (Normative)

For all in-scope DevSecOps implementations supporting SDD-relevant software-enabled capabilities, the following minimum requirements shall be met. These requirements address the DevSecOps capability, its controls, and its evidence; they do not replace project, product, certification, or CMS lifecycle requirements.

DevSecOps Control Stages

For each DevSecOps control stage, defined objectives, controls, and evidence shall be implemented in accordance with applicable governance rules. DevSecOps control stages are technical and operational stages of the engineering toolchain; they are not identical to CMS lifecycle phases or formal project phase gates.

Indicative control-stage sequence: Design & Plan -> Code -> Build -> Test & Verify -> Package & Release -> Deploy & Operate -> Evolve

| **Control Stage** | **Mandatory Objective** |
| --- | --- |
| Design & Plan | Security, safety-interface, architecture, compliance, and traceability requirements are defined, reviewed, and linked to applicable control obligations. |
| Code | Known security flaws are avoided through approved credential handling, secure coding practices, review rules, and controlled source management. |
| Build | The software supply chain is protected; builds are reproducible or otherwise controlled according to the applicable release model. |
| Test & Verify | Vulnerabilities, dependency risks, quality findings, and safety impacts are identified, assessed, treated, and evidenced. SAST, SCA, DAST, test automation, and equivalent verification methods shall be applied where applicable. |
| Package & Release | Artifact identity, integrity, traceability, and release authorization are assured. Cryptographic signing shall be applied where required by classification, criticality, release model, customer obligation, or applicable standard. |
| Deploy & Operate | Deployment records, runtime version information, monitoring inputs, vulnerability monitoring, dependency monitoring, and operational traceability are maintained where applicable. |
| Evolve | Changes, patches, updates, vulnerability treatment, and lifecycle decisions are controlled, traceable, and auditable. |

DevSecOps Controls (Outcome-Based)

The responsible engineering organization or program, as applicable, shall ensure that:

Credentials, secrets, and access tokens are handled according to approved credential-handling rules, including prevention of unauthorized disclosure in source code, build logs, artifacts, and configuration.

Dependencies and third-party software components are transparent, verifiable, and managed in alignment with the applicable FOSS, supplier-control, and software supply chain processes.

Vulnerabilities are identified, assessed, prioritized, treated, and tracked according to defined SLAs and documented risk acceptance rules.

Design, architecture, requirements, source code, reviews, builds, tests, released artifacts, and deployment records are traceable to the extent required by the applicable project, product, and regulatory context.

Releasable artifacts are uniquely identifiable and integrity-protected; cryptographic signing shall be applied where required by classification, criticality, release model, customer obligation, or applicable standard.

Release approvals and relevant automated or manual gate results are formally documented and auditable.

Subordinate directives, standards, process descriptions, and platform rules shall derive detailed implementation requirements from this policy and from applicable cybersecurity, safety, quality, FOSS, supplier, and certification obligations.

Evidence

For mandatory controls, evidence shall be available and retained. Machine-generated evidence shall be preferred where technically and economically feasible, including:

Design, architecture, and requirements traceability evidence where applicable.

Security scan reports, including vulnerability treatment status, remediation decisions, accepted risks, and SLA evidence where applicable.

Software Bill of Materials (SBOM) and dependency transparency evidence where applicable.

Artifact identification, integrity, hash, and signature evidence where required.

Traceability records linking requirements, source changes, reviews, builds, tests, releases, deployments, and operations where applicable.

Approval, review, audit, and waiver logs.

Manual execution and manual evidence are permitted where automation is technically infeasible, economically disproportionate, regulatorily constrained, or not justified for one-off activities. Manual execution shall be controlled, repeatable where needed, and formally justified when used as an alternative to mandatory automation.

Maturity & Applicability

The Group defines DevSecOps maturity levels based on:

Security domain

System criticality

Operational context

Required evidence and auditability

Economic proportionality and lifecycle phase

Responsible organizations shall achieve the defined maturity level applicable to their scope or obtain formally approved waivers.

| **Dimension** | **Level 1 (Initial)** | **Level 2 (Repeatable)** | **Level 3 (Defined)** |
| --- | --- | --- | --- |
| Culture | Basic security awareness exists; development, operations, and governance collaboration is ad hoc. | Initial collaboration between teams exists; security and compliance responsibilities are partially recognized. | Security, quality, and compliance culture is actively promoted; teams share responsibility for secure and auditable delivery. |
| Processes | Control execution is largely manual or inconsistent; evidence is collected case by case. | Basic DevSecOps processes and review routines exist and are used repeatedly. | DevSecOps practices are integrated into the development, release, and operations process with documented control and evidence rules. |
| Automation | Manual checks dominate; automation is limited and not consistently connected to evidence. | Selected controls are automated and partially integrated into CI/CD or software factory workflows. | Mandatory controls are automated where feasible; policy gates and evidence generation are integrated into approved pipelines. |
| Competence | Security and DevSecOps competence is limited and depends on individual experts. | Initial training and role awareness exist for relevant teams. | Relevant team members are trained in applicable DevSecOps, security, evidence, and toolchain practices; role-specific competence is maintained. |

Governance & Responsibilities

Group-wide DevSecOps governance is the responsibility of the corporate Software Industrialisation and DevSecOps Lead in coordination with the DevSecOps Governance Board, Architecture Board or Design Authority, Cyber Security Function, Safety Authority, and affected divisions.

The competent governance bodies decide or recommend, according to their delegated authority, on:

- Mandatory DevSecOps rules and control baselines
- DevSecOps maturity targets and applicability criteria

approval-required deviations and waivers

platform conformance and authorized use where applicable

- Divisions and responsible engineering organizations are responsible for:

providing or using DevSecOps platforms that conform to defined requirements

enabling programs and engineering teams to apply the approved DevSecOps rules

reporting maturity, compliance, waiver, and evidence status to corporate governance

supporting internal and external audits of DevSecOps maturity and control effectiveness

Deviations (Waivers)

Deviations from mandatory requirements:

Shall be permitted only if technically, regulatorily, economically, or operationally justified.

Shall be formally requested.

Shall include risk classification, impact assessment, compensating controls, and accountable owner.

Shall be time-limited.

Shall be recorded in a centralized waiver registry.

Shall be re-evaluated prior to expiry.

High-risk cybersecurity deviations require approval by the competent Cyber Security Function. Safety-critical deviations require approval of the responsible Safety Authority.

Permanent waivers are prohibited.

Unapproved deviations constitute a policy violation.

Compliance, Reporting, and Enforcement

Compliance with this Policy is mandatory for all in-scope DevSecOps implementations.

Compliance shall be:

Verified as part of applicable program, project, or release approvals where DevSecOps-controlled evidence is required.

Reviewed in architecture decisions where toolchain, pipeline, deployment, security domain, or evidence architecture is affected.

Reviewed as part of applicable COMPANY process reviews, including PDR, CDR, release reviews, or equivalent agile milestones where relevant.

Subject to internal and external audits by the competent audit, cybersecurity, safety, quality, or governance functions.

Reported periodically to the responsible corporate governance bodies.

Material or repeated violations may result in escalation to Executive Management and corrective actions.

Entry into Force

This Policy enters into force upon formal authorization and remains valid until superseded or revoked.
