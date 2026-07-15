# Evidence Trust Model

## Status And Scope

Status: active, report-only model version 1.

The machine-readable source of truth is:

```text
model/evidence/evidence-trust-model.yaml
```

Its internal model schema is:

```text
schemas/evidence-trust-model.schema.json
```

This model improves how the repository reasons about evidence confidence. It
does not change the governance run input schema, existing result snapshots,
current latest-result selection, OPA policy behavior, released baselines, or
consumer workflow interfaces.

## Core Distinction

Evidence trust and governance outcome are separate decisions.

- Trust answers whether evidence identity, bytes, origin, age, custody, and
  authenticity were verified.
- Governance evaluation answers whether the evidence satisfies controls,
  architecture gates, thresholds, approvals, and exceptions.

A trusted report may contain governance findings. A passing report may remain
unverified. Neither value may be inferred from the other.

## Current-State Assessment

### DevSecOps Intake

The current GitHub Actions intake already records:

- repository, branch, commit, workflow run, event, status, and baseline
- artifact names and sizes
- SHA-256 for the control evaluation report
- SHA-256 for the governance run input when present
- the downstream run URL

This provides useful identity, provenance, and integrity material. The snapshot
does not yet record that those signals were evaluated as named verification
checks, and it does not assign a trust level.

### Architecture Intake

The architecture intake records:

- repository, branch, commit, workflow run, event, status, and architecture
  baseline
- normalized evidence-presence flags and gate results
- the downstream run URL

It does not currently store digests for the architecture report, release input,
or downloaded artifact.

### Shared Gaps

Both intake paths still need:

- an explicit verifier and verification timestamp
- per-check results instead of inferred booleans
- run-attempt and replay-key handling
- freshness policies by evidence type and decision context
- raw-to-normalized chain-of-custody records
- trusted issuer and attestation verification
- a normalized trust projection for indexes and the viewer

Existing snapshots remain valid historical evidence and are not retroactively
promoted. Without an explicit trust assessment, their model default is
`unverified`.

## Trust Dimensions

| Dimension | Question |
|---|---|
| Identity | What evidence record and governed subject are being evaluated? |
| Integrity | Do recomputed digests match the collected evidence bytes? |
| Provenance | Which producer, workflow, run attempt, event, commit, and baseline created the evidence? |
| Authenticity | Did an approved issuer attest to the exact evidence subject? |
| Freshness | Is the evidence valid for the time and decision context in which it is used? |
| Replay resistance | Is this evidence unique to the claimed subject and run attempt? |
| Chain of custody | Can acquisition and every normalization step be traced by digest? |

Presence alone does not satisfy a dimension. A verifier must evaluate its
required claims and record the result.

## Trust Levels

| Rank | Level | Meaning | Explicit limitation |
|---:|---|---|---|
| 0 | `unverified` | Evidence is recorded without asserted verification. | Not sufficient for independent audit reliance or automated blocking. |
| 1 | `integrity_verified` | Subject identity exists and collected bytes match a verified digest. | Does not establish producer identity or authoritative provenance. |
| 2 | `provenance_verified` | Integrity, source run, commit, artifact binding, freshness, replay, and custody are verified. | Does not provide cryptographic issuer assurance. |
| 3 | `attested` | Provenance-verified evidence has a valid, subject-bound attestation from an approved issuer. | Does not imply a governance pass or authorize blocking by itself. |

Levels are monotone. A higher level includes every dimension and check required
by lower levels.

## Assignment Rules

The effective trust level is assigned by the intake verifier, not by the
evidence producer.

The producer may provide claims and attestations, but it cannot self-declare a
trusted level. The verifier must:

1. resolve the authoritative workflow run
2. bind repository, commit, run attempt, artifact, and baseline
3. recompute and compare content digests
4. evaluate freshness and replay rules
5. record acquisition and transformation custody
6. validate attestation signature, issuer, and subject for `attested`

`unknown`, missing, skipped, and `not_evaluated` checks do not satisfy a trust
level.

## Target Trust Record

The next additive contract phase should introduce a normalized block similar
to this shape:

```json
{
  "trust": {
    "model_id": "evidence-trust-model-v1",
    "effective_level": "integrity_verified",
    "verifier": "central-governance-intake",
    "verified_at": "2026-07-15T12:33:25Z",
    "checks": [
      {
        "id": "content_digest_verified",
        "result": "pass",
        "evidence_refs": ["downloaded_artifact.control_evaluation_report_sha256"]
      }
    ]
  }
}
```

This is a target shape, not a current downstream contract. Schema changes must
follow the evidence schema versioning and release process.

## Chain Of Custody Target

For each intaken artifact, future verification should retain or reference:

- authoritative source URI
- collector identity and version
- collection timestamp
- raw archive digest
- extracted evidence digests
- normalization transformation identifiers
- normalized snapshot digest
- previous verification record when re-verifying

Large raw artifacts may remain in the platform evidence store. The central
snapshot needs stable references and digests, not a duplicate raw archive.

## Freshness And Replay

Freshness must be contextual. A release approval, vulnerability scan, SBOM,
architecture review, and runtime observation may require different validity
windows. No universal expiry is defined in version 1 because control owners,
Security, and Operations must approve those windows.

The future replay key should bind at least:

```text
repository + commit + workflow + run + run_attempt + artifact + subject_digest
```

Reusing the same digest is not automatically invalid, but reuse across a
different subject or incompatible decision context must be visible and
evaluated.

## Migration Plan

### Phase 1: Model And Gap Assessment

- validate this structured model
- keep all trust behavior report-only
- do not rewrite historical snapshots

### Phase 2: Additive Capture

- add optional trust metadata
- add architecture content and archive digests
- add run attempt and custody fields to both intake paths
- preserve existing schema compatibility

### Phase 3: Verification Projection

- centralize trust-level derivation
- evaluate freshness and replay
- expose trust separately from governance result in indexes and viewer
- keep findings report-only

### Phase 4: Attestation Pilot

- approve trust roots and issuer identities
- select an attestation format and predicate
- verify signatures and subject binding for representative repositories

### Phase 5: Enforcement Decision

- evaluate migration and release impact
- define exception and downgrade behavior
- require explicit approval before any trust signal becomes blocking

## Open Decisions

| Decision | Required review |
|---|---|
| Trusted issuer and trust-root registry | Security, Platform, Governance |
| Freshness windows per evidence type | Control owners, Security, Operations |
| Initial attestation format and predicate | Security, Platform, Architecture |
| Trust requirements for protected mainline or release | Governance, Security, Release Manager |

These decisions block later phases, not the report-only model introduced here.

## Latest-State And Viewer Impact

Version 1 does not change which result becomes `latest_result`. Mainline push
selection remains unchanged, branch and manual history remain separate, and the
viewer continues to show current governance outcomes without a trust badge.

Adding a viewer trust projection belongs to Phase 3 and requires tests that
prevent a trust value from being confused with `pass`, `fail`, or `findings`.

## Release Decision

No baseline release is required for Phase 1 because:

- the downstream evidence contract is unchanged
- no field becomes mandatory
- existing snapshots remain valid
- OPA and workflow enforcement are unchanged
- the model is report-only

Any schema change consumed by downstream repositories or any trust-based gate
requires a separate release and migration decision.
