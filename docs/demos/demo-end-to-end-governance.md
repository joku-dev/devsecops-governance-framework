# End-to-End Governance Demo Runbook

## Purpose

This runbook describes the live demo for the governance-as-code repository with the
`joku-dev/ha-CPsWMS` application repository.

The demo shows the full loop:

1. Source governance documents are kept in the governance repository.
2. Machine-readable controls, architecture markers, policies and baselines are derived from those documents.
3. The application repository provides evidence and runs governance workflows.
4. The governance repository receives the downstream results through intake workflows.
5. The status viewer shows DevSecOps, architecture and source-lineage results together.

The target state for the demo is report-only. Findings should be visible and explainable, but the demo should not block delivery unless a workflow is explicitly configured to do so.

## Demo Message

Governance is no longer only a document or a review meeting. The governance repository keeps the source documents, translates them into versioned machine-readable baselines, evaluates application evidence, and publishes human-readable and machine-readable results.

For the demo, the important point is traceability:

- A source document explains the governance intent.
- A model file or OPA policy implements part of that intent.
- A released baseline freezes a reviewed version of that implementation.
- An application workflow runs against that baseline.
- The viewer shows the result and links back to the generated artifacts.

## Repositories

| Repository | Role | Demo branch |
|---|---|---|
| `joku-dev/devsecops-governance-as-code` | Governance source, models, policies, baselines, intake and viewer | `main` |
| `joku-dev/ha-CPsWMS` | Application evidence and downstream GitHub Actions workflows | `main` |

Local paths used during development:

```text
/workspace/devsecops-governance-as-code
/workspace/ha-CPsWMS
```

## Current Demo Baselines

| Domain | Baseline | Release package |
|---|---|---|
| DevSecOps | `l1-baseline-v1.1.3` | `releases/l1/v1.1.3/` |
| Architecture | `architecture-baseline-l1-v0.1.0` | `releases/architecture/l1/v0.1.0/` |
| Application solution | `ha-CPsWMS-demo-baseline` | Supplied by `ha-CPsWMS` architecture evidence |

Why this matters:

- DevSecOps and architecture are not evaluated from an unversioned working directory during the demo.
- The app repository can pin a released governance baseline.
- The viewer can show which baseline produced a result.

## Current Mainline Results

These values are the known-good state after the current end-to-end test.

| Domain | Repository | Status | Baseline | Last mainline run | Commit | Generated |
|---|---|---|---|---|---|---|
| DevSecOps | `joku-dev/ha-CPsWMS` | `pass` | `l1-baseline-v1.1.3` | `28592257991` | `4a86f0c5b3d7aa1883533fa787530a1f5ff886e7` | `2026-07-02T13:05:30Z` |
| Architecture | `joku-dev/ha-CPsWMS` | `PASS` | `architecture-baseline-l1-v0.1.0` | `28592256765` | `4a86f0c5b3d7aa1883533fa787530a1f5ff886e7` | `2026-07-02T13:05:12Z` |

Expected summaries:

| Domain | Expected result |
|---|---|
| DevSecOps | `16/16` controls pass, `0` fail |
| Architecture | `4/4` gates pass, `0` findings |

Interpretation:

- The current `ha-CPsWMS` mainline is demo-ready for both governance domains.
- The result does not mean formal production approval. It means the repository passes the currently released report-only governance checks.

## Public Source Placeholders

The public source placeholders live under:

```text
docs/governance/source-documents/
```

Original source documents are withheld from the public repository. Current public placeholders:

| Source document | Governance domain |
|---|---|
| `DSCB-STD-SRC-001.public.md` | DevSecOps control baseline |
| `PRA-STD-SRC-001.public.md` | DevSecOps platform reference architecture |
| `DEVSECOPS-DIR-SRC-001.public.md` | DevSecOps directive |
| `DEVSECOPS-POL-SRC-001.public.md` | DevSecOps policy |
| `ARCH-SDD-SRC-001.public.md` | Architecture runtime governance |

Why this matters:

- The demo can start with the documents instead of the tooling.
- The governance repository can show which runtime artifacts came from which source.
- The architecture source document was not originally written as runtime governance, but the repo now contains a machine-readable addendum derived from it.

## Source Lineage

Open the generated source-lineage report:

```text
generated/reports/source-lineage-report.md
generated/reports/source-lineage-report.json
```

Current expected summary:

| Metric | Value |
|---|---:|
| Source documents | `10` |
| Source documents with lineage entries | `10` |
| Derived artifact links | `119` |
| Missing derived artifacts | `0` |

Interpretation:

- Every current source document has at least one lineage entry.
- The derived artifact links cover governance models, OPA policies, release packages, schemas, generated reports, indexes and the viewer.
- `0` missing derived artifacts means the lineage catalog currently points to files that exist in the repository.

