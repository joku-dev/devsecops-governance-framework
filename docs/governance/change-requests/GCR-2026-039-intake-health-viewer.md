# Governance Change Request

## Summary

- Add a dedicated Intake Health section to the static governance status viewer.
- Present report-only event counts, success rate, duration percentiles,
  operational records, dimensional metrics, and latest-result age.
- Keep the committed `status/intake-health.json` projection as the only metric
  source and make the absence of an approved SLO explicit.

## Change ID

```text
GCR-2026-039
```

## Source Document Intake

| Question | Answer |
|---|---|
| Full source-document intake required? | no |
| New or updated source document? | no |
| Reviewed non-source paths | viewer generator and output, Intake Health projection, demo runbook, architecture and management documentation |
| Register updated? | no |
| Supersedes existing source? | no |
| Possible duplicate or replacement candidate? | no; this is a projection presentation increment |
| Similarity assessment | `not_relevant` |

## Artifact Intake Classification

| Artifact | Type | Target | Impact |
|---|---|---|---|
| Intake Health viewer section | generated read-only presentation | `scripts/generate_status_viewer.py`, `generated/viewer/status-viewer.html` | additive |
| Viewer regression test | validation evidence | `tests/test_result_ledger.py` | additive |
| Demo and operations documentation | runbook and guides | `docs/demos/`, `docs/operations/` | explanatory |
| Architecture and management updates | governance documentation | `docs/governance/` | explanatory |

Owner: Governance Platform Maintainers. Schema and evidence-contract impact are
none. Runtime impact is report-only presentation. Release impact is none.

## Why This Change Is Needed

The machine-readable Intake Health projection is operationally useful, but a
demo or operator should not need to interpret the raw JSON. The viewer needs a
professional read-only presentation that preserves the projection's explicit
window and avoids turning limited observations into an SLO verdict.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | none |
| DevSecOps controls | none |
| Platform model | none |
| Architecture governance | architecture document lists Intake Health as a viewer concern |
| OPA policies | none |
| Schemas and evidence contracts | none |
| Viewer, status indexes or intake | viewer reads existing projection; indexes and intake behavior unchanged |
| Release package or baseline | none |
| Downstream repositories | none |

## Governance Behavior

- [x] Report-only presentation behavior

Invariants:

- the viewer consumes rather than recalculates the health projection
- no success-rate or duration threshold creates a health verdict
- `no_data` is displayed as observation state, not success
- conflicts and Collection Attempts retain their separate detail sections
- latest-result selection and Evidence Trust remain unchanged
- generated viewer output remains static and read-only
- released baseline packages remain unchanged

## Release Decision

- [x] No release required

The viewer is a central presentation projection and does not change a released
consumer workflow or baseline package.

## Validation Plan

- [x] targeted viewer regression test
- [x] generated viewer content inspection
- [x] `python3 scripts/run_demo.py`
- [x] `python3 scripts/validate_runtime_governance.py`
- [x] `python3 scripts/validate_governance_repo.py`
- [x] `python3 -m unittest discover -s tests`
- [x] `mkdocs build --strict`

## Reviewer Notes

Review focus: clear report-only language, no hidden metric recalculation, useful
dimensional and age presentation, demo consistency, static output regeneration,
and absence of SLO, blocking, schema, or release impact.
