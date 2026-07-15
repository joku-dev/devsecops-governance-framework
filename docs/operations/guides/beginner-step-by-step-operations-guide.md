# Beginner Step-By-Step Operations Guide

## What This Repository Is

This repository is not a normal application server.

You do not start it like a web backend or a database. Instead, you use it as an **operational governance workspace**.

That means:

- you maintain governance content,
- you validate that content,
- you generate reports and rendered documents,
- you evaluate governance rules,
- you review the outputs,
- and only then do you approve or change governance decisions.

## What You Need Before You Start

Open a terminal and go into the repository:

```bash
cd /workspace/devsecops-governance-framework
```

Useful tools:

- `python3`
- `opa`
- optionally `jsonschema` and `pyyaml` in your Python environment

If you want the full local schema validation without warnings, install:

```bash
python3 -m pip install jsonschema pyyaml
```

## The Operational Big Picture

Operationally, the repository is used in this order:

1. Open or update the governance source files.
2. Validate that the repository is internally consistent.
3. Generate governance artifacts and reports.
4. Render `Policy` and `Directive`.
5. Review the status viewer and reports.
6. Run tests and policy checks.
7. If needed, run the demo environment.
8. Review results and commit changes.

The rest of this guide explains each step in detail.

## Step 1: Understand What You Are Editing

Before changing anything, know where each type of information lives.

### Controls

Files in `model/controls/` contain the structured governance requirements.

Examples:

- `model/controls/dscb-l1.yaml`
- `model/controls/dscb-l2.yaml`
- `model/controls/dscb-l3.yaml`
- `model/controls/dscb-gov.yaml`

### Governance Documents

These define the higher-level governance structure:

- `docs/governance/devsecops-policy.md`
- `docs/governance/devsecops-directive.md`
- `model/documents/governance-documents.yaml`
- `model/documents/governance-document-rendering.yaml`

### Platform Capabilities

These describe which platform functions support the controls:

- `model/platform/platform-capabilities.yaml`
- `model/platform/pra-levels.yaml`

### Traceability

These files explain how things relate:

- `model/traceability/control-to-platform.yaml`
- `model/traceability/document-to-control.yaml`

### Rules

Executable governance checks live here:

- `policies/opa/`

### Outputs

Generated artifacts are written here:

- `generated/xlsx/`
- `generated/reports/`
- `generated/documents/`
- `generated/viewer/`
- `generated/demo/`

## Step 2: Make Your Governance Change

Now edit the source files you actually want to change.

Typical examples:

- change a control requirement in `model/controls/`
- update `Policy` or `Directive` text in `docs/`
- add or adjust a platform capability in `model/platform/`
- change traceability in `model/traceability/`
- update approval or waiver logic in `model/waivers/`
- update OPA rules in `policies/opa/`

### What this step does

This step changes the **governance source of truth**.

At this point nothing has been validated or regenerated yet.

## Step 3: Validate The Repository

Run:

```bash
python3 scripts/validate_governance_repo.py
```

### What this step does

This command checks whether the repository still makes sense after your change.

It validates things such as:

- control structure,
- traceability references,
- known evidence types,
- known platform capabilities,
- governance document references,
- OPA rule availability and syntax.

### What you should expect

If everything is fine, you should see:

```text
Validation passed
```

If you see warnings about `jsonschema`, the repo still works, but local schema validation is being skipped because the Python package is not installed.

## Step 4: Generate The Core Governance Reports

Run:

```bash
python3 scripts/generate_traceability_csv.py
python3 scripts/generate_document_control_matrix.py
python3 scripts/generate_open_gap_report.py
```

### What this step does

These scripts convert the governance source model into reviewable artifacts.

### What each script creates

#### `generate_traceability_csv.py`

Creates:

- `generated/xlsx/traceability_matrix.csv`

Use it to understand:

- which controls map to which platform capabilities,
- which evidence is expected,
- which controls are policy candidates,
- which authority documents apply.

#### `generate_document_control_matrix.py`

Creates:

- `generated/xlsx/document_control_matrix.csv`
- `generated/reports/document-control-matrix.md`

Use it to understand:

- which governance documents authorize which controls,
- how `Policy`, `Directive`, and `Standards` connect to the detailed requirements.

