# GCR-2026-114: Source Candidate Review Decisions

## Decision Status

**Human review decision recorded on 8 October 2026.** The three named source
documents remain candidates. The PRA reviewer-comments file is classified as
supporting review material and is removed from the source-document register.

## Decisions

| Artifact | Decision | Effect |
|---|---|---|
| `TOOLCHAIN-ARCH-CAND-001` | Keep as candidate | Remains related to PRA, DSCB and SDLC sources; no architecture or control derivation is authorized. |
| `SDLC-PROC-CAND-001` | Keep as candidate | Remains a process candidate; no gate, RACI, workflow or blocking behavior is authorized. |
| `SW-INDUSTRIALISATION-OM-CAND-001` | Keep as candidate | Remains a proposal candidate; no organization, funding, mandate or decision-right change is authorized. |
| Former `PRA-REV-INPUT-001` | Supporting review material only | Moved to `docs/governance/review-packets/DevSecOps_Platform_Reference_Architecture_Reviewer_Comments_Review_v0.4.md`; removed from source-document registration because it is reviewer commentary, not a normative source. |

The separate decision to keep `DEVSECOPS-POL-CAND-002` as a candidate is
recorded in [GCR-2026-113](GCR-2026-113-devsecops-policy-v2-candidate-review-decision.md).

## Decision Authority And Date

| Field | Value |
|---|---|
| Decision | Human maintainer decision conveyed on 2026-10-08 |
| Organizational role | Not asserted by this record |
| Register effect | Three candidates retained; one supporting artifact removed from the source register |

The maintainer confirmed that the authorized current versions are tracked in
Git and use `requirements` in their filenames. Git confirmed that ten such
files are tracked and unchanged in the review worktree. The incumbent Policy,
Directive, DSCB and PRA requirements extracts are used as authorized
comparators here. The separately registered `ARCH-GOV-SRC-002` replacement
candidate remains a candidate under the source register. Tracking does not
authorize any new, untracked candidate.

## Source And Artifact Paths

- Toolchain candidate: `docs/governance/source-documents/Enterprise_SDLC_Toolchain_Reference_Architecture_v0.3.md`
- SDLC V5 candidate: `docs/governance/source-documents/Software_Development_Process_DevSecOps_V5_Activity_RACI_Artifacts.md`
- Operating Model candidate: `docs/governance/source-documents/Software_Industrialisation_Enterprise_Operating_Model_revised_extended_scope_polished.md`
- PRA reviewer material: `docs/governance/review-packets/DevSecOps_Platform_Reference_Architecture_Reviewer_Comments_Review_v0.4.md`
- Consolidated findings: [Source Document Candidate Review](../review-packets/source-document-candidate-review-2026-10-08.md)

## Unresolved Review Conditions

- Confirm provenance, owner, intended authority and approval path for each
  untracked candidate. The incumbent requirements extracts remain the
  authorized comparison sources unless a separate approved change replaces
  them.
- Resolve DSCB-L2-REQ-015–017 and stable PRA identifiers before considering
  the Toolchain Architecture for baseline use.
- Resolve process ownership, control references and the proposed blocking gate
  semantics before considering SDLC V5 for normative use.
- Confirm executive sponsorship, Steering Board authority, scope, funding and
  endorsement before considering the Industrialisation Model for normative use.
- Confirm the retained PRA comments apply to the authorized tracked PRA
  requirements extract, then close each comment before using it to revise the
  platform standard.

## Impact Classification

| Area | Impact |
|---|---|
| Policy or directive | None |
| DevSecOps controls | None |
| Platform or architecture model | None |
| OPA policies, schemas or evidence contracts | None |
| Runtime enforcement | None |
| Released baselines | None |
| Intake register | Three candidates retained; reviewer commentary removed from source registration |
| Release | None |

No source candidate is approved or promoted by this decision record. Future
promotion or derivation requires a separate human-approved change request.
