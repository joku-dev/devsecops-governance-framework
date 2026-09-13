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
| LD-01 | Who can authorize remediation and who can approve closure, for which repositories/resources? | Explicit named role bindings controlled separately from proposed decisions | **Appointment confirmed, 13 September 2026.** `joku-dev` / GitHub ID `81616324` holds the three separate pilot roles with explicitly confirmed role combination; versioned binding and pilot-only validity recorded in the [live preparation](governance-lifecycle-live-preparation.md). Personal live consent verification remains pending |
| LD-02 | Which channel proves deliberate consent and authenticated identity? | A review of an immutable decision digest through an authenticated provider adapter | **Design direction confirmed:** personal GitHub decision statement; Codex prepares, the person issues consent. Content/identity/time binding, rejection/withdrawal and verifier acceptance remain pending; PR merge alone is insufficient |
| LD-03 | Who controls role bindings and can withdraw approvals? | Separately reviewed role registry and immutable withdrawal evidence | **Registry owner confirmed:** `joku-dev`; numbered replacement/withdrawal history is prepared separately from proposal records. Authenticated live administration remains pending |
| LD-04 | Which evidence sources and checks are accepted? | Named producer/workflow, immutable commit/run/attempt/artifact, integrity and provenance checks | **Confirmed operating scope, 13 September 2026:** official GitHub API, pinned Self-Security source/mainline attempt 1 and complete immutable pilot retention without automatic deletion. Independent provider recheck and durable receipts implemented; accountable operating acceptance remains pending |
| LD-05 | What are freshness, clock-skew and replay limits? | Evaluate the offline 24-hour/zero-skew boundary against real execution cadence | **Confirmed limited pilot policy:** 24-hour maximum evidence age, zero future skew, exact replay no-op and conflicting origin/content quarantine. Durable implementation and negative tests are documented in the [pilot intake guide](governance-lifecycle-durable-pilot-intake.md) |
| LD-06 | Where is merge-time revision acceptance serialized? | Local atomic append plus complete merged-chain and accepted-prefix validation in required CI | **Implemented for the synthetic pilot** in [ADR-CLG-002](governance-lifecycle-kernel.md#git-acceptance-and-competing-prs-adr-clg-002). Multiprocess and competing-Git-branch tests pass. Strict required checks remain a deployment assumption; live publisher acceptance is still pending |
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

## CLG-03 technical status

The [synthetic action intake](governance-lifecycle-decisions.md) now binds the
whole remediation plan, validates test consent against the fixed role binding,
and persists rejection, withdrawal and progress. LD-01–05 and LD-07 remain open;
fixture consistency is not authenticated human consent. LD-06 also covers action
transactions through the shared revision, atomic append and Git-prefix checks.

## CLG-04 technical preparation

The [closure implementation](governance-lifecycle-closure.md) and
[pilot runbook](../../demos/demo-governance-lifecycle-pilot.md) now exercise
synthetic closure/reopening, explicit-time reports and a bounded review-PR
publisher scope. The separately dated live observation is not accepted lifecycle
evidence. LD-01–05 and LD-07 remain open, including accountable acceptance and
post-closure correction/withdrawal procedure. No runtime release is approved.

## CLG-05 technical preparation

[Synthetic exceptions](governance-lifecycle-exceptions.md) reuse the existing
DevSecOps waiver authority map through an immutable test profile. Observation
coverage, expiry and withdrawal remain separate from finding/remediation state.
The critical test fixture names both required subjects; this does not prove real
joint consent or appoint people. LD-01–05 and LD-07 remain open. Live waiver
activation also requires accountable confirmation of the adapter's scope/date
mapping and real authority verification. Architecture exceptions need a separate
adapter and are not inferred from GRS-002.

## Confirmed appointment update — 13 September 2026

The earlier CLG-03–05 status paragraphs above describe those packages at delivery.
The maintainer has now confirmed LD-01 appointments and the LD-03 registry owner,
including the pilot-only multiple-role arrangement for `joku-dev`.
[Live preparation](governance-lifecycle-live-preparation.md) records the exact
binding and disabled profile. LD-02/03 live verification, LD-04 trust/retention,
LD-05 operating values and LD-07 acceptance remain incomplete. No live activation
or individual remediation/closure consent follows from this appointment.

## Confirmed operating-profile update — 13 September 2026

The maintainer's subsequent `ja` confirms the concrete LD-04/05 pilot proposal:
GitHub trust root and pinned source, 24-hour age, zero future skew, complete
immutable retention with no automatic deletion and explicit replay/quarantine.
The [durable intake validation](governance-lifecycle-durable-pilot-intake.md)
implements these values. Older package-status paragraphs retain their dated
context. Personal consent verification and LD-07 operating acceptance remain open.

## Personal channel probe, 13 September 2026

The [bound GitHub channel probe](governance-lifecycle-personal-channel.md) now
provides a read-only verifier, a concrete personal statement on PR #87 and negative
tests for identity, content and withdrawal history. The first real GET check is
waiting for that personal statement. Confirmation proves this limited channel
test only; action-specific live consent integration and LD-07 remain pending.

## Personal channel confirmation, 13 September 2026

The maintainer personally issued comment `5653982008` on PR #87. The retained
provider capture confirms the bound request and account, with unchanged original
comment bytes. A CRLF parsing correction handles GitHub's actual transport format;
raw-byte edit detection remains intact. Required PR CI rechecks new captures
against the provider. This closes the first positive channel test, while
action-specific consent integration and LD-07 remain pending.

## Action consent validation, 13 September 2026

The [GitHub action validator](governance-lifecycle-action-consent.md) binds individual
requests to the appointed role, exact plan, evidence and state revision. It retains
rejection, progress, closure and post-closure withdrawal, with independent provider
checks for new proof and prerequisites. Positive failure/action sequences remain
injected test fixtures; real PASS creates no finding or fabricated action. The
bounded operational publisher and accountable LD-07 acceptance remain pending.

## Concrete LD-07 operating request, 13 September 2026

The [bounded manual GitHub workflow and operating runbook](governance-lifecycle-live-operation.md)
are prepared. A separate digest-bound request asks the named maintainer to accept
this report-only GRS-002 pilot. The personal channel test and technical merges do
not satisfy this request. No operating acceptance capture exists yet; effective
activation remains false. After personal acceptance, the first provider-checked
publication PR records activation. Portfolio, other consumers and Bitbucket
operation remain outside this request.
