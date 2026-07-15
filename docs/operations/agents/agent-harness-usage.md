# Agent Harness Usage

## Purpose

The agent harness is a deterministic safety net for Codex governance-agent routing.

It does not call an LLM and does not grade free-text agent answers. It checks whether repository changes imply the expected governance roles, validations, release-impact classification, and safety invariants.

## What It Covers

The harness currently covers:

- path-to-agent routing for governance repository areas
- mandatory `repo-steward` selection for meaningful changes
- required validation commands per selected role
- scenario fixtures for common governance changes
- candidate source-document protection
- released baseline protection
- evidence context protection for non-mainline results

The role profile document remains the source of truth:

```text
docs/governance/governance-roles-and-agent-profiles.md
```

The model-neutral agent contracts live in:

```text
.agents/roles/
.agents/routing/governance-agent-routing.yaml
.agents/skills/
```

## Files

```text
tests/agent_harness/routing.py
tests/agent_harness/test_agent_contracts.py
tests/agent_harness/test_agent_routing.py
tests/agent_harness/test_agent_scenarios.py
tests/agent_harness/scenarios/*.json
tests/agent_harness/expected/*.expected.json
.agents/roles/*.yaml
.agents/routing/governance-agent-routing.yaml
.agents/skills/*/SKILL.md
```

## Run The Harness

Run only the harness:

```bash
python3 -m unittest discover -s tests/agent_harness
```

Run it with the full repository tests:

```bash
python3 -m unittest discover -s tests
```

The harness is intentionally local-only. It must not require network access, GitHub secrets, live Codex execution, or live LLM calls.

Use the deterministic dispatch CLI for day-to-day routing:

```bash
python3 scripts/dispatch_governance_agents.py --base-ref origin/main
```

For the end-to-end operator workflow around dispatch, role execution, validation, and commit readiness, read:

```text
docs/operations/agents/how-to-run-agent-review.md
```

The routing contract also reserves adapter paths for company CI/CD platforms such as Bamboo, Bitbucket, Jenkins, and GitLab. These paths route to neutral governance roles (`devsecops-baseline`, `release-manager`, and `repo-steward`) rather than to GitHub- or Codex-specific behavior.

## Add A Scenario

1. Add a scenario JSON file under:

```text
tests/agent_harness/scenarios/
```

2. Add the matching expected result under:

```text
tests/agent_harness/expected/
```

The expected file name must match this pattern:

```text
<scenario-name>.expected.json
```

3. Include at least:

```json
{
  "selected_agents": ["repo-steward"],
  "required_validations": ["git diff --check"],
  "release_impact": "none",
  "forbidden_changes": [],
  "commit_readiness": "requires_review"
}
```

4. Run:

```bash
python3 -m unittest discover -s tests/agent_harness
```

## Interpret Failures

A routing failure means the changed paths no longer map to the expected review roles.

A required-validation failure means a selected role does not demand a validation command expected by the scenario.

A release-impact failure means a scenario may silently change release or baseline semantics.

A candidate-protection failure means a candidate source document may have produced derived governance artifacts too early.

An evidence-context failure means a branch, pull request, or manual run may be treated like an official mainline result.

## Extend Routing

Update routing only when the repository structure or governance ownership model changes:

```text
tests/agent_harness/routing.py
```

Keep changes small and add or update a scenario for every new routing rule.

## Relationship To Existing Validators

The harness does not replace:

```bash
opa check policies/opa
python3 scripts/validate_runtime_governance.py
python3 scripts/validate_governance_repo.py
```

It tells maintainers which of those validations should be requested by the selected governance roles.
