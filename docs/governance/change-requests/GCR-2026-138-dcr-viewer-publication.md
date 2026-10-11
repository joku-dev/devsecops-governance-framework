# GCR-2026-138: One-Time Publication of the Redacted DCR Pilot Projection

## Maintainer Decision

On 9 October 2026, the repository maintainer authorized one public publication
of the existing, redacted Document Consistency Review projection for
`dcr-semantic-pilot-20261007-run2`, through the merge and Pages deployment of
PR #243. This is a narrow exception to the general publication restriction in
`dcr-rollout-0002` and GCR-2026-133.

The completed pilot remains `partial`. Publication does not approve a source,
confirm consistency, resolve a finding, assess implementation coverage, or
approve production rollout.

## Summary

- Correct the Viewer input from the provider `not_run` template to the validated, completed Phase 2 pilot report.
- Publish only the existing public allowlist projection on the public GitHub Pages site.
- Keep provider execution, future or repeated publication, scheduling, blocking, and production rollout unauthorized.

## Decision Scope

| Field | Value |
|---|---|
| Review | `dcr-semantic-pilot-20261007-run2` from `docs/examples/document-consistency-review-phase2-live-pilot-report.json` |
| Overall status | `partial` |
| Execution | `completed`; no new provider call is authorized by this decision |
| Source scope | `DSCB-STD-REQ-001` and `PRA-STD-REQ-001`, the two registered requirements-only pilot sources in the report manifest |
| Formal validation | `pass` |
| Semantic review | `partial`; zero finding records in this report |
| Human decisions | `not_run` |
| Implementation coverage | `not_assessed` |
| Freshness | Derived from the manifest and current source hashes; it is not a claim that the review was rerun recently |
| Destination | Public Governance Viewer on GitHub Pages |
| Duration | The projection may remain available as part of the published site until it is replaced or the publication is removed |

The publication contains only the existing `public_redacted` allowlist: review
ID, overall and section states, source IDs and registered versions, execution
status, source-hash freshness, finding metadata, and explicit limitations. The
current report contains no finding entries. The Viewer reads this fixed report
path; it does not discover or publish new review IDs automatically. A different
report or a changed publication scope requires a new decision.

It contains no source excerpts, complete source text, provider response, semantic
prose, recommendation, provider/model identifier, or human decision content.
The Viewer remains read-only and report-only. The output expressly makes no
consistency claim.

## Boundaries

This decision does not authorize:

- additional provider runs or processing of other source documents;
- publication of future review results or automated publication on later runs;
- scheduled or automatic execution;
- normative source approval, promotion, or derivation;
- implementation-coverage conclusions;
- blocking enforcement or production rollout;
- a reusable provider, model, data-flow, or retention profile.

The historical assessment `dcr-rollout-0002` and acceptance GCR-2026-133 remain
unchanged. Their general restrictions still apply outside this single projection.
The `publication_and_automation` readiness criterion remains open for any broader
capability. Pages rebuilds may continue to display this fixed report until it is
replaced or publication is removed; that does not authorize a new review result.

## Artifact Intake Classification

| Field | Value |
|---|---|
| Artifact | One-time publication decision for the DCR report projection |
| Artifact type | Governance decision record |
| Target path | `docs/governance/change-requests/GCR-2026-138-dcr-viewer-publication.md` |
| Owner | Repository Maintainer (`joku-dev`) |
| Source Document Intake required? | No; no source document is added or changed |
| Evidence contract impact | None |
| Runtime governance impact | Report-only presentation of an existing validated report |
| Release impact | None |
| Validation required | Viewer projection tests, repository validation, full CI, and successful Pages deployment |

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | None |
| DevSecOps controls | None |
| Platform model | None |
| Architecture governance | None |
| OPA policies | None |
| Schemas and evidence contracts | None |
| Viewer | Correct the selected report; publish only its redacted allowlist |
| Result indexes and intake | None; no status index is changed |
| Release package or baseline | None |
| Downstream repositories | None |

## Derived Artifacts

- `generated/viewer/app/data.json` is regenerated during the Viewer build from the validated pilot report; it is not hand-edited or committed as an independent decision record.
- GitHub Pages publishes the regenerated Viewer after PR #243 merges to `main`.

## Governance Behavior

- [x] Report-only governance behavior
- [ ] Blocking governance behavior
- [ ] Release packaging only

This is a one-time publication of an existing result. It does not start a review,
change review state, or trigger consumer action.

## Release Decision

- [x] No release required

## Validation Plan

- [x] Focused Document Consistency Review projection tests
- [ ] Repository and full GitHub CI validation
- [x] Strict documentation build
- [ ] Confirm the Pages deployment and inspect the published projection

## Reviewer Notes

The public Viewer has the same visibility as the public repository. The
projection's explicit allowlist and no-consistency-claim boundary are part of
this decision. Before reporting completion, verify the deployed page reflects
the intended report and keeps the separate human-decision and implementation
coverage states visible as `not_run` and `not_assessed`.
