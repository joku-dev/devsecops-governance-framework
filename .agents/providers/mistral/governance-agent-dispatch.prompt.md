# Mistral Governance Agent Dispatch

Use this prompt as the Mistral entry point for a branch, pull request, or change-set review in this repository.

## Runtime Inputs

Provide:

- changed file paths relative to the repository root
- user goal or change summary
- available validation output
- pipeline context if available: `mainline`, `branch`, `pull_request`, or `manual`
- CI/CD platform if available: `github-actions`, `bitbucket-pipelines`, `bamboo`, `jenkins`, `gitlab-ci`, or `local`

## Required Source Contracts

Read these files first:

```text
.agents/routing/governance-agent-routing.yaml
docs/governance/governance-roles-and-agent-profiles.md
docs/operations/agents/agent-system-usage.md
docs/operations/agents/agent-harness-usage.md
```

For every selected agent, read:

```text
.agents/roles/<agent-id>.yaml
.agents/skills/<matching-skill>/SKILL.md
```

Do not read `.codex/agents/` or `.github/codex/prompts/` as source contracts. Those files are Codex provider adapters only.

## Dispatch Procedure

1. Normalize changed paths relative to the repository root.
2. Select agents from `.agents/routing/governance-agent-routing.yaml`.
3. Always include `repo-steward` for meaningful changes.
4. For each selected agent, apply the matching `.agents/roles/*.yaml` contract and `.agents/skills/*/SKILL.md` workflow.
5. Classify release impact as `none`, `governance_model`, `candidate`, or `released_baseline`.
6. Classify policy and workflow behavior as `report-only`, `blocking`, or `unchanged`.
7. For evidence changes, classify run context as `mainline`, `branch`, `pull_request`, or `manual`.
8. Report required validation commands and whether they were run.

## Safety Checks

- Do not derive controls, markers, OPA policies, schemas, or release packages from candidate source documents before review.
- Do not silently mutate released baselines.
- Do not change report-only behavior into blocking behavior without explicit classification and release review.
- Do not update official latest status from branch, pull request, or manual evidence unless explicitly intended.
- Do not include local artifacts such as `.DS_Store`, `__pycache__`, or timestamp-only generated noise.
- Do not introduce Mistral-only governance rules. Add shared rules to the model-neutral `.agents/` contracts.

## Output Format

Return plain text or JSON that preserves this structure:

```text
Selected agents:
- repo-steward: reason
- <agent>: reason

Impact:
- release impact: none|governance_model|candidate|released_baseline
- enforcement behavior: unchanged|report-only|blocking
- evidence context: none|mainline|branch|pull_request|manual
- provider: mistral
- platform: github-actions|bitbucket-pipelines|bamboo|jenkins|gitlab-ci|local|unknown

Required validation:
- <command>: run|not run|not applicable

Findings:
- <severity>: <file/path>: <issue>

Commit readiness:
- ready|not ready
- reason
```
