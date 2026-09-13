# GCR-2026-073: Confirmed Operating Profile and Durable Pilot Intake

On 13 September 2026 the maintainer answered `ja` to the concrete pilot operating
profile: the selected GitHub/Self-Security source, 24-hour evidence age, zero
future skew, complete immutable retention during the pilot without automatic
deletion, and idempotent replay with quarantine for conflicting content.

| Field | Classification |
|---|---|
| Artifact types | Recorded operating decision, immutable operating-profile model/schema, durable validation receipt contract/store, generator, tests and operating guide |
| Target paths | `model/governance/lifecycle/live-operating/`, lifecycle library/schemas/CLI, `governance/lifecycle/live-validation/`, separate diagnostic status/report and docs |
| Owner/review lenses | Governance analysis, evidence/intake, release management and repository stewardship |
| Source Document Intake | Not required: confirmed limited pilot operation; no enterprise policy or baseline change |
| Evidence contract impact | Additive pilot-validation receipts embedding complete raw capture bytes; existing accepted synthetic contracts unchanged |
| Runtime impact | Durable pilot validation and required provenance checks for new receipt proposals; live lifecycle operation still awaits LD-07 |
| Release impact | None; no released package/tag, producer, OPA or consumer enforcement change |
| Validation | Full pinned suite, strict docs, corruption/retention/replay/conflict/concurrency/freshness negatives, real capture and independent GitHub recheck |

A receipt records eligibility under the confirmed operating policy, not operational
lifecycle acceptance. Complete capture bytes survive artifact expiry in immutable
Git-tracked transactions. New receipt proposals must be checked independently
against GitHub by required PR CI; offline hash consistency alone cannot establish
provider authenticity. PR review exceptions do not bypass these checks.

The new store has a separate namespace and projection. PASS creates no artificial
Finding and never closes an existing one. No automatic workflow dispatch, deletion,
consumer update or official publisher is introduced. Personal decision verification
and accountable live acceptance follow on this concrete, retained evidence.
