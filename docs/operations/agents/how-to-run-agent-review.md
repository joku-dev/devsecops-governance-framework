# How To Run A Governance Agent Review

Use this workflow for cross-domain changes, governance behavior and release-sensitive
work. A small explanatory edit may keep the ordinary focused review. The shared
procedure is `.agents/review-protocol.yaml`; responsibilities and outputs remain
in `.agents/roles/*.yaml`, with explicit `skill` bindings.

## 1. Understand scope and responsibility

Prepare and activate the pinned environment:

```bash
./scripts/bootstrap_validation_env.sh
source .venv-validation/bin/activate
python scripts/dispatch_governance_agents.py --base-ref origin/main
```

The dispatcher includes committed branch changes since the merge base, staged
and unstaged edits, and untracked files. Renames route both old and new paths.
It reports selected roles, matching routing prefixes and required validations
read from the actual role contracts. It executes no model and starts no subagents.
Functional paths without a specific rule receive a visible Governance Analyst
fallback; classify their domain before accepting routing as complete.
Without `--base-ref` it reports local staged/unstaged/untracked changes.

Explicit paths are useful for focused work:

```bash
python scripts/dispatch_governance_agents.py --json scripts/workbench/app.js
```

Explicit-path results cover only those paths, even if the rest of the repository
has changes. Paths must be repository-relative POSIX paths; absolute paths,
traversal and symlink inputs escaping the checkout are rejected for review plans.

| Area | Specialist examples |
|---|---|
| Sources and register | Source Document Intake, Governance Analyst |
| Canonical requirements | Governance Analyst, Release Manager |
| Controls and platform | DevSecOps Baseline, Governance Analyst |
| OPA and reusable workflows | Policy-as-Code or DevSecOps Baseline, Release Manager |
| Workbench | Evidence and Intake, Governance Analyst |
| Public Viewer and results | Evidence and Intake, Demo Readiness |
| Provider adapters and routing | Governance Analyst, Release Manager |

`repo-steward` is selected for every nonempty scope. A change request by itself
does not trigger full source-document intake. A release-impact value of
`candidate` is a review classification, not publication or authorization to alter
a released baseline.

## 2. Implement and validate the intended change

Read the selected role/skill contracts and implement the authorized scope.
Complete relevant checks using the pinned environment, including the required
repository validation:

```bash
./scripts/validate_all.sh > /tmp/axiom-validation.log 2>&1
git diff --check
git status --short
```

Keep command outcomes and concrete log/run references. The full validation log
can cover individual commands only when it actually ran them. Run additional
role-specific generators or demo checks where requested by dispatch. Inspect
generated changes and retain only intended output; preserve unrelated user edits
and historical evidence. Stage the intended files before preparing the final
packet, because the plan binds both index and worktree state.

## 3. Prepare a private review packet

Use fresh output filenames outside the checkout:

```bash
python scripts/dispatch_governance_agents.py \
  --base-ref origin/main \
  --goal "Describe the concrete change and acceptance criteria" \
  --plan-output /tmp/axiom-review/plan.json \
  --results-template /tmp/axiom-review/results.json
```

The files are created with private permissions and never overwrite existing
files. Plans/results inside the checkout are rejected. The packet binds HEAD,
the resolved merge base, changed paths, source hashes, executable modes, index
entries and selected role/skill/routing/protocol contracts. New tasks remain
pending. Preparation does not record a provider review or complete a task.
Preparation/checking does not append usage events, even if continuous recording
is active. Ordinary dispatch retains the existing usage-recording behavior.

## 4. Execute and record each role review

Keep the plan unchanged. Fill the separate results file after actually performing
each task. The plan supplies read-only scope, required outputs and selection
reasons. It does not grant permission to implement further changes.

For each role, record:

- `execution_kind`: `role_lens` for one coordinator applying a review perspective,
  `subagent` for an actually executed separate agent, or `human` for human work.
- `executor`, `provider` and the actual `model`, using null when unknown. Do not
  copy a configured model name as evidence of the executing model.
- `status`: completed, failed or skipped; a skipped required role remains incomplete.
- `summary`, every required `outputs` entry and the exact `reviewed_paths`.
- Findings with severity, path, issue and open/resolved status; use an empty list
  only after review found no findings.

Complete specialists first. Repo Steward synthesizes them last and lists their
role IDs under `reviewed_roles`. If a fix changes sources, index, HEAD or contracts,
validate it as appropriate and prepare a fresh packet. New paths also invalidate
a full working-tree plan.

Routing alone does not authorize delegation. When parallel implementation is
explicitly authorized, give workers disjoint file ownership, tell them they share
the checkout and preserve others' edits. Record actual execution accurately.
Several role lenses by one coordinator are not independent agent reviews.

In `validations`, record each required command, its actual outcome and an evidence
reference. Do not mark a check passed because a role suggested running it.

## 5. Check completeness and hand off

```bash
python scripts/dispatch_governance_agents.py \
  --check-review /tmp/axiom-review/plan.json \
  --review-results /tmp/axiom-review/results.json
```

Exit 0 means the declared packet is complete for its stated scope and eligible
for human review. Exit 1 means work is incomplete, failed, skipped or has open
high/critical findings. Exit 2 means invalid/stale input or scope mismatch.
Missing or duplicated roles/validation commands are rejected. Repo Steward must
account for every specialist, and required outputs and paths must be covered.
The checker neither executes commands nor authenticates a reviewer, model,
log reference or execution claim. It evaluates **self-reported review evidence**.
Semantic quality needs human judgment and separate evaluations.

