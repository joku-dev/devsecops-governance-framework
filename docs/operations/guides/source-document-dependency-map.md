# Source Document Dependency Map

## Purpose

This page explains which files in `docs/governance/source-documents/` currently
support governed models and which files are held for intake or human review.
The generated report at `generated/reports/source-lineage-report.md` lists the
current direct artifact links, shared intake outputs, and unresolved source
references.

The reporting change is recorded in
[GCR-2026-149](../../governance/change-requests/GCR-2026-149-source-lineage-report-clarification.md).

The report separates direct model or release lineage from shared intake and
impact reports. A shared report may mention every registered source, but it is
not a direct derivation from every source. Missing or unregistered source
counts remain informational; the source-lineage validator still fails when a
referenced derived artifact is missing.

## Current disposition

There are 15 registered source files, and all 15 exist. There are no unregistered
files in the source-document directory. The files fall into three groups:

| Group | Sources | Current use |
|---|---|---|
| Approved, partially effective | `DSCB-STD-REQ-001`, `PRA-STD-REQ-001` | Inputs to current DevSecOps controls, platform models, traceability, policies and related artifacts. The authority ledger records 46 of 55 DSCB requirements and 38 of 56 PRA requirements as effective; the rest remain unresolved. |
| Approved, not yet effective | `ARCH-TPL-REQ-001`, `ARCH-EA-REQ-001`, `ARCH-SA-REQ-001`, `ARCH-PA-REQ-001` | Approved as normative sources by GCR-2026-142. Their 756 analyzed requirements have no effective decisions in the authority ledger yet. Approval permits future governed derivation; it does not mean the requirements are implemented. |
| Review or candidate | Three `review` sources and six `candidate` sources | Retained for review, replacement assessment, and intake. Candidates do not authorize normative runtime derivation. Some, such as the CISO catalog, have explicitly non-normative review models and packets. |

The three `review` sources are the DevSecOps Policy extract, DevSecOps Directive
extract, and integrated SDD architecture extract. The policy and directive
extracts feed their working governance documents and document-to-control
traceability. The SDD extract is referenced by the current working architecture
models, while its source status remains `review`.

## Historical reference to the retired example

The released architecture baseline `architecture-baseline-l1-v0.1.0` contains
five source-model files that refer to
`docs/governance/source-documents/ARCH-SDD-SRC-001.public.md`. It was one of
the `*.public.md` example placeholders intentionally removed in the source
cleanup recorded by PR #244 (`430550f`). The placeholders were replaced by
real source documents; for this architecture source the replacement is the
requirements extract at
`docs/governance/source-documents/ARCH-SDD-SRC-001.requirements.md`. The
register and current working architecture models use that real source.

The immutable v0.1.0 release snapshot still records the former example path.
The lineage report surfaces that literal historical reference because the
removed path is not registered today. It is not a missing current source or a
missing derived artifact. This PR leaves the released package unchanged; if a
future architecture baseline is issued, its source metadata should use the real
requirements extract.

## Cleanup decision

Do not delete or move any source file based on the current inventory. All files
are registered and each has an identified intake or governance purpose. Keep
candidate files in place until their recorded review decides whether they are
accepted, replaced, superseded, or retired. Resolve the historical architecture
reference through a governed follow-up before changing release provenance.

Refresh the generated dependency view after source, register, model, or release
changes:

```bash
python3 scripts/generate_source_lineage_report.py
python3 scripts/generate_governance_change_impact_report.py
```
