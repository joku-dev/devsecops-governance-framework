# Software Industrialisation Problem And Capability Map

| Field | Value |
|---|---|
| Document type | Strategic capability map |
| Status | Draft alignment document |
| Change type | Documentation-only |
| Intended audience | Enterprise Architecture, DevSecOps Governance, Platform, Security, Audit and Software Industrialisation stakeholders |
| Purpose | Explain which software industrialisation problems this repository addresses and which repository capabilities provide the answer. |
| Intake classification | Explanatory governance documentation; not a registered source document. |
| Governance behavior | Documentation-only; no controls, schemas, policies, releases or runtime behavior are derived from this document. |
| Baseline impact | None until a separate approved change request modifies controls, schemas, policies, releases or source-document registration. |

## Executive Summary

Software industrialisation fails when every product team interprets governance,
architecture, evidence, security, release and platform expectations locally.
The result is not only technical variation. It is organisational variation:
different pipelines, different evidence, different exception handling, different
release readiness criteria and different audit narratives.

This repository is the answer to that problem space. It turns governance from a
document-only discipline into a versioned, evidence-driven, reusable and
auditable operating capability.

The core capability is not a single tool. The repository provides an integrated
governance system:

- source-document intake and lineage
- structured DevSecOps and architecture governance models
- machine-readable evidence contracts
- policy-as-code rules where automation is suitable
- CI/CD platform adapters
- versioned baseline releases
- normalized downstream result intake
- status reporting and viewer output
- waiver, exception and controlled-deviation handling
- agent-assisted review support with human decision rights

The industrialisation value is repeatability. A product team should not have to
reinvent what "compliant", "release-ready", "architecture-ready" or
"evidence-complete" means. The repository defines those expectations centrally,
packages them as reusable baselines and lets downstream teams produce evidence
against the same model.

## The Problem Space

### 1. Governance Exists As Documents, But Delivery Happens In Pipelines

Traditional governance often stops at policy, directive, standards and review
documents. Delivery teams work in repositories, pipelines, artifacts, scans and
release workflows. When these worlds are not connected, governance becomes
manual interpretation after the fact.

Typical symptoms:

- standards are known but not executable
- evidence is collected manually and late
- each project interprets the same requirement differently
- audit preparation depends on interviews and document searches
- delivery teams see governance as external overhead

### 2. Architecture And DevSecOps Drift Apart

Architecture governance and DevSecOps governance often evolve as separate
systems. Architecture defines intent, guardrails and quality expectations.
DevSecOps defines controls, evidence, pipeline behavior and security gates.

When these systems are disconnected:

- architecture decisions do not become operational evidence expectations
- pipeline gates are not traceable to architecture intent
- release readiness is assessed differently by different authorities
- exceptions and waivers become parallel routes for unmanaged deviations
- Enterprise Architecture cannot easily see how its intent is executed

### 3. Product Teams Rebuild The Same Governance Logic Locally

Without a central reusable baseline, each application repository or platform
team tends to copy, simplify, fork or reinterpret governance logic.

Typical symptoms:

- local CI/CD templates diverge
- control logic is duplicated in pipelines
- scanner, SBOM, artifact and approval evidence vary by team
- fixes made in one repository do not improve the enterprise baseline
- platform migration requires governance logic to be rewritten

### 4. Evidence Is Not Comparable Across Repositories

Industrialisation needs comparable signals. If every repository produces a
different evidence shape, the organisation cannot reliably answer which teams
are ready, which controls are covered, which findings recur and which platforms
need investment.

Typical symptoms:

- evidence is stored in different formats and locations
- audit evidence cannot be aggregated
- dashboard data is incomplete or inconsistent
- control coverage is unclear
- findings cannot be trended across products

### 5. Release Baselines Are Not Treated As Products

Governance requirements change over time. If the baseline is not packaged,
versioned and migration-managed, downstream teams cannot know which version they
are consuming or whether an update is safe.

Typical symptoms:

- teams consume `main` instead of a stable baseline
- baseline changes surprise downstream repositories
- no clear release notes or migration path exist
- controls, schemas and workflows mutate without release discipline
- audit cannot reconstruct which rules applied at a point in time

### 6. Exceptions, Waivers And Risk Acceptance Are Too Informal

