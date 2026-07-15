# Documentation Structure Model

## Purpose

This document defines how documentation in this repository should be organised
as the repository grows.

It provides a stable classification model for the `docs/` tree so that future
changes can improve navigation without weakening governance lineage, source
document intake, release traceability or downstream repository references.

## Status

| Field | Value |
|---|---|
| Document type | Documentation structure model |
| Status | Draft operating guidance |
| Change type | Documentation-only |
| Primary audience | Governance maintainers, Enterprise Architecture, DevSecOps platform team, AI agents |
| Scope | Human-readable documentation under `docs/` |
| Out of scope | Machine-readable governance model data, released baseline packages, generated reports |
| Source Document Intake | Not a source document |
| Baseline impact | None |

## Guiding Principle

The documentation structure should make the repository feel like one coherent
governance system while keeping the operational risk of reorganising files low.

The structure should therefore separate:

- official entrypoints
- normative governance documents
- source documents
- governance change records
- architecture and operating model explanations
- runbooks and operational procedures
- evidence and result handling
- platform adapter documentation
- onboarding paths
- demos, examples and reference runs
- release documentation

The repository should avoid large documentation moves unless the target
structure is already documented, navigation updates are prepared, and validation
can confirm that published paths remain coherent.

## Stable Zones

The following areas should be treated as stable zones.

| Area | Path | Rule |
|---|---|---|
| Official entrypoints | `docs/index.md`, `docs/official-entrypoints.md`, `docs/ai-index.md`, `docs/lesekompass.md` | Keep these paths stable because humans and agents use them for orientation. |
| Source documents | `docs/governance/source-documents/` | Do not mix with explanatory documentation. Full Source Document Intake applies here. |
| Governance change requests | `docs/governance/change-requests/` | Keep as the audit trail for governance and documentation changes. |
| Release documentation | `docs/releases/` | Keep stable because release references are consumed by downstream teams. |
| Role-based paths | `docs/paths/` | Keep stable because they provide reader journeys. |
| Generated reports | `generated/reports/` | Do not move into `docs/`; these are generated outputs. |

## Recommended Target Taxonomy

The `docs/` tree should evolve towards the following conceptual taxonomy.

```text
docs/
  index.md
  official-entrypoints.md
  ai-index.md
  lesekompass.md

  governance/
    source-documents/
    change-requests/
    core/
    architecture/
    operating-model/

  operations/
    guides/
    runbooks/
    processes/
    evidence/
    agents/
    adapters/
    status/
    planning/
    reference-runs/

  onboarding/
  paths/
  controls/
  platform/
  pipeline-baseline/
  releases/
  examples/
  publishing/
  demos/
```

This is a target taxonomy, not an immediate migration instruction. Existing
paths should be moved only through small, reviewed migration changes.

## Document Classes

### Official Entrypoint Documents

Purpose:

- provide a small number of stable starting points
- guide human readers and AI agents to the right document
- reduce direct dependency on deep file paths

Recommended paths:

- `docs/index.md`
- `docs/official-entrypoints.md`
- `docs/ai-index.md`
- `docs/lesekompass.md`

Rules:

- keep these files short and navigational
- update them whenever important documentation is added
- avoid embedding detailed operating procedures here

### Normative Governance Documents

Purpose:

- describe governance intent, authority, principles and mandatory governance
  concepts
- connect policy, directive, baselines and governance-as-code behavior

Recommended current path:

- `docs/governance/`

Potential future subfolders:

- `docs/governance/core/`
- `docs/governance/operating-model/`

Rules:

- do not mix approved source documents into this class
- avoid changing normative wording through structural cleanup changes
- use a GCR when the document changes governance meaning

### Source Documents

Purpose:

- preserve source material from which governance requirements, controls,
  architecture rules or operating requirements may be derived

Required path:

- `docs/governance/source-documents/`

Rules:

- full Source Document Intake applies only when files under this path or the
  source document register change
- source documents should not be silently edited for formatting
- candidate replacements must be reviewed through the source intake process

### Governance Change Requests

Purpose:

- record decisions, impact, source classification and validation for governance
  and documentation changes

Required path:

- `docs/governance/change-requests/`

Rules:

- keep GCRs close to the governance source and audit trail
- use Non-Source Change Classification for ordinary explanatory documentation
- do not use GCRs as substitutes for source documents

### Architecture And Capability Explanations

Purpose:

- explain how Enterprise Architecture, DevSecOps governance and software
  industrialisation fit together
- make the repository understandable as a coherent architecture system

Recommended current paths:

- `docs/governance/architecture/`
- `docs/platform/`

Previous path:

- `docs/governance/`

Examples:

- ADO and DevSecOps-as-Code integration model
- software industrialisation problem and capability map
- governance repository architecture comparison
- platform and control baseline relationship

Rules:

- these documents are explanatory unless they explicitly define normative
  controls, policies or release behavior
- changes should normally be documentation-only unless they alter operational
  governance behavior

### Operating Model And Process Documents

Purpose:

- describe how maintainers operate the repository
- explain review, intake, enforcement, release and publishing processes

Recommended current path:

- `docs/operations/adapters/`

Previous path:

- `docs/operations/`

Potential future path:

- `docs/governance/operating-model/` for governance lifecycle documents
- `docs/operations/runbooks/` for executable procedures

