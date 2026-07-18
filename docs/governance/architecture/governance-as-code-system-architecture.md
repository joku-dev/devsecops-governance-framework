# Governance-as-Code System Architecture

## Document Status

| Attribute | Value |
|---|---|
| Document type | Current-state, as-built system architecture |
| Status | Current explanatory architecture |
| Effective date | 2026-07-17 |
| Owner | Governance Platform Maintainers |
| Change request | `GCR-2026-035` |
| Governance effect | None; documentation-only |
| Released baseline effect | None |
| Source Document Intake | Not required; no new governance source |

## Purpose

This document describes how the implemented Governance-as-Code system works as
one technical system. It connects the foundation, structured governance models,
released baselines, downstream workflows, evidence intake, Trust evaluation,
append-only history, portfolio projections, graph, and viewer.

This is an explanatory architecture document. It does not create policy,
approve a control, change an enforcement mode, or modify a released baseline.
Where it conflicts with an approved policy, directive, source document,
machine-readable model, schema, or released package, those authoritative
artifacts take precedence.

The document complements rather than replaces:

- `docs/foundation/04_REFERENCE_ARCHITECTURE.md` for the target layer model
- `docs/governance/architecture/ado-devsecops-integrated-governance-model.md`
  for the organisation and decision operating model
- `docs/governance/architecture/runtime-governance-addendum.md` for runtime
  architecture governance concepts
- `docs/operations/status/current-governance-platform-state.md` for current
  operational status

## Scope

In scope:

- the central `devsecops-governance-framework` repository
- multiple application and service repositories consuming released baselines
- DevSecOps and architecture runtime evaluation
- collector, evidence, Trust, replay, ledger, and failed-attempt handling
- result indexes, portfolio reporting, governance graph, and static viewer
- governance change control, releases, validation, and agent review routing

Out of scope:

- deployment architecture of consumer applications
- a long-running governance API, database, or event broker
- Kubernetes as the current runtime platform
- automatic approval by an AI agent
- enterprise-wide approval workflows outside this repository

## Architecture Drivers

The implementation follows these repository guardrails:

1. Governance intent, executable controls, runtime evidence, and intelligence
   projections are separate concerns.
2. Human accountability remains explicit; automation produces evidence and
   recommendations, not unreviewed governance authority.
3. Released baselines are immutable snapshots and consumer repositories pin a
   release tag or commit SHA rather than depending on mutable `main`.
4. Evidence is evaluated independently from the governance outcome it reports.
5. Historical result snapshots are append-only; conflicting writes are visible
   and quarantined.
   A legacy identity that lacks only `artifact_digest` can be matched to an
   otherwise identical enriched identity without rewriting history; two
   different present artifact digests remain a conflict.
6. Generated reports, indexes, graph data, and the viewer are projections. They
   do not become new sources of truth.
7. Report-only and blocking behavior are explicit configuration choices.
8. Platform-specific adapters surround a model- and schema-based governance
   core.

## System Context

```text
 Governance authorities and source documents
                     |
                     v
 +-----------------------------------------------------------+
 | Central Governance-as-Code Repository                     |
 | intent -> models -> policies -> releases -> result ledger |
 |                    -> indexes -> graph/viewer              |
 +-----------------------------------------------------------+
       | released workflow + baseline       ^ result dispatch/artifact
       v                                    |
 +------------------+  +------------------+  +------------------+
 | Consumer repo A  |  | Consumer repo B  |  | Consumer repo N  |
 | application CI   |  | application CI   |  | application CI   |
 +------------------+  +------------------+  +------------------+
       |                       |                       |
       +--------- GitHub Actions / CI runtime --------+
                               |
                               v
             Owners, operators, reviewers, auditors
                    via reports, Pages and viewer
```

The central repository is the versioned governance control plane. Consumer
repositories retain their application source and execute pinned workflow
contracts in their own CI context. Selected downstream artifacts are then
collected into the central repository for portfolio visibility and audit.

## Four-Layer Architecture

| Layer | Responsibility | Main implementation |
|---|---|---|
| Governance Intent | Explain authority, direction, roles, lifecycle, and source lineage | `docs/foundation/`, `docs/governance/`, `model/documents/`, `governance/` |
| Governance Model | Express controls, mappings, evidence types, architecture guardrails, schemas, and policies | `model/`, `architecture/`, `schemas/`, `policies/opa/` |
| Governance Runtime | Validate the central repo, publish baselines, execute consumer checks, collect results, and evaluate Trust | `.github/workflows/`, `scripts/`, `releases/` |
| Governance Intelligence | Project history into indexes, reports, portfolio status, graph, and viewer | `status/`, `generated/reports/`, `generated/graph/`, `generated/viewer/` |

