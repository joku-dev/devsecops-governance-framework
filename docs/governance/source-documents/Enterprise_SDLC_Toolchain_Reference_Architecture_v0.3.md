| Enterprise Reference Architecture |
| --- |
| Enterprise Software Development Lifecycle Toolchain Reference Architecture |

*Aligned controls, platform levels and lifecycle evidence for federated software delivery*

Table of Contents



Source documents and precedence	5

Executive summary	6

1 Purpose and document authority	7

2 Scope and architecture boundary	7

3 Conformance and deployment model	7

3.1 Assurance and technical minimum	7

3.2 Independent deployment context	8

4 Architecture principles	9

5 Enterprise capability model	9

5.1 Capability catalogue	9

6 Logical architecture	10

6.1 Control plane and execution plane	11

6.2 Product architecture and industrialisation interface	11

7 Lifecycle integration P0 to P9	11

8 Information and traceability architecture	12

8.1 Canonical relationship	13

9 Integration architecture	13

10 Security and trust architecture	14

10.1 Identity and secrets	14

10.2 Build and trust zones	14

10.3 Monitoring and runtime integrity	14

11 Software supply chain and release architecture	14

12 Governance and evidence architecture	15

12.1 Evidence record and gate decision	16

12.2 Evidence status across P2 to P9	16

13 Deployment patterns and domain variants	16

14 Roles and operating responsibilities	16

15 Assessment and transition	17

15.1 Assessment criteria	17

15.2 Staged adoption	17

16 Open actions and decisions	18

17 Proposed architecture decision	18

Annex A Control to capability traceability	20

L1 enterprise baseline	20

L2 secure DevSecOps	21

L3 trusted supply chain	21

Governance requirements	22

Annex B Evidence contract	23

Gate decision record	23

Annex C Conformance assessment checklist	24

Source documents and precedence

| **Source** | **Authority for this architecture** |
| --- | --- |
| **DevSecOps Control Baseline Standard aligned with Platform Levels** | Control obligations, assurance levels L1–L3, required evidence and DSCB identifiers |
| **DevSecOps Platform Reference Architecture Standard aligned with Control Baseline** | PRA-Level minimum technical capabilities, eight layers and domain variants |
| **Software Development Process DevSecOps V5 Activity RACI Artifacts** | P0–P9 phase definitions, P6a, decisions, activity RACI and output artifacts |
| **Earlier enterprise toolchain architecture draft** | Previous architecture draft; retained where consistent with the three updated sources |

Confirm source revisions, precedence, ownership and approval before baselining (A01).

Executive summary

The enterprise needs one logical toolchain contract linking mandatory controls, lifecycle activities, technical platform services and evidence. The updated Control Baseline and Platform Reference Architecture now align L1 with PRA-Level 1, L2 with PRA-Level 2, and L3 with PRA-Level 3. The Software Development Process defines the authoritative phase sequence, including pre-production P2, formalisation at P2 to P3, verification dry run P6a, release P8 and in-service P9.

This architecture retains a vendor-neutral C1–C7 capability model. Its primary integration chain is control requirement to logical capability to platform service to lifecycle activity to evidence to decision. ALM and product architecture systems remain authoritative for their respective objects and integrate with the DevSecOps Platform through versioned contracts.

A programme selects its applicable Control Baseline during P0. The minimum PRA-Level follows from that selection. Central, federated, isolated and air-gapped deployment patterns are an independent choice and cannot lower mandatory controls. Additional product, safety, security-domain and contractual obligations may apply.

This architecture resolves the obsolete A–D profile model and the earlier P-phase mismatch. It does not silently resolve wording or ownership issues in the source documents. Section 16 records those matters as actions, with proposed decision owners and closure evidence.

1 Purpose and document authority

This reference architecture specifies the logical capabilities, information objects, integration contracts, trust boundaries and evidence relationships required to support software development and in-service maintenance. It provides a basis for platform roadmaps, programme toolchain design, onboarding, architecture review and conformance assessment.

The Control Baseline owns mandatory outcomes and required evidence. The Software Development Process owns activities, gate outcomes and activity-level RACI. The Platform Reference Architecture owns technical minimums. This document owns the enterprise-wide capability and integration contract. Where a source conflict exists, the accountable source owner resolves it; this document records the dependency in Section 16 rather than changing another document by implication.

**ARCH-001**Each enterprise control used by a programme SHALL have a traceable logical capability, a platform means, an execution activity, an evidence record and a decision or assessment path.

**ARCH-002**The implementation SHALL preserve the authoritative identity and revision of each source requirement and SHALL NOT duplicate a divergent normative statement in a local toolchain catalogue.

2 Scope and architecture boundary

The architecture covers software products, embedded and system software, third-party and open-source components, their delivery pipelines and relevant operational feedback. It spans P0 applicability through P9 in-service change. Internal office IT and purely experimental prototypes are outside the Control Baseline scope unless designated; the programme shall record the applicability decision.

