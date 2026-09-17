# CI/CD Pipeline Control Baseline

This folder translates the DevSecOps Governance and Control Baseline into a tool-agnostic CI/CD Pipeline Control Baseline.

## Purpose

The pipeline baseline defines:

- mandatory and conditional pipeline stages
- where each control is checked in the pipeline
- gate semantics for pass, warn, fail, waiver, and manual review
- minimum evidence contracts
- minimum metadata required for traceability
- waiver integration behavior
- reference mappings for GitHub Actions, Bitbucket Pipelines, Bamboo, GitLab CI, and Jenkins

## Important

This baseline is tool-agnostic. Tool-specific pipeline templates are implementation examples. The authoritative mapping is `control-placement.yaml`.

## Implemented Adapter Paths

| Platform | Current repository support |
|---|---|
| GitHub Actions | Reusable released workflows, adoption templates, real consumer runs and automated central intake. |
| Bamboo with Bitbucket Data Center | Bamboo 12.1.9 YAML Specs reference templates plus platform-neutral artifact validation and manual bundle intake; validate against the actual server and agent versions before use. |
| Bitbucket Pipelines | Reference pipeline, normalized field mapping and manual bundle intake. |
| Jenkins | DevSecOps and architecture reference Jenkinsfiles plus manual bundle intake. |
| GitLab CI | Reference template using the same evidence contracts. |

All new integrations begin in report-only mode. A reference template proves the
mapping and file contract; it does not prove compatibility with a particular
company installation or authorize a blocking gate.

The platform-neutral bundle commands are documented in the adapter READMEs and
`docs/operations/adapters/cicd-platform-adapter-strategy.md`.