#### `generate_open_gap_report.py`

Creates:

- `generated/xlsx/open_gap_report.csv`
- `generated/reports/open-gap-report.md`

Use it to understand:

- what is still incomplete,
- what remains only a draft,
- what should be automated next,
- where governance follow-up is needed.

## Step 5: Render Policy And Directive

Run:

```bash
python3 scripts/render_governance_documents.py
```

### What this step does

This command creates review-ready files from the maintained `Policy` and `Directive`.

### What it creates

- `generated/documents/devsecops-pol-001.rendered.md`
- `generated/documents/devsecops-pol-001.html`
- `generated/documents/devsecops-dir-001.rendered.md`
- `generated/documents/devsecops-dir-001.html`

### What you use them for

These are the files you can show to reviewers, governance stakeholders, or use as intermediate deliverables for later DOCX/PDF rendering.

## Step 6: Generate The Status Viewer

Run:

```bash
python3 scripts/generate_status_viewer.py
```

### What this step does

This creates a static HTML dashboard that summarizes the current state of the repository.

### What it creates

- `generated/viewer/status-viewer.html`

### What you see there

The viewer shows:

- current governance document status,
- number of controls,
- number of policy candidates,
- current open gaps,
- selected traceability and authority mappings,
- links to generated reports and rendered documents.

## Step 7: Run The Automated Tests

Run:

```bash
python3 -m unittest discover -s tests
```

### What this step does

This checks whether the repository scripts still work as expected.

The tests cover things like:

- validation,
- report generation,
- document rendering,
- status viewer generation,
- demo execution.

### What success looks like

You should see something like:

```text
Ran 9 tests in ...
OK
```

## Step 8: Check The OPA Rules Directly

Run:

```bash
opa check policies/opa
```

### What this step does

This verifies the syntax and loadability of the OPA/Rego rules.

Use this especially when you changed files in `policies/opa/`.

## Step 9: Run The Demo Environment

Run:

```bash
python3 scripts/run_demo.py
```

### What this step does

This runs a complete end-to-end demonstration.

It:

- validates the repo,
- regenerates the governance artifacts,
- evaluates a compliant release candidate,
- evaluates a non-compliant release candidate,
- writes demo summaries.

### What it creates

- `generated/demo/demo-run.md`
- `generated/demo/green-summary.json`
- `generated/demo/green-summary.md`
- `generated/demo/red-summary.json`
- `generated/demo/red-summary.md`

### What you learn from it

You can immediately demonstrate:

- a passing governance case,
- a failing governance case,
- which OPA rules trigger in the failing scenario.

## Step 10: Review The Results

At this point, open the most important outputs:

- `generated/reports/open-gap-report.md`
- `generated/reports/document-control-matrix.md`
- `generated/viewer/status-viewer.html`
- `generated/documents/devsecops-pol-001.html`
- `generated/documents/devsecops-dir-001.html`
- `generated/demo/demo-run.md`

### What this step does

This is the operational review step.

You now decide:

- Is the governance change correct?
- Did any new gaps appear?
- Did the Policy or Directive rendering still look right?
- Did any policy checks fail?
- Does the demo still behave as expected?

## Step 11: Commit And Push

If the results are correct, commit your changes:

```bash
git status
git add .
git commit -m "Describe the governance change"
git push origin main
```

### What this step does

This makes the governance change operationally visible and reproducible for everyone else.

## Fast Daily Command Sequence

If you just want the normal operational sequence, use:

```bash
python3 scripts/validate_governance_repo.py
python3 scripts/generate_traceability_csv.py
python3 scripts/generate_document_control_matrix.py
python3 scripts/generate_open_gap_report.py
python3 scripts/render_governance_documents.py
python3 scripts/generate_status_viewer.py
python3 -m unittest discover -s tests
opa check policies/opa
```

## Full Demonstration Sequence

If you want to demonstrate the repository end-to-end, use:

```bash
python3 scripts/run_demo.py
```

## In One Sentence

Operationally, this repository is used by **editing governance sources, validating them, generating artifacts, rendering documents, reviewing the viewer and reports, testing the automation, and then publishing the resulting governance state**.
