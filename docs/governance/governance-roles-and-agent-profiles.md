# Governance Roles And Agent Profiles

## Purpose

This document defines role profiles for humans and AI agents working in this repository.

These profiles are the governance source of truth. The model-neutral implementation lives under `.agents/`, and Codex-specific adapters live under `.codex/` and `.github/codex/`.

The profiles are decision and review lenses: each role knows what to inspect, which questions to ask, and when to escalate to another role.

## Operating Principle

Do not let one change silently mix source intake, policy interpretation, executable rule changes, release packaging and demo presentation.

Use these profiles to decide:

- which files to read first
- which review questions matter
- whether a pull request is documentation-only, report-only, blocking, or release-impacting
- which validation commands must run
- whether a new baseline or release candidate is needed

## Role Summary

| Role | Primary responsibility | Typical trigger |
|---|---|---|
| Source Document Intake Agent | Register and classify incoming source documents | New or updated file under `docs/governance/source-documents/` |
| Governance Analyst Agent | Translate governance intent into structured requirements | Source document review or change request |
| Architecture Runtime Governance Agent | Maintain architecture markers, gates, policies and baselines | Changes under `architecture/` or architecture OPA |
| DevSecOps Baseline Agent | Maintain control baseline, platform mapping and evidence model | Changes under `model/controls/`, `model/platform/`, `pipeline-baseline/` |
| Policy-as-Code Agent | Maintain executable OPA rules and enforcement behavior | Changes under `policies/opa/` or workflow enforcement |
| Evidence And Intake Agent | Maintain downstream evidence, result intake, indexes and viewer | Changes under `status/`, `generated/viewer/`, app workflows |
| Release Manager Agent | Decide release candidate versus baseline release | Changes under `releases/`, reusable workflows, schemas, policies |
| Demo Readiness Agent | Keep demo runbooks, viewer and ha-CPsWMS story consistent | Demo docs, current-main reports, viewer changes |
| Repo Steward Agent | Protect repo hygiene, validation and safe commit discipline | Every change |

## Source Document Intake Agent

Primary files:

```text
docs/governance/source-documents/
model/documents/source-document-register.yaml
docs/governance/change-requests/
generated/reports/source-lineage-report.md
generated/reports/governance-change-impact.md
generated/reports/source-document-intake-status.md
generated/reports/source-document-intake-review-briefs.md
generated/reports/source-document-requirement-delta.md
```

Responsibilities:

- Register every incoming source document.
- Apply full Source Document Intake only to documents under `docs/governance/source-documents/` or source-document register changes.
- Use `candidate` when a new document may duplicate or replace an existing source.
- Use `candidate_replacement_for` and `similarity_assessment` for possible replacements.
- Prepare decision-support review briefs for candidate, draft and replacement items.
- Prepare requirement-level delta evidence for likely replacement candidates.
- Ensure a change request exists when documents are added, replaced or promoted.
- Do not derive controls, markers, policies or baselines from a candidate before review.
- Do not autonomously promote, retire, supersede or approve source documents.

Review questions:

- Does this change actually touch `docs/governance/source-documents/` or `model/documents/source-document-register.yaml`?
- Is this source new, a possible duplicate, or a replacement candidate?
- Does it supersede an existing source document?
- Is the status correct: `candidate`, `draft`, `intake`, `review`, `approved`, `superseded`, or `retired`?
- Is a change request needed?
- Is lineage required yet?
- Which human decision is required, and which options should be presented?
- Which requirements appear added, changed, removed or equivalent?

Validation:

```bash
python3 scripts/generate_source_document_intake_status.py
python3 scripts/generate_source_document_intake_review_briefs.py
python3 scripts/generate_source_document_requirement_delta.py
python3 scripts/generate_governance_change_impact_report.py
python3 scripts/validate_governance_repo.py
```

## Governance Analyst Agent

Primary files:

```text
docs/governance/
model/documents/
model/traceability/
model/controls/
architecture/
generated/reports/governance-change-impact.md
```

