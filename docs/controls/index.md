# Controls

## Purpose

This section explains how the control baseline is structured in this repository and how readers should interpret the machine-readable control files.

The authoritative control definitions live in:

- `model/controls/dscb-l1.yaml`
- `model/controls/dscb-l2.yaml`
- `model/controls/dscb-l3.yaml`
- `model/controls/dscb-gov.yaml`

## What A Control File Contains

Each control file contains:

- the baseline level
- the baseline name
- the required platform level
- the individual requirements

Each individual requirement usually contains:

- a unique requirement ID
- a domain
- a title
- a control objective
- the normative requirement text
- expected platform capabilities
- expected evidence
- verification method
- policy-as-code information
- waiver rules

Control automation coverage is tracked separately in:

- `model/controls/control-coverage.yaml`

## Current Baseline Layers

### `L1`

File:

- `model/controls/dscb-l1.yaml`

Current role:

- minimum operational DevSecOps baseline
- first released version available for downstream use
- strongest current practical onboarding target

Current size:

- `16` requirements

Typical topics:

- traceability
- source code integrity
- SBOM generation
- vulnerability scanning
- build process control

### `L2`

File:

- `model/controls/dscb-l2.yaml`

Current role:

- stronger maturity level beyond the initial operational rollout

### `L3`

File:

- `model/controls/dscb-l3.yaml`

Current role:

- strongest technical baseline in the current model
- includes stronger release and signing expectations

### `GOV`

File:

- `model/controls/dscb-gov.yaml`

Current role:

- governance-oriented controls that support the overall operating model

## Example Requirement Structure

Example from `L1`:

- `DSCB-L1-REQ-003`
- domain: `source_code_integrity`
- verification method: `automated`
- policy candidate: `true`

Operational meaning:

- the requirement is specific enough to be enforced or checked automatically
- it is a good candidate for policy-as-code
- it fits well into CI/CD gate logic

## How To Read A Control Requirement

When reading one requirement, use this order:

### Step 1

Read the `id`.

Example:

- `DSCB-L1-REQ-006`

This tells you:

- the baseline level
- that it is a requirement
- its unique position in the baseline

### Step 2

Read the `control_objective`.

This explains the reason behind the requirement.

### Step 3

Read the `requirement`.

This is the normative text that explains what must exist or happen.

### Step 4

Read `platform_capabilities`.

This tells you what a platform should provide to help satisfy the requirement.

### Step 5

Read `evidence`.

This tells you what proof is expected.

### Step 6

Read `verification`.

This tells you whether the requirement is checked:

- automatically
- manually
- or through a hybrid method

### Step 7

Read `policy_as_code`.

This tells you whether the repository is expected to translate the requirement into executable policy logic.

## How To Distinguish Control Types

Not every control is the same kind of thing.

In practice, controls often fall into these groups:

### Evidence-oriented controls

These require proof but are not always directly enforceable by code.

Example:

- traceability records
- approval records

### Gate-oriented controls

These are good candidates for CI/CD enforcement.

Example:

- branch protection
- SBOM existence
- vulnerability thresholds

### Governance-oriented controls

These describe who must decide, approve, or govern something.

Example:

- waiver authority
- approval responsibility

## How Controls Connect To The Rest Of The Repo

Controls do not stand alone.

They connect to:

- `model/platform/` for implementing platform capabilities
- `model/evidence/` for expected proof
- `model/traceability/` for mappings
- `policies/opa/` for executable gate logic
- `docs/governance/` for the authority and intent documents
- `model/controls/control-coverage.yaml` for the current automation status per control

## Automation Coverage Status

Each control also has a recorded automation coverage status in:

- `model/controls/control-coverage.yaml`

The allowed values are:

- `automated`
- `manual`
- `planned`
- `not_applicable`

These values mean:

### `automated`

The repository currently has machine-readable evaluator or policy logic for this control.

### `manual`

The control is intentionally handled through governance review, audit, or human evidence interpretation rather than CI/CD-style automation.

### `planned`

The control is a targeted next automation candidate, but the evaluator or evidence contract is not yet fully implemented.

### `not_applicable`

The control is outside the intended automation scope for this repository model.

## Coverage Prioritization

The prioritized current coverage view is generated into:

- `generated/reports/control-coverage-report.md`
- `generated/reports/control-coverage-report.json`

This report helps answer:

- which controls are already automated
- which controls still rely on manual review
- which controls should be automated next

## Step-By-Step: Inspect The L1 Baseline

### Step 1

Open the `L1` control file:

```bash
sed -n '1,260p' model/controls/dscb-l1.yaml
```

### Step 2

Look at the first few requirement IDs and domains.

### Step 3

Identify which controls are marked as `policy_as_code.candidate: true`.

### Step 4

Check whether the verification method is:

- `automated`
- `hybrid`
- or another value

### Step 5

Cross-check the relevant evidence types in:

```bash
sed -n '1,260p' model/evidence/evidence-types.yaml
```

## Step-By-Step: Decide Whether A Control Should Become Policy-As-Code

Use this checklist:

1. Is the requirement objectively testable?
2. Can the pipeline or platform provide machine-readable evidence?
3. Is pass/fail logic unambiguous?
4. Can the result be enforced without a human interpretation step?

If the answer is mostly yes, the control is a strong policy-as-code candidate.

## Practical Example

### Example: Branch Protection

Why it works well:

- the repository API can expose branch protection state
- direct push rules can be checked mechanically
- required review rules can be checked mechanically

That makes it a strong automated gate candidate.

### Example: Secure Coding Practices

Why it is harder:

- policy intent is clear
- but proving real secure coding behavior often needs multiple evidence sources
- human review and interpretation may still be needed

That makes it more likely to stay hybrid.

## How To Use This Section As A Beginner

Recommended reading order:

1. `model/controls/dscb-l1.yaml`
2. `docs/governance/policy-directive-baseline-verification-and-governance-as-code-explained.md`
3. `docs/platform/control-baseline-and-platform-architecture-relationship-explained.md`
4. `model/evidence/evidence-types.yaml`

## Recommended Next Document

After this page, read:

- `docs/platform/control-baseline-and-platform-architecture-relationship-explained.md`

That document explains how the platform is supposed to implement what the controls require.