Rules:

- keep process documents distinct from source documents
- keep step-by-step runbooks distinct from conceptual operating models
- document whether a process is advisory, report-only or blocking

### Evidence And Result Handling Documents

Purpose:

- describe evidence contracts, schema versioning, result intake, viewer usage and
  storage behavior

Recommended current path:

- `docs/operations/evidence/`

Previous path:

- `docs/operations/`

Rules:

- update schemas and tests when evidence contracts change
- separate explanatory documentation from machine-readable schema files under
  `schemas/`

### Agent Operation Documents

Purpose:

- describe how AI agents, agent profiles, harnesses and usage tracking support
  governance work

Recommended current path:

- `docs/operations/agents/`

Previous path:

- `docs/operations/`

Rules:

- keep agent usage guidance operational
- keep role authority and reviewer responsibility in governance role documents
- avoid making agents final decision makers for source intake decisions

### Platform Adapter Documents

Purpose:

- describe how the governance repository integrates with CI/CD platforms such as
  GitHub Actions, Bitbucket and Bamboo

Recommended current path:

- `docs/operations/`

Potential future path:

- `docs/operations/adapters/`

Rules:

- keep executable templates in their platform-specific technical locations
- use adapter documentation to explain behavior, constraints and rollout path
- version-sensitive platform details should be explicit

### Onboarding And Reader Paths

Purpose:

- help new teams, operators, auditors and maintainers consume the repository
  effectively

Recommended paths:

- `docs/onboarding/`
- `docs/paths/`

Rules:

- keep these documents reader-oriented
- avoid duplicating policy text
- link to official governance and release documents instead of copying content

### Demos, Examples And Reference Runs

Purpose:

- show concrete usage, validation examples and historical reference runs

Recommended current paths:

- `docs/operations/reference-runs/`
- root-level `docs/demo-*` documents until migrated

Potential future paths:

- `docs/demos/`
- `docs/examples/`
- `docs/operations/reference-runs/`

Rules:

- reference runs may describe a point-in-time result
- demos should not be confused with normative governance behavior
- historical reference output should not be used as the source of truth for the
  current baseline

### Release Documents

Purpose:

- publish human-readable release notes, release statements and baseline
  descriptions

Recommended path:

- `docs/releases/`

Rules:

- do not rewrite released baseline documents during structure cleanup
- new releases should point to the technical release package under `releases/`
- release documentation should remain stable for downstream consumers

## Migration Rules

Documentation structure improvements should follow these rules.

1. Define the intended target class before moving a document.
2. Move only a small group of related documents at a time.
3. Update `mkdocs.yml`, `docs/official-entrypoints.md` and `docs/ai-index.md`.
4. Preserve or clearly redirect important old reader paths where needed.
5. Do not mix structural moves with governance meaning changes.
6. Do not move source documents without applying the Source Document Intake
   rules.
7. Do not rewrite released baseline documents as part of a cleanup.
8. Validate the repository after each migration package.

## Recommended First Migration Packages

The lowest-risk future migration packages are:

| Package | Candidate move | Risk |
|---|---|---|
| Agent operations | completed: root-level agent operation documents moved into `docs/operations/agents/` | Low |
| Evidence operations | completed: evidence and architecture evidence operation documents moved into `docs/operations/evidence/` | Medium |
| Platform adapters | completed: CI/CD, GitHub, Bitbucket, Bamboo and Mistral adapter documents moved into `docs/operations/adapters/` | Medium |
| Demos | completed: demo and ha-CPsWMS result explanation documents moved into `docs/demos/` | Low to medium |
| Architecture explanations | completed: ADO integration, capability map and repository comparison moved into `docs/governance/architecture/` | Medium |
| Runtime governance explanations | completed: runtime governance addendum and transformation documents moved into `docs/governance/architecture/` | Low |

These packages should be handled in separate commits so reviewers can see that
the changes are structural rather than semantic.

## Source Intake Boundary

This document does not change Source Document Intake scope.

Full Source Document Intake applies when:

- a file is added to or changed under `docs/governance/source-documents/`
- the source document register is changed
- a change explicitly introduces, replaces, supersedes or retires a source
  document

Ordinary documentation structure work outside that boundary should be recorded
as a Non-Source Change Classification in the relevant GCR.

## Validation Expectations

Before merging documentation structure changes, maintainers should normally run:

```bash
python3 scripts/validate_runtime_governance.py
python3 scripts/validate_governance_repo.py
python3 -m unittest discover -s tests
```

If MkDocs is available locally, also run:

```bash
python3 -m mkdocs build --strict
```

Generated report timestamp churn should not be committed when the content did
not change.

## Relationship To The Repository Target Structure

This document complements
`docs/operations/planning/repository-target-structure-and-migration-plan.md`.

The target structure plan describes the broader repository layout across
`docs/`, `model/`, `generated/`, `releases/`, `schemas/`, scripts and workflow
areas.

This document focuses specifically on the documentation layer and defines how
future documentation moves should be classified and sequenced.

## Conclusion

The repository should be reorganised gradually, using a documented taxonomy and
small migration packages.

That approach improves the reader experience and makes Enterprise Architecture,
DevSecOps governance and governance-as-code appear as one integrated system
without putting source lineage, releases or downstream references at risk.
