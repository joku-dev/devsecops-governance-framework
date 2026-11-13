# Agent Review Tooling Reference

This reference documents the routing, receipts, PR reporting, optional execution
and offline evaluation delivered by PRs #351–#355 (GCR-2026-163–167).
Start with [How To Run A Governance Agent Review](how-to-run-agent-review.md)
for the sequence from implementation to human review. Commands below run from
the repository root with the pinned validation environment activated.

## Choose the operation

| Need | Entry point | Result | Provider call |
|---|---|---|---|
| Select required perspectives | `dispatch_governance_agents.py --base-ref origin/main` | Roles, routing reasons, validations and release classification | No |
| Bind a review to source state | Dispatcher with `--plan-output`, `--results-template`, `--goal` | Private plan and pending results | No |
| Check declared completion | Dispatcher with `--check-review`, `--review-results` | Completeness report | No |
| Export publishable metadata | `record_agent_review.py` | Allowlisted receipt and optional separate usage event | No |
| Render a PR receipt block | `report_agent_review_status.py --receipt` | Markdown to paste into the PR description | No |
| Inspect attached PR metadata | **Agent Review Status** workflow | Job summary and `agent-review-status` artifact | No |
| Inspect prepared role tasks | `run_agent_reviews.py` | Private prompts, schemas, commands and pending results | No |
| Execute separate read-only reviews | Runner with explicit `--execute` | Private responses, traces and completion result | Yes, optional |
| Prepare or score synthetic cases | `evaluate_agent_reviews.py` | Private evaluation packets or structured-label report | No |

Scripts live under `scripts/`. Routing selection, declared execution, completion
and human approval are separate states. Neither a successful CLI exit nor a green
reporting job means that a model review ran or that a human approved the PR.

## Routing and revision binding

The dispatcher adds roles from **all** matching prefixes in
`.agents/routing/governance-agent-routing.yaml`; it does not stop at the first
match. `repo-steward` is required for every nonempty scope. For example,
architecture OPA changes retain Policy-as-Code and Release Manager and add
Architecture Runtime Governance. Intake scripts also add Architecture Runtime
Governance when their names match `scripts/intake_architecture_`.

PR #351 adds explicit coverage for requirements, controls/platform/evidence
models, Viewer projections, result intake/indexes, lifecycle code and models,
Workbench, provider contracts, demo runbooks and operational status pages.
The dispatcher prints the exact matched prefixes. An unclassified functional
path under `.agents/`, `.codex/`, `.github/`, `scripts/`, `model/`, `tests/` or
`apps/` receives a visible Governance Analyst fallback. Review its ownership
before treating selection as sufficient. Other unmatched paths still select
Steward for a nonempty change.

Without `--base-ref`, dispatch covers local edits. With it, dispatch includes
branch changes since the merge base plus staged, unstaged and untracked paths.
Explicit positional paths produce a limited-scope plan, unsuitable for receipt
publication or the optional execution runner. Rename detection routes both names.

A plan binds HEAD, merge base, source bytes/modes, index entries and selected
role/skill/routing/protocol contracts. After a commit, merge, rebase, source edit
or staging change, generate a new plan and perform the affected reviews again.
Never edit a plan's digests to reuse an obsolete review. A target-branch change
can also change required roles or the effective merge base; recheck before delivery.

## Private artifacts and public receipts

Choose a fresh directory outside the checkout for each revision/run. For example:

```bash
umask 077
review_dir=$(mktemp -d "${TMPDIR:-/tmp}/axiom-review.XXXXXX")
```

Use the same `review_dir` throughout one review. Private JSON files are created
with mode `0600`; runner/evaluation run directories use `0700`. Parent folders
are not automatically hardened, so use a private parent as above. Existing
artifacts are not overwritten. Retain them according to the sensitivity of the
review; they can contain source text, user goals and model responses.

| Artifact | Contents | Publication |
|---|---|---|
| `plan.json` | Goal, source binding, scope, required role tasks and contracts | Private |
| `results.json` | Execution identity/kind, outputs, findings and actual validation references | Private |
| Runner role directories | Prompts, raw responses, event streams, stderr and traces | Private |
| Receipt JSON | Commit/merge base, paths, opaque digests, role status/kind, validation status and finding counts | Explicitly exported metadata only |
| Receipt usage JSONL | One metadata snapshot per distinct receipt | Separate from legacy dispatch logs |
| Evaluation packets/answers/report | Synthetic prompts, supplied responses and scores/optional measurement metadata | Private by default |

Receipts omit goals, executor names, model responses, summaries, role outputs,
finding text and log references. They still disclose repository paths and
metadata: inspect the exported file before intentional publication. Digests
provide consistency checks, not authentication of execution or reviewer identity.

The exporter requires a clean committed checkout and a current full-branch plan
with a base commit. Complete the committed-revision review before export:

```bash
python scripts/record_agent_review.py \
  --plan "$review_dir/plan.json" --results "$review_dir/results.json" \
  --output "$review_dir/receipt.json" --usage-log "$review_dir/usage.jsonl"
python scripts/record_agent_review.py --summary --usage-log "$review_dir/usage.jsonl"
python scripts/report_agent_review_status.py --receipt "$review_dir/receipt.json"
```

Incomplete but valid results can be exported with
`eligible_for_human_review: false`; exporting does not finish pending work.
Repeated export of the same plan/results preserves the first receipt timestamp
and does not append another event. Different results create a different receipt
identity and need a new output filename. A `.lock` serializes usage-log writes;
retry after the current exporter finishes. Inspect an abandoned lock before
removing it. Legacy `generated/agent-usage/` logs are not converted or rewritten.
The summary counts selected roles, declared executed roles, completed roles and
declared execution kinds separately; it does not measure tokens or costs.

## PR status and delivery

Paste exactly one rendered block, including both
`<!-- agent-review-receipt:start -->` and
`<!-- agent-review-receipt:end -->`, into the **PR description**. Comments and
private packet paths are not inspected. After a new commit, generate/review/export
a fresh packet and replace the old block. The reporter checks the exact PR head,
merge base, sorted changed paths, required roles and validation command set.

| Reported status | Meaning | Next action |
|---|---|---|
| `missing` | No receipt block in the description | Export and attach the intended receipt |
| `invalid` | Malformed, duplicated, oversized or schema/digest-invalid block | Render from a valid exporter output; replace the complete block |
| `stale` | Commit, scope, role order or validation set differs | Regenerate and review against the current head/target contracts |
| `incomplete` | Metadata matches but readiness is false | Finish required roles/checks or resolve open high/critical findings, then export new results |
| `declared_complete` | Matching metadata declares all required work complete | Hand off for independent human review |

The workflow runs for PR open, synchronize, reopen, description edit and ready
events. Find the result in **Actions → Agent Review Status → job summary** and
the `agent-review-status` JSON/Markdown artifact. It posts no PR comment and
does not modify approvals. This report-only job is not a new required merge gate;
its exit success is not a declaration that metadata is complete.

Only trusted target-branch code/dependencies execute. Proposed contracts are
read as bounded regular-file data: at most 200 relevant files, 64 KiB each.
The PR body is bounded to 1 MiB and the receipt JSON to 64 KiB. Required roles
and validation commands are the union of target and proposed contracts, so a PR
cannot silently remove its own review requirements. An intentional retirement
may require a transitional contract. Reporter absence on the trusted base is an
explicit bootstrap skip; it never executes the proposed reporter instead.

For local inspection, fetch the event's base and head Git objects, then run the
trusted target implementation with a GitHub PR event JSON:

```bash
python scripts/report_agent_review_status.py --event-file "$review_dir/event.json" \
  --output-json "$review_dir/pr-status.json" --output-md "$review_dir/pr-status.md"
```

The event needs `pull_request.base.sha`, `pull_request.head.sha` (full commit
SHAs) and `pull_request.body`. Keep these report paths private too. The local
report command uses ordinary file writes and can replace its own report files.

## Optional provider execution

The runner consumes an already prepared full-branch plan from a **clean,
committed feature branch**. Read selected role/skill contracts and run their
required validators first. Put actual command outcomes and evidence references
in the plan's results template. The runner only imports its `validations` array;
it does not execute checks or reuse role reviews from that file.

```bash
python scripts/dispatch_governance_agents.py --base-ref origin/main \
  --goal "Review the committed feature and its acceptance criteria" \
  --plan-output "$review_dir/plan.json" --results-template "$review_dir/results.json"
# Record actual validation outcomes in results.json before supplying it below.
python scripts/run_agent_reviews.py --plan "$review_dir/plan.json" \
  --output-dir "$review_dir/prepared" --validation-results "$review_dir/results.json"
```

Preparation needs Python 3.11+ (`tomllib`) and valid Codex role adapter files,
but makes no provider call. Inspect `prepared/<role>/prompt.json`,
`response.schema.json` and `command.json`. Prepared reviews remain pending.
The pinned validation environment is the recommended interpreter environment.

The following **optional** command starts live Codex sessions, may consume account
credits and requires an installed/authenticated compatible Codex CLI. Use it only
when live review is authorized; the default preparation command grants no such
authorization. The runner does not install a CLI or obtain credentials.

```bash
python scripts/run_agent_reviews.py --plan "$review_dir/plan.json" \
  --output-dir "$review_dir/executed" --validation-results "$review_dir/results.json" \
  --execute --parallel-specialists 1 --timeout-seconds 180
python scripts/dispatch_governance_agents.py --check-review "$review_dir/plan.json" \
  --review-results "$review_dir/executed/results.json"
```

