# Repository Target Structure And Migration Plan

## Purpose

This document proposes a professional target structure for `devsecops-governance-as-code`.

The goal is to make the repository easier to understand, easier to operate, and better suited for:

- governance ownership
- application repository onboarding
- documentation publishing
- release packaging
- audit preparation
- long-term scaling

## Design Principle

The most important principle is:

> Human-readable documentation, machine-readable governance source data, generated artifacts, and released baseline packages should not be mixed together.

That means the repository should clearly separate:

1. **documentation for people**
2. **structured source/model data**
3. **generated outputs**
4. **released baseline packages**
5. **automation**

## Recommended Target Structure

```text
docs/
  index.md
  governance/
  controls/
  platform/
  pipeline-baseline/
  onboarding/
  operations/
  releases/

model/
  controls/
  platform/
  documents/
  traceability/
  evidence/
  waivers/

policies/
  opa/

scripts/

schemas/

templates/
  ci/

status/

generated/
  documents/
  reports/
  viewer/
  xlsx/
  demo/

releases/
  v0.1/
    baseline-package.md
    source/
    generated-documents/
    traceability/
    policy-rules/
    schemas/
    release-metadata.json

.github/
  workflows/
    validate.yml
    publish-docs.yml
    release-baseline.yml
  pull_request_template.md
  CODEOWNERS

mkdocs.yml
```

## Why This Structure Is Better

### `docs/`

This becomes the navigation and publishing layer for people.

It should contain:

- explanations
- onboarding guides
- operating model
- management readouts
- published background documentation

It should **not** be the primary location for machine-readable source data.

### `model/`

This becomes the working source-of-truth layer for structured governance data.

This is where the actual machine-readable governance model lives.

This is the best place for:

- controls
- platform capabilities
- governance document catalog
- evidence types
- waivers
- traceability

This makes it much clearer which content is:

- authoritative model data
- versus explanatory documentation

### `generated/`

This remains the current working output area.

It should contain generated artifacts such as:

- rendered documents
- reports
- status viewer
- matrices
- demo outputs

This is operational output, not source.

### `releases/`

This becomes the versioned baseline publication layer.

This is where approved baseline snapshots should live.

Each release package should contain:

- the source snapshot used for the release
- generated review artifacts
- policy rules
- traceability outputs
- schemas
- metadata describing the release

This is especially important if the repository becomes an official enterprise governance baseline.

## Recommended Mapping From Current Structure

The following mapping is the recommended evolution path.

### Current `model/controls/`

Current:

```text
model/controls/
```

Target:

```text
model/controls/
```

Reason:

- these files are structured governance source data, not end-user documentation

### Current `model/platform/`

Current:

```text
model/platform/
```

Target:

```text
model/platform/
docs/platform/
```

Split logic:

- `model/platform/` contains the machine-readable platform capability data
- `docs/platform/` contains the human explanation of the platform model

### Current `model/documents/`

Current:

```text
model/documents/
```

Target:

```text
model/documents/
```

Reason:

- `governance-documents.yaml` and related rendering config are structured governance metadata

### Current `model/traceability/`

Current:

```text
model/traceability/
```

Target:

```text
model/traceability/
```

Reason:

- traceability is part of the core governance model

### Current `model/evidence/`

Current:

```text
model/evidence/
```

Target:

```text
model/evidence/
```

Reason:

- evidence types are core model definitions

### Current `model/waivers/`

Current:

```text
model/waivers/
```

Target:

```text
model/waivers/
```

Reason:

- waiver structures are part of the governance data model

### Current `docs/policy/` and `docs/directive/`

Current:

```text
docs/policy/
docs/directive/
```

Recommended target:

```text
docs/governance/
```

Example:

```text
docs/governance/devsecops-policy.md
docs/governance/devsecops-directive.md
```

Reason:

- Policy and Directive are human-facing governance documents
- grouping them under `governance/` makes navigation clearer

### Current `docs/governance/source-documents/`

Current:

```text
docs/governance/source-documents/
```

Recommended target:

```text
docs/governance/source-documents/
```

Reason:

- these are still documentation-side source reference artifacts, not machine-readable model data

### Current onboarding and explanation documents

Current examples:

- `docs/onboarding/application-repo-onboarding.md`
- `docs/onboarding/how-other-repositories-use-the-central-governance-baseline.md`
- `docs/governance/policy-directive-baseline-verification-and-governance-as-code-explained.md`
- `docs/platform/control-baseline-and-platform-architecture-relationship-explained.md`

Recommended target:

```text
docs/onboarding/
docs/governance/
docs/controls/
docs/platform/
```

For example:

```text
docs/onboarding/application-repo-onboarding.md
docs/onboarding/how-other-repositories-use-the-central-governance-baseline.md
docs/governance/policy-directive-baseline-verification-and-governance-as-code-explained.md
docs/platform/control-baseline-and-platform-architecture-relationship-explained.md
```

### Current reusable workflow and templates

Current:

- `.github/workflows/devsecops-baseline-reusable.yml`
- `templates/ci/`
- `examples/github-actions/workflows/`

