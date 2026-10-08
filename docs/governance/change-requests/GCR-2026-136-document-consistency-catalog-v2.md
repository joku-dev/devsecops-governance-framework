# GCR-2026-136: Expanded Synthetic DCR Evaluation Catalog

## Purpose

Add a versioned offline regression catalog for Document Consistency Review.
Catalog v1 remains immutable and continues to represent the three cases used by
`dcr-catalog-run-0001`. Catalog v2 binds four curated synthetic cases to a new
source manifest, including three additional negative/context-boundary patterns.

## Scope

Catalog v2 covers:

1. a clear conflict with an explicit shared context that requires both exact
   evidence items;
2. closely worded, aligned approval requirements that must not be called a
   conflict;
3. emergency and urgent-operation statements whose shared context is
   unproven; a `context_missing` candidate is not scored as an asserted
   conflict;
4. similar 90-day record statements that address retention and availability,
   which must not be called a conflict.

The local regression also submits a proposed conflict with one missing source
excerpt. Deterministic validation quarantines it, and the positive catalog case
fails to count it as a detection.

## Execution and decision boundary

All inputs and outputs in this change are synthetic fixtures. Local adapter,
validator and evaluator code may be exercised without a provider. No Mistral or
other provider call, new provider run ID, rollout decision, source promotion,
blocking behavior, or production conclusion is authorized. A future provider
comparison using catalog v2 requires its own proposal, provider-unbound run
package update, exact runtime binding, and explicit per-run approval.

## Compatibility and integrity

- `semantic-evaluation-catalog-v1.json`, its source manifest, and
  run-0001 reports remain unchanged.
- Catalog v2 uses `SYN-SRC-C-001` and `SYN-SRC-D-001`, a new synthetic source
  manifest, and a separate catalog identifier.
- Evaluation counts are limited to four curated cases. They are not model
  quality, recall, precision, false-positive rates, or evidence about real
  documents.
- A detection is counted only when its evidence is valid, it is not
  quarantined, its semantic state is `proposed`, and applicability is
  `same_context`.

## Artifact Intake Classification

| Field | Value |
|---|---|
| Artifact | Versioned synthetic evaluation catalog and test fixtures |
| Artifact type | Governance evaluation model / synthetic test data |
| Target paths | `model/governance/document-consistency/semantic-evaluation-catalog-v2.json`; `tests/fixtures/document-consistency-review-semantic-v2/` |
| Owner | Repository Maintainer / Governance Platform Lead |
| Source Document Intake required? | No; fixtures are synthetic and are not governance sources |
| Evidence contract impact | Local evaluation semantics only; no provider evidence created |
| Runtime governance impact | None; no run is authorized |
| Release impact | None |
| Validation required | Catalog and manifest schema validation, operations validation, evaluator regression, repository validation |

## Governance impact

- No controls, source authority, traceability, architecture, OPA, schemas for
  provider responses, or released baselines change.
- Production rollout remains `pending`; limited report-only pilot conditions
  remain in force.
- The existing method-comparison proposal remains bound to its original
  catalog and manifest. This version does not amend or authorize that proposed
  provider run.
