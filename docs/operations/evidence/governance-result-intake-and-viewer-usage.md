# Governance Result Intake And Viewer Usage

## Purpose

This guide explains two operational capabilities of this repository:

1. how to create normalized governance result snapshots for downstream repositories
2. how the status viewer distinguishes `main` results from branch or pull-request results

The current intake stores governance outcomes and additive provenance,
integrity, and custody metadata. The report-only model for evaluating that
metadata is defined in `docs/operations/evidence/evidence-trust-model.md`.
Trust verification does not change latest-result selection. The viewer projects
Trust as a separate report-only signal.

Typed evidence such as vulnerability scans uses a separate snapshot store and
index. This prevents an evidence-quality signal from being mistaken for a
governance outcome.

## Part 1: Result Intake

### Goal

The goal of result intake is to convert a successful downstream governance run into a standardized JSON snapshot under:

- `status/results/`

This keeps downstream evidence history:

- Git-tracked
- comparable across repositories
- reusable for the central viewer

New automated GitHub Actions intake snapshots contain an optional `trust`
block. It records content hashes, run attempt, source binding, and initial
custody through the versioned Evidence Collector Contract defined in
`docs/operations/evidence/evidence-collector-contract.md`. The collector record
is stored as `trust.capture`; DevSecOps and architecture intake use the same
profile with explicit domain context. The central verifier recomputes the
captured-subject hashes and may
assign `integrity_verified`; unresolved checks remain `not_evaluated`.
It also compares the workflow update time with the intake verification time
using the provisional 24-hour governance-result Freshness policy. An expired
or future-dated result creates a report-only failed Trust check; it does not
change the governance outcome or latest-result selection. Historical
snapshots are not rewritten and project as `unverified`.

### Append-Only Result Ledger

All central intake paths use append-only snapshot writes:

- a new snapshot path is created once
- re-intake with the same run context and subject digests is an idempotent no-op
- different evidence for an existing snapshot path never overwrites the original
- the conflicting identity and payload digests are stored under `status/intake-conflicts/`
- conflict handling remains report-only and does not replace `latest_result`

The central verifier also evaluates `replay_key_unique`. The replay identity
binds repository, commit, workflow, run, run attempt, artifact, and subject
digests. Digest reuse within the same repository, commit, and artifact context
is compatible; reuse across an incompatible decision context is a report-only
finding. Replay findings do not alter the independently derived integrity
level or governance outcome.

The governance, architecture, and typed-evidence workflows use concurrency
groups scoped to intake type, consumer repository, and downstream run ID.
Duplicate delivery of the same run is therefore serialized, while distinct
runs from the same or different consumers can remain queued and execute. This
avoids GitHub replacing an older pending multi-consumer intake event with a
newer one. The recomputable portfolio projection retains its own static group.

All commit steps reconcile with the current `main` branch and retry failed
pushes. Concurrent intake runs therefore converge the shared graph, viewer,
indexes, and portfolio projection without discarding distinct events.

Failed DevSecOps, architecture, and typed-evidence collection attempts are
written append-only under `status/collection-attempts/` before the workflow is
reported as failed. These records are report-only and never replace successful
evidence or official latest state. If authoritative GitHub run metadata cannot
be retrieved, the attempt is still recorded with the requested repository and
run identity plus a `source_metadata_unavailable` error so that authentication
and availability failures do not become invisible.

## Typed Evidence Trust Intake

For a GitHub Actions run containing an `application-evidence` artifact, use:

```bash
python3 scripts/intake_evidence_trust_github_actions_run.py \
  --repository-id joku-dev/governance-framework-demo-consumer \
  --run-id 29432884108
python3 scripts/generate_typed_evidence_results_index.py
python3 scripts/generate_status_viewer.py
```

The intake requires a vulnerability Trust record plus the exact scan report
and evaluated application artifact. It binds the repository, commit, run, and
artifact to authoritative GitHub Actions metadata, recomputes both subject
digests, and applies the 24-hour vulnerability Freshness policy. Producer-side
Trust is therefore not accepted without central re-verification.

