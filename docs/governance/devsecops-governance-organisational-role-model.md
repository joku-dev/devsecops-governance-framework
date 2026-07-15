# DevSecOps Governance Organisational Role Model

**INTERNAL**

**DevSecOps Governance-as-Code**

Organisational Role Model, Inputs, Activities and Outputs

| **Field**     | **Value**                                                                                                                                       |
|---------------|-------------------------------------------------------------------------------------------------------------------------------------------------|
| Document type | Role model / operating model section                                                                                                            |
| Version       | 1.0 draft                                                                                                                                       |
| Purpose       | Define organisational responsibilities for DevSecOps Governance-as-Code, including governance board leadership and platform IaC responsibility. |
| Intended use  | Can be inserted into the DevSecOps Governance-as-Code report as an expanded organisational roles chapter.                                       |
| Intake classification | Explanatory organisational documentation; not a formal governance document and not a registered source document. |
| Governance behavior | Documentation-only; no controls, schemas, policies, releases or runtime behavior are derived from this document. |

**Note.** This document describes organisational roles. Agent roles or automation profiles may support analysis, routing and validation, but they do not replace the organisational accountabilities described here.

# 1. Purpose and Scope

This document defines the organisational role model for DevSecOps Governance-as-Code. It identifies the accountable organisational functions, their inputs, required activities, outputs and decision boundaries.

The model assumes that the Enterprise DevSecOps Governance & Software Industrialisation Lead chairs the DevSecOps Governance Board under mandate of the Chief Digitalisation Officer. The CDO remains the executive accountable owner. The Board remains the formal technical governance body. Cybersecurity, safety and architecture decision rights remain with the respective authorities.

All platform-relevant capabilities are expected to be implemented, maintained and evolved through Infrastructure as Code wherever technically feasible. This responsibility is assigned to the DevSecOps Platform Lead / Platform Owner, while application teams retain ownership for application-specific evidence and remediation.

# 2. Operating Principles

| **Principle**                                | **Meaning**                                                                                                                                                             |
|----------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Federated execution under central governance | Central governance owns the baseline and interpretation model; divisions and application teams execute within that baseline.                                            |
| Decision authority is not automation         | Pipelines, OPA rules and generated reports support decisions but do not replace accountable organisational authorities.                                                 |
| Evidence over assertion                      | Compliance status must be based on artifacts, scans, workflow results, structured records and traceability, not on unverified statements.                               |
| No silent baseline mutation                  | Released baselines, controls, schemas, policy rules and platform behavior must not be changed without review and version control.                                       |
| Platform capabilities as code                | Platform-relevant CI/CD capabilities, adapters, infrastructure and policy execution environments should be implemented as versioned, reviewable Infrastructure as Code. |
| Clear mainline status semantics              | Central status and viewers should represent accepted mainline state, not temporary pull request or diagnostic state.                                                    |

# 3. Consolidated Responsibility Logic

| **Responsibility Area**                                                 | **Accountable Role**                                                                       |
|-------------------------------------------------------------------------|--------------------------------------------------------------------------------------------|
| Enterprise DevSecOps mandate                                            | Chief Digitalisation Officer / Executive Owner                                             |
| Operational governance-as-code ownership                                | Enterprise DevSecOps Governance & Software Industrialisation Lead                          |
| Board leadership                                                        | Enterprise DevSecOps Governance & Software Industrialisation Lead acting under CDO mandate |
| DevSecOps standards and baseline approval                               | DevSecOps Governance Board                                                                 |
| Cybersecurity controls and risk acceptance                              | CISO / Cybersecurity Function                                                              |
| Safety lifecycle and safety-critical deviations                         | Safety Authority                                                                           |
| Architecture guardrails and design decisions                            | Architecture Board / Design Authority                                                      |
| Platform Infrastructure as Code, CI/CD adapters and platform automation | DevSecOps Platform Lead / Platform Owner                                                   |
| Program adoption and transition                                         | Divisions and Programs                                                                     |
| Application evidence and remediation                                    | Application Team                                                                           |
| Repository enforcement                                                  | Application Repository Owner                                                               |
| Deviations from mandatory requirements                                  | Waiver Authority according to risk classification                                          |
| Independent review and audit preparation                                | Audit and Compliance Reviewer                                                              |

# 4. Detailed Organisational Role Descriptions

## 1. Chief Digitalisation Officer / Executive Owner

**Role purpose.** The Chief Digitalisation Officer is the executive accountable owner for the enterprise DevSecOps mandate. The role ensures that DevSecOps is established as an enterprise software delivery and governance capability rather than a local tooling initiative.

### Inputs

| **Input**                                     | **Description**                                                                                           |
|-----------------------------------------------|-----------------------------------------------------------------------------------------------------------|
| DevSecOps Policy                              | Defines what is mandatory and who is accountable.                                                         |
| DevSecOps Directive                           | Defines how the policy is executed in practice.                                                           |
| Maturity and adoption reports                 | Show maturity distribution, adoption progress, blocked programs and systemic gaps.                        |
| Platform capability assessments               | Show whether enterprise platforms can support the required governance baseline.                           |
| Critical waiver and deviation cases           | Require executive decision when risk or organizational impact exceeds delegated authority.                |
| Security, safety and architecture escalations | Provide domain-risk input that may require executive balancing of delivery, risk, compliance and funding. |
| Budget and resource proposals                 | Define required capacity for platform, governance, rollout and evidence operations.                       |

