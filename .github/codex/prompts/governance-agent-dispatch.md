# Governance Agent Dispatch

Use this prompt for a branch or pull request review in this repository.

## Inputs

- Changed file list
- User goal or PR summary
- Any validation output already available

## Source Of Truth

Read these first:

```text
.agents/routing/governance-agent-routing.yaml
docs/governance/governance-roles-and-agent-profiles.md
AGENTS.md
docs/operations/agents/agent-harness-usage.md
```

## Dispatch Procedure

1. Normalize changed paths relative to the repository root.
2. Select agents from `.agents/routing/governance-agent-routing.yaml`.
3. Always include `repo-steward` for meaningful changes.
4. For each selected agent, read the matching `.agents/roles/*.yaml` contract and `.agents/skills/*/SKILL.md` workflow.
5. Classify release impact as `none`, `governance_model`, `candidate`, or `released_baseline`.
6. Classify policy and workflow behavior as `report-only`, `blocking`, or `unchanged`.
7. For evidence changes, classify run context as `mainline`, `branch`, `pull_request`, or `manual`.
8. Report required validation commands and whether they were run.

## Required Safety Checks

- Do not derive controls, markers, OPA policies, schemas, or release packages from candidate source documents before review.
- Do not silently mutate released baselines.
- Do not change report-only behavior into blocking behavior without explicit classification and release review.
- Do not update official latest status from branch, pull request, or manual evidence unless explicitly intended.
- Do not include local artifacts such as `.DS_Store` or `__pycache__`.

## Output Format

```text
Selected agents:
- repo-steward: reason
- <agent>: reason

Impact:
- release impact: none|governance_model|candidate|released_baseline
- enforcement behavior: unchanged|report-only|blocking
- evidence context: none|mainline|branch|pull_request|manual

Required validation:
- <command>: run|not run|not applicable

Findings:
- <severity>: <file/path>: <issue>

Commit readiness:
- ready|not ready
- reason
```
