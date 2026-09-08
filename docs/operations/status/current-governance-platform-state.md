# Current Governance Platform State

## Purpose

This document explains the current overall state of the `devsecops-governance-framework` repository after the latest governance, release, publishing, downstream integration, architecture runtime governance, and result intake work.

It is intended as a single place where readers can understand:

- what the repository now contains
- what has already been proven operationally
- how downstream repositories are expected to use it
- how results are now stored and summarized

## Current High-Level State

The repository now acts as six things at the same time:

1. a governance source repository
2. a documentation publishing repository
3. a released baseline package repository
4. a central index for normalized downstream governance results
5. a static status viewer for DevSecOps, architecture and lineage status
6. a generated governance intelligence graph for relationship exploration
7. a report-only self-security subject whose repository protection, workflow
   supply chain, ownership, and release integrity are assessed independently
   from consumer outcomes

## What Exists Now

### Governance Source Layer

The machine-readable governance source remains in:

- `model/controls/`
- `model/platform/`
- `model/documents/`
- `model/traceability/`
- `model/evidence/`
- `model/waivers/`
- `architecture/`
- `schemas/`

This is the working source-of-truth layer.

### Documentation Layer

The human-readable documentation now lives under:

- `docs/governance/`
- `docs/onboarding/`
- `docs/operations/`
- `docs/platform/`
- `docs/releases/`

This layer explains the operating model, onboarding flow, release model, and governance interpretation.

### Release Layer

The current released baseline packages are:

- DevSecOps L1: `l1-baseline-v1.1.3` under `releases/l1/v1.1.3/`
- Architecture L1: `architecture-baseline-l1-v0.1.0` under `releases/architecture/l1/v0.1.0/`

These packages provide frozen, reviewable snapshots of:

- control or architecture model data
- evidence and input schemas
- OPA policy rules
- versioned workflow wrappers
- downstream usage examples
- release metadata and checksums

### Central Results Layer

The repository now also contains a normalized central results store:

- `status/results/`
- `status/repository-results-index.json`
- `status/architecture-results/`
- `status/architecture-results-index.json`

This allows the repository to record downstream governance outcomes in a structured and auditable way.

Central intake operations are additionally recorded under:

- `status/intake-events/`

These append-only events include success, failure, and measured collection
duration. They are operational telemetry for a later health projection and do
not replace result snapshots or Collection Attempts.

### Viewer Layer

The static viewer is generated at:

- `generated/viewer/status-viewer.html`

It summarizes the latest known downstream DevSecOps and architecture results and links them back to generated reports and source lineage information.

### Governance Graph Layer

The deterministic, read-only graph projection is generated at:

- `generated/graph/governance-graph.json`

Its contract and generator are:

- `schemas/governance-graph.schema.json`
- `scripts/generate_governance_graph.py`

The graph is rendered interactively inside the static viewer. It does not replace the source models, indexes, result snapshots, or released baselines and provides no write-back path.

## What Has Been Proven Operationally

The repository is not only a modelling repository anymore.

The following has already been demonstrated in practice:

### 1. Documentation Publishing Works

The repository now supports GitHub Pages publishing through GitHub Actions.

Relevant parts:

- `mkdocs.yml`
- `.github/workflows/publish-docs.yml`
- `.github/workflows/static.yml`

This means the documentation layer can be built and published as a static site.

### 2. Governance Validation Works

The governance repository validates successfully through:

- repository validation
- tests
- documentation build validation

This proves functional consistency and buildability. It does not by itself
prove that the governance authority is protected against unreviewed mutation,
workflow supply-chain compromise, or unsigned release replacement. That
separate posture is evaluated through the Governance Repository Self-Security
profile.

### 3. Released L1 Baselines Exist

The current versioned baseline releases are:

- DevSecOps release tag: `l1-baseline-v1.1.3`
- DevSecOps package path: `releases/l1/v1.1.3/`
- Architecture release tag: `architecture-baseline-l1-v0.1.0`
- Architecture package path: `releases/architecture/l1/v0.1.0/`

This means downstream repositories can consume stable baseline references without pointing at `main`.

### 4. Real Downstream Consumption Was Proven

The repository was exercised successfully against:

- `joku-dev/ha-CPsWMS`

This included:

- reusable workflow consumption
- branch protection enforcement
- protected-branch PR flow
- successful DevSecOps baseline run on `main`
- successful architecture runtime governance run on `main`
- successful CI run on `main`

Current known-good `ha-CPsWMS` mainline results:

| Domain | Status | Baseline | Run |
|---|---|---|---|
| DevSecOps | `pass` | `l1-baseline-v1.1.3` | `29415015878` |
| Architecture | `PASS` | `architecture-baseline-l1-v0.1.0` | `29415015294` |

