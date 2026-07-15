# Agent Usage Snapshot

Date: 2026-07-06

## Purpose

This snapshot records the current agent usage tracking state after introducing detailed architecture evidence support, report-only visibility, and routing improvements.

## Current Usage Summary

```text
Events: 7

Agent usage:
- repo-steward: 7
- release-manager: 3
- governance-analyst: 2
- evidence-and-intake: 1

Provider usage:
- none: 7

Platform usage:
- local: 7

Run type usage:
- dispatch: 7
```

The remaining automatic recording window is:

```text
Remaining runs: 13
```

## Interpretation

The current usage is local deterministic dispatch only. No Codex or Mistral provider-backed review has been recorded yet.

`repo-steward` appears in every run as expected.

`release-manager` usage increased after schema, collector, validation, and routing changes were classified as release-candidate relevant.

`governance-analyst` usage increased after the agent system and repository validation paths were routed explicitly.

`evidence-and-intake` usage appeared when detailed architecture evidence collection and schema handling changed.

## Routing Improvements Already Made

The first recorded runs exposed useful routing gaps:

| Gap | Fix |
|---|---|
| New untracked files were not included in local dispatch. | Dispatcher now includes `git ls-files --others --exclude-standard`. |
| `.agents/...` paths were normalized incorrectly. | Path normalization now preserves dot-directories. |
| Architecture evidence templates and collector/report paths routed too weakly. | Added architecture evidence routing rules. |
| Agent system routing and harness changes routed too weakly. | Added `.agents/` and `tests/agent_harness/` routing rules. |
| Repo validator changes routed too weakly. | Added `scripts/validate_governance_repo.py` routing rule. |

## Current Caveat

The usage log currently records dispatch decisions, not actual provider execution.

Provider-backed runs should use:

```bash
python3 scripts/dispatch_governance_agents.py \
  --run-type provider_review \
  --provider codex \
  --platform github-actions \
  --source pull-request \
  --base-ref origin/main
```

For company target usage, replace provider and platform with:

```text
provider: mistral
platform: bamboo
```

## Next Observations To Watch

- whether `architecture-runtime-governance` appears for architecture model and evidence changes
- whether `evidence-and-intake` appears for schemas, collector output, intake, and viewer changes
- whether `release-manager` appears for candidate-impacting schema, workflow, policy, and validator changes
- whether provider-backed events begin to appear once Codex or Mistral executes the selected roles
