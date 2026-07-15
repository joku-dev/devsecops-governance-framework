# App Architecture Evidence Templates

## Purpose

Application repositories can add structured architecture evidence under:

```text
.governance/architecture/
```

The architecture governance collector reads these files and uses them to raise marker maturity from "described" to "verified" when evidence is approved.

The collector also accepts the neutral detailed evidence types from:

```text
docs/operations/evidence/architecture-evidence-type-taxonomy.md
```

Detailed evidence types are currently reported as `detailed_evidence.report_only: true` in `architecture-release-input.json`. They can strengthen existing coarse evidence areas, but they do not introduce new blocking gates by themselves.

## Files

| File | Evidence type | Typical effect |
|---|---|---|
| `solution-baseline.json` | `solution_baseline` | Satisfies solution baseline presence. |
| `release-compatibility-declaration.json` | `release_compatibility_declaration` | Satisfies release compatibility declaration presence and approval when `status` is `approved`. |
| `security-evidence.json` | `security_evidence` | Strengthens E6, S5 and P8 security marker scores. |
| `resilience-evidence.json` | `resilience_evidence` | Strengthens S8 and P10 resilience marker scores. |
| `operation-evidence.json` | `operation_evidence` | Strengthens P11 observability marker score. |
| `feedback-evidence.json` | `feedback_evidence` | Strengthens B5 feedback-loop marker score. |
| `threat-model.json` | `threat_model` | Detailed, report-only security architecture evidence. |
| `interface-contract.json` | `interface_contract` | Detailed, report-only interface and compatibility evidence. |
| `deployment-manifest.json` | `deployment_manifest` | Detailed, report-only deployment and runtime evidence. |
| `model-based-architecture.json` | `model_based_architecture` | Detailed, report-only model-based architecture evidence without a tool mandate. |

## Detailed Evidence Types

Examples of detailed, tool-neutral evidence types:

| Evidence type | Current coarse area |
|---|---|
| `interface_contract` | `release_compatibility_declaration` |
| `contract_test_result` | `release_compatibility_declaration` |
| `threat_model` | `security_evidence` |
| `security_architecture_review` | `security_evidence` |
| `deployment_manifest` | `deployment_evidence` |
| `observability_evidence` | `operation_evidence` |
| `resilience_test_evidence` | `resilience_evidence` |
| `architecture_review_record` | `review_evidence` |
| `architecture_exception` | `exception_evidence` |
| `model_based_architecture` | `solution_baseline` |

Use detailed types when an application team already has stronger evidence. Keep using the coarse types for current gate satisfaction until Enterprise Architecture promotes specific detailed expectations to report-only or blocking checks.

## Status Semantics

| Status | Meaning |
|---|---|
| `draft` | Evidence exists but is not verified. |
| `reviewed` | Evidence has been reviewed but is not yet approved for gate satisfaction. |
| `approved` | Evidence is accepted for gate satisfaction. |

## Usage

Copy the `.governance/architecture/` folder into the application repository and update owners, baseline names, evidence references, limitations and follow-up actions.

For demo purposes, keep files in `draft` to show findings. Change selected files to `approved` to demonstrate how findings are reduced through evidence.
