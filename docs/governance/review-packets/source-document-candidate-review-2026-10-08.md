# Source Document Candidate Review — 8 October 2026

## Purpose and decision boundary

This packet records the initial semantic review of the five recently registered
source-document candidates. It supports human decisions; it does not promote,
retire, approve, or authorize derivation from any candidate.

The maintainer confirmed that authorized current versions are tracked in Git
and use `requirements` in their filenames. Git confirms ten
`*.requirements.md` files are tracked and unchanged in this worktree. The
incumbent Policy, Directive, DSCB and PRA requirements extracts are the
authorized comparators for this review. A tracked architecture file,
`ARCH-GOV-SRC-002.requirements.md`, remains explicitly registered as a
replacement candidate and is not treated as an approved source. The newly
reviewed candidate documents are untracked and are not authorized by the
tracking state of the incumbent extracts.

At review snapshot `a8fc36f3de7f33cd2a26dff94f9a28985e78d64f`, the four
DevSecOps Policy, Directive, Control Baseline and Platform requirements
extracts were unchanged; their latest shared update is commit `e6feb68`.

`DEVSECOPS-POL-CAND-002` has a separate recorded human decision to keep it as a
candidate in [GCR-2026-113](../change-requests/GCR-2026-113-devsecops-policy-v2-candidate-review-decision.md).
[GCR-2026-114](../change-requests/GCR-2026-114-source-candidate-decisions.md)
records the decisions for the three other candidates and the reviewer material.
Technical review conditions remain open.

## Candidate review matrix

| Candidate | Initial relationship | Review finding | Recommended disposition | Human decision |
|---|---|---|---|---|
| PRA reviewer comments v0.4 — formerly `PRA-REV-INPUT-001` | Supporting review input for `PRA-STD-REQ-001` | The file contains reviewer comments, proposed dispositions and unresolved decisions. It is not a standalone normative source. Confirm the comments apply to the authorized PRA requirements extract and close each against that content. | Supporting review material only; moved to `docs/governance/review-packets/`. | Confirmed in GCR-2026-114 |
| `TOOLCHAIN-ARCH-CAND-001` — Enterprise SDLC Toolchain Reference Architecture v0.3 | Related to PRA, DSCB and the SDLC process | Its own source authority and approval are explicitly unresolved. Actions A01–A06 block a controlled enterprise baseline. It maps DSCB-L2-REQ-015–017, which are not present in the repository's registered L2 baseline (currently 14 L2 requirements). The document itself says those entries remain advisory pending a decision. | Keep as a related architecture candidate. Resolve the candidate's authority, stable PRA IDs, the L2 control mismatch, system-of-record ownership and monitoring contracts before baseline consideration. | Confirmed in GCR-2026-114 |
| `SDLC-PROC-CAND-001` — Software Development Process DevSecOps V5 | Related process source for the Directive, controls and platform | Its own revision and approval are not established and some source references are redacted. All 27 distinct DSCB/PRA identifiers resolve to current tracked models. It says the CDO owns the normative baseline; the Directive names the CDO as enterprise owner and separately defines Governance Board responsibilities, so the candidate's ownership wording needs a clear interpretation. It also defines `fail` as blocking; that enforcement meaning must be reconciled with approved report-only and blocking scopes before adoption. | Keep as a process candidate. Confirm the candidate's owner and approval path, clarify the CDO/Board boundary, and explicitly decide gate semantics and lifecycle applicability. | Confirmed in GCR-2026-114 |
| `SW-INDUSTRIALISATION-OM-CAND-001` — Software Industrialisation Enterprise Operating Model proposal | Related enterprise operating-model proposal; not a replacement for policy or controls | The document labels itself a proposal and calls for executive approval, a Steering Board mandate, an Office, capability leads, RACI, funding, capacity and cross-Business-Unit decision rights. These are material organizational commitments whose authority and resourcing are not evidenced by the proposal itself. | Keep as a proposal candidate. Obtain the sponsor, intended approving body, mandate, affected organizational scope and endorsement path before baseline consideration. | Confirmed in GCR-2026-114 |

## Cross-document findings

1. The Toolchain Architecture and SDLC V5 are designed to fit together: the
   former assigns lifecycle activities and gates to the process and keeps
   platform capability contracts separate. Their current versions are both
   candidates, so this proposed division of authority is not yet approved.
2. The Toolchain Architecture refers to 17 L2 controls while the authorized
   current baseline has 14. Its 49 distinct DSCB references include all 46
   current DSCB requirement IDs plus `DSCB-L2-REQ-015`–`017`, which are absent
   from the current baseline and appear as unresolved proposals in the PRA
   reviewer material. The Toolchain document contains no stable PRA requirement
   IDs; its own Action A04 calls for stable capability IDs and a completed
   crosswalk. The SDLC V5 document refers to 27 distinct DSCB IDs, all present
   in current models. Identifier existence does not confirm semantic mapping,
   source authority or applicability.