| **Architecture concern** | **Within this document** | **Authoritative elsewhere** |
| --- | --- | --- |
| **Controls** | Links and technical means | Control Baseline defines obligation, level and evidence |
| **Process** | Information flows and integration points | SDLC defines P0–P9 activities, outputs, RACI and gates |
| **Platform** | Logical capability contract and interfaces | PRA defines minimum technical services and platform levels |
| **Product architecture** | Industrialisation constraints and product interfaces | Product design authority owns product design and safety case |

Tool brands are implementation choices. A central service, division service or programme service may satisfy a logical capability only if the required controls, interfaces, data protection and evidence remain effective.

3 Conformance and deployment model

3.1 Assurance and technical minimum

| **Programme control selection** | **Minimum platform** | **Cumulative rule** |
| --- | --- | --- |
| **L1 enterprise baseline** | PRA-Level 1 | All applicable L1 and governance controls |
| **L2 secure DevSecOps** | PRA-Level 2 | L1 plus L2 and governance controls |
| **L3 trusted supply chain** | PRA-Level 3 | L1 plus L2 plus L3 and governance controls |

The PRA-Level is a technical minimum derived from the selected Control Baseline, not an optional maturity score. The selected platform instance may provide a higher PRA-Level. A lower level requires formal treatment of the gap and cannot be declared conformant merely by choosing a different deployment variant.

3.2 Independent deployment context

The programme records two independent dimensions at P0: its cumulative assurance level L1–L3 and its deployment pattern. Central, federated, programme-isolated and air-gapped patterns are described in Section 13. Classified or restricted operation adds domain constraints while retaining the minimum capabilities of the required PRA-Level.

*Figure 1. Assurance level and deployment pattern are selected independently at P0; each instance is assessed against its derived minimum.*

**CONF-001**At P0, the programme SHALL record applicability, selected L1–L3 baseline, derived PRA-Level, deployment pattern, domain constraints, toolchain capability assessment and approving authority.

**CONF-002**A conformance assessment SHALL identify the evaluated platform instance, versions, supported programmes, applicable controls, exceptions, evidence and assessment date.

**CONF-003**A change to classification, criticality, customer obligations, connectivity or trust infrastructure SHALL trigger reassessment of applicability and affected architecture contracts.

The previous A–D profiles are withdrawn from this proposal. A–C could understate the mandatory L1 baseline and D combined high assurance with disconnected deployment. Migration of older profile records is an explicit action (A03).

4 Architecture principles

| **Principle** | **Architectural consequence** |
| --- | --- |
| **Capability before product** | Describe stable enterprise outcomes and interfaces before selecting tools. |
| **Authoritative source** | One system of record owns each object and its approved baseline. |
| **Evidence by execution** | Pipelines and lifecycle tools produce verifiable evidence as work occurs. |
| **Immutable subject** | Gates evaluate exact revisions and digests; promotion does not rebuild a released artifact. |
| **Policy authority separate from execution** | Approved rules and release authority are distinguishable from tools that run tasks. |
| **Federation with common contracts** | Domain toolchains may differ, but identities, schemas, controls and evidence remain interoperable. |
| **Domain-aware trust** | Cross-domain or disconnected paths explicitly manage import, trust roots and evidence export. |

5 Enterprise capability model

C1–C7 define the logical enterprise contract. A product may implement more than one capability; a capability may be delivered by several controlled services. Every capability has an accountable owner, measurable outcome and interface to its authoritative objects.

| **Group** | **Capability domain** | **Primary outcome and PRA relationship** |
| --- | --- | --- |
| **C1** | Engineering experience | Controlled workspace, portal, golden paths and local checks; Developer Workspace layer. |
| **C2** | Lifecycle management | Requirements, architecture, planning and configuration links; primarily external ALM systems of record, integrated with Evidence and Traceability. |
| **C3** | Software engineering | Protected source, controlled builds, tests and dependencies; Source Control and Pipeline Execution. |
| **C4** | Assurance | Security, quality, safety and policy results; Security and Compliance Control. |
| **C5** | Software supply chain | Immutable artifacts, SBOM, signing and provenance; Artifact and Dependency Management. |
| **C6** | Release and operations | Approved release, deployment, observability and in-service response; Deployment and Monitoring. |
| **C7** | Governance and evidence | Identity, policy, traceability, decisions and reporting; Evidence and Traceability plus cross-cutting services. |

5.1 Capability catalogue