This is the first demo proof point: the repository can explain how document-based governance flows into machine-readable governance assets.

## Local Prerequisites

Required tools:

```bash
python3
git
```

Useful tools:

```bash
gh
opa
```

Check GitHub authentication if you want to inspect or rerun GitHub Actions from the terminal:

```bash
gh auth status
```

The local viewer can be served from the generated viewer directory:

```bash
cd /workspace/devsecops-governance-as-code/generated/viewer
python3 -m http.server 8000
```

Then open:

```text
http://localhost:8000/status-viewer.html
```

## Validate The Governance Repository

Run this in the governance repository:

```bash
cd /workspace/devsecops-governance-as-code
python3 scripts/validate_runtime_governance.py
python3 scripts/validate_governance_repo.py
python3 -m unittest discover -s tests
```

Why:

- `validate_runtime_governance.py` checks the architecture runtime governance model, architecture schemas, marker catalog, generated reports and OPA readiness examples.
- `validate_governance_repo.py` checks DevSecOps controls, traceability, pipeline placement, governance requirements and source-document lineage.
- The unit tests cover the scripts that generate reports, indexes, release packages and viewer data.

Expected result:

```text
Runtime governance validation passed
Validation passed
OK
```

Interpretation:

- The governance repository is internally consistent.
- This step validates the governance engine and generated metadata, not a new application run.

## Demo Step 1: Show The Source-To-Artifact Chain

Open:

```text
docs/governance/source-documents/
generated/reports/source-lineage-report.md
```

Explain:

- The source documents are the human governance input.
- The lineage report is the machine-readable accountability layer.
- For architecture, the `ARCH-SDD-SRC-001.public.md` source document leads to architecture levels, quality markers, guardrails, OPA policies, schemas, release package and viewer output.
- For DevSecOps, the source documents lead to control models, policy-as-code, release baselines, generated reports and viewer output.

Expected interpretation:

- If a stakeholder asks "where did this check come from?", the demo can point to the source document and the derived artifacts.
- If a derived artifact is missing, validation should fail and the lineage report should show it.

## Demo Step 2: Show Released Baselines

Open the release packages:

```text
releases/l1/v1.1.3/baseline-package.md
releases/l1/v1.1.3/release-metadata.json
releases/architecture/l1/v0.1.0/baseline-package.md
releases/architecture/l1/v0.1.0/release-metadata.json
```

Explain:

- A baseline freezes a reviewed governance state.
- Application repositories should consume baseline tags or pinned commits, not an arbitrary local working tree.
- DevSecOps and architecture now use the same operating model: source documents, machine-readable model, OPA checks, released baseline, downstream execution, result intake and viewer status.

Expected interpretation:

- `l1-baseline-v1.1.3` is the current DevSecOps L1 demo baseline.
- `architecture-baseline-l1-v0.1.0` is the current architecture L1 demo baseline.
- The architecture baseline is intentionally early, but it is now versioned and demo-ready.

## Demo Step 3: Show Application Evidence

In the application repository, inspect governance evidence:

```bash
cd /workspace/ha-CPsWMS
find .governance -maxdepth 4 -type f | sort
```

Expected evidence areas:

```text
.governance/architecture/
.governance/devsecops/
```

For the current demo, the relevant files are:

```text
.governance/architecture/solution-baseline.json
.governance/architecture/release-compatibility-declaration.json
.governance/architecture/security-evidence.json
.governance/architecture/resilience-evidence.json
.governance/architecture/operation-evidence.json
.governance/architecture/feedback-evidence.json
.governance/devsecops/release-evidence.json
```

Why:

- The application repository owns its evidence.
- The governance repository owns the reusable rules, schemas, collectors and viewer.
- This split allows the same governance repo to evaluate multiple application repositories later.

### What The Architecture Evidence Looks Like

Each architecture evidence file is a small JSON review record. It does not contain all architecture documentation itself. Instead, it records who owns the evidence, whether it is approved, what repository files support it, and what limitations or follow-up actions remain.

Common architecture evidence fields:

| Field | Purpose |
|---|---|
| `evidence_type` | Tells the collector what kind of architecture evidence this file represents. |
| `status` | Review state. The demo expects `approved` for the passing mainline state. |
| `owner` | Accountable role for the evidence. |
| `approved_by` and `approval_date` | Review attribution for the demo evidence. |
| `baseline_version` | Used for baseline and compatibility evidence. |
| `summary` | Human explanation of what the evidence proves. |
| `evidence_refs` | Repository files that support the claim. |
| `known_limitations` | Visible caveats that do not currently fail the report-only demo. |
| `follow_up_actions` | Improvement backlog items for later hardening. |

Example architecture evidence shape:

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

How to explain this in the demo:

- `solution-baseline.json` defines the app-owned solution baseline that the repository claims to be compatible with.
- `release-compatibility-declaration.json` states that the current release candidate is compatible with that baseline.
- `security-evidence.json`, `resilience-evidence.json` and `operation-evidence.json` provide release-critical support for security, resilience, deployment and runtime operation checks.
- `feedback-evidence.json` shows that operational or benchmark feedback can feed back into architecture improvement.
- The collector turns these files plus referenced repository artifacts into `generated/current-main/ha-cpswms/architecture-release-input.json`.

### What The DevSecOps Evidence Looks Like

The DevSecOps demo uses:

```text
.governance/devsecops/release-evidence.json
```

That file records approved demo evidence for repository protection, SBOM presence, vulnerability scan presence, artifact integrity, dependency source approval and pipeline gate behavior.

Representative shape:

```json
{
  "status": "approved",
  "owner": "DevSecOps Owner",
  "repository": {
    "protected_branch": true,
    "direct_push_allowed": false,
    "review_required": true
  },
  "sbom": {
    "exists": true,
    "linked_to_artifact": true
  },
  "vulnerability_scan": {
    "exists": true
  },
  "artifact": {
    "digest_exists": true,
    "digest_linked_to_artifact": true,
    "signature_exists": false
  },
  "pipeline": {
    "security_gates_enforced": true,
    "security_thresholds_exceeded": false
  }
}
```

Interpretation:

- Missing or incomplete evidence should become report findings.
- Approved evidence can turn findings into passing gates without changing the policy code.
- Demo evidence is intentionally transparent about limitations. It can pass the current report-only demo while still showing what must be improved for production-grade evidence.

## Demo Step 4: Show The App Workflows

In `joku-dev/ha-CPsWMS`, show these GitHub Actions workflows:

| Workflow | Purpose | Expected demo behavior |
|---|---|---|
| `DevSecOps Baseline` | Runs the released DevSecOps baseline | Passes on mainline |
| `DevSecOps Governance` | Runs DevSecOps governance with selectable mode | Report-only by default for demo |
| `Architecture Runtime Governance` | Runs architecture governance against `architecture-baseline-l1-v0.1.0` | Passes on mainline |

Explain:

- The app workflows execute in the application context.
- They publish artifacts in the application repository's GitHub Actions run.
- On pull requests, the governance checks run and produce artifacts, but they do not update the central governance viewer.
- On `push` to `main`, the relevant workflows send repository-dispatch intake events to the governance repository.
- DevSecOps can be manually switched between report-only and blocking behavior.
- Architecture is currently used as report-only for the live demo unless the workflow is configured to fail on findings.

Expected interpretation:

- The demo is safe to run live because findings can be reported without blocking.
- The same mechanics can later be hardened into mandatory gates.

## Demo Step 5: Trigger A Live Mainline Refresh

Preferred demo flow:

1. Create a small pull request in `ha-CPsWMS`.
2. Merge it to `main`.
3. Watch the app repository workflows run on `main`.
4. Watch the governance repository intake workflows update the indexes and viewer.

Why:

- Mainline status is the most useful demo artifact.
- A mainline run proves that the status does not only come from local scripts.
- The viewer can show the latest real repository result.

Alternative:

1. Manually rerun the app workflows.
2. Use this only when a mainline change is not practical.

Interpretation:

- Pull-request runs are useful for validating a proposed change before merge.
- Manual reruns are useful for testing.
- A merged mainline change gives the strongest demo story because it refreshes the repository's official status.

## Demo Step 6: Observe Downstream App Runs

Current known-good app runs:

| Workflow | Run | Expected status |
|---|---:|---|
| Architecture Runtime Governance | `28592256765` | Success |
| DevSecOps Baseline | `28592257991` | Success |
| DevSecOps Governance | `28592256817` | Success |
| CI | `28592256856` | Success |

Open the run URLs:

```text
https://github.com/joku-dev/ha-CPsWMS/actions/runs/28592256765
https://github.com/joku-dev/ha-CPsWMS/actions/runs/28592257991
```

Explain:

- The app repo runs the checks and creates evidence artifacts.
- The architecture result is associated with `architecture-baseline-l1-v0.1.0`.
- The DevSecOps result is associated with `l1-baseline-v1.1.3`.

Expected interpretation:

- If a pull-request workflow succeeds, the proposed change has report evidence in the app repository, but the central viewer is not expected to update.
- If a `main` push workflow succeeds and the viewer updates, the downstream-to-governance loop is working.
- If a `main` push workflow succeeds but the viewer does not update, inspect the governance intake workflow.

## Demo Step 7: Observe Governance Intake

In the governance repository, inspect the intake workflows:

```text
.github/workflows/intake-governance-result.yml
.github/workflows/intake-architecture-result.yml
```