### Required activities

| **Activity**                          | **Required expertise and execution detail**                                                                                                                                                                                                         |
|---------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Establish enterprise mandate          | Approve DevSecOps Governance-as-Code as the enterprise operating model for governed software delivery. This requires understanding the strategic relevance of DevSecOps for Software Defined Defence and the ability to anchor it across divisions. |
| Approve adoption objectives           | Define which programs, repositories and platforms are in scope, which maturity level is expected and which timelines apply. This requires portfolio-level prioritization and change-management expertise.                                           |
| Ensure funding and resourcing         | Evaluate platform, tooling, governance and staffing needs and allocate resources. This requires budget ownership, understanding of technical capability gaps and awareness of rollout risk.                                                         |
| Resolve enterprise-level conflicts    | Decide when division, program, platform, cybersecurity, safety or architecture priorities conflict and cannot be resolved by the Governance Board.                                                                                                  |
| Review maturity and compliance status | Challenge whether reported progress is evidence-based, whether adoption risks are visible and whether maturity targets remain realistic.                                                                                                            |
| Decide on critical risk escalations   | Make or co-make decisions where critical cybersecurity, safety, compliance or delivery impact exceeds delegated authority.                                                                                                                          |

### Outputs

| **Output**              | **Description**                                                                            |
|-------------------------|--------------------------------------------------------------------------------------------|
| Enterprise mandate      | Formal confirmation that DevSecOps Governance-as-Code is the enterprise baseline approach. |
| Funding decision        | Approved budget, staffing or platform investment.                                          |
| Adoption targets        | Defined rollout expectations, maturity targets and timelines.                              |
| Executive status report | Periodic reporting to executive management.                                                |
| Escalation decision     | Resolution of conflicts or risks above Board-level authority.                              |

**Role boundaries.** The CDO does not operate pipelines, author OPA rules, approve every technical finding or produce application evidence. The role is accountable for mandate, funding, adoption and executive escalation.

## 2. Enterprise DevSecOps Governance & Software Industrialisation Lead

Role purpose. The Enterprise DevSecOps Governance & Software Industrialisation Lead is the delegated operational governance owner for DevSecOps Governance-as-Code across the company. The role acts on behalf of the CDO, chairs the DevSecOps Governance Board and ensures that DevSecOps, software industrialisation and architecture governance are applied consistently across divisions, programs, platforms and application repositories.

### Inputs

| **Input**                                  | **Description**                                                                          |
|--------------------------------------------|------------------------------------------------------------------------------------------|
| CDO mandate                                | Defines delegated authority, target state, scope and expected outcomes.                  |
| Policy, Directive and Standards            | Define mandatory intent, governance structure, control expectations and execution rules. |
| Control baseline and platform architecture | Define controls and platform capabilities to be maintained.                              |
| Architecture governance assets             | Define quality markers, guardrails, review gates and architecture readiness rules.       |
| Application repository results             | Provide evidence of baseline consumption, compliance status and recurring findings.      |
| Security, safety and architecture findings | Identify domain-specific risks or required changes.                                      |
| Platform feedback                          | Shows whether CI/CD platforms can implement the required evidence and control model.     |
| Governance change requests                 | Trigger updates to documents, models, schemas, policies, workflows or releases.          |

### Required activities

| **Activity**                                               | **Required expertise and execution detail**                                                                                                                                                                             |
|------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Chair the DevSecOps Governance Board                       | Prepare agendas, structure decisions, ensure the correct authorities participate, document decisions and track actions. Requires governance facilitation, technical understanding and authority management.             |
| Maintain the central governance operating model            | Ensure that policy, directive, standards, controls, platform mapping, architecture governance, evidence contracts and release packages remain aligned.                                                                  |
| Translate governance intent into executable baseline logic | Determine which requirements can be represented as YAML models, JSON schemas, OPA/Rego policies, CI/CD checks, evidence contracts or generated reports. Requires policy interpretation and automation design expertise. |
| Coordinate source document changes                         | Ensure that new or changed governance source documents are registered, reviewed and not prematurely converted into controls, markers, policies or baselines before approval.                                            |
| Control baseline evolution                                 | Coordinate changes to controls, platform capabilities, evidence expectations and maturity levels. Ensure downstream impact is visible before release.                                                                   |
| Control release lifecycle                                  | Classify changes as editorial, draft, release candidate or baseline-impacting. Coordinate release notes, versioned baseline packages, migration guidance and downstream communication.                                  |
| Govern application onboarding                              | Define how application repositories consume the baseline, what evidence they must produce, when checks become required and how rollout maturity is measured.                                                            |
| Ensure evidence-driven reporting                           | Ensure central status, indexes and viewers are based on accepted mainline evidence, not temporary pull request or diagnostic results.                                                                                   |
| Coordinate domain authorities                              | Bring CISO, Safety Authority, Architecture Board, Platform Owner and application representatives into decisions when their domains are affected.                                                                        |
| Escalate unresolved risks                                  | Escalate to CDO, CISO, Safety Authority or Architecture Board when a decision exceeds delegated authority.                                                                                                              |
| Protect against local divergence                           | Ensure that application teams do not copy or fork the governance baseline locally and that platform adapters remain additive.                                                                                           |