| **Group** | **Capability IDs and descriptions** |
| --- | --- |
| **C1** | C1.1 workspace; C1.2 developer portal; C1.3 golden paths; C1.4 local assurance |
| **C2** | C2.1 requirements and traceability; C2.2 architecture and modelling; C2.3 planning and work; C2.4 configuration and change |
| **C3** | C3.1 source control; C3.2 build orchestration; C3.3 test automation; C3.4 dependency management |
| **C4** | C4.1 code and composition analysis; C4.2 dynamic and interface testing; C4.3 infrastructure and container assurance; C4.4 policy evaluation |
| **C5** | C5.1 artifact repository; C5.2 bill of materials; C5.3 signing and verification; C5.4 provenance and promotion |
| **C6** | C6.1 release orchestration; C6.2 deployment and environment; C6.3 observability; C6.4 in-service response |
| **C7** | C7.1 identity; C7.2 control and policy; C7.3 evidence and traceability; C7.4 assurance reporting |

**CAP-001**Each implemented capability SHALL declare its owner, supported PRA-Level, interface contract, trust boundary, service dependencies and evidence output.

**CAP-002**A programme SHALL establish which enterprise, division, programme or external ALM service is authoritative for each required lifecycle object.

6 Logical architecture

The logical model has six delivery domains and a cross-cutting governance and evidence plane. C2 lifecycle management spans product and process systems of record; it is not implied to be a ninth DevSecOps Platform layer. The eight PRA layers provide technical implementation services and may integrate to ALM and product tools outside the platform boundary.

*Figure 2. External C2 lifecycle systems retain object ownership while eight PRA layers deliver the DevSecOps Platform and C7 evidence contract.*

| **Logical area** | **Inputs** | **Outputs and consumers** |
| --- | --- | --- |
| **C1 engineering experience** | Identity, approved templates, programme context | Controlled development path consumed by product teams |
| **C2 lifecycle management** | Product intent, risk, change and requirements | Approved baselines and relationships consumed by C3–C7 |
| **C3 engineering execution** | Approved source, configuration and dependencies | Build and test results, immutable outputs |
| **C4 assurance** | Source, dependencies, build, environment | Findings, policy results and disposition |
| **C5 supply chain** | Approved outputs and metadata | Stored artifacts, SBOM, provenance and signatures |
| **C6 release and operations** | Approved artifact and gate decision | Deployment state, telemetry and in-service triggers |
| **C7 governance and evidence** | Controls, identities and all lifecycle records | Evidence graph, waivers, conformance and gate decisions |

6.1 Control plane and execution plane

The control plane manages approved controls, level assignment, identities, policies, gate criteria, waiver status and decisions. The execution plane runs development, build, test, scan, release, deployment and monitoring tasks. A decision record binds rule version, subject digest, evaluated evidence and authority to an execution result.

**ARCH-003**The toolchain SHALL keep the versioned decision context separate from the mutable systems executing a task, with independence appropriate to product risk.

6.2 Product architecture and industrialisation interface

At P4, the product architecture should demonstrate that its software components, interfaces, target environments and update model can be built, verified, packaged, signed, deployed and maintained by an approved toolchain. Product Design Authority retains design accountability; Software Industrialisation assesses the feasibility of the production and evidence path. The exact review gate and decision rights remain open (A07).

7 Lifecycle integration P0 to P9

The Software Development Process is the authoritative lifecycle. Toolchain integrations shall preserve its phase meanings, outputs, activity RACI and gate status. P2 draft results are not release evidence merely because a pipeline produced them; promotion into the formal P3–P7 lifecycle requires the P2 to P3 formalisation decision.

| **Phase** | **Toolchain contract** | **Decision or key evidence** |
| --- | --- | --- |
| **P0 Applicability** | Classify scope, assign DSCB level, derive PRA level and select deployment pattern | Applicability Assessment; Baseline Assignment Approval |
| **P1 Planning** | Record toolchain, CM/SCM, CI/CD and evidence strategy | Approved Software Planning Data and Evidence Contract |
| **P2 Pre-production** | Keep draft requirements/design/code/tests and early scans under CM | Draft links, findings and readiness assessment; no formal release |
| **P2 to P3** | Resolve draft object lineage and formalise selected baselines | Readiness and formalisation decision |
| **P3 Requirements** | Baseline approved software requirements and traceability | Requirements baseline and review record |
| **P4 Design** | Link software architecture and interface design to approved requirements | Design baseline and architecture review |
| **P5 Coding** | Protect changes and connect code/review to formal design | Source baseline, code review and static analysis |
| **P6 Integration and test** | Run controlled builds, integrate components, scan and generate SBOM | Build and test records, findings and artifact digest |
| **P6a Dry run** | Support rehearsal without substituting formal verification | Dry-run results and readiness decision |
| **P7 Verification** | Verify against baseline and compile approval evidence | Verification results, compliance matrix, findings and waiver state |
| **P8 Release and operations** | Approve immutable configuration, deploy and establish operational traceability | Release decision, artifact identity, deployment and runtime records |
| **P9 In service** | Triage CVEs/incidents/drift, manage updates and verify deployed patches | Maintenance decision, patch approval and post-deployment verification |

