# Mistral Role Execution Contract

## Purpose

This contract describes how a Mistral runtime should execute one selected governance role from the model-neutral agent layer.

The role execution contract is provider-specific orchestration guidance only. The source of truth remains:

```text
.agents/roles/
.agents/skills/
.agents/routing/governance-agent-routing.yaml
docs/governance/governance-roles-and-agent-profiles.md
```

## Required Inputs

Each role execution must receive:

- `role_id`: selected governance role id
- `changed_paths`: repository-relative changed paths
- `user_goal`: short change summary
- `pipeline_context`: `mainline`, `branch`, `pull_request`, or `manual`
- `platform`: CI/CD surface such as `bitbucket-pipelines`, `bamboo`, `github-actions`, `jenkins`, `gitlab-ci`, or `local`
- `validation_output`: validation output already available, if any

## Required Reads

For `role_id`, read:

```text
.agents/roles/<role_id>.yaml
```

Then read the skill named or implied by that role from:

```text
.agents/skills/*/SKILL.md
```

Also keep the routing and invariant context available from:

```text
.agents/routing/governance-agent-routing.yaml
```

## Execution Rules

- Apply the selected role's `responsibilities`, `validations`, and `output_contract`.
- Use the skill workflow as the procedure for review.
- Include `repo-steward` in the combined review for meaningful repository changes.
- Preserve the shared impact classifications used by the neutral dispatch prompt.
- Treat Mistral as the provider value, not as a governance domain.
- Keep Bitbucket and Bamboo behavior in platform adapters, not in this provider adapter.

## Output Requirements

Every role result must include:

- `role_id`
- `provider`: `mistral`
- `platform`
- `changed_paths_reviewed`
- `impact`
- `required_validation`
- `validation_status`
- `findings`
- `commit_readiness`

Findings should identify severity, file path, issue, and suggested remediation.

## Non-Goals

This contract must not:

- define new governance roles
- override routing from `.agents/routing/governance-agent-routing.yaml`
- replace skill workflows
- create Mistral-only validation requirements
- encode Bamboo or Bitbucket pipeline syntax
