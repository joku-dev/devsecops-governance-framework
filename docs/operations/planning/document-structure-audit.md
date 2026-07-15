# Documentation Structure Audit

## Purpose

This document records the current state of the documentation structure after the
first documentation migration wave.

It is a stabilisation artifact. It does not move files, change governance
behavior or redefine source-document intake. Its purpose is to make the current
structure reviewable before additional restructuring is attempted.

## Status

| Field | Value |
|---|---|
| Document type | Documentation structure audit |
| Status | Draft audit |
| Change type | Documentation-only |
| Primary audience | Governance maintainers, Enterprise Architecture, DevSecOps platform team, AI agents |
| Scope | Human-readable documentation under `docs/` |
| Source Document Intake | Not a source document |
| Baseline impact | None |

## Completed Migration Wave

The first migration wave created a clearer separation between documentation
classes without changing source documents, governance behavior, schemas, policy
rules or released baselines.

| GCR | Area | Result |
|---|---|---|
| `GCR-2026-008` | Documentation structure model | Added the structure model and migration rules. |
| `GCR-2026-009` | Agent operations | Moved agent operation documents into `docs/operations/agents/`. |
| `GCR-2026-010` | Evidence operations | Moved evidence and result-handling documents into `docs/operations/evidence/`. |
| `GCR-2026-011` | Platform adapters | Moved platform adapter documents into `docs/operations/adapters/`. |
| `GCR-2026-012` | Demos | Moved demo and ha-CPsWMS result explanation documents into `docs/demos/`. |
| `GCR-2026-013` | Governance architecture | Moved architecture explanation documents into `docs/governance/architecture/`. |
| `GCR-2026-014` | Runtime governance | Moved runtime governance explanation documents into `docs/governance/architecture/`. |

## Current Stable Zones

These zones should be treated as stable unless a focused migration GCR explains
why they need to change.

| Zone | Path | Current assessment |
|---|---|---|
| Official entrypoints | `docs/index.md`, `docs/official-entrypoints.md`, `docs/ai-index.md`, `docs/lesekompass.md` | Stable; keep at root for human and AI orientation. |
| Source documents | `docs/governance/source-documents/` | Stable; full Source Document Intake boundary. |
| Governance change requests | `docs/governance/change-requests/` | Stable; historical audit trail. |
| Governance architecture | `docs/governance/architecture/` | Stable; holds explanatory architecture and runtime governance documents. |
| Operations guides | `docs/operations/guides/` | Stable; contains practical repository operation, baseline update and documentation publishing guides. |
| Operations processes | `docs/operations/processes/` | Stable; contains governance operation processes, waiver handling, enforcement options, timing and intake verification. |
| Agent operations | `docs/operations/agents/` | Stable; contains agent usage, harness and tracking guidance. |
| Evidence operations | `docs/operations/evidence/` | Stable; contains evidence contracts, result intake and architecture evidence guidance. |
| Platform adapters | `docs/operations/adapters/` | Stable; contains GitHub, Bitbucket, Bamboo, CI/CD and Mistral adapter guidance. |
| Examples | `docs/examples/` | Stable; contains schema-backed example payloads. |
| Publishing | `docs/publishing/` | Stable; contains publication-oriented communication artifacts. |
| Demos | `docs/demos/` | Stable; contains demo runbooks and result explanations. |
| Release documentation | `docs/releases/` | Stable; do not rewrite released baseline documentation during cleanup. |
| Role paths | `docs/paths/` | Stable; keep reader journeys predictable. |

## Root-Level And Example Documentation Assessment

Some files remain directly under `docs/`. This is intentional for entrypoints,
files with test or schema coupling and a small grouped examples area.