**LIFE-001**The toolchain SHALL preserve typed links across requirement, design, code, build, test, artifact, release, deployment, operational trigger, maintenance decision and post-deployment verification.

**LIFE-002**P2 evidence SHALL carry a draft or pre-production status; formal release gates SHALL evaluate the approved baselines and evidence state established from P3 onward.

**LIFE-003**A maintenance release SHALL inherit applicable controls and retain links to its in-service trigger, impact assessment, change classification, evidence, approval and installed version.

8 Information and traceability architecture

Each lifecycle object has one declared system of record. Other tools may cache or display it but shall retain the source identifier, revision and resolution path. A release snapshot captures the exact object versions and relationship state used for the decision.

| **Object family** | **Examples** | **Authoritative source to declare** |
| --- | --- | --- |
| **Applicability and control** | Baseline assignment, DSCB revision, waiver | Governance registry or approved ALM |
| **Product intent** | Requirement, architecture/design, risk, plan | Approved requirements and design ALM |
| **Change and source** | Change request, review, commit, source baseline | Change/CM and SCM systems |
| **Execution** | Pipeline run, test, scan, policy result | CI and specialised execution systems |
| **Supply chain** | Artifact digest, SBOM, dependency, provenance, signature | Artifact and metadata repositories |
| **Decision and operation** | Gate, release, deployment, incident, patch | Release/CM and operational systems |

**TRC-001**Every object required for a release or compliance decision SHALL have a stable, resolvable identifier and a version, baseline or digest.

**TRC-002**Relationships SHALL be typed, attributable and versioned so a released configuration can be reconstructed without relying on the latest mutable state.

**TRC-003**Evidence and object retention SHALL follow the applicable product, contractual, security and legal requirements; the schedule and cross-domain rules must be confirmed (A10).

8.1 Canonical relationship

Requirement → design → change → source → build → test and scan → artifact and SBOM → release decision → deployment → runtime version → operational trigger → maintenance decision → patch → post-deployment verification. Each edge identifies its producer, relation type, object versions and observation time.

*Figure 3. Versioned object relationships carry the P2 formalisation boundary through release, deployed state and P9 maintenance feedback.*

9 Integration architecture

Versioned APIs and events connect systems of record to systems of execution. An integration contract specifies producer and consumer, schema/version, object IDs, workload identity, authorization, errors, retries, idempotency, time source, retention, confidentiality and failure handling. A failed control or evidence integration is visible and cannot be treated as success.

| **Interface** | **Minimum exchanged content** | **Failure consequence** |
| --- | --- | --- |
| **ALM to SCM/CI** | Approved baseline, change ID, requirement and design references | Build or gate cannot claim traceability |
| **SCM/CI to evidence** | Commit, review, pipeline definition/run and immutable output digest | Evidence marked incomplete |
| **Scanner/policy to gate** | Rule version, subject, findings, threshold and decision | Fail closed or documented manual decision |
| **Artifact to deployment** | Digest, SBOM, provenance, signature and release authority | Unverified artifact is not deployed |
| **Operations to engineering** | Installed version, incident, vulnerability and drift context | P9 trigger tracked for manual triage |

**INT-001**Enterprise integrations SHALL use documented, versioned interfaces and a compatibility policy.

**INT-002**Control/evidence transfer errors SHALL be observable; gates SHALL NOT convert missing or invalid evidence into a passing result.

**INT-003**Events SHALL include event ID, producer identity, subject ID and version, schema version, event time and correlation ID.

10 Security and trust architecture

10.1 Identity and secrets

Managed human identity, role-based access, privileged MFA at L2, segregated duties and accountable workload identity apply across the toolchain. Pipeline secrets and signing keys do not belong in source, pipeline definitions, unprotected configuration or logs. The implementation obtains them from approved trust services at execution time and records rotation and revocation.

**SEC-001**Privilege to administer controls, approve releases, publish artifacts or sign software SHALL be separated according to the approved risk and role model.

**SEC-002**Pipeline credentials SHALL be scoped to the executing workload, protected from untrusted change content and revoked or rotated under a defined lifecycle.

10.2 Build and trust zones

At L3, isolated and recreated build environments and reproducible results are required by the Control Baseline. The architecture records source, dependency and build input identities, runner configuration, produced artifact digest and builder identity. Classified or air-gapped zones require controlled intake, offline verification, local trust roots and permitted evidence exchange.

**SEC-003**Trust boundary crossings SHALL identify approved import/export paths, malware and integrity checks, allowed metadata, operator authority and audit evidence.

10.3 Monitoring and runtime integrity

At L1, deployed versions and relevant security events remain traceable. L2 requires security event generation and forwarding. L3 adds runtime integrity and continuous compliance evidence. Three newer L2 entries address unified logs, health state and configuration publication, but currently use 'should'; their normative status and technical destinations are open (A02 and A06).