Responsibilities:

- Interpret source-document intent.
- Identify affected controls, architecture markers, guardrails, evidence and reviews.
- Separate explanatory documentation from executable governance behavior.
- Record assumptions and unresolved decisions in a change request.

Review questions:

- What requirement or governance intent changed?
- Is the change normative, explanatory, or evidence-related?
- Which derived artifacts should change?
- Which artifacts must remain unchanged until review completes?

Validation:

```bash
python3 scripts/validate_governance_repo.py
python3 scripts/validate_runtime_governance.py
```

## Architecture Runtime Governance Agent

Primary files:

```text
architecture/
policies/opa/architecture_*.rego
schemas/architecture-release-candidate.schema.json
schemas/app-architecture-evidence.schema.json
docs/releases/architecture-baseline-l1-v0.1.0.md
releases/architecture/
```

Responsibilities:

- Maintain architecture levels, quality markers, guardrails and review gates.
- Keep architecture OPA policies aligned with the architecture source.
- Decide whether a source update changes runtime governance behavior.
- Protect the released architecture baseline from silent mutation.

Review questions:

- Does the change affect L1, L2, L3 or GOV architecture levels?
- Does it change marker thresholds or required evidence?
- Does it create findings for `ha-CPsWMS` current main?
- Is a new architecture baseline release needed?

Validation:

```bash
python3 scripts/validate_runtime_governance.py
python3 -m unittest discover -s tests
```

## DevSecOps Baseline Agent

Primary files:

```text
model/controls/
model/platform/
model/evidence/
model/traceability/
pipeline-baseline/
docs/releases/l1-baseline-v1.1.3.md
releases/l1/
```

Responsibilities:

- Maintain L1, L2, L3 and GOV controls.
- Maintain platform capability mapping and evidence expectations.
- Keep traceability complete from document to control and control to platform.
- Protect released DevSecOps baselines from silent mutation.

Review questions:

- Did control text, evidence type, maturity or automation change?
- Is a policy-as-code rule affected?
- Does the change alter downstream app evidence contracts?
- Is a patch, minor or major baseline release required?

Validation:

```bash
python3 scripts/validate_governance_repo.py
python3 -m unittest discover -s tests
```

## Policy-as-Code Agent

Primary files:

```text
policies/opa/
policies/example-input.release-candidate.json
demo/inputs/
scripts/generate_*governance_report.py
```

Responsibilities:

- Maintain executable OPA rules.
- Keep report-only and blocking semantics explicit.
- Ensure rules have representative inputs and tests.
- Avoid changing enforcement behavior without documentation and release review.

Review questions:

- Does the policy produce a finding, warning, or blocking failure?
- Is the finding actionable and traceable to evidence?
- Does this affect pull requests, mainline, manual runs, or all of them?
- Are waivers or exceptions handled correctly?

Validation:

```bash
opa check policies/opa
python3 scripts/validate_governance_repo.py
python3 scripts/validate_runtime_governance.py
python3 -m unittest discover -s tests
```

## Evidence And Intake Agent

Primary files:

```text
status/
scripts/intake_*github_actions_run.py
scripts/generate_*results_index.py
scripts/generate_status_viewer.py
generated/viewer/status-viewer.html
docs/operations/evidence/governance-result-intake-and-viewer-usage.md
```

Responsibilities:

- Maintain downstream result intake.
- Keep `mainline`, `branch`, `pull_request` and `manual` semantics distinct.
- Ensure the viewer shows official mainline state correctly.
- Keep PR checks separate from central mainline status unless explicit PR intake is added.

Review questions:

- Is this a PR result, branch result, manual diagnostic run, or mainline push?
- Should it update `latest_result`, or only history?
- Does it change viewer interpretation?
- Is `GH_RESULT_INTAKE_TOKEN` required?

Validation:

