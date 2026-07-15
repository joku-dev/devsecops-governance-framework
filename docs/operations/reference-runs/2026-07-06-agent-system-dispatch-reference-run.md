# Agent System Dispatch Reference Run - 2026-07-06

## Purpose

This reference run documents how the repository governance agent system works from changed paths to selected review roles, required validations, warnings, and provider execution.

The run is intentionally deterministic. It uses the local dispatch CLI and the model-neutral harness. It does not require Codex, Mistral, GitHub, Bitbucket, Bamboo, secrets, or network access.

Provider adapters such as Codex or Mistral can use the same dispatch result as input for an LLM-assisted review.

## Repository State

Run date: 2026-07-06

Branch at start:

```text
main
```

The relevant model-neutral contracts are:

```text
.agents/routing/governance-agent-routing.yaml
.agents/roles/*.yaml
.agents/skills/*/SKILL.md
tests/agent_harness/routing.py
scripts/dispatch_governance_agents.py
```

Provider adapters are projections of this neutral layer:

```text
.codex/agents/
.github/codex/prompts/
.agents/providers/mistral/
```

Platform adapters are CI/CD projections:

```text
pipeline-baseline/templates/bitbucket/
pipeline-baseline/templates/bamboo/
pipeline-baseline/templates/jenkins/
pipeline-baseline/templates/gitlab-ci/
```

## How The System Works

The agent system has four layers:

1. Role contracts define what each governance role owns.
2. Routing maps changed paths to the roles that must review them.
3. Skills describe the review workflow for each role.
4. Provider adapters translate the neutral contracts into a runtime such as Codex or Mistral.

The deterministic dispatch CLI performs these steps:

1. Accept changed paths from command-line arguments or `git diff`.
2. Normalize paths relative to the repository root.
3. Match paths against `.agents/routing/governance-agent-routing.yaml`.
4. Always add `repo-steward` when there is a meaningful repository change.
5. Collect validations from the selected roles.
6. Classify release impact.
7. Emit warnings for risky combinations, such as source-document changes together with derived governance artifacts.

## Scenario A: Company Platform Adapter Change

This scenario represents a change to Bitbucket and Bamboo pipeline templates.

### Input

```text
pipeline-baseline/templates/bitbucket/bitbucket-pipelines.yml
pipeline-baseline/templates/bamboo/bamboo-specs.yml
```

### Command

```bash
python3 scripts/dispatch_governance_agents.py \
  pipeline-baseline/templates/bitbucket/bitbucket-pipelines.yml \
  pipeline-baseline/templates/bamboo/bamboo-specs.yml
```

### Actual Output

```text
Governance Agent Dispatch

Changed files:
- pipeline-baseline/templates/bitbucket/bitbucket-pipelines.yml
- pipeline-baseline/templates/bamboo/bamboo-specs.yml

Selected agents:
- devsecops-baseline
- release-manager
- repo-steward

Release impact: none

Required validation:
- git diff --check
- python3 -m unittest discover -s tests
- python3 scripts/validate_governance_repo.py
```

### Machine-Readable Output

```bash
python3 scripts/dispatch_governance_agents.py --json \
  pipeline-baseline/templates/bitbucket/bitbucket-pipelines.yml \
  pipeline-baseline/templates/bamboo/bamboo-specs.yml
```

```json
{
  "changed_files": [
    "pipeline-baseline/templates/bitbucket/bitbucket-pipelines.yml",
    "pipeline-baseline/templates/bamboo/bamboo-specs.yml"
  ],
  "release_impact": "none",
  "required_validations": [
    "git diff --check",
    "python3 -m unittest discover -s tests",
    "python3 scripts/validate_governance_repo.py"
  ],
  "selected_agents": [
    "devsecops-baseline",
    "release-manager",
    "repo-steward"
  ],
  "warnings": []
}
```

### Interpretation

`devsecops-baseline` is selected because platform pipeline templates can change how the baseline is validated or enforced.

`release-manager` is selected because pipeline template changes can affect release evidence, repeatability, or promotion behavior.

`repo-steward` is selected for every meaningful repository change. Its job is to keep the commit focused, check local artifacts, and require `git diff --check`.

The release impact is `none` because the example changes platform adapter templates, not released baseline content, OPA policies, schemas, or governance model files.

No warning is emitted because the changed files are all platform-adapter files and do not mix candidate source documents with derived governance artifacts.

## Scenario B: Risky Governance Change

This scenario represents a higher-risk change where a candidate source document, an OPA policy, and an evidence schema change together.

### Input

```text
docs/governance/source-documents/DEVSECOPS-POL-SRC-001.public.md
policies/opa/vulnerability_gate.rego
schemas/governance-evidence.schema.json
```

### Command