3. SDLC V5's blocking `fail` gate is a process proposal, not authorization to
   change policy enforcement. Any adoption needs an explicit scope and
   enforcement decision consistent with the report-only/blocking alignment.
4. The Operating Model would establish or formalize cross-enterprise roles,
   governance and funding. It needs organizational sponsorship and approval
   independent of the technical source-document review.
5. The PRA reviewer comments can help close the PRA review, but comments and
   proposed dispositions do not themselves approve the standard or create new
   requirements.

The current authorized PRA comparator is the tracked
`PRA-STD-SRC-001.requirements.md` file. The remaining reviewer-input question
is whether the v0.4 comments were written against the content represented by
that authorized extract and how each comment should be dispositioned.

## Detailed semantic review findings

The checks below compare candidate statements with the authorized tracked
requirements extracts and current model identifiers. They are review findings,
not candidate approval. Section references point to the candidate files named
in the matrix above.

### Toolchain Reference Architecture v0.3

- **Control identifier coverage:** Annex A contains 49 distinct DSCB IDs. It
  includes all 46 IDs in the current DSCB models and adds L2-REQ-015–017. Its
  statement that it covers 17 L2 controls therefore counts the three proposed
  monitoring entries; the current authorized baseline has 14 L2 requirements.
  The candidate explicitly calls the three entries advisory and leaves them
  for Action A02. This is an unresolved dependency, not authority to add
  controls.
- **PRA traceability:** The candidate maps to C1–C7 capability IDs and PRA
  layers, but it does not map its controls to stable IDs from the authorized
  PRA requirements extract. Action A04 itself requires stable PRA IDs and a
  validated crosswalk. Until that is closed, the proposed control-to-platform
  mapping cannot establish PRA coverage or conformance.
- **Architecture boundary:** The document assigns control obligations to the
  DSCB, activities and gates to SDLC, and technical minimums to PRA. This is a
  useful proposed separation and aligns with the PRA extract's minimum-level
  relationship (PRA REQ-031–038). It remains a proposal until owners approve
  the boundaries and resolve source conflicts (A01/A08).
- **Monitoring and evidence:** Sections 9–12 propose observable integration
  failures, immutable subjects, evidence-linked decisions, and fail-closed
  treatment of missing or invalid evidence. These are technical design
  proposals. Their gate effect, exception path, operational ownership,
  destination, retention and domain handling need approval (A06/A09/A10); they
  do not themselves authorize blocking in consuming workflows.
- **Transition and deployment:** The proposed L1–L3 to PRA-Level mapping is
  consistent with the current requirements extract. Retiring former A–D
  profiles and migrating existing programme selections remains a separate
  decision (A03); no existing programme classification should be inferred
  from the new model.
- **Disposition:** retain as candidate. Close A01–A06 and validate the full
  control-to-PRA-to-capability-to-process-to-evidence matrix before a
  controlled-baseline decision. A bounded pilot may test interfaces only with
  its working rules and report-only/blocking scope explicitly recorded.

### Software Development Process DevSecOps V5

- **Scope conflict to resolve:** The “Zweck und Scope” section says the process
  is directly applicable to *zulassungsrelevante Software* and can be extended
  for higher criticality/security. The authorized DSCB requirement
  `DSCB-GOV-REQ-001` says all programs implement L1. The candidate also lists
  L1 as the minimum baseline and selects applicability at P0. These statements
  leave unclear whether the process lifecycle applies to every in-scope
  program or only the stated subset. The process owner must define scope and
  reconcile it with the all-program L1 obligation before adoption.
- **P2 control boundary:** The candidate treats P2 as pre-production and
  informal for change management, while P3–P7 use formal baselines and
  release-relevant evidence. It also assigns controls across phases and
  describes P2 control/evidence preparation. Clarify which controls already
  apply in P2, what “non-formal” excludes, and what must be complete at the
  P2→P3 formalisation gate. Do not read “pre-production” as a blanket control
  exemption.
- **Blocking semantics:** The process principles say every phase ends in a
  gate (`pass`, `fail`, `manual review`, `waiver required`, or `not applicable`);
  its gate model defines `fail` as blocking the phase or release. This is a
  proposed enforcement mode. It needs an explicit consuming-workflow scope,
  authorization, exception/waiver path, and consistent treatment of the
  repository's approved report-only and legacy blocking contexts before any
  workflow adopts it.
- **Approval authority:** The candidate assigns gate or decision accountabilities
  across DM, V&V, RM and GOV and says project assignments and independence must
  be documented. Its RACI note distinguishes artifact accountability from gate
  approval authority. Confirm those role assignments and delegated powers
  against the authorized Directive, especially waiver, release, applicability
  and escalation decisions; a RACI entry alone does not grant authority.
