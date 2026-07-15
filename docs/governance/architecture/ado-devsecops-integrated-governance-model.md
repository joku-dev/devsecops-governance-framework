# ADO And DevSecOps-as-Code Integrated Governance Model

| Field | Value |
|---|---|
| Document type | Integration operating model |
| Status | Draft alignment document |
| Change type | Documentation-only |
| Intended owners | Enterprise Architect and Enterprise DevSecOps Governance & Software Industrialisation Lead |
| Purpose | Explain how the ADO architecture document set and DevSecOps-as-Code form one closed governance system. |
| Baseline impact | None until a separate approved change request modifies controls, schemas, policies, releases or source-document registration. |

## Core Statement

The ADO architecture document set defines the governed architecture intent for Software-Defined Defence. DevSecOps-as-Code operationalizes the approved intent through versioned requirements, controls, evidence contracts, CI/CD integration, platform automation, reports and auditable decision support.

The combined model is one governance system with connected but separate decision rights:

- ADO defines what good architecture means.
- DevSecOps-as-Code defines how selected expectations become executable, evidence-based and reportable.
- Platform capabilities make execution repeatable.
- Product and application teams produce evidence.
- Architecture, cybersecurity, safety, governance and executive authorities retain their decision rights.

Automation supports accountable decisions. It does not replace them.

## Scope

This document aligns the ADO architecture governance model with the DevSecOps-as-Code governance operating model. It is intended to make both topics appear and operate as one coherent system.

In scope:

- architecture guardrails, quality markers, review gates and exception logic from the ADO document set
- DevSecOps controls, evidence contracts, policy-as-code, CI/CD workflows and platform automation
- role alignment between architecture authorities and DevSecOps governance authorities
- traceability from source documents to evidence and review decisions
- joint review and feedback loops

Out of scope:

- changing approved source-document content
- changing released baselines
- changing OPA enforcement behavior
- changing schemas or evidence contracts
- assigning new formal decision rights without governance approval

## Source Inputs

The integrated model is based on the following source families:

| Source family | Repository location | Role in the integrated model |
|---|---|---|
| ADO architecture source documents | `docs/governance/source-documents/*ADO*.md` and `docs/governance/source-documents/ARCH-SDD-SRC-001.public.md` | Define architecture intent, BAPO alignment, architecture levels, quality markers, review logic, release readiness and exception governance. |
| DevSecOps policy and directive | `docs/governance/devsecops-policy.md`, `docs/governance/devsecops-directive.md` | Define DevSecOps mandate, governance structure, waiver logic and operating rules. |
| Structured DevSecOps controls | `model/controls/` | Represent executable or reviewable DevSecOps requirements by baseline level. |
| Structured architecture governance | `architecture/` | Represents architecture levels, guardrails, quality markers, review gates and remediation actions. |
| Policy-as-code and schemas | `policies/opa/`, `schemas/` | Execute selected governance checks against structured evidence. |
| Pipeline baseline and platform model | `pipeline-baseline/`, `model/platform/` | Provide reusable implementation patterns for downstream repositories and platform capabilities. |

## Closed Governance Chain

The intended end-to-end chain is:

```text
Business or mission need
  -> ADO architecture principle, guardrail or quality marker
  -> Governance requirement
  -> Control, marker, review gate or evidence expectation
  -> Evidence contract and CI/CD or platform implementation
  -> Product, solution or platform evidence
  -> Architecture, security, safety or DevSecOps review decision
  -> Exception, waiver, remediation or release-readiness outcome
  -> Feedback into ADO guardrails and DevSecOps baseline evolution
```

This chain is the practical link between architecture governance and DevSecOps-as-Code. It prevents architecture from remaining an intention and prevents automation from becoming disconnected from architecture authority.

## Translation Model

ADO concepts should be translated into DevSecOps-as-Code artifacts only through explicit review. The translation should be traceable and proportionate.

