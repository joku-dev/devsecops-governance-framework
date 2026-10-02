# GCR-2026-108: Verify ha-CPsWMS container evidence provenance

The maintainer requests that the ha-CPsWMS five-image vulnerability and SBOM
evidence be able to reach Trust level `provenance_verified` when all required
checks pass. This change closes the two missing rank-2 checks in central
intake: authoritative baseline-reference resolution and a verifiable
raw-artifact-to-normalized-snapshot custody record.

The baseline check binds the coverage report's declared baseline to exactly one
GitHub Actions `referenced_workflows` entry for the pinned L1 reusable workflow,
including its immutable workflow commit. Custody records hash all six
downloaded artifact archives and the normalized typed subjects and observations,
and name each transformation performed by intake. The effective level is
derived only after replay assessment passes alongside every other rank-2 check.

| Classification | Decision |
|---|---|
| New artifacts | Additive verifier behavior, custody fields in the Trust record schema, focused tests and documentation |
| Source-document intake | None: implements the active report-only Evidence Trust model |
| Contract impact | Additive optional custody record; existing records and snapshots remain valid |
| Release impact | No released baseline or release package changes |
| Enforcement | Report-only; no workflow or policy gate is changed |
| Scope | Central `joku-dev/ha-CPsWMS` five-image vulnerability and SBOM intake only |
| Limits | Co-collected evidence; no producer attestation, risk acceptance, compliance result, or release approval |
| Historical data | No retroactive promotion or rewriting of existing snapshots |
| Validation | Focused tests, full pinned repository validation, strict docs, then fresh producer run and central intake |

`provenance_verified` is an intake capability, not a claim that the live
ha-CPsWMS status has already advanced. A fresh successful mainline run captured
after deployment is required to demonstrate that status.
