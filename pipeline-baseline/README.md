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