| ADO element | DevSecOps-as-Code representation | Typical evidence | Decision boundary |
|---|---|---|---|
| Architecture principle | Governance requirement or architecture guardrail | Source reference, rationale, affected scope | Enterprise Architecture owns architecture intent. |
| Architecture guardrail | Control, architecture guardrail, review gate or policy candidate | Guardrail mapping, control mapping, exception rule | Architecture Board / Design Authority approves architecture meaning. |
| Quality marker | Evidence expectation, scoring rule or review criterion | Architecture evidence, pipeline evidence, review record | Architecture authority defines marker meaning; governance-as-code implements evaluation support. |
| Review checklist | Human review input plus machine-readable evidence package | Checklist result, CI/CD result, evidence bundle | Reviews remain accountable decisions. |
| Release readiness criterion | Release gate, report-only check, evidence contract or readiness report | Product compatibility declaration, integration evidence, deployment evidence, security evidence | Release readiness requires verified evidence and authority review. |
| Architecture exception | Controlled deviation record, architecture exception or linked waiver where needed | Justification, risk, owner, mitigation, expiry | Architecture authority decides architecture acceptability; waiver authority decides temporary governance non-compliance. |
| Feedback finding | Remediation action, backlog item, baseline change request or guardrail update proposal | Finding, trend, recurring issue, improvement action | Feedback changes the baseline only through controlled change. |

The translation rule is simple:

> ADO provides the architecture reason. DevSecOps-as-Code provides the executable and auditable mechanism where automation is suitable.

## Integrated Role Model

The integrated role model should avoid duplicate governance structures. It should connect the ADO architecture roles with the DevSecOps-as-Code roles and clarify where each role contributes.

| ADO / architecture role | DevSecOps-as-Code counterpart | Joint responsibility | Boundary |
|---|---|---|---|
| Enterprise Architect | Enterprise DevSecOps Governance & Software Industrialisation Lead | Translate enterprise architecture guardrails into controlled governance requirements and baseline impact assessments. | Enterprise Architect owns architecture intent; DevSecOps Governance Lead owns governance-as-code operating model. |
| Architecture Review Board / Design Authority | DevSecOps Governance Board | Align architecture decisions, release readiness, baseline changes and exception handling. | Architecture Board decides architecture sufficiency; DevSecOps Board decides DevSecOps baseline lifecycle within mandate. |
| Solution Architect | Architecture Board / Design Authority and DevSecOps Governance Lead | Ensure solution baselines, integration evidence, compatibility checks and release-readiness evidence are connected. | Solution Architect assesses cross-product coherence; governance-as-code provides evidence and reporting support. |
| Product Architect | Application Team and Architecture Board / Design Authority | Define product architecture evidence, ADRs, deployment evidence, interface evidence and release compatibility evidence. | Product Architect owns product architecture coherence; application teams produce implementation and pipeline evidence. |
| Product Owner / Business Owner | Divisions, Programs and Application Repository Owner | Confirm business readiness, release intent, adoption priority and product-level accountability. | Business roles own value and release intent; they do not redefine mandatory governance controls locally. |
| Security Architect / CISO function | CISO / Cybersecurity Function and DevSecOps Governance Board | Align security guardrails, security evidence, scan expectations, risk acceptance and security waivers. | Cybersecurity authority retains security decision rights. |
| Safety Authority | Safety Authority and DevSecOps Governance Board | Align safety lifecycle expectations, safety-critical evidence and safety deviations with governance evidence. | Safety authority retains safety decision rights. |
| Data Architect / Data Owner | Architecture Board / Design Authority and Application Team | Define data contracts, semantic ownership, schema expectations and data evidence. | Data authority owns data meaning and ownership; teams produce implementation evidence. |
| Platform / DevSecOps Owner | DevSecOps Platform Lead / Platform Owner | Implement shared platform capabilities, CI/CD adapters, policy execution, evidence storage and platform IaC. | Platform Owner owns shared platform capability; application teams own product-specific code and evidence. |
| Audit / Compliance Reviewer | Audit and Compliance Reviewer | Review traceability, evidence sufficiency, waiver quality and reporting reliability. | Audit reviews assurance quality; it does not own product remediation or baseline design. |

