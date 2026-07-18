# Governance Document Hierarchy

## Intent

The repository now models not only controls and platform capabilities, but also the governance document stack that authorizes them.

## Hierarchy

1. **Policy**: defines mandatory organizational intent and accountability.
2. **Directive**: defines binding operating rules, waiver handling, and compliance workflow.
3. **Standards**: define detailed normative control and platform requirements.
4. **Policy-as-Code / Evidence / Traceability**: implement and verify selected parts of the standards in an auditable way.

## Repository Representation

- `model/documents/governance-documents.yaml` contains the structured document catalog.
- `model/traceability/document-to-control.yaml` maps governance documents to control levels and selected controls.
- `docs/governance/devsecops-policy.md` and `docs/governance/devsecops-directive.md` capture the current working drafts.

## Non-Normative Review Material

Human decision material for a registered candidate source is grouped under
`docs/governance/review-packets/<source-id>/`. Each packet provides one stable
entry point for its review brief, candidate explanation, source placeholder,
change request, structured models, and generated reports.

Review packets are not an additional normative layer. They do not approve a
source or authorize controls, policies, evidence contracts, enforcement, or
releases. The applicable source status and human decision remain recorded in
the source-document register and governance change request.

Private input files used to prepare a public-neutral review packet must remain
outside the public `docs/` tree in a Git-ignored local source area. Only the
registered public placeholder and sanitized review artifacts belong in the
repository.

## Why This Matters

Without the Policy and Directive layers, the repository can express control requirements, but it cannot clearly show which higher-level governance artifacts make those requirements mandatory or how deviations are supposed to be handled procedurally.