### Outputs

| **Output**                             | **Description**                                                              |
|----------------------------------------|------------------------------------------------------------------------------|
| Board agenda and decision log          | Structured record of topics, decisions, open actions and escalations.        |
| Versioned governance baseline          | Controlled baseline package for downstream consumption.                      |
| Governance release notes               | Explanation of what changed and what downstream teams must do.               |
| Evidence contract                      | Definition of evidence expected from application repositories and platforms. |
| Reusable workflow and adapter guidance | Instructions for consuming the central baseline from CI/CD platforms.        |
| Central status model                   | Interpretation model for mainline, branch, pull request and manual results.  |
| Application onboarding guidance        | Practical instructions for application teams and repository owners.          |
| Escalation package                     | Prepared decision input for executive or domain authority decisions.         |

Role boundaries. The Enterprise DevSecOps Governance & Software Industrialisation Lead chairs and operates the governance system at enterprise level but does not replace independent cybersecurity, safety, architecture or executive decision authority. The role does not own application remediation and does not unilaterally accept high-risk deviations.

## 3. DevSecOps Governance Board

**Role purpose.** The DevSecOps Governance Board is the formal technical governance body for DevSecOps. It ensures that standards, baselines, maturity levels, waivers and adoption decisions are consistent, reviewable and enforceable.

### Inputs

| **Input**                         | **Description**                                                           |
|-----------------------------------|---------------------------------------------------------------------------|
| Policy and Directive              | Provide mandatory governance intent and operating rules.                  |
| Control baseline change proposals | Propose additions, removals or changes to controls.                       |
| Platform capability reports       | Show whether required controls can be implemented on available platforms. |
| Application compliance results    | Show evidence from onboarded repositories.                                |
| Waiver requests                   | Require review and approval within delegated authority.                   |
| Maturity reports                  | Show adoption progress and gaps.                                          |
| Audit and compliance findings     | Highlight evidence gaps or governance weaknesses.                         |

### Required activities

| **Activity**                              | **Required expertise and execution detail**                                                                                                                                     |
|-------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Approve standards and baselines           | Review whether proposed controls are necessary, testable, proportionate and aligned with policy and directive. Requires DevSecOps, security, platform and governance expertise. |
| Define maturity levels                    | Determine what L1, L2, L3 and GOV require in terms of controls, evidence, automation and adoption readiness.                                                                    |
| Evaluate waiver requests                  | Assess risk classification, affected requirements, justification, compensating controls, expiry date and approval authority.                                                    |
| Monitor enterprise adoption               | Review adoption status across divisions, programs and repositories and determine whether delays require management action.                                                      |
| Coordinate domain-specific implementation | Align enterprise baseline requirements with constraints such as classified environments, air-gapped platforms or restricted operational networks.                               |
| Decide baseline release readiness         | Determine whether a change is ready to become a release candidate or released baseline.                                                                                         |
| Review recurring findings                 | Identify patterns in evidence, waivers or platform failures and decide whether the baseline, tooling or rollout approach must change.                                           |
| Ensure traceability                       | Verify that requirements remain traceable from source documents to controls, platform capabilities, evidence and reports.                                                       |

### Outputs

| **Output**                       | **Description**                                                                            |
|----------------------------------|--------------------------------------------------------------------------------------------|
| Approved standards and baselines | Formal approval of controlled governance artifacts.                                        |
| Waiver decisions                 | Approved, rejected or escalated waiver outcomes.                                           |
| Maturity model                   | Defined levels and adoption expectations.                                                  |
| Adoption report                  | Status of rollout, maturity and compliance progress.                                       |
| Baseline release decision        | Decision whether to release, defer or rework a baseline update.                            |
| Governance action list           | Follow-up actions for platform, application, security, architecture or audit stakeholders. |

**Role boundaries.** The Board owns the DevSecOps governance decision model. It does not implement application fixes, operate every pipeline or replace CISO, Safety Authority or Architecture Board decision rights.

## 4. CISO / Cybersecurity Function

**Role purpose.** The CISO or cybersecurity function owns cybersecurity authority. The role defines mandatory cybersecurity expectations and retains decision rights for cybersecurity risk acceptance.

### Inputs

| **Input**                      | **Description**                                                |
|--------------------------------|----------------------------------------------------------------|
| Cybersecurity control baseline | Defines mandatory security controls.                           |
| Vulnerability scan results     | Show vulnerabilities, severity and remediation status.         |
| SBOM evidence                  | Provides component and dependency transparency.                |
| Security domain classification | Defines applicable security domain and assurance expectations. |
| Waiver requests                | Identify deviations from mandatory security requirements.      |
| Compensating controls          | Describe temporary measures for risk reduction.                |
| Threat and risk assessments    | Provide context for deviations or architecture decisions.      |