- **Identifier integrity:** All 27 distinct DSCB identifiers cited resolve to
  current model IDs. This establishes identifier existence only. Each phase's
  cited controls still needs semantic applicability review, particularly where
  references are abbreviated or optional by baseline level.
- **Baseline-to-phase coverage:** The candidate cites all 16 L1 controls, but
  only 4 of 14 current L2 controls, 3 of 11 L3 controls, and 4 of 5 governance
  controls in its phase/control references. Not cited there are L2-REQ-002–010
  and 012, L3-REQ-002–008 and 010, and GOV-REQ-003. The candidate's baseline
  overview lists broader control ranges, so this is an unresolved allocation
  question rather than proof those controls are intentionally omitted. The
  process owner should map every applicable control to a phase/activity,
  evidence output and decision point, or identify the authoritative mechanism
  that covers controls with no process-phase reference.
- **Normative wording:** The baseline-reference section says implementations
  “should” consume approved, versioned control files and avoid an unprotected
  main branch. Decide whether this is advice or a mandatory process safeguard;
  if mandatory, state its owner, approved source and evidence.
- **Disposition:** retain as candidate. Resolve scope, P2 applicability,
  blocking semantics, authority/RACI and source revision/approval before
  process adoption or workflow derivation.

### Software Industrialisation Enterprise Operating Model

- **Organizational authority:** The proposal creates a Software Industrialisation
  Steering Board, Office, capability leads, cross-Business-Unit participation,
  decision rights, funding commitments and permanent capability ownership.
  Its own approval section requires an executive mandate and endorsement. No
  sponsor, approved mandate, appointments or funding decision is included in
  the candidate packet, so these provisions are proposed organizational
  commitments rather than current operating authority.
- **Governance interfaces:** The proposal names enterprise governance and a
  Software Industrialisation Steering Board while the authorized DevSecOps
  Directive already defines a DevSecOps Governance Board and the architecture
  framework has its own decision authority. Define which body decides strategy,
  portfolio, technical architecture, control changes, waivers, risk acceptance
  and escalations; identify which existing bodies remain authoritative. The
  candidate must not create overlapping or conflicting delegated powers.
- **Applicability and local obligations:** The model expects participating
  Business Units to contribute capacity, adopt agreed capabilities and follow
  enterprise decisions while preserving local delivery and resource
  accountability. The approving body must define which entities are in scope,
  how commitments bind them, how local variation is approved, and how conflicts
  with existing Business Management System or contractual obligations are
  handled.
- **Operational readiness:** The proposal requires funded capacity, named
  benefit owners, competence continuity, assurance, permanent operating
  charters, support and retirement decisions. These depend on named owners,
  funding authority, measures and transition evidence that are not supplied by
  the proposal itself.
- **Reference completeness:** Several internal references are generic or
  redacted (for example, controlled BMS/SDD documents). Resolve exact controlled
  document identities and revisions before approval so precedence and
  organizational interfaces can be checked.
- **Disposition:** retain as a proposal candidate. Obtain an executive sponsor,
  intended approving body, mandate, in-scope organizations, governance
  interface decisions, resourcing and endorsement route before considering
  normative status.

### PRA reviewer comments v0.4

- The reviewer file contains detailed recommendations and explicit decisions
  still required, including PRA identifiers and control mapping, L2 monitoring,
  service catalogue, system-of-record ownership, governance authority and
  isolated-domain signing. It references PRA/DSCB IDs but is commentary, not
  an approved source.
- The file's intended target and comparator remain unconfirmed. Before
  accepting a comment as a change request, map it to the exact authorized PRA
  requirement(s), establish whether it addresses the current tracked extract or
  a different full-source revision, and record accept, reject, defer or
  clarification-needed with rationale and decision owner.
- **Disposition:** supporting review material only. No PRA requirement,
  platform capability or control changes follow from the comments until a
  separately authorized change is approved.

## Inputs needed for final decisions

- For each untracked candidate, its owner, provenance, intended authority and
  approval path. The authorized incumbent requirements versions remain the
  comparison sources unless a separate approved change replaces them.
- Confirmation that the retained PRA reviewer comments apply to the authorized
  PRA requirements extract, plus a disposition for every comment.
- A control-baseline owner decision on the three proposed L2 monitoring
  controls, with stable IDs and matching PRA mappings if accepted.
- The process authority and decision rights for SDLC V5, including whether
  `fail` blocks in any consuming workflow and under what scope.
- Executive or Steering Board sponsorship and approval route for the
  Industrialisation Operating Model proposal.

## Interim safeguards

- The Policy v2, Toolchain Architecture, SDLC V5 and Industrialisation Model
  remain candidates; PRA reviewer comments are supporting review material and
  are no longer registered as a source document.
- No control, policy, schema, workflow, runtime gate, release or baseline is
  derived from this packet or from the candidates.
- Existing source-document statuses and released baselines remain unchanged.
