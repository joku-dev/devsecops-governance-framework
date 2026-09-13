# CLG-01 Pilot Decision Sheet

13 September 2026. Technical contract preparation for
[CLG-01](governance-lifecycle-contract.md). **Live activation is not approved.**
This document records implementation choices and the decisions needed before
live intake. It does not appoint people, establish new governance authorities,
approve sources or create an SLA.

## Technical decisions implemented for offline work

| Topic | Chosen implementation | Reason and limit |
|---|---|---|
| First input | GRS-002 `pull_request_review_required`, `refs/heads/main`, existing report schema 0.2.0 | One concrete criterion; no inferred control findings from gate summaries |
| Test identity | Repository `synthetic/governance-lifecycle`, context `test`, `test-human:*` actors | Synthetics are structurally distinct from live approval channels |
| Test approval | Local immutable JSON statement plus raw SHA-256; exact role/profile/content binding | Tests reproducibly detect tampering; no claim of authentication |
| Test role binding | Separate decision and closure roles in the versioned synthetic profile | Exercises scope and role checks without appointing actual people |
| Test acceptance | Provenance level plus nine required checks; 24-hour maximum age and zero future skew | Fixed offline boundaries; asserted fixture verification only |
| Compatibility | Exact source-schema/profile/policy versions | No implicit interpretation across changed rules |
| Enforcement | Report-only lifecycle design; no publisher or consumer integration | No operational writes in CLG-01 |

## Decisions requiring accountable human confirmation

| ID | Decision to record before live use | Proposed starting point | Status / required evidence |
|---|---|---|---|
| LD-01 | Who can authorize remediation and who can approve closure, for which repositories/resources? | Explicit named role bindings controlled separately from proposed decisions | **Open.** Confirm actual people, role owner, scope, version, validity and revocation process; maintainer coordinates with governance roles |
| LD-02 | Which channel proves deliberate consent and authenticated identity? | A review of an immutable decision digest through an authenticated provider adapter | **Open.** Demonstrate content/identity/time binding, rejection, withdrawal and a policy for bot/tool-mediated actions; PR merge alone is insufficient |
| LD-03 | Who controls role bindings and can withdraw approvals? | Separately reviewed role registry and immutable withdrawal evidence | **Open.** Confirm registry owner, authorized changes and separation from proposal writers |
| LD-04 | Which evidence sources and checks are accepted? | Named producer/workflow, immutable commit/run/attempt/artifact, integrity and provenance checks | **Open.** Confirm allowlist, trust roots, independent check implementation and snapshot retention |
| LD-05 | What are freshness, clock-skew and replay limits? | Evaluate the offline 24-hour/zero-skew boundary against real execution cadence | **Open.** Confirm production values, context approval and conflicting/late evidence handling; test constants are not binding policy |
| LD-06 | Where is merge-time revision acceptance serialized? | Protected acceptance step checking the actual accepted ledger head | **Open for CLG-02 design.** Demonstrate two competing proposals cannot both consume one revision; do not rely only on branch CI |
| LD-07 | What qualifies the pilot for live operation? | CLG-04 runbook with complete synthetic failure sequence plus separately labeled current live observation | **Open.** Named operational acceptance, confirmed LD-01–05, tested negative cases and scoped publisher review |

The maintainer can coordinate these decisions while CLG-02 prepares the offline
kernel. Do not fill an open authority slot with an agent, an inferred GitHub
account role or an existing waiver authority. Proposed new normative roles,
mandatory evidence or deadlines must follow source intake and governance change
review before live enforcement. Preserve `model/waivers/waiver-authorities.yaml`.

## ADR-CLG-001 — Separate contracts from acceptance

**Status:** implemented for offline contract validation; live architecture remains
subject to the decisions above. Related change: GCR-2026-062.

**Context:** Schema-valid evidence can still be forged, stale, superseded or
inapplicable. A signed commit or a tool executing as a human does not establish
conscious approval of a particular governance decision. The pilot needs usable
contracts before organizational assignments are complete.

**Decision:** Use additive typed records, digest-bound references and separate
synthetic test verification. Keep runtime acceptance, authenticated authority,
append-only storage and projection in later packages. The test profile cannot
be enabled for live intake by changing a boolean; its schema fixes environment,
identity, channel and disabled-live status. Live operation needs an explicit new
profile contract and a reviewed adapter.

**Alternatives considered:** Treating JSON Schema success as acceptance would
lose the identity/revocation/context boundary. Building the full runtime in
CLG-01 would combine contracts, persistence and authorization before review.
Copying waiver roles would invent authority for a different decision type.

**Consequences:** CLG-01 can validate a concrete packet now. It cannot claim a
closed operational finding, trusted human approval or complete P01–P10 runtime
acceptance. Canonicalization and record versions are explicit so CLG-02 can
build against reviewable contracts. Later contract changes require version and
example/test updates rather than silent changes to accepted record meaning.
