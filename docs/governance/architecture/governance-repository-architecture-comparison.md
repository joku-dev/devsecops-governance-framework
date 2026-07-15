# Governance Repository Architecture Comparison

| Field | Value |
|---|---|
| Document type | Architecture and operating model comparison |
| Status | Draft comparison document |
| Change type | Documentation-only |
| Intended audience | Enterprise Architecture, DevSecOps Governance, Platform Engineering, Security, Audit and Software Industrialisation stakeholders |
| Purpose | Compare the central governance repository architecture with a governance approach that does not use a central repository. |
| Intake classification | Explanatory architecture and operating model documentation; not a registered source document. |
| Governance behavior | Documentation-only; no controls, schemas, policies, releases or runtime behavior are derived from this document. |
| Baseline impact | None until a separate approved change request modifies controls, schemas, policies, releases or source-document registration. |

## Executive Summary

The central governance repository is an architectural pattern for making
software delivery governance repeatable, versioned, evidence-driven and
auditable.

The alternative is a non-repository governance model where policies, standards,
architecture guidance, evidence expectations, CI/CD logic and audit material
remain distributed across documents, wikis, ticket systems, local pipeline
templates and manual review processes.

Both models can exist in an organisation. The difference is industrialisation.
The repository model turns governance into a reusable operational system. The
non-repository model keeps governance primarily as a coordination and document
management activity.

The recommended architecture is the central governance repository model with
controlled source intake, versioned baseline releases, platform-neutral
evidence contracts, CI/CD adapters, policy-as-code where suitable, normalized
result intake and clear human decision rights.

## Comparison Scope

This document compares two operating models:

| Model | Meaning |
|---|---|
| Central governance repository | A versioned repository owns the reusable governance baseline, structured models, evidence contracts, schemas, policy-as-code, release packages, CI/CD adapter templates, generated reports and result intake model. |
| Governance without central repository | Governance remains distributed across document repositories, wikis, local project templates, tool-specific pipelines, manual review records and ad hoc evidence collection. |

This comparison does not create new governance requirements. It explains the
architectural trade-offs between two implementation approaches.

## Model A: Central Governance Repository

The central repository acts as a controlled governance execution and evidence
hub. It does not replace human authorities. It provides the reusable technical
and procedural backbone that allows those authorities to govern consistently.

Current architectural layers:

| Layer | Repository area | Responsibility |
|---|---|---|
| Source document layer | `docs/governance/source-documents/`, `model/documents/` | Registers authoritative source documents and candidate sources before derivation. |
| Structured model layer | `model/`, `architecture/`, `schemas/` | Represents controls, platform capabilities, evidence, waivers, traceability, architecture markers, guardrails and gates. |
| Policy execution layer | `policies/opa/`, validation scripts | Executes selected checks where evidence is objective enough. |
| CI/CD adapter layer | `pipeline-baseline/`, platform adapter docs | Lets GitHub Actions, Bamboo, Jenkins, GitLab or other platforms call the same governance core. |
| Release layer | `releases/`, `docs/releases/` | Publishes versioned baseline packages for downstream consumption. |
| Evidence and result layer | `status/`, generated reports, viewer | Stores normalized downstream results and presents status. |
| Documentation layer | `docs/` | Explains operating model, onboarding, adapter usage, release model and governance interpretation. |
| Agent support layer | `.agents/`, `.codex/`, tests | Supports review routing, intake support, release checks and repository stewardship. |

The central architecture can be summarized as:

```text
Source documents
  -> source intake and register
  -> structured governance and architecture models
  -> schemas, evidence contracts and policy-as-code
  -> released baseline packages
  -> CI/CD platform adapters
  -> downstream repository evidence
  -> normalized central result intake
  -> reports, viewer, audit and feedback
```

## Model B: Governance Without A Central Repository

In the alternative model, the organisation still has governance, but the
governance system is not represented as one reusable, versioned technical
baseline.

Typical components:

- policies and standards in document systems
- architecture guidance in separate architecture repositories or wikis
- project-specific CI/CD templates
- local scanner configuration per team
- evidence stored in pipeline artifacts, tickets, review notes or shared drives
- audit preparation through manual collection
- waiver and exception records in separate tools
- baseline interpretation by individual reviewers or project teams

The non-repository model can be summarized as:

```text
Policy, standards and architecture documents
  -> manual interpretation by teams
  -> local pipeline and evidence implementation
  -> local review and local evidence storage
  -> manual status consolidation
  -> audit preparation by collection and reconciliation
```

This model can work for small scope or early exploration. It becomes difficult
when many repositories, products, platforms, divisions and assurance
authorities must use the same baseline consistently.

## Architecture Comparison

| Concern | Central governance repository | Without central governance repository |
|---|---|---|
| Source of truth | Source documents and structured models are versioned and linked. | Source material is distributed across documents, wikis and team-local interpretations. |
| Baseline ownership | One baseline can be released, tagged and consumed by many repositories. | Each project often reconstructs or copies the baseline locally. |
| Change control | Changes are reviewed through change requests, validation and Git history. | Changes may happen through document updates, meetings or tool changes without one technical record. |
| Evidence model | Evidence contracts define comparable machine-readable input. | Evidence format varies by team, tool or reviewer. |
| CI/CD integration | Platform adapters call a shared governance core. | Governance logic is embedded in local pipelines. |
| Auditability | Git history, reports, release metadata and result snapshots provide traceability. | Audit evidence is collected manually and reconciled after the fact. |
| Release management | Baselines are versioned packages with release notes, metadata and checksums. | The effective baseline version can be unclear or document-version dependent. |
| Architecture governance | Markers, guardrails, gates and architecture evidence can be represented structurally. | Architecture governance remains mainly document and review-board driven. |
| Waivers and exceptions | Deviations can be linked to controls, evidence, owners, expiry and release decisions. | Deviations may be stored across tickets, emails or review notes. |
| Scaling | Improvements to the central baseline can benefit all consuming repositories. | Each team must adopt changes locally. |
| Platform diversity | GitHub, Bamboo, Jenkins or GitLab can map to the same normalized evidence model. | Each platform tends to create its own governance interpretation. |
| Operational visibility | Central result indexes and viewer provide current state. | Status requires manual consolidation or tool-specific dashboards. |

## Process Comparison

| Process area | With central governance repository | Without central governance repository |
|---|---|---|
| Source intake | Source documents are registered before derivation. | Source documents may be referenced informally or interpreted directly. |
| Baseline update | Change request, impact analysis, validation and release decision. | Document update, meeting decision or local implementation change. |
| Downstream onboarding | Teams consume a released baseline and evidence contract. | Teams receive guidance and implement their own controls. |
| CI/CD adoption | Teams use reusable workflows or platform adapters. | Teams create or adapt local pipeline logic. |
| Evidence production | Evidence is generated in expected formats. | Evidence is collected according to local process or tool output. |
| Result reporting | Results can be normalized into central status and viewer output. | Results are usually reported per project or per tool. |
| Waiver handling | Waivers can be validated, expired, reported and linked. | Waivers may be separate from pipeline and release evidence. |
| Architecture review | Architecture evidence can support gates and review decisions. | Reviews rely more heavily on documents and human inspection. |
| Audit preparation | Evidence and history are already structured. | Evidence collection often becomes a separate audit project. |

## Decision Matrix

| Decision question | Repository model is stronger when | Non-repository model may be sufficient when |
|---|---|---|
| How many repositories are in scope? | Many repositories or programs need the same baseline. | Only one or two teams are experimenting. |
| Is evidence comparability required? | Enterprise reporting, audit and portfolio visibility matter. | Evidence is reviewed only locally. |
| Are multiple CI/CD platforms used? | GitHub, Bamboo, Jenkins, GitLab or other tools coexist. | One team owns one simple pipeline. |
| Is baseline versioning important? | Teams must pin, migrate and audit baseline versions. | Governance guidance changes rarely and informally. |
| Is architecture runtime governance in scope? | Architecture evidence, markers and gates should be visible in delivery. | Architecture review remains fully manual. |
| Are waivers and exceptions recurring? | Deviations must be tracked, expired, reported and improved. | Deviations are rare and handled case by case. |
| Is audit reconstruction important? | The organisation must prove which controls applied at a point in time. | Audit relies on manual review and interviews. |
| Is software industrialisation a target? | Repeatability, reuse and scaling are explicit goals. | The organisation is still exploring its operating model. |

