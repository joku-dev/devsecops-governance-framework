# Source Document Intake Review Operating Model

## Purpose

This operating model defines how the Source Document Intake Agent supports
human intake reviews for architecture and DevSecOps governance source
documents.

Full Source Document Intake review applies only to documents under
`docs/governance/source-documents/` or documents intentionally being introduced
there as source documents.

This document is explanatory governance process documentation. It is not a
registered source document and does not authorize controls, architecture
markers, policies, schemas, workflows, releases or baselines by itself.

The model connects ADO architecture source material and DevSecOps-as-Code in
one controlled review flow. It keeps the repository safe by separating review
support from governance decisions and by preventing unreviewed candidate
documents from changing runtime governance.

## Operating Principles

- ADO architecture documents and DevSecOps source documents are reviewed as one
  governance system.
- The Intake Agent prepares evidence, options, and review packets, but does not
  approve, promote, supersede, or retire source documents.
- Candidate documents remain non-deriving until a human review decision is
  recorded in a governance change request.
- Requirement deltas are used to make architectural and DevSecOps impact
  visible before controls, markers, policies, schemas, or releases change.
- Documentation-only, report-only, blocking, and release-impacting changes stay
  explicitly separated.

## Review Scope

The full Source Document Intake review model applies when one of these inputs
changes:

- a file under `docs/governance/source-documents/`
- the source document register under `model/documents/source-document-register.yaml`
- ADO architecture source material that may replace or extend an existing
  architecture governance source and is introduced under
  `docs/governance/source-documents/`
- DevSecOps policy, directive, platform reference or control baseline source
  material introduced under `docs/governance/source-documents/`

A governance change request outside these conditions does not by itself trigger
full Source Document Intake. It may record a non-source classification, impact
analysis and release decision, but the source document register remains
unchanged.

It also applies when a downstream pipeline, such as Bitbucket/Bamboo, needs to
prove that only reviewed sources influenced generated governance behavior.

## Review Roles

| Role | Responsibility |
|---|---|
| Source Document Intake Agent | Classifies sources, prepares review briefs, prepares requirement deltas, and checks derivation guardrails. |
| Enterprise Architect | Confirms ADO architecture intent, replacement decisions, and architecture authority. |
| Governance Owner | Confirms whether the change affects policy, directive, operating model, or governance ownership. |
| DevSecOps Baseline Owner | Confirms control, platform, evidence, and pipeline-baseline impact. |
| Architecture Runtime Governance Owner | Confirms marker, guardrail, review-gate, schema, and architecture policy impact. |
| Release Manager | Confirms whether a baseline release, release candidate, or no release is required. |
| Repo Steward | Confirms repository hygiene, validation, lineage, and safe commit scope. |

The same person may hold more than one human role, but the review record should
show which review lens was applied.

## Agent Outputs

The Intake Agent prepares these review inputs:

- source classification: new, duplicate, replacement candidate, superseding
  source, or retired source
- status recommendation: `candidate`, `draft`, `intake`, `review`,
  `approved`, `superseded`, or `retired`
- review brief with decision options
- requirement-level delta for likely replacements
- change-request fields that still need human confirmation
- derivation guardrail status
- validation commands and observed validation results

The primary reports are:

- `generated/reports/source-document-intake-status.md`
- `generated/reports/source-document-intake-review-briefs.md`
- `generated/reports/source-document-requirement-delta.md`
- `generated/reports/governance-change-impact.md`
- `generated/reports/architecture-source-replacement-assessment.md`

## Intake Review Packet

Every formal intake review should be based on an intake review packet. The
packet is not a new generated artifact yet; it is the agreed set of inputs the
reviewer reads before making a decision.

Required packet contents:

- changed source document paths
- source document register diff
- relevant governance change request
- intake status report
- intake review brief
- requirement delta for replacement candidates
- change impact report
- architecture replacement assessment when ADO architecture sources are
  involved
- validation results

Recommended packet contents:

- affected controls, markers, gates, policies, schemas, or release packages
- expected downstream consumer impact
- proposed release decision
- open questions for the Enterprise Architect or Governance Owner

## Review Flow

### 1. Register

Every incoming source document must be registered before it can influence
derived governance artifacts.

For uncertain, overlapping, or replacement-looking documents, use:

- `status: candidate`
- `candidate_replacement_for` when there is a likely existing target
- `similarity_assessment` when the relationship is known enough to classify

### 2. Classify

The Intake Agent classifies the source as one of:

- new independent source
- possible duplicate
- replacement candidate
- superseding source
- retired source
- draft source needing authority confirmation

The classification is evidence for review, not the final decision.

### 3. Prepare Review Evidence

