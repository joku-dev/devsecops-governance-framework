# Governance Change Request

## Summary

- Add a report-only Ed25519 attestation verifier and public demo trust root.
- Bind signatures to repository, commit, run attempt, artifact, and evidence
  subject digest.
- Demonstrate an `attested` candidate without promoting operational Trust.

## Change ID

```text
GCR-2026-041
```

## Intake And Impact

No new governance source document is introduced. The artifacts are an additive
internal Trust experiment: two schemas, one public-key pilot registry, verifier
code, representative signed evidence, tests, a generated assessment, and
operations documentation.

| Area | Impact |
|---|---|
| Controls, architecture markers, OPA | none |
| Current result and Trust indexes | none |
| Evidence contract | optional internal pilot; existing evidence unchanged |
| Enforcement | report-only; no workflow failure or delivery effect |
| Released baselines | none; packages and tags unchanged |
| Consumers | none; no repository or workflow mutation |

## Safety Invariants

- only public demo key material is committed
- the verifier, not the producer, derives assessment results
- all context and subject checks must pass for `candidate_level: attested`
- the pilot never writes `effective_level: attested`
- production trust roots, issuer operations, and producer emission require a
  separate approval and release decision

## Release Decision

- [x] No release required

The pilot does not modify a consumer-facing released contract or baseline.

## Validation Plan

- [x] valid signature and schema tests
- [x] tampered statement, subject mismatch, and unknown-root tests
- [x] deterministic representative assessment
- [x] full repository validation
- [x] strict documentation build
