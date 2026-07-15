# DevSecOps Policy - Software Defined Defence (SDD)

## Purpose

This policy defines the mandatory DevSecOps foundations for the development, operation, and evolution of software in the context of Software Defined Defence within the Group.

It establishes that software-based defence capabilities must be delivered securely, reproducibly, auditably, and controllably across their full lifecycle.

## Role In The Governance Stack

The policy answers the question: **what is mandatory and who is accountable**.

It therefore sits above the more detailed governance artifacts:

- the DevSecOps Directive defines the binding execution and waiver workflow,
- the DevSecOps Control Baseline Standard defines the normative control requirements,
- the Platform Reference Architecture Standard defines the platform capabilities that enable those requirements.

## Scope

This policy applies to:

- all software components in SDD-relevant systems, products, and platforms,
- all organizational units across all divisions,
- all development, integration, deployment, and operational phases,
- all internally developed and externally sourced software integrated into company systems,
- all security domains, including classified and non-classified environments,
- IM developments with public customer-facing properties.

Exemptions apply only to non-security-relevant office IT applications and require formal justification and approval through the defined waiver process.

## Responsibilities

### Chief Digitalisation Officer (CDO)

The CDO is accountable for:

- enterprise-wide implementation of DevSecOps,
- establishment and funding of the DevSecOps platform capability,
- integration of safety requirements into the DevSecOps lifecycle,
- reporting adoption and maturity status to executive management.

### Cyber Security Function (CSCSO)

The CSCSO is accountable for:

- definition of mandatory cybersecurity control baselines,
- security domain classification,
- cybersecurity risk acceptance,
- approval of high-risk cybersecurity deviations,
- audit rights regarding cybersecurity compliance.

### Safety Authority

The responsible safety authority is accountable for:

- definition of mandatory safety-related lifecycle requirements,
- approval of safety-critical deviations,
- oversight of safety compliance within DevSecOps processes.

### DevSecOps Governance Board

The DevSecOps Governance Board shall:

- define and maintain mandatory standards,
- define maturity targets,
- evaluate and approve waivers within delegated authority,
- monitor enterprise-wide compliance.

### Divisions And Programs

Divisions and programs are accountable for:

- implementing DevSecOps requirements within their scope,
- using approved DevSecOps platforms,
- achieving defined maturity levels,
- reporting compliance status as required.

Failure to comply constitutes a policy violation.

## Fundamental Principles

### Security By Design And By Default

Cybersecurity controls shall be integrated into architecture, development, and operations and enforced prior to deployment.

### Safety Integration

Where applicable, safety requirements shall be integrated into the software lifecycle and supported by traceable and auditable evidence.

### Automation First

Security, safety, quality, and compliance controls shall be implemented through automated mechanisms wherever technically feasible.

Test automation shall provide project-defined coverage across requirements and shall be measured as a KPI.

Generic version-related documents such as release notes, certificates of conformance, and test reports should be generated automatically wherever feasible.

### Lifecycle Ownership

Responsible teams shall maintain accountability from code creation through operational deployment and evolution.

### Federated Execution Under Central Governance

Implementation may be decentralized across divisions and programs but shall operate within centrally defined governance, standards, and control baselines.

### Evidence-Based Compliance

Compliance evidence shall be generated automatically from approved development and operational pipelines.

## Policy Outcomes

This policy requires that:

- mandatory minimum requirements are defined in normative standards,
- maturity and applicability are governed centrally,
- deviations are controlled through a formal waiver process,
- compliance, reporting, and enforcement remain auditable.

The detailed execution of these outcomes is specified in the Directive and implemented in the structured control, evidence, and policy models of this repository.

## Structured Mapping

This policy is represented in `model/documents/governance-documents.yaml` and traced to controls in `model/traceability/document-to-control.yaml`.
