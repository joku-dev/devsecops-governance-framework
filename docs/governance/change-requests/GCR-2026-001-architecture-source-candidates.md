# Governance Change Request

## Summary

- Register five received SDD architecture documents as source-document candidates.
- Do not derive controls, architecture markers, policies, schemas, or baselines yet.
- Mark the R4R Architecture Governance Framework as a possible replacement candidate for the existing architecture governance framework source.
- Keep current runtime governance behavior unchanged.

## Change ID

```text
GCR-2026-001
```

## Source Document Intake

| Question | Answer |
|---|---|
| Full source-document intake required? | yes |
| New or updated source document? | New architecture source candidates |
| Source document path | `docs/governance/source-documents/ARCH-*.public.md` |
| Reviewed non-source path | not applicable |
| Register updated? | yes |
| Supersedes existing source? | not confirmed |
| Possible duplicate or replacement candidate? | yes, `ARCH-GOV-SRC-002` may replace `ARCH-SDD-SRC-001` |
| Similarity assessment | `replacement_candidate` for `ARCH-GOV-SRC-002`; `not_assessed` for the other candidates |
| Source status | candidate |

## Why This Change Is Needed

The new architecture documents were received and need to be controlled in the repository before any derivation work starts.

The repository should remember that these documents exist, preserve their original content, and make them visible in the source-document register and impact report without changing executable governance behavior.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | None |
| DevSecOps controls | None |
| Platform model | None |
| Architecture governance | Candidate sources registered only; no marker, gate, guardrail, remediation, or level changes |
| OPA policies | None |
| Schemas and evidence contracts | None |
| Viewer, status indexes or intake | None |
| Release package or baseline | None |
| Downstream repositories | None |

## Replacement Review

| Existing source ID | Similarity | Notes |
|---|---|---|
| `ARCH-SDD-SRC-001` | high | `ARCH-GOV-SRC-002` has the same SDD Architecture Governance Framework title and may replace or supersede the current 20260630v2 source after review. |

Decision:

- [ ] New independent source
- [ ] Possible duplicate, keep as candidate
- [x] Replacement candidate, review required
- [ ] Replacement confirmed
- [ ] Not relevant, retire candidate

Replacement notes:

- No lineage or derived runtime governance artifacts are moved in this change.
- Replacement must be confirmed in a later change request before `ARCH-SDD-SRC-001` is marked `superseded`.

## Derived Artifacts

Changed derived artifacts:

- `model/documents/source-document-register.yaml`
- `generated/reports/source-lineage-report.md`
- `generated/reports/source-lineage-report.json`
- `generated/reports/governance-change-impact.md`
- `generated/reports/governance-change-impact.json`

## Governance Behavior

Choose one:

- [x] Documentation-only
- [ ] Report-only governance behavior
- [ ] Blocking governance behavior
- [ ] Release packaging only

Notes:

- Runtime governance behavior is unchanged.
- Candidate documents are intentionally not used as normative input yet.

## Release Decision

Choose one:

- [x] No release required
- [ ] Release candidate required
- [ ] Patch baseline release required
- [ ] Minor baseline release required
- [ ] Major baseline release required

Release notes:

- No release is required because this change only registers candidate source documents.

## Validation Plan

Confirm what must pass before merge.

- [x] `python3 scripts/validate_runtime_governance.py`
- [x] `python3 scripts/validate_governance_repo.py`
- [x] `python3 -m unittest discover -s tests`
- [x] Source lineage regenerated or confirmed unchanged
- [ ] Viewer regenerated if status or presentation changed
- [ ] Downstream example checked if consumer behavior changed

## Reviewer Notes

- Review the new documents before promoting any candidate from `candidate` to `intake`.
- Confirm whether `ARCH-GOV-SRC-002` replaces `ARCH-SDD-SRC-001`.
- If replacement is confirmed, update `supersedes`, `superseded_by`, lineage, architecture model source references, and release planning in a separate change.
