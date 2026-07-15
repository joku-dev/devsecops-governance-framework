# How To Run A Governance Agent Review

## Purpose

Use this runbook when you want to review a branch, pull request, or local change with the governance agent system.

The process is model-neutral first. Codex and Mistral are provider adapters. GitHub Actions, Bitbucket Pipelines, Bamboo, Jenkins, and GitLab CI are platform adapters.

## Quick Path

1. Identify changed files.
2. Run deterministic dispatch.
3. Read the selected role contracts and skill workflows.
4. Execute each selected role review.
5. Run or record the required validation.
6. Write findings and commit readiness.
7. Keep provider and platform details out of the governance core.

## Step 1: Identify Changed Files

For a local branch, run:

```bash
git diff --name-only origin/main
```

For an already staged change, run:

```bash
git diff --cached --name-only
```

For the complete branch scope compared with `main`, run:

```bash
git diff --name-only origin/main...HEAD
```

Use repository-relative paths in the dispatch input.

## Step 2: Run Dispatch

For the current local diff:

```bash
python3 scripts/dispatch_governance_agents.py --base-ref origin/main
```

For explicit paths:

```bash
python3 scripts/dispatch_governance_agents.py pipeline-baseline/templates/bitbucket/README.md
```

For machine-readable output:

```bash
python3 scripts/dispatch_governance_agents.py --json --base-ref origin/main
```

The dispatch result tells you:

- changed files
- selected agents
- release impact
- required validation
- warnings

## Step 3: Interpret Selected Agents

Always expect `repo-steward` when a meaningful repository change exists.

Common path examples:

| Changed path | Expected additional agents |
|---|---|
| `pipeline-baseline/templates/bitbucket/` | `devsecops-baseline`, `release-manager` |
| `pipeline-baseline/templates/bamboo/` | `devsecops-baseline`, `release-manager` |
| `policies/opa/` | `policy-as-code`, `release-manager` |
| `schemas/` | `evidence-and-intake`, `release-manager` |
| `architecture/` | `architecture-runtime-governance`, `policy-as-code` |
| `model/controls/` | `devsecops-baseline`, `governance-analyst` |
| `docs/governance/source-documents/` | `source-document-intake`, `governance-analyst` |
| `releases/` | `release-manager` |

If dispatch emits a warning, handle it before commit readiness.

## Step 4: Read Role And Skill Contracts

For each selected agent, read the neutral role contract:

```text
.agents/roles/<agent-id>.yaml
```

Then read the matching skill workflow:

```text
.agents/skills/<skill-name>/SKILL.md
```

Examples:

| Agent | Role contract | Skill workflow |
|---|---|---|
| `repo-steward` | `.agents/roles/repo-steward.yaml` | `.agents/skills/repo-steward/SKILL.md` |
| `devsecops-baseline` | `.agents/roles/devsecops-baseline.yaml` | `.agents/skills/devsecops-baseline/SKILL.md` |
| `release-manager` | `.agents/roles/release-manager.yaml` | `.agents/skills/release-management/SKILL.md` |
| `policy-as-code` | `.agents/roles/policy-as-code.yaml` | `.agents/skills/policy-as-code/SKILL.md` |
| `evidence-and-intake` | `.agents/roles/evidence-and-intake.yaml` | `.agents/skills/evidence-and-intake/SKILL.md` |

The role contract decides responsibility and required output. The skill workflow decides review procedure.

## Step 5: Execute The Review

For each selected agent, answer the output contract from its role file.

A `devsecops-baseline` review should report:

```text
control impact
evidence impact
release impact
validation results
```

A `release-manager` review should report:

```text
release impact
baseline mutation decision
migration impact
validation results
```

A `repo-steward` review should report:

```text
scope review
hygiene findings
validation summary
commit readiness
```

A `source-document-intake` review should report:

```text
source classification
review brief and decision options
requirement delta summary for replacement candidates
human decision required
candidate derivation blocked or allowed
validation results
```

Keep findings concrete:

```text
<severity>: <file/path>: <issue>
```

Use `none` when no findings exist.

## Step 6: Run Validation

Run the commands from dispatch first.

Common commands:

```bash
git diff --check
python3 scripts/validate_governance_repo.py
python3 scripts/validate_runtime_governance.py
python3 -m unittest discover -s tests
```

For source-document intake changes, also run:

```bash
python3 scripts/generate_source_document_intake_status.py
python3 scripts/generate_source_document_intake_review_briefs.py
python3 scripts/generate_source_document_requirement_delta.py
```

For OPA policy changes, also run:

```bash
opa check policies/opa
```

If the full test suite updates only generated report timestamps, remove that timestamp-only noise from the commit unless a refreshed report timestamp is intentional.

## Step 7: Write The Review Result

Use this format:

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

Optionally record usage for reference runs or audit evidence:

```bash
python3 scripts/dispatch_governance_agents.py \
  --log-usage \
  --run-type provider_review \
  --provider codex \
  --platform local \
  --source reference-run \
  <changed-paths>
```

For details, see:

```text
docs/operations/agents/agent-usage-tracking.md
```

## Step 8: Provider Choices

### Codex

For Codex, use:

```text
.github/codex/prompts/governance-agent-dispatch.md
.codex/agents/*.toml
```

Codex adapter files must point back to:

```text
.agents/roles/
.agents/skills/
.agents/routing/governance-agent-routing.yaml
```

### Mistral

For Mistral, use:

```text
.agents/providers/mistral/governance-agent-dispatch.prompt.md
.agents/providers/mistral/role-execution-contract.md
```

Mistral must also read the same neutral contracts under `.agents/`.

Do not create Mistral-only role ownership, routing, validation rules, or governance invariants.

## Step 9: Platform Choices

Keep CI/CD platform details in platform adapter files:

```text
pipeline-baseline/templates/bitbucket/
pipeline-baseline/templates/bamboo/
pipeline-baseline/templates/jenkins/
pipeline-baseline/templates/gitlab-ci/
.github/workflows/
```

Platform adapters should emit normalized evidence and use central validators. They should not fork governance logic.

## Step 10: Commit Readiness Rules

Mark ready only when:

- dispatch has been run or the selected agents are otherwise justified
- selected role and skill contracts were read
- required validation passed or skipped with a clear reason
- findings are resolved or explicitly accepted
- generated timestamp-only noise is excluded unless intentional
- no local artifacts are included
- release impact is classified
- enforcement behavior is classified when policies or workflows change

Mark not ready when:

- released baselines are changed without release-manager approval
- candidate source documents produce derived artifacts before review
- policy behavior changes from report-only to blocking without explicit classification
- evidence from branch, pull request, or manual context is treated as official latest state without intent
- validation is missing and no acceptable reason is documented

## Reference Runs

Use these as examples:

```text
docs/operations/reference-runs/2026-07-06-agent-system-dispatch-reference-run.md
docs/operations/reference-runs/2026-07-06-codex-provider-agent-review-pr12.md
docs/operations/reference-runs/2026-07-06-codex-multi-agent-platform-adapter-review.md
```