### Required activities

| **Activity**                                   | **Required expertise and execution detail**                                                                                                          |
|------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------|
| Define cybersecurity baseline expectations     | Determine mandatory requirements for vulnerability management, dependencies, artifact integrity, access control, software supply chain and evidence. |
| Define vulnerability management rules          | Set severity thresholds, remediation expectations, SLA logic and acceptable evidence for vulnerability scans.                                        |
| Classify security domains                      | Determine applicable security domain and additional control strictness or platform constraints.                                                      |
| Review high-risk cybersecurity waivers         | Assess whether justification, compensating controls, expiry and residual risk are acceptable.                                                        |
| Accept or reject cybersecurity risk            | Make explicit risk decisions for deviations and ensure named authority is documented.                                                                |
| Exercise veto authority                        | Reject reductions of mandatory cybersecurity controls when residual risk is unacceptable.                                                            |
| Review audit-relevant evidence                 | Assess whether security evidence is sufficient for cybersecurity audit expectations.                                                                 |
| Coordinate with platform and application teams | Ensure required security evidence can be generated and findings are technically actionable.                                                          |

### Outputs

| **Output**                      | **Description**                                              |
|---------------------------------|--------------------------------------------------------------|
| Cybersecurity baseline approval | Confirmation of mandatory security expectations.             |
| Vulnerability management rules  | Severity thresholds, SLA expectations and remediation rules. |
| Security risk acceptance        | Explicit decision on accepted residual cybersecurity risk.   |
| Security waiver decision        | Approved, rejected or escalated waiver.                      |
| Security audit finding          | Formal finding or observation.                               |
| Security veto decision          | Decision preventing reduction of mandatory controls.         |

**Role boundaries.** The cybersecurity function defines and decides cybersecurity requirements and risks. It does not implement all application fixes or own every repository workflow.

## 5. Safety Authority

**Role purpose.** The Safety Authority owns safety-related decision rights and ensures that safety lifecycle requirements and safety-critical deviations are explicitly controlled.

### Inputs

| **Input**                     | **Description**                                                         |
|-------------------------------|-------------------------------------------------------------------------|
| Safety lifecycle requirements | Define applicable safety expectations.                                  |
| Safety impact classification  | Identifies whether a system, component or deviation is safety-relevant. |
| Safety evidence               | Shows whether required safety-related evidence exists.                  |
| Deviation or waiver requests  | Identify departures from mandatory safety expectations.                 |
| Release readiness reports     | Show whether release evidence affects safety-relevant operation.        |
| Compensating measures         | Describe temporary risk reduction measures.                             |

### Required activities

| **Activity**                              | **Required expertise and execution detail**                                                              |
|-------------------------------------------|----------------------------------------------------------------------------------------------------------|
| Define safety lifecycle expectations      | Determine which safety-related activities, evidence and review points must be integrated into DevSecOps. |
| Classify safety impact                    | Assess whether a system, change, control deviation or release has safety relevance.                      |
| Review safety-critical deviations         | Determine whether deviations are acceptable, require mitigation or must be rejected.                     |
| Define required safety evidence           | Specify what evidence must exist before release, deployment or waiver acceptance.                        |
| Assess compensating measures              | Review whether proposed controls reduce safety risk sufficiently during a temporary exception.           |
| Coordinate with architecture and security | Align safety decisions with system architecture, cybersecurity controls and operational constraints.     |

### Outputs

| **Output**                   | **Description**                                     |
|------------------------------|-----------------------------------------------------|
| Safety impact classification | Formal classification of safety relevance.          |
| Safety evidence requirement  | Required evidence for safety-relevant delivery.     |
| Safety waiver decision       | Approved, rejected or escalated deviation decision. |
| Safety risk statement        | Documented residual risk position.                  |
| Safety escalation            | Escalation to executive or governance level.        |

**Role boundaries.** The Safety Authority defines and controls the safety decision boundary. It does not replace engineering teams that must produce technical evidence.

## 6. DevSecOps Platform Lead / Platform Owner

**Role purpose.** The DevSecOps Platform Lead or Platform Owner provides the technical execution capability required to apply the central DevSecOps and architecture governance baseline across CI/CD platforms, development environments and runtime-adjacent platform services. All platform-relevant capabilities shall be implemented, maintained and evolved through Infrastructure as Code wherever technically feasible.

### Inputs

| **Input**                           | **Description**                                                                                                    |
|-------------------------------------|--------------------------------------------------------------------------------------------------------------------|
| Platform reference architecture     | Defines required platform capabilities, layers, integration points and constraints.                                |
| DevSecOps control baseline          | Defines controls that the platform must technically support.                                                       |
| Pipeline baseline                   | Defines CI/CD stages, gates, evidence points and control placement.                                                |
| Evidence contracts                  | Define evidence artifacts, schemas, result formats and upload mechanisms.                                          |
| Infrastructure-as-Code standards    | Define how platform infrastructure, configuration and environment setup must be represented, reviewed and applied. |
| CI/CD platform constraints          | Describe GitHub Actions, GitLab CI, Jenkins, Bamboo, Bitbucket or other limitations.                               |
| Security domain requirements        | Define restrictions for classified, air-gapped, restricted or cloud/on-prem environments.                          |
| Secrets and credential requirements | Define how credentials, tokens, signing keys and service identities must be managed.                               |

