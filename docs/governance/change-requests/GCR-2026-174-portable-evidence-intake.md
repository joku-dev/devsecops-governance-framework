# GCR-2026-174 — Portable evidence intake candidate

Date: 2026-11-15. Status: implemented candidate for review; no operational acceptance.

This is the next technical increment of the portability goal v1.2 (PR #368), after M1 / GCR-2026-173. Classification under the [new-artifact intake process](../../operations/processes/new-artifact-intake-process.md): executable intake, versioned technical contracts, consumer templates, tests and operating documentation. It is not a normative source document and derives no new control or baseline.

The legacy neutral ZIP import only records declarations. The successor adds one file verifier and actual OPA recomputation for CI and VM callers, native read-only GitHub/GitLab/Bamboo acquisition, provider/instance identities, explicit freshness/replay, private SQLite v2 state and a backup-first legacy migration candidate. Native capture and verification stay separate. Existing source result bytes and their Trust fields are never rewritten or promoted.

The optional new GitHub workflow/template paths export a complete bundle. Existing released workflow pins, OPA packages, result ledgers, accepted status indexes and the operating acceptance fingerprints remain unchanged. The legacy private VM store now declares schema version 1 and rejects newer databases. Version 2 requires the new operator; a migration never switches the active data root, services or publisher.

Report-only findings remain evidence, not execution failures or approval. Integrity verification alone does not qualify a bundle for a native candidate. Native candidate eligibility is separate from official acceptance, publication, compliance and merge enforcement. Architecture governance remains parked.

Scope and remaining M2 work are recorded in the [intake guide](../../operations/evidence/portable-evidence-intake.md). In particular, Bamboo Spec/SCM/job provenance closure and GitHub PR merge-checkout closure remain unsupported in this increment; neither receives equivalent native Trust through a flag. Central operations/publication, automatic discovery, VM activation/update integration and complete capacity acceptance still require their next increments. This GCR does not mark M2 or the full goal complete.

Validation: pinned bootstrap/full repository validation, focused real-OPA and native-response fixtures, schema/YAML/strict documentation checks, migration/replay/recovery tests and revision-bound role lenses. Exact validation counts and CI outcomes belong to the revision-bound PR receipt, not a fabricated live acceptance record.
