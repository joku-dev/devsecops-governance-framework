# Architecture Evidence Enterprise Architecture Package

Status: draft / discussion package

## Purpose

This page collects the documents and reference material needed to discuss detailed architecture evidence with Enterprise Architecture.

## Package Contents

| Topic | Document |
|---|---|
| Evidence type taxonomy | `docs/operations/evidence/architecture-evidence-type-taxonomy.md` |
| Mapping from existing input documents | `docs/operations/evidence/architecture-evidence-taxonomy-mapping.md` |
| EA decision brief | `docs/operations/evidence/architecture-evidence-ea-decision-brief.md` |
| Adoption guide for app teams | `docs/operations/evidence/detailed-architecture-evidence-adoption-guide.md` |
| Reference run | `docs/operations/reference-runs/2026-07-06-detailed-architecture-evidence-reference-run.md` |
| Provider-backed agent review | `docs/operations/reference-runs/2026-07-06-codex-provider-detailed-evidence-review.md` |
| Application repo evidence flow | `docs/operations/evidence/application-repo-architecture-evidence-flow.md` |
| Company Bitbucket/Bamboo/Mistral path | `docs/operations/adapters/company-bitbucket-bamboo-mistral-target-path.md` |
| Agent usage snapshot | `docs/operations/agents/agent-usage-snapshot-latest.md` |

## Current Technical State

The repository currently supports detailed evidence as report-only metadata.

The collector emits:

```text
architecture.detailed_evidence
```

The report renders:

```text
Detailed Evidence
Report-Only Advisories
```

The validator checks the application evidence templates against:

```text
schemas/app-architecture-evidence.schema.json
```

## Key Position

The current position is tool-neutral.

`model_based_architecture` does not require a specific modeling tool. A specific tool, repository, notation, or export format can be added later as a company-specific refinement.

## Decisions Requested

1. Which detailed evidence types should be accepted?
2. Which detailed evidence types should be expected for Product, Solution, and Enterprise Architecture?
3. Which system classes require model-based architecture evidence?
4. Which model export formats are acceptable for review and audit?
5. Which detailed evidence can remain report-only?
6. Which detailed evidence should eventually create findings?
7. Which detailed evidence should eventually become blocking?
8. Which exception process applies when detailed evidence is missing?

## Recommended Next Discussion Outcome

Agree on a first report-only expectation set:

```text
threat_model
interface_contract
deployment_manifest
model_based_architecture
architecture_review_record
```

Then run this expectation set in CI for several application repositories before promoting anything to blocking.
