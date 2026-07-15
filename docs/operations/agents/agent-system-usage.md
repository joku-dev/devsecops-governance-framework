# Agent System Usage

## Purpose

The repository now separates governance-agent behavior into two layers:

- model-neutral contracts under `.agents/`
- Codex adapter files under `.codex/` and `.github/codex/`

The model-neutral layer is the durable repository contract. Codex files project that contract into Codex-specific working surfaces.

This separation is intentional. GitHub and Codex are the private learning and prototyping path, while company environments may use Bitbucket, Bamboo, and Mistral. Those company-specific surfaces must be added as adapters around the same `.agents/` contracts instead of forking the governance model.

## Model-Neutral Layer

```text
.agents/roles/*.yaml
.agents/routing/governance-agent-routing.yaml
.agents/skills/*/SKILL.md
```

Use this layer for:

- role responsibility contracts
- routing rules from changed paths to required roles
- reusable workflow steps
- validation expectations
- output expectations

The role profile document remains the governance source of truth:

```text
docs/governance/governance-roles-and-agent-profiles.md
```

## Codex Adapter Layer

```text
.codex/agents/*.toml
.github/codex/prompts/governance-agent-dispatch.md
.github/codex/prompts/repo-steward-review.md
```

Use this layer for:

- project-scoped Codex custom agents
- branch or pull request dispatch prompts
- focused repo-steward reviews

Codex agent files should point back to `.agents/roles/` and `.agents/skills/` instead of duplicating detailed governance logic.

## Future Provider And Platform Adapters

Future adapters should stay additive:

```text
.agents/roles/
.agents/routing/governance-agent-routing.yaml
.agents/skills/
```

remain the shared contract.

Examples of allowed adapter layers:

```text
.codex/agents/
.github/codex/prompts/
pipeline-baseline/templates/bamboo/
pipeline-baseline/templates/bitbucket/
pipeline-baseline/templates/jenkins/
templates/ci/
```

For a Mistral-based company setup, add Mistral-specific prompts, wrappers, or runtime configuration as a provider adapter that reads `.agents/roles/` and `.agents/skills/`. Do not move role responsibility, routing, validation expectations, or governance invariants into a Mistral-only location.

For Bitbucket and Bamboo, keep platform variables and pipeline syntax in dedicated templates or wrapper scripts. They should emit the same normalized governance evidence expected by the central schemas and validators.

## Mistral Provider Adapter

Use the Mistral provider adapter when the company execution surface uses Mistral instead of Codex:

```text
.agents/providers/mistral/README.md
.agents/providers/mistral/governance-agent-dispatch.prompt.md
.agents/providers/mistral/role-execution-contract.md
```

The adapter is provider-specific only. It must read the model-neutral contracts under `.agents/roles/`, `.agents/skills/`, and `.agents/routing/governance-agent-routing.yaml`.

Use Bitbucket or Bamboo templates for CI/CD execution details, and use the Mistral adapter only for model-provider prompt and role execution guidance.

## Full Branch Review

For the daily operator workflow, start here:

```text
docs/operations/agents/how-to-run-agent-review.md
```

Use:

```text
.github/codex/prompts/governance-agent-dispatch.md
```

For a detailed documented local reference run, read:

```text
docs/operations/reference-runs/2026-07-06-agent-system-dispatch-reference-run.md
docs/operations/reference-runs/2026-07-06-codex-provider-agent-review-pr12.md
docs/operations/reference-runs/2026-07-06-codex-multi-agent-platform-adapter-review.md
```

Provide changed paths, user goal, and validation output if available.

For a local deterministic dispatch without Codex, run:

```bash
python3 scripts/dispatch_governance_agents.py --base-ref origin/main
```

Or pass paths directly:

```bash
python3 scripts/dispatch_governance_agents.py policies/opa/vulnerability_gate.rego
```

Machine-readable output is available with:

```bash
python3 scripts/dispatch_governance_agents.py --json policies/opa/vulnerability_gate.rego
```

Expected review output:

- selected agents
- release impact
- enforcement behavior
- evidence context
- required validation
- findings
- commit readiness

Optional usage tracking is documented in:

```text
docs/operations/agents/agent-usage-tracking.md
```

## Specific Role Review

For a role-specific review, start with the model-neutral role and skill:

```text
.agents/roles/<role-id>.yaml
.agents/skills/<skill-name>/SKILL.md
```

Then use the matching Codex adapter:

```text
.codex/agents/<role-id>.toml
```

## Repo Steward Review

Use:

```text
.github/codex/prompts/repo-steward-review.md
```

This review checks scope, local artifacts, generated timestamp-only noise, validation evidence, and commit readiness.

## Parallel Agent Usage

Parallel subagents are useful when a change touches separate governance domains, for example:

- `policy-as-code` plus `release-manager`
- `architecture-runtime-governance` plus `policy-as-code`
- `evidence-and-intake` plus `demo-readiness`

Always include `repo-steward` before commit readiness.

## Extend The System

When adding or changing a role:

1. Update `docs/governance/governance-roles-and-agent-profiles.md`.
2. Update or add `.agents/roles/*.yaml`.
3. Update `.agents/routing/governance-agent-routing.yaml` if path ownership changes.
4. Update or add `.agents/skills/*/SKILL.md`.
5. Add or update provider adapters such as `.codex/agents/*.toml` or future Mistral adapter files only as projections of the neutral contracts.
6. Add or update platform adapters such as Bamboo, Bitbucket, Jenkins, or GitLab templates only as pipeline projections of the neutral evidence contract.
7. Add or update harness scenarios under `tests/agent_harness/`.
8. Run:

```bash
python3 -m unittest discover -s tests/agent_harness
python3 -m unittest discover -s tests
git diff --check
```
