# Governance Change Request

## Change ID

`GCR-2026-050`

## Decision

On 9 September 2026 the repository maintainer instructed:

> bitte verlängere die Frist bis 12.12.2026

Extend only the legacy blocking-risk review deadline for
`joku-dev/ha-CPsWMS` from `2026-08-18T00:00:00Z` through 12 December 2026,
23:59:59 Europe/Berlin (`2026-12-12T22:59:59Z`). The original decision and
deadline remain recorded in GCR-2026-043. This extension takes effect on the
decision date and does not retroactively clear previously failed validations.

## Artifact Intake Classification

| Field | Value |
|---|---|
| Artifact | Maintainer decision extending an existing risk-review deadline |
| Type | governance change record and model metadata |
| Owner | Repository Owner; action owner Governance Platform Lead |
| Source Document Intake required | no; no source or source-register change |
| Model | `model/enforcement/blocking-mode-alignment.yaml` |
| Evidence contract impact | none |
| Runtime governance impact | none |
| Repository validation impact | legacy record remains active until the new deadline |
| Release impact | none |

## Scope And Remaining Review

The instruction authorizes this deadline extension, not a completed review by
all accountable roles, a new blocking activation, or a change of consumer mode.
Keep `acknowledged_pending_review`, `preserve_without_new_approval`, and
`enforcement_change_authorized: false`.

The five gaps remain: minimum Trust, clean replay verification, current clean
Typed Evidence, a representative intake observation sample, and accountable
approval. Repository Owner, Governance Platform Lead, Security, and Release
Manager remain the required reviewers. They must record the substantive review
outcome before the new deadline using the existing Blocking Mode Alignment
process.

No source is promoted, no historical evidence is removed, and no OPA policy,
consumer workflow, repository protection, or released baseline is changed.

## Derived Artifacts And Validation

Regenerate the blocking-mode-alignment report and source-lineage, change-impact,
graph, and viewer projections affected by this change record. Verify the
deadline boundary, run the pinned bootstrap and full validation suite, and
build the documentation in strict mode before merge.

## Release Decision

No baseline release is required.
