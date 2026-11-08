# GCR-2026-160 — Approval of Current Policy, Directive and SDD Sources

## Summary

Record the repository maintainer's explicit instruction on 8 November 2026 to
mark the three currently used sources still under review as approved and released
for use as normative source inputs. Their register status changes from `review`
to `approved`. The decision binds the exact existing sanitized extracts below.

## Human decision and version binding

The instruction followed a source-usage inventory at main
`c1f6e2bda11bb8e55ecc8e958701ffe2c8eea972` and an explanation that DSCB and PRA
were already approved while SDD, Policy and Directive remained under review.
The maintainer then requested: “KAnnst Du diese quellen als approved und
freigegeben kennzeichnen.” This records that human decision; the agent does
not independently grant source authority or claim provider-authenticated consent.

All three register versions remain `requirements-only-sanitized`. Approval
covers these repository extracts, not an unspecified upstream original or a
future edit. Changed source bytes require a new reviewed decision.

| Registered source ID | Repository source path | SHA-256 |
|---|---|---|
| `DEVSECOPS-POL-REQ-001` | `docs/governance/source-documents/DEVSECOPS-POL-SRC-001.requirements.md` | `33bcf4291e399f47236b2c6b68413a43a957841c204e9e4f3318342ef65a52cb` |
| `DEVSECOPS-DIR-REQ-001` | `docs/governance/source-documents/DEVSECOPS-DIR-SRC-001.requirements.md` | `879be84e250ec3882802860d34177a332fb895da260f9ffd7493f4e5d0c86ed6` |
| `ARCH-SDD-REQ-001` | `docs/governance/source-documents/ARCH-SDD-SRC-001.requirements.md` | `150729e2bec6664195eec8a72f90a1ec3b337765fdd1ac6c08023498c1b020cd` |

## Artifact intake classification

| Field | Decision |
|---|---|
| Artifact type | Recorded human source-approval decision and register update |
| Owner | Repository maintainer; Governance Owner and Architecture Owner review perspectives |
| Full Source Document Intake required? | Yes; source register status changes |
| New or changed source document? | No; all source bytes and versions remain unchanged |
| Replacement or supersession? | No; candidate relationships and lineage remain unchanged |
| Evidence contract or schema impact | None |
| Runtime governance impact | No policy, gate or enforcement change |
| Release impact | No release; released packages and tags remain unchanged |
| Validation | Pinned bootstrap, full repository validation, source-dependent report/viewer generation, strict MkDocs and revision-bound role review |

## Meaning and limits of approval

- The three extracts may serve as approved normative source inputs in subsequent
  governed work. The register now has nine approved sources, six candidates,
  and no sources in `review`.
- Source approval is separate from requirement decisions, canonical activation,
  effective artifact adoption, implementation evidence and deployment approval.
  Existing lifecycle cases, authority decisions and artifact mappings stay as-is.
- Policy and Directive working documents retain their existing draft status.
  This source decision does not publish those drafts as approved policies.
- The existing explicit-declaration extraction rule and unverified identifier
  provenance remain unchanged. Approval does not infer requirements from prose.
- No security certification, completeness claim or claim of latest upstream
  version follows from this decision.
- All six candidate sources retain their status and remain non-deriving. The
  registered architecture and policy replacement candidates are not accepted,
  rejected, promoted or substituted by this decision.
- This does not create an authorized source-set baseline, accept a consistency
  review, change lifecycle operating acceptance or authorize blocking/release.
  Projections bound to the former register hash must remain stale or unavailable.
- The historical `ARCH-SDD-SRC-001.public.md` reference in the immutable
  architecture v0.1.0 package is retained as historical provenance.

## Affected artifacts

- `model/documents/source-document-register.yaml`
- This decision, source dependency guide, current-state addendum and MkDocs navigation
- Script-generated lineage, intake, review briefs, requirement delta, architecture
  replacement, change impact, source process status, governance graph and Viewer projections
- Existing source-status regression expectations updated for the approved population

## Validation record

Validation results and revision-bound review evidence are recorded in the PR.
This decision records maintainer source approval; protected-branch CODEOWNER
review and successful CI remain separate merge prerequisites.
