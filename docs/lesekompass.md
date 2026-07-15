# Reading Compass For New Team Members

## Purpose

This reading compass helps new team members understand the repository without having to read every document in order.

Use it as the first human orientation layer before choosing a role-based path or changing governance artifacts.

## The Short Version

This repository is not just documentation. It is a governance-as-code engine with four connected layers:

| Layer | What it contains | Where to look |
|---|---|---|
| Governance intent | Policy, directive, standards and source documents | `docs/governance/`, `docs/governance/source-documents/` |
| Machine-readable models | Controls, platform mappings, architecture markers, evidence and traceability | `model/`, `architecture/`, `schemas/` |
| Executable governance | OPA policies, reusable workflows and validation scripts | `policies/opa/`, `.github/workflows/`, `scripts/` |
| Published and consumed results | Released baselines, generated reports, status indexes and viewer | `releases/`, `generated/`, `status/` |

The current demo target is `joku-dev/ha-CPsWMS`.

## Current North Star

| Domain | Current baseline | Current mainline demo status |
|---|---|---|
| DevSecOps L1 | `l1-baseline-v1.1.3` | `pass`, run `29415015878`, `16/16` applicable controls |
| Architecture L1 | `architecture-baseline-l1-v0.1.0` | `PASS`, run `29415015294`, `4/4` gates |

The demo is intentionally report-only. Findings should be visible in reports, artifacts, indexes and the viewer unless a consuming workflow explicitly enables blocking behavior.

## First 30 Minutes

Read these in order if you are new:

1. `README.md`
2. `docs/official-entrypoints.md`
3. `docs/demos/demo-end-to-end-governance.md`
4. `docs/operations/status/current-governance-platform-state.md`
5. `docs/releases/index.md`

After that, choose the path that matches your role:

| If you are... | Read next |
|---|---|
| new to the repository | `docs/paths/beginner-path.md` |
| operating an application integration | `docs/paths/operator-path.md` |
| reviewing compliance or evidence | `docs/paths/auditor-path.md` |
| maintaining this repository | `docs/paths/maintainer-path.md` |
| an AI agent or automation assistant | `docs/ai-index.md` and `AGENTS.md` |

## How To Navigate By Question

| Question | Start here |
|---|---|
| What is this repository for? | `README.md`, then `docs/index.md` |
| What is the official navigation page? | `docs/official-entrypoints.md` |
| What is the current demo status? | `docs/demos/demo-end-to-end-governance.md` |
| Which baselines are current? | `docs/releases/index.md` |
| How does an app repo consume governance? | `docs/onboarding/application-repo-onboarding.md` |
| What evidence does an app repo need? | `docs/operations/evidence/governance-evidence-contract.md` |
| How are results ingested and shown? | `docs/operations/evidence/governance-result-intake-and-viewer-usage.md` |
| Where did a control or marker come from? | `generated/reports/source-lineage-report.md` |
| What changed or could change from source documents? | `generated/reports/governance-change-impact.md` |
| Which architecture source may replace the current one? | `generated/reports/architecture-source-replacement-assessment.md` |
| How do report-only and blocking differ? | `docs/operations/processes/operational-governance-enforcement-options.md` |

## Mental Model For The Repository

Read from left to right:

```text
Source documents
  -> structured control and architecture models
  -> schemas and OPA policies
  -> released baselines
  -> downstream application evidence
  -> normalized status results
  -> generated reports and status viewer
```

Important rule: do not silently change released baselines. If released behavior changes, use an explicit release or release-candidate flow.

## What Is Generated

Generated reports and viewer files normally come from scripts:

| Output | Usual generator |
|---|---|
| Source lineage report | `scripts/generate_source_lineage_report.py` |
| Governance change impact report | `scripts/generate_governance_change_impact_report.py` |
| Architecture source replacement assessment | `scripts/generate_architecture_source_replacement_assessment.py` |
| Repository results index | `scripts/generate_repository_results_index.py` |
| Architecture results index | `scripts/generate_architecture_results_index.py` |
| Status viewer | `scripts/generate_status_viewer.py` |

Avoid hand-editing generated outputs unless the change is explicitly scoped and the owning script is not appropriate.

## Validation Habit

Before committing governance behavior, schemas, generated reports, viewer data, or docs that describe current results, run:

```bash
python3 scripts/validate_runtime_governance.py
python3 scripts/validate_governance_repo.py
python3 -m unittest discover -s tests
```

Expected healthy result:

```text
Runtime governance validation passed
Validation passed
OK
```

## Known Orientation Pitfalls

| Pitfall | How to avoid it |
|---|---|
| Confusing historical releases with the current release | Treat `v1.1.3` as current DevSecOps L1 and `architecture/l1/v0.1.0` as current Architecture L1. Older release docs are historical. |
| Confusing the architecture governance baseline with the application solution baseline | `architecture-baseline-l1-v0.1.0` is the reusable governance baseline. `ha-CPsWMS-demo-baseline` is app evidence. |
| Confusing PR results with official status | The viewer's latest result prefers `push` results on `main`. Branch and PR runs stay in history. |
| Treating report-only findings as approval blockers | Report-only findings are visible but do not fail the workflow unless blocking is explicitly enabled. |
| Deriving runtime governance from candidate sources too early | Candidate source documents require manual review before changing source status, lineage, YAML source fields, or release planning. |

## Suggested First Tasks

For a new team member, the safest first contributions are:

1. run the three validation commands locally
2. read the current demo runbook and compare it with the generated current-main reports
3. inspect the source lineage report for one DevSecOps source and one architecture source
4. follow the operator path for a downstream repository onboarding scenario
5. review the architecture source replacement assessment before proposing architecture baseline changes