```bash
python3 scripts/generate_status_viewer.py
python3 scripts/validate_governance_repo.py
python3 -m unittest discover -s tests
```

## Release Manager Agent

Primary files:

```text
docs/releases/
releases/
.github/workflows/*baseline*
docs/releases/release-publication-checklist.md
docs/releases/release-and-migration-model.md
```

Responsibilities:

- Decide whether a change needs no release, a release candidate, or a baseline release.
- Maintain release metadata, checksums, release docs and workflow refs.
- Protect existing released baselines from untracked behavior changes.
- Make downstream migration impact explicit.

Review questions:

- Is this editorial, patch, minor, or major?
- Does downstream evidence shape change?
- Does a reusable workflow ref need a new tag?
- Have release docs and checksums been updated together?

Validation:

```bash
python3 scripts/validate_governance_repo.py
python3 scripts/validate_runtime_governance.py
python3 -m unittest discover -s tests
```

## Demo Readiness Agent

Primary files:

```text
docs/demos/demo-end-to-end-governance.md
docs/demos/demo-ha-cpswms-runtime-governance.md
docs/demos/ha-cpswms-architecture-governance-results.md
generated/viewer/status-viewer.html
generated/current-main/ha-cpswms/
status/
```

Responsibilities:

- Keep demo docs, viewer data and current-main results consistent.
- Preserve the distinction between demo artifacts and current-main artifacts.
- Ensure `ha-CPsWMS` mainline status is not confused with PR or branch runs.

Review questions:

- Does the demo still show DevSecOps and architecture end to end?
- Are run IDs, baselines, commits and generated timestamps current where they claim to be current?
- Does the viewer match status indexes?
- Are report-only and blocking semantics clear?

Validation:

```bash
python3 scripts/validate_runtime_governance.py
python3 scripts/validate_governance_repo.py
python3 -m unittest discover -s tests
```

## Repo Steward Agent

Primary files:

```text
AGENTS.md
docs/ai-index.md
docs/operations/ai-working-rules.md
.github/pull_request_template.md
.github/CODEOWNERS
```

Responsibilities:

- Keep changes focused.
- Prevent accidental `.DS_Store` commits.
- Ensure validation is run and reported.
- Ensure generated timestamp-only noise is not committed unless intentional.
- Ensure commits and pushes follow maintainer preference.

Review questions:

- Are unrelated files included?
- Are generated artifacts updated by scripts?
- Did validation run?
- Is the commit scope coherent?
- Are source-document, release and enforcement impacts clear?

Validation:

```bash
git status --short
git diff --check
python3 scripts/validate_runtime_governance.py
python3 scripts/validate_governance_repo.py
python3 -m unittest discover -s tests
```

## Review Routing Matrix

| Change type | Required roles |
|---|---|
| New source document | Source Document Intake Agent, Repo Steward Agent |
| Candidate replacement | Source Document Intake Agent, Governance Analyst Agent, affected domain agent |
| Architecture marker or gate change | Architecture Runtime Governance Agent, Policy-as-Code Agent, Release Manager Agent |
| DevSecOps control change | DevSecOps Baseline Agent, Governance Analyst Agent, Release Manager Agent |
| OPA policy change | Policy-as-Code Agent, affected domain agent, Release Manager Agent |
| Evidence schema change | Evidence And Intake Agent, affected domain agent, Release Manager Agent |
| Viewer or status index change | Evidence And Intake Agent, Demo Readiness Agent |
| Release package change | Release Manager Agent, affected domain agent, Repo Steward Agent |
| Demo-only documentation | Demo Readiness Agent, Repo Steward Agent |

## How To Use These Profiles In Practice

For each meaningful change, add a short role note in the change request or pull request:

```text
Roles involved:
- Source Document Intake Agent: candidate source registered.
- Architecture Runtime Governance Agent: no runtime derivation yet.
- Release Manager Agent: no release required.
- Repo Steward Agent: validation passed.
```

This keeps review lightweight while making the governance responsibility explicit.
