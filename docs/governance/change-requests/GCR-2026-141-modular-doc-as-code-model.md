# GCR-2026-141 — Modular Doc-as-Code Model

## Status

Proposed for maintainer review.

## Classification

- Change class: explanatory documentation, publication workflow and validation schema
- Governance behavior: unchanged
- Runtime enforcement: unchanged
- Released baselines: unchanged
- Source-document intake: not applicable; no external or normative source is introduced

## Intent

Evolve the accepted Git-native publication pilot into a professional target
model in which chapters and requirements can be maintained separately while a
versioned manifest controls the complete publication.

## Affected artifacts

- `docs/publishing/doc-as-code-pilot/`
- `doc-as-code/scripts/`
- `doc-as-code/schemas/`
- `.github/workflows/doc-as-code-preview.yml`
- `.github/workflows/publish-docs.yml`
- `docs/operations/planning/doc-as-code-architecture-decision.md`
- navigation and automated tests

## Decision proposal

1. Use `publication.yaml` as the ordered publication contract.
2. Store every publication requirement in a separate Markdown file with a
   stable ID and schema-validated metadata.
3. Keep the pilot explanatory. Empty source and control references explicitly
   record that no normative lineage is claimed.
4. Generate HTML, DOCX, PDF, a requirement index and source/output provenance
   from one source set.
5. Show changed requirements in the pull-request job summary.
6. Preserve the `doc-as-code/` component boundary so the system can later move
   to a dedicated repository with its history and contracts.

## Acceptance evidence

- Manifest and requirement schemas validate.
- References stay inside the publication directory and IDs are unique.
- Unit tests verify order, assembly and rejection of uncontrolled metadata.
- The full repository validation succeeds.
- CI builds all three publication formats from the same manifest.

## Open decision

A branded Word template is deferred until the maintainer provides or approves
the logo, fonts, colors, page geometry, headers and footers. The neutral output
remains deterministic meanwhile.