Dependencies flow down through controlled contracts. Runtime and intelligence
feed evidence back upward for review, but they do not silently rewrite intent
or released models.

## Runtime and Deployment View

```text
 +---------------- Git repository ----------------+
 | docs | model | policies | schemas | releases   |
 | status ledger | generated read models          |
 +------------------------+------------------------+
                          |
                          v
 +---------------- GitHub Actions ----------------+
 | governance CI | release workflows | intake     |
 | portfolio refresh | docs publishing | retry    |
 +------------+----------------------+------------+
              |                      |
              v                      v
     Python generators/         OPA policy engine
     validators/collectors      and Rego tests
              |
              v
 +------------------------------------------------+
 | Static outputs: MkDocs site, HTML viewer, JSON |
 | graph, Markdown/JSON reports, workflow artifacts|
 +------------------------------------------------+
```

The current runtime is event-driven and short-lived. GitHub Actions supplies
execution, scheduling, permissions, concurrency control, and artifact access.
Python scripts perform deterministic collection, normalization, generation,
and validation. OPA evaluates Rego policy. Git stores approved configuration
and append-only evidence history. There is currently no continuously running
application service, Kubernetes workload, external database, or message queue.

## Logical Components

| Component | Responsibility | Key locations |
|---|---|---|
| Source and change intake | Classify new artifacts, register candidate sources, record impact and review decisions | `model/documents/`, `docs/governance/change-requests/`, `docs/operations/processes/` |
| DevSecOps control baseline | Define controls, platform mappings, traceability, evidence requirements, and OPA behavior | `model/controls/`, `model/platform/`, `model/traceability/`, `policies/opa/` |
| Architecture runtime governance | Define levels, markers, review gates, exceptions, release candidates, and runtime policy | `architecture/`, architecture rules under `policies/opa/`, `schemas/architecture-*.schema.json` |
| Release manager | Freeze reviewed models, schemas, policies, workflow wrappers, metadata, and checksums | `releases/`, `docs/releases/`, versioned workflows in `.github/workflows/` |
| Consumer workflow adapter | Load a pinned baseline, collect repository context, evaluate it, and publish artifacts | reusable and versioned workflows under `.github/workflows/` |
| Evidence collectors | Acquire a named artifact, bind subjects and digests, normalize a contract-specific result | `scripts/intake_*`, `scripts/collect_*`, `model/evidence/evidence-collector-contract.yaml` |
| Evidence Trust verifier | Evaluate subject integrity, source metadata, custody, freshness, and replay without changing the underlying outcome | `scripts/lib/evidence_trust.py`, `model/evidence/`, Trust schemas |
| Append-only result ledger | Accept new snapshots, treat identical intake as idempotent, quarantine conflicting identity reuse | `scripts/lib/result_ledger.py`, `status/results/`, `status/architecture-results/`, `status/typed-evidence-results/`, `status/intake-conflicts/` |
| Collection attempt, intake telemetry, and health | Record failed or partial collection for retry, record every intake execution, and project report-only operational indicators | `scripts/record_collection_attempt.py`, `scripts/record_intake_event.py`, `scripts/generate_intake_health.py`, `status/collection-attempts/`, `status/intake-events/`, `status/intake-health.json` |
| Status and portfolio projections | Select context-aware latest results, summarize adoption, and validate multi-consumer isolation | result index generators, `scripts/generate_multi_consumer_readiness.py`, `status/*-index.json`, `governance/portfolio-adoption-reporting.yaml` |
| Governance Intelligence Graph | Join stable identifiers into a deterministic read-only relationship graph | `scripts/generate_governance_graph.py`, `schemas/governance-graph.schema.json`, `generated/graph/` |
| Viewer and documentation | Present status, Trust, Intake Health, attempts, portfolio information, lineage, and graph navigation | `scripts/generate_status_viewer.py`, `generated/viewer/`, `mkdocs.yml` |
| Agent review system | Route bounded governance reviews using model-neutral roles and skills; record explicit agent involvement separately | `.agents/`, `.codex/agents/`, `tests/agent_harness/`, `status/evidence-agent-provenance/` |

