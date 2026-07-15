# Demo Guide: Governance-as-Code with ha-CPsWMS

Date: 2026-07-02

## Demo Goal

Show how `devsecops-governance-as-code` acts as the central DevSecOps baseline and how `ha-CPsWMS` consumes that baseline as an application repository.

The main story:

1. The governance repo owns controls, policies, schemas, releases, and reusable workflows.
2. The application repo generates evidence: artifact, SBOM, vulnerability scan, static analysis, traceability, and governance run input.
3. The central baseline evaluates that evidence and produces pass/fail governance results.
4. Results are collected back into the governance repo for reporting and status visibility.

## Repositories

```bash
cd /workspace/devsecops-governance-as-code
git status --short --branch

cd /workspace/ha-CPsWMS
git status --short --branch
```

Expected:

- both repos are clean
- both are on `main`

## Part 1: Introduce The Central Governance Repo

```bash
cd /workspace/devsecops-governance-as-code
sed -n '1,140p' README.md
```

Key points to explain:

- `model/controls/` contains the structured control baseline.
- `policies/opa/` contains executable policy-as-code checks.
- `schemas/` defines machine-readable evidence contracts.
- `releases/l1/v1.1.3/` contains the released L1 baseline package.
- `.github/workflows/devsecops-baseline-l1-v1.1.3.yml` is the versioned reusable workflow entrypoint.
- `status/repository-results-index.json` is the central result index.

## Part 2: Validate The Governance Repo

```bash
cd /workspace/devsecops-governance-as-code
python3 scripts/validate_governance_repo.py
python3 -m unittest discover -s tests
opa check policies/opa
```

Expected result:

- validation passes
- 46 controls are loaded
- 16 L1, 14 L2, 11 L3, 5 GOV controls
- 18 unit tests pass
- OPA policies parse successfully

Talk track:

> Before an application can rely on the baseline, the baseline itself must be validated as controlled source data and executable policy.

## Part 3: Run The Local Governance Demo

```bash
cd /workspace/devsecops-governance-as-code
python3 scripts/run_demo.py
sed -n '1,120p' generated/demo/demo-run.md
```

Expected result:

- `green` scenario passes
- `red` scenario fails
- output is written to `generated/demo/`

Open the scenario summaries:

```bash
sed -n '1,120p' generated/demo/green-summary.md
sed -n '1,160p' generated/demo/red-summary.md
```

Explain:

- green input has required evidence and policy conditions
- red input intentionally misses or violates evidence requirements
- failing policies include branch protection, SBOM, vulnerability gate, artifact integrity, access control, dependency source control, IaC, artifact signing, and pipeline gates

## Part 4: Show The Control Evaluation Report

```bash
cd /workspace/devsecops-governance-as-code
sed -n '1,120p' generated/control-evaluation-report.md
```

Expected result for the demo green input:

- total controls: 46
- applicable controls: 30
- tested controls: 30
- passed: 30
- failed: 0
- not applicable: 16

Talk track:

> The policy result is not just a generic pass/fail. It maps back to individual DevSecOps baseline controls.

## Part 5: Introduce ha-CPsWMS As The Application Repo

```bash
cd /workspace/ha-CPsWMS
sed -n '1,120p' README.md
```

Key points:

- `ha-CPsWMS` is a Home Assistant to Neo4j semantic world model.
- It has multiple services: `ha-sync`, `semantic-enrichment`, `query-api`, `world-model-chat`, and `semantic_core`.
- It is the governed application repository in this demo.

Run its tests:

```bash
cd /workspace/ha-CPsWMS
python3 -m pytest -q
```

Expected:

- 26 tests pass

## Part 6: Show How ha-CPsWMS Calls The Central Baseline

```bash
cd /workspace/ha-CPsWMS
sed -n '1,320p' .github/workflows/devsecops-baseline.yml
```

Explain the three jobs:

1. `prepare-devsecops-evidence`
   - builds `dist/ha-cpswms-source.tar.gz`
   - generates `security/sbom.cyclonedx.json`
   - generates `security/vulnerability-scan.json`
   - runs `ruff` and `bandit`
   - writes `governance/traceability.json`
   - writes `governance/operations-evidence.json`
   - writes `governance/governance-run-input.json`