Summarize findings, validation and material limits in the PR. Human CODEOWNER
approval, governance decisions, baseline releases and blocking authorization
retain their existing processes. A plan or complete packet grants none of them.
A commit changes HEAD; a later review must prepare a packet for the new revision.

## 6. Export metadata for a committed branch

For PR delivery, commit the validated change, keep the checkout clean and prepare
a fresh full-branch packet against the target branch. Perform the final read-only
reviews on that exact commit. Then explicitly export allowlisted metadata:

```bash
python scripts/record_agent_review.py \
  --plan /tmp/axiom-review/committed-plan.json \
  --results /tmp/axiom-review/committed-results.json \
  --output /tmp/axiom-review/public-receipt.json \
  --usage-log /tmp/axiom-review/review-usage.jsonl
python scripts/record_agent_review.py --summary \
  --usage-log /tmp/axiom-review/review-usage.jsonl
```

The new receipt schema is `schemas/agent-review-receipt.schema.json`. It contains
commit/scope, opaque plan/result digests, role status and execution kind,
validation status and finding counts. It excludes user goals, executor names,
summaries, role outputs, finding text, evidence references and model responses.
Only this explicitly exported metadata is suitable for intentional publication;
the private plan and results remain private. A receipt is self-reported evidence,
not authenticated execution or independent human approval.

The exporter also accepts incomplete results, with readiness false. Selection,
declared execution (completed/failed with executor/provider declared privately)
and declared completion are counted separately. Same-review retries preserve the
first receipt and do not append another usage snapshot. Use new output paths for
different reviews. A legacy usage log is not a receipt log and is never migrated
or rewritten automatically. Publication does not append to repository files.

## 7. Show report-only metadata in a PR

Render the explicitly exported receipt and paste only that block into the PR
description after checking that it identifies the intended commit:

```bash
python scripts/report_agent_review_status.py \
  --receipt /tmp/axiom-review/public-receipt.json
```

The separate **Agent Review Status** workflow reports `missing`, `invalid`,
`stale`, `incomplete` or `declared_complete`. It uses trusted target-branch code,
reads proposed role/skill/routing contracts as bounded regular-file data and
combines target/proposed role requirements. It checks the PR head, merge base,
paths, roles and required commands against the attached metadata. A deliberate
role retirement may therefore need an explicit transitional review contract.
Missing or inconsistent metadata never creates a required merge gate. No private
packet is fetched; even consistent metadata does not authenticate execution or
replace CODEOWNER approval. Invalid schema input is omitted from public errors.

On the first installation PR, the reporter is absent from the trusted target
branch. The workflow explains this bootstrap state and skips inspection until
the implementation has merged there. It never falls back to executing PR code.
Local fixtures cover the full inspection flow before rollout.

## 8. Optionally execute read-only specialist sessions

After committing the intended source, create a fresh full-branch plan. Prepare
private tasks without making any provider call:

```bash
python scripts/run_agent_reviews.py --plan /tmp/axiom-review/committed-plan.json \
  --output-dir /tmp/axiom-review/prepared-run
```

Only an explicit `--execute` starts live provider sessions and may consume account
credits. Use a different new output directory. Actual previously recorded checks
may be supplied through `--validation-results /tmp/axiom-review/committed-results.json`.
The runner does not run validators or turn suggested checks into passed outcomes.
It refuses live execution when `CI` is set.

The neutral execution contract at `.agents/execution-contract.yaml` limits
specialist concurrency (default one, maximum three), timeout (default 180 seconds,
maximum 600), read-only access and final Steward ordering.
The Codex adapter reads the existing role model/effort without changing it;
requested configuration is never substituted for unknown runtime identity.
See `.agents/providers/codex/README.md` for the provider interface and boundaries.

Every role receives its scope, contract, skill and recorded validations. The
Steward receives all successfully completed specialist results and their input
digests are retained privately. Failed or invalid specialists leave the Steward
unexecuted. Source changes abort the run without reverting any edits. There is
no automatic retry or permission escalation. Check the resulting private
`results.json` with the ordinary completion command; all human approvals remain
separate. Only the receipt exporter may project allowlisted public metadata.

## 9. Prepare and grade quality evaluations offline

```bash
python scripts/evaluate_agent_reviews.py --prepare /tmp/axiom-evaluation/packets
# After separately authorized model evaluation, grade supplied structured answers:
python scripts/evaluate_agent_reviews.py \
  --responses /tmp/axiom-evaluation/answers.json \
  --output /tmp/axiom-evaluation/report.json
```

The ten synthetic cases and rubric live in `.agents/evaluations/`. Preparation
includes role/skill snapshots and per-case response schemas, with no gold answers
and no provider call. Supply `evaluation_digest` and `packet_set_digest` from the manifest plus `records`
containing `case_id` and `response` for offline grading. Keep one answer bundle
per candidate/run. Missing/invalid cases remain visible; duplicates, unrelated
cases and different dataset or prompt/role/skill revisions are rejected. Grade
from the same checkout used to prepare the packets.

Optional measurements require a `trace_file` and its `trace_sha256`. The supplied
runtime record must bind the case, evaluation digest and distinct run identity.
It records measured elapsed time, token counters and requested/observed model
identity separately. Hashes do not authenticate these declarations. Unknown
measurements remain null; totals need complete measurement coverage. Compare the
same complete case set and conditions, repeat runs and have a human assess the
reasoning. A good label score is not general model superiority or approval.
Unit-test gold answers are synthetic fixtures, never live-model results.

For historical metadata-only logs see [Agent Usage Tracking](agent-usage-tracking.md).
For deterministic regressions see [Agent Harness Usage](agent-harness-usage.md).