| File | Current classification | Recommendation |
|---|---|---|
| `docs/index.md` | Official entrypoint | Keep at root. |
| `docs/official-entrypoints.md` | Official entrypoint | Keep at root. |
| `docs/ai-index.md` | AI and maintainer navigation | Keep at root. |
| `docs/lesekompass.md` | Reading compass | Keep at root. |
| `docs/examples/governance-run-input.example.json` | Schema-backed example input | Moved into `docs/examples/`; validation and active consumer docs now reference the grouped path. |
| `docs/examples/governance-compliance-result.example.json` | Schema-backed example output | Moved into `docs/examples/`; validation now references the grouped path. |
| `docs/examples/governance-compliance-result.extended.example.json` | Schema-backed extended example output | Moved into `docs/examples/`; active consumer docs now reference the grouped path. |
| `docs/automation-classification.md` | Cross-cutting explanation | Review later; possible future target is `docs/governance/architecture/` or `docs/operations/`. |
| `docs/publishing/confluence-governance-repo-artikel.md` | Publishing/article artifact | Moved into `docs/publishing/`; remains a communication artifact, not a source document. |
| `docs/migration-status.md` | Migration status | Keep temporarily; possible future target is `docs/operations/planning/`. |
| `docs/roadmap.md` | Roadmap | Keep temporarily; possible future target is `docs/operations/planning/`. |

## Operations Root Assessment

The operations root still contains mixed operational documents. That is
acceptable after the first migration wave because the most cohesive clusters
have already been moved.

| Candidate group | Current files | Possible future path | Recommendation |
|---|---|---|---|
| Runbooks and guides | completed: practical guide documents moved into `docs/operations/guides/` | `docs/operations/guides/` | Stable after migration. |
| Process and governance operations | completed: governance process documents moved into `docs/operations/processes/` | `docs/operations/processes/` | Stable after migration. |
| AI working rules | `ai-working-rules.md` | `docs/operations/agents/` | Review as a separate agent-operations migration. |
| Status and lessons learned | completed: current platform state, ha-CPsWMS validation status and lessons learned moved into `docs/operations/status/` | `docs/operations/status/` | Stable after migration. |
| Planning and cleanup | completed: planning and structure documents moved into `docs/operations/planning/` | `docs/operations/planning/` | Stable after migration. |
| Reference runs | `docs/operations/reference-runs/` | Already grouped | Keep stable. |

## Known Compatibility Decisions

The migration wave intentionally did not rewrite:

- historical GCR references that record the path context at the time of the
  decision
- released baseline packages
- generated agent usage logs
- source documents under `docs/governance/source-documents/`

This preserves auditability and avoids changing historical records for cosmetic
reasons.

## Validation Baseline

Each migration package in the first wave was validated with:

```bash
python3 scripts/validate_runtime_governance.py
python3 scripts/validate_governance_repo.py
python3 -m unittest discover -s tests
```

MkDocs validation is available through the repository's documentation
requirements file:

```bash
python3 -m venv .venv-docs
.venv-docs/bin/python -m pip install --upgrade pip
.venv-docs/bin/python -m pip install -r requirements-docs.txt
.venv-docs/bin/mkdocs build --strict
```

The local MkDocs strict build passed after installing `requirements-docs.txt`
into the ignored `.venv-docs/` environment.

The build may report informational messages for source documents and
non-navigation pages. Those messages should be reviewed, but they did not block
the strict build during this audit update.

## Recommended Next Steps

The next documentation changes should be smaller than the first migration wave
and should focus on one of these options:

1. Make MkDocs validation available locally or in CI before additional
   navigation-heavy changes.
2. Review whether `docs/operations/ai-working-rules.md` should move into
   `docs/operations/agents/`.

The JSON examples have been moved into `docs/examples/`. The recommended
publishing article has been moved into `docs/publishing/`. The recommended
operations guides have been moved into `docs/operations/guides/`. The
process and governance operation documents have been moved into
`docs/operations/processes/`. The recommended immediate next step is to review
whether the AI working rules should move into the agent operations folder.

## Conclusion

The documentation structure is now significantly clearer than before the
migration wave. The repository has stable zones for architecture explanations,
runtime governance, operations guides, governance processes, agent operations,
evidence handling, platform adapters, examples, publishing artifacts and demos.

Further movement should be conservative and should prioritize validation,
compatibility and reader navigation over purely aesthetic folder cleanup.
