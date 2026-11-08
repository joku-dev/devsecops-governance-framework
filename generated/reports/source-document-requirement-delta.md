# Source Document Requirement Delta

Generated: `2026-11-08T14:17:54Z`

## Decision State

- Current state: `review_support_only`
- Runtime governance changed: `false`
- Candidate promoted: `false`
- Stricter rules enabled: `false`

## Summary

- Replacement pairs: `2`

### Status Counts

| Status | Count |
|---|---:|

### Review Priority Counts

| Priority | Count |
|---|---:|

## Requirement Intake Identification

- Registered source documents: `15`
- Scanned source documents: `14`
- Not scanned because source text is withheld: `1`
- Extraction mode: `explicit_identifiers_only` (no prose inference)
- Explicit requirement identifiers with unverified origin: `46`
- Extracted row identifiers with unverified origin: `0`
- Confirmed source-author identifiers (P1): `0`

Counts are per source document. Only labelled requirement declarations are included; prose and synthetic row IDs are excluded. P1 requires `author_provided` provenance in the source register.

### Counts By Source Status

| Source status | Confirmed author IDs / P1 | Explicit IDs / unverified |
|---|---:|---:|
| `approved` | `0` | `46` |
| `candidate` | `0` | `0` |

### Counts By Source Document

| Source ID | Source status | Confirmed author IDs / P1 | Explicit IDs / unverified | Scanned |
|---|---|---:|---:|---|
| `DEVSECOPS-POL-REQ-001` | `approved` | `0` | `0` | `true` |
| `DEVSECOPS-DIR-REQ-001` | `approved` | `0` | `0` | `true` |
| `DSCB-STD-REQ-001` | `approved` | `0` | `46` | `true` |
| `PRA-STD-REQ-001` | `approved` | `0` | `0` | `true` |
| `ARCH-SDD-REQ-001` | `approved` | `0` | `0` | `true` |
| `ARCH-TPL-REQ-001` | `approved` | `0` | `0` | `true` |
| `ARCH-EA-REQ-001` | `approved` | `0` | `0` | `true` |
| `ARCH-SA-REQ-001` | `approved` | `0` | `0` | `true` |
| `ARCH-PA-REQ-001` | `approved` | `0` | `0` | `true` |
| `ARCH-GOV-REQ-001` | `candidate` | `0` | `0` | `true` |
| `CISO-REQ-SRC-001` | `candidate` | `0` | `0` | `false` |
| `DEVSECOPS-POL-CAND-002` | `candidate` | `0` | `0` | `true` |
| `TOOLCHAIN-ARCH-CAND-001` | `candidate` | `0` | `0` | `true` |
| `SDLC-PROC-CAND-001` | `candidate` | `0` | `0` | `true` |
| `SW-INDUSTRIALISATION-OM-CAND-001` | `candidate` | `0` | `0` | `true` |

Unscanned source `CISO-REQ-SRC-001`: Intake metadata only; underlying source text is withheld.

## Replacement Pair Deltas

### `ARCH-GOV-REQ-001` versus `ARCH-SDD-REQ-001`

- Candidate: `docs/governance/source-documents/ARCH-GOV-SRC-002.requirements.md`
- Target: `docs/governance/source-documents/ARCH-SDD-SRC-001.requirements.md`
- Replacement classification: `registered_replacement_candidate`
- Candidate requirement statements: `0`
- Target requirement statements: `0`
- Differences requiring review: `0`
- Comparison status: `no_explicit_requirements`

Pair status counts:

- Candidate intake classes: `none`
- Target intake classes: `none`


### Added In Candidate

No items.

### Changed In Candidate

No items.

### Removed From Candidate

No items.

### Equivalent Sample

No items.

### `DEVSECOPS-POL-CAND-002` versus `DEVSECOPS-POL-REQ-001`

- Candidate: `docs/governance/source-documents/DevSecOps_Policy_Review_Integrated_v2_CHANGE_MARKED.md`
- Target: `docs/governance/source-documents/DEVSECOPS-POL-SRC-001.requirements.md`
- Replacement classification: `registered_replacement_candidate`
- Candidate requirement statements: `0`
- Target requirement statements: `0`
- Differences requiring review: `0`
- Comparison status: `no_explicit_requirements`

Pair status counts:

- Candidate intake classes: `none`
- Target intake classes: `none`


### Added In Candidate

No items.

### Changed In Candidate

No items.

### Removed From Candidate

No items.

### Equivalent Sample

No items.

## Review Notes

- This delta compares explicit requirement declarations only; it is not a final legal or architecture decision.
- Only explicitly labelled requirements such as DSCB-L1-REQ-001 are inventoried; repeated or overlapping sources are counted per source.
- Unlabelled prose, headings, version history, synthetic extraction row IDs and reference-only mentions do not create requirements.
- Candidate-intake records whose underlying source text is withheld are listed as unscanned and are not counted.
- Changed, added, and removed mandatory or prohibition statements require human architecture-owner review.
- Removed statements may indicate content deleted from the candidate or moved into companion documents; confirm against the full architecture source set before deciding.
- P1 requires confirmed source-author identifier provenance; otherwise an explicit identifier remains unassigned. No P2 prose candidates are generated.
- Intake identification class and priority are separate from delta review priority and source approval status.
- No source document status, lineage, runtime governance, policy, schema, or release package is changed by this report.