### Required activities

| **Activity**                                              | **Required expertise and execution detail**                                                                                                                                                                                                                                                                                                                                |
|-----------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Implement platform capabilities as Infrastructure as Code | Model platform infrastructure, CI/CD execution environments, runners, artifact repositories, evidence storage, policy execution services and supporting components as version-controlled IaC. Requires expertise in Terraform/OpenTofu, Ansible, Helm, Kubernetes manifests, GitLab/GitHub configuration, cloud or on-prem automation and secure configuration management. |
| Maintain approved platform IaC blueprints                 | Provide reusable, reviewed and versioned IaC blueprints for standard platform capabilities. Blueprints must be suitable for controlled rollout and must not rely on undocumented manual setup.                                                                                                                                                                             |
| Maintain CI/CD platform adapters                          | Ensure that GitHub Actions, GitLab CI, Jenkins, Bamboo or Bitbucket consume the same governance baseline without changing governance semantics.                                                                                                                                                                                                                            |
| Implement approved pipeline blueprints                    | Translate governance requirements into reusable workflows, templates, jobs and platform patterns while preserving control placement, evidence generation and report-only or blocking behavior.                                                                                                                                                                             |
| Provide evidence generation mechanisms                    | Ensure that build artifacts, SBOMs, vulnerability scans, signatures, test reports, architecture evidence and governance result files can be generated consistently.                                                                                                                                                                                                        |
| Provide evidence storage and retrieval                    | Ensure generated evidence can be stored, retrieved, linked to runs and made available for central intake, reporting, audit and compliance review.                                                                                                                                                                                                                          |
| Maintain secure artifact repositories                     | Provide controlled artifact storage for application artifacts, SBOMs, signatures, baseline packages and governance evidence with traceability, access control and retention expectations.                                                                                                                                                                                  |
| Integrate secrets and credentials securely                | Define mechanisms for credentials, tokens, signing keys, scanner credentials and service identities. Secrets must not be hardcoded in repositories or IaC files.                                                                                                                                                                                                           |
| Validate IaC before platform changes                      | Ensure IaC changes are reviewed, linted, security-checked and tested before application. Manual console changes should be avoided except for documented break-glass cases.                                                                                                                                                                                                 |
| Detect and manage configuration drift                     | Implement mechanisms to detect divergence between live platform configuration and approved IaC baseline. Drift must be reported, assessed and remediated or formally accepted.                                                                                                                                                                                             |
| Support environment-specific variants                     | Provide IaC patterns for cloud, on-prem, air-gapped, classified or restricted environments without forking the governance model.                                                                                                                                                                                                                                           |

### Outputs

| **Output**                       | **Description**                                                                                           |
|----------------------------------|-----------------------------------------------------------------------------------------------------------|
| Approved platform IaC blueprints | Version-controlled and reviewed Infrastructure-as-Code modules or templates.                              |
| CI/CD platform adapter           | Tool-specific implementation for GitHub, GitLab, Jenkins, Bamboo, Bitbucket or other supported platforms. |
| Approved pipeline blueprint      | Reusable CI/CD pattern for application repositories.                                                      |
| Evidence generation mechanism    | Workflow, script, template or service that creates required evidence files.                               |
| Evidence storage mechanism       | Controlled storage and retrieval path for evidence produced by application and governance runs.           |
| Secure artifact repository       | Controlled repository for build artifacts, SBOMs, signatures, releases and evidence.                      |
| Platform capability mapping      | Mapping between governance controls and platform implementation capability.                               |
| IaC validation report            | Evidence that infrastructure changes were linted, validated, security-checked and reviewed.               |
| Drift report                     | Statement whether live configuration matches the approved IaC baseline.                                   |
| Platform lifecycle plan          | Upgrade, migration and maintenance plan for governance-relevant platform capabilities.                    |

**Role boundaries.** The Platform Lead owns platform capability and all platform-relevant IaC. This includes IaC required to provision, configure, validate and operate DevSecOps platform capabilities. The Platform Lead does not own product-specific application code, product-specific remediation or central governance content. Application teams remain responsible for application-specific evidence and remediation.

## 7. Architecture Board / Design Authority

**Role purpose.** The Architecture Board or Design Authority owns architecture decision rights, architecture readiness criteria and architecture exceptions within the governance model.

### Inputs

| **Input**                    | **Description**                                                                                      |
|------------------------------|------------------------------------------------------------------------------------------------------|
| Architecture guardrails      | Define mandatory architecture expectations.                                                          |
| Quality markers              | Define measurable architecture quality expectations.                                                 |
| Review gates                 | Define required architecture review points.                                                          |
| Architecture evidence        | Includes architecture descriptions, deployment assumptions, interface evidence and baseline records. |
| Exception requests           | Identify deviations from architecture expectations.                                                  |
| Release readiness reports    | Show whether architecture evidence supports release.                                                 |
| Security and safety findings | Indicate domain-specific architecture risk.                                                          |

