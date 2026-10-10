# GCR-2026-149: Governance Requirement Lifecycle Viewer

## Summary

Add a read-only, source-linked view in Governance Workspace that traces the
registered governance source through the structured requirement case, human
decision, effective Requirement-to-Artifact mapping, and OPA policy inventory.
The view is generated from the source register, lifecycle case files, the
effective artifact register, and repository policy files.

The presentation distinguishes decisions from implementation mappings, and
policy mappings from OPA validation and runtime enforcement. No current OPA
validation snapshot is stored in the viewer data; this is shown as unrecorded.

## Artifact intake classification

| Field | Value |
|---|---|
| Artifact name | Governance Requirement Lifecycle Viewer |
| Artifact type | Read-only viewer behavior and generated presentation data |
| Target paths | `scripts/lib/governance_requirement_lifecycle_view.py`, `scripts/lib/viewer_app.py`, `apps/governance-viewer/`, `scripts/generate_status_viewer.py`, generated viewer outputs, this request, viewer guide, function catalog, technical function inventory, MkDocs navigation |
| Owner | Governance Platform / Evidence and Intake |
| Source Document Intake required? | No; the view consumes already registered sources and approved lifecycle decisions. Candidate sources remain visibly unapproved. |
| Evidence contract impact | None; no evidence is created or reclassified. |
| Runtime governance impact | None; read-only projection only. No OPA rules, workflow gates, or enforcement modes change. |
| Release impact | None; no baseline or release package changes. |
| Validation required | Regenerate viewer, inspect computed lifecycle counts and generated output, run repository validation, and review documentation navigation. |

## Scope

- Show source registration and intake status, lifecycle case coverage, proposal
  decision counts, activations, effective mappings, and OPA mapping counts.
- Link the displayed stages to their source files and the Golden Path planning
  workpackage where applicable.
- Keep missing lifecycle cases and missing validation data explicit rather than
  treating them as completed or empty states.
- Replace the ambiguous `Migrated` label in the fallback viewer with `Decided`.

## Out of scope

- Creating or changing requirement decisions, lifecycle cases, controls,
  platform capabilities, effective mappings, evidence contracts, OPA policies,
  tests, enforcement, workflows, releases, or baselines.
- Claiming that an effective mapping proves deployment in a program.
- Claiming that an OPA policy file or mapping proves a current successful check
  or runtime enforcement.
- Deriving from source documents in `candidate` or `review` status.

## Governance intent

- [x] Read-only viewer/reporting change
- [ ] Report-only runtime behavior change
- [ ] Blocking behavior
- [ ] Baseline or release change

## Validation record

- [x] Regenerate `generated/viewer/` from the repository sources.
- [x] Check the projected source, decision, mapping, and OPA counts against the
  model inputs.
- [x] Run `git diff --check` and review generated-output scope.
- [x] Run repository governance validation; `scripts/validate_governance_repo.py`
  passed. Strict MkDocs build also passed.
