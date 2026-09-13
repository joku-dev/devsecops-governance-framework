# GCR-2026-066: CLG-05 Synthetic Time-Limited Exceptions

The maintainer requested the next CLG package after authorizing the one-time
review exception and merge of #79. Base: `58ed8e73cbff76263c86da24f086b7cbda2dfa97`.
CLG-04's open live appointments and accountable acceptance are not bypassed;
this work prepares the next synthetic technical package.

| Field | Classification |
|---|---|
| Artifact types | Additive exception/profile/event/transaction/index contracts, synthetic intake and projection, immutable demo evidence, tests and guidance |
| Target paths | Lifecycle scripts/schemas, new versioned test exception profile, separate `governance/lifecycle/synthetic-exceptions/`, dedicated index/report, tests and lifecycle docs |
| Owner/review lenses | Governance analysis, evidence/intake, release management and repository stewardship |
| Source Document Intake | Not required; existing waiver contract and authority model are reused without new normative authorities |
| Evidence impact | Explicit observation-bound risk acceptance, expiry and withdrawal; no claim of authenticated human consent |
| Runtime impact | Report-only synthetic treatment dimension, independent of finding state and remediation progress |
| Release impact | No release, released-baseline mutation, OPA enforcement change or consumer migration |
| Validation | Pinned full suite, strict MkDocs, authority/scope/time/coverage/revocation tests, replay and accepted-prefix checks |

Coverage is bounded to explicit accepted failing observations in the current
finding episode. GRS-002 provides one atomic branch criterion; this package does
not invent sub-resource coverage. A subset of observations is partial coverage;
new observations are never automatically waived. Risk classification is an
explicit input, not inferred from finding severity. The authority map is a
versioned snapshot of `model/waivers/waiver-authorities.yaml`; test identities are
not real appointments. Architecture exceptions are not interchangeable with
this DevSecOps GRS-002 contract and require a later domain adapter.

## Review boundaries

[ADR-CLG-005](../../operations/evidence/governance-lifecycle-exceptions.md#bounded-coverage-and-time-adr-clg-005)
records the observation coverage unit and explicit synthetic UTC date mapping.
A waiver never closes a finding, suppresses a quarantine or changes work
progress. Revocation/expiry can expose renewed decision need without mutating
accepted bytes; overlapping active grants retain their independent coverage.
Renewal requires a fresh waiver identity and consent for the current revision.

Governance analysis preserves existing authority names and separates explicit
risk classification from finding severity. Evidence/intake review covers
resource/subject/revision binding, coverage and deterministic time evaluation.
Release review finds no baseline, OPA or consumer-contract change. Repository
stewardship requires full validation, unchanged earlier scenarios and profiles,
and a prefix check for the new ledger/profile. The closure publisher scope
explicitly rejects exceptions; no automatic waiver publication is enabled.
