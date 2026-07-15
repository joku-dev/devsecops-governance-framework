# Evidence Collector Contract

## Purpose

The Evidence Collector Contract defines the normalized record produced before
evidence Trust verification. It makes source identity, production time,
collection time, collected subjects, digests, custody, and collection errors
consistent across collector implementations.

The structured contract is
`model/evidence/evidence-collector-contract.yaml`. Collector records validate
against `schemas/evidence-collector-record.schema.json`.

## Separation Of Concerns

A collector answers:

- where the evidence came from
- when it was produced and collected
- which bytes and subjects were captured
- which custody steps occurred
- whether collection was complete, partial, or failed

A collector does not answer:

- whether the evidence proves governance compliance
- which Trust level should be assigned
- whether delivery should be blocked

Collector status, evidence Trust, and governance outcome are therefore three
independent signals.

## Record Shape

Every version `0.1.0` record contains:

| Area | Meaning |
|---|---|
| Contract | Stable contract identity and version |
| Status | `collected`, `partial`, or `failed` |
| Collector | Implementation ID and version |
| Evidence context | Evidence type and governance domain |
| Time | Authoritative `produced_at` and central `captured_at` |
| Source | Provider, URI, repository, commit, workflow, run, attempt, and artifact |
| Subjects | Evidence references, byte sizes, and SHA-256 digests |
| Custody | Ordered collection actions and their outputs |
| Errors | Structured error code, message, and retryability |

`produced_at` is the time at which the authoritative source finished producing
the evidence. `captured_at` is when central intake collected it. Freshness uses
those meanings and does not substitute a local file modification time.

## Status Semantics

| Status | Required state |
|---|---|
| `collected` | At least one digested subject, at least two custody steps, and no collection errors |
| `partial` | At least one subject and at least one explicit error |
| `failed` | No usable subjects and at least one explicit error |

Missing mandatory identity, time, or subject metadata cannot be represented as
successfully collected evidence. The current intake stops before writing a
governance snapshot if mandatory GitHub Actions metadata is unavailable.
Persistence and display of standalone failed collection attempts is a future
operational decision; the contract already defines their portable shape.

## First Collector Profile

The first profile is `github-actions-governance-result`:

- collector: `central-governance-intake` version `0.1.0`
- evidence type: `governance_result`
- domains: DevSecOps and architecture
- source provider: `github_actions`
- implementation: both automated GitHub Actions intake scripts
- Freshness rule: `freshness-governance-result-24h`

For new automated intake, the collector record is stored directly as
`trust.capture`. This avoids duplicating the same source, subject, and custody
metadata in two structures. Trust verification consumes that record and adds
verification checks without changing the collector observations.

The schema-valid example is
`docs/examples/evidence-collector-record.example.json`.

## Compatibility And Adoption

Version `0.1.0` is additive, provisional, and report-only:

- historical Trust records with the legacy string collector identity remain valid
- historical snapshots are not rewritten or reclassified
- latest-result selection is unchanged
- current downstream producers do not need to emit new fields
- released DevSecOps and architecture baselines remain unchanged
- collector or Trust findings do not block delivery

Changing required producer fields or enabling blocking would require explicit
migration and release review.

## Adding A Collector Profile

Add a new collector through a focused GCR:

1. select an authoritative provider and evidence type
2. define production-time and subject-identity semantics
3. add the profile to the structured contract
4. produce schema-valid collected, partial, and failed examples
5. connect an applicable Freshness or subject-binding rule
6. add representative collection and Trust tests
7. preserve historical records and keep initial behavior report-only

The recommended next pilot is a vulnerability-scan collector once the scanner
format and artifact subject identity have been selected.
