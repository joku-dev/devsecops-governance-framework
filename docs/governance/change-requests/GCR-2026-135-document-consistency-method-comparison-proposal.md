# GCR-2026-135: Proposal for a Second-Provider DCR Method Comparison

## Decision Status

**Proposal only. No provider call or new DCR run is authorized by this record.**

The current management recommendation is to compare a second provider against
the same blinded synthetic catalog used by `dcr-catalog-run-0001`. Mistral is
the proposed second provider. This proposal does not authorize a reusable
provider profile, real-source review, publication, automation, blocking, or a
production rollout.

## Proposed One-Time Experiment

| Field | Proposed value |
|---|---|
| Purpose | Compare one second-provider output with the existing bounded synthetic reference |
| Proposed run ID | `dcr-catalog-run-0002` (reserved only after approval) |
| Provider | Mistral, subject to explicit per-run approval |
| Model | Exact provider-reported model identifier; must be confirmed before execution |
| Mode | Manual, report-only |
| Human evaluation | Separate from provider output; reviewer must be named before execution |
| Production effect | None; `limited_pilot_ready` and production `pending` remain unchanged |

## Fixed and Blinded Scope

Reuse only the six synthetic provider-input files from `dcr-catalog-run-0001`:
two synthetic sources, their synthetic register and manifest, the provider
projection schema, and `semantic-catalog-v1`. Bind the run to the existing
manifest SHA-256
`87f57dc0303b29702a1471a48ce7de85999b4fac117f28e687bcbc257e602b16` and
projection schema SHA-256
`83ae80f32e3c91e96fd6bcb14a1321d3c4aded60ad7fa2d6912e26861d0f529f`.

The expected-outcome catalog (SHA-256
`39d1c49924a45ededf9389dbbe3c824fa54976f147415265ff1aca76134fa39d`) remains
outside provider input and is used only after the response is captured. No
registered governance sources, local unregistered documents, consumer
repositories, secrets, unrelated repository content, or internet-retrieved
material may be added.

## Execution Gates

Execution remains blocked until a separate human approval records all of the
following for this exact run:

1. the exact Mistral model identifier and available deterministic parameters;
2. the account-specific provider retention and data-processing configuration;
3. local raw-response handling and deletion point;
4. a cost, context-size, and request-size ceiling;
5. the named human reviewer for evaluating any finding;
6. explicit approval to execute this one report-only run.

If any provider-retention or data-flow term cannot be verified, do not submit
the input. A prior provider approval or the WP-DCR-001 maintainer acceptance
does not satisfy these gates.

## Evaluation and Result Boundaries

After the provider response is captured, the existing deterministic adapter and
validator must check source IDs, hashes, anchors, and exact excerpts. The
blinded catalog may then evaluate the three versioned synthetic cases. Record
case-level differences from run 0001, provider-reported model and parameters,
elapsed time, human triage effort, and attributable cost where available.

The comparison can describe behavior on these three synthetic cases only. It
cannot establish general accuracy, precision, recall, false-positive rates,
compliance, real-document consistency, or implementation coverage. Findings
remain unconfirmed until separately reviewed by a human.

## Artifact Intake Classification

| Field | Value |
|---|---|
| Artifact | Proposal for a second-provider DCR method comparison |
| Artifact type | Governance decision proposal / documentation |
| Target path | `docs/governance/change-requests/GCR-2026-135-document-consistency-method-comparison-proposal.md` |
| Owner | Repository Maintainer / Governance Platform Lead |
| Source Document Intake required? | No; no source document or register entry is added |
| Evidence contract impact | None |
| Runtime governance impact | None; this proposal authorizes no run |
| Release impact | None |
| Validation required | Repository and runtime governance validation, unit tests, strict documentation build |

## Impact and Exclusions

| Area | Impact |
|---|---|
| Source register and source authority | None; no source is added, promoted, or replaced |
| Controls, traceability, architecture, OPA, and schemas | None |
| Released baselines and downstream consumers | None |
| Viewer, scheduling, automation, and blocking | Not authorized |
| Evidence artifacts | None until a separately approved run occurs |
| Lifecycle acceptance fingerprints | Unchanged |

This proposal is consistent with the separately recorded WP-DCR-001 acceptance
and the rollout readiness requirement that every provider run receive its own
authorization. It does not change the accepted rollout decision or initiate
execution.
