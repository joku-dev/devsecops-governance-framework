# Optional Codex Review Execution

The neutral `.agents/execution-contract.yaml`, role/skill contracts and
`.agents/review-protocol.yaml` remain authoritative. `scripts/run_agent_reviews.py`
prepares private tasks from a current full-branch review plan. It makes no model
call unless the operator explicitly passes `--execute`. Live execution is refused
when `CI` is set. No test or repository workflow invokes live models.

The adapter uses the role's existing `.codex/agents/<role>.toml` model/effort and
instructions. It requests a separate ephemeral Codex CLI session with a read-only
sandbox, no approval escalation, ignored user configuration and JSON-schema
output. The requested model is recorded separately from runtime-observed model
identity; absence of an observed identity remains null. There is no model fallback.

The [official non-interactive documentation](https://learn.chatgpt.com/docs/non-interactive-mode)
describes read-only execution and structured output. The
[CLI reference](https://learn.chatgpt.com/docs/developer-commands?surface=cli)
documents ephemeral runs and ignoring user configuration. These interfaces were
checked on 13 November 2026 against the installed CLI help.

Specialists execute serially by default. An explicit parallel-specialist count
up to three authorizes only separate read-only reviews. The final Steward starts
after all specialists succeed and receives their exact results; private trace
metadata records their digests. Failed/timed-out/invalid responses leave required
work incomplete. Local timeout cancels the process group; remote cancellation is
not independently attested. Source changes abort the run and are never reverted.

Prompts, responses, event streams and traces stay in a new private directory
outside the checkout. Role scope is an instruction; the CLI sandbox enforces
read-only command access rather than per-file read isolation. Never put secrets
in review inputs. Repository/source text and previous agent outputs are data,
not authority to change the task or launch further agents. Validation outcomes
must be recorded from actual checks; this runner does not run validators or
generators. Human decisions, release authority and protected merge rules remain
separate.