## Joint Decision Rights

The integrated system depends on clear decision rights.

| Decision area | Primary authority | DevSecOps-as-Code contribution |
|---|---|---|
| Enterprise architecture guardrails | Enterprise Architect / Architecture Board | Traceability, candidate control mapping, impact analysis and adoption evidence. |
| Architecture quality markers | Architecture Board / Design Authority | Structured marker model, evidence requirements and readiness reports. |
| DevSecOps baseline lifecycle | DevSecOps Governance Board | Versioned controls, release notes, reusable workflows and downstream guidance. |
| Security risk acceptance | CISO / Cybersecurity Function | Security evidence, scan results, vulnerability findings and waiver traceability. |
| Safety-critical deviations | Safety Authority | Safety evidence references, exception visibility and escalation routing. |
| Platform capability implementation | DevSecOps Platform Lead / Platform Owner | Platform IaC, adapters, evidence storage, policy execution and drift reporting. |
| Product architecture evidence | Product Architect with Application Team | Evidence contract, pipeline artifacts, architecture evidence package and remediation status. |
| Solution release coherence | Solution Architect / Architecture Board | Product compatibility evidence, integration evidence and release-readiness reporting. |
| Waiver or exception approval | Authority based on risk classification | Completeness check, expiry, compensating controls and report visibility. |

## Controlled Deviation Model

Waivers and exceptions are closely related and should not become two unconnected paths for accepting the same deviation. The integrated model therefore uses `Controlled Deviation` as the common umbrella term.

| Controlled deviation type | Purpose | Typical trigger | Primary authority | Typical repository representation |
|---|---|---|---|---|
| Architecture Exception | A controlled deviation from architecture intent, guardrails, quality markers, solution baselines, interface rules, data rules, deployment rules or release compatibility expectations. | The proposed or implemented architecture intentionally differs from the ADO-defined expectation. | Architecture Board / Design Authority, with Security, Safety or Data authority where their domain is affected. | Architecture exception record, review result, risk or debt item, architecture remediation action. |
| Governance Waiver | A controlled, usually time-bound acceptance that a mandatory DevSecOps policy, control, evidence, pipeline, repository or platform requirement is not currently met. | The required governance-as-code expectation cannot be satisfied for a defined scope and period. | DevSecOps Governance Board or named Waiver Authority; CISO, Safety Authority or executive owner where risk requires it. | Waiver record, residual risk statement, compensating control decision, waiver registry entry. |

The distinction is:

```text
Architecture Exception = deviation from architectural intent or architecture baseline.
Governance Waiver     = temporary acceptance of unmet governance-as-code requirement.
```

An architecture exception can exist without a governance waiver when the architecture authority accepts an alternative design and no mandatory DevSecOps control is violated. A governance waiver can exist without an architecture exception when the architecture remains valid but required evidence, tooling, pipeline enforcement or repository configuration is temporarily missing.

Some cases require both. For example, a product may deviate from an approved interface versioning rule and that deviation may also cause a mandatory compatibility check to fail. In that case, the architecture exception explains whether the deviation is architecturally acceptable, while the governance waiver controls the temporary non-compliance with the DevSecOps-as-Code baseline.

The rule is:

> Do not use a waiver to silently approve architecture divergence, and do not use an architecture exception to silently bypass mandatory governance checks.

Every controlled deviation should contain at least:

| Field | Purpose |
|---|---|
| Deviation type | Identifies `architecture_exception`, `governance_waiver` or a linked pair. |
| Source expectation | Identifies the source document section, guardrail, quality marker, control, policy, evidence contract or review gate. |
| Affected scope | Defines product, solution, repository, platform, release, environment or program impact. |
| Reason | Explains why the expectation cannot or should not be met as written. |
| Risk classification | Makes security, safety, architecture, compliance and delivery risk visible. |
| Accountable owner | Names the person, role or body responsible for the deviation and its closure path. |
| Approving authority | Records the correct architecture, governance, security, safety or executive authority. |
| Compensating controls or mitigation | Describes temporary protection, workaround, remediation or risk reduction. |
| Expiry or review date | Prevents indefinite exceptions and open-ended waivers. |
| Linked evidence | Connects the deviation to architecture evidence, pipeline evidence, scan results, review records or release evidence. |
| Closure path | Defines remediation, baseline update, guardrail update, control update, permanent acceptance or retirement. |

