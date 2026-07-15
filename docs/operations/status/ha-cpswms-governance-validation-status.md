# ha-CPsWMS Governance Validation Status

## Purpose

This document records the successful end-to-end validation of the repository then named `devsecops-governance-as-code` against the application repository `ha-CPsWMS`. The current repository identity is `devsecops-governance-framework`.

## Scope

The validation covers:

- reusable governance workflow consumption from the central governance repository
- branch protection enforcement on `main`
- DevSecOps baseline gate execution in GitHub Actions
- normal application CI execution in GitHub Actions
- documentation publishing activation in the governance repository

## Governance Repository Status

Repository:

- `joku-dev/devsecops-governance-as-code` (repository identity at the time of this validation)

Confirmed status:

- GitHub Pages is enabled
- governance validation is green
- static documentation deployment is active through GitHub Actions

Relevant successful runs:

- `Governance CI` run `28283726835` on `2026-06-27T08:21:05Z`
- `Deploy static content to Pages` run `28283726838` on `2026-06-27T08:21:05Z`

Relevant governance fix:

- commit `d914566ed1c6ee2bd472a853d36318933955b120`
- purpose: handle protected branches correctly when the detailed branch protection API is unavailable to the workflow token

## Application Repository Status

Repository:

- `joku-dev/ha-CPsWMS`

Confirmed status:

- `main` branch protection is enabled
- governance workflow is consumed through the central reusable workflow
- pull-request-based update flow is working
- baseline and CI both pass on `main`

Relevant merged change:

- merge commit `8e7b742f41f902b4b85d1f6d4f3e556a96d937a3`
- merge description: `Merge PR #2: Update governance workflow after branch protection fix`

Relevant successful runs on `main`:

- `DevSecOps Baseline` run `28284063513` on `2026-06-27T08:36:38Z`
- `CI` run `28284063427` on `2026-06-27T08:36:38Z`

Relevant successful pull request validation runs:

- `DevSecOps Baseline` run `28283965287` on `2026-06-27T08:32:01Z`
- `CI` run `28283965152` on `2026-06-27T08:32:01Z`

## What Was Proven

The validation demonstrates that:

1. an application repository can consume the central governance workflow by commit pin
2. branch protection settings are reflected in governance evidence and gate evaluation
3. the central baseline gate can block non-compliant conditions and pass compliant ones
4. governance changes can be rolled out through a protected-branch PR flow
5. operational documentation publishing can run in parallel with governance validation

## Operational Meaning

This means the repository is no longer only a modelling exercise. It has been proven in a real GitHub-based integration flow with:

- governance source repository
- reusable GitHub Actions workflow
- protected target repository
- pull request review gate
- successful main-branch enforcement outcome

## Recommended Next Step

Repeat the same onboarding and validation pattern with at least one additional repository to confirm that the approach is reusable beyond a single application repository.
