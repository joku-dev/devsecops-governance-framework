# Governance Change Request

## Summary

- Add a versioned governance graph schema and deterministic derived graph.
- Add an interactive, dependency-free graph view to the static status viewer.
- Preserve Git, status indexes, result snapshots, and released baselines as authoritative sources.
- Keep all runtime governance behavior report-only and read-only.

## Change ID

```text
GCR-2026-033
```

## Source Document Intake

| Question | Answer |
|---|---|
| Full source-document intake required? | no |
| New or updated source document? | no |
| Reviewed non-source path | `schemas/`, `scripts/`, `generated/`, `tests/`, `docs/operations/status/` |
| Register updated? | no |
| Supersedes existing source? | no |
| Possible duplicate or replacement candidate? | no |
| Similarity assessment | `not_relevant` |

## Artifact Intake Classification

| Artifact | Type | Target | Impact |
|---|---|---|---|
| Graph contract | schema | `schemas/governance-graph.schema.json` | additive |
| Graph generator | generated-output tooling | `scripts/generate_governance_graph.py` | report-only |
| Graph snapshot | generated | `generated/graph/governance-graph.json` | report-only |
| Viewer projection | generated UI | `generated/viewer/status-viewer.html` | report-only |
| Usage guide | documentation | `docs/operations/status/governance-intelligence-graph-viewer.md` | none |

Owner: Governance Platform Maintainers. Source Document Intake is not required. Release impact is `none`.

## Why This Change Is Needed

The existing static viewer summarizes status well but makes cross-domain relationships difficult to explain during a professional demo. A graph projection lets users navigate lineage and operational evidence while keeping the governed JSON artifacts explicit and auditable.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | none |
| DevSecOps controls | none |
| Platform model | additive derived presentation only |
| Architecture governance | none |
| OPA policies | none |
| Schemas and evidence contracts | new non-breaking graph schema |
| Viewer, status indexes or intake | viewer enhancement; intake regenerates graph |
| Release package or baseline | none |
| Downstream repositories | none |

## Derived Artifacts

- `generated/graph/governance-graph.json`
- `generated/viewer/status-viewer.html`
- regenerated source-lineage and governance-change-impact reports

## Governance Behavior

- [x] Report-only governance behavior

Invariants: no write-back, no change to official latest-result selection, no historical deletion, no Trust escalation, and no enforcement change.

## Release Decision

- [x] No release required

The change does not alter a released baseline package, reusable released workflow, control, or OPA decision.

## Validation Plan

- [x] `python3 scripts/validate_runtime_governance.py`
- [x] `python3 scripts/validate_governance_repo.py`
- [x] `python3 -m unittest discover -s tests`
- [x] Source lineage regenerated
- [x] Viewer regenerated
- [x] `mkdocs build --strict`
- [x] Demo flow checked with current `ha-CPsWMS` results

## Reviewer Notes

Review focus: deterministic identifiers, absence of dangling edges, source-of-truth wording, current-main selection, keyboard-accessible node inspection, offline rendering, and absence of baseline or blocking changes.