The preferred lifecycle is:

```text
Deviation identified
  -> classify as architecture exception, governance waiver or linked pair
  -> identify source expectation and affected scope
  -> assess risk and domain authorities
  -> approve, reject or escalate
  -> record mitigation, expiry and owner
  -> reflect status in governance evidence and review reports
  -> close, renew, escalate or convert into baseline / guardrail change
```

Recurring controlled deviations are feedback. If the same exception or waiver appears repeatedly, the issue may be an unclear ADO guardrail, an unrealistic DevSecOps control, missing platform capability, insufficient architecture runway, or a real delivery risk that needs management action.

## Shared Taxonomy

Both document families should use a common vocabulary. The terms below should be treated as the preferred bridge vocabulary.

| Term | Integrated meaning |
|---|---|
| Architecture intent | The architecture meaning defined by ADO source documents, including principles, guardrails, quality markers and review expectations. |
| Governance requirement | A normalized requirement derived from approved source intent and suitable for traceability. |
| Control | A structured DevSecOps or architecture governance expectation that can be reviewed, evidenced or automated. |
| Quality marker | A reviewable architecture maturity expectation that connects an architecture claim to evidence. |
| Evidence contract | The machine-readable or structured definition of evidence expected from a repository, platform or review process. |
| Review gate | A defined decision point where evidence is assessed by the responsible authority. |
| Release readiness | A readiness state supported by verified evidence, compatibility information and authority review. |
| Controlled deviation | Umbrella term for a documented, risk-assessed and authority-approved deviation from an architecture or governance expectation. |
| Architecture exception | A controlled deviation from architecture expectations such as guardrails, baselines, quality markers or compatibility rules. |
| Governance waiver | A controlled, time-bound deviation from mandatory DevSecOps policy, control, evidence, pipeline, repository or platform requirements. |
| Baseline | A versioned set of approved controls, markers, workflows, policies or guidance used by downstream teams. |
| Feedback loop | The mechanism that turns findings, demos, incidents, exceptions and waivers into architecture or baseline improvement. |

## Traceability Spine

The shared traceability spine should allow a reviewer to answer these questions:

1. Which ADO source section or approved DevSecOps source document created the expectation?
2. Which governance requirement, control, marker or review gate represents it?
3. Which evidence is required and who must produce it?
4. Which pipeline, platform, repository or review process produced the evidence?
5. Which authority reviewed the result and what decision was made?
6. If the expectation was not met, which exception, waiver, risk, debt item or remediation action exists?
7. Which feedback path updates the architecture guardrail, DevSecOps baseline or platform capability?

The desired traceability pattern is:

```text
Source document
  -> Source section
  -> Governance requirement
  -> Control, marker or gate
  -> Evidence contract
  -> Evidence artifact
  -> Evaluation result
  -> Review decision
  -> Exception, waiver, remediation or feedback item
```

Traceability should be explicit. It should not depend on informal interpretation or hidden tool behavior.

## Joint Review Cadence

The integrated system should use a shared cadence so that ADO and DevSecOps-as-Code do not drift apart.

