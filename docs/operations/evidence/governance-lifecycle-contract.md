# Governance Lifecycle Contract — CLG-01

Version: **0.1.0**, 13 September 2026. Scope: executable record contracts and
synthetic offline examples for the [closed-loop pilot](../planning/closed-loop-governance-implementation-plan.md).
Change classification: [GCR-2026-062](../../governance/change-requests/GCR-2026-062-governance-lifecycle-contracts.md).

CLG-01 supplies schemas, content/reference checks and closure packet prerequisites.
It does **not** supply a lifecycle state machine, append-only store, mainline
intake, authenticated human approval verifier or operational closure. Successful
validation of a JSON record does not establish its acceptance or authority.
The checked-in profile rejects live use. All evidence and people in the examples
are synthetic, including every asserted trust check and approval proof.

## Artifacts and validation layers

| Artifact | Contract |
|---|---|
| Observation | One GRS-002 criterion result, source context, immutable snapshot digest, existing Evidence Trust record and acceptance proof reference |
| Decision | Proposed remediation action and rationale, failure reference, expected finding revision, content-bound approval/rejection/withdrawal |
| Remediation | Approved decision reference, concrete action, owner, target time, work evidence and progress |
| Closure | Remediation, FAIL and newer PASS references, evaluation time, reason `remediated` and separately bound human approval |
| Event | Aggregate identity, consecutive revision, predecessor digest, effective/recorded times, policy version and typed source references |
| Test profile | Versioned synthetic-only source, trust, freshness and role-binding settings; `live_intake_enabled: false` |

The schemas are `schemas/governance-lifecycle-{observation,decision,remediation,closure,event,profile}.schema.json`
with definitions in `governance-lifecycle-common.schema.json`. The observation
reuses `evidence-trust-record.schema.json` through an offline schema registry.
No schema resolver retrieves remote resources.

Validation has three distinct boundaries:

1. **JSON Schema:** required fields, types, closed objects, version, identifiers,
   UTC timestamps, event genesis shape and synthetic/live proof-channel separation.
2. **Record and packet consistency:** recomputed fingerprints and content digests,
   exact referenced bytes, fixture proof bindings, revision edges, criterion
   identity, compatible evidence and closure prerequisites.
3. **Future runtime acceptance:** authenticated identities and trust roots,
   current role authority, revocation history, accepted ledger head, merge-time
   concurrency, durable idempotency and state transitions. These remain CLG-02–04.

`validate_record` implements the first two layers for an individual record.
`validate_test_record` and `check_closure_prerequisites` additionally operate on
explicitly supplied synthetic resources. They are not a production authorization
API. Neither a successful call nor a PR merge grants governance authority.

## Pilot identity and canonicalization

The pilot supports exactly `GRS-002`, key `pull_request_review_required`, in
domain `governance_repository_security`, finding type `criterion_failure`, and
resource `refs/heads/main`. Broader resources and rule adapters require an
explicit contract extension. Repository IDs use lowercase ASCII `owner/repo`,
without surrounding whitespace. An adapter must resolve provider identity and
reject ambiguous aliases; it must not silently rename a repository.

The finding key contains `repository_id`, `domain`, `rule_id`, `finding_type`
and `resource`. Its ID is:

```text
finding: + sha256(canonical({"fingerprint_version": "1", "key": <key>}))
```

`canonical` is the existing `scripts/lib/result_ledger.py::canonical_digest`
serialization: JSON object keys sorted, separators `,` and `:`, ASCII escaping
(`ensure_ascii=True`), then UTF-8 bytes, without a trailing newline. Schema-typed
payloads use strings, integers, booleans, nulls, arrays and objects; do not add
floating-point values to the hashed contract. Arrays retain their order. This
is a repository-specific canonicalization, not a claim of RFC 8785 compliance.
Other implementations must match the fixed test vector before exchanging data.
A changed canonicalization requires a new fingerprint version and migration.

Finding, observation and event IDs are separate. All record IDs have a type
prefix. A reference is `{id, digest}`, hashing the complete referenced record;
profile and role-binding references also carry a version. Snapshot and proof
references hash **raw bytes**, including any newline. The same identifier with
different accepted content is a conflict, never an in-place update.