```bash
python3 scripts/dispatch_governance_agents.py \
  docs/governance/source-documents/DEVSECOPS-POL-SRC-001.public.md \
  policies/opa/vulnerability_gate.rego \
  schemas/governance-evidence.schema.json
```

### Actual Output

```text
Governance Agent Dispatch

Changed files:
- docs/governance/source-documents/DEVSECOPS-POL-SRC-001.public.md
- policies/opa/vulnerability_gate.rego
- schemas/governance-evidence.schema.json

Selected agents:
- evidence-and-intake
- governance-analyst
- policy-as-code
- release-manager
- repo-steward
- source-document-intake

Release impact: candidate

Required validation:
- git diff --check
- opa check policies/opa
- python3 -m unittest discover -s tests
- python3 scripts/generate_governance_change_impact_report.py
- python3 scripts/generate_status_viewer.py
- python3 scripts/validate_governance_repo.py

Warnings:
- Derived governance artifact path changed; verify no candidate source was used before review.
```

### Machine-Readable Output

```bash
python3 scripts/dispatch_governance_agents.py --json \
  docs/governance/source-documents/DEVSECOPS-POL-SRC-001.public.md \
  policies/opa/vulnerability_gate.rego \
  schemas/governance-evidence.schema.json
```

```json
{
  "changed_files": [
    "docs/governance/source-documents/DEVSECOPS-POL-SRC-001.public.md",
    "policies/opa/vulnerability_gate.rego",
    "schemas/governance-evidence.schema.json"
  ],
  "release_impact": "candidate",
  "required_validations": [
    "git diff --check",
    "opa check policies/opa",
    "python3 -m unittest discover -s tests",
    "python3 scripts/generate_governance_change_impact_report.py",
    "python3 scripts/generate_status_viewer.py",
    "python3 scripts/validate_governance_repo.py"
  ],
  "selected_agents": [
    "evidence-and-intake",
    "governance-analyst",
    "policy-as-code",
    "release-manager",
    "repo-steward",
    "source-document-intake"
  ],
  "warnings": [
    "Derived governance artifact path changed; verify no candidate source was used before review."
  ]
}
```

### Interpretation

`source-document-intake` is selected because a source document changed.

`governance-analyst` is selected because source-document changes may affect control interpretation, lifecycle decisions, or governance traceability.

`policy-as-code` is selected because an OPA policy changed.

`evidence-and-intake` is selected because a schema changed and evidence compatibility must be reviewed.

`release-manager` is selected because policy and schema changes can affect release readiness and downstream compatibility.

`repo-steward` is selected for hygiene, validation discipline, and commit readiness.

The release impact is `candidate` because OPA policies and schemas can affect governance behavior but are not released baseline files by themselves.

The warning is important. It prevents a common governance error: taking an unreviewed candidate source document and immediately deriving policy, schema, or other governance artifacts from it before formal review.

## Provider Execution After Dispatch

After dispatch, a provider adapter can execute the selected roles.

For Codex, use:

```text
.github/codex/prompts/governance-agent-dispatch.md
.codex/agents/*.toml
```

For Mistral, use:

```text
.agents/providers/mistral/governance-agent-dispatch.prompt.md
.agents/providers/mistral/role-execution-contract.md
```

In both cases, the provider must read the same neutral contracts:

```text
.agents/routing/governance-agent-routing.yaml
.agents/roles/*.yaml
.agents/skills/*/SKILL.md
```

The provider must not redefine roles, routing, validations, or governance invariants.

## Commit Readiness Pattern

A complete agent-system run should record:

```text
Selected agents:
- <agent>: <reason>

Impact:
- release impact: none|governance_model|candidate|released_baseline
- enforcement behavior: unchanged|report-only|blocking
- evidence context: none|mainline|branch|pull_request|manual
- provider: codex|mistral|none
- platform: github-actions|bitbucket-pipelines|bamboo|jenkins|gitlab-ci|local|unknown

Required validation:
- <command>: run|not run|not applicable

Findings:
- <severity>: <file/path>: <issue>

Commit readiness:
- ready|not ready
- reason
```

For local deterministic dispatch, `provider` is `none` because no LLM provider is called.

## Validation For This Reference Run

Run the harness:

```bash
python3 -m unittest discover -s tests/agent_harness
```

Run the full repository test suite:

```bash
python3 -m unittest discover -s tests
```

Check whitespace and patch hygiene:

```bash
git diff --check
```

## What This Proves

This reference run proves that the repository can:

- select governance roles from changed paths without a live LLM
- preserve `repo-steward` as a mandatory hygiene role
- distinguish ordinary platform adapter changes from candidate governance changes
- emit required validation commands from role ownership
- produce machine-readable dispatch output for CI/CD or provider wrappers
- keep GitHub/Codex, Bitbucket/Bamboo, and Mistral as adapters around the same governance core