## Sources of Truth and Read Models

| Information | Authoritative location | Derived projection |
|---|---|---|
| Governance authority and source status | approved documents and `model/documents/source-document-register.yaml` | source lineage and intake reports |
| Control and platform model | `model/controls/`, `model/platform/`, `model/traceability/` | coverage, automation, and traceability reports |
| Architecture governance model | `architecture/` | runtime governance reports and result indexes |
| Executable policy | `policies/opa/` | evaluation output and test results |
| Released baseline | versioned package under `releases/` plus checksums | release documentation |
| Downstream result history | append-only JSON snapshots under `status/` | latest indexes, portfolio report, graph, viewer |
| Intake conflict history | `status/intake-conflicts/` | viewer conflict summaries |
| Failed collection history | `status/collection-attempts/` | derived `open`, `resolved`, or `permanent` lifecycle |
| Intake operation history | `status/intake-events/` | Intake Health success-rate and latency projection |
| Consumer registry and isolated result paths | `status/application-repository-integrations.yaml`, result history under `status/` | portfolio and Multi-Consumer Readiness reports |
| Agent involvement | explicit records under `status/evidence-agent-provenance/` | provenance index and viewer |

The generated files are reproducible read models. A reader must follow their
source references when making an audit or governance decision.

## End-to-End Flow

### 1. Governance Change and Baseline Publication

```text
classify artifact
      -> register/review source when required
      -> analyse impacted requirements and controls
      -> update models, schemas, policy and tests
      -> validate repository
      -> create explicit release candidate/release
      -> publish immutable package and checksums
```

A documentation-only explanation can stop after classification, GCR, review,
and validation. A behavior or contract change must update the corresponding
models, tests, documentation, and release decision.

### 2. Consumer Evaluation

1. A consumer repository calls a versioned reusable workflow pinned to a
   release tag or full commit SHA.
2. The workflow collects repository and pipeline context.
3. OPA and supporting scripts evaluate the applicable DevSecOps or architecture
   baseline.
4. The workflow publishes machine-readable evidence and a human-readable
   report as CI artifacts.
5. Report-only mode records findings while allowing the workflow to complete;
   blocking mode fails according to the explicitly selected contract.
6. An accepted mainline result can dispatch central intake when the required
   cross-repository token is configured.

### 3. Central Intake and Trust Evaluation

```text
consumer run
   -> repository_dispatch or manual intake
   -> read GitHub run metadata
   -> download named artifact
   -> validate and normalize payload
   -> calculate subject/artifact SHA-256 digests
   -> evaluate Trust, freshness and replay
   -> append snapshot or quarantine conflict
   -> regenerate indexes, graph and viewer
   -> validate, rebase and commit projection changes
```

The intake workflows use an event-specific concurrency group containing the
repository and run identity. This serializes duplicate work for the same run
without globally blocking unrelated consumers. Before committing, they rebase
and regenerate projections so concurrent results can converge on current
`main`.

### 4. Failed Collection and Retry

If artifact retrieval or normalization fails, the intake workflow records an
append-only collection-attempt entry. That record is operational evidence, not
a successful result. An operator can explicitly start the retry workflow for a
fully retryable entry. The viewer correlates a later successful snapshot with
the original attempt and derives its lifecycle; it never rewrites the attempt.

### 5. Intelligence Projection

Index generators retain history and select the appropriate latest view per
repository and runtime context. Portfolio reporting uses registered consumers
and accepted results. The graph joins existing identifiers into navigable
relationships. The static viewer renders those projections without a write-back
path.

## Evidence and Trust Architecture

Governance outcome and Evidence Trust answer different questions:

- the outcome says whether the evaluated subject passed, failed, or produced
  report-only findings
- the Trust record says how strongly the collected bytes and their provenance
  have been verified

The current Trust ladder is:

| Level | Meaning |
|---|---|
| `unverified` | Evidence was captured, but integrity has not been established. |
| `integrity_verified` | A subject identity exists and the collected bytes match a verified digest. |
| `provenance_verified` | Integrity plus the required source, run, commit, artifact, freshness, replay, and custody checks are verified. |
| `attested` | A trusted issuer has cryptographically attested the subject under an accepted policy. |

The current collector path can derive `integrity_verified`. It does not claim
trusted producer identity merely because an artifact was downloadable. The
higher levels remain contract boundaries for future hardening.