Recommended target documentation grouping:

```text
docs/pipeline-baseline/
```

The actual executable files should remain where GitHub needs them:

- `.github/workflows/`
- `templates/ci/`

But the documentation about them should be grouped in one place.

### Current `generated/`

Current:

```text
generated/
```

Recommended target:

```text
generated/
```

No major structural change is required here.

This is already a good separation for generated artifacts.

### New `releases/`

This should be added as a first-class structure.

Example:

```text
releases/
  v0.1/
    baseline-package.md
    source/
    generated-documents/
    traceability/
    policy-rules/
    schemas/
    release-metadata.json
```

Reason:

- allows reproducible baseline publication
- gives application repositories a stable reference point
- improves auditability
- supports enterprise rollout

## Recommended `docs/` Navigation Structure

The `docs/` tree should be optimized for readers.

Recommended structure:

```text
docs/
  index.md
  governance/
    policy.md
    directive.md
    governance-document-hierarchy.md
    source-of-truth.md
    policy-directive-baseline-verification-and-governance-as-code-explained.md
    MANAGEMENT_READOUT.md
  model/controls/
    control-baseline-and-platform-architecture-relationship-explained.md
  model/platform/
    platform-capability-model.md
  pipeline-baseline/
    reusable-workflow.md
    compliance-evidence-model.md
  onboarding/
    application-repo-onboarding.md
    how-other-repositories-use-the-central-governance-baseline.md
  operations/
    how-to-use-this-repo.md
    beginner-step-by-step-operations-guide.md
    operational-governance-enforcement-options.md
  releases/
    release-process.md
    release-catalog.md
```

## Recommended Source-of-Truth Strategy

The current repository already points in the right direction:

- structured YAML should become the working governance model
- documentation should explain and render that model
- generated artifacts should be treated as outputs

Therefore the best long-term source-of-truth structure is:

### Human documentation

- `docs/`

### Structured governance source

- `model/`

### Generated outputs

- `generated/`

### Released governance packages

- `releases/`

This is cleaner than placing everything under `docs/`.

## Recommended GitHub Workflow Naming

Your suggested GitHub workflow naming also makes sense.

Recommended target:

```text
.github/workflows/
  validate.yml
  publish-docs.yml
  release-baseline.yml
```

Suggested intent:

- `validate.yml`
  - run validation
  - run tests
  - run OPA checks
  - regenerate key artifacts if needed

- `publish-docs.yml`
  - publish MkDocs or Pages site
  - expose human-readable governance portal

- `release-baseline.yml`
  - create a versioned baseline package
  - export release artifacts into `releases/vX.Y/`

## Recommended Release Package Content

A proper released baseline should ideally contain:

### Source Snapshot

- control YAML
- platform YAML
- evidence YAML
- traceability YAML
- waiver model
- document catalog

### Generated Review Artifacts

- rendered policy
- rendered directive
- traceability matrix
- document-control matrix
- open gap report
- status viewer snapshot

### Executable Governance Content

- OPA policy rules
- reusable pipeline workflow references
- integration templates

### Metadata

For example:

```json
{
  "release_id": "v0.1",
  "baseline_repo": "devsecops-governance-as-code",
  "commit": "db69905",
  "status": "pilot",
  "included_levels": ["L1", "L2", "L3", "GOV"],
  "published_at": "2026-06-27T00:00:00Z"
}
```

## Recommended Migration Approach

This should be done incrementally, not in one large disruptive move.

### Phase 1: Documentation Layer

First:

- add `docs/index.md`
- group human-readable documents into clearer topical folders
- add `mkdocs.yml`

This gives immediate usability benefits with relatively low risk.

### Phase 2: Source Model Layer

Then:

- introduce `model/`
- move `model/controls/`, `model/platform/`, `model/documents/`, `model/traceability/`, `model/evidence/`, `model/waivers/` into it
- update scripts, tests, and references

This is the most structurally important step.

### Phase 3: Release Layer

Then:

- add `releases/`
- add packaging logic
- create the first official baseline release

### Phase 4: Documentation Publishing

Then:

- add `mkdocs.yml`
- publish via GitHub Pages or similar

## What Should Not Be Done

The following would be less ideal:

- moving everything into `docs/` without separating source model data
- mixing generated outputs with authoritative source data
- treating release snapshots as if they were the working source
- changing the structure without updating validation scripts and tests

## Recommended Final Direction

The strongest long-term structure for this repository is:

```text
docs/      -> documentation for humans
model/     -> source of truth for governance data
generated/ -> generated working outputs
releases/  -> versioned published baseline packages
```

This structure best supports:

- governance operations
- engineering usability
- auditability
- release management
- future scaling into an enterprise governance product

## Final Recommendation

Yes, the proposed direction makes sense.

But the best implementation is not:

- “put everything into `docs/`”

The best implementation is:

- use `docs/` as the human-facing portal
- use `model/` as the structured governance source
- use `generated/` as current output
- use `releases/` as the approved publication layer

That gives the repository a much more professional and scalable operating shape.