### Required activities

| **Activity**                          | **Required expertise and execution detail**                                                                                                  |
|---------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------|
| Maintain architecture guardrails      | Define and update architecture constraints applied consistently across systems or product classes.                                           |
| Define quality markers                | Determine measurable expectations such as traceability, modularity, interface ownership, deployment readiness, observability and resilience. |
| Review architecture evidence          | Assess whether documentation, models, deployment information, interface contracts and runtime assumptions are sufficient.                    |
| Decide design authority matters       | Approve or reject architecture decisions, design deviations and baseline compatibility statements.                                           |
| Evaluate architecture exceptions      | Assess justification, residual risk, mitigation, expiry and impact on release or operation.                                                  |
| Review release architecture readiness | Determine whether release evidence supports deployment, operational readiness and compatibility with approved baseline.                      |
| Coordinate with security and safety   | Ensure architecture decisions do not bypass cybersecurity or safety authorities.                                                             |

### Outputs

| **Output**                      | **Description**                                              |
|---------------------------------|--------------------------------------------------------------|
| Architecture review record      | Documented review outcome and required actions.              |
| Design authority decision       | Approved, rejected or conditional architecture decision.     |
| Architecture exception decision | Controlled approval or rejection of deviation.               |
| Architecture readiness result   | Statement whether architecture evidence supports release.    |
| Required remediation actions    | Specific actions assigned to application or platform teams.  |
| Architecture baseline decision  | Decision regarding compatibility with architecture baseline. |

**Role boundaries.** The Architecture Board evaluates architecture sufficiency and decides exceptions. Product and application teams must supply the evidence.

## 8. Divisions and Programs

**Role purpose.** Divisions and programs are accountable for implementing DevSecOps requirements within their delivery scope. They own adoption in real projects and products.

### Inputs

| **Input**                             | **Description**                                             |
|---------------------------------------|-------------------------------------------------------------|
| Enterprise standards                  | Define mandatory governance requirements.                   |
| Control baseline and maturity targets | Define required maturity and evidence expectations.         |
| Platform onboarding guidance          | Defines how application teams consume the central baseline. |
| Application compliance reports        | Show repository-level findings and status.                  |
| Waiver decisions                      | Define accepted temporary deviations.                       |
| Architecture and security findings    | Require program-level remediation or planning.              |

### Required activities

| **Activity**                         | **Required expertise and execution detail**                                                                    |
|--------------------------------------|----------------------------------------------------------------------------------------------------------------|
| Plan DevSecOps adoption              | Determine which repositories, teams, products and delivery phases must be onboarded and in which order.        |
| Assign implementation responsibility | Ensure that application teams, repository owners and platform contacts are identified.                         |
| Manage transition roadmaps           | Define migration steps for existing programs that cannot immediately meet the target baseline.                 |
| Ensure evidence production           | Make sure application teams produce required SBOM, vulnerability, build, governance and architecture evidence. |
| Track remediation                    | Monitor whether findings are fixed, accepted through waiver or escalated.                                      |
| Report compliance status             | Provide program-level status on adoption, findings, waivers, maturity and blockers.                            |
| Control local deviations             | Prevent local redefinition of the governance baseline and ensure deviations follow the waiver process.         |

### Outputs

| **Output**               | **Description**                                       |
|--------------------------|-------------------------------------------------------|
| Program adoption plan    | Plan for onboarding repositories and teams.           |
| Transition roadmap       | Migration plan for existing programs.                 |
| Compliance status report | Program-level status on DevSecOps implementation.     |
| Remediation plan         | Actions for addressing findings.                      |
| Waiver request           | Formal request for temporary deviation.               |
| Maturity progress report | Evidence of progress against agreed maturity targets. |

**Role boundaries.** Divisions and programs own implementation and adoption in their scope. They do not own the central baseline and must not redefine mandatory controls locally.

## 9. Application Team

**Role purpose.** The Application Team owns product-specific implementation and evidence production in the application repository.

### Inputs

| **Input**                          | **Description**                                       |
|------------------------------------|-------------------------------------------------------|
| Central reusable workflow          | Provides the baseline evaluation mechanism.           |
| Evidence contract                  | Defines required evidence files and formats.          |
| Application source code            | Product code and configuration under team ownership.  |
| Build artifact                     | Object checked, packaged or released.                 |
| SBOM tooling                       | Produces software bill of materials.                  |
| Vulnerability scan tooling         | Produces security scan results.                       |
| Architecture evidence requirements | Define required architecture and deployment evidence. |
| Governance findings                | Show failed checks, warnings or missing evidence.     |

### Required activities

