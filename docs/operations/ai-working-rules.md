# AI Working Rules

## Purpose

This document explains how AI agents should work safely in this repository.

`AGENTS.md` is the short operational instruction. This document gives the reasoning and the slightly fuller workflow.

## Default Working Model

Use this loop:

1. Read the relevant source, model, policy, schema and generated output.
2. Make a focused change.
3. Regenerate derived artifacts when the repository has a script for them.
4. Validate.
5. Review `git status --short` and `git diff`.
6. Commit only the intended files.
7. Push after each completed step when requested by the maintainer.

## Treat Source And Generated Files Differently

Source-like files include:

```text
docs/governance/source-documents/
model/
architecture/
pipeline-baseline/
policies/opa/
schemas/
scripts/
tests/
docs/
```

Generated or intake files include:

```text
generated/
status/
releases/
```

Rules:

- Prefer scripts for generated files.
- Do not hand-edit indexes when an intake script or generator exists.
- Do not remove historical result files unless the maintainer explicitly asks.
- Do not change release packages casually; released baselines are controlled artifacts.

## Source-Document Lineage

Every important governance artifact should be traceable to a source document.

Use:

```bash
python3 scripts/generate_source_lineage_report.py
python3 scripts/validate_governance_repo.py
```

The key report is:

```text
generated/reports/source-lineage-report.md
```

The healthy demo state is:

```text
Source documents: 20
Derived artifact links: 289
Missing derived artifacts: 0
```

If a new artifact is added from a source document, update the relevant lineage metadata instead of leaving the artifact orphaned.

## Validation Expectations

Full validation:

```bash
python3 scripts/validate_runtime_governance.py
python3 scripts/validate_governance_repo.py
python3 -m unittest discover -s tests
```

Interpretation:

- Runtime validation protects architecture governance.
- Governance repo validation protects DevSecOps controls, traceability and lineage.
- Unit tests protect generators, release scripts, intake helpers and reports.

If validation changes only a generated timestamp and no meaningful content changed, keep the commit focused and do not include timestamp-only noise unless the maintainer wants a refreshed report timestamp.

## Demo Safety Rules

The demo target is `joku-dev/ha-CPsWMS`.

Keep these values consistent across demo docs and viewer data:

| Domain | Status | Baseline | Run |
|---|---|---|---|
| DevSecOps | `pass` | `l1-baseline-v1.1.3` | `29415015878` |
| Architecture | `PASS` | `architecture-baseline-l1-v0.1.0` | `29415015294` |

Primary demo document:

```text
docs/demos/demo-end-to-end-governance.md
```

Architecture-specific demo document:

```text
docs/demos/demo-ha-cpswms-runtime-governance.md
```

Do not reintroduce old demo assumptions that architecture is expected to produce findings. The current demo state is green: `4/4` architecture gates and `0` findings.

## Report-Only And Blocking

Default demo posture:

```text
report-only
```

Report-only means:

- findings are visible
- artifacts are created
- viewer and indexes are updated
- delivery is not blocked by default

Blocking means:

- a workflow fails on findings
- the same evidence and policy logic are used
- enforcement is stricter, but the governance model is not different

Only change enforcement behavior when the maintainer explicitly asks.

## Release Discipline

Current released baselines:

```text
l1-baseline-v1.1.3
architecture-baseline-l1-v0.1.0
```

When changing a released baseline, prefer a new version. Update release statements, release metadata, package checksums, reusable workflows and documentation together.

Do not silently mutate the meaning of an existing released baseline.

## Git Hygiene

Before every commit:

```bash
git status --short
git diff --check
git diff --stat
```

Never commit:

```text
.DS_Store
docs/.DS_Store
docs/governance/.DS_Store
```

If the worktree contains unrelated local changes, leave them alone. Work with relevant user changes, but do not revert changes you did not make unless explicitly instructed.

## Useful Commands

Open current viewer locally:

```bash
cd /workspace/devsecops-governance-framework/generated/viewer
python3 -m http.server 8000
```

Then open:

```text
http://localhost:8000/status-viewer.html
```

Regenerate viewer:

```bash
python3 scripts/generate_status_viewer.py
```

Regenerate source-lineage report:

```bash
python3 scripts/generate_source_lineage_report.py
```

Inspect current latest architecture result:

```bash
jq '.repositories[] | select(.repository_id=="joku-dev/ha-CPsWMS")' status/architecture-results-index.json
```

Inspect current latest DevSecOps result:

```bash
jq '.repositories[] | select(.repository_id=="joku-dev/ha-CPsWMS")' status/repository-results-index.json
```
