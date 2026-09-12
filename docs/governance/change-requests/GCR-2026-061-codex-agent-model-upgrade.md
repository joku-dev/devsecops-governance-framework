# GCR-2026-061: Upgrade Codex governance agents to GPT-6 Astra

## Request And Artifact Classification

The maintainer requested the model upgrade and a small historical review
comparison before continuing with planning PR #74. This change is based on
`5311182c220548474fcd90b04c38dc46b144937a` and is independent of that PR.

| Field | Value |
|---|---|
| Artifact type | Codex provider configuration, explanatory documentation and dated evaluation evidence |
| Target paths | `.codex/agents/*.toml`, existing agent guides, `docs/operations/reference-runs/` |
| Owner | Repository maintainer; governance analysis and repository stewardship review |
| Source Document Intake required? | No; no normative source or model-neutral role change |
| Evidence contract impact | None on consumer or governance-result contracts |
| Runtime governance impact | None on policies, enforcement, intake or human decision authority |
| Provider behavior impact | All nine Codex roles request `gpt-6-astra`; reasoning remains `high` |
| Release impact | No baseline or repository release required for this adapter update |
| Validation | Pinned full suite, strict MkDocs build, adapter diff inspection, bounded live model evaluation |

Classification follows the
[new artifact intake process](../../operations/processes/new-artifact-intake-process.md).
Evaluation outputs are experimental review evidence, not official findings,
accepted consumer snapshots, source approvals or independent human reviews.

## Change And Rationale

Replace the unavailable `gpt-5-codex` model in all nine Codex adapters with
`gpt-6-astra`. Keep the existing high reasoning effort, developer instructions,
neutral role contracts, routing and provider boundaries intact. A uniform first
pilot isolates the model change; lower-cost role selection can be evaluated
separately. No model-neutral artifact needs changing because responsibilities
and governance behavior do not change.

The official migration guidance supports retaining the current effective
reasoning effort. Availability was checked with Codex CLI 0.153.0 and the
existing ChatGPT login. The former model is rejected for that account; GPT-6
responds successfully. Three fixed historical packets were reviewed with
GPT-5.5 and GPT-6. The [reference run](../../operations/reference-runs/2026-09-12-gpt6-agent-evaluation.md)
records both favorable results and limitations, including higher observed
GPT-6 latency and the lack of a direct old-model comparison.

## Preservation And Validation

No changes to OPA, released packages, source registrations, status indexes,
consumer workflows or human approval rules. PR #74 remains open while this
change is prepared. Evaluation calls are explicit, read-only and excluded from
the deterministic CI harness. Historical review outputs retain their original
content and are accompanied by an analyst assessment.

Run `./scripts/bootstrap_validation_env.sh`, `./scripts/validate_all.sh`, strict
MkDocs, JSON/schema/hash checks on the evaluation bundle and `git diff --check`.
Confirm each adapter differs only in the requested model. Exclude generated
timestamp and worktree-path noise after inspection. The PR records validation
results and remains subject to the active review and required-check rules.
