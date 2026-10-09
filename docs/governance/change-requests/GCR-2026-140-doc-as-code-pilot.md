# GCR-2026-140: Git-native Documentation and Publication Pilot

**Status: implemented locally for maintainer review; merge and public deployment pending.**

## Summary

- Record a Git-native documentation architecture that keeps Markdown, structured governance models and external source documents in their existing authority boundaries.
- Add one explanatory Markdown publication and build HTML, DOCX, PDF and SHA-256 provenance from that single source.
- Pin Pandoc 3.12 by upstream release checksum and require XeLaTeX so all declared formats either build or fail visibly.
- Make pull requests produce a short-lived review artifact; add the exports to the existing Pages publication after a protected merge to `main`.
- Keep the broader model-to-document work package, normative source promotion, baseline changes and new enforcement separate.

## Change ID

```text
GCR-2026-140
```

## Source Document Intake

| Question | Answer |
|---|---|
| Full source-document intake required? | no |
| New or updated source document? | no; the pilot is explanatory publication material |
| Source document path | not applicable |
| Reviewed non-source path | `docs/publishing/doc-as-code-pilot.md`, architecture decision and publication workflow |
| Register updated? | no |
| Supersedes existing source? | no |
| Possible duplicate or replacement candidate? | no |
| Similarity assessment | not_relevant |
| Source status | not applicable |

## Artifact Intake Classification

| Field | Value |
|---|---|
| Artifact name | Git-authored documentation publication pilot |
| Artifact type | documentation / workflow / generated publication |
| Target path | `docs/operations/planning/doc-as-code-architecture-decision.md`; `docs/publishing/doc-as-code-pilot.md`; `doc-as-code/`; `.github/workflows/doc-as-code-preview.yml`; `.github/workflows/publish-docs.yml` |
| Owner | Repository Maintainer / Governance Platform Lead |
| Source Document Intake required? | no |
| Evidence contract impact | none; the publication provenance is a build record, not governance evidence |
| Runtime governance impact | none |
| Release impact | none |
| Validation required | Pandoc/PDF build, Pages strict build, rendered export and provenance review, repository validation before merge |

## Why This Change Is Needed

The repository already publishes Markdown through MkDocs and retains manually
managed Word/PDF materials. The current governance renderer uses a simplified
Markdown-to-HTML implementation, skips DOCX when Pandoc is missing, and has no
PDF path. That leaves source ownership, rendering behavior, export provenance
and reviewer access split across different practices.

This pilot establishes one explicit Git source and a pinned renderer path for
all three publication formats. It is intentionally limited to explanatory
content while the repository reviews the workflow and output quality.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | None |
| DevSecOps controls | None |
| Platform model | None |
| Architecture governance | Documentation architecture decision only; no runtime architecture model changes |
| OPA policies | None |
| Schemas and evidence contracts | None; provenance manifest is publication metadata only |
| Viewer, status indexes or intake | None |
| Release package or baseline | None |
| Downstream repositories | None |

## Derived Artifacts

- Standalone HTML, DOCX and PDF exports for `DOC-AS-CODE-PILOT-001`.
- `publication-provenance.json`, containing the source path and SHA-256, Git
  revision, Pandoc and XeLaTeX versions, and output SHA-256 values.
- A PR artifact retained for 14 days and a Pages download bundle generated
  from the merged source.

## Governance Behavior

- [x] Documentation-only
- [ ] Report-only governance behavior
- [ ] Blocking governance behavior
- [ ] Release packaging only

Publication metadata does not confer normative authority. A later use for
mandatory or baseline content requires the normal governance review.

## Release Decision

- [x] No release required
- [ ] Release candidate required
- [ ] Patch baseline release required
- [ ] Minor baseline release required
- [ ] Major baseline release required

## Validation Plan

- [ ] Build all three formats using Pandoc 3.12 and XeLaTeX.
- [ ] Review page layout and content in the DOCX/PDF exports.
- [ ] Verify source/output hashes and metadata in the provenance record.
- [x] Run `mkdocs build --strict` and repository validation before merge.
- [ ] Review the PR artifact and the Pages download links after merge.

## Reviewer Notes

- Architecture details and explicit boundaries are in
  `docs/operations/planning/doc-as-code-architecture-decision.md`.
- The renderer, shared styling and toolchain configuration are grouped in
  `doc-as-code/`; publication sources remain under `docs/publishing/` for the
  existing MkDocs and governance navigation.
- This does not start or complete the separate model-to-document backlog
  `WP-MDG-001`; that effort remains deferred.
- The first pilot uses Pandoc's default DOCX styles. A branded reference DOCX,
  expansion to additional publications and formal accessibility certification
  need a follow-up decision after the rendering review.
- Pandoc and XeLaTeX are build-time dependencies. The workflow pins the Pandoc
  archive to its upstream SHA-256; XeLaTeX and the Liberation Sans/lmodern
  fonts/packages are installed on the Ubuntu 24.04 runner. The PDF engine
  version is captured in the provenance manifest and comes from the runner's
  package repositories. Byte-for-byte PDF identity across package updates is
  not claimed.
- Local pre-PR validation: `./scripts/bootstrap_validation_env.sh`, the OPA,
  runtime-governance and repository-governance validators, and
  `.venv-docs/bin/mkdocs build --strict` passed. All 742 unit tests passed with
  the pinned validation environment on `PATH` and commit signing disabled only
  for test-created repositories; the initial run hit the machine-wide Git
  commit-signing setting in one temporary-repository test.