| **Activity**                         | **Required expertise and execution detail**                                                                         |
|--------------------------------------|---------------------------------------------------------------------------------------------------------------------|
| Produce build or source artifact     | Package the application reproducibly so it can be evaluated by the baseline.                                        |
| Generate SBOM evidence               | Use approved tooling to create a valid bill of materials that reflects the evaluated artifact.                      |
| Generate vulnerability scan evidence | Run approved scanners, produce machine-readable results and ensure severity information is usable.                  |
| Provide governance input             | Create or maintain governance-run input files for richer control evaluation where required.                         |
| Provide architecture evidence        | Maintain architecture, deployment, interface, runtime and exception evidence expected by the architecture baseline. |
| Call the central baseline workflow   | Integrate the reusable workflow with pinned references instead of copying governance logic locally.                 |
| Review pull request findings         | Determine whether findings require code fixes, evidence fixes or waiver requests.                                   |
| Remediate findings                   | Fix vulnerabilities, missing evidence, configuration gaps, architecture gaps or build issues.                       |
| Prepare waiver requests              | Provide justification, affected requirements, compensating controls and expiry for temporary deviations.            |
| Preserve evidence integrity          | Ensure evidence is produced by the pipeline and not manually fabricated or edited after the fact.                   |

### Outputs

| **Output**                | **Description**                                        |
|---------------------------|--------------------------------------------------------|
| Application artifact      | Build or source artifact evaluated by the baseline.    |
| SBOM                      | Machine-readable bill of materials.                    |
| Vulnerability scan result | Machine-readable security scan evidence.               |
| Governance run input      | Optional richer evidence input for control evaluation. |
| Architecture evidence     | Product-specific architecture evidence.                |
| Pipeline evidence         | Generated evidence from the application CI/CD run.     |
| Remediation evidence      | Proof that findings were fixed.                        |
| Waiver request            | Formal request for temporary exception.                |

**Role boundaries.** The Application Team owns product evidence and remediation. It does not own the central governance baseline or its interpretation logic.

## 10. Application Repository Owner

**Role purpose.** The Application Repository Owner is responsible for enforcing the governance workflow in repository configuration.

### Inputs

| **Input**                       | **Description**                                               |
|---------------------------------|---------------------------------------------------------------|
| Stable governance workflow runs | Evidence that the baseline workflow works reliably.           |
| Branch protection settings      | Controls for protected branches and required reviews.         |
| Required check recommendations  | Governance decision on when checks should become mandatory.   |
| Pinned workflow reference       | Release tag or commit SHA of the reusable workflow.           |
| Repository onboarding status    | Shows whether evidence and workflow integration are complete. |

### Required activities

| **Activity**                         | **Required expertise and execution detail**                                       |
|--------------------------------------|-----------------------------------------------------------------------------------|
| Configure repository workflow        | Add or approve the workflow file that calls the central governance baseline.      |
| Pin reusable workflow reference      | Ensure the repository uses an approved tag or commit SHA, not a moving reference. |
| Enable branch protection             | Configure main so direct changes cannot bypass review and required checks.        |
| Configure required governance checks | Make the baseline check mandatory once it has proven stable.                      |
| Monitor check stability              | Confirm workflow reliability on real pull requests before enforcement.            |
| Coordinate with application team     | Ensure artifact, SBOM and scan paths align with workflow inputs.                  |
| Prevent local governance forks       | Ensure the repository does not copy and alter governance logic locally.           |

### Outputs

| **Output**                        | **Description**                                        |
|-----------------------------------|--------------------------------------------------------|
| Protected main branch             | Branch protection configured and active.               |
| Required governance check         | Central baseline check enforced.                       |
| Pinned workflow reference         | Approved reference to central workflow.                |
| Onboarded repository              | Repository meets onboarding definition of done.        |
| Repository configuration evidence | Evidence of branch protection and check configuration. |

**Role boundaries.** The Repository Owner enforces the approved mechanism. The role does not approve governance exceptions or redefine baseline content.

## 11. Waiver Authority

**Role purpose.** The Waiver Authority approves or rejects deviations from mandatory governance requirements. The correct authority depends on risk classification.

### Inputs

| **Input**                | **Description**                                                |
|--------------------------|----------------------------------------------------------------|
| Waiver request           | Formal request for exception.                                  |
| Affected requirements    | Controls, policies or governance expectations not met.         |
| Risk classification      | Low, medium, high cybersecurity, high safety or critical risk. |
| Justification            | Explanation why compliance is temporarily not possible.        |
| Compensating controls    | Temporary controls to reduce risk.                             |
| Named approver and dates | Accountable person or body, approval date and expiry.          |

### Required activities

| **Activity**                   | **Required expertise and execution detail**                                                                                           |
|--------------------------------|---------------------------------------------------------------------------------------------------------------------------------------|
| Validate completeness          | Check that scope, object, affected requirements, justification, risk classification, compensating controls and expiry are documented. |
| Confirm approval authority     | Determine whether Governance Board, CISO, Safety Authority or joint executive decision is required.                                   |
| Assess technical justification | Evaluate whether the reason for deviation is credible and temporary.                                                                  |
| Assess risk classification     | Determine whether risk level is correctly stated and domain authorities are involved.                                                 |
| Review compensating controls   | Judge whether compensating measures sufficiently reduce residual risk during the waiver period.                                       |
| Approve, reject or escalate    | Make a decision within authority or escalate to the correct decision body.                                                            |
| Ensure time limitation         | Confirm the waiver has a clear expiry date and is not open-ended.                                                                     |
| Review expiry or revocation    | Ensure expired or revoked waivers are not silently accepted by governance checks.                                                     |

