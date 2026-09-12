# GPT-6 Governance-Agent Evaluation — 12 September 2026

## Decision And Scope

Use `gpt-6-astra` with reasoning effort `high` as the first model upgrade for
the nine Codex role adapters. Role instructions remain unchanged. This is a
bounded pilot decision, supported by working model access and a small review
comparison, rather than proof of generally superior performance.

The maintainer requested this work before continuing with PR #74. The change
record is [GCR-2026-061](../../governance/change-requests/GCR-2026-061-codex-agent-model-upgrade.md).
Reviewed repository and role-contract revision:
`5311182c220548474fcd90b04c38dc46b144937a`.

Official OpenAI guidance identifies `gpt-6-astra` as a Codex model and advises
retaining an existing supported reasoning effort during migration.
[Codex models](https://learn.chatgpt.com/docs/models),
[GPT-6 migration guidance](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-astra).
These sources were checked on 12 September 2026; account availability was
tested separately below.

## Availability

Runtime: Codex CLI `0.153.0`, using the existing ChatGPT login. No new API key,
authentication setup or global user setting was introduced.

| Requested model | Observation |
|---|---|
| `gpt-5-codex` | Exit 1: the service rejects this model when using Codex with a ChatGPT account |
| `gpt-6-astra` | Availability prompt returned `READY`, exit 0; all three review calls succeeded |
| `gpt-5.5` | All three comparison review calls succeeded |

The old adapter configuration therefore cannot supply a live baseline in this
environment. GPT-5.5 is an explicitly identified comparison reference, not the
previously configured runtime. The exact requested IDs are recorded; the CLI
event stream does not establish an immutable backend model snapshot.

## Method

Each model received the same user prompt for each case: the unchanged role
instructions, neutral role contract, skill workflow and selected historical
code/patch excerpts. The prompts explicitly prohibit tools, writes, delegation
and claims of executed tests. Both models used `high`, the same JSON response
schema and Codex invocation options. User configuration was excluded with
`--ignore-user-config`; authentication still used the existing login.

There was one attempt per model and packet, with at most two calls running
concurrently. The fixed input digests and selected line ranges are in the
[manifest](files/2026-09-12-gpt6-agent-evaluation/manifest.json). These are selected
historical changes from merged PRs, not full re-reviews of all files in those PRs.

| Case | Historical commit | PR | Review role |
|---|---|---|---|
| Replay handling | `22f5c836c327fa882115908038981c9adade6dca` | #16 | evidence-and-intake |
| Harmonized requirements candidate | `35de4d47df30a1b7bd0ecc91059f8e670bb93119` | #43 | source-document-intake |
| Reviewed operational publication | `f992b64c60229b688647815f8002550bd74b634b` | #59 | repo-steward |

The [review rubric](files/2026-09-12-gpt6-agent-evaluation/rubric.json) was written
before running the comparison. The coordinating coding agent assessed the
responses against supplied code, used local counterexamples for concrete
behaviors, and distinguished supported observations, false alarms and proposals
that need further context. This assessment is not an independent human review.

## Results

All six review calls returned valid JSON matching the requested schema. None
used tools, wrote files through a model tool or claimed to have run tests.

| Case | GPT-5.5 elapsed | GPT-6 elapsed | GPT-5.5 output tokens | GPT-6 output tokens |
|---|---:|---:|---:|---:|
| Replay | 29.76 s | 41.62 s | 1,354 | 1,023 |
| Candidate | 30.16 s | 40.41 s | 1,354 | 978 |
| Publication | 28.27 s | 57.40 s | 1,262 | 1,277 |
| Sum of individual calls | 88.19 s | 139.43 s | 3,970 | 3,278 |

CLI-reported input totals were 58,100 tokens for GPT-5.5 and 63,251 for GPT-6;
cached input was 4,224 versus 0. Reported reasoning output was 1,548 versus 988.
The table uses the CLI's `output_tokens` field without adding other counters.
Provider/runtime prefixes differ despite identical user packets. Latency
includes CLI startup, service latency and concurrent scheduling. The sums are
not the elapsed time of the whole parallel evaluation. No monetary cost
comparison or subscription-credit estimate is inferred from these counters.
Raw measurements are in [results.json](files/2026-09-12-gpt6-agent-evaluation/results.json).

| Case | Assessed outcome |
|---|---|
| Replay | Both models identify the same-run conflict issue and the overly broad report-reuse condition. GPT-6 combines related observations more concisely and distinguishes missing operational evidence from a demonstrated defect. |
| Candidate | GPT-5.5 raises two false alarms: treating the explicitly review-only model as forbidden runtime derivation, and claiming a Release Manager review omission despite the checklist. GPT-6 raises neither and preserves the human decision boundary. |
| Publication | GPT-6 identifies acceptance of an already staged local artifact under an allowed ledger path; a temporary-repository counterexample confirms that selection behavior. GPT-5.5's stale-PR and out-of-scope generated-output objections describe deliberate reviewed-publication behavior. Both models also propose checks whose necessity depends on context beyond the packet. |

The item-by-item [assessment](files/2026-09-12-gpt6-agent-evaluation/assessment.json)
records the adjudication, including qualifications. Finding counts are not a
quality score: related issues are grouped differently, and some suggestions
are useful without proving a bug.

## Limits And Follow-Up

The sample contains three roles, three selected packets and no repeated trials
or blinded grading. It does not test all nine roles, live custom-agent dispatch,
long tasks, tool execution, prompt injection resistance or production
throughput. The same neutral contracts remain relevant to other providers.
Passing the existing agent harness establishes routing/contract consistency,
not model quality or service availability.

The replay counterexample confirms historical behavior and a misleading
same-context reason; it does not prove that malicious evidence was accepted
operationally. The publication counterexample requires an already staged local
artifact; normal ignore rules can exclude an untracked file. Timestamp-only
selection alone does not establish a defect without knowing publication intent.
These observations warrant separate focused reviews; this model migration
does not modify replay semantics or the publisher and creates no official
consumer findings.

Continue with GPT-6 for the first pilot, retaining the existing reasoning effort
and role responsibilities. Before broader deployment, sample additional
architecture, policy and release work. Assess lower-cost models for routine
roles separately. Do not claim a speed or cost improvement from this run:
GPT-6 took longer here, while producing fewer total output tokens and fewer
unsupported objections in the inspected packets.

## Reproduce A Review

The evidence bundle contains the exact prompts, response schema, unedited
model responses, rubric, measurements, assessment and counterexample results.
Prompts are stored losslessly in JSON `text` fields to preserve the original
whitespace of numbered source excerpts; input digests hash the decoded text.
It contains public repository excerpts and no credentials or private source
workbook. Model responses are experimental output and may contain incorrect
claims; read them with the assessment.

From the repository root, create a fresh output directory outside the tracked
bundle and run a chosen packet, for example:

```bash
mkdir -p /tmp/governance-model-repeat
python3 - <<'PY'
from pathlib import Path
import json
packet = Path("docs/operations/reference-runs/files/2026-09-12-gpt6-agent-evaluation/replay.prompt.json")
Path("/tmp/governance-model-repeat/replay.prompt.txt").write_text(
    json.loads(packet.read_text(encoding="utf-8"))["text"], encoding="utf-8"
)
PY
codex exec --ignore-user-config --ephemeral --skip-git-repo-check \
  --sandbox read-only --model gpt-6-astra \
  -c 'model_reasoning_effort="high"' \
  --cd /tmp/governance-model-repeat --json \
  --output-schema "$PWD/docs/operations/reference-runs/files/2026-09-12-gpt6-agent-evaluation/response.schema.json" \
  --output-last-message /tmp/governance-model-repeat/replay-response.json \
  - < /tmp/governance-model-repeat/replay.prompt.txt \
  > /tmp/governance-model-repeat/replay-events.jsonl
```

Select `gpt-5.5` for the comparison reference. Retain new measurements separately
rather than replacing this dated record. Repeated answers and token usage are
not expected to be byte-identical. These calls are explicitly live and are not
added to `validate_all.sh` or CI.
