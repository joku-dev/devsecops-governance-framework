# How To Update Baseline Input Documents

## Purpose

This guide explains the official maintenance flow when the baseline input documents change.

Baseline input documents are the upstream governance sources such as:

- Policy
- Directive
- approved management decisions
- platform or operating model constraints that are explicitly adopted into governance

The key principle is:

- do not start with generated artifacts
- always start with the governing source documents and then propagate the change through the repository model

## When To Use This Guide

Use this guide when:

- a policy statement changes
- a directive introduces a new mandatory requirement
- an existing requirement is clarified or split
- a role or responsibility changes
- a verification method changes
- a previously manual requirement becomes technically automatable

## Change Flow Overview

Use this order:

1. update the source governance document
2. identify affected requirements
3. update controls
4. update traceability
5. update verification and evidence expectations
6. update generated and release-facing artifacts
7. validate the repository
8. publish a new baseline release if downstream repos are affected

## Step 1: Update The Source Document

Update the authoritative document first:

- `docs/governance/devsecops-policy.md`
- `docs/governance/devsecops-directive.md`

If you also maintain imported working sources, align them under:

- `docs/governance/source-documents/`

## Step 2: Identify The Governance Impact

Ask these questions for every changed paragraph:

- does it create a new requirement
- does it change an existing requirement
- does it remove a requirement
- does it only clarify wording without changing meaning
- does it change who is responsible
- does it change how compliance is verified

## Step 3: Update Controls

Controls are the machine-readable baseline requirements.

Update the affected control definitions in:

- `controls/`

Typical mapping rules:

- new requirement -> add a new control
- changed requirement -> update the existing control text, metadata, or evidence references
- removed requirement -> deprecate or remove the control carefully

## Step 4: Update Traceability

After controls change, update the traceability model in:

- `traceability/document-to-control.yaml`

Every relevant Policy or Directive statement should end up in one of these states:

- mapped to a control
- intentionally marked as governance-only
- intentionally marked as not yet implemented with a documented gap

## Step 5: Update Verification Logic

The next question is whether the changed requirement should be:

- automated as code
- evaluated from structured evidence
- reviewed manually

Relevant implementation areas are:

- `policies/opa/`
- `scripts/control_evaluation.py`
- `model/evidence/`
- `schemas/governance-run-input.schema.json`

## Step 6: Update Evidence Expectations

If the change requires new machine-readable proof, update:

- `docs/operations/evidence/governance-evidence-contract.md`
- `docs/examples/governance-run-input.example.json`
- `schemas/governance-run-input.schema.json`

## Step 7: Update Release-Facing Artifacts

If the change affects downstream repositories, prepare release-facing updates:

- update release documentation under `docs/releases/`
- update or prepare versioned release packages under `releases/`
- update reusable workflows if consumer integration changes

## Step 8: Regenerate Derived Artifacts

Run the repository generation steps so that rendered and operational artifacts match the new source of truth.

Typical commands:

```bash
python3 scripts/generate_traceability_csv.py
python3 scripts/generate_source_document_intake_status.py
python3 scripts/generate_source_document_intake_review_briefs.py
python3 scripts/generate_source_document_requirement_delta.py
python3 scripts/generate_repository_results_index.py
python3 scripts/generate_status_viewer.py
```

## Step 9: Validate The Repository

Run:

```bash
python3 scripts/validate_governance_repo.py
python3 -m unittest discover -s tests
```

## Step 10: Decide Whether A New Release Is Needed

Use this release rule:

- patch release -> editorial clarifications, no operational behavior change
- minor release -> new controls, new evidence fields, additional verification logic
- major release -> breaking changes for downstream consumers

## Worked Example

Example change:

- the Directive now requires release approval records to identify the approver role

Repository changes:

1. update the Directive wording
2. update the affected control to require explicit approval metadata
3. update `traceability/document-to-control.yaml`
4. update `schemas/governance-run-input.schema.json`
5. update `docs/examples/governance-run-input.example.json`
6. update `scripts/control_evaluation.py` if control evaluation becomes stricter
7. validate the repo
8. publish a new minor release if downstream repos must now provide the new field

## Maintainer Checklist

- source document updated
- control catalog updated
- traceability updated
- verification logic updated where needed
- evidence contract updated where needed
- release documentation updated where needed
- generated artifacts refreshed
- validation and tests passed

## Related Documents

- `docs/governance/policy-directive-baseline-verification-and-governance-as-code-explained.md`
- `docs/operations/evidence/governance-evidence-contract.md`
- `docs/operations/evidence/governance-result-intake-and-viewer-usage.md`
- `docs/operations/processes/source-document-intake-process.md`
- `docs/releases/release-and-migration-model.md`
