# GCR-2026-142 — Normative Source Approval

## Summary

- Record the human maintainer decision to approve six registered requirements
  extracts as normative governance sources.
- Change their register status from `intake` to `approved`.
- Preserve all source bytes, identifiers, lineage, existing derived artifacts,
  runtime behavior and released baselines.
- Keep all candidate and active-review sources in their existing states.

## Change ID

```text
GCR-2026-142
```

## Source Document Intake

| Question | Answer |
|---|---|
| Full source-document intake required? | yes; the source-document register changes |
| New or updated source document? | no source bytes change; six existing registrations receive a human approval decision |
| Source document path | `docs/governance/source-documents/DSCB-STD-SRC-001.requirements.md`; `PRA-STD-SRC-001.requirements.md`; `ARCH-TPL-SRC-001.requirements.md`; `ARCH-EA-SRC-001.requirements.md`; `ARCH-SA-SRC-001.requirements.md`; `ARCH-PA-SRC-001.requirements.md` |
| Register updated? | yes |
| Supersedes existing source? | no |
| Possible duplicate or replacement candidate? | no; the six sources were already accepted at intake |
| Similarity assessment | existing independent sources; no replacement decision in this change |
| Source status | `approved` |

## Human Decision

On 9 October 2026, the repository maintainer explicitly directed that the
following registered sources be treated as normative:

1. `DSCB-STD-REQ-001` — DevSecOps Control Baseline Requirements Extract
2. `PRA-STD-REQ-001` — Platform Reference Architecture Requirements Extract
3. `ARCH-TPL-REQ-001` — Architecture Templates and Checklists Requirements Extract
4. `ARCH-EA-REQ-001` — Enterprise Architecture Requirements Extract
5. `ARCH-SA-REQ-001` — Solution Architecture Requirements Extract
6. `ARCH-PA-REQ-001` — Product Architecture Requirements Extract

This decision confirms source authority for the sanitized requirements extracts
at their registered versions. It authorizes their use as normative inputs in
future governed derivation work. Any new or changed control, marker, policy,
schema, workflow or baseline still requires its own impact review and change.

## Impact Analysis

| Area | Impact |
|---|---|
| Policy or directive | none |
| DevSecOps controls | existing DSCB lineage remains; no control content changes |
| Platform model | existing PRA lineage remains; no platform content changes |
| Architecture governance | four architecture extracts become approved normative sources; no marker or runtime change |
| OPA policies | none |
| Schemas and evidence contracts | none |
| Viewer, status indexes or intake | intake, review, lineage and impact reports are regenerated; the prior one-time DCR projection correctly becomes stale because its source-register commitment predates this approval |
| Release package or baseline | none; released packages and checksums are unchanged |
| Downstream repositories | none until a separately approved derivation or release changes a consumed artifact |

## Replacement Review

- [x] Not a source-document replacement review item

The six documents already exist as independent registered sources. Candidate
replacement relationships for other documents remain unchanged.

## Derived Artifacts

- `generated/reports/source-document-intake-status.{json,md}`
- `generated/reports/source-document-intake-review-briefs.{json,md}`
- `generated/reports/source-lineage-report.{json,md}`
- `generated/reports/governance-change-impact.{json,md}`
- `generated/reports/architecture-source-replacement-assessment.{json,md}`
- `generated/reports/source-document-requirement-delta.{json,md}`

## Governance Behavior

- [x] Report-only governance behavior

The authoritative status of the six sources changes to `approved`. Runtime
enforcement, report-only versus blocking modes, policies and released baseline
contents do not change in this change request.

## Release Decision

- [x] No release required

No released baseline asset changes. Future derivations from these approved
sources must make their own release decision.

## Validation Plan

- [x] Source lineage regenerated
- [x] Intake status and review briefs regenerated
- [x] Requirement delta and architecture replacement assessment regenerated
- [x] Governance impact report regenerated
- [x] `./scripts/bootstrap_validation_env.sh`
- [x] `./scripts/validate_all.sh` — 745 tests passed on 2026-10-09

## Reviewer Notes

- This record implements an explicit human decision; it is not an autonomous
  source approval by the Source Document Intake Agent.
- `DEVSECOPS-POL-REQ-001`, `DEVSECOPS-DIR-REQ-001` and
  `ARCH-SDD-REQ-001` remain under active review.
- All six candidate sources remain non-normative and blocked from derivation.
- A future Document Consistency Review may establish a fresh projection for
  the approved source population; this approval does not relabel the previous
  one-time review as current.
