# Mistral Provider Adapter

## Purpose

This directory contains the Mistral-specific projection of the repository governance agent system.

The adapter is intentionally thin. It helps a Mistral runtime execute the same governance roles, routing rules, skill workflows, validation expectations, and output contracts that are defined in the model-neutral agent layer.

## Source Contracts

Read these contracts before running a Mistral governance review:

```text
.agents/routing/governance-agent-routing.yaml
.agents/roles/*.yaml
.agents/skills/*/SKILL.md
docs/governance/governance-roles-and-agent-profiles.md
docs/operations/agents/agent-system-usage.md
```

The files in this directory are not a governance source of truth. They must not redefine role ownership, path routing, release classification, validation expectations, or policy behavior.

## Adapter Files

```text
.agents/providers/mistral/governance-agent-dispatch.prompt.md
.agents/providers/mistral/role-execution-contract.md
```

Use `governance-agent-dispatch.prompt.md` as the Mistral entry prompt for a branch, pull request, or change-set review.

Use `role-execution-contract.md` to configure orchestration wrappers, Bamboo jobs, or Bitbucket build steps that call Mistral for one or more selected governance roles.

## Expected Flow

1. Collect changed paths relative to the repository root.
2. Select roles from `.agents/routing/governance-agent-routing.yaml`.
3. Always include `repo-steward` for meaningful repository changes.
4. Read every selected role contract from `.agents/roles/`.
5. Read the matching skill workflow from `.agents/skills/`.
6. Run or record the validations required by the selected roles.
7. Return the review using the shared output contract.

For local deterministic dispatch without a model provider, use:

```bash
python3 scripts/dispatch_governance_agents.py --base-ref origin/main
```

## Company Platform Usage

For a Bitbucket and Bamboo setup, keep platform behavior in platform adapter files such as:

```text
pipeline-baseline/templates/bitbucket/
pipeline-baseline/templates/bamboo/
```

Those platform adapters may invoke a Mistral wrapper, but they should still emit normalized evidence through the central schemas and validators.

## Architecture Detailed Evidence

When Mistral reviews architecture evidence, it should read `architecture.detailed_evidence` from:

```text
architecture-release-input.json
```

This field is report-only unless a future governance baseline explicitly promotes a detailed evidence type to a blocking rule.

Mistral may use detailed evidence to improve review quality, for example:

| Detailed type | Review focus |
|---|---|
| `threat_model` | Security assumptions, mitigations, residual risks. |
| `interface_contract` | Interface ownership, compatibility, versioning, testability. |
| `deployment_manifest` | Deployment assumptions, runtime configuration, rollback readiness. |
| `model_based_architecture` | Model availability, baseline metadata, reviewable export. |

Mistral must not infer a vendor-specific tool mandate from `model_based_architecture`.

## Adapter Boundaries

Allowed in this directory:

- Mistral prompt phrasing
- Mistral orchestration instructions
- Runtime input and output formatting guidance
- Provider-specific safety reminders

Not allowed in this directory:

- new role definitions
- new path routing rules
- replacement skill workflows
- duplicate validation matrices
- provider-only governance invariants
- platform-specific pipeline syntax
