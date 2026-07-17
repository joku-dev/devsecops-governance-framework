# Governance Change Request

## Summary

- Make central result snapshot writes append-only and idempotent.
- Quarantine conflicting writes without replacing the original snapshot.
- Evaluate replay identity and incompatible digest reuse as report-only Trust checks.
- Correct result-index source-file pairing so payload and provenance path remain bound while sorting.

## Change ID

```text
GCR-2026-034
```

## Source Document Intake

| Question | Answer |
|---|---|
| Full source-document intake required? | no |
| New or updated source document? | no |
| Reviewed non-source paths | `scripts/`, `schemas/`, `status/`, `tests/`, `docs/operations/evidence/` |
| Register updated? | no |
| Supersedes existing source? | no |
| Possible duplicate or replacement candidate? | no |
| Similarity assessment | `not_relevant` |

## Artifact Intake Classification

| Artifact | Type | Target | Impact |
|---|---|---|---|
| Result-ledger helper | implementation | `scripts/lib/result_ledger.py` | report-only hardening |
| Conflict record | evidence | `status/intake-conflicts/` | additive |
| Conflict schema | schema | `schemas/intake-conflict.schema.json` | additive |
| Replay projection | evidence schema/index/viewer | existing Trust and index contracts | additive optional |

Owner: Governance Platform Maintainers. Evidence-contract impact is additive. Runtime impact is report-only. Release impact is none.

## Why This Change Is Needed

The central result registry must not silently rewrite historical evidence. Re-intake of identical evidence should be harmless, while a different payload for an existing snapshot identity must remain visible for review. Replay evaluation must distinguish an idempotent retry from digest reuse across an incompatible decision context.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | none |
| DevSecOps controls | none |
| Platform model | none |
| Architecture governance | none |
| OPA policies | none |
| Schemas and evidence contracts | optional replay details and new conflict schema |
| Viewer, status indexes or intake | append-only writes, corrected path binding, replay/conflict display |
| Release package or baseline | none |
| Downstream repositories | none; producer payloads unchanged |

## Derived Artifacts

- regenerated result indexes
- regenerated status viewer
- regenerated source-lineage and governance-impact reports

## Governance Behavior

- [x] Report-only governance behavior

Invariants:

- existing snapshots are never overwritten by automated or manual intake
- identical evidence identity is an idempotent no-op
- conflicting evidence is quarantined and does not replace `latest_result`
- replay findings do not change governance outcomes or Evidence Trust integrity level
- mainline, branch, pull-request, and manual selection semantics remain unchanged

## Release Decision

- [x] No release required

No downstream producer field, released workflow, baseline, control, or OPA rule changes.

## Validation Plan

- [x] `python3 scripts/validate_runtime_governance.py`
- [x] `python3 scripts/validate_governance_repo.py`
- [x] `python3 -m unittest discover -s tests`
- [x] Index source-file regression covered
- [x] Idempotent and conflicting writes covered
- [x] Replay contexts covered
- [x] Viewer regenerated
- [x] `mkdocs build --strict`

## Reviewer Notes

Review focus: immutable history, portable conflict records, replay-context compatibility, unchanged latest-state selection, additive schema compatibility, and absence of blocking behavior.
