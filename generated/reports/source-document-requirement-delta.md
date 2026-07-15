# Source Document Requirement Delta

Generated: `2026-07-15T10:29:56Z`

## Decision State

- Current state: `review_support_only`
- Runtime governance changed: `false`
- Candidate promoted: `false`
- Stricter rules enabled: `false`

## Summary

- Replacement pairs: `1`

### Status Counts

| Status | Count |
|---|---:|
| `changed` | `1` |
| `equivalent` | `2` |
| `removed` | `1` |

### Review Priority Counts

| Priority | Count |
|---|---:|
| `high` | `2` |
| `low` | `2` |

## Replacement Pair Deltas

### `ARCH-GOV-SRC-002` versus `ARCH-SDD-SRC-001`

- Candidate: `docs/governance/source-documents/ARCH-GOV-SRC-002.public.md`
- Target: `docs/governance/source-documents/ARCH-SDD-SRC-001.public.md`
- Replacement classification: `registered_replacement_candidate`
- Candidate requirement statements: `3`
- Target requirement statements: `4`
- Differences requiring review: `2`

Pair status counts:

- `changed`: `1`
- `equivalent`: `2`
- `removed`: `1`

### Added In Candidate

No items.

### Changed In Candidate

| Priority | Candidate ref | Target ref | Similarity | Potential impacts | Candidate statement | Target statement |
|---|---|---|---:|---|---|---|
| `high` | `docs/governance/source-documents/ARCH-GOV-SRC-002.public.md:19` | `docs/governance/source-documents/ARCH-SDD-SRC-001.public.md:20` | `0.631` | `evidence_contracts, runtime_governance_review` | - Architecture exceptions shall remain visible until closure. | - Architecture evidence shall remain traceable to private source authority. |

### Removed From Candidate

| Priority | Candidate ref | Target ref | Similarity | Potential impacts | Candidate statement | Target statement |
|---|---|---|---:|---|---|---|
| `high` | `n/a` | `docs/governance/source-documents/ARCH-SDD-SRC-001.public.md:19` | `0.0` | `runtime_governance_review` |  | - Architecture exceptions shall be documented with owner, risk, expiry, and follow-up action. |

### Equivalent Sample

| Priority | Candidate ref | Target ref | Similarity | Potential impacts | Candidate statement | Target statement |
|---|---|---|---:|---|---|---|
| `low` | `docs/governance/source-documents/ARCH-GOV-SRC-002.public.md:17` | `docs/governance/source-documents/ARCH-SDD-SRC-001.public.md:17` | `1.0` | `runtime_governance_review` | - Architecture governance shall preserve human decision accountability. | - Architecture governance shall preserve human decision accountability. |
| `low` | `docs/governance/source-documents/ARCH-GOV-SRC-002.public.md:18` | `docs/governance/source-documents/ARCH-SDD-SRC-001.public.md:18` | `1.0` | `review_gates, runtime_governance_review` | - Architecture governance shall use versioned baselines for reproducible review. | - Architecture governance shall use versioned baselines for reproducible review. |

## Review Notes

- This is a keyword-based normative statement delta, not a final legal or architecture decision.
- Changed, added, and removed mandatory or prohibition statements require human architecture-owner review.
- Removed statements may indicate content deleted from the candidate or moved into companion documents; confirm against the full architecture source set before deciding.
- No source document status, lineage, runtime governance, policy, schema, or release package is changed by this report.
