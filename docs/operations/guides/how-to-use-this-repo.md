# How To Use This Repo

## Purpose

This repository is a governance-as-code workspace for DevSecOps policy, directive, control, platform, evidence, waiver, and traceability modeling.

It is not a long-running service. Instead, teams use it to maintain structured governance content, validate consistency, generate review artifacts, and prepare policy-as-code enforcement.

## Who Uses It

### Governance Owner

The Governance Owner maintains:

- `model/controls/`
- `model/documents/`
- `model/traceability/`
- `model/waivers/`

Typical tasks:

- update control requirements,
- adjust policy and directive drafts,
- review gaps and missing governance decisions,
- prepare governance review artifacts.

### Platform Owner

The Platform Owner maintains:

- `model/platform/platform-capabilities.yaml`
- related traceability mappings

Typical tasks:

- map platform capabilities to controls,
- identify missing platform enablement,
- align platform architecture with required baseline levels.

### Security / Policy Engineer

The Security or Policy Engineer maintains:

- `policies/opa/`
- policy candidate definitions in `model/controls/`

Typical tasks:

- validate Rego policies,
- test policy behavior against representative input,
- decide which automated controls should become executable gates.

### Audit / Compliance Reviewer

Audit and Compliance stakeholders use the generated artifacts for review and evidence discussions.

Typical tasks:

- inspect governance document authority,
- inspect control-to-platform traceability,
- review open modeling or implementation gaps,
- review waiver governance alignment.

## Daily Workflow

### 1. Update The Structured Sources

Edit the relevant YAML or Markdown files in:

- `model/controls/`
- `model/platform/`
- `model/documents/`
- `model/traceability/`
- `model/waivers/`
- `docs/`

### 2. Validate Repository Consistency

Run:

```bash
python3 scripts/validate_governance_repo.py
```

This checks:

- control schemas,
- governance document schemas,
- governance run input schema and example payload,
- traceability consistency,
- known evidence and platform capabilities,
- governance document paths,
- OPA policy syntax.

If you want to understand the machine-readable contract that downstream repositories should produce, read:

- `docs/operations/evidence/governance-evidence-contract.md`
- `docs/operations/evidence/governance-evidence-schema-versioning.md`
- `schemas/governance-run-input.schema.json`
- `docs/examples/governance-run-input.example.json`

If you want to change Policy or Directive inputs safely and propagate them through the baseline, read:

- `docs/operations/guides/how-to-update-baseline-input-documents.md`

If you want to normalize downstream run results back into this repository and refresh the viewer, read:

- `docs/operations/evidence/governance-result-intake-and-viewer-usage.md`

### 3. Generate Review Artifacts

Generate the core outputs:

```bash
python3 scripts/generate_traceability_csv.py
python3 scripts/generate_document_control_matrix.py
python3 scripts/generate_open_gap_report.py
python3 scripts/render_governance_documents.py
python3 scripts/generate_control_evaluation_report.py \
  --input-file demo/inputs/release-candidate-green.json \
  --output-file generated/control-evaluation-report.json \
  --markdown-file generated/control-evaluation-report.md
python3 scripts/generate_status_viewer.py
```

Important outputs:

- `generated/xlsx/traceability_matrix.csv`
- `generated/xlsx/document_control_matrix.csv`
- `generated/xlsx/open_gap_report.csv`
- `generated/reports/document-control-matrix.md`
- `generated/reports/open-gap-report.md`
- `generated/documents/devsecops-pol-001.rendered.md`
- `generated/documents/devsecops-pol-001.html`
- `generated/documents/devsecops-dir-001.rendered.md`
- `generated/documents/devsecops-dir-001.html`
- `generated/control-evaluation-report.json`
- `generated/control-evaluation-report.md`
- `generated/viewer/status-viewer.html`

### 4. Run Regression Checks

Run:

```bash
python3 -m unittest discover -s tests
opa check policies/opa
```

### 5. Review And Commit

Before committing, check:

- whether the gap report changed as expected,
- whether generated artifacts reflect the intended governance change,
- whether the repository still validates cleanly.

## How To Use The Outputs

### `traceability_matrix.csv`

Use this file to understand which controls map to which:

- platform capabilities,
- evidence expectations,
- policy candidates,
- authority documents.

### `document_control_matrix.csv`

Use this file to review which governance documents authorize or shape which controls.

This is useful for:

- governance board reviews,
- audit preparation,
- policy/directive/standard alignment discussions.

### `open_gap_report`

Use the open gap report to focus follow-up work.

Typical gap categories include:

- draft governance documents,
- incomplete platform capability classification,
- automated controls not yet promoted to policy-as-code candidates.

## Example Commands

### Full Local Check

```bash
python3 scripts/validate_governance_repo.py
python3 scripts/generate_traceability_csv.py
python3 scripts/generate_document_control_matrix.py
python3 scripts/generate_open_gap_report.py
python3 -m unittest discover -s tests
opa check policies/opa
```

### Demo Run

```bash
python3 scripts/run_demo.py
```

This generates:

- `generated/demo/demo-run.md`
- `generated/demo/green-summary.json`
- `generated/demo/green-summary.md`
- `generated/demo/red-summary.json`
- `generated/demo/red-summary.md`

### Validate A Governance Run Input

If another repository wants to provide richer governance evidence, it should produce a file such as:

- `governance/governance-run-input.json`

The official contract for that payload is documented in:

- `docs/operations/evidence/governance-evidence-contract.md`

The governing schema is:

- `schemas/governance-run-input.schema.json`

The example payload is:

- `docs/examples/governance-run-input.example.json`

### Evaluate A Single Policy

```bash
opa eval -f pretty \
  -d policies/opa \
  -i policies/example-input.release-candidate.json \
  'data.devsecops.branch_protection.deny'
```

## Recommended CI Integration

At minimum, CI should run:

```bash
python3 scripts/validate_governance_repo.py
python3 -m unittest discover -s tests
opa check policies/opa
```

Optionally, CI can also generate the reports and publish them as pipeline artifacts for governance review.
