# ha-CPsWMS Architecture Governance Results

## Purpose

This document explains the architecture governance check that was executed for `ha-CPsWMS`.

It answers four questions:

1. What was checked?
2. Why was it checked?
3. How was the result generated?
4. How should the result be interpreted?

The check is currently used as **report-only governance**. It makes architecture readiness visible in CI and in the viewer, but it does not block pull requests.

## Target

| Field | Value |
|---|---|
| Application repository | `/workspace/ha-CPsWMS` |
| Local generated report commit | `77e8fcd` |
| Latest mainline commit in viewer | `716c3cda4fa5cef7504ca7b3263f0cd1697b6e6c` |
| Release ID | `ha-CPsWMS-demo` |
| Detected services | `5` |
| Governance repository | `/workspace/devsecops-governance-framework` |

## Source Files

The result was produced from these governance files:

| File | Purpose |
|---|---|
| `scripts/collect_architecture_release_input.py` | Collects observable architecture evidence from the app repository. |
| `scripts/generate_architecture_governance_report.py` | Runs the architecture OPA policies and writes JSON/Markdown reports. |
| `policies/opa/architecture_readiness.rego` | Checks basic architecture readiness markers. |
| `policies/opa/architecture_integration_readiness.rego` | Checks integration-readiness markers and evidence. |
| `policies/opa/architecture_operation_readiness.rego` | Checks runtime, operation and feedback readiness. |
| `policies/opa/architecture_release_readiness.rego` | Checks release-critical architecture evidence. |
| `generated/demo/ha-cpswms-architecture-release-input.json` | Machine-readable policy input generated from `ha-CPsWMS`. |
| `generated/demo/ha-cpswms-architecture-governance-report.json` | Machine-readable result. |
| `generated/demo/ha-cpswms-architecture-governance-report.md` | Human-readable result. |

The app repository provided these explicit architecture evidence files:

| Evidence file | Meaning |
|---|---|
| `.governance/architecture/solution-baseline.json` | Declares the demo solution baseline. |
| `.governance/architecture/release-compatibility-declaration.json` | Declares compatibility with the demo baseline. |
| `.governance/architecture/security-evidence.json` | Provides approved security-related architecture evidence. |
| `.governance/architecture/resilience-evidence.json` | Provides approved resilience evidence. |
| `.governance/architecture/operation-evidence.json` | Provides approved operation/runtime evidence. |
| `.governance/architecture/feedback-evidence.json` | Provides approved feedback evidence. |

## How The Check Was Run

The architecture release input was generated with:

```bash
python3 scripts/collect_architecture_release_input.py \
  --repo /workspace/ha-CPsWMS \
  --output generated/demo/ha-cpswms-architecture-release-input.json \
  --release-id ha-CPsWMS-demo \
  --baseline ha-CPsWMS-demo-baseline
```

The report was generated with:

```bash
python3 scripts/generate_architecture_governance_report.py \
  --input generated/demo/ha-cpswms-architecture-release-input.json \
  --output-json generated/demo/ha-cpswms-architecture-governance-report.json \
  --output-md generated/demo/ha-cpswms-architecture-governance-report.md
```

## How The Input Was Produced

The collector reads the target application repository and turns repository state into a policy input JSON.

It looks for:

| Signal | Examples |
|---|---|
| Architecture documentation | `docs/ARCHITECTURE.md`, `README.md` |
| Deployment documentation | `docs/DEPLOYMENT.md` |
| Runtime topology | `docker-compose.yml`, `**/Dockerfile` |
| Interface and data contracts | `**/schemas/*.json` |
| Test evidence | `tests/**/*.py` |
| Benchmark and feedback evidence | `benchmark/reports/*benchmark.json`, `benchmark/reports/performance_evolution_summary.md` |
| Approved architecture evidence | `.governance/architecture/*.json` |

It then produces:

- marker assessments with scores
- evidence references
- release compatibility information
- solution baseline information
- runtime, feedback, security and deployment evidence flags
- architecture exceptions, if present

For the current run, the generated input contains:

| Input aspect | Result |
|---|---:|
| Release candidate mode | `true` |
| Marker assessments | `32` |
| Architecture exceptions | `0` |
| Release compatibility declaration | present and approved |
| Solution baseline | present |
| Compatibility evidence | present |
| Security evidence | present |
| Deployment evidence | present |
| Runtime evidence | present |
| Feedback evidence | present |

## Marker Scoring

The collector uses a simple maturity score:

| Score | Meaning |
|---:|---|
| `1` | Evidence is missing or too weak. |
| `3` | Evidence is present. |
| `4` | Evidence is verified or approved. |
| `5` | Evidence is continuous or strongly automated. |

The current demo mainly uses `3` and `4`:

- `3` means the repository contains relevant architecture evidence.
- `4` means the evidence is approved through `.governance/architecture/*.json` or otherwise verified.

