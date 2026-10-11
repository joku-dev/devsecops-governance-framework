# GCR-2026-148 — Guided source intake and review workbench

## Summary

Add a protected, locally served AXIOM workspace so maintainers can intake a
new source version, inspect requirements beside original text, compare versions,
record unconfirmed review proposals and prepare an inspectable candidate package
or Draft-PR without manually navigating the repository structure.

## Artifact Intake Classification

| Field | Value |
|---|---|
| Artifact | Local Review Workbench, private draft schema, tests, ADR and operations guide |
| Type | executable support tool, schema, documentation |
| Target paths | `scripts/workbench/`, `scripts/serve_governance_workbench.py`, `schemas/governance-workbench-draft.schema.json`, `tests/test_governance_workbench.py`, `docs/operations/` |
| Owner | Repository maintainer / source intake reviewers |
| Full Source Document Intake required? | no; implementation introduces no source document |
| Source register updated? | no |
| New derivation allowed? | no |
| Evidence contract impact | none; local private draft format is separate |
| Runtime governance impact | none; report-only decision preparation |
| Release impact | none; no baseline release |

## Authority and scope

The user requested autonomous implementation of a webapp supporting source
intake and document review on 2026-10-11. This implements the supporting UI and
local operational tool. It does not authorize semantic provider execution,
source promotion, normative finding disposition, baseline approval or automatic
publication of private source text. The optional per-action Draft-PR adapter
requires explicit publication selection in the application.

## Impact

- Existing register and original sources remain the source of truth.
- Existing source extraction and delta functions are reused, including warnings
  and identifier-provenance classifications.
- Draft notes remain `proposal_only`; self-declared reviewer names do not create
  authenticated authority or change requirement lifecycle decisions.
- Every draft binds checkout HEAD, register hash and source hashes. Stale
  packages and altered uploaded bytes cannot be exported silently.
- Private uploads are excluded from Git/Pages. Existing public viewer, status
  indexes, OPA policies, releases and lifecycle-acceptance fingerprints are
  unchanged.
- GitHub is an optional publication adapter. Core operation also works through
  exported packets for other repository platforms.

## Validation and review focus

Run pinned bootstrap, complete repository validation and workbench integration
security tests. Review the authenticated HTTP boundary, private draft handling,
HTML escaping, archive limits, hash binding and optional PR adapter. A production
browser/enterprise acceptance and live CLI publication smoke test are separate;
this change does not claim either was completed.

## Release decision

No baseline release, no enforcement changes, no source-authority changes.

## Related implementation

- [Operations guide](../../operations/guides/governance-review-workbench.md)
- [Architecture decision](../../operations/planning/governance-review-workbench-adr.md)
