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

The GitHub Actions intake records:

- repository, branch, commit, workflow run, event, status, and baseline
- artifact names and sizes
- SHA-256 for the downloaded archive, control evaluation report, and
  governance run input when present
- workflow run attempt and the authoritative artifact download URI
- initial download and extract-and-hash custody steps
- the downstream run URL

This provides useful identity, provenance, integrity, and custody material. The
central verifier independently recomputes captured-subject digests and may
derive `integrity_verified`. It does not derive a higher level from capture
alone.

### Architecture Intake

The architecture intake records:

- repository, branch, commit, workflow run, event, status, and architecture
  baseline
- normalized evidence-presence flags and gate results
- the downstream run URL
- SHA-256 for the downloaded archive, architecture report, and release input
- workflow run attempt and initial custody steps

These fields are additive. Existing architecture snapshots remain valid and are
not rewritten.

### Shared Verification State

Both intake paths now record a named verifier, verification timestamp, and
per-check results. The remaining Phase 3 capabilities are:

- replay-key construction and duplicate or cross-subject reuse evaluation
- freshness policies by evidence type and decision context
- a normalized snapshot digest and transformation record
- trusted issuer and attestation verification

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

## Additive Trust Capture Record

New automated intake snapshots include a normalized block. This abbreviated
view shows the trust state and capture categories; the linked example contains
the complete schema-valid record:

```json
{
  "trust": {
    "model_id": "evidence-trust-model-v1",
    "capture_phase": "additive_capture",
    "effective_level": "unverified",
    "assessment_status": "not_evaluated",
    "verifier": null,
    "verified_at": null,
    "checks": [],
    "capture": {
      "collector": "central-governance-intake",
      "captured_at": "2026-07-15T14:00:00Z",
      "source": {
        "repository_id": "joku-dev/ha-CPsWMS",
        "commit_id": "716c3cda4fa5cef7504ca7b3263f0cd1697b6e6c",
        "run_id": "29415015294",
        "run_attempt": 1,
        "artifact_name": "architecture-governance-evidence",
        "...": "workflow name and authoritative source URI"
      },
      "subjects": [
        {
          "id": "architecture_governance_report",
          "algorithm": "sha256",
          "digest": "<64 lowercase hexadecimal characters>",
          "...": "evidence reference and byte size"
        }
      ],
      "custody": [
        {"action": "download", "...": "actor, time, source, outputs"},
        {"action": "extract_and_hash", "...": "actor, time, source, outputs"}
      ]
    }
  }
}
```

The complete contract and example are
`schemas/evidence-trust-record.schema.json` and
`docs/examples/evidence-trust-record.example.json`. The intake collector may
record claims and hashes, but `not_evaluated` requires `unverified`, a null
verifier, a null verification timestamp, and no verification checks.

## Chain Of Custody

For each newly intaken artifact, additive capture retains or references:

- authoritative source URI
- collector identity
- collection timestamp
- raw archive digest
- extracted evidence digests
- the download and extract-and-hash steps

Phase 3 still needs normalization transformation identifiers, a normalized
snapshot digest, and linkage to a previous verification record when
re-verifying.

Large raw artifacts may remain in the platform evidence store. The central
snapshot needs stable references and digests, not a duplicate raw archive.

## Freshness And Replay

Freshness must be contextual. A release approval, vulnerability scan, SBOM,
architecture review, and runtime observation may require different validity
rules. The provisional, versioned policy set is defined in
`model/evidence/evidence-freshness-policies.yaml`:

| Evidence type | Provisional validity rule | Current evaluation |
|---|---|---|
| Governance result | maximum age 24 hours | evaluated during DevSecOps and architecture intake |
| Vulnerability scan | maximum age 24 hours | configured; waits for typed evidence timestamp |
| Runtime evidence | maximum age 30 minutes | configured; waits for typed evidence timestamp |
| Architecture review | maximum age 180 days | configured; waits for typed approval timestamp |
| SBOM | must match the evaluated subject digest | configured; waits for subject binding |
| Release approval | must match the exact release candidate | configured; waits for candidate binding |

Version `0.1.0` is deliberately `provisional` and `report_only`. Missing
metadata produces `not_evaluated`; an expired or future-dated governance
result produces a failed Trust check without changing its governance outcome,
latest-result selection, or delivery behavior. Later changes require a new
GCR and policy version. Existing assessments are preserved and are not
reclassified retrospectively.

The future replay key should bind at least:

```text
repository + commit + workflow + run + run_attempt + artifact + subject_digest
```

Reusing the same digest is not automatically invalid, but reuse across a
different subject or incompatible decision context must be visible and
evaluated.

## Migration Plan

### Phase 1: Model And Gap Assessment

- complete
- validate this structured model
- keep all trust behavior report-only
- do not rewrite historical snapshots

### Phase 2: Additive Capture

- complete
- add optional trust metadata
- add architecture content and archive digests
- add run attempt and custody fields to both intake paths
- preserve existing schema compatibility

### Phase 3: Verification Projection

- current
- centralize trust-level derivation
- evaluate governance-result freshness with provisional policy v0.1
- project unresolved typed freshness and replay checks as `not_evaluated`
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
| Approve or revise provisional freshness policy v0.1 | Control owners, Security, Operations |
| Initial attestation format and predicate | Security, Platform, Architecture |
| Trust requirements for protected mainline or release | Governance, Security, Release Manager |

Approval of the provisional Freshness policy blocks completion of Phase 3,
not its current report-only use. The other decisions block the later
attestation and enforcement phases.

## Latest-State And Viewer Impact

Version 1 does not change which result becomes `latest_result`. Mainline push
selection remains unchanged, and branch and manual history remain separate.
Indexes and the viewer now show evidence trust next to, but never instead of,
the governance result. Historical snapshots without a Trust record project as
`unverified` with assessment status `not_available`.

## Release Decision

No baseline release is required for the report-only Phase 3 projection because:

- the change affects central intake snapshots, internal indexes, and the viewer
- no downstream producer field becomes mandatory
- existing snapshots remain valid
- OPA and workflow enforcement are unchanged
- the model is report-only

Any schema change consumed by downstream repositories or any trust-based gate
requires a separate release and migration decision.