## Gate 1: Architecture Readiness

### What Was Checked

The gate checks whether the repository is sufficiently described, owned and understandable from an architecture point of view.

It checks these marker IDs:

```text
B1 B2 B3 B4 P0 P1 P2 P3 P7 S0 S1 S2
```

Each marker must have:

- score `>= 3`, or
- a valid approved exception.

### Why This Is Checked

A repository should not move into governed delivery if its architecture is not understandable. The check asks whether basic architecture, product, solution and ownership information exists.

### How It Was Checked

OPA policy:

```text
policies/opa/architecture_readiness.rego
```

Main evidence sources:

```text
docs/ARCHITECTURE.md
README.md
docs/DEPLOYMENT.md
```

### Result

```text
Architecture Readiness: PASS
Findings: 0
```

### Interpretation

The current repository contains enough basic architecture evidence for the demo readiness gate.

## Gate 2: Integration Readiness

### What Was Checked

The gate checks whether the repository has enough interface, schema, compatibility and deployment evidence for integration.

It checks these marker IDs:

```text
E3 E5 S3 S4 S5 S7 P4 P5 P6
```

Each marker must have:

- score `>= 3`, or
- a valid approved exception.

It also requires:

- compatibility evidence
- deployment evidence

### Why This Is Checked

Architecture is not only documentation. Integration readiness asks whether the product can participate in a larger solution through declared interfaces, schemas, deployment assumptions and compatibility evidence.

### How It Was Checked

OPA policy:

```text
policies/opa/architecture_integration_readiness.rego
```

Main evidence sources:

```text
.governance/architecture/release-compatibility-declaration.json
.governance/architecture/solution-baseline.json
docs/ARCHITECTURE.md
docs/DEPLOYMENT.md
docker-compose.yml
semantic-enrichment/schemas/*.json
world-model-chat/schemas/*.json
tests/**/*.py
```

### Result

```text
Integration Readiness: PASS
Findings: 0
```

### Interpretation

The current repository provides enough demo evidence for integration readiness. It has architecture documentation, deployment evidence, schemas and a compatibility declaration.

## Gate 3: Operation Readiness

### What Was Checked

The gate checks whether operation and feedback evidence is mature enough.

It checks these marker IDs:

```text
B5 P11
```

Each marker must have:

- score `>= 4`, or
- a valid approved exception.

It also requires:

- runtime evidence
- feedback evidence

### Why This Is Checked

A system can look architecturally correct but still be weak operationally. This gate asks whether the repository provides evidence about runtime behavior, operations and feedback loops.

### How It Was Checked

OPA policy:

```text
policies/opa/architecture_operation_readiness.rego
```

Main evidence sources:

```text
.governance/architecture/operation-evidence.json
.governance/architecture/feedback-evidence.json
docs/DEPLOYMENT.md
docker-compose.yml
benchmark/reports/performance_evolution_summary.md
```

### Result

```text
Operation Readiness: PASS
Findings: 0
```

### Interpretation

Operation readiness passes because approved operation and feedback evidence exists. This is still demo-scoped; the evidence notes that live monitoring dashboard exports and formal architecture debt linkage are future improvements.

## Gate 4: Release Readiness

### What Was Checked

The gate checks whether release-critical architecture evidence is available.

It checks these marker IDs:

```text
E6 E7 E8 S3 S5 S6 S8 P5 P6 P8 P9 P10 P13
```

Each marker must have:

- score `>= 4`, or
- a valid approved exception.

It also requires:

- release compatibility declaration
- baseline version
- approved compatibility declaration
- solution baseline
- compatibility evidence
- security evidence
- deployment evidence

Approved exceptions, if any exist, must include:

- owner
- mitigation
- risk classification
- review date
- expiry date
- approval authority
- non-expired status

### Why This Is Checked

Release readiness is stricter than basic readiness. It asks whether a release candidate can be related to a solution baseline and whether critical security, compatibility, resilience, deployment and release evidence is present.

### How It Was Checked

OPA policy:

```text
policies/opa/architecture_release_readiness.rego
```

Main evidence sources:

```text
.governance/architecture/release-compatibility-declaration.json
.governance/architecture/solution-baseline.json
.governance/architecture/security-evidence.json
.governance/architecture/resilience-evidence.json
docs/DEPLOYMENT.md
docker-compose.yml
benchmark/reports/performance_evolution_summary.md
semantic-enrichment/schemas/*.json
world-model-chat/schemas/*.json
```

### Result

```text
Release Readiness: PASS
Findings: 0
```

### Interpretation

The current repository satisfies the demo release-readiness gate. It has an approved compatibility declaration, a solution baseline, security evidence, deployment evidence and release-critical marker evidence.

This does not mean formal production release approval. It means the current machine-readable demo governance policy accepts the current repository evidence.

## Overall Result

