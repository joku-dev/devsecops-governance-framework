# Roadmap

## Current State

The original MVP roadmap has largely been completed for the current DevSecOps L1/L2/L3/GOV model and the first Architecture L1 runtime governance baseline.

Current validated state:

- `46` DevSecOps controls are represented in structured YAML.
- `46` control-to-platform traceability mappings exist.
- DevSecOps L1 is released as `l1-baseline-v1.1.3`.
- Architecture L1 runtime governance is released as `architecture-baseline-l1-v0.1.0`.
- The `ha-CPsWMS` mainline demo is green for DevSecOps and architecture runtime governance.
- Source lineage, governance change impact, architecture source replacement assessment, result indexes and the status viewer exist.

This roadmap therefore tracks the next professionalization steps, not the initial migration.

## Step 1: Review Architecture Source Replacement

Manually review the likely architecture source replacement candidate identified in:

- `generated/reports/architecture-source-replacement-assessment.md`

If replacement is confirmed, update source register status, lineage, architecture YAML `source_document` fields and release planning together.

## Step 2: Onboard A Second Repository

Repeat the `ha-CPsWMS` onboarding and result-intake pattern for another repository.

This should prove that the governance baseline, evidence contract, result intake and viewer are reusable beyond the current demo target.

## Step 3: Harden Result Integrity

Strengthen revision protection for stored downstream results:

- append-only result handling
- per-result digests
- manifest generation
- clearer intake rules for milestone, branch, manual and release-relevant runs

## Step 4: Review Verification Requirements

Review verification requirements with Security, Quality, Platform Owner, Architecture and program representatives.

The review should confirm that each verification requirement is technically checkable, audit-relevant and does not weaken the original normative requirement.

## Step 5: Decide Enforcement Progression

Keep the current demo report-only unless explicitly changed.

After at least one additional repository is onboarded, decide which DevSecOps and architecture checks should remain report-only and which should become blocking gates in consuming workflows.

## Step 6: Decide Long-Term Source-Of-Truth Model

Decide whether YAML becomes the formal master source or remains synchronized with an external BMS/document management system.