### Outputs

| **Output**                    | **Description**                             |
|-------------------------------|---------------------------------------------|
| Approved waiver               | Time-bound approved exception.              |
| Rejected waiver               | Decision that deviation is not acceptable.  |
| Escalated waiver              | Transfer to higher or different authority.  |
| Compensating control decision | Accepted or rejected compensating controls. |
| Residual risk statement       | Documented accepted risk.                   |
| Waiver registry entry         | Structured and traceable waiver record.     |

**Role boundaries.** A waiver does not remove a requirement permanently. It is a controlled, time-limited exception with named accountability.

## 12. Audit and Compliance Reviewer

**Role purpose.** The Audit and Compliance Reviewer assesses whether the Governance-as-Code model produces sufficient traceability, evidence and reviewability for audit and compliance purposes.

### Inputs

| **Input**                          | **Description**                                                              |
|------------------------------------|------------------------------------------------------------------------------|
| Generated reports                  | Control evaluation reports, gap reports, lineage reports and status reports. |
| Traceability matrices              | Links from policy and directive to controls, evidence and results.           |
| Status snapshots                   | Central status indexes and viewer outputs.                                   |
| Waiver registry                    | Approved, expired, revoked or rejected deviations.                           |
| Release packages                   | Versioned governance baselines and release notes.                            |
| Pipeline and architecture evidence | Application evidence and architecture readiness outputs.                     |

### Required activities

| **Activity**                     | **Required expertise and execution detail**                                                                           |
|----------------------------------|-----------------------------------------------------------------------------------------------------------------------|
| Review traceability              | Verify that governance requirements can be traced from source documents to controls, evidence and results.            |
| Assess evidence completeness     | Determine whether generated artifacts are sufficient to support compliance claims.                                    |
| Review waiver quality            | Check whether waivers are justified, time-bound, approved by the right authority and linked to compensating controls. |
| Verify baseline release evidence | Confirm that released baselines are versioned, documented and not silently changed.                                   |
| Assess reporting reliability     | Review whether status indexes and viewer outputs reflect accepted mainline state rather than temporary results.       |
| Identify audit gaps              | Detect missing evidence, inconsistent mappings, unclear ownership or uncontrolled local interpretations.              |
| Prepare audit packages           | Compile reports, traceability views, evidence references and waiver summaries for review.                             |
| Recommend improvements           | Provide concrete improvement actions for governance, evidence, reporting or ownership.                                |

### Outputs

| **Output**                 | **Description**                                       |
|----------------------------|-------------------------------------------------------|
| Audit finding              | Formal finding or observation.                        |
| Compliance assessment      | Evaluation of governance compliance status.           |
| Evidence review result     | Statement on evidence completeness and reliability.   |
| Audit preparation package  | Structured package for internal or external review.   |
| Improvement recommendation | Actionable recommendation for governance improvement. |

**Role boundaries.** Audit and compliance review assesses evidence and control effectiveness. It does not own the central baseline, application remediation or platform implementation.

# 5. Ownership Boundaries

| **Boundary**                                  | **Ownership Statement**                                                                                                                                                                                         |
|-----------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Central governance repository                 | Owns the baseline, interpretation model, evidence contracts, release packages, reusable workflow references and central status model.                                                                           |
| Platform capability                           | Owned by the Platform Lead. Platform-relevant infrastructure, adapters, runner setup, artifact repositories, evidence storage and policy execution environments should be maintained as Infrastructure as Code. |
| Application repositories                      | Own application code, build output, product-specific evidence, remediation and repository enforcement configuration.                                                                                            |
| Security, safety and architecture authorities | Retain decision rights for their risk domains and must not be bypassed by automation or platform convenience.                                                                                                   |
| Audit and compliance                          | Review evidence, traceability and assurance quality but do not own the baseline or product remediation.                                                                                                         |

# 6. Platform Infrastructure-as-Code Clarification

The Platform Lead is accountable for all platform-relevant Infrastructure as Code. This includes the IaC needed to provision, configure, validate and operate DevSecOps platform capabilities used by application teams. Typical examples are CI/CD runner infrastructure, CI/CD platform configuration, artifact repositories, evidence storage, policy execution environments, secrets integration patterns, platform adapters, baseline workflow execution infrastructure and environment provisioning required for governed software delivery.

Application teams may own product-specific deployment manifests, product IaC or environment configuration where these are part of the application or product boundary. These artifacts must comply with the central platform blueprints, security requirements, architecture guardrails and evidence contracts. They do not transfer ownership of the central platform capability away from the Platform Lead.

Manual platform configuration should be treated as an exception. Where manual intervention is unavoidable, it should be documented, reviewed and either backported into IaC or formally accepted as a controlled deviation.