2. `devsecops-baseline`
   - calls:

```text
joku-dev/devsecops-governance-as-code/.github/workflows/devsecops-baseline-l1-v1.1.3.yml@l1-baseline-v1.1.3
```

3. `governance-control-evaluation`
   - checks out the governance repo
   - runs the central evaluator against the application evidence
   - uploads machine-readable and Markdown evaluation reports

## Part 7: Show The Application Evidence Contract

```bash
cd /workspace/ha-CPsWMS
sed -n '1,220p' governance/governance-run-input.main.json
```

Important fields to point out:

- `release_candidate`
- `required_platform_level`
- `repository`
- `traceability`
- `source_control`
- `static_analysis`
- `evidence.sbom`
- `evidence.vulnerability_scan`
- `artifact.digest`
- `pipeline.security_gates`
- `release_approval`
- `dependencies`
- `operations`

Talk track:

> The application repo does not copy governance logic. It produces evidence in the agreed contract. The central repo owns the interpretation.

## Part 8: Show The ha-CPsWMS Evaluation Result

```bash
cd /workspace/ha-CPsWMS
sed -n '1,120p' generated/control-evaluation-report.main.md
```

Current local report summary:

- total controls: 46
- applicable controls: 16
- tested controls: 16
- passed: 13
- failed: 3
- not applicable: 30

Then show the central indexed result in the governance repo:

```bash
cd /workspace/devsecops-governance-as-code
sed -n '1,260p' status/repository-results-index.json
```

Latest central index result for `joku-dev/ha-CPsWMS`:

- status: `pass`
- baseline: `l1-baseline-v1.1.3`
- pipeline run: `28314109954`
- total controls: 46
- applicable controls: 16
- tested controls: 16
- pass: 16
- fail: 0
- not applicable: 30

Explain the distinction:

- local checked-in report files can represent a specific snapshot or scenario
- the central result index shows the latest ingested GitHub Actions result

## Part 9: Show The Governance Baseline Statement

```bash
cd /workspace/ha-CPsWMS
sed -n '1,220p' docs/GOVERNANCE_BASELINE_STATEMENT.md
```

Key points:

- documents successful L1 baseline integration
- references pipeline run evidence
- explains what L1 does and does not assert
- explicitly says L2/L3 and artifact signing need additional maturity

## Part 10: Optional Status Viewer

If a browser is available, open:

```text
/workspace/devsecops-governance-as-code/generated/viewer/status-viewer.html
```

Or regenerate it:

```bash
cd /workspace/devsecops-governance-as-code
python3 scripts/generate_status_viewer.py
```

Use this as the visual close:

> Governance is not only a CI gate. It becomes a central status view across repositories.

## Suggested 20-Minute Demo Flow

1. 2 min: show repo statuses and explain the two-repo setup.
2. 3 min: show governance repo structure and validation.
3. 4 min: run `scripts/run_demo.py` and compare green versus red.
4. 4 min: show `ha-CPsWMS` workflow and evidence generation.
5. 4 min: show control evaluation and central result index.
6. 3 min: close with governance statement and next maturity steps.

## Fallbacks

If live commands are risky or time is short, use these checked-in files:

- `generated/demo/demo-run.md`
- `generated/demo/green-summary.md`
- `generated/demo/red-summary.md`
- `generated/control-evaluation-report.md`
- `status/repository-results-index.json`
- `/workspace/ha-CPsWMS/generated/control-evaluation-report.main.md`
- `/workspace/ha-CPsWMS/docs/GOVERNANCE_BASELINE_STATEMENT.md`

## Useful One-Liners

```bash
cd /workspace/devsecops-governance-as-code && python3 scripts/validate_governance_repo.py
cd /workspace/devsecops-governance-as-code && python3 scripts/run_demo.py
cd /workspace/ha-CPsWMS && python3 -m pytest -q
cd /workspace/ha-CPsWMS && sed -n '1,320p' .github/workflows/devsecops-baseline.yml
cd /workspace/devsecops-governance-as-code && sed -n '1,260p' status/repository-results-index.json
```

