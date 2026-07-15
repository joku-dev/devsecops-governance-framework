# DevSecOps Directive

Document ID: `DEVSECOPS-DIR-001`
Document Type: `directive`
Status: `draft`
Document Number: `TBD`

| Field | Value |
| --- | --- |
| Prepared by | J. Kutscher |
| Approved by | Head of Divisional Engineering |
| Endorsed by | - |
| Authorized by | J. Kutscher |
| Area of application | Approved internal entities |

## Record of Revisions

| Version | Brief description of change | Date |
| --- | --- | --- |
| 1.0 | Initial Version | 2024-12-10 |

Purpose: Defines binding implementation rules for governance structure, platform ownership, adoption, control baseline management, waiver handling, and compliance reporting.
# DevSecOps Directive

## Purpose

This Directive defines the governance structure, operational responsibilities, and implementation framework required to enforce the DevSecOps Policy across the enterprise.

It ensures that DevSecOps is implemented consistently across divisions and programs while maintaining alignment with cybersecurity, safety, and regulatory requirements.

It establishes:

- governance and decision authority,
- mandatory adoption rules,
- control baseline management,
- waiver and deviation management,
- reporting and compliance mechanisms.

## Role In The Governance Stack

The directive answers the question: **how the policy must be executed in practice**.

Compared with the Policy, the Directive is intentionally more procedural. It is the document that governance boards, quality owners, and delivery teams use when a control is not met and an explicit decision is required.

## Scope

This Directive applies to:

- all programs developing software within SDD-relevant systems,
- all divisions responsible for software engineering,
- all DevSecOps platforms and software factories,
- all security domains and operational environments,
- both internal development and externally sourced software integrated into enterprise systems.

## Strategic Authority

### Chief Digitalisation Officer (CDO)

The CDO is the enterprise owner of DevSecOps and is responsible for:

- establishing DevSecOps as the enterprise software delivery model,
- providing and funding enterprise DevSecOps platform capabilities,
- defining enterprise adoption timelines and maturity targets,
- integrating safety lifecycle requirements into DevSecOps,
- reporting DevSecOps maturity to executive management.

### Cyber Security Function (CSCSO)

The security function is responsible for:

- defining mandatory cybersecurity control baselines,
- defining vulnerability management requirements and SLAs,
- classifying security domains,
- accepting cybersecurity risk associated with deviations,
- conducting cybersecurity compliance audits.

The CSCSO holds veto authority regarding reductions of mandatory cybersecurity controls.

### Safety Authority

The Safety Authority within the CDO organization is responsible for:

- defining mandatory safety lifecycle requirements,
- determining safety impact classifications,
- approving deviations affecting safety-critical systems,
- ensuring safety evidence generation within DevSecOps processes.

## DevSecOps Governance Board

### Establishment

A DevSecOps Governance Board shall be established to coordinate enterprise-wide DevSecOps implementation.

The Board operates as the primary technical governance body for DevSecOps.

### Composition

The Board should include:

- Head of SDD Capabilities as chair,
- representative of the CSCSO organization,
- representative of the Safety Authority,
- SDD Enterprise Architect,
- representatives from major divisions or programs,
- compliance representative where applicable.

### Responsibilities

The DevSecOps Governance Board is responsible for:

- maintaining the DevSecOps control baseline structure,
- approving DevSecOps standards and technical baselines,
- defining enterprise DevSecOps maturity levels,
- evaluating waiver requests within delegated authority,
- monitoring enterprise adoption and maturity progress,
- coordinating domain-specific DevSecOps implementations.

### Escalation

The Board escalates decisions to:

- the CSCSO for high-risk cybersecurity matters,
- the Safety Authority for safety-critical deviations,
- the CDO for enterprise-level governance conflicts.

## DevSecOps Platform Governance

### Platform Ownership

Enterprise DevSecOps platform capabilities shall be operated under the responsibility of the DevSecOps Platform Lead within the CDO organization. This includes both on-premises and cloud-based platforms.

The Platform Lead is responsible for:

- maintaining approved pipeline blueprints,
- implementing enterprise control baselines,
- providing secure artifact repositories,
- implementing evidence generation mechanisms,
- managing platform lifecycle and upgrades.

### Domain Platform Variants

Where required by security or operational constraints, domain-specific DevSecOps platform variants may be established, including:

- air-gapped environments,
- classified system environments,
- restricted operational networks.

All domain platforms must comply with enterprise DevSecOps Standards.

## Mandatory Adoption Rules

### New Programs

All programs initiated after entry into force of the Policy shall implement DevSecOps in accordance with enterprise Standards.

DevSecOps adoption shall be considered during program approval processes.

### Existing Programs

Existing programs shall establish a DevSecOps transition roadmap aligned with enterprise maturity targets.

Transition timelines shall be defined by the DevSecOps Governance Board.

## Control Baseline Management

Mandatory DevSecOps control baselines shall be defined in DevSecOps Standards.

The control baseline shall include requirements covering:

- cybersecurity,
- safety,
- software supply chain integrity,
- artifact integrity and signing,
- traceability and evidence,
- operational monitoring and lifecycle management.

Programs must implement the applicable control baseline based on:

- security domain,
- system criticality,
- operational environment.

## Waiver And Deviation Management

### Waiver Principles

Deviations from mandatory requirements are permitted only when:

- technical or regulatory justification exists,
- risk classification is documented,
- compensating controls are defined,
- the approving authority and named approver are documented,
- an approval date is documented,
- expiry dates are defined.

All waivers must be documented in a centralized waiver registry.

Each approved waiver record shall at minimum contain:

- a unique waiver identifier,
- the affected scope or object,
- the affected requirements,
- the written justification,
- compensating controls or compensating measures,
- approval authority,
- named approver,
- approval date,
- expiry date,
- current status.

### Waiver Authority

Approval authority shall follow the risk classification:

- low or medium risk: DevSecOps Governance Board,
- high cybersecurity risk: CSCSO,
- high safety risk: Safety Authority,
- critical risk: CDO and CSCSO jointly.

## Reporting And Compliance Monitoring

The DevSecOps Governance Board shall establish enterprise reporting covering:

- platform adoption rates,
- DevSecOps maturity distribution across programs,
- open waivers by risk category,
- vulnerability remediation performance,
- compliance audit findings.

Reporting shall be provided periodically to the CDO and relevant governance bodies.

## Relationship To Standards, Processes, And Guidelines

This Directive is implemented through supporting documents such as:

- DevSecOps Standards including the Control Baseline Standard, Platform Architecture Standard, and related supply chain, artifact integrity, and evidence standards,
- DevSecOps Processes including waiver management, platform onboarding, and maturity assessment,
- DevSecOps Guidelines including pipeline blueprint usage, secure coding practices, and SBOM management guidance.

## Entry Into Force

This Directive enters into force upon approval and remains valid until superseded or revoked.

## Structured Mapping

This directive is represented in `model/documents/governance-documents.yaml` and traced to controls in `model/traceability/document-to-control.yaml`.
## Entry Into Force

Upon approval

## Repository Source

Rendered from `docs/governance/devsecops-directive.md` using `scripts/render_governance_documents.py`.