11 Software supply chain and release architecture

Approved source is built in controlled pipelines. Dependencies resolve from approved repositories according to level. Scans and assessments produce findings linked to the same subject. Releasable artifacts receive unique identities, integrity data and SBOMs at L1; signing and protected keys are added at L2; L3 adds deterministic rebuild, isolated execution, dependency provenance, enterprise trust and runtime verification.

*Figure 4. Trust boundaries separate engineering, build, artifact and target zones; the control and evidence planes bind the release decision.*

| **Transition** | **Required identity binding** | **Evidence** |
| --- | --- | --- |
| **Source to build** | Source baseline and build configuration | Review, pipeline run and build input manifest |
| **Build to artifact** | Output digest, dependency set and environment | Build result, scan, SBOM and provenance as applicable |
| **Artifact to release** | Same immutable digest evaluated by the gate | Waiver/finding state, signing and approval |
| **Release to deployment** | Approved digest and target configuration | Verification result and deployment record |
| **Deployment to P9** | Installed version and runtime state | Monitoring, incident and maintenance records |

**SUP-001**A release gate SHALL evaluate the exact immutable artifact version intended for deployment and retain its SBOM, integrity, scan, approval and applicable signing/provenance records.

**SUP-002**Deployment SHALL verify that the received artifact and target configuration match the approved release decision.

12 Governance and evidence architecture

Controls remain authoritative in the Control Baseline, identified by DSCB IDs. The architecture maps their outcomes to C1–C7, PRA layers, process activities and evidence. Annex A is a complete identifier-level working mapping for the current source set; it is not a substitute for controlled requirement wording or a validated platform capability inventory.

12.1 Evidence record and gate decision

The evidence contract in Annex B binds a control revision, lifecycle activity, subject version/digest, producer, result, timestamp and integrity metadata. A gate records the exact criteria, evaluated evidence set, residual findings, waivers, decision, authority and time. The decision may be pass, fail, manual review, waiver required or not applicable only where the process and authority allow it.

**EVD-001**Required evidence SHALL be linked to the evaluated subject and to the applicable Control Baseline revision before a gate may pass.

**EVD-002**A gate SHALL fail closed on missing or invalid mandatory evidence unless an authorised documented manual decision is permitted and recorded.

**EVD-003**A waiver SHALL identify requirement, subject, scope, risk, compensating measure, approving authority, issue and expiry dates, and closure condition; expiry invalidates its use in a later release.

12.2 Evidence status across P2 to P9

Pre-production evidence is clearly marked draft and can support risk reduction. Formal P3–P7 evidence is tied to approved baselines. P8 captures an immutable release decision. P9 preserves the installed-version chain and links new incidents, CVEs, drift and change classifications to the next maintenance decision and patch release.

13 Deployment patterns and domain variants

| **Pattern** | **Implementation characteristic** | **Architecture review focus** |
| --- | --- | --- |
| **Central enterprise** | Shared platform services and governed tenancy | Availability, segregation, capacity and common change control |
| **Federated** | Local execution with shared identity, policy, artifact or evidence | Versioned interfaces, outages and split responsibility |
| **Programme isolated** | Dedicated stack with enterprise control mapping | Operational ownership, patching and evidence exchange |
| **Air-gapped or classified** | Locally complete services and controlled transfer | Offline trust, dependency updates, import/export and classification |

A variant must retain the minimum PRA-Level of every programme it supports. Central services are not assumed reachable in an isolated environment; local equivalent capabilities and evidence export rules are specified explicitly.

**DEP-001**The programme SHALL document deployment pattern, trust boundaries, source and target of every critical exchange, service owner, recovery assumption and applicable domain restrictions.

14 Roles and operating responsibilities

The process owns activity-level RACI. The roles below assign architecture and service accountability without changing that RACI. Approval rights require confirmation in the Directive, Design Authority mandate and platform operating model (A08).

| **Role or function** | **Architecture responsibility** | **Decision boundary** |
| --- | --- | --- |
| **Enterprise Software Industrialisation** | Own C1–C7 contract, mapping and adoption roadmap | Propose enterprise architecture changes |
| **Design Authority** | Review logical/technical coherence and material deviations | Approve architecture subject to formal mandate |
| **Control owners and Security/Quality/Safety** | Own specialist control intent and acceptance | Approve domain-specific risk disposition within mandate |
| **Platform service owner** | Provide PRA capabilities and service evidence | Approve service change within delegated authority |
| **Programme engineering and product design** | Own product design, applicability and compliant use | Approve product baselines and product risk within mandate |
| **Process owners and release roles** | Own P0–P9 activities, gates and artifact RACI | Exercise process decision rights as defined in SDP |

15 Assessment and transition

15.1 Assessment criteria

A conformance assessment tests actual implementation and sampled evidence, not a claimed platform label. It validates selected baseline, required PRA capabilities, data lineage, identity and trust, gate behavior, operational traceability and waiver status. Annex C provides the minimum assessment questions.

