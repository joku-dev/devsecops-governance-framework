# Documentation and capability review, 17 September 2026

## Scope

This review compared the repository's current documentation and all 24 existing
README files with the versioned implementation and status projections at
`a74e06708c622f98f2699e136accbec9838c41ab`.

The review covered 301 Markdown documents under `docs/`, the primary navigation
pages, the two function inventories, operational status and evidence guidance,
pipeline adapter documentation, OPA documentation and status-store guidance.
Searches for superseded run IDs, release links and implementation labels were
combined with file inventory, current JSON indexes and the required validation.

## Current evidence used

| Area | Verified state |
|---|---|
| DevSecOps baseline | `l1-baseline-v1.1.3`; ha-CPsWMS run `35131186298`, pass, 16/16 applicable controls |
| Architecture baseline | `architecture-baseline-l1-v0.1.0`; ha-CPsWMS run `35131185047`, pass, 4/4 gates |
| Measured L1 | run `35241262722`; 5 measured, 6 partial, 2 findings, 3 gaps; 58 passing tests |
| Typed evidence | run `35241262722`; integrity-verified vulnerability and CycloneDX SBOM evidence for five images |
| Control assurance | 16 controls; 7 complete/integrity-verified, 6 partial and 3 missing/unverified |
| Intake health | 11 successful events, no failed or partial events, no open collection attempts and two quarantined conflicts in the current projection |
| Repository implementation | 138 scripts/modules, 21 GitHub workflows, 15 OPA modules and 98 JSON schemas |

## Changes made

- Current entrypoints now link the v0.2.0 adoption/operations release and the
  primary Governance Workspace.
- Current demo tables use the accepted 16 September governance runs and identify
  the separate 17 September measured-evidence run.
- The root README and function catalog describe central intake, typed evidence,
  SBOM Trust, measured L1, per-control assurance, lifecycle operation and the
  actual maturity of platform adapters.
- Evidence and viewer guidance explains the separate selection rules and the
  current 58-test, five-image evidence set.
- Status stores now have local README guidance for append-only history, Trust
  boundaries and official latest selection.
- The OPA README lists all current DevSecOps and architecture policy modules.

## Historical-document rule

Released baseline packages, release statements, dated reference runs, earlier
rollout records and delivered publication editions retain the claims and run IDs
that applied when they were created. Where a current navigation page links such
material, it labels it historical. This prevents a documentation refresh from
rewriting audit history.

## Decision boundary

This review changes explanations and navigation only. It does not alter a
released baseline, policy outcome, schema, evidence snapshot, official index,
workflow enforcement mode, lifecycle acceptance or consumer configuration.