Freshness and replay are currently report-only context checks. A stale result
or incompatible replay context remains visible but does not silently change a
governance PASS to FAIL and does not independently lower byte-integrity Trust.
The replay identity binds repository, commit, workflow, run, run attempt,
artifact, and subject digest.

Agent provenance is also independent. It records an explicitly asserted
`selected`, `executed`, `reviewed`, or `approved` relationship to a known
subject digest. It is not a cryptographic attestation and cannot raise the
Evidence Trust level by itself.

## Result Ledger and Consistency Model

The central evidence store follows four rules:

1. A new result identity creates a new immutable snapshot.
2. An identical retry is an idempotent no-op.
3. A changed payload targeting an existing identity never replaces the
   original; a conflict record is created for review.
4. Latest-state, portfolio, graph, and viewer data are recomputed projections
   over the retained history.

Git provides versioning and optimistic concurrency rather than database
transactions. Intake workflows mitigate concurrent updates with scoped
concurrency groups, pull/rebase/regenerate retry loops, deterministic
generators, and schema validation. This is suitable for the current event rate,
but it is a deliberate scalability boundary.

## Runtime Context and Latest-State Semantics

The system distinguishes mainline, pull-request, branch, and manual or
diagnostic runs. Historical records from every relevant context may remain
visible, while portfolio and management views must use accepted mainline,
release, or explicitly accepted manual evidence. A newer pull-request run must
not silently replace the accepted mainline state.

## Multi-Consumer Model

Multiple consumer repositories are first-class. Each consumer has a normalized
`owner/name` identity, its own result history, baseline target, adoption state,
owner, and architecture scope. Repository-specific paths prevent cross-consumer
result collision. Portfolio projection reads the integration registry and the
central indexes; it does not grant onboarding or waive missing evidence.

Adding a consumer therefore does not require copying central policies. It
requires registration, a pinned workflow integration, required permissions,
an initial accepted run, central intake, and ownership of follow-up findings.

## Security and Trust Boundaries

| Boundary | Main control |
|---|---|
| Governance maintainer to released consumer contract | reviewed release, version pin, checksums, branch protection |
| Consumer repository to central intake | explicit dispatch, named artifact, repository/run identity, scoped token |
| Downloaded bytes to accepted subject | schema validation, SHA-256 binding, Trust checks, replay evaluation |
| Automated writer to Git history | least-required workflow permissions, scoped concurrency, validation, append-only ledger |
| Generated view to governance decision | read-only projection, source links, human accountability |
| AI agent to evidence | explicit provenance record; no inferred authority and no automatic Trust elevation |

`GH_RESULT_INTAKE_TOKEN` is required when the default token cannot read a
different repository's run artifacts. The token should have only the repository
and Actions access needed for that operation. Workflow write permissions in the
central repository are limited to the jobs that must persist results.

## Quality Attributes

| Attribute | Current architectural response |
|---|---|
| Auditability | Git history, source lineage, GCRs, immutable releases, append-only result and conflict records |
| Reproducibility | pinned validation dependencies and OPA version, deterministic generators, schemas, tests, checksums |
| Integrity | subject and artifact digests, central verification, append-only ledger |
| Portability | model/schema/policy core plus platform adapters; GitHub Actions is the current reference implementation |
| Availability | CI-triggered operation; static documentation and viewer remain readable without a live backend |
| Observability | workflow logs, collection attempts, conflicts, result indexes, portfolio report, graph, viewer |
| Scalability | repository-partitioned history and scoped concurrency; bounded by Git-based storage and regeneration cost |
| Maintainability | separation of authoritative models, implementation scripts, generated outputs, and versioned releases |

## Enforcement Model

Report-only is the current safe default for the demo and hardening features.
Findings remain visible in artifacts, indexes, portfolio views, and the viewer.
Blocking requires an explicit workflow or policy decision and must include the
corresponding documentation, tests, migration impact, and release decision.

Evidence freshness, replay findings, intake conflicts, collection failures,
agent provenance, graph relationships, and portfolio projections do not by
themselves change an underlying governance outcome.

Blocking Readiness is likewise a read-only decision projection. It combines
released baseline pinning, mainline stability, Trust, replay, Typed Evidence,
Architecture, intake health, conflict, waiver, rollback, and accountable
approval signals. Its schema fixes `enforcement_change_authorized` to `false`;
consumer workflow and branch-protection activation remains a separate reviewed
change with release and migration analysis.

