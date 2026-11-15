# GCR-2026-178 — Exact-source prepared runtime package

Date: 2026-11-15. Status: implementation candidate under the portability Goal.

Classification under the [artifact intake process](../../operations/processes/new-artifact-intake-process.md): reproducible technical source/runtime distribution, bounded package admission, prepared offline dependency installation and tests. This is not a normative governance source, baseline release, signature replacement or deployment approval. It complements the exact-commit internal Git mirror path and does not activate a live VM installation.

Packages contain tracked blobs/modes and the original Git commit/tree, plus optional target-specific checksum-pinned OPA and hash-locked wheels. Admission requires an independently pinned package SHA-256, verifies every member, reconstructs the exact Git identity and uses no public dependency fallback. Private configuration, credentials, drafts, untracked files and operational databases are excluded. Prepared core evaluation is separate from scanner images/databases and VM operating-system provisioning. Actual offline and cross-platform evidence must be reported at the scope executed.
