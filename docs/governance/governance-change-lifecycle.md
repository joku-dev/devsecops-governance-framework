# Governance Change Lifecycle

## Purpose

This lifecycle defines how new or updated input documents become governed repository changes.

It is intentionally lightweight in version `0.1`: enough structure to make changes traceable and reviewable, without slowing down early repository development.

## Scope

Use this lifecycle for changes that affect:

- source documents under `docs/governance/source-documents/`
- DevSecOps controls
- architecture markers, levels, guardrails or gates
- OPA policies
- evidence contracts or schemas
- status intake and viewer behavior
- released baselines

Documentation-only changes may still use the pull request checklist, but usually do not need a full change request.

Before adding, moving or consuming a new artifact, classify it with:

```text
docs/operations/processes/new-artifact-intake-process.md
```

This first step decides whether the artifact belongs to Source Document Intake,
Evidence/Result Intake, examples, documentation, generated outputs, release
packages or another governed repository area.

## Lifecycle Overview

| Step | Purpose | Output |
|---|---|---|
| 0. Artifact classification | Classify any new artifact before it enters a governed area | Artifact intake classification in the change request |
| 1. Source intake | Register the new or updated input document when it is source material | `model/documents/source-document-register.yaml` |
| 2. Change request | Explain why the change exists and what it may affect | `docs/governance/change-requests/GCR-*.md` |
| 3. Impact analysis | Identify affected controls, markers, policies, schemas, releases and downstream repositories | Change request impact section or generated report |
| 4. Derived artifact update | Update controls, architecture models, policies, schemas, docs and generated outputs | Repository changes |
| 5. Pull request | Introduce the change through review | GitHub pull request |
| 6. Validation | Prove repository consistency | CI and local validation output |
| 7. Release decision | Decide whether a new baseline is required | No release, release candidate or baseline release |
| 8. Merge and publish | Make the change official | Merge commit, optional tag and release package |

## Step 1: Source Intake

All input documents must live under:

```text
docs/governance/source-documents/
```

Every input document must be registered in:

```text
model/documents/source-document-register.yaml
```

The register records:

- stable source ID
- title
- status
- source path
- owner
- version
- intake date
- governance domains
- derived artifact areas
- superseded source, if any

Allowed statuses:

| Status | Meaning |
|---|---|
| `candidate` | Source was received but has not yet been classified as new, duplicate or replacement. No lineage is required yet. |
| `draft` | Source exists but is not yet approved or fully derived. |
| `intake` | Source has been accepted into the repo for analysis and derivation. |
| `review` | Derived artifacts are under review. |
| `approved` | Source is approved for governed derivation. |
| `superseded` | Source was replaced by a newer source. |
| `retired` | Source is retained for history but no longer active. |

## Step 2: Change Request

Create a change request from:

```text
docs/governance/change-requests/TEMPLATE.md
```

Recommended filename:

```text
docs/governance/change-requests/GCR-YYYY-NNN-short-title.md
```

The change request should answer:

- What changed in the input document?
- Why does it matter?
- Is the document new, a possible duplicate, or a replacement candidate?
- Which controls, markers, policies, schemas, docs or releases may be affected?
- Is the change report-only or blocking?
- Is a new baseline release required?

## Replacement Candidates

When a new source document may match or replace an existing source document, register it as:

```yaml
status: candidate
candidate_replacement_for:
  - ARCH-SDD-SRC-001
similarity_assessment:
  assessment: replacement_candidate
  compared_to:
    - source_id: ARCH-SDD-SRC-001
      similarity: high
      notes: Same framework family with newer date or version.
```

Use `candidate` when the repository should remember the document but no derived controls, markers, policies or baselines should change yet.

After review:

| Decision | Register action |
|---|---|
| New independent source | Set new document to `intake`; keep `supersedes: null`. |
| Duplicate or not relevant | Set new document to `retired` and record notes. |
| Replacement confirmed | Set new document to `intake` with `supersedes: <old-id>`; set old document to `superseded` with `superseded_by: <new-id>`. |

Only after a replacement is confirmed should derived artifacts be moved to the new source document and the lineage report updated.

## Step 3: Impact Analysis

At v0.1, impact analysis may be written directly into the change request.
The repository also provides a lightweight generated impact report:

```bash
python3 scripts/generate_governance_change_impact_report.py
```

Generated outputs:

```text
generated/reports/governance-change-impact.md
generated/reports/governance-change-impact.json
```