### 5. Central Result Recording Exists

Successful downstream runs are now recorded in the repository as normalized result snapshots.

Current examples:

- `status/results/joku-dev__ha-CPsWMS/2026-07-15T17-07-40Z-run-29415015878.json`
- `status/architecture-results/joku-dev__ha-CPsWMS/2026-07-15T17-06-39Z-run-29415015294.json`

And summarized centrally in:

- `status/repository-results-index.json`
- `status/architecture-results-index.json`

## Step-By-Step Explanation Of The Current Operating Model

### Step 1: Define Governance In Structured Form

Governance controls, evidence, traceability, and related models are maintained under `model/`.

### Step 2: Explain Governance In Human-Readable Form

Policy, Directive, onboarding, release, and operations documentation are maintained under `docs/`.

### Step 3: Validate The Repository

The repository validates itself through scripts and tests.

This ensures:

- data consistency
- documentation buildability
- workflow consistency

### Step 4: Release A Frozen Baseline

When a stable downstream baseline is needed, a versioned release package is created under `releases/`.

Current examples are:

- `releases/l1/v1.1.3/`
- `releases/architecture/l1/v0.1.0/`

### Step 5: Downstream Repositories Consume The Released Workflow

Other repositories should consume:

- `.github/workflows/devsecops-baseline-l1-v1.1.3.yml`
- `.github/workflows/architecture-baseline-l1-v0.1.0.yml` when architecture runtime governance is in scope

and pin it by:

- release tag
- or full commit SHA

### Step 6: Downstream Pipelines Produce Governance Results

Application repositories run the governance baseline workflow and produce governance-relevant pipeline outcomes.

### Step 7: Important Outcomes Can Be Normalized Back Into This Repository

Selected results can be recorded under:

- `status/results/`

This creates an auditable, Git-tracked registry of downstream governance outcomes.

### Step 8: A Central Index Summarizes The Latest Known State

The collector script regenerates:

- `status/repository-results-index.json`

This index can then be used by viewers, reports, or later dashboard integrations.

## What Downstream Repositories Should Use Today

If another repository wants to consume the current approved `L1` baseline, it should use:

- `.github/workflows/devsecops-baseline-l1-v1.1.3.yml`
- reference: `@l1-baseline-v1.1.3`

If it also consumes the released architecture runtime governance baseline, it should use:

- `.github/workflows/architecture-baseline-l1-v0.1.0.yml`
- reference: `@architecture-baseline-l1-v0.1.0`

It should not consume `main` if revision-safe governance consumption is required.

## What Is Already Well Documented

The following areas are already covered in dedicated documents:

- official entrypoints: `docs/official-entrypoints.md`
- control evaluation status explanation: `docs/operations/evidence/how-to-read-control-evaluation-status.md`
- MkDocs and Pages: `docs/operations/guides/mkdocs-and-github-pages-step-by-step.md`
- downstream validation proof: `docs/operations/status/ha-cpswms-governance-validation-status.md`
- results storage model: `docs/operations/evidence/governance-results-storage-model.md`
- DevSecOps L1 release package: `docs/releases/l1-baseline-v1.1.3.md`
- DevSecOps L1 release statement: `docs/releases/l1-baseline-v1.1.3-release-statement.md`
- Architecture L1 release package: `docs/releases/architecture-baseline-l1-v0.1.0.md`
- Architecture L1 release statement: `docs/releases/architecture-baseline-l1-v0.1.0-release-statement.md`

## Remaining Gaps

The current model is already useful, but there are still professionalization steps that could be added later:

- stronger revision protection for stored result snapshots
- signed manifests or digests for downstream result packages
- broader collector automation and operational hardening
- viewer enhancement for larger multi-repository portfolios
- additional released packages for `L2` and `L3`
- confirmed review of the likely architecture source replacement candidate before changing runtime governance or release planning
- continued hardening of source-document intake decision metadata after the report-only intake status, review briefs and requirement deltas are reviewed

## Current Recommendation

The current repository should now be treated as:

- an operational governance source
- an operational release source for `L1`
- an operational documentation source
- a first controlled registry for downstream governance results
- a first controlled registry for source-document intake status, decision-support review briefs and requirement deltas
- a demo-ready report-only governance status viewer

## Recommended Next Step

The most logical next governance step is to use `generated/reports/source-document-intake-status.md`, `generated/reports/source-document-intake-review-briefs.md` and `generated/reports/source-document-requirement-delta.md` to review open source-document intake items, especially the likely architecture source replacement candidate, before changing runtime governance source status, lineage, or baseline planning.

The most logical next technical hardening step is to strengthen revision protection for stored downstream results by adding:

- append-only result handling
- per-result digests
- manifest generation
- clearly documented intake rules
