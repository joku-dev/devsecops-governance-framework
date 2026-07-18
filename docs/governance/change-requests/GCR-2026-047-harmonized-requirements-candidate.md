# Governance Change Request

## Summary

- Register the private standards-requirements catalog as a public-neutral
  candidate source placeholder.
- Add a non-normative harmonized requirements candidate and source-ID mapping.
- Add a non-normative L1-L3/GOV maturity assignment for all harmonized
  requirements.
- Add preliminary design-coverage reporting and public artifact hygiene
  validation.
- Preserve existing controls, policies, evidence contracts, workflows,
  enforcement, and released baselines unchanged.

## Change ID

```text
GCR-2026-047
```

## Artifact Classification

| Field | Value |
|---|---|
| Artifact | CISO standards requirements catalog and harmonized model |
| Type | candidate source plus review-only governance model |
| Public source path | `docs/governance/source-documents/CISO-REQ-SRC-001.public.md` |
| Private workbook | withheld and excluded from Git |
| Owner | Governance Owner, subject to CISO confirmation |
| Source Document Intake | required |
| Runtime governance impact | none |
| Enforcement | none |
| Evidence contract impact | none |
| Release impact | none until a separate approval decision |

## Source Classification

The source is a related and overlapping candidate, not a confirmed replacement.
It has high overlap with the current DevSecOps Control Baseline and medium
overlap with Platform and Architecture Governance. The explicit
`related_source` assessment records coexistence without asserting duplicate,
replacement, or superseding status.

## Candidate Evidence

| Measure | Value |
|---|---:|
| Raw workbook rows | 264 |
| Unique source requirements | 233 |
| Duplicate source identifier pairs | 29 |
| Missing source identifiers | 10 |
| Harmonized candidate requirements | 44 |
| Unmapped unique source requirements | 0 |
| Preliminary weighted design coverage | 50.4% |
| Proposed minimum L1 requirements | 22 |
| Proposed minimum L2 requirements | 17 |
| Proposed minimum L3 requirements | 1 |
| Proposed GOV-overlay requirements | 4 |

No source requirement text or Office metadata is included in the public
candidate model or mapping.

## Decision Boundary

The candidate does not authorize:

- changes to `model/controls/`
- changes to `architecture/`
- changes to OPA policy or enforcement
- evidence schema or collector changes
- release or reusable workflow changes
- consumer compliance claims

## Human Review Required

- [ ] CISO confirms authority and intended enterprise applicability.
- [ ] CISO confirms or adjusts the proposed minimum maturity levels.
- [ ] Governance Owner confirms coexistence or replacement intent.
- [ ] DevSecOps Baseline Owner reviews control mappings and gaps.
- [ ] Enterprise Architect reviews architecture and product-security routing.
- [ ] Platform Owner reviews capability implications.
- [ ] Legal or License Compliance confirms publication boundaries.
- [ ] Release Manager records the future release decision.

## Validation Plan

- [x] harmonized model and mapping schema validation
- [x] maturity assignment and report schema validation
- [x] mapping integrity and decision-boundary tests
- [x] public artifact hygiene scan, including configured private terms
- [x] source intake status and review brief regeneration
- [x] repository and runtime validation
- [x] complete unit test suite
- [x] strict documentation build

## Release Decision

No release is required for the candidate intake and review model. Any approved
control or evidence change requires a separate change request and explicit
release assessment.
