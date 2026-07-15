# Agent Usage Tracking

## Purpose

Agent usage tracking records which governance roles and skills were selected or executed during a dispatch or provider-backed review.

Use it to answer:

- which agents are used most often
- which skills are used most often
- how often a provider such as Codex or Mistral was used
- whether `repo-steward` appears consistently
- whether routing is too broad, too narrow, or missing important changes

## Tracking Principle

Track every intentional governance-agent dispatch in a compact machine-readable log.

The log must stay metadata-only. Do not store prompts, secrets, file contents, model responses, or proprietary review text in the JSONL event stream.

Use detailed Markdown documentation only for selected reference runs, release-relevant changes, provider-backed reviews, and periodic snapshots.

## Event Types

There are two important event types:

| Event type | Meaning |
|---|---|
| `dispatch` | The deterministic router selected agents from changed paths. |
| `provider_review` | A provider such as Codex or Mistral actually executed the selected role review. |

Dispatch tells you what should review the change.

Provider review tells you what actually reviewed the change.

Use `provider_review` only when a provider actually executed a role-based review or implementation step. Do not mark every deterministic router run as provider-backed just because the command was run during a Codex or Mistral session.

| Situation | Use |
|---|---|
| You only want to know which roles are responsible. | `dispatch` |
| Codex intentionally performed the selected role review or implementation. | `provider_review` with `provider: codex` |
| Mistral intentionally performed the selected role review or implementation. | `provider_review` with `provider: mistral` |
| CI only evaluates changed paths and selected roles. | `dispatch` |

## Default Log Path

The default JSONL path is:

```text
generated/agent-usage/agent-usage.jsonl
```

This path is generated output. Prefer publishing it as a CI artifact or committing it only for intentional reference runs.

The automatic recording state is stored at:

```text
generated/agent-usage/recording-state.json
```

This state file is generated output too. It records whether future runs should be captured continuously or in a bounded recording window.

## Log A Dispatch Event

```bash
python3 scripts/dispatch_governance_agents.py \
  --log-usage \
  --provider none \
  --platform local \
  --source manual \
  pipeline-baseline/templates/bitbucket/README.md
```

The command still prints the normal dispatch result and appends one JSONL event.

## Record Continuously

To capture all future dispatcher or provider-review runs without remembering `--log-usage` every time:

```bash
python3 scripts/dispatch_governance_agents.py --record-continuous
```

This creates or updates:

```text
generated/agent-usage/recording-state.json
```

After activation, normal dispatcher commands are recorded automatically:

```bash
python3 scripts/dispatch_governance_agents.py --base-ref origin/main
```

Provider-review events can still set provider metadata while continuous recording is active.

Preferred shortcut:

```bash
python3 scripts/dispatch_governance_agents.py \
  --provider-review codex \
  --platform github-actions \
  --source pull-request \
  --base-ref origin/main
```

Check the recording state:

```bash
python3 scripts/dispatch_governance_agents.py --recording-status
```

## Record The Next N Runs

Use a bounded window only when you intentionally want a limited experiment:

```bash
python3 scripts/dispatch_governance_agents.py --record-next 20
```

This creates or updates:

```text
generated/agent-usage/recording-state.json
```

After activation, normal dispatcher commands are recorded automatically until the counter reaches zero.

```bash
python3 scripts/dispatch_governance_agents.py --base-ref origin/main
```

The recording state is not a lock. Running `--record-continuous` switches the state to continuous recording. Running `--record-next 20` again switches it back to a bounded window.

## Log A Codex Provider Review

```bash
python3 scripts/dispatch_governance_agents.py \
  --provider-review codex \
  --platform local \
  --source manual \
  pipeline-baseline/templates/bitbucket/README.md
```

The `--provider-review codex` shortcut records the event as `run_type: provider_review` and `provider: codex`.

Use it only when Codex actually executed the selected role review or implementation, not merely when dispatch selected the roles.

## Log A Mistral Provider Review

```bash
python3 scripts/dispatch_governance_agents.py \
  --provider-review mistral \
  --platform bamboo \
  --source pull-request \
  pipeline-baseline/templates/bamboo/bamboo-specs.yml
```

Use the same model-neutral role and skill contracts that Mistral reads from:

```text
.agents/roles/
.agents/skills/
.agents/routing/governance-agent-routing.yaml
```

## Event Format

Each JSONL line contains one event:

```json
{
  "timestamp": "2026-07-06T17:30:00Z",
  "run_type": "dispatch",
  "provider": "none",
  "platform": "local",
  "source": "manual",
  "changed_paths": [
    "pipeline-baseline/templates/bitbucket/README.md"
  ],
  "selected_agents": [
    "devsecops-baseline",
    "release-manager",
    "repo-steward"
  ],
  "skills": [
    "devsecops-baseline",
    "release-management",
    "repo-steward"
  ],
  "release_impact": "none",
  "required_validations": [
    "git diff --check",
    "python3 -m unittest discover -s tests",
    "python3 scripts/validate_governance_repo.py"
  ],
  "warnings": []
}
```

## Summarize Usage

```bash
python3 scripts/dispatch_governance_agents.py --usage-summary
```

For JSON:

```bash
python3 scripts/dispatch_governance_agents.py --usage-summary --json
```

For a custom log path:

```bash
python3 scripts/dispatch_governance_agents.py \
  --usage-summary \
  --usage-log path/to/agent-usage.jsonl
```

## Generate A Snapshot

Use the snapshot generator when the raw log should be turned into stable review material:

```bash
python3 scripts/generate_agent_usage_snapshot.py
```

Default outputs:

```text
generated/agent-usage/agent-usage-summary.json
docs/operations/agents/agent-usage-snapshot-latest.md
```

The JSON summary is machine-readable. The Markdown snapshot is for human review and architecture/governance discussions.

The snapshot includes:

- total event count
- agent and skill usage
- provider, platform, and run type usage
- frequent change areas
- warnings
- latest runs

The snapshot is still metadata-only. It must not include prompts, secrets, file contents, or provider responses.

Example summary:

```text
Governance Agent Usage Summary

Events: 3

Agent usage:
- repo-steward: 3
- release-manager: 2
- devsecops-baseline: 1

Skill usage:
- repo-steward: 3
- release-management: 2
- devsecops-baseline: 1
```

## How To Interpret Counts

High `repo-steward` usage is expected because it is selected for every meaningful repository change.

High `release-manager` usage can mean:

- many changes touch release-sensitive paths
- pipeline, policy, schema, or baseline work is frequent
- routing may be intentionally conservative

Low usage of a domain agent can mean:

- that domain is stable
- the repository has not exercised that domain yet
- routing may be missing a path

Compare `dispatch` and `provider_review` counts:

- high dispatch with low provider review means roles are selected but not formally executed
- high provider review means the team is using the agent system as an actual review workflow

For the current recorded snapshot, see:

```text
docs/operations/agents/agent-usage-snapshot-latest.md
```

For the first provider-backed Codex reference review, see:

```text
docs/operations/reference-runs/2026-07-06-codex-provider-detailed-evidence-review.md
```

## Retention And Commit Guidance

Keep the JSONL log compact and metadata-only. Commit it when it is intentionally used as audit evidence for governance-agent adoption.

Create human-readable snapshots periodically, for example after:

- a release
- a provider-backed reference run
- 50 recorded events
- a monthly review

For noisy CI environments, prefer uploading the JSONL log as an artifact and committing only aggregate snapshots.
