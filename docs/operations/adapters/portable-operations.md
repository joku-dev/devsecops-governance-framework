# Portable operations candidate

The [portability runtime](portable-governance-runtime.md) and [evidence intake](../evidence/portable-evidence-intake.md) now have an additive operations boundary in `scripts/lib/portable_intake/operations.py`. See [GCR-2026-175](../../governance/change-requests/GCR-2026-175-portable-operations-boundaries.md). Existing accepted ledger/publisher paths do not import this successor.

## Separate responsibilities

| Component | Responsibility | Deliberate boundary |
| --- | --- | --- |
| `SCM` | Resolve the configured repository and branch; list/reconcile/create native PRs/MRs | Exact repository IDs, source/target/head binding; no merge or reopen operation |
| `Writer` | Bounded authenticated JSON/form POST | Separate credential from `Reader`; an uncertain mutation is reconciled before retry |
| `dispatch_ci` | Explicit GitHub workflow/GitLab pipeline/Bamboo plan request | No discovery, evaluator, shadow collector or default trigger; no approval assertion |
| `GitWorkspace` | Fresh private checkout, restricted candidate files, reproducible local commit, non-forced proposal-branch push | Does not change the active Workbench checkout or an accepted baseline |
| `run_link` | Native provider/instance run links, including GitLab subgroups and opaque Bamboo keys | A link is navigation, not evidence provenance |
| `require_compatible` | Compare the new VM's installed/candidate executable dependency closure | Drift requires an application update; no implicit code activation during data intake |

SCM identity is checked through the configured read-only API before proposal mutation. Native IDs remain strings. Source and target must belong to the configured central repository. Branch-name equality on a fork is insufficient. Existing requests are listed across all states: a matching closed or merged request remains terminal, and a different head or ambiguous match requires reconciliation. A lost creation response can be recovered by looking up the frozen source branch; it does not cause another create call. Returned URLs must use the configured HTTPS SCM instance without credentials/query/fragment.

The caller owns batch serialization, routing/operating acceptance, shadow duration and credential admission. These adapters do not establish that authority. The later VM coordinator must preserve the one-open-proposal limit, at most 25 frozen results, original legacy batch identities, explicit routing ownership and the 24-hour/new-run shadow requirements. This increment does not claim that coordinator is integrated.

## Git and recovery

`GitWorkspace.prepare(base)` requires a full immutable SHA and creates a fresh private scratch directory. Commit requires that prepared workspace and an explicit timezone-aware frozen timestamp. Author/committer identity and time are fixed; a recovered workspace can reproduce the same commit. Only 1–25 explicitly named files under `status/portable/v2/candidates/<repository-key>/<execution-key>.json` are allowed, with a 4 MiB per-file limit. Existing paths, symlink parents and changed staged bytes are rejected. No other source or baseline path is staged.

Push is limited to `automation/portable-consumer/<24 hexadecimal characters>`, without force. A parent/default branch is never a valid publication target for this method. API proposal reconciliation remains separate from Git push, so a batch coordinator must check terminal requests before publishing/recovering a branch.

Credentials are supplied through the child environment and a credential helper, not argv, URLs or tracked files. HTTP redirects, interactive askpass, ambient Git configuration, hooks and trace output are disabled for this isolated operation. These controls protect the private staging process; they do not authenticate a human approval or a governance role.

The new drift closure extends the unchanged legacy set with `config/`, `infra/`, all `.github/` implementation files and relevant root Git/Python metadata. In particular, changing the portability compatibility manifest or a setup action cannot pass as a harmless result-only update. Existing legacy profiles keep their previous implementation until a separately controlled migration.

## Provider contracts and acceptance

Existing CodeQL, Dependency Review and repository Self-Security PR checks also run against stacked feature branches. Their previous `main` base filter left dependent increments without those checks. The same check implementations and permissions are retained; no additional required check or consumer blocking mode is activated.

GitHub uses native pull requests and workflow dispatch. GitLab uses project-scoped merge requests and pipeline creation; subgroup paths are retained for display while native project IDs drive requests. Bitbucket Data Center uses its PR API and paginated state retrieval. Bamboo plan dispatch requires an explicitly configured `native_branch` matching the requested ref, sends a form-encoded POST, and refuses variable overrides. A plan key is not treated as an arbitrary job key or a proof of which commit eventually ran.

Official request contracts checked for this candidate: [GitHub PRs](https://docs.github.com/en/rest/pulls/pulls), [workflow dispatch](https://docs.github.com/en/rest/actions/workflows), [GitLab merge requests](https://docs.gitlab.com/api/merge_requests/), [pipelines](https://docs.gitlab.com/api/pipelines/), [Bitbucket Data Center PRs](https://developer.atlassian.com/server/bitbucket/rest/v1003/api-group-pull-requests/) and [Bamboo's form-encoded plan queue contract](https://docs.atlassian.com/atlassian-bamboo/REST/8.2.3/). The Bamboo reference is an API contract reference, not a claim to support or recommend that historical product version.

Current evidence consists of provider-shaped synthetic request/response fixtures and real local Git commits, including lost responses, terminal proposals, fork/head conflicts, unsafe URLs/branches, credential boundaries, drift and deterministic recovery. Actual instance URLs, product versions/editions, native import, permissions and target behavior remain open. No real repository proposal, workflow trigger, VM update, new publisher or blocking check is activated by this increment.
