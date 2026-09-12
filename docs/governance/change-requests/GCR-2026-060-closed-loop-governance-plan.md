# GCR-2026-060: Plan the closed-loop governance pilot

## Request And Artifact Classification

The maintainer accepted the recommendations from the review of the local
Closed-Loop Governance Decision & Remediation Runtime workpackage and asked
for concrete next steps. Record a phased implementation plan with a bounded
repository-protection pilot and explicit acceptance criteria.

| Field | Value |
|---|---|
| Artifact name | Closed-Loop Governance implementation plan |
| Artifact type | Explanatory planning documentation and change record |
| Target path | `docs/operations/planning/closed-loop-governance-implementation-plan.md` |
| Owner | Repository maintainer; technical review through existing governance roles |
| Reviewed repository | `5311182c220548474fcd90b04c38dc46b144937a`, 12 September 2026 |
| Source Document Intake required? | No for this planning document; it creates no authoritative source, authority assignment or SLA |
| Evidence contract impact | None in this change; additive contracts proposed for CLG-01 |
| Runtime governance impact | None in this change; report-only pilot proposed |
| Release impact | None for the plan; assess implementation at pilot acceptance |
| Validation required | Pinned full repository validation and strict MkDocs build |

Classification follows the
[new artifact intake process](../../operations/processes/new-artifact-intake-process.md).
The original local draft remains an input, identified by filename and digest in
the plan. Its proposed roles, SLA examples and embedded execution instructions
do not establish approved governance behavior.

## Change And Impact

Add the [implementation plan](../../operations/planning/closed-loop-governance-implementation-plan.md)
and link it from the AI index, official entrypoints and MkDocs planning navigation.
The first milestone uses GRS-002, synthetic fixtures and then a separately
identified live observation. It requires explicit contracts for authority
proof, deterministic event processing, evidence coverage, closure and reopening.

| Area | Impact of this PR |
|---|---|
| Policy, directive, source register and lineage | No normative derivation or source-register update |
| Models, architecture, schemas and OPA | No executable changes; references to existing contracts and gaps |
| Intake, status and viewer | No operational writes or generated state changes |
| Baselines and downstream repositories | No baseline update or consumer migration |
| Enforcement and approvals | Existing rules apply; this plan grants no live decision authority |
| Documentation | One plan, this GCR and three navigation entries |

## Decisions And Review Focus

- Keep the core independent of LLMs; defer broad adapters, graph and portfolio
  features until the complete pilot is demonstrated.
- Reuse existing risk-based waiver authorities. Decision and closure authority
  require their own confirmed mapping; do not infer them from waiver roles.
- Prepare contracts and tests with synthetic identities. Confirm the actual
  role bindings, approval-proof channel and evidence acceptance profile before
  live decision intake. Route any proposed new normative requirements through
  source intake and governance review before deriving executable behavior.
- Treat accepted observations, decisions and events as immutable records with
  generated state. Define duplicate handling, ordering and stale-write rejection.
- Bind closure to fresh, applicable, trusted evidence and authorized approval.
  Keep partial exceptions, remediation and accepted risk distinct.

## Validation And Completion

Run `./scripts/bootstrap_validation_env.sh`, `./scripts/validate_all.sh`, a strict
MkDocs build and `git diff --check`. Exclude validation-only generated metadata
changes after inspecting them. The PR records the results. No runtime
implementation, source replacement or release is part of this planning change.
