# Artifact Intake Classification Examples

## Purpose

This example shows how the New Artifact Intake Process classifies typical
incoming artifacts before they enter the governed repository structure.

These examples are illustrative. They are not source documents, runtime
evidence, release packages or approved governance decisions.

Use the process document for the official rules:

```text
docs/operations/processes/new-artifact-intake-process.md
```

## Example 1: New ADO Architecture Source Document

| Field | Example value |
|---|---|
| Artifact name | `ADO_AC1_Architecture_Governance_Framework_R5.md` |
| Artifact type | source |
| Intended use | Possible newer ADO architecture governance source |
| Target path | `docs/governance/source-documents/ADO_AC1_Architecture_Governance_Framework_R5.md` |
| Owner | architecture-owners |
| Source Document Intake required? | yes |
| Evidence contract impact | none |
| Runtime governance impact | none until review decision |
| Release impact | none until replacement or derivation decision |
| Required process | Source Document Intake and possible replacement review |
| Required validation | Source lineage, intake status, review briefs, requirement delta, repo validation |

Decision:

- Register as `candidate`.
- Do not derive controls, markers, policies, schemas or release content until
  the replacement review is complete.

## Example 2: Downstream Pipeline Evidence Bundle

| Field | Example value |
|---|---|
| Artifact name | `ha-cpswms-main-28600000000-artifacts.zip` |
| Artifact type | evidence |
| Intended use | Import downstream CI evidence into central governance status |
| Target path | Temporary intake bundle; normalized result under `status/results/` |
| Owner | evidence-and-intake |
| Source Document Intake required? | no |
| Evidence contract impact | none |
| Runtime governance impact | report-only status update |
| Release impact | none |
| Required process | Evidence/result intake and spot-check governance intake |
| Required validation | Bundle validation, intake script, results index, viewer, repo validation |

Decision:

- Use `scripts/intake_ci_artifact_bundle.py` or the platform-specific intake
  script.
- Do not hand-edit `status/repository-results-index.json`.

## Example 3: New Optional Evidence Schema Field

| Field | Example value |
|---|---|
| Artifact name | `governance-run-input.schema.json` update for `deployment.region` |
| Artifact type | schema |
| Intended use | Add optional downstream evidence field |
| Target path | `schemas/governance-run-input.schema.json` |
| Owner | evidence-and-intake |
| Source Document Intake required? | no unless derived from new source material |
| Evidence contract impact | additive |
| Runtime governance impact | none unless evaluator behavior changes |
| Release impact | possible minor release if downstream consumers should adopt it |
| Required process | Evidence contract review |
| Required validation | Schema validation, example update, repo validation, unit tests |

Decision:

- Update the schema and example together.
- Record whether the field is optional or required.
- Do not treat an optional schema field as blocking behavior.

## Example 4: Bamboo Adapter Template

| Field | Example value |
|---|---|
| Artifact name | `bamboo-governance-plan.yaml` |
| Artifact type | workflow |
| Intended use | Reusable Bamboo 12.1.9 adapter example |
| Target path | `pipeline-baseline/templates/bamboo/` |
| Owner | platform-adapter |
| Source Document Intake required? | no |
| Evidence contract impact | none unless generated evidence shape changes |
| Runtime governance impact | none or report-only, depending on adapter behavior |
| Release impact | possible release candidate if packaged for consumers |
| Required process | CI/CD adapter review |
| Required validation | Adapter documentation, example check, repo validation |

Decision:

- Keep adapter behavior aligned with the existing evidence contract.
- Record any Bamboo-specific limitations in adapter documentation.

## Example 5: Confluence Publishing Page

| Field | Example value |
|---|---|
| Artifact name | `governance-operating-model-confluence.md` |
| Artifact type | documentation |
| Intended use | Narrative explanation for stakeholders |
| Target path | `docs/publishing/governance-operating-model-confluence.md` |
| Owner | governance maintainers |
| Source Document Intake required? | no |
| Evidence contract impact | none |
| Runtime governance impact | none |
| Release impact | none |
| Required process | Publishing documentation review |
| Required validation | MkDocs strict build and repo validation |

Decision:

- Keep it as a communication artifact.
- If it starts defining policy, controls or mandatory behavior, create a
  separate source-document intake decision.
