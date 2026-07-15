# Architecture Evidence Enterprise Architecture Decision Brief

Status: draft / discussion input

## Purpose

This brief lists the Enterprise Architecture decisions needed before detailed architecture evidence becomes more than report-only context.

The current implementation is tool-neutral and non-blocking.

## Current Repo Position

The governance repository currently supports two evidence layers:

| Layer | Current status | Example |
|---|---|---|
| Coarse evidence | Existing gate input | `security_evidence`, `operation_evidence`, `release_compatibility_declaration` |
| Detailed evidence | Report-only taxonomy | `threat_model`, `interface_contract`, `deployment_manifest`, `model_based_architecture` |

Detailed evidence is collected into:

```text
architecture.detailed_evidence
```

This field is visible in the architecture governance report, but it does not introduce a new blocking gate by itself.

## Decisions Needed From Enterprise Architecture

| Decision | Recommendation | Rationale |
|---|---|---|
| Which detailed evidence types are accepted? | Start with `threat_model`, `interface_contract`, `deployment_manifest`, `model_based_architecture`, `architecture_review_record`. | These map cleanly to current architecture markers and do not require a vendor tool. |
| Which system classes require model-based architecture evidence? | Start with integration-heavy, release-critical, or high-assurance systems only. | Avoids overloading small products and preserves adoption speed. |
| Should model evidence require a specific tool? | Keep tool-neutral for now. | The repository should validate metadata and reviewable exports before native tool files. |
| Which export format is reviewable in CI? | Prefer PDF, HTML, XMI, JSON, or generated model reports. | CI can archive and reviewers can inspect these without proprietary tooling. |
| Which detailed evidence is report-only first? | All detailed evidence types. | Gives teams time to produce evidence without surprise release blocking. |
| Which detailed evidence may become blocking later? | Promote only after templates, examples, owners, and exception process exist. | Prevents governance from becoming brittle. |
| Who approves model baselines? | Enterprise Architecture defines policy; Solution Architect or Product Architect owns execution. | Keeps accountability clear across levels. |
| How are exceptions handled? | Use existing architecture exception flow. | Avoids a second waiver mechanism. |

## Proposed Adoption Sequence

1. Keep detailed evidence report-only.
2. Run the collector in application CI and archive `architecture-release-input.json`.
3. Review detailed evidence summaries in architecture governance reports.
4. Ask teams which evidence is easy or hard to produce.
5. Agree accepted names and metadata with Enterprise Architecture.
6. Add templates for accepted evidence types.
7. Promote selected evidence types to report-only expectations.
8. Add findings for missing expected evidence.
9. Add exception handling.
10. Promote only the highest-value checks to blocking gates.

## Questions For The Enterprise Architect

1. Which detailed evidence types are mandatory for Product Architecture?
2. Which detailed evidence types are mandatory for Solution Architecture?
3. Which detailed evidence types are mandatory for Enterprise-impacting changes?
4. Is model-based architecture required for every system or only specific system classes?
5. Which model export format is acceptable for review and audit?
6. Who approves a model baseline?
7. Which evidence can remain in application repositories, and which must live in a central architecture repository?
8. Which missing evidence should produce findings but not block?
9. Which missing evidence should eventually block release readiness?
10. What is the exception process for missing detailed evidence?

## Non-Goals

This brief does not propose:

- a vendor-specific modeling tool mandate
- immediate blocking gates for detailed evidence
- a replacement for existing architecture review boards
- a second exception or waiver process
