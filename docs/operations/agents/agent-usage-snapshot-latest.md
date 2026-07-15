# Agent Usage Snapshot Latest

Generated at: `2026-07-06T20:04:36Z`

## Summary

- Source log: `generated/agent-usage/agent-usage.jsonl`
- Events: `17`
- First event: `2026-07-06T18:12:27Z`
- Last event: `2026-07-06T20:04:30Z`
- Data handling: metadata-only; no prompts, secrets, file contents, or model responses are stored.

## Agent Usage

| Agent | Count |
| --- | --- |
| repo-steward | 17 |
| release-manager | 9 |
| evidence-and-intake | 8 |
| architecture-runtime-governance | 7 |
| governance-analyst | 2 |
| demo-readiness | 1 |
| devsecops-baseline | 1 |

## Skill Usage

| Skill | Count |
| --- | --- |
| repo-steward | 17 |
| release-management | 9 |
| evidence-and-intake | 8 |
| architecture-runtime-governance | 7 |
| governance-analysis | 2 |
| demo-readiness | 1 |
| devsecops-baseline | 1 |

## Provider Usage

| Provider | Count |
| --- | --- |
| none | 15 |
| codex | 2 |

## Platform Usage

| Platform | Count |
| --- | --- |
| local | 17 |

## Run Type Usage

| Run type | Count |
| --- | --- |
| dispatch | 15 |
| provider_review | 2 |

## Frequent Change Areas

| Change area | Count |
| --- | --- |
| docs/operations | 29 |
| tests | 26 |
| scripts | 23 |
| pipeline-baseline/templates/app-architecture-evidence | 14 |
| generated/reports | 12 |
| generated/agent-usage | 8 |
| schemas | 7 |
| generated/demo | 4 |
| .agents/routing | 3 |
| .agents/providers | 2 |
| policies/example-input.architecture-release-candidate-findings.json | 2 |
| policies/example-input.architecture-release-candidate.json | 2 |
| docs/ai-index.md | 1 |
| docs/official-entrypoints.md | 1 |
| generated/viewer | 1 |
| mkdocs.yml | 1 |
| pipeline-baseline/templates/bamboo | 1 |
| pipeline-baseline/templates/bitbucket | 1 |

## Warnings

| Warning | Count |
| --- | --- |
| none | none |

## Latest Runs

| Timestamp | Type | Provider | Platform | Agents | Impact | Paths | Areas |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-07-06T18:36:02Z | dispatch | none | local | architecture-runtime-governance, devsecops-baseline, evidence-and-intake, release-manager, repo-steward | candidate | 17 | docs/operations, generated/reports, pipeline-baseline/templates/bamboo, pipeline-baseline/templates/bitbucket, scripts, tests |
| 2026-07-06T18:40:06Z | provider_review | codex | local | architecture-runtime-governance, evidence-and-intake, release-manager, repo-steward | candidate | 11 | docs/operations, pipeline-baseline/templates/app-architecture-evidence, schemas, scripts |
| 2026-07-06T18:46:25Z | dispatch | none | local | architecture-runtime-governance, evidence-and-intake, release-manager, repo-steward | candidate | 5 | docs/operations, generated/demo, scripts, tests |
| 2026-07-06T18:52:42Z | dispatch | none | local | architecture-runtime-governance, evidence-and-intake, release-manager, repo-steward | candidate | 5 | docs/operations, pipeline-baseline/templates/app-architecture-evidence, scripts, tests |
| 2026-07-06T18:59:05Z | dispatch | none | local | architecture-runtime-governance, evidence-and-intake, release-manager, repo-steward | candidate | 12 | docs/operations, generated/demo, pipeline-baseline/templates/app-architecture-evidence, policies/example-input.architecture-release-candidate-findings.json, policies/example-input.architecture-release-candidate.json, schemas, scripts, tests |
| 2026-07-06T19:04:17Z | dispatch | none | local | architecture-runtime-governance, evidence-and-intake, release-manager, repo-steward | candidate | 14 | docs/operations, generated/demo, pipeline-baseline/templates/app-architecture-evidence, policies/example-input.architecture-release-candidate-findings.json, policies/example-input.architecture-release-candidate.json, schemas, scripts, tests |
| 2026-07-06T19:15:15Z | dispatch | none | local | repo-steward | none | 4 | docs/operations, generated/agent-usage, scripts, tests |
| 2026-07-06T19:42:08Z | dispatch | none | local | repo-steward | none | 3 | docs/operations, scripts, tests |
| 2026-07-06T19:47:10Z | dispatch | none | local | architecture-runtime-governance, demo-readiness, evidence-and-intake, repo-steward | candidate | 8 | docs/ai-index.md, docs/official-entrypoints.md, docs/operations, generated/agent-usage, generated/viewer, mkdocs.yml, scripts |
| 2026-07-06T20:04:30Z | provider_review | codex | local | repo-steward | none | 3 | docs/operations, scripts, tests |
