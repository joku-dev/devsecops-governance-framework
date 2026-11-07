# GCR-2026-151 — Explicit requirement identifiers at intake

## Intent and authority

The maintainer requested on 6 November 2026 that intake stop inferring
requirements from document prose. Admit explicit requirement declarations such
as `DSCB-L1-REQ-001` instead. Modal keywords, version history, synthetic
extraction row IDs and references must not create requirements.

## Artifact intake classification

- Type: intake implementation, agent instructions, review-support reports and documentation.
- Full Source Document Intake: not required; no source or source-register changes.
- Runtime policy/enforcement and released baseline impact: none.
- Existing lifecycle cases, decisions, source bytes and retained DCR evidence: preserved.

## Change

Use one explicit-declaration parser for intake deltas, the private Workbench,
new lifecycle imports and new DCR structural inventories. Preserve actual
requirement labels and original source locators. Distinguish declarations from
reference-only mentions and traceability mappings. Identifier authorship and
source authority remain separate: unverified explicit identifiers do not gain
P1 or normative approval. An empty extraction is not a consistency claim.

No new `inferred_candidate` items are produced. Legacy prose counters remain
zero for compatibility. Historical lifecycle counts continue to include
previous proposals; this change does not retroactively reject their decisions.

## Validation

Regression cases cover labelled declarations, all existing DSCB levels,
unlabelled obligations, synthetic row IDs, references, mapping tables, Markdown
formatting and supported source formats. Exercise Workbench upload/export,
replacement comparisons and lifecycle imports. Run repository validators and
the required pinned bootstrap/full validation; record toolchain limitations
separately from test results.

Validation environment: pinned Python dependencies and OPA 1.18.2 on Python
3.11.14, optional PDF parser from the repository lock, and temporary OpenSSL
3.5.4 for the existing Ed25519 verification (the system LibreSSL does not
support that command). The Node-CLI test is skipped locally; JavaScript syntax
and escaping are separately exercised through the available Node runtime.

Final validation: pinned bootstrap completed; `validate_all.sh` passed OPA,
runtime governance, repository governance and evidence-agent provenance
validation, then 802 unit tests (one Node-CLI skip). The separate Node runtime
passed syntax and the same escaping assertion against the current JS file.

## Release decision

No baseline release or source promotion. Human source, requirement, consistency
and enforcement decisions remain within their existing contracts.
