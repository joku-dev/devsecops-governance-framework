# GCR-2026-161 — Five-Phase Requirement Journey Guide

## Summary

- Explain the document-to-runtime journey in five phases, followed by a technical
  reference for names, identifiers, registers and implementation details.
- Trace the existing Branch Protection example through source declaration,
  proposal, canonical revision, effective artifact mapping and Rego module.
- Preserve document paths and old section anchors, label the 9 October snapshot
  as historical, and align the system architecture overview with the same phases.
- Provide an accessible static SVG alongside Mermaid source so the existing
  MkDocs publication shows the diagram without a renderer or runtime change.

## Artifact intake classification

| Field | Decision |
|---|---|
| Artifact type | Explanatory architecture documentation and static diagram |
| Target paths | Document-to-OPA rulebook, system architecture overview, shared diagram, this GCR and MkDocs navigation |
| Owner | Governance Platform Maintainers |
| Full Source Document Intake required? | No; no source document or source register change |
| Reviewed non-source paths | `docs/governance/architecture/`, this change request and documentation navigation |
| New or replaced governance source? | No |
| Evidence contract or schema impact | None |
| Runtime governance impact | None |
| Release impact | No release |

## Reading structure

1. Approve source / Quelle freigeben.
2. Decide requirement / Anforderung entscheiden.
3. Confirm implementation / Umsetzung bestätigen.
4. Publish rule set / Regelstand veröffentlichen.
5. Apply and review results / Anwenden und Ergebnisse prüfen.

Each phase explains input, task, human decision, outcome and purpose. Rejection,
duplicates and conflicts remain outcomes within the relevant phase. Technical
records are supporting evidence rather than additional user steps. Native Git
requirements enter phase 2 with their versioned native source.

## Governance boundaries

This is a reading structure for the existing procedures. It does not combine
source approval, requirement activation, implementation equivalence, publication
or blocking authorization into one decision. Authority Ledger and GCR remain
supporting authority and decision records. Explicit-declaration extraction,
candidate protection, immutable history and artifact hash binding are unchanged.

The documented example binds `DSCB-L1-REQ-003`,
`RLC-DSCB-STD-REQ-001-MIGRATION-P0012`, `GRQ-000003@rev1`, `RTA-000001`
and `policies/opa/branch_protection.rego`. The existing mapping has
`enforcement: none`. Publication and runtime evaluation are clearly marked as
process continuations, not as evidence of a particular release, consumer run,
blocking integration or production approval.

No source, source status, canonical requirement, artifact mapping, API, schema,
runtime policy, workflow, operating acceptance, release package or tag changes.
Historical status figures retain their date and link to authoritative current
status sources rather than being silently refreshed.

## Validation and delivery

- Compare the example with the source register, source statement, lifecycle
  decision, canonical catalog, control, RTA record and Rego module.
- Check old section anchors, local links, SVG/phase correspondence, Mermaid
  structure and the rendered documentation.
- Run pinned bootstrap, complete repository validation and strict MkDocs.
- Restore only unrelated generated validation output; commit documentation only.
- Complete a revision-bound role review, verify the signed commit, push and open
  a focused PR. Record actual outcomes and evidence references in that PR.

The coordinator's role lenses do not replace independent protected-branch review.
