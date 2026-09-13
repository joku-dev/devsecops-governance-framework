# GCR-2026-064: CLG-03 Decisions and Remediation Intake

## Request and artifact classification

The maintainer requested CLG-03 after authorizing the one-time review exception
and merge of PR #77. Base: `853ec6615ef9a868daa6eec0f6d75f6242856635`.

| Field | Classification |
|---|---|
| Artifact types | Additive decision/remediation and transaction/index contracts, synthetic action intake, state projection, fixtures, tests and operating guidance |
| Target paths | `schemas/governance-lifecycle-*.schema.json`, `scripts/lib/governance_lifecycle/`, dedicated CLI/demo, additive synthetic ledger transactions, generated synthetic index, tests and lifecycle docs |
| Review lenses | Governance analysis, evidence/intake, release management and repository stewardship |
| Source Document Intake | Not required; implements the reviewed plan without new normative sources, real appointments or global SLAs |
| Evidence impact | New 0.2.0 action contracts; old 0.1.0 records, observations, accepted transactions and profile remain intact |
| Runtime impact | Synthetic decision/rejection/withdrawal and remediation intake; report-only; no live authority, waiver or closure |
| Release impact | No baseline/repository release or consumer migration in CLG-03; assess runtime release at CLG-04 |
| Validation | Pinned full suite, old-history replay, action authorization/content/role/revision tests, withdrawal/progress races, deterministic demo and strict MkDocs |

The actual live role registry, authenticated consent channel and operational
acceptance remain open in LD-01–05 and LD-07. Technical checks and this change
record do not supply independent human approval or appoint real decision makers.

## Implementation and review boundaries

[ADR-CLG-003](../../operations/evidence/governance-lifecycle-decisions.md#bound-plan-and-authorization-adr-clg-003)
binds owner, deadline, action, work reference and case ID inside the approval
target. Rejection grants no authority; withdrawal disables further progress;
replacement creates a new case. Exact retries cannot reactivate withdrawn
approval. Remediation completion and latest PASS do not close a finding or
resolve quarantined evidence.

Four new action transactions extend the accepted five-record CLG-02 prefix.
Mixed-version replay regenerates all records and events. The historical CLG-02
projection is retained as a test fixture; the current index is generated from
the complete ledger. Existing POSIX serialization and CI accepted-prefix checks
cover actions; a real withdrawal/progress race tests the shared revision.

Governance analysis preserves the open live decisions and approved plan.
Evidence/intake checks cover content, scope, revision, role and fixture resources.
Release review finds no released-package, OPA or consumer-contract changes.
Repository stewardship requires the full pinned validation, strict documentation
build, unchanged accepted prefix and exclusion of unrelated generated metadata.
