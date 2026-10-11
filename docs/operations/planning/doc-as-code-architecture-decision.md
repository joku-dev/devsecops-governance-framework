# ADR-DAC-001 — Git-native Documentation and Publication

**Status:** Modular pilot target proposed for review
**Date:** 2026-10-09
**Change requests:** [GCR-2026-140](../../governance/change-requests/GCR-2026-140-doc-as-code-pilot.md), [GCR-2026-141](../../governance/change-requests/GCR-2026-141-modular-doc-as-code-model.md)

## Context

The repository already has a MkDocs site and several manually maintained
publication packages. `scripts/render_governance_documents.py` is a narrow
renderer for selected governance documents; it creates a simplified HTML view
and only creates DOCX when Pandoc happens to be installed. It does not provide
a governed PDF path or a common publication record.

The repository also handles external governance sources, structured control
models, generated reports and explanatory prose. These classes must not be
collapsed into one authoring model: external source authority remains subject
to source-document intake, structured governance data remains model-owned, and
generated reports remain generator-owned.

## Decision

1. **Authored explanatory documentation:** Markdown in the repository is the
   canonical editable source for an explicitly selected publication. Git
   history and pull requests provide versioning, review and change traceability.
2. **Structured governance data:** controls, requirements, architecture
   markers, policies, schemas and evidence contracts continue to use their
   existing structured sources. Their derived reports are not manually
   authored publications.
3. **External source material:** documents under
   `docs/governance/source-documents/` and the source-document register retain
   the authority assigned by the existing intake and review processes. This
   pilot neither imports nor promotes a source document.
4. **Publication scope:** the pilot uses one explanatory publication under
   `docs/publishing/`. A schema-validated manifest declares its identity,
   version, classification, formats and ordered content. Chapters and stable,
   individually editable requirement files remain inside its directory. The
   exporter refuses paths outside that publication area.
5. **Component boundary:** renderer, shared publication styles and pinned
   toolchain configuration live together under `doc-as-code/`. GitHub Actions
   calls the component through its local composite action. The authored source
   remains in `docs/publishing/` so it participates in the existing MkDocs site
   and review navigation.
6. **Rendering:** MkDocs remains the website renderer. A version-pinned Pandoc
   build creates standalone HTML, DOCX and PDF from the same ordered source set.
   The Pandoc archive is checksum-pinned. PDF uses XeLaTeX on the Ubuntu 24.04
   runner, and its exact version is recorded. Export files and a SHA-256
   provenance record are build outputs, not a second editable copy.
7. **Publication boundary:** pull requests build reviewable export artifacts.
   The existing protected `main` Pages workflow may publish the pilot download
   files only after merge. No governance baseline or control release is made.
8. **Authority and approval:** publication format does not change document
   authority. A document that proposes policy, mandatory controls, architecture
   rules or baseline behavior must go through the applicable governance and
   source-review decision before it is treated as normative.

## Consequences

- Authors can make and review changes in Git while readers can receive HTML,
  Word and PDF renderings from one manifest-controlled source set.
- Every build records all source paths and hashes, stylesheet hash, Git revision,
  renderer version and hashes of the generated files. The PDF engine version
  makes changes in the runner's TeX packages visible in provenance. CI also
  verifies and records the Pandoc release archive hash.
- The pilot checks the actual rendering toolchain instead of silently
  omitting missing formats.
- Binary exports are publication products, not Git source files; the GitHub
  Actions artifact and Pages site retain the rendered versions.
- Requirement metadata is schema-validated and produces a machine-readable
  index. Pull requests receive a focused summary of changed requirements.
- The default Pandoc Word styles are used for this pilot. A branded reference
  DOCX, repository-wide publication catalog, localization, PDF accessibility
  certification and formal document-control approval are follow-up decisions.
- Model-to-document generation remains a separate capability and does not
  replace the manually authored Markdown pilot.
- The repository module boundary is ready for a later extraction, but the
  publication source remains integrated with this repository's MkDocs and
  governance review process until a separate repository is explicitly chosen.

## Pilot Acceptance Boundary

The modular target is technically in scope for review when one manifest and all
declared files validate and build as HTML, DOCX and PDF; generated content carries a provenance
record; PR builds expose the files for review; and the merged Pages build
places download links beside the readable source page. The artifacts remain
explanatory and do not assert compliance or normative approval.