## Current Deployment Decision and Kubernetes

The current architecture intentionally runs on GitHub Actions with static
outputs. This keeps the operational footprint small, aligns execution with code
changes and downstream runs, and preserves Git-native auditability.

Kubernetes is deferred. It becomes relevant if the system needs sustained high
event volume, low-latency APIs, worker autoscaling, independent availability,
or a queue/database that can no longer be handled safely by Git-based intake.
Moving execution to Kubernetes must preserve the existing schemas, immutable
release references, evidence identities, Trust semantics, append-only history,
and human decision boundaries. Kubernetes would change the deployment model,
not the governance contracts.

## Known Limitations and Risks

| Limitation | Consequence or mitigation |
|---|---|
| Git is the result ledger and coordination store | Good auditability at current scale; unsuitable for very high write rates without an ingestion service or database. |
| Viewer is statically generated | Simple and portable, but not a live query or write-back application. |
| GitHub Actions is the complete reference adapter | Other CI platforms require adapters that preserve the same contracts. |
| Current Trust generally stops at `integrity_verified` | Producer identity and authoritative provenance are not yet fully verified. |
| Only a public-key demo issuer is registered | Signature and subject binding are proven report-only; production issuer lifecycle and operational `attested` promotion remain open. |
| Freshness and replay are report-only | Operators must review findings; they are not automatic enforcement gates. |
| Collection lifecycle and health are projected from immutable events | There is no mutable operational job state or automatic retry scheduler. Health indicators are report-only and thresholds are not yet defined. |
| Vulnerability scan is the current typed collector pilot | Additional evidence types still need contract-conformant adapters and tests. |
| Some governance approvals remain organisational | Repository automation cannot substitute for the accountable governance forum. |

## Evolution Priorities

The next architecture increments should preserve current contracts and can be
introduced independently:

1. observe Intake Health over a representative period, then define operational
   objectives and alerting
2. add collector adapters for further evidence types
3. move the signed-attestation pilot toward an approved issuer and key lifecycle
4. formalize remaining approval and exception boundaries
5. introduce a service, queue, database, or Kubernetes deployment only when
   measured scale or availability requirements justify it

## Change Impact Rules

Use this document as the orientation map, then update the authoritative area:

| Intended change | Required review focus |
|---|---|
| Governance intent or source | source intake, lineage, requirements, human approval |
| Control, marker, or review gate | traceability, OPA, tests, evidence and release impact |
| Evidence or Trust contract | backward compatibility, schema version, collector, indexes and viewer |
| Enforcement behavior | report-only/blocking semantics, consumer migration, release decision |
| Result intake or ledger | idempotency, conflict retention, concurrency, latest-state semantics |
| Graph, report, or viewer | deterministic projection and unchanged source-of-truth boundaries |
| Blocking readiness or activation | technical criteria, accountable approval, waiver tests, rollback, consumer migration and release decision |
| Runtime platform | security, availability, state migration, contract preservation and operating ownership |

## Validation

The architecture description is guarded by the repository validation suite and
documentation build:

```bash
python3 scripts/validate_runtime_governance.py
python3 scripts/validate_governance_repo.py
python3 -m unittest discover -s tests
mkdocs build --strict
```

The repository-wide reproducible entry point is:

```bash
./scripts/validate_all.sh
```

## Related Documents

- `docs/foundation/01_VISION.md`
- `docs/foundation/02_CONSTITUTION.md`
- `docs/foundation/03_ARCHITECTURE_PRINCIPLES.md`
- `docs/foundation/04_REFERENCE_ARCHITECTURE.md`
- `docs/foundation/05_CURRENT_DIRECTION.md`
- `docs/governance/architecture/ado-devsecops-integrated-governance-model.md`
- `docs/governance/architecture/runtime-governance-addendum.md`
- `docs/operations/evidence/evidence-trust-model.md`
- `docs/operations/evidence/evidence-collector-contract.md`
- `docs/operations/evidence/governance-result-intake-and-viewer-usage.md`
- `docs/operations/guides/evidence-and-governance-hardening-guide.md`
- `docs/operations/status/governance-intelligence-graph-viewer.md`
- `docs/operations/status/portfolio-adoption-reporting.md`
- `docs/operations/status/current-governance-platform-state.md`
