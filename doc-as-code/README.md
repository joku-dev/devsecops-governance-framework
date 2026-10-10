# Doc-as-Code component

This directory contains the reusable publication machinery for Git-authored
documents in this repository.

## Component boundary

| Concern | Location |
|---|---|
| Publication source and reader-facing navigation | `docs/publishing/` |
| Publication catalog and order | `publication.yaml` beside each publication |
| Individual requirements | `requirements/*.md` with validated YAML frontmatter |
| Publication and requirement contracts | `doc-as-code/schemas/` |
| Shared HTML styling | `doc-as-code/styles/` |
| Renderer | `doc-as-code/scripts/build_publication.py` |
| Renderer and PDF toolchain pins | `doc-as-code/toolchain.env` |
| Generated local output | `build/doc-as-code/` (ignored by Git) |
| Shared CI build action | `doc-as-code/action.yml` |
| CI entrypoints | `.github/workflows/doc-as-code-preview.yml` and `publish-docs.yml` |

The component also renders the canonical governance requirement catalog from
`docs/publishing/governance-requirement-catalog/publication.yaml`. That
publication is generated from the active catalog revisions by
`scripts/manage_requirement_lifecycle.py generate-publication`. Its
`publication_class: normative` identifies the content class; the Requirement
Authority Ledger still determines whether Git or an external source document
is authoritative for each migrating source.

The split is deliberate: MkDocs continues to own the repository's full
documentation tree, while the renderer, toolchain and publication styling have
their own directory boundary. GitHub Actions workflow definitions stay under
the root `.github/workflows/` path and call into this component.
Both workflows invoke the same local composite action, so tool installation
and export behavior have one implementation.

## Build

Validate the manifest, referenced files and requirement metadata without a
rendering toolchain:

```bash
python3 doc-as-code/scripts/build_publication.py --validate-only
```

Install the Pandoc release listed in `toolchain.env` and the configured PDF
engine/packages, then build the ordered publication:

```bash
python3 doc-as-code/scripts/build_publication.py
```

For CI, install the configured Pandoc archive, then pass that archive to verify
its checksum and include the verified hash in `publication-provenance.json`:

```bash
python3 doc-as-code/scripts/build_publication.py \
  --pandoc-archive /path/to/pandoc-3.12-linux-amd64.tar.gz
```

## Future extraction

The component does not own governance source documents or approval decisions.
If a later decision creates a dedicated documentation repository, this folder
is the natural home for its renderer and shared style/toolchain configuration;
selected source documents can be moved with their Git history and publication
workflow after MkDocs and governance references have a migration plan.