15.2 Staged adoption

| **Stage** | **Result** | **Exit evidence** |
| --- | --- | --- |
| **Align** | Approve sources, ownership and two-axis model | Decision record and action closure for baseline blockers |
| **Specify** | Versioned control/capability/phase/evidence map and schemas | Reviewed interface and evidence contracts |
| **Pilot** | One representative P0–P9 path using approved services | Evidence-complete release and one in-service change |
| **Federate** | Repeatable onboarding for divisions and programmes | Conformance assessment and operational service evidence |

A pilot can proceed as a bounded proof while source-language decisions remain open, but no unapproved or ambiguous 'should' control is silently represented as mandatory. The pilot uses a recorded working rule set and upgrades it after the source owners decide.

16 Open actions and decisions

The following actions are part of the proposed architecture package. Owners are proposed functions, not assigned individuals. Each item remains open until its acceptance evidence is reviewed. A01–A06 block a controlled enterprise baseline; the remaining items can be addressed alongside a bounded pilot if their risk is recorded.

| **ID** | **Resolution needed** | **Proposed owner** | **Closure evidence** |
| --- | --- | --- | --- |
| **A01** | Confirm approved source revisions, precedence, document owner and formal approval route. | Governance and Design Authority | Approved document register and decision record |
| **A02** | Decide whether DSCB-L2-REQ-015–017 are mandatory SHALL or guidance and update SDP/PRA references. | Control Baseline owner with Security and Process owners | Consistent wording and exact IDs in all three sources |
| **A03** | Retire A–D profiles and migrate programme selections to L1–L3 plus deployment pattern. | Software Industrialisation and Programme Governance | Migration rule and recorded P0 decisions |
| **A04** | Issue stable PRA capability IDs and validate every DSCB-to-PRA-to-C mapping. | Platform Architecture and Control owners | Versioned, complete matrix with no unmapped required control |
| **A05** | Declare systems of record and ALM ownership for requirements, design, change, verification and release. | Process owner, Enterprise Architecture and programmes | Approved object register and interface owners |
| **A06** | Specify monitoring destinations for logs, health and configuration and define availability/retention. | Platform and Operations with Security | Accepted observability and configuration contracts |
| **A07** | Define the P4 product-to-industrialisation compatibility review and decision rights. | Product Design Authority and Software Industrialisation | Review criteria and pilot architecture decision |
| **A08** | Confirm Platform Lead/service owner, Design Authority, Board and waiver authorities in the Directive. | Governance owner | Approved RACI, waiver process and delegated decision rights |
| **A09** | Agree machine-readable P2 formalisation, P6a, P7/P8 gate and P9 maintenance schemas. | SDLC Process owner and Toolchain Architecture | Versioned schemas and pass/fail test cases |
| **A10** | Set evidence retention, classification, transfer and deletion rules for all domains. | Information Security, Quality and Records | Approved retention matrix and cross-domain handling rules |
| **A11** | Validate offline trust, dependency intake and signing lifecycle for air-gapped L3. | Platform service owner with Security | Reviewed threat model and transfer/recovery test |
| **A12** | Run an end-to-end P0–P9 pilot and verify one release plus one maintenance update. | Pilot programme and Platform service owner | Gate evidence, deployment lineage and assessment report |

17 Proposed architecture decision

Adopt the C1–C7 logical capability model and the control-to-capability-to-platform-to-process-to-evidence chain as the common design basis for enterprise and federated SDLC toolchains. Select L1–L3 at P0, derive the minimum PRA-Level from that choice and select the deployment pattern independently. Use the updated SDP phase definitions and keep each source document authoritative for its own obligations.

Approval of this architecture should be conditional on closure of baseline-blocking Actions A01–A06 and formal review by the relevant control, platform, process, security, quality and design authorities. Until then, this document is suitable for coordinated review and bounded pilot planning, not a declaration that every source standard or role has been formally approved.

Annex A Control to capability traceability

This working matrix covers all 16 L1, 17 L2, 11 L3 and five governance identifiers present in the updated Control Baseline. Capability labels refer to Section 5; platform entries identify PRA layers or cross-cutting trust services, not approved product instances. The process phase is the primary producer or consumer, not a claim that the control applies only in that phase.

* The L2 monitoring entries 015–017 are included for traceability but use 'should' in the current source. They remain advisory pending Action A02; the matrix does not change their normative status.

L1 enterprise baseline