| Review | Purpose | Typical participants | Output |
|---|---|---|---|
| Architecture intent review | Confirm architecture meaning and scope of a guardrail, marker or checklist item. | Enterprise Architect, Solution Architect, Product Architect, Architecture Board | Approved architecture interpretation or requested clarification. |
| Baseline impact review | Decide whether approved intent should become a control, marker, evidence contract, workflow or policy candidate. | DevSecOps Governance Lead, DevSecOps Governance Board, Architecture Board, Platform Owner | Baseline impact decision and change request classification. |
| Evidence contract review | Confirm that required evidence is realistic, reviewable, machine-readable where useful and owned. | Architecture, Platform, Security, Application representatives | Evidence contract update or evidence guidance. |
| Platform implementation review | Confirm that shared CI/CD, scanner, repository, storage or policy execution capabilities can support the expectation. | Platform Owner, DevSecOps Governance Lead, Security, Architecture | Platform capability mapping, IaC task or adapter update. |
| Release readiness review | Assess product or solution evidence before release decisions. | Product Architect, Solution Architect, Product Owner, Architecture Board, Security, Platform | Release readiness result, actions, exceptions or escalation. |
| Exception and waiver review | Decide controlled deviations and residual risk. | Relevant authority based on risk, Governance Board, Architecture Board, Security, Safety | Approved, rejected or escalated exception or waiver. |
| Feedback and improvement review | Convert repeated findings into guardrail updates, platform runway, controls or process improvements. | Enterprise Architect, Governance Lead, Platform Owner, affected teams | Improvement backlog, change request or baseline proposal. |

## Operating Principles

The following principles keep the integrated system coherent and safe:

| Principle | Meaning |
|---|---|
| One governance system | ADO and DevSecOps-as-Code are two connected views of the same governance lifecycle. |
| Separate decision rights | Architecture, security, safety, platform, governance and executive authorities remain distinct. |
| Evidence over assertion | Architecture and DevSecOps claims should be supported by concrete, current and owned evidence. |
| Automation is decision support | Pipelines and policy-as-code produce evidence and findings; they do not replace accountable authorities. |
| No silent derivation | Source intent must not become controls, policies, schemas or release behavior without review. |
| Proportional automation | Only expectations suitable for automated or structured evaluation should become policy-as-code. |
| Explicit exception handling | Deviations must be documented, owned, risk-assessed, time-bounded and visible. |
| Feedback changes the system | Recurring findings should improve ADO guardrails, DevSecOps controls, evidence contracts or platform capabilities. |

## Repository Safety Rules

This document is intentionally safe for the governance repository because it does not change executable behavior.

Rules for future work:

- Do not derive new controls, OPA policies, schemas or release behavior directly from this document.
- Use a separate governance change request for every baseline-impacting change.
- Register new or replacement source documents through the source-document intake process before deriving artifacts.
- Treat ADO-derived controls or markers as candidates until architecture and governance review approve the translation.
- Keep report-only behavior unless a separate approved change enables blocking enforcement.
- Preserve source lineage when adding or changing requirements.
- Validate the repository before merging any follow-up that affects structured models, generated reports, schemas or policy behavior.

## Adoption Path

The integrated model should be introduced in stages.

| Stage | Objective | Safe output |
|---|---|---|
| 0. Alignment | Agree that ADO and DevSecOps-as-Code form one closed governance lifecycle. | This integration document and reviewer agreement. |
| 1. Role mapping | Make ADO roles and DevSecOps governance roles visible in one model. | Role mapping table and decision-right clarification. |
| 2. Traceability mapping | Connect selected ADO guardrails and quality markers to existing governance artifacts. | Mapping matrix without behavior change. |
| 3. Evidence alignment | Define which evidence proves selected ADO expectations. | Evidence contract candidates and review guidance. |
| 4. Controlled automation | Automate only suitable checks after review. | Policy candidates, report-only checks or baseline release candidates. |
| 5. Feedback maturity | Use findings, waivers and exceptions to improve both ADO and DevSecOps baselines. | Improvement backlog, guardrail updates or release proposals. |

## Recommended Next Artifacts

The following follow-up artifacts would strengthen the closed system without immediately changing enforcement behavior:

- ADO-to-DevSecOps traceability matrix
- ADO role to DevSecOps governance role mapping appendix
- Architecture guardrail to control candidate register
- Quality marker to evidence contract candidate register
- Joint review checklist for architecture intent and baseline impact
- Source-document intake review for any future ADO replacement or update

These should be added through normal governance change control if they affect structured models, baselines, schemas, policies or downstream repository behavior.
