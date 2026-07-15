# Governance Change Request

## Summary

- Add a documentation-only integration model connecting the ADO architecture document set with DevSecOps-as-Code.
- Clarify how architecture intent, DevSecOps controls, evidence contracts, platform automation and review decisions form one closed governance system.
- Add a controlled deviation model that separates Architecture Exceptions from Governance Waivers while keeping them traceable where both apply.
- Preserve existing decision rights and avoid changes to controls, schemas, OPA policies, release packages or source-document registration.

## Change ID

```text
GCR-2026-002
```

## Source Document Intake

| Question | Answer |
|---|---|
| Full source-document intake required? | no |
| New or updated source document? | no |
| Source document path | not applicable |
| Reviewed non-source path | `docs/governance/ado-devsecops-integrated-governance-model.md` |
| Intake classification | explanatory governance alignment documentation |
| Register updated? | no |
| Supersedes existing source? | no |
| Possible duplicate or replacement candidate? | no |
| Similarity assessment | not_relevant |
| Source status | not applicable |

## Non-Source Change Classification

This change is outside full Source Document Intake because it does not add or
update a file under `docs/governance/source-documents/` and does not update the
source document register.

Classification decision:

- The document is accepted as explanatory governance alignment documentation.
- The document is not a normative source document.
- The document does not belong under `docs/governance/source-documents/`.
- The source document register remains unchanged.
- The document connects existing ADO and DevSecOps-as-Code concepts; it does
  not introduce new authoritative governance requirements by itself.
- No controls, architecture markers, policies, schemas, evidence contracts,
  workflows, releases or baselines may be derived from this document without a
  separate approved governance change request.
- Runtime governance behavior remains unchanged.

Classification record references:

- `docs/governance/ado-devsecops-integrated-governance-model.md`
- `docs/governance/change-requests/GCR-2026-002-ado-devsecops-integrated-governance-model.md`
- `docs/operations/source-document-intake-process.md`
- `model/documents/source-document-register.yaml`

## Why This Change Is Needed

The ADO architecture document set and the DevSecOps-as-Code governance model are closely related, but they can appear like separate governance worlds unless their roles, translation points and feedback loops are made explicit.

This change creates a safe integration document that explains how ADO defines governed architecture intent and how DevSecOps-as-Code makes selected expectations executable, evidence-based, reportable and auditable.

It also clarifies that Architecture Exceptions and Governance Waivers are related forms of controlled deviation, but they have different purposes and authorities.

The goal is to provide a shared working basis for the Enterprise Architect and the Enterprise DevSecOps Governance & Software Industrialisation Lead without changing executable governance behavior.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | None. |
| DevSecOps controls | None. |
| Platform model | None. |
| Architecture governance | Documentation alignment only. No marker, gate or guardrail changes. |
| OPA policies | None. |
| Schemas and evidence contracts | None. |
| Viewer, status indexes or intake | None. |
| Release package or baseline | None. |
| Downstream repositories | None. |

## Replacement Review

Skipped because this change does not add or update a source document.

| Existing source ID | Similarity | Notes |
|---|---|---|
| not applicable | unknown | This is not a source-document replacement. |

Decision:

- [ ] New independent source
- [ ] Possible duplicate, keep as candidate
- [ ] Replacement candidate, review required
- [ ] Replacement confirmed
- [ ] Not relevant, retire candidate
- [x] Not a source-document replacement review item

Replacement notes:

- The new document is an integration operating model, not an authoritative replacement for ADO source documents or DevSecOps source documents.
- No candidate source exists and no retirement action is required.

## Derived Artifacts

- `docs/governance/ado-devsecops-integrated-governance-model.md`
- `mkdocs.yml` navigation entry
- `docs/official-entrypoints.md` entry
- `docs/ai-index.md` orientation entry

## Governance Behavior

Choose one:

- [x] Documentation-only
- [ ] Report-only governance behavior
- [ ] Blocking governance behavior
- [ ] Release packaging only

Notes:

- The change explicitly states that no controls, schemas, policies or release behavior are derived directly from the integration document.

## Release Decision

Choose one:

- [x] No release required
- [ ] Release candidate required
- [ ] Patch baseline release required
- [ ] Minor baseline release required
- [ ] Major baseline release required

Release notes:

- No baseline release is required because this is a documentation-only alignment artifact.

## Validation Plan

Confirm what must pass before merge.

- [x] `python3 scripts/validate_runtime_governance.py`
- [x] `python3 scripts/validate_governance_repo.py`
- [x] `python3 -m unittest discover -s tests`
- [ ] Source lineage regenerated or confirmed unchanged
- [ ] Viewer regenerated if status or presentation changed
- [ ] Downstream example checked if consumer behavior changed

For this documentation-only change, repository validation is sufficient unless reviewers request the full suite.

MkDocs build validation was attempted with `python3 -m mkdocs build --strict`, but the local environment does not have the `mkdocs` module installed.

## Reviewer Notes

- Review whether the model accurately preserves ADO architecture decision rights.
- Review whether the DevSecOps-as-Code translation model is clear enough to support future traceability work.
- Confirm that the document does not imply immediate enforcement, baseline or schema changes.
