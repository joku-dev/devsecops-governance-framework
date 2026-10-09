# GCR-2026-143 — Hybrid Requirement Lifecycle

## Status

Proposed for maintainer review.

## Intent

Establish the controlled two-to-three-year transition from normative input documents to a canonical Git requirement catalog while preserving document authority until each requirement is explicitly decided and activated.

## Decision proposal

1. Introduce an Authority Ledger with four explicit authority modes.
2. Store requirement-level analysis, classification, human decision, and activation in versioned lifecycle cases.
3. Use immutable `GRQ-*` revisions as the canonical target model.
4. Require separate authorization for derived artifacts, releases, and blocking enforcement.
5. Seed migration cases for the six approved sources without approving their 867 proposals or changing their current authority.
6. Generate a catalog-controlled Doc-as-Code publication and reviewable HTML, Word, and PDF previews from active catalog revisions.

## Impact

- Adds models, schemas, CLI, validation, tests, operating guidance, CI reporting, and catalog publication previews.
- Generalizes the existing Doc-as-Code contracts and composite action so explanatory and canonical normative publications use the same pinned renderer.
- Does not change controls, policies, runtime enforcement, released baselines, or source text.
- The six source documents remain authoritative while their ledger mode is `migration_in_progress`.

## Human decisions still required

Each proposal needs a named reviewer decision. Completion of each source migration needs a catalog release reference and explicit authority transition. Any runtime blocking decision remains separate.

## Validation

`./scripts/validate_all.sh` validates schemas, lifecycle invariants, repository behavior, and unit tests.
