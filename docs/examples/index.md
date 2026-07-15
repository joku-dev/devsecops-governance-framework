# Governance Examples

## Purpose

This folder contains schema-backed example payloads for repositories and
pipelines that integrate with the DevSecOps governance baseline.

The examples are not source documents and do not define governance policy by
themselves. They make the active schemas easier to understand, test and adopt.

## Official Examples

| Example | Purpose | Schema |
|---|---|---|
| `docs/examples/governance-run-input.example.json` | Example input facts for a governance evaluation run. | `schemas/governance-run-input.schema.json` |
| `docs/examples/governance-compliance-result.example.json` | Minimal example governance compliance result. | `schemas/governance-compliance-result.schema.json` |
| `docs/examples/governance-compliance-result.extended.example.json` | Extended example governance compliance result with execution, policy and control evaluation details. | `schemas/governance-compliance-result.schema.json` |
| `docs/examples/artifact-intake-classification.example.md` | Worked examples for classifying new artifacts before intake. | not applicable |
| `docs/examples/artifact-intake-checklist.template.md` | Reusable checklist template for artifact intake decisions. | not applicable |

## Usage Guidance

Use these examples as reference payloads when creating application repository
evidence, CI/CD adapter outputs or local test fixtures.

Application repositories should still publish their own runtime evidence under
their configured governance evidence path, for example
`governance/governance-run-input.json` or a pipeline-generated evidence
artifact. The examples in this folder are repository documentation and test
fixtures, not runtime evidence outputs.