| **DSCB ID** | **C ID** | **PRA capability area** | **Phase** | **Evidence anchor** |
| --- | --- | --- | --- | --- |
| **DSCB-L1-REQ-001** | C2.1 C7.3 | Evidence and traceability | P3–P7 | Requirements to test and configuration links |
| **DSCB-L1-REQ-002** | C3.1 | Source control | P2 P5 | Authored commit history |
| **DSCB-L1-REQ-003** | C3.1 | Source control | P5 | Protected branch settings and review |
| **DSCB-L1-REQ-004** | C4.1 | Security controls | P2 P5 | Static analysis and review results |
| **DSCB-L1-REQ-005** | C3.4 C5.2 | Artifact and dependency | P6 | Dependency inventory and scan |
| **DSCB-L1-REQ-006** | C5.2 | Artifact and dependency | P6 P8 | SBOM bound to artifact identity |
| **DSCB-L1-REQ-007** | C3.2 | Pipeline execution | P6 | Controlled pipeline execution record |
| **DSCB-L1-REQ-008** | C3.2 C5.1 | Pipeline and artifact | P6 | Unique artifact version and digest |
| **DSCB-L1-REQ-009** | C4.1 | Security controls | P2 P6 | Vulnerability scan report |
| **DSCB-L1-REQ-010** | C4.4 C7.3 | Security and evidence | P6 P7 | Finding disposition before release |
| **DSCB-L1-REQ-011** | C5.1 C5.3 | Artifact and dependency | P6 P8 | Repository integrity and digest |
| **DSCB-L1-REQ-012** | C5.1 | Artifact and dependency | P6 P8 | Resolvable artifact identifier |
| **DSCB-L1-REQ-013** | C6.1 C7.3 | Deployment and evidence | P7 P8 | Authorized release decision |
| **DSCB-L1-REQ-014** | C6.2 | Deployment management | P8 | Approval linked to deployment record |
| **DSCB-L1-REQ-015** | C7.3 | Evidence and traceability | P1–P9 | Machine-readable execution evidence |
| **DSCB-L1-REQ-016** | C6.3 C7.3 | Monitoring and evidence | P8 P9 | Deployed version and event record |

L2 secure DevSecOps

| **DSCB ID** | **C ID** | **PRA capability area** | **Phase** | **Evidence anchor** |
| --- | --- | --- | --- | --- |
| **DSCB-L2-REQ-001** | C1.1 | Developer workspace | P1 P5 | Managed environment record |
| **DSCB-L2-REQ-002** | C1.1 C7.2 | Developer workspace | P1 P5 | Approved configuration baseline |
| **DSCB-L2-REQ-003** | C7.1 | Identity across layers | P1 P5 | IAM integration and access logs |
| **DSCB-L2-REQ-004** | C7.1 | Identity across layers | P1 P5 | Privileged MFA policy evidence |
| **DSCB-L2-REQ-005** | C3.4 | Artifact and dependency | P6 | Approved repository configuration |
| **DSCB-L2-REQ-006** | C3.4 C7.2 | Artifact and dependency | P6 | External download control log |
| **DSCB-L2-REQ-007** | C5.3 | Artifact and dependency | P8 | Verified artifact signature |
| **DSCB-L2-REQ-008** | C5.3 C7.1 | Trust and signing services | P8 | Key protection and signing record |
| **DSCB-L2-REQ-009** | C6.2 | Deployment management | P1 P8 | Controlled IaC definition |
| **DSCB-L2-REQ-010** | C2.4 C6.2 | Source and deployment | P1 P8 | IaC history and approval |
| **DSCB-L2-REQ-011** | C4.4 | Pipeline and security | P6 P7 | Evaluated security gate record |
| **DSCB-L2-REQ-012** | C4.4 C6.1 | Security and release | P7 P8 | Threshold and blocking decision |
| **DSCB-L2-REQ-013** | C6.3 | Operational monitoring | P8 P9 | Security event record |
| **DSCB-L2-REQ-014** | C6.3 | Operational monitoring | P8 P9 | Event forwarding evidence |
| **DSCB-L2-REQ-015*** | C6.3 | Operational monitoring | P9 | Central log receipt and retention |
| **DSCB-L2-REQ-016*** | C6.3 | Operational monitoring | P9 | Health state publication record |
| **DSCB-L2-REQ-017*** | C6.2 C6.3 | Deployment and monitoring | P9 | Configuration inventory snapshot |

L3 trusted supply chain