The reviewer generates or refreshes:

```bash
python3 scripts/generate_source_document_intake_status.py
python3 scripts/generate_source_document_intake_review_briefs.py
python3 scripts/generate_source_document_requirement_delta.py
python3 scripts/generate_governance_change_impact_report.py
```

When ADO architecture source material is involved, also refresh:

```bash
python3 scripts/generate_architecture_source_replacement_assessment.py
```

### 4. Hold Human Review

The human reviewer confirms:

- source authority
- relationship to existing sources
- replacement or coexistence decision
- impact on architecture governance and DevSecOps-as-Code
- required derived artifacts
- release decision
- unresolved assumptions

The Enterprise Architect should decide architecture intent and replacement
meaning. The Governance Owner should decide governance adoption and operating
model impact.

### 5. Record Decision

The decision is recorded in a governance change request. The change request
must state whether the change is:

- documentation-only
- report-only governance behavior
- blocking governance behavior
- release packaging only

It must also state whether a release is required.

### 6. Derive Only After Approval

Controls, markers, policies, schemas, workflows, templates, releases, or
baseline packages may only be derived from the source after the review decision
allows it.

Candidate material may be discussed, compared, and reported, but must not be
used as the normative source for executable governance behavior.

### 7. Validate

Before merge or commit, run the relevant validation set:

```bash
python3 scripts/validate_runtime_governance.py
python3 scripts/validate_governance_repo.py
python3 -m unittest discover -s tests
```

For documentation-only changes, the same validation is preferred because this
repository tightly links documentation, reports, and source lineage.

## Decision Model

| Decision | Meaning | Allowed next step |
|---|---|---|
| Keep as candidate | The document is known, but not accepted for derivation. | Continue review, update packet, no runtime derivation. |
| New independent source | The document adds a new accepted source area. | Update register and lineage, then derive only approved artifacts. |
| Related source | The document supports an existing source but does not replace it. | Link relationship, keep source boundaries explicit. |
| Replacement candidate | The document may replace an existing source, but the decision is not final. | Keep candidate status and prepare requirement delta. |
| Replacement confirmed | The human reviewer confirms replacement. | Update register, lineage, derived artifacts, and release decision. |
| Superseded | The old source remains historical and is replaced for new derivation. | Preserve history and derive only from the accepted successor. |
| Retired | The source is no longer used for new derivation. | Preserve history and prevent new derivation. |

## ADO And DevSecOps Alignment

The review should make these relationships explicit:

- ADO architecture source documents define architecture intent, review gates,
  quality markers, and architecture evidence expectations.
- DevSecOps source documents define policy, directive, control, platform,
  evidence, and pipeline-baseline expectations.
- Shared topics such as evidence, risk, quality gates, waivers, exceptions, and
  release decisions must have one agreed review path.
- If ADO architecture wording changes a DevSecOps control expectation, that
  impact must be visible in the change request before any baseline changes.
- If DevSecOps evidence or pipeline behavior changes architecture review
  semantics, the Enterprise Architect should review the effect before release.

The target state is not two parallel governance systems. It is one source
intake and review flow with two expert lenses: architecture and DevSecOps.

## Bitbucket And Bamboo Integration

For Bitbucket/Bamboo adoption, the recommended first step is to run the intake
review generators in report-only mode when source documents or the register
change.

The Bamboo plan should:

- run the intake status generator
- run the intake review brief generator
- run the requirement delta generator for replacement candidates
- run repository validation
- publish the reports as build artifacts
- avoid blocking deployments until the review process is accepted by the human
  owners

Blocking behavior may be introduced later only for narrow safety cases, such
as deriving runtime governance from a candidate source before review.

## Review Checklist

Use this checklist before accepting an intake decision:

- [ ] Incoming source document is registered.
- [ ] Candidate, draft, intake, review, approved, superseded, or retired status
      is deliberate.
- [ ] Possible duplicate or replacement relationship is documented.
- [ ] Intake review brief exists.
- [ ] Requirement delta exists for likely replacements.
- [ ] Architecture impact is reviewed by the Enterprise Architect when ADO
      sources are involved.
- [ ] DevSecOps control, platform, evidence, and pipeline impact is reviewed
      when DevSecOps behavior may change.
- [ ] Change request records the human decision.
- [ ] No candidate source has been used to derive controls, markers, policies,
      schemas, workflows, templates, releases, or baselines before review.
- [ ] Release decision is explicit.
- [ ] Validation results are recorded.

## Non-Goals

- no autonomous approval by an agent
- no silent source replacement
- no automatic source promotion
- no direct change to released baselines
- no new blocking gates from this operating model alone
- no duplicate ADO and DevSecOps review boards for the same source decision