| Option | Default | Accepted range/meaning |
|---|---|---|
| `--plan` | Required | Current full-branch plan with a base commit |
| `--output-dir` | Required | New directory outside checkout; preparation cannot be resumed in place |
| `--validation-results` | Omitted | Import recorded validations; omission leaves them pending |
| `--execute` | Off | Explicit live execution; refused for any nonempty `CI` environment value |
| `--parallel-specialists` | `1` | `1`–`3`; read-only specialists only |
| `--timeout-seconds` | `180` | `1`–`600` per provider invocation, not a whole-run deadline |

Each role gets its own ephemeral session with read-only sandbox, no approval
escalation, ignored user configuration and schema-constrained JSON output.
All specialists must finish successfully before the final Steward runs; the
Steward receives their exact results and lists the reviewed role IDs. A failed,
timed-out or malformed specialist response leaves Steward skipped. Successful
provider execution can still produce an incomplete packet because validations
are pending or high/critical findings remain open.

The source state is checked around execution. Concurrent edits abort the run
and are never reverted; do not share a live review checkout with writers.
Read-only sandbox access is not per-file read isolation. Scope is a review
instruction, not a guarantee that other readable files are inaccessible.
No retries, model fallback or permission escalation occur automatically.
On timeout the local process group is terminated; remote cancellation is not
independently confirmed. Provider responses are bounded to 1 MiB and parsed
event streams to 10 MiB.

`execution.json` records mode, attempted/invoked provider state, contract/plan
binding and per-role traces. Role directories add `response.json`, `events.jsonl`,
`stderr.log` and `trace.json`; Steward also has `execution-prompt.json`.
Traces separate requested model/adapter digest from runtime-observed model and
usage. Unsupported/absent event fields remain unknown. Actual process/session
traces improve traceability but do not supply human approval. Export the
resulting `executed/results.json` through the receipt exporter if publication is
intended. Never paste raw execution artifacts into the PR.

## Offline evaluation inputs and interpretation

The runner above reviews Git changes. The evaluator below prepares and grades
ten **synthetic** cases; it does not invoke that runner or call a provider.
Use a separate private directory:

```bash
umask 077
evaluation_dir=$(mktemp -d "${TMPDIR:-/tmp}/axiom-evaluation.XXXXXX")
python scripts/evaluate_agent_reviews.py --prepare "$evaluation_dir/packets"
```

`evaluation-manifest.json` contains `evaluation_digest`, `packet_set_digest` and
per-case role/skill/prompt digests. Each case has `<case-id>.prompt.json` and
`<case-id>.schema.json`. Gold expectations stay out of provider packets; the
dataset in `.agents/evaluations/review-quality-v1.json` retains them for grading.
Any separately authorized model evaluation must use only the supplied packets
and record its own execution; there is no integrated live evaluation CLI.

One answer bundle per candidate/run has this shape. Digest placeholders must be
replaced with values from the manifest. This single benign-case response is an
illustrative **synthetic fixture**, not a measured model result or full benchmark:

```json
{
  "evaluation_digest": "<evaluation_digest from manifest>",
  "packet_set_digest": "<packet_set_digest from manifest>",
  "records": [{
    "case_id": "candidate-registration-only",
    "response": {
      "release_impact": "none",
      "enforcement_behavior": "unchanged",
      "evidence_context": "none",
      "findings": []
    }
  }]
}
```

For each finding, the case schema requires `code`, `severity`, nonempty `reason`
and nonempty `evidence_refs`. Codes must be in the packet's taxonomy, severity is
`low`, `medium`, `high` or `critical`, and evidence references are keys of that
case's supplied `inputs`. A finding code may occur only once per response.
Every response must include the three classifications and `findings`.

```bash
python scripts/evaluate_agent_reviews.py --responses "$evaluation_dir/answers.json" \
  --output "$evaluation_dir/report.json"
```

`--dataset PATH` optionally selects another supported synthetic dataset for both
preparation and grading. Use the same checkout, dataset, roles and skills for
both steps; do not patch bundle digests after a revision change. Missing/invalid
answers stay visible as `missing`/`invalid`. Unknown or duplicate case IDs and
different dataset/prompt revisions reject the bundle. Reports omit raw reasons
and answers. They remain private and are not attached by the PR reporter.

Optional measurement fields belong on an answer record alongside `case_id` and
`response`: `trace_file` (prefer an absolute private path) and `trace_sha256`
(SHA-256 of its exact bytes). Both are required together. Relative paths resolve
from the grader's working directory, not from the answer bundle's directory.
The JSON trace, at most 1 MiB, has the following fields:

| Field | Requirement |
|---|---|
| `case_id`, `evaluation_digest`, `packet_set_digest` | Match this answer and manifest exactly |
| `run_id` | Distinct per measured case; 1–64 letters, digits or hyphens |
| `elapsed_seconds` | Actual finite, nonnegative number |
| `usage` | Null/omitted if unknown; otherwise nonnegative integer `input_tokens`, `cached_input_tokens`, `output_tokens` |
| `requested_model`, `observed_model` | Separate identifiers or null/omitted when unknown |

Preserve original runtime evidence separately. A supplied trace hash establishes
byte consistency, not authenticity; reports label it
`supplied_runtime_trace_not_authenticated`. Do not turn example values or unit-test
fixtures into measurements. The runner's role trace format is not directly the
evaluation case trace format.

| Report field | Interpretation |
|---|---|
| `complete_coverage`, `valid_cases` | Every case needs one schema-valid answer; no quality threshold is implied |
| `true_positive`, `false_positive`, `false_negative` | Taxonomy hits, unsupported codes for that case, missed expected codes |
| `precision`, `recall` | TP/(TP+FP), TP/(TP+FN); zero denominator yields null |
| `severity_correct` | Count of matching severities among taxonomy hits |
| `classification_accuracy` | Correct release/enforcement/context labels divided by three times all case count |
| `measurement_case_count` | Valid cases with accepted supplied traces |
| `sum_case_elapsed_seconds` | Sum only with measurement coverage of every case; not batch wall-clock time |
| `usage` | Totals only with full trace and token coverage; cached input stays separate |

Exit 0 from grading means the report was produced, even for missing answers or
poor scores. Compare complete identical case sets and conditions, repeat runs
and assess reasons/evidence manually. There is no built-in pass threshold,
monetary cost calculation, automatic model selection or general superiority claim.

## Exit codes and troubleshooting

| Command | Exit 0 | Exit 1 | Exit 2 |
|---|---|---|---|
| Dispatcher completion check | Declared complete | Incomplete, failed/skipped required work or open high/critical findings | Invalid/stale packet or scope mismatch |
| Runner | Preparation succeeded, or executed packet declared complete | Executed packet remains incomplete | Invalid state/input, bounds or setup error |
| Receipt exporter | Valid metadata exported, possibly incomplete | — | Invalid/stale/private-path/log conflict |
| PR reporter | Report rendered, including missing/invalid/stale/incomplete metadata | — | Invocation, Git objects or inspection inputs unusable |
| Offline evaluator | Packets/report written, regardless of score | — | Invalid invocation, dataset/bundle/trace or output conflict |

| Symptom | Recovery |
|---|---|
| Clean-checkout/full-branch error | Commit intended files, inspect untracked files, prepare against the real target without positional paths |
| Stale plan after staging/commit/rebase | Validate the changed revision and generate a new plan/results pair |
| Existing output path | Use a new file/run directory; preserve the old evidence |
| Live execution refused in CI | Use preparation only in CI; perform authorized live review locally |
| Codex start/timeout/response failure | Inspect private stderr/events/trace; verify CLI/account compatibility; fix the cause and explicitly start a new run |
| Runner exit 1 despite successful sessions | Check recorded validations, required role outputs and open findings with the completion checker |
| PR reports stale after retargeting | Recalculate full scope and target/proposed requirements, then review/export the new revision |
| CODEOWNER approval disappears after a push/retarget | Obtain approval for the current head under repository rules; a receipt cannot restore it |
| Evaluation rejects digests | Return to the preparation checkout or prepare/review a fresh packet set; never relabel old answers |
| Null model/time/token fields | Preserve unknowns; supply actual runtime evidence where available |

## Implementation and regression map

| Responsibility | Production files | Deterministic regressions |
|---|---|---|
| Routing | `scripts/lib/agent_routing.py`, neutral routing/role/skill contracts | `test_agent_routing.py`, contract/scenario tests |
| Plan and completeness | `scripts/lib/agent_review.py`, dispatcher, review protocol | `test_review_execution.py` |
| Receipts/private writes/usage | `scripts/lib/agent_receipts.py`, exporter, receipt schema | `test_agent_receipts.py` |
| Trusted-base PR report | `scripts/lib/agent_review_status.py`, reporter, separate workflow | `test_agent_review_status.py` |
| Bounded execution/Codex projection | `scripts/lib/agent_execution.py`, `agent_codex.py`, runner, execution contract | `test_agent_execution.py` (provider mocked) |
| Synthetic quality scoring | `scripts/lib/agent_evaluation.py`, evaluator, evaluation dataset | `test_agent_evaluation.py` (fixture answers/traces) |

Tests are under `tests/agent_harness/`. Run them through the
[harness instructions](agent-harness-usage.md); they execute no live models.
Full repository validation and a strict MkDocs build remain the delivery checks.
Routing tests prove deterministic selection, mocked execution tests prove local
control flow, and fixture grading tests prove arithmetic/schema handling. None
of them establishes live-provider quality, independent review or approval.