Minimum impact categories:

| Area | Questions |
|---|---|
| Source documents | Which input documents are new, changed, superseded or retired? |
| DevSecOps controls | Are L1, L2, L3 or GOV controls added, changed or removed? |
| Architecture governance | Are markers, guardrails, gates, levels or remediations affected? |
| OPA policies | Does executable governance behavior change? |
| Schemas | Does downstream evidence shape change? |
| Viewer and intake | Does result interpretation or status rendering change? |
| Releases | Is a new baseline or release candidate needed? |
| Downstream repositories | Do consumers need migration work? |

Future versions may generate an impact report automatically.
The current report is register- and lineage-based. It does not infer semantic document deltas yet; it shows likely affected artifact areas, review lanes, validation commands and release considerations for each registered source document.

Generate the source-document intake status and review briefs when open candidate,
draft, or replacement decisions need preparation:

```bash
python3 scripts/generate_source_document_intake_status.py
python3 scripts/generate_source_document_intake_review_briefs.py
python3 scripts/generate_source_document_requirement_delta.py
```

The review briefs support human decision-making only. They must not promote,
retire, supersede, or approve source documents by themselves.

The requirement delta report supports replacement review by extracting
normative-looking statements from the candidate and target source documents and
classifying them as added, changed, removed, or equivalent. It is a review aid,
not a final architecture decision.

For architecture source replacement candidates, generate the architecture replacement assessment:

```bash
python3 scripts/generate_architecture_source_replacement_assessment.py
```

Generated outputs:

```text
generated/reports/architecture-source-replacement-assessment.md
generated/reports/architecture-source-replacement-assessment.json
```

This report supports review only. It must not change runtime governance behavior by itself.

## Step 4: Derived Artifact Update

Update derived artifacts in the correct layer:

| Change type | Typical files |
|---|---|
| DevSecOps control change | `model/controls/`, `model/traceability/`, `policies/opa/` |
| Platform change | `model/platform/`, `pipeline-baseline/`, `model/traceability/` |
| Architecture change | `architecture/`, `policies/opa/architecture_*.rego`, `schemas/architecture-*.json` |
| Evidence contract change | `model/evidence/`, `schemas/`, `docs/operations/evidence/governance-evidence-contract.md` |
| Viewer/status change | `scripts/generate_status_viewer.py`, `status/`, `generated/viewer/status-viewer.html` |
| Release change | `docs/releases/`, `releases/`, `.github/workflows/*baseline*` |

Preserve source-document lineage when adding new derived artifacts.

## Step 5: Pull Request

Governance behavior should enter the repository through pull requests.

The PR should include:

- source document update or reference
- source-document register update
- change request or impact explanation
- derived artifact changes
- validation evidence
- release decision
- report-only or blocking decision

## Step 6: Validation

Run:

```bash
python3 scripts/validate_runtime_governance.py
python3 scripts/validate_governance_repo.py
python3 -m unittest discover -s tests
```

The validator checks that registered source documents exist, live under the source-document root, and have lineage entries.

## Step 7: Release Decision

Not every change creates a release.

| Change | Release decision |
|---|---|
| Editorial documentation update | No release |
| Register or lineage cleanup | No release |
| Working model update with no downstream behavior change | No release or release candidate |
| Policy, schema or evidence behavior change | Release candidate recommended |
| Downstream reusable workflow or baseline package change | New baseline release required |

Versioning guidance:

| Release type | Use when |
|---|---|
| Patch | Bug fix or clarification that preserves intended behavior |
| Minor | Additive controls, markers, evidence or report-only checks |
| Major | Breaking evidence contract or enforcement change |

## Step 8: Merge And Publish

After merge:

- viewer and generated reports should reflect the merged state
- official entrypoints should link new major documents
- release docs and tags should exist if a new baseline was published
- downstream app repositories should be notified if migration is required

## Current v0.1 Controls

The repository currently enforces:

- source document register schema validation
- registered source paths must exist
- registered source paths must be under `docs/governance/source-documents/`
- every file under `docs/governance/source-documents/` must be registered
- every non-draft, non-candidate source document must have a source-lineage entry
- source-lineage report must have no missing derived artifacts
- governance change impact report must be generatable
- source-document intake status and review briefs must be generatable
- source-document requirement delta must be generatable for likely replacement candidates
- review briefs must not enable autonomous decisions or change runtime governance

This gives governance over the governance repository without requiring full automated semantic extraction from source documents yet.