The observation delivery key hashes the finding and complete `source_context`
(repository, commit, producer, run, attempt and context kind). It excludes
receipt time and result bytes so that conflicting deliveries remain detectable.
CLG-02 must compare the original producer payload as well: snapshot digest,
observed time, rule/result and source/profile/policy versions. Identical
redelivery retains the original accepted observation and adds no occurrence or
event. Different producer content for the same delivery key is quarantined.
A new run/attempt with the same failure is a new observation of the same finding.
A changed trust assessment must retain its own provenance; it cannot overwrite
an earlier accepted record. This utility computes keys; it does not implement
that delivery protocol or an occurrence counter.

## Time, versions and immutable records

Lifecycle timestamps are second-resolution UTC `YYYY-MM-DDTHH:MM:SSZ`; invalid
calendar dates and alternate offsets are rejected. `observed_at` is producer
observation time, `effective_at` is event business time and `recorded_at` is
intake time. A late observation keeps its earlier effective time. Event order
is the accepted aggregate revision, not sorting by producer timestamps.

Genesis is `finding_opened`, revision 1, expected revision 0, null predecessor.
Every subsequent event references its predecessor and advances exactly one
revision. A decision/remediation/closure states the revision it expects before
its event is appended. The synthetic packet reserves revisions 1–5 for opening,
decision, remediation, PASS observation and closure; only the opening event is
included in CLG-01. It is not an accepted event history.

CLG-02 must check the expected revision against the **accepted merge-time head**.
Two valid PRs based on the same head cannot both advance it. Tests of one
revision edge here do not demonstrate that concurrency control. Persisted
observations, decisions, remediations, closures and events are immutable. Current
state belongs only in a generated projection. The proposed lifecycle storage
paths and publisher permissions remain unimplemented.

Record schema version, acceptance-profile version, source security-profile
version and lifecycle policy version are separate. Version compatibility in the
pilot is exact equality; no semver compatibility is inferred. Each replay and
closure check takes an explicit `as_of`, bound into the closure content.
The checker does not consult the current clock.

## Approval and withdrawal contract

The signed/approved target digest covers the **whole record excluding only
`approval`**, including its ID, environment, profile, finding, expected revision,
rationale and referenced evidence. Approval binds that digest, finding ID and
expected revision to a subject, role, versioned role binding, channel, issue
time, disposition and proof reference. Proof verification must also bind all
these approval fields; changing just the declared approver or disposition is
not a valid new approval.

For synthetic examples, proof bytes contain `{environment: synthetic, approval: ...}`
with every approval field except `proof_ref`; tests compare the entire object.
The fixture role binding maps only `test-human:*` identities. These are test
actors, not authenticated people. For live-shaped records the schema requires
`external_review` and disallows the test-human prefix, but no live verifier or
approved live profile exists in this change.

The future verifier must establish authenticated person identity, conscious
consent, scope, current versioned role membership and withdrawal status from a
separately controlled channel. A `subject_type: human` field, Git signature,
bot-submitted PR or tool running under a person's account is insufficient.
Decision and closure approval use distinct roles; no CISO/board authority is
inferred from existing waiver authorities. The
[decision sheet](governance-lifecycle-pilot-decisions.md) identifies what needs
human confirmation before live intake.

`reject` and `revoke` are new bound records. Withdrawal requires `supersedes_ref`;
the previous approval stays immutable. CLG-03 must resolve that predecessor,
verify authority to withdraw, and evaluate the complete revocation history at
`as_of`. A supplied rejection/withdrawal cannot authorize closure in the offline
packet checker. The checker does not discover a later withdrawal omitted from
a packet. A withdrawn historical closure requires visible clarification; it is
not silently erased or automatically counted as a new technical failure.

## Observation acceptance and GRS-002 adapter

The current self-security report is an input, not proof of acceptance. The
future adapter supports `governance-repository-security-report.schema.json`
version `0.2.0`, extracts exactly one GRS-002 criterion, and preserves profile
version, repository and observed time. Missing/duplicate criteria or a summary
without the criterion cannot provide a PASS. `unknown` and `not_evaluated` may
be represented in a record but cannot establish successful remediation.

The envelope adds source commit/run/attempt/producer/context, immutable snapshot
bytes, SHA-256, capture/custody, verification and an acceptance proof. The
synthetic acceptance proof binds the observation excluding its `acceptance`
object plus all acceptance fields except `proof_ref`. That includes the trust
record and the criterion result. The offline checker compares snapshot identity,
profile, criterion and time and binds the captured subject to the same bytes.
It does not perform an API call or authenticate the producer.