Industrialised delivery does not mean every rule is always met immediately. It
means deviations are visible, owned, justified, time-bounded and reviewed by the
correct authority.

Typical symptoms:

- waivers are hidden in emails or tickets
- architecture exceptions are not linked to governance waivers
- expiry dates and compensating controls are missing
- repeated deviations do not feed back into platform or baseline improvement
- risk acceptance authority is unclear

### 7. Platform Diversity Breaks Governance Consistency

Organisations rarely have only one CI/CD platform. GitHub Actions, Bitbucket,
Bamboo, Jenkins and GitLab may coexist. If governance is tied to one platform,
industrialisation stops at the first platform boundary.

Typical symptoms:

- governance logic is embedded in platform-specific YAML
- moving from GitHub to Bamboo requires a redesign
- platform metadata is not normalized
- result intake is platform-specific
- teams argue about tool syntax instead of governance outcomes

### 8. Reviews Do Not Scale Without Decision Support

Human decision rights remain essential, but reviews do not scale when every
reviewer must manually inspect source documents, deltas, derived artifacts,
pipeline evidence and release impact from scratch.

Typical symptoms:

- architecture and governance reviews are slow
- source-document replacements are risky
- review packets are inconsistent
- candidate sources influence derived artifacts too early
- decisions are hard to reconstruct later

## The Capability Space

The repository answers the problem space through a set of connected
capabilities. Each capability has a specific industrialisation role.

## Capability Map

| Industrialisation problem | Repository capability | Primary repository areas | Industrialisation outcome |
|---|---|---|---|
| Governance remains document-only | Structured governance model | `model/`, `architecture/`, `schemas/` | Governance becomes machine-readable and reviewable. |
| Source intent is unclear or changes silently | Source intake and lineage | `model/documents/`, `docs/governance/source-documents/`, generated lineage and intake reports | Source changes are visible before derivation. |
| ADO architecture and DevSecOps drift apart | Integrated ADO and DevSecOps model | `docs/governance/architecture/ado-devsecops-integrated-governance-model.md`, `architecture/`, `model/controls/` | Architecture intent and DevSecOps execution share one governance chain. |
| Teams produce inconsistent evidence | Evidence contract | `schemas/governance-run-input.schema.json`, `model/evidence/`, `docs/operations/evidence/governance-evidence-contract.md` | Evidence becomes comparable across repositories. |
| Controls are interpreted locally | Versioned control baseline | `model/controls/`, `releases/l1/` | Teams consume the same approved baseline. |
| Architecture readiness is subjective | Architecture runtime governance | `architecture/`, `policies/opa/architecture_*.rego`, `releases/architecture/` | Architecture markers, guardrails and review gates become structured. |
| Pipeline governance is copied per tool | CI/CD adapter model | `pipeline-baseline/`, `docs/operations/adapters/cicd-platform-adapter-strategy.md` | Tool-specific adapters call one shared governance core. |
| Results cannot be aggregated | Normalized result intake | `status/`, `scripts/intake_*`, `generated/viewer/` | Downstream outcomes become centrally visible and auditable. |
| Baseline changes are unsafe | Release packaging | `releases/`, `docs/releases/` | Downstream teams pin stable versions and migrate deliberately. |
| Deviations are unmanaged | Waiver and controlled deviation model | `model/waivers/`, `docs/operations/processes/waiver-management-standard.md`, integrated ADO/DevSecOps model | Deviations become visible, owned and time-bounded. |
| Reviews do not scale | Agent-assisted review support | `.agents/`, `docs/operations/processes/source-document-intake-review-operating-model.md`, generated review briefs | Agents prepare evidence; humans keep decision rights. |
| Repository quality is fragile | Validation and regression suite | `scripts/validate_*`, `tests/` | Governance changes are checked before commit and release. |

## Capability 1: Controlled Source Intake And Lineage

The repository treats source documents as controlled inputs, not as casual file
attachments. New or changed source material is registered, classified and
reviewed before it drives derived governance behavior.

Relevant capabilities:

- source document register
- candidate status for uncertain or replacement-looking sources
- intake status report
- review briefs
- requirement-level deltas
- source lineage report
- governance change requests

Industrialisation effect:

- prevents silent replacement of standards
- makes ADO and DevSecOps source changes reviewable
- protects released baselines from uncontrolled mutation
- gives Enterprise Architecture and Governance one shared intake path

