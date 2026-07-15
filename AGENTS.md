# Agent Instructions

## Purpose

This file gives Codex and other AI agents the minimum operating context for this repository.

This repository is a governance-as-code engine. Treat it as a controlled governance system, not as a generic documentation repository.

## Repository Mission

The repository translates governance source documents into:

- structured DevSecOps control models
- structured architecture runtime governance models
- OPA policy-as-code
- JSON schemas
- released baselines
- generated reports
- downstream result intake indexes
- a static governance status viewer

The current demo target is `joku-dev/ha-CPsWMS`.

## Source Of Truth

Prefer these sources when changing behavior:

| Area | Primary files |
|---|---|
| Foundation and direction | `docs/foundation/01_VISION.md`, `docs/foundation/02_CONSTITUTION.md`, `docs/foundation/03_ARCHITECTURE_PRINCIPLES.md`, `docs/foundation/04_REFERENCE_ARCHITECTURE.md`, `docs/foundation/05_CURRENT_DIRECTION.md`, `docs/foundation/07_AI_CONTEXT.md` |
| Source documents | `docs/governance/source-documents/` |
| New artifact intake | `docs/operations/processes/new-artifact-intake-process.md` |
| Source document intake | `model/documents/source-document-register.yaml`, `docs/governance/governance-change-lifecycle.md`, `docs/operations/processes/source-document-intake-review-operating-model.md` |
| Role and review routing | `docs/governance/governance-roles-and-agent-profiles.md` |
| Model-neutral agent contracts | `.agents/roles/`, `.agents/routing/governance-agent-routing.yaml`, `.agents/skills/` |
| Codex agent adapters | `.codex/agents/`, `.github/codex/prompts/`, `docs/operations/agents/agent-system-usage.md` |
| Agent routing harness | `tests/agent_harness/`, `docs/operations/agents/agent-harness-usage.md` |
| DevSecOps controls | `model/controls/` |
| Platform mapping | `model/platform/`, `model/traceability/` |
| Architecture governance | `architecture/` |
| OPA policies | `policies/opa/` |
| Schemas | `schemas/` |
| Result indexes | `status/` |
| Release packages | `releases/` and `docs/releases/` |
| Viewer | `generated/viewer/status-viewer.html` |
| AI navigation | `docs/ai-index.md` |

Generated reports under `generated/` should normally be updated by scripts, not by manual editing, except for narrowly scoped timestamp cleanup after validation noise.

Foundation documents provide architectural and strategic guardrails. They do not replace approved policy, directive, standards, released baselines, source-document registers, or recorded governance decisions.

## Current Released Baselines

| Domain | Baseline |
|---|---|
| DevSecOps L1 | `l1-baseline-v1.1.3` |
| Architecture L1 | `architecture-baseline-l1-v0.1.0` |

Do not silently change released baseline packages or tags. If a baseline changes, create an explicit new release or release-candidate flow.

## Current Demo State

The `ha-CPsWMS` mainline demo state is:

| Domain | Status | Baseline | Run |
|---|---|---|---|
| DevSecOps | `pass` | `l1-baseline-v1.1.3` | `29415015878` |
| Architecture | `PASS` | `architecture-baseline-l1-v0.1.0` | `29415015294` |

Use `docs/demos/demo-end-to-end-governance.md` as the primary demo runbook.

## Required Validation

Before committing governance behavior, schemas, generated reports, viewer data, or docs that describe current results, run:

```bash
./scripts/bootstrap_validation_env.sh
./scripts/validate_all.sh
```

The bootstrap is idempotent. The complete validation command uses the pinned
Python dependencies and OPA version declared by the repository. Its expanded
validation sequence is:

```bash
opa check policies/opa
python3 scripts/validate_runtime_governance.py
python3 scripts/validate_governance_repo.py
python3 -m unittest discover -s tests
```

The unit test suite includes the local agent harness under `tests/agent_harness/`. It validates deterministic role routing and safety invariants without live Codex or LLM calls.

Governance-agent behavior is model-neutral first: update `.agents/roles/`, `.agents/routing/`, and `.agents/skills/` before updating Codex-specific adapters under `.codex/agents/`.

For very small documentation-only changes, the same validation is still preferred because docs and generated indexes are tightly connected in this repo.

## Commit And Push Practice

The maintainer preference is:

1. Make one coherent change.
2. Validate it.
3. Commit it.
4. Push it.
5. Report the commit hash.

Keep commits focused. Do not mix unrelated generated output, local OS files, and source changes.

## Files To Avoid Committing

Never add local OS or editor artifacts, especially:

```text
.DS_Store
docs/.DS_Store
docs/governance/.DS_Store
```

If they are present as untracked files, leave them alone unless explicitly asked to remove them.

## Report-Only Versus Blocking

The current demo should remain report-only unless explicitly changed.

- Report-only means findings are visible in reports, artifacts, indexes and the viewer.
- Blocking means the workflow fails on findings.

DevSecOps supports manual mode selection. Architecture is currently demonstrated as report-only and can be hardened later by enabling fail-on-findings in consuming workflows.

## Safe Change Rules

- Do not rewrite source document history casually.
- Do not modify released baseline packages unless creating an intentional release update.
- Do not change OPA enforcement behavior without updating docs and tests.
- Do not change schemas without validating existing examples and generated results.
- Do not edit status indexes by hand when an intake or generator script should be used.
- Do not delete historical status results unless explicitly requested.
- Preserve source-document lineage when adding new governance artifacts.
- New source documents that may duplicate or replace existing sources should be registered as `candidate` first. Do not derive controls, markers, policies or baselines from a candidate until review confirms the decision.
- Classify new artifacts with `docs/operations/processes/new-artifact-intake-process.md` before choosing a target path or deriving behavior from them.

## Useful Starting Points

Read these first for most future work:

```text
docs/ai-index.md
docs/official-entrypoints.md
docs/foundation/01_VISION.md
docs/foundation/02_CONSTITUTION.md
docs/foundation/07_AI_CONTEXT.md
docs/governance/governance-change-lifecycle.md
docs/governance/governance-roles-and-agent-profiles.md
docs/operations/processes/new-artifact-intake-process.md
docs/operations/processes/source-document-intake-review-operating-model.md
docs/demos/demo-end-to-end-governance.md
docs/operations/evidence/governance-result-intake-and-viewer-usage.md
docs/releases/index.md
generated/reports/source-lineage-report.md
generated/reports/governance-change-impact.md
generated/reports/architecture-source-replacement-assessment.md
generated/reports/source-document-intake-status.md
generated/reports/source-document-intake-review-briefs.md
generated/reports/source-document-requirement-delta.md
```