Typed snapshots and their aggregate index are stored under:

```text
status/typed-evidence-results/
status/typed-evidence-results-index.json
```

The latest typed result follows the same operational principle as governance
results: a `main` branch `push` is preferred, so a later manual diagnostic run
does not replace it. This selection is confined to the typed-evidence index;
it does not change governance `latest_result`.

## Intake Script

Use:

```bash
python3 scripts/intake_governance_result.py
```

For GitHub Actions runs that already uploaded the standard governance artifacts, use:

```bash
python3 scripts/intake_github_actions_run.py \
  --repository-id joku-dev/ha-CPsWMS \
  --run-id 28314109954
```

This script fetches the downstream run metadata, jobs, artifact list, `governance-control-evaluation` artifact, governance run input, and control evaluation summary from GitHub Actions.

## What The Script Produces

The script writes one normalized file to:

```text
status/results/<owner>__<repo>/<timestamp>-run-<run-id>.json
```

For guidance on verifying that intake artifacts are real and not placeholder evidence, see:

- `docs/operations/processes/spot-check-governance-intake.md`

## Example

```bash
python3 scripts/intake_governance_result.py \
  --repository-id joku-dev/ha-CPsWMS \
  --baseline-level L1 \
  --governance-baseline-ref l1-baseline-v1.1.3 \
  --pipeline-name "DevSecOps Baseline" \
  --pipeline-run-id 28302814664 \
  --pipeline-url https://github.com/joku-dev/ha-CPsWMS/actions/runs/28302814664 \
  --pipeline-event push \
  --pipeline-status success \
  --branch main \
  --branch-protected true \
  --commit-id a7c0f5beef39405887a0caaac23fa785147151b9 \
  --baseline-gate-status success \
  --ci-status success \
  --governance-control-evaluation-status success \
  --governance-control-report true \
  --governance-run-input true \
  --static-analysis-summary true \
  --traceability-mapping true \
  --operations-evidence true \
  --overall-status pass \
  --control-evaluation-summary-file generated/control-evaluation-report.json \
  --notes "Full structured L1 coverage retained on main with run-context-aware evaluation."
```

## Recommended Intake Rule

Use the script for:

- successful `main` runs
- important PR or branch runs that show meaningful governance improvement

Do not use it for:

- broken experiments
- partial local tests without a real pipeline run
- duplicate snapshots without new information

## Pull Request Versus Mainline Behavior

For the full timing diagram from application repository evidence production to central intake and viewer update, see:

```text
docs/operations/processes/application-repo-governance-timing.md
```

For `joku-dev/ha-CPsWMS`, governance checks and central result intake are intentionally separated.

| Event in app repository | Governance checks run in app repo? | Governance repo checked out as tooling? | Artifacts created in app run? | Central governance intake triggered? | Viewer latest mainline updated? |
|---|---:|---:|---:|---:|---:|
| `pull_request` | yes | yes | yes | no | no |
| `workflow_dispatch` | yes | yes | yes | no by default | no |
| `push` to `main` | yes | yes | yes | yes | yes |

Meaning:

- Pull requests validate the proposed application change and publish evidence in the application repository's GitHub Actions run.
- Pull requests do not automatically update this governance repository's status indexes or viewer.
- A merge or direct push to `main` is the official operational signal.
- Mainline push runs trigger `repository_dispatch` intake into this governance repository when `GH_RESULT_INTAKE_TOKEN` is configured.
- The viewer's latest status is therefore the official mainline state, not the latest PR state.

This distinction prevents temporary pull-request findings, experimental branch checks, or diagnostic reruns from replacing the official mainline status.

Current `ha-CPsWMS` behavior:

| Workflow | Runs on PR | Runs on push to `main` | Triggers central intake |
|---|---:|---:|---:|
| `Architecture Runtime Governance` | yes | yes | only on `push` to `main` |
| `DevSecOps Baseline` | yes | yes | only on `push` to `main` |
| `DevSecOps Governance` | yes | yes | no central intake in the current workflow |