Official lifecycle state will accept only mainline, release or separately
approved contexts under a confirmed live profile. Branch, PR, diagnostic/manual
and synthetic data do not become official by being schema-valid. The test
profile accepts **only** context `test`, producer `synthetic-grs002-fixture`
and repository `synthetic/governance-lifecycle`. Unknown mappings and conflicts
must remain visible; an LLM cannot supply missing evidence or rule IDs.

## Closure prerequisites and future transitions

The offline closure packet must resolve the decision, completed remediation,
FAIL observation and newer criterion PASS by exact digest, for the same finding
and profile. The action must match the decision. A completed work item alone
is insufficient. The PASS must follow recorded remediation and precede the
closure approval. The source schema/profile/policy versions must be comparable,
all referenced records must exist by `as_of`, and expected revisions must be
ordered. The closure approval has its own content and role binding.

For accepted observations, the synthetic profile requires `provenance_verified`
or higher and **all nine**
checks underlying that level in the existing Trust model, each uniquely present
with result `pass` and evidence references. An asserted `attested` label does not
replace a failed or missing check. Snapshot bytes, trust source and subject must
match. The PASS age at `as_of` is at most 86,400 seconds; future evidence is
rejected. This is a test constant, not an approved production SLA or freshness
policy. Live acceptance must recompute checks against trusted sources and use
confirmed freshness/clock-skew limits.

| Future transition | Required meaning |
|---|---|
| Absent → open | New accepted criterion FAIL creates one finding |
| Open → open | Independent same-scope FAIL adds an occurrence; repeated delivery does not |
| Open → closed | Valid decision/remediation/PASS/approval chain, current accepted revision and no superseding failure or withdrawal |
| Closed → closed | Delayed older FAIL retained in history; identical redelivery has no effect |
| Closed → open | Actually newer accepted comparable FAIL; same finding ID and preserved closure history |
| Any → needs clarification | Conflicting content, uncertain causality, incomparable versions or invalidated authorization; no invented PASS |

Those transitions, conflicting evidence after the packet, role revocation
history, merge races and projection replay remain runtime work. Risk acceptance
and partial waivers are separate treatment dimensions reserved for CLG-05;
`reason` currently allows only `remediated`.

## Executable coverage and remaining acceptance

| Pilot case | CLG-01 executable check | Remaining package |
|---|---|---|
| P01 | Six schema-valid records, raw fixture digests, reference and closure packet prerequisites | Full append/intake/transition chain in CLG-02–04 |
| P02 | Stable delivery key; same-key/different-content conflict detectable | Durable deduplication and occurrence counts in CLG-02 |
| P03 | Consecutive revision and predecessor digest/scope | Concurrent PR and merge-head protection in CLG-02 |
| P04/P05 | Observed and recorded times remain separate and ordered | Delayed FAIL and actual reopening projection in CLG-02/04 |
| P06 | Criterion granularity, scope, exact versions, PASS/FAIL and reference binding | Real adapter comparison/coverage in CLG-02/04 |
| P07 | Snapshot integrity, required check failures, duplicate checks, explicit freshness | Real producer/trust verification and conflict ledger in CLG-02/04 |
| P08 | Content, revision, role, test proof, rejection and withdrawal shape | Authenticated consent, supersession and revocation history in CLG-03/04 |
| P09 | Test-only profile, rejected branch/PR/manual/live input and proof-channel separation | Operational acceptance under a confirmed live profile in CLG-04 |
| P10 | Repeatable non-mutating contract checks with explicit `as_of` | Ledger replay and equal projections/metrics in CLG-02/04 |
| P11 | No waiver-based closure reason in the pilot schema | Exception dimensions, partial coverage, expiry and withdrawal in CLG-05 |

Run from the repository root:

```bash
./scripts/bootstrap_validation_env.sh
.venv-validation/bin/python scripts/validate_governance_lifecycle_contracts.py
.venv-validation/bin/python -m unittest discover -s tests -p 'test_governance_lifecycle_contracts.py'
./scripts/validate_all.sh
.venv-docs/bin/mkdocs build --strict
```

The governance repository validator invokes the dedicated contract checker; the
normal unit suite runs the negative tests. Valid examples are in
`docs/examples/governance-lifecycle/`; full invalid payloads and their expected
schema failures are in `tests/fixtures/governance-lifecycle/invalid/`.
`tests/fixtures/governance-lifecycle/resources/` holds the synthetic snapshots,
acceptance statements, approval statements and work evidence. Their fixture URIs
are resolved from an explicit in-memory mapping, never by network access.