## Capability 2: Structured Governance Model

The repository translates approved governance intent into structured data:
controls, platform capabilities, evidence types, waivers, traceability,
architecture markers, guardrails and review gates.

Relevant capabilities:

- `model/controls/`
- `model/platform/`
- `model/evidence/`
- `model/traceability/`
- `model/waivers/`
- `architecture/`
- JSON schemas under `schemas/`

Industrialisation effect:

- governance becomes testable and versionable
- documents, reports and policy rules can be generated from shared data
- the organisation can reason about coverage and impact
- downstream teams receive consistent expectations

## Capability 3: Evidence Contracts

Software industrialisation requires repeatable evidence. The repository defines
what downstream repositories should produce so that governance results can be
evaluated consistently.

Relevant capabilities:

- governance run input schema
- evidence type model
- pipeline evidence generation
- architecture evidence package
- control evaluation report
- run-context-aware evaluation

Industrialisation effect:

- evidence is produced during delivery, not reconstructed later
- repositories become comparable
- pull request, branch, manual and mainline runs can be interpreted correctly
- audit preparation becomes evidence-driven

## Capability 4: Policy-As-Code Where Suitable

Not every governance expectation should become an automated gate. The
repository uses policy-as-code only where the required evidence is objective
enough for machine evaluation.

Relevant capabilities:

- OPA/Rego rules
- policy candidate mapping
- report-only and blocking mode distinction
- example inputs
- validation scripts and tests

Industrialisation effect:

- repeatable checks replace repeated manual inspection where appropriate
- governance findings become visible early
- blocking behavior can be introduced deliberately
- decision rights stay separate from automation

## Capability 5: Architecture Runtime Governance

The repository does not limit governance-as-code to security controls. It also
models architecture readiness, quality markers, guardrails, review gates and
remediation actions.

Relevant capabilities:

- architecture levels
- architecture quality markers
- guardrails
- review gates
- architecture OPA policies
- architecture release package
- architecture evidence flow

Industrialisation effect:

- architecture intent becomes operationally visible
- architecture review can use structured evidence
- ADO architecture guidance and DevSecOps evidence can be aligned
- product and solution readiness can be assessed more consistently

## Capability 6: Reusable CI/CD Platform Adapters

The governance core is designed to be platform-neutral. Platform adapters own
tool syntax and variable mapping, while the repository keeps the shared
governance logic in one place.

Relevant capabilities:

- GitHub Actions reference path
- Bamboo 12.1.9 YAML Specs starter templates
- Bitbucket adapter guidance
- Jenkins and GitLab adapter strategy
- normalized platform context
- shared scripts and schemas

Industrialisation effect:

- governance logic is not copied into every platform
- platform migration does not change the control model
- Bamboo, Bitbucket, Jenkins or GitHub can publish comparable evidence
- platform teams implement adapters while governance stays central

## Capability 7: Released Baseline Packages

The repository treats governance baselines as versioned products. Released
packages contain stable snapshots of models, workflows, schemas, policies,
examples, metadata and checksums.

Relevant capabilities:

- DevSecOps L1 baseline releases
- Architecture L1 baseline release
- release metadata
- release statements
- checksums
- downstream usage examples
- release and migration model

Industrialisation effect:

- application teams can pin known versions
- change impact becomes visible before rollout
- audit can reconstruct which baseline applied
- baseline evolution becomes an intentional product lifecycle

## Capability 8: Central Result Intake And Viewer

The repository can normalize downstream run results and summarize them in a
central status model and static viewer.

Relevant capabilities:

- result snapshots under `status/`
- repository and architecture result indexes
- intake scripts
- mainline, branch and manual result semantics
- generated status viewer

Industrialisation effect:

- enterprise status is based on accepted evidence
- mainline state is separated from temporary PR or diagnostic runs
- downstream progress becomes visible
- recurring findings can feed baseline, platform or architecture improvement

## Capability 9: Controlled Deviations

Industrialised governance must handle reality without losing control. The
repository separates architecture exceptions from governance waivers while
placing both under the broader idea of controlled deviations.

Relevant capabilities:

- waiver authority model
- waiver example
- waiver management standard
- integrated ADO and DevSecOps controlled deviation model
- review and release impact documentation

Industrialisation effect:

- deviations are explicit instead of hidden
- risk ownership is visible
- temporary acceptance gets expiry and mitigation
- recurring deviations become improvement signals

## Capability 10: Agent-Assisted Governance Work

The repository includes model-neutral agent roles and skills. These agents help
prepare review evidence, route work and protect repository safety, while human
roles retain decision rights.

Relevant capabilities:

- source document intake agent
- governance analyst agent
- architecture runtime governance agent
- DevSecOps baseline agent
- policy-as-code agent
- evidence and intake agent
- release manager agent
- repo steward agent
- deterministic routing tests

Industrialisation effect:

- reviews become more repeatable
- decision packets are easier to prepare
- source-document changes are less likely to bypass review
- repository safety rules are easier to apply consistently

## End-To-End Industrialisation Chain

The repository supports this target chain:

```text
Policy, directive, ADO architecture and standards
  -> controlled source intake and lineage
  -> structured governance and architecture model
  -> controls, markers, gates and evidence contracts
  -> platform-neutral governance core
  -> CI/CD platform adapters
  -> downstream repository evidence
  -> policy-as-code and report generation
  -> normalized result intake
  -> central status, audit evidence and feedback
  -> baseline, platform or architecture improvement
```

This chain is the practical industrialisation mechanism. It makes governance
repeatable without removing architecture, security, safety, platform or
business decision rights.

## Current Proven State

The repository already demonstrates an operational L1 capability:

- a released DevSecOps L1 baseline exists
- a released Architecture L1 baseline exists
- a reference downstream application repository has consumed the baseline
- GitHub Actions integration has been proven end to end
- central result intake and viewer semantics exist
- Bamboo/Bitbucket integration guidance and Bamboo 12.1.9 templates exist
- source-document intake review support exists
- validation and tests protect repository consistency

This means the repository is not only conceptual. It is already usable as the
central baseline and evidence model for a controlled rollout.

## What The Repository Solves

The repository solves these industrialisation needs:

- one controlled place for governance-as-code source data
- one review path for ADO and DevSecOps source alignment
- one evidence contract for downstream repositories
- one reusable baseline release model
- one platform-neutral governance core
- one normalized result intake model
- one visible status and reporting layer
- one controlled deviation vocabulary
- one validation discipline for governance changes

## What The Repository Does Not Solve Alone

The repository is an enabling system, not the whole operating organisation.
These topics still require people, mandate and platform execution:

- enterprise adoption decision and funding
- formal approval of source documents and baselines
- rollout planning across divisions and programs
- scanner, artifact signing and platform hardening implementation
- CISO, safety and architecture risk decisions
- remediation in application repositories
- operational support for CI/CD platforms
- audit acceptance of the final evidence model

The repository makes these decisions evidence-based and repeatable. It does not
replace the authorities that must make them.

## Recommended Use In An Architecture Or Management Discussion

Use this document as the bridge between the industrial problem and the
repository answer.

Recommended narrative:

1. The problem is not missing tools; it is uncontrolled variation in how teams
   interpret and prove governance.
2. The repository creates a central, versioned, evidence-driven governance
   baseline.
3. ADO architecture and DevSecOps-as-Code become one closed governance system:
   architecture defines intent, DevSecOps-as-Code operationalizes selected
   expectations, and teams produce evidence.
4. Platform adapters let the same governance core run on different CI/CD
   systems.
5. Released baselines and normalized results make adoption auditable and
   scalable.
6. Human authorities keep decision rights; automation provides evidence,
   findings and consistency.

## Professionalisation Roadmap

The next maturity steps are:

- expand real scanner integration beyond placeholder evidence
- harden Bamboo/Bitbucket result intake and platform metadata mapping
- introduce stronger artifact signing and provenance checks for higher maturity
- define portfolio-level adoption reporting across multiple repositories
- mature waiver and architecture exception records into one controlled
  deviation registry
- promote selected report-only checks into blocking checks only after ownership,
  evidence quality and remediation paths are accepted
- continue aligning ADO architecture source changes with DevSecOps baseline
  evolution through source-document intake review

## Closing Statement

Software industrialisation requires more than automation. It requires a
repeatable operating system for governance, evidence, architecture, platform
execution, release baselines and feedback.

This repository provides that operating system. It makes governance executable
where automation is appropriate, reviewable where human judgment is required
and reusable where teams need consistent delivery support.
