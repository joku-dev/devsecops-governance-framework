# Demo: ha-CPsWMS Architecture Runtime Governance

## Purpose

This document is the architecture-specific companion to the full end-to-end demo runbook:

```text
docs/demos/demo-end-to-end-governance.md
```

Use this document when the demo audience wants to go deeper into the architecture runtime governance part only.

## Current Demo State

| Field | Value |
|---|---|
| Application repository | `joku-dev/ha-CPsWMS` |
| Application branch | `main` |
| Architecture governance baseline | `architecture-baseline-l1-v0.1.0` |
| Solution baseline | `ha-CPsWMS-demo-baseline` |
| Latest mainline run | `28592256765` |
| Latest mainline commit | `4a86f0c5b3d7aa1883533fa787530a1f5ff886e7` |
| Generated | `2026-07-02T13:05:12Z` |
| Current result | `PASS`, `4/4 gates`, `0 findings` |

Interpretation:

- The architecture checks are demo-ready on mainline.
- The checks are currently used report-only for the demo.
- A `PASS` means the current evidence satisfies the released L1 architecture governance checks. It is not a formal production approval.

## Demo Flow

1. Show the source architecture framework document.
2. Show the machine-readable architecture addendum.
3. Show the released architecture baseline.
4. Show the app repository evidence.
5. Show the GitHub Actions run.
6. Show the viewer result.
7. Explain what would create findings.

## Source-To-Runtime Mapping

Start with:

```text
docs/governance/source-documents/ARCH-SDD-SRC-001.public.md
```

Then show the derived runtime governance artifacts:

```text
architecture/quality-markers.yaml
architecture/guardrails.yaml
architecture/review-gates.yaml
architecture/arch-l1.yaml
architecture/arch-l2.yaml
architecture/arch-l3.yaml
architecture/arch-gov.yaml
policies/opa/architecture_readiness.rego
policies/opa/architecture_integration_readiness.rego
policies/opa/architecture_operation_readiness.rego
policies/opa/architecture_release_readiness.rego
schemas/architecture-release-candidate.schema.json
```

Why:

- The original framework remains the human governance reference.
- The YAML, schemas and OPA policies are the machine-readable runtime addendum.
- The addendum allows CI/CD to evaluate architecture evidence repeatably.

## Released Baseline

Open:

```text
docs/releases/architecture-baseline-l1-v0.1.0.md
docs/releases/architecture-baseline-l1-v0.1.0-release-statement.md
releases/architecture/l1/v0.1.0/baseline-package.md
releases/architecture/l1/v0.1.0/release-metadata.json
```

Explain:

- `architecture-baseline-l1-v0.1.0` is the released governance baseline.
- `ha-CPsWMS-demo-baseline` is the solution/product baseline supplied by the application evidence.
- The app workflow should report the governance baseline as `architecture-baseline-l1-v0.1.0` and keep the solution baseline inside the collected release input.

## Application Evidence

In the application repository:

```bash
cd /workspace/ha-CPsWMS
find .governance/architecture -maxdepth 2 -type f | sort
```

Expected evidence areas:

```text
.governance/architecture/solution-baseline.json
.governance/architecture/release-compatibility-declaration.json
.governance/architecture/security-evidence.json
.governance/architecture/resilience-evidence.json
.governance/architecture/operation-evidence.json
.governance/architecture/feedback-evidence.json
```

Why:

- The app repository owns product evidence.
- The governance repository owns reusable policy logic.
- Findings should be resolved by improving evidence or approved exceptions, not by changing policy logic for one application.

### Evidence File Pattern

The architecture evidence files share a common structure defined by:

```text
schemas/app-architecture-evidence.schema.json
```

Common fields:

| Field | Meaning in the demo |
|---|---|
| `evidence_type` | Which evidence category the file represents. |
| `status` | `approved` evidence is accepted by the current demo collector and policies. |
| `owner` | Role accountable for the evidence. |
| `approved_by` | Review body or reviewer that approved the evidence. |
| `approval_date` | Date of evidence approval. |
| `baseline_version` | Used where the evidence declares a product or solution baseline. |
| `summary` | Human-readable claim being made. |
| `evidence_refs` | Repository files that substantiate the claim. |
| `known_limitations` | Limitations that remain visible for governance review. |
| `follow_up_actions` | Follow-up work for later hardening. |