| **DSCB ID** | **C ID** | **PRA capability area** | **Phase** | **Evidence anchor** |
| --- | --- | --- | --- | --- |
| **DSCB-L3-REQ-001** | C3.2 | Pipeline execution | P6 | Independent rebuild comparison |
| **DSCB-L3-REQ-002** | C2.4 C3.2 | Source and pipeline | P6 | Versioned build configuration |
| **DSCB-L3-REQ-003** | C3.2 | Pipeline execution | P6 | Isolation configuration and run |
| **DSCB-L3-REQ-004** | C3.2 | Pipeline execution | P6 | Per-run environment recreation |
| **DSCB-L3-REQ-005** | C3.4 C5.4 | Artifact and dependency | P6 | Verifiable dependency provenance |
| **DSCB-L3-REQ-006** | C5.4 | Artifact and dependency | P6 | Provenance captured in build record |
| **DSCB-L3-REQ-007** | C5.3 | Trust and signing services | P8 | Enterprise-signed artifact record |
| **DSCB-L3-REQ-008** | C5.3 C7.1 | Trust and signing services | P8 | Managed key lifecycle evidence |
| **DSCB-L3-REQ-009** | C2.1 C7.3 | Evidence and traceability | P3–P9 | Requirement to runtime relationship |
| **DSCB-L3-REQ-010** | C6.2 C6.3 | Deployment and monitoring | P8 P9 | Runtime integrity verification |
| **DSCB-L3-REQ-011** | C7.3 C7.4 | Evidence and traceability | P1–P9 | Continuous compliance evidence |

Governance requirements

| **DSCB ID** | **C ID** | **PRA capability area** | **Phase** | **Evidence anchor** |
| --- | --- | --- | --- | --- |
| **DSCB-GOV-REQ-001** | C7.2 | Governance and evidence | P0 | Approved baseline assignment |
| **DSCB-GOV-REQ-002** | C7.4 | Governance and evidence | P0–P9 | Assessment and review record |
| **DSCB-GOV-REQ-003** | C7.2 C7.3 | Governance and evidence | P7 P8 | Approved waiver for non-compliance |
| **DSCB-GOV-REQ-004** | C7.2 | Governance and evidence | P0–P9 | Directive-compliant deviation decision |
| **DSCB-GOV-REQ-005** | C7.3 | Governance and evidence | P0–P9 | Risk, expiry and closure record |

Annex B Evidence contract

The following is the minimum interoperable evidence record for toolchain-to-governance exchange. Product- or domain-specific schemas may add attributes while preserving the common identity and decision relationship.

| **Field** | **Minimum meaning** | **Validation rule** |
| --- | --- | --- |
| **evidence_id** | Unique evidence record identity | Resolvable and immutable or versioned |
| **control_id** | Exact DSCB identifier and revision | Valid for subject's selected baseline |
| **activity_id** | P-phase, process activity and execution step | Maps to current SDP activity |
| **subject** | Object type, ID, revision and digest | Matches evaluated artifact/baseline |
| **producer** | Service and workload or human identity | Authenticated and attributable |
| **result** | Pass, fail, conditional, waived or not applicable | Defined semantics; no implicit pass |
| **time** | Execution and observation timestamps | Correlatable and protected |
| **artifact_reference** | Location of detailed result | Readable under retention policy |
| **integrity** | Digest/signature and verification metadata | Verifies expected content |
| **relationships** | Requirement, design, change, build, release and deployment links | Typed, versioned and resolvable |
| **classification** | Information domain and handling label | Consistent with cross-domain policy |
| **schema_version** | Version of evidence contract | Consumer compatibility declared |

Gate decision record

A gate decision identifies decision ID, subject baseline/digest, selected L1–L3 level, criterion and policy revision, evidence manifest, finding and waiver state, decision, human or service authority, trusted timestamp, and allowed next lifecycle transition. It captures why the decision was made, not only the result.

Annex C Conformance assessment checklist

| **Assessment question** | **Expected evidence** |
| --- | --- |
| **Is programme scope, classification and L1–L3 level approved at P0?** | Applicability Assessment and DSCB assignment |
| **Does the platform provide at least the derived PRA-Level?** | Instance inventory, capability evidence and gap review |
| **Is the deployment pattern independent of assurance selection?** | Architecture and trust boundary decision |
| **Are authoritative ALM, SCM, artifact and operations records declared?** | System-of-record register and versioned interfaces |
| **Are P2 drafts kept distinct from formal P3 baselines?** | Draft status, formalisation decision and lineage |
| **Does product design have an implementable build/test/release path?** | P4 review against industrialisation constraints |
| **Can a release subject be traced end to end?** | Object graph and release snapshot |
| **Are security and quality gates bound to exact rules and evidence?** | Rule version, subject digest and decision record |
| **Do required SBOM, scans, integrity, signing and provenance exist for level?** | Artifact-linked evidence and verification results |
| **Is deployment restricted to the approved artifact and target?** | Approval, signature/integrity check and deployment log |
| **Can P9 incidents and vulnerabilities lead to controlled patch decisions?** | Installed version, trigger, triage and patch trace |
| **Are waivers approved, scoped, time-bounded and unexpired?** | Waiver registry and gate evaluation |
| **Can evidence survive outage, migration and retention duration?** | Availability, export, restore and retention tests |
| **Are air-gapped transfer and local trust controls tested where applicable?** | Import/export and trust-root verification |

Assessors should record conformant, non-conformant or not applicable for each question, link the evidence, name the assessed instance and document corrective actions. A partial pilot result is not an enterprise-wide conformance claim.
