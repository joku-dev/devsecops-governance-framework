# Document Consistency Review Operations

## Purpose and current boundary

Phase 4 supplies the provider-neutral operating contracts for finding
continuity, review scope, reviewer configuration, triage and a candidate review
package. It does not execute a semantic provider, accept a finding, publish the
viewer or approve rollout.

The current rollout decision is `pending`. The checked-in Phase-2 report remains
`not_run`; therefore no complete review baseline exists yet.

## Governed artifacts

| Artifact | Purpose |
| --- | --- |
| `model/governance/document-consistency/operating-model-v1.json` | Existing role routes, unconfirmed authority and escalation boundary |
| `model/governance/document-consistency/reviewer-config-v1.json` | Immutable candidate configuration with provider `not_configured` |
| `model/governance/document-consistency/provider-adapter-config-v1.json` | Active provider-neutral normalization contract; runtime provider binding remains required |
| `model/governance/document-consistency/semantic-evaluation-catalog-v1.json` | Curated synthetic expected outcomes for bounded provider and model comparisons |
| `model/governance/document-consistency/trigger-scope-matrix-v1.json` | Machine-readable incremental, full and methodology-comparison triggers |
| `model/governance/document-consistency/rollout-decision-v1.json` | Explicit prerequisites and prohibited claims while rollout is pending |
| `docs/examples/document-consistency-review-phase4-candidate-package.json` | Hash-bound incomplete candidate package; no normative approval |
| `tests/fixtures/document-consistency-review-operations/synthetic-ledger.json` | Synthetic continuity and triage evidence only |

Validate all contracts and referenced bytes with:

```bash
.venv-validation/bin/python scripts/validate_document_consistency_review_operations.py
```

The same check runs through `scripts/validate_governance_repo.py` and therefore
the normal repository validation.

## Finding continuity

A persistent finding identity uses a stable rule or category, stable governed
entities and a scope key. It is independent of review ID, line number, source
hash and model wording. Each review creates a separate occurrence.

| State | Meaning |
| --- | --- |
| `new` | First observed occurrence under the persistent identity |
| `unchanged` | Reassessed without a documented worsening |
| `worsened` | Severity increased or the affected source scope expanded |
| `resolved` | Explicitly reassessed and no longer present |
| `reopened` | Present after a prior resolved occurrence |
| `not_reassessed` | The current review did not cover the finding; it remains open |

Absence from an incremental run cannot produce `resolved`. Merges and splits
retain explicit predecessor and successor links. Semantic correlation is a
proposal for human triage; uncertain identities are not silently combined.

## Triage and authority

Triage records an existing role route, priority, decision, next action,
optional target date, escalation route, decision scope and rationale. A missing
owner remains `null` and visible. No person, decision body or binding SLA is
invented.

`false_positive` and `accepted_exception` decisions are scope-bound and remain
in history. A relevant source, applicability, authority or rule change requires
reassessment. The candidate operating model does not establish automatic
source precedence. Normative decisions remain human-only.

## Trigger and scope planning

- Source, source-status and implementation changes start with affected sources
  and dependencies.
- Roles, terms and relationships expand to a full review when impact is unknown.
- Topic-authority changes always require a full review and human authority review.
- Schema, review-rule and converter changes invalidate affected evidence and
  require regressions.
- Prompt, model and provider changes require curated catalog and methodology
  comparison; they do not rewrite historical results.
- Unknown change types fail conservatively to a full review.

Source freshness and methodology freshness remain separate. A methodology
change can limit comparability without erasing the historical observation.

## Curated semantic evaluation

The synthetic catalog evaluates explicit expected detections and prohibited
detections by category and exact evidence locators. Only non-quarantined
findings with valid evidence are eligible. Run it with:

```bash
.venv-validation/bin/python \
  scripts/evaluate_document_consistency_semantic_report.py \
  --catalog model/governance/document-consistency/semantic-evaluation-catalog-v1.json \
  --report <validated-semantic-report.json> \
  --output <evaluation-report.json>
```

The report must use the same source manifest and exact source set as the
catalog. Other reports return `not_applicable`; they do not become false misses
or passing evidence. Counts describe only the versioned cases and must not be
reported as population-level recall, precision or false-positive rates.

Prepare a provider-unbound, hash-bound catalog run package with:

```bash
.venv-validation/bin/python \
  scripts/prepare_document_consistency_semantic_catalog_run.py \
  --output-dir /private/tmp/dcr-semantic-catalog-run
```

The generated `provider-input/` contains exactly six files and deliberately
excludes the expected-outcome catalog. `run-package.json` binds the catalog by
digest and remains `prepared_not_run`. Provider and model must be selected and
authorized separately before execution.

## Configuration and rollback

Reviewer configurations are versioned and immutable after review. A new rules,
prompt, model, provider, parameter, schema, validator, converter or source
manifest combination gets a new configuration ID. Rollback selects a previously
reviewed configuration; it never edits an existing configuration in place.

The first reviewer configuration is `candidate`. Provider name, model and
parameters are empty because no reusable live-provider decision exists. The
separate adapter configuration is active for deterministic normalization only;
it does not authorize or select a provider. Live comparison remains `pending`.

## Candidate package and rollout

The candidate package binds its artifacts to exact SHA-256 values and the main
commit against which it was prepared. Its `incomplete` state is intentional:
the referenced semantic report is `not_run`, so it cannot become the immutable
first complete review baseline.

Rollout can be decided only after provider/model, data flow and retention are
approved; a real bounded pilot is run; humans assess usefulness, false
positives and known misses; effort and cost are observed; and the source scope
is confirmed. Until then it is prohibited to claim that the full document set
was reviewed, semantic consistency or compliance was proven, a normative
baseline was approved, or production rollout was authorized.