The important point for the demo is that these files are review records with traceable references. They do not hide limitations; they make them explicit.

### Current Architecture Evidence Files

| File | Evidence type | What it proves in the demo |
|---|---|---|
| `.governance/architecture/solution-baseline.json` | `solution_baseline` | The current repo revision, topology, schemas and deployment assumptions belong to `ha-CPsWMS-demo-baseline`. |
| `.governance/architecture/release-compatibility-declaration.json` | `release_compatibility_declaration` | The release candidate is declared compatible with the demo solution baseline. |
| `.governance/architecture/security-evidence.json` | `security_evidence` | Security assumptions and CI/deployment evidence exist for the demo scope. |
| `.governance/architecture/resilience-evidence.json` | `resilience_evidence` | Restart, recovery and resilience evidence exists at demo level. |
| `.governance/architecture/operation-evidence.json` | `operation_evidence` | Deployment and runtime operation evidence exists. |
| `.governance/architecture/feedback-evidence.json` | `feedback_evidence` | Benchmark or feedback evidence exists for improvement loops. |

### Example: Solution Baseline Evidence

This file is the app-owned baseline claim:

```json
{
  "evidence_type": "solution_baseline",
  "status": "approved",
  "owner": "Solution Architect",
  "baseline_version": "ha-CPsWMS-demo-baseline",
  "approved_by": "Architecture Demo Review",
  "approval_date": "2026-07-02",
  "summary": "Demo solution baseline for the Home Assistant to Neo4j semantic world model capability.",
  "evidence_refs": [
    "docs/ARCHITECTURE.md",
    "docs/DEPLOYMENT.md",
    "docker-compose.yml"
  ],
  "known_limitations": [
    "Baseline is prepared for governance demo and should be formalized before production use."
  ],
  "follow_up_actions": [
    "Assign a permanent baseline owner.",
    "Replace demo approval with formal architecture review approval."
  ]
}
```

How to explain it:

- `architecture-baseline-l1-v0.1.0` is the reusable governance baseline.
- `ha-CPsWMS-demo-baseline` is the application-owned solution baseline.
- The evidence references point to files that describe architecture, deployment and runtime topology.

### Example: Release Compatibility Evidence

This file connects the current release candidate to the solution baseline:

```json
{
  "evidence_type": "release_compatibility_declaration",
  "status": "approved",
  "owner": "Product Architect",
  "baseline_version": "ha-CPsWMS-demo-baseline",
  "approved_by": "Architecture Demo Review",
  "approval_date": "2026-07-02",
  "evidence_refs": [
    "docs/ARCHITECTURE.md",
    "docs/DEPLOYMENT.md",
    "docker-compose.yml",
    "semantic-enrichment/schemas/enrichment_schema.json",
    "world-model-chat/schemas/cypher_query_schema.json"
  ],
  "known_limitations": [
    "Compatibility declaration is demo-scoped and does not replace a formal product release review."
  ]
}
```

How to explain it:

- Release readiness requires a compatibility declaration.
- The schema references show that interface and data compatibility are evidenced, not only asserted.
- If this file is missing or not approved, release readiness should produce a finding.

### Example: Runtime And Operation Evidence

Operation evidence links the runtime governance check to deployable, observable repository artifacts:

```json
{
  "evidence_type": "operation_evidence",
  "status": "approved",
  "owner": "Operations Owner",
  "summary": "Demo operation evidence based on deployment health-check guidance, Docker Compose runtime visibility and benchmark reports.",
  "evidence_refs": [
    "docs/DEPLOYMENT.md",
    "docker-compose.yml",
    "benchmark/reports/performance_evolution_summary.md"
  ],
  "known_limitations": [
    "No live monitoring dashboard export is currently committed."
  ],
  "follow_up_actions": [
    "Add dashboard or metrics evidence.",
    "Add operational health indicators for query-api and world-model-chat."
  ]
}
```

How to explain it:

- The current demo can pass with approved operation evidence.
- The limitation remains visible, so stakeholders can distinguish demo readiness from production-grade monitoring maturity.
- Future hardening can require live dashboard exports or stronger runtime telemetry without changing the overall evidence model.

### How The Collector Uses The Evidence

The collector reads `.governance/architecture/*.json` and combines it with repository signals such as:

| Repository signal | Example source |
|---|---|
| Architecture documentation | `docs/ARCHITECTURE.md` |
| Deployment documentation | `docs/DEPLOYMENT.md` |
| Runtime topology | `docker-compose.yml` |
| Interface and data schemas | `**/schemas/*.json` |
| Tests and benchmark reports | `tests/**/*.py`, `benchmark/reports/*` |
| Approved app evidence | `.governance/architecture/*.json` |

The collector then writes a policy input with:

```text
architecture.marker_assessments
architecture.release_compatibility_declaration
architecture.solution_baseline
architecture.compatibility_evidence
architecture.security_evidence
architecture.deployment_evidence
architecture.runtime_evidence
architecture.feedback_evidence
architecture.exceptions
```

Open the generated input when you want to show the exact policy payload:

```text
generated/current-main/ha-cpswms/architecture-release-input.json
```

Key interpretation:

- The app evidence is the raw claim and review record.
- The collected release input is the normalized policy payload.
- OPA evaluates the normalized payload, not ad hoc prose.

## Local Reproduction

Generate architecture release input:

```bash
cd /workspace/devsecops-governance-as-code
python3 scripts/collect_architecture_release_input.py \
  --repo /workspace/ha-CPsWMS \
  --output generated/demo/ha-cpswms-architecture-release-input.json \
  --release-id ha-CPsWMS-demo \
  --baseline ha-CPsWMS-demo-baseline
```

Generate the architecture governance report:

```bash
python3 scripts/generate_architecture_governance_report.py \
  --input generated/demo/ha-cpswms-architecture-release-input.json \
  --output-json generated/demo/ha-cpswms-architecture-governance-report.json \
  --output-md generated/demo/ha-cpswms-architecture-governance-report.md
```

Expected current gate summary:

| Gate | Status | Findings |
|---|---:|---:|
| Architecture Readiness | `PASS` | `0` |
| Integration Readiness | `PASS` | `0` |
| Operation Readiness | `PASS` | `0` |
| Release Readiness | `PASS` | `0` |

## GitHub Actions Result

Current known-good architecture run:

```text
https://github.com/joku-dev/ha-CPsWMS/actions/runs/28592256765
```

Expected interpretation:

- The workflow ran on `main`.
- The result was ingested by the governance repository.
- The viewer shows this as the latest architecture result for `joku-dev/ha-CPsWMS`.

## Viewer

Open:

```text
http://localhost:8000/status-viewer.html
```

Show:

- Latest Architecture Results
- Runtime Governance
- Runtime Governance Artifacts
- Source Lineage Report

Expected current viewer values:

| Viewer value | Expected |
|---|---|
| Repository | `joku-dev/ha-CPsWMS` |
| Status | `PASS` |
| Baseline | `architecture-baseline-l1-v0.1.0` |
| Last Mainline Run | `28592256765` |
| Summary | `4/4 gates pass`, `0 findings` |

## What Would Produce Findings

Findings are generated by OPA `deny` rules when required evidence is missing or too weak.

Examples:

| Situation | Expected effect |
|---|---|
| Missing solution baseline | Release readiness finding |
| Missing release compatibility declaration | Release readiness finding |
| Missing runtime evidence | Operation readiness finding |
| Missing interface or schema evidence | Integration readiness finding |
| Expired architecture exception | Finding instead of accepted exception |

In report-only mode, these findings are visible in the report, GitHub Actions summary, artifacts and viewer. Blocking behavior is an enforcement choice that can be enabled later without changing the basic evidence model.

## Demo Message

The architecture framework has been moved into the same operating model as the DevSecOps controls:

1. Human source document.
2. Machine-readable markers and levels.
3. OPA policies.
4. Released baseline.
5. Application evidence.
6. GitHub Actions execution.
7. Governance repository intake.
8. Viewer status.

This is the bridge from document-oriented architecture governance to runtime governance as code.
