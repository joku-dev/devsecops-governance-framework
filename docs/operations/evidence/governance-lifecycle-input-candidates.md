# Lifecycle Input Candidates (CLG-06.3)

Current operating context: the separate [GitHub GRS-002 pilot](../status/governance-lifecycle-current-state.md)
is accepted after PRs #92/#93. This guide describes the scope of its own
contract or adapter; synthetic, diagnostic and preparation records retain their
original labels and do not independently authorize operation.

The additional adapters prepare **diagnostic DevSecOps control and architecture
gate candidates** from existing producer reports. They do not submit observations to
the lifecycle kernel. The [implementation plan](../planning/closed-loop-governance-implementation-plan.md)
keeps producer adaptation and live acceptance separate.
[GCR-2026-069](../../governance/change-requests/GCR-2026-069-lifecycle-devsecops-candidates.md)
records the DevSecOps classification and boundaries;
[GCR-2026-070](../../governance/change-requests/GCR-2026-070-lifecycle-architecture-candidates.md)
records the architecture adapter and live decision brief.

## DevSecOps contract — CLG-06.3a

The adapter supports the required projection of the producer's
`control-evaluation-report@1.0.0`, described by
`schemas/governance-lifecycle-devsecops-source.schema.json`. This is an adapter
input contract, not a replacement schema for the existing producer. Extra
producer metadata remains bound by the raw-byte digest. Required rows contain
explicit `control_id`, `level` and `status`; optional messages are preserved as
text. The adapter does not evaluate policy messages, infer identifiers or expand
one failed gate into additional control findings.

It validates unique control IDs, ID/level agreement and all summary counters
against the explicit rows. `pass`, `fail`, `not_tested` and `not_applicable` stay
separate. A subset report describes only its listed controls; the adapter does
not assert catalog completeness. It does not resolve IDs against an authenticated
released baseline. Unknown status values, unsupported producer schema versions,
missing rows and ambiguous IDs are rejected.

The represented resource is `repository`, the granularity supplied by this
report. It does not invent branch, service, deployment or artifact findings.
Branch and release context remain explicit source metadata; a later live
adapter must approve the appropriate scope and compatibility policy.

## Architecture contract — CLG-06.3b

The architecture producer currently emits an unversioned report. The adapter
explicitly names its supported shape `architecture-gate-report@legacy-shape-v1`
in `schemas/governance-lifecycle-architecture-source.schema.json`. This is a
local adapter contract, not an invented producer version. Versioned reports
require an explicit adapter revision; unknown top-level fields are rejected.

Exactly four distinct gates are required: `architecture_readiness`,
`integration_readiness`, `operation_readiness` and `release_readiness`.
Each produces **one gate candidate**, even if its finding list contains several
messages. `pass` and `findings` retain producer meaning; `counts.findings` counts
gates with messages, not individual messages or marker failures. Gate status,
message presence and all four source summary counters must agree. Blank messages,
unknown/missing/duplicate gates and inconsistent counters are rejected.

The adapter preserves text and row pointers without parsing marker identifiers.
A passing gate does not establish PASS for an individual marker or close a
lifecycle finding. Recommended remediations, advisories and detailed evidence
remain source metadata bound by the report digest; they create no work,
exceptions, decisions or extra outcomes.

The declared full commit must match the report target commit or its recorded
prefix (at least seven hex characters). This is only a consistency check: a
short commit does not authenticate provenance or supply the missing full commit.
Repository, run, baseline, policy and observation context still need an explicit
descriptor; they are never inferred from local paths or free text.

## Required declared context

`schemas/governance-lifecycle-candidate-context.schema.json` requires all of:

- repository and branch;
- full commit and policy revision;
- producer identifier, run ID and attempt;
- baseline reference;
- event, purpose, release-context flag and synthetic flag;
- observation timestamp and expected raw report SHA-256.

The DevSecOps producer's event, purpose and release-context fields must match.
A producer report labeled `source: demo` requires synthetic context. The adapter
checks that the supplied digest matches the actual bytes, requires observation
time no later than the explicit evaluation time, and reports age in seconds.
It does not assign a freshness limit or mark freshness as passed.

These are **caller declarations**, not authenticated provenance. Even if declared
metadata says `mainline`, the output remains `trust_status: unverified`,
`acceptance_status: not_evaluated`, `environment: diagnostic` and
`official_state: false`. Synthetic metadata is classified as `test`; otherwise
push/main, push/branch, pull request, manual and release remain distinct.
No current clock, network lookup or implicit context reconstruction is used.

## Reproduce the synthetic examples

```bash
./scripts/bootstrap_validation_env.sh
.venv-validation/bin/python scripts/prepare_lifecycle_devsecops_candidates.py \
  --report docs/examples/lifecycle-candidates/devsecops-report.json \
  --context docs/examples/lifecycle-candidates/devsecops-context.json \
  --output /tmp/devsecops-lifecycle-candidates.json \
  --evaluated-at 2026-09-13T12:01:00Z
cmp /tmp/devsecops-lifecycle-candidates.json \
  docs/examples/lifecycle-candidates/devsecops-candidates.json
```

The four example outcomes are fabricated test declarations, not a re-evaluation
of those controls. Tests additionally adapt the repository's existing red and
green generated demo reports, preserving their 46 explicit rows and counters.

The architecture example contains four gates, two with three total messages.
It therefore yields four candidates, including two `findings` results:

```bash
.venv-validation/bin/python scripts/prepare_lifecycle_architecture_candidates.py \
  --report docs/examples/lifecycle-candidates/architecture-report.json \
  --context docs/examples/lifecycle-candidates/architecture-context.json \
  --output /tmp/architecture-lifecycle-candidates.json \
  --evaluated-at 2026-09-13T12:01:00Z
cmp /tmp/architecture-lifecycle-candidates.json \
  docs/examples/lifecycle-candidates/architecture-candidates.json
```

An integration test also executes the actual architecture report generator with
OPA and an explicitly synthetic target, then adapts its four gate results.
This does not refresh or replace any official consumer evidence.

Each output candidate binds its declared repository/domain/rule/resource,
source row pointer, result and message to the raw report/context and adapter
identity. Its `candidate:` ID is not a Finding ID. Re-evaluating the same input
at a later time changes age, not the candidate IDs. Changed content or producer
context changes their identity.

Keep the exact source report and descriptor with the output. The output stores
digests and row pointers, not an authenticated copy or trusted provenance proof.
Within this repository, output is limited to the dedicated example or diagnostic
candidate-report directories; accepted ledger, model, status and official viewer
paths are not writable through this CLI. No operational publisher scope is added.

## Acceptance remains a separate step

The candidate record type cannot pass the existing accepted-observation schema.
No finding, decision, remediation, waiver or closure is created. Admission to
live lifecycle state requires an approved profile and independently verified
producer/run/artifact, baseline/policy, scope, freshness and replay rules.
Consent and role verification require the named decisions in
[LD-01–05 and LD-07](governance-lifecycle-pilot-decisions.md).

Architecture reports currently expose gate outcomes and free-text findings.
The adapter retains that granularity; marker IDs and marker-level PASS/failure
cannot be invented from those messages. Architecture exceptions
also require their own authority/scope adapter before live treatment.

The [live-pilot decision brief](governance-lifecycle-live-decision-brief.md)
provides concrete role slots and proposals for consent, evidence verification,
freshness and operating acceptance. It records the next required human input;
technical PR review exceptions do not appoint lifecycle approvers.