Explain:

- The app repository sends result metadata and artifacts to the governance repository.
- The governance repository updates:

```text
status/repository-results-index.json
status/architecture-results-index.json
generated/viewer/status-viewer.html
```

- The intake workflows regenerate indexes and the viewer before committing.
- The intake workflows use rebase with autostash so near-simultaneous DevSecOps and architecture intakes can both land.

Expected interpretation:

- Intake commits are not manual demo cosmetics; they are part of the governance feedback loop.
- A race between two intake workflows should be recoverable by rerunning the failed intake.

## Demo Step 8: Interpret The Viewer

Open:

```text
http://localhost:8000/status-viewer.html
```

Show these sections:

| Viewer section | What to explain |
|---|---|
| Repository Governance Status | DevSecOps and Architecture status side by side for each repository |
| Runtime Governance | End-to-end demo status, architecture gates and DevSecOps release result |
| Repository Execution | Mainline history, branch validation, manual diagnostics and run links |
| Artifacts & Machine Data | Links to indexes, reports, lineage and generated machine-readable files |

Expected interpretation:

- DevSecOps should show `pass` for baseline `l1-baseline-v1.1.3`.
- Architecture should show `PASS` for baseline `architecture-baseline-l1-v0.1.0`.
- The viewer is the demo cockpit: it makes the current governance state visible without opening every raw JSON file.

## Report-Only Versus Blocking

The demo should run report-only unless a blocking gate is intentionally demonstrated.

| Domain | Report-only behavior | Blocking behavior |
|---|---|---|
| DevSecOps | Findings are reported in summaries, artifacts and viewer data | Manual workflow mode can fail on findings |
| Architecture | Findings are reported in summaries, artifacts and viewer data | Can be hardened by enabling fail-on-findings in the consuming workflow |

Why:

- Report-only mode is the safest way to demonstrate rollout.
- Blocking mode is useful after teams agree on evidence quality, exceptions and remediation paths.
- Both modes should use the same evidence and policy logic so the governance result remains comparable.

Interpretation:

- A report-only failure is still a real governance signal.
- Blocking is an enforcement choice, not a different governance model.

## What The Demo Proves

The demo proves that:

1. Governance source documents can be linked to machine-readable artifacts.
2. DevSecOps controls and architecture topics can use the same baseline mechanics.
3. Application repositories can provide evidence without copying policy logic.
4. GitHub Actions can run governance checks on the app repository.
5. Governance repository intake can collect downstream results.
6. A viewer can show mainline governance status for both DevSecOps and architecture.

## What The Demo Does Not Yet Prove

The demo does not yet prove:

- formal production approval
- complete enterprise security certification
- fully automated semantic extraction from every source document
- live SBOM, vulnerability scanner or artifact-signing integrations for every application
- live operational monitoring integration
- mature architecture L2/L3 rollout

Interpretation:

- The demo is a working governance loop.
- Some evidence is still demo evidence or manually curated governance evidence.
- The next maturity step is tool integration and broader application coverage.

## Troubleshooting

### Viewer Is Stale

Regenerate it:

```bash
cd /workspace/devsecops-governance-as-code
python3 scripts/generate_status_viewer.py
```

Then refresh:

```text
http://localhost:8000/status-viewer.html
```

### Source Lineage Looks Wrong

Regenerate and validate:

```bash
python3 scripts/generate_source_lineage_report.py
python3 scripts/validate_governance_repo.py
```

Expected result:

```text
Validation passed
```

### Architecture Findings Appear

Inspect the architecture report artifact from the app workflow or the local generated report.

Typical causes:

- missing `.governance/architecture/*.json` evidence
- evidence does not match the schema
- baseline or compatibility declaration is missing
- runtime or feedback evidence is below the expected marker level

Interpretation:

- The finding should describe the missing evidence and the expected remediation.
- In report-only mode, the workflow can still complete while making the issue visible.

### DevSecOps Findings Appear

Inspect the DevSecOps report artifact from the app workflow.

Typical causes:

- missing `.governance/devsecops/release-evidence.json`
- missing CI, dependency or artifact evidence
- policy candidate configured as blocking in the selected mode

Interpretation:

- Report-only mode should publish the finding.
- Blocking mode should fail the workflow when the finding is configured as enforceable.

### Intake Does Not Update The Viewer

Check the governance repository Actions tab for:

```text
Intake Governance Result
Intake Architecture Result
```

If two intake runs overlap, rerun the failed one. The workflows use `git pull --rebase --autostash origin main`, so a rerun should usually recover from a concurrent update.

### GitHub Authentication Fails

Use:

```bash
gh auth login
gh auth status
```

The demo also needs the application repository to have a token or secret that can dispatch result intake to the governance repository.
