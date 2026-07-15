# Architecture Source Replacement Assessment

Generated: `2026-07-15T09:58:52Z`

## Summary

- Architecture source documents: `12`
- Active architecture sources: `1`
- Candidate architecture sources: `5`
- Comparisons: `5`
- Likely replacements: `1`

## Decision State

- Current state: `assessment_only`
- Runtime governance changed: `false`
- Recommended next step: Manually review likely replacements before changing source status, lineage, architecture YAML source_document fields, or baseline release planning.

## Active Architecture Sources

| Source ID | Title | Version | Source path |
|---|---|---|---|
| `ARCH-SDD-SRC-001` | SDD Architecture Governance Framework | `public-placeholder` | `docs/governance/source-documents/ARCH-SDD-SRC-001.public.md` |

## Candidate Architecture Sources

| Source ID | Title | Version | Source path |
|---|---|---|---|
| `ARCH-TPL-SRC-001` | SDD Architecture Template and Checklists | `public-placeholder` | `docs/governance/source-documents/ARCH-TPL-SRC-001.public.md` |
| `ARCH-EA-SRC-001` | SDD Enterprise Architecture Guidelines | `public-placeholder` | `docs/governance/source-documents/ARCH-EA-SRC-001.public.md` |
| `ARCH-SA-SRC-001` | SDD Solution Architecture Guidelines | `public-placeholder` | `docs/governance/source-documents/ARCH-SA-SRC-001.public.md` |
| `ARCH-PA-SRC-001` | SDD Product Architecture Guidelines | `public-placeholder` | `docs/governance/source-documents/ARCH-PA-SRC-001.public.md` |
| `ARCH-GOV-SRC-002` | SDD Architecture Governance Framework | `public-placeholder` | `docs/governance/source-documents/ARCH-GOV-SRC-002.public.md` |

## Comparisons

### `ARCH-TPL-SRC-001` versus `ARCH-SDD-SRC-001`

- Candidate: `docs/governance/source-documents/ARCH-TPL-SRC-001.public.md`
- Target: `docs/governance/source-documents/ARCH-SDD-SRC-001.public.md`
- Candidate Doc ID: `unknown`
- Target Doc ID: `unknown`
- Title overlap: `0.0`
- Content overlap: `0.562`
- Shared headings: `0`
- Classification: `independent_candidate`
- Recommendation: Keep as candidate or classify as separate source; no replacement action recommended yet.

- Registered similarity assessment: `not_assessed`

### `ARCH-EA-SRC-001` versus `ARCH-SDD-SRC-001`

- Candidate: `docs/governance/source-documents/ARCH-EA-SRC-001.public.md`
- Target: `docs/governance/source-documents/ARCH-SDD-SRC-001.public.md`
- Candidate Doc ID: `unknown`
- Target Doc ID: `unknown`
- Title overlap: `0.0`
- Content overlap: `0.562`
- Shared headings: `0`
- Classification: `independent_candidate`
- Recommendation: Keep as candidate or classify as separate source; no replacement action recommended yet.

- Registered similarity assessment: `not_assessed`

### `ARCH-SA-SRC-001` versus `ARCH-SDD-SRC-001`

- Candidate: `docs/governance/source-documents/ARCH-SA-SRC-001.public.md`
- Target: `docs/governance/source-documents/ARCH-SDD-SRC-001.public.md`
- Candidate Doc ID: `unknown`
- Target Doc ID: `unknown`
- Title overlap: `0.0`
- Content overlap: `0.562`
- Shared headings: `0`
- Classification: `independent_candidate`
- Recommendation: Keep as candidate or classify as separate source; no replacement action recommended yet.

- Registered similarity assessment: `not_assessed`

### `ARCH-PA-SRC-001` versus `ARCH-SDD-SRC-001`

- Candidate: `docs/governance/source-documents/ARCH-PA-SRC-001.public.md`
- Target: `docs/governance/source-documents/ARCH-SDD-SRC-001.public.md`
- Candidate Doc ID: `unknown`
- Target Doc ID: `unknown`
- Title overlap: `0.0`
- Content overlap: `0.562`
- Shared headings: `0`
- Classification: `independent_candidate`
- Recommendation: Keep as candidate or classify as separate source; no replacement action recommended yet.

- Registered similarity assessment: `not_assessed`

### `ARCH-GOV-SRC-002` versus `ARCH-SDD-SRC-001`

- Candidate: `docs/governance/source-documents/ARCH-GOV-SRC-002.public.md`
- Target: `docs/governance/source-documents/ARCH-SDD-SRC-001.public.md`
- Candidate Doc ID: `unknown`
- Target Doc ID: `unknown`
- Title overlap: `1.0`
- Content overlap: `0.71`
- Shared headings: `0`
- Classification: `registered_replacement_candidate`
- Recommendation: Review as likely replacement before moving lineage or creating a new architecture baseline.

- Registered similarity assessment: `replacement_candidate`
- Registered candidate replacement for: `ARCH-SDD-SRC-001`

## Review Guidance

- Do not change architecture runtime governance behavior from this report alone.
- Confirm replacement manually in a change request before changing register status.
- If replacement is confirmed, update `supersedes`, `superseded_by`, architecture YAML `source_document` fields, lineage, and release planning together.
- A confirmed replacement will likely need a new architecture baseline release candidate.