| Gate | Status | Findings |
|---|---:|---:|
| Architecture Readiness | PASS | 0 |
| Integration Readiness | PASS | 0 |
| Operation Readiness | PASS | 0 |
| Release Readiness | PASS | 0 |

Summary:

```text
Gate count: 4
Passed: 4
Gates with findings: 0
Total findings: 0
```

## How To Interpret A PASS

A `PASS` means:

- required evidence was found
- required marker scores met the policy threshold
- no invalid or expired exception was needed
- OPA returned no deny messages for the gate

A `PASS` does not mean:

- formal certification
- production approval
- complete security accreditation
- complete operational maturity
- absence of future architecture work

The current result is best interpreted as:

```text
ha-CPsWMS is demo-ready for architecture runtime governance.
The repository provides sufficient approved, machine-readable evidence for the current report-only architecture gates.
```

## How Findings Would Be Produced

Findings are generated when an OPA `deny` rule returns a message.

Examples:

| Situation | Example finding |
|---|---|
| Required marker missing | `Architecture-readiness marker B1 is missing and has no valid exception.` |
| Score below threshold | `Release-critical architecture marker P10 requires score 4 or a valid exception.` |
| Missing compatibility declaration | `Release candidate requires a release compatibility declaration.` |
| Missing runtime evidence | `Operation readiness requires runtime evidence.` |
| Expired exception | `Approved architecture exception ... is expired and must not be used for release readiness.` |

In report-only mode, these findings would be visible in:

```text
generated/demo/ha-cpswms-architecture-governance-report.md
generated/demo/ha-cpswms-architecture-governance-report.json
generated/viewer/status-viewer.html
GitHub Actions Step Summary
GitHub Actions artifact: architecture-governance-evidence
```

## Architecture Status Index

The architecture result is now also stored in the same style as the DevSecOps governance status.

Architecture snapshots are stored under:

```text
status/architecture-results/
```

The generated architecture index is:

```text
status/architecture-results-index.json
```

The current latest tracked architecture result for `ha-CPsWMS` contains:

| Field | Value |
|---|---|
| Repository | `joku-dev/ha-CPsWMS` |
| Architecture governance baseline | `architecture-baseline-l1-v0.1.0` |
| ha-CPsWMS solution baseline | `ha-CPsWMS-demo-baseline` |
| Last tracked run | `29415015294` |
| Run URL | `https://github.com/joku-dev/ha-CPsWMS/actions/runs/29415015294` |
| Branch | `main` |
| Event | `push` |
| Commit | `716c3cda4fa5cef7504ca7b3263f0cd1697b6e6c` |
| Generated | `2026-07-15T12:23:26Z` |
| Result | `PASS`, `4/4 gates`, `0 findings` |

This is a mainline result. Earlier architecture history entries include branch and early mainline runs that used the demo solution baseline as the reported architecture baseline. The current mainline result reports the released governance baseline, `architecture-baseline-l1-v0.1.0`.

## Current Known Limitations

The current evidence files intentionally record follow-up work. Important examples:

| Area | Limitation |
|---|---|
| Security | No dedicated vulnerability scan report is committed as architecture evidence. |
| Resilience | No dedicated degraded-mode or failover test report exists yet. |
| Operation | No live monitoring dashboard export is committed yet. |
| Feedback | Feedback is benchmark-oriented and not yet linked to a formal architecture debt register. |
| Baseline | The solution baseline is demo-scoped and should be formalized before production use. |

These limitations do not fail the current demo policy because approved evidence exists and the current policy scope is intentionally report-only.

## Reproduction Commands

Regenerate the architecture input:

```bash
cd /workspace/devsecops-governance-framework
python3 scripts/collect_architecture_release_input.py \
  --repo /workspace/ha-CPsWMS \
  --output generated/demo/ha-cpswms-architecture-release-input.json \
  --release-id ha-CPsWMS-demo \
  --baseline ha-CPsWMS-demo-baseline
```

Regenerate the architecture report:

```bash
python3 scripts/generate_architecture_governance_report.py \
  --input generated/demo/ha-cpswms-architecture-release-input.json \
  --output-json generated/demo/ha-cpswms-architecture-governance-report.json \
  --output-md generated/demo/ha-cpswms-architecture-governance-report.md
```

Regenerate the viewer:

```bash
python3 scripts/generate_status_viewer.py
```

Validate the governance repository:

```bash
python3 scripts/validate_runtime_governance.py
python3 scripts/validate_governance_repo.py
```

## Demo Explanation

For a live demo, explain the flow like this:

```text
The application repository owns its evidence.
The governance repository owns the policies and collectors.
The collector converts repository evidence into a machine-readable release input.
OPA evaluates architecture readiness, integration readiness, operation readiness and release readiness.
The report shows PASS or findings per gate.
The viewer summarizes the result together with the DevSecOps governance result.
```

This demonstrates how document-oriented architecture governance can be moved toward runtime governance without losing traceability to the original architecture framework.