If PR-level central visibility is needed later, add explicit PR result intake and keep it marked as `branch` or `pull_request` history so it does not replace `latest_result`.

## Part 2: Viewer Usage

## Mainline Versus Branch Results

The viewer now distinguishes between:

- `mainline`
- `branch`
- `manual`

Meaning:

- `mainline` means the recorded run belongs to a `push` event on the repository's `main` branch
- `branch` means the recorded run belongs to a feature branch or PR flow
- `manual` means the recorded run was started through `workflow_dispatch`

This matters because:

- `mainline` is the official operational state
- `branch` shows improvement work in progress
- `manual` shows diagnostic checks without replacing the official push-based mainline state

Manual diagnostic runs should normally provide:

- `run_context.event: workflow_dispatch`
- `run_context.purpose: diagnostic`
- `run_context.release_context: false`

This allows release-specific controls to be shown as `not_applicable` instead of false failures.

## Latest Result Rule

The repository results index intentionally keeps:

- `latest_result` = latest `main` `push` result if one exists

This prevents a feature-branch result from replacing the official mainline state.

It also prevents a manual diagnostic run from replacing the official push-based operational state.

At the same time:

- branch, PR, and manual runs still remain visible in `history`

## How To Refresh The Viewer

After adding or updating result snapshots, run:

```bash
python3 scripts/generate_repository_results_index.py
python3 scripts/generate_status_viewer.py
```

## Recommended Workflow

Use this order:

1. record the downstream result with `scripts/intake_governance_result.py`
2. regenerate `status/repository-results-index.json`
3. regenerate `generated/viewer/status-viewer.html`
4. validate the governance repository
5. commit the updated result and viewer state

## Automated Intake Workflow

The repository includes:

- `.github/workflows/intake-governance-result.yml`

It can be run manually with:

- `repository_id`
- `run_id`
- optional `governance_baseline_ref`
- optional `baseline_level`

The workflow then:

1. downloads the downstream governance-control-evaluation artifact
2. writes a normalized result under `status/results/`
3. regenerates `status/repository-results-index.json`
4. regenerates `generated/viewer/status-viewer.html`
5. validates the repository
6. commits and pushes the updated central status

For cross-repository artifact access, configure a repository secret:

- `GH_RESULT_INTAKE_TOKEN`

The token should have read access to the downstream repository's GitHub Actions artifacts.

The workflow uses this governance repository's `GITHUB_TOKEN` to commit the updated normalized status files back to the governance repository.

The same workflow also accepts `repository_dispatch` events of type:

- `governance-result-ready`

Expected `client_payload` fields:

```json
{
  "repository_id": "joku-dev/ha-CPsWMS",
  "run_id": "28314109954",
  "governance_baseline_ref": "l1-baseline-v1.1.3",
  "baseline_level": "L1"
}
```

## Automated Typed-Evidence Workflow

The separate `.github/workflows/intake-evidence-trust.yml` workflow accepts:

- manual inputs `repository_id`, `run_id`, and optional `artifact_name`
- `repository_dispatch` events of type `typed-evidence-trust-ready`

Expected dispatch payload:

```json
{
  "repository_id": "joku-dev/governance-framework-demo-consumer",
  "run_id": "29432884108",
  "artifact_name": "application-evidence"
}
```

For cross-repository artifact access, configure `GH_RESULT_INTAKE_TOKEN` with
Actions read access to the producer repository. The workflow centrally
verifies the evidence, regenerates only the typed index and shared viewer,
validates the repository, and commits the new typed snapshot. Producer-side
automatic dispatch is optional; manual workflow dispatch remains sufficient
for the demo.

## Practical Benefit

With this model, the viewer can now show:

- official operational `main` status
- branch-level improvement runs
- coverage trends over time
- baseline version changes across runs
- evidence Trust independently from governance `pass`, `fail`, or `findings`
- typed vulnerability Trust, scanner observations, Freshness, integrity, and subject binding without creating a governance outcome
- append-only intake conflicts and replay findings without replacing official mainline state
