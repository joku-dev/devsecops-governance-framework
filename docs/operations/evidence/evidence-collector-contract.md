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
successfully collected evidence. The current intake records a separate
report-only collection attempt when a GitHub Actions artifact cannot be
downloaded or validated. It does not create a governance snapshot from that
failed attempt.

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

## Vulnerability Scan Pilot

The second profile is `repository-normalized-vulnerability-scan`:

- collector: `central-vulnerability-scan-collector` version `0.1.0`
- evidence type: `vulnerability_scan`
- domain: DevSecOps
- input: repository-normalized JSON with scanner identity and findings
- subjects: the scan report and evaluated application artifact
- Freshness rule: maximum age 24 hours
- state: pilot

The pilot deliberately accepts the small format already used by the repository
instead of claiming native compatibility with every scanner. Trivy, Grype,
Snyk, and other tools can later receive explicit adapters into this normalized
input. Placeholder and demo scanner identities are rejected.

The complete operator guide, input reference, output interpretation, and
failure behavior are documented in
`docs/operations/evidence/vulnerability-scan-collector-usage.md`.

Example:

```bash
python3 scripts/collect_vulnerability_scan_evidence.py \
  --scan-path security/vulnerability-scan.json \
  --evaluated-subject-path dist/application.tar.gz \
  --repository-id owner/repository \
  --commit-id abc123 \
  --run-id 42 \
  --run-attempt 1 \
  --source-uri https://example.invalid/actions/artifacts/7/zip \
  --produced-at 2026-07-15T13:55:00Z
```

The output is a full evidence Trust record. It verifies the collected bytes and
applies the provisional Freshness policy, but it does not infer a governance
pass. A stale scan has a failed report-only Freshness check while retaining any
independently established integrity level.

The pilot binds the scan report and application artifact by collecting both in
one record. This is `co_collected` binding, not proof that the scanner attested
to the artifact digest. The distinction remains explicit in collector
observations until scanner-native attestations are supported.

## Central Typed-Evidence Intake

`scripts/intake_evidence_trust_github_actions_run.py` is the first central
consumer of the vulnerability profile. It downloads the complete
`application-evidence` artifact and requires both the normalized scan and the
evaluated application artifact. It then replaces the producer-side
verification assessment with a central verification performed over the
downloaded bytes.

The resulting snapshot validates against
`schemas/typed-evidence-result.schema.json`. The generator
`scripts/generate_typed_evidence_results_index.py` projects snapshots into
`status/typed-evidence-results-index.json`, which validates against
`schemas/typed-evidence-results-index.schema.json` and feeds the dedicated
viewer section.

This adoption is additive:

- existing collector and Trust records remain valid
- the downstream producer contract remains optional
- a later manual run cannot replace an existing `main` push as latest typed evidence
- typed Trust does not alter the governance-result indexes
- all Trust and Freshness findings remain report-only