## Strengths Of The Central Repository Model

- It creates one reusable governance baseline instead of many local variants.
- It makes governance data versionable, reviewable and testable.
- It separates source documents from derived runtime behavior.
- It supports controlled baseline releases and migration.
- It lets downstream teams produce comparable evidence.
- It allows platform adapters without copying governance logic into each tool.
- It supports audit with Git history, release packages, reports and evidence.
- It gives Enterprise Architecture a bridge from intent to delivery evidence.
- It makes recurring findings visible as improvement signals.

## Risks Of The Central Repository Model

The repository model also introduces responsibilities:

- the repository itself must be governed and validated
- released baselines must not be changed silently
- downstream teams need onboarding guidance
- platform adapters need maintenance
- evidence contracts must stay realistic
- report-only and blocking behavior must remain explicit
- source-document intake must prevent premature derivation

These are manageable risks, but they require ownership. The repository should
therefore be treated as a governed platform capability, not as a loose
documentation folder.

## Strengths Of The Non-Repository Model

The non-repository model has advantages in limited contexts:

- lower initial tooling investment
- fewer repository-maintenance responsibilities
- easier early drafting in document-centric organisations
- flexible local interpretation during exploration
- no need to maintain shared adapters or schemas

These strengths are strongest before enterprise rollout begins. They become
weaker once repeatability, auditability and multi-repository adoption matter.

## Risks Of The Non-Repository Model

Common risks:

- local interpretation drift
- duplicated pipeline logic
- inconsistent evidence
- unclear baseline versions
- difficult audit reconstruction
- weak traceability from source documents to delivery behavior
- hard-to-scale waiver and exception handling
- limited visibility across repositories and platforms
- improvements do not automatically benefit other teams

The risk is not that governance disappears. The risk is that governance remains
too manual and local to industrialise.

## Recommended Architecture

Use the central governance repository as the enterprise baseline hub.

Recommended operating pattern:

1. Keep authoritative source documents under `docs/governance/source-documents/`.
2. Register source documents before derivation.
3. Represent approved intent in structured models.
4. Release stable baseline packages for downstream teams.
5. Let CI/CD platforms call the shared governance core through adapters.
6. Require downstream repositories to produce normalized evidence.
7. Intake accepted mainline results into central status when needed.
8. Keep report-only and blocking behavior explicit.
9. Treat waivers and exceptions as controlled deviations.
10. Feed recurring findings back into baseline, architecture and platform improvement.

## When Not To Use The Repository As The Primary Mechanism

Do not force every governance activity into the repository.

The repository should not replace:

- human architecture authority
- CISO or safety risk decisions
- product ownership
- business release decisions
- local remediation work
- enterprise funding and rollout decisions
- formal document approval systems where they remain legally authoritative

The repository should make those decisions easier to evidence, compare and
operate. It should not pretend to be the authority for everything.

## Boundary With Source Document Intake

This comparison document is not a source document.

Full Source Document Intake applies only to documents under
`docs/governance/source-documents/` or documents intentionally being introduced
there.

This document is a non-source explanatory comparison. It may inform architecture
and management discussions, but it does not authorize changes to controls,
architecture markers, OPA policies, schemas, evidence contracts, workflows,
release packages or baselines.

## Conclusion

The central governance repository model is the stronger architecture for
software industrialisation because it turns governance into a reusable,
versioned and evidence-producing system.

The non-repository model is simpler at the beginning, but it scales poorly when
many teams, platforms, products and assurance authorities must work from the
same baseline.

The target architecture should therefore use the governance repository as the
operational baseline hub while preserving human decision rights and formal
source-document authority.
