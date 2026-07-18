# Evidence Attestation And Subject-Binding Pilot

## Outcome

The repository can verify a representative Ed25519 signature against a
registered public key and prove that the signature covers the exact evidence
context and subject digest. The capability is deliberately `report_only`.

A successful assessment reports `candidate_level: attested`, while
`effective_level` remains `integrity_verified`. It demonstrates the
cryptographic mechanism without changing results, policies, released
baselines, consumer workflows, or delivery decisions.

## Signed Statement

The canonical JSON statement binds all of these values:

| Claim | Purpose |
|---|---|
| `repository_id` | prevents cross-repository reuse |
| `commit_id` | binds evidence to the evaluated revision |
| `run_id` and `run_attempt` | distinguishes retries and reruns |
| `artifact_name` | binds the platform artifact identity |
| subject `id`, `algorithm`, and `digest` | binds the exact evidence bytes |

Canonicalization uses UTF-8 JSON with sorted keys and no insignificant
whitespace. The pilot format is
`governance-evidence-attestation-json-v0.1`; it is an internal experimental
format, not a released consumer contract or an endorsement of a final
attestation standard.

## Trust Root

`model/evidence/evidence-trust-roots.yaml` contains only a demo public key, its
issuer, algorithm, status, validity start, and permitted repository scope. No
private key or production secret is stored. `pilot_report_only` roots cannot
authorize blocking.

Production adoption still requires Security, Platform, and Governance approval
for issuer ownership, key generation and storage, rotation, revocation,
repository scope, incident response, and audit retention.

## Verification

Run the representative example:

```bash
python3 scripts/verify_evidence_attestation.py \
  docs/examples/evidence-attestation.example.json \
  --output /tmp/evidence-attestation-assessment.json
```

The verifier checks:

1. issuer, key, and repository scope exist in the pilot registry
2. the Ed25519 signature is valid for the canonical statement
3. subject identifier and digest match collected evidence
4. repository, commit, run, run attempt, and artifact match authoritative
   collection context

Tampering, an unknown key, a different context, or a different digest produces
a visible failed assessment. Findings remain report-only.

## Files And Boundaries

- attestation schema: `schemas/evidence-attestation.schema.json`
- assessment schema: `schemas/evidence-attestation-assessment.schema.json`
- trust-root registry schema: `schemas/evidence-trust-root-registry.schema.json`
- public pilot registry: `model/evidence/evidence-trust-roots.yaml`
- verifier library: `scripts/lib/evidence_attestation.py`
- command: `scripts/verify_evidence_attestation.py`
- signed example: `docs/examples/evidence-attestation.example.json`
- committed assessment: `generated/reports/evidence-attestation-pilot.json`

The pilot does not mutate Trust records or indexes. Operational promotion to
`attested` additionally requires every `provenance_verified` prerequisite,
producer-side signed attestations, approved trust roots, migration guidance,
release review, and explicit maintainer approval.

## Release Decision

No release is required. This is an internal report-only verifier and example;
no downstream field is mandatory, no reusable workflow or released package is
changed, and existing evidence remains valid. Selecting a production format or
requiring producer emission is consumer-facing and needs a separate release
and migration decision.
