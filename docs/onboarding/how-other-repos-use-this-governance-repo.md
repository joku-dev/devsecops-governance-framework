# How Other Repositories Use This Governance Repo

## Why This Document Exists

Many users understand how to work **inside** this repository, but not yet how another software project would **use** it operationally.

This document explains exactly that.

## The Core Idea

This repository contains the governance logic:

- control definitions,
- policy and directive content,
- traceability mappings,
- OPA rules,
- validation scripts,
- report generators,
- viewer generation.

A normal software project repository does **not** usually contain all of that.

So if another team wants to use this governance model, their pipeline must also make this repository available.

## Short Answer

Yes:

If another repository wants to use this governance model, it must usually do one of these things:

1. clone this repository in addition to the application repository, or
2. consume generated governance artifacts that were built from this repository.

Today, the first option is the most direct and realistic one.

## The Two-Repository Model

In practice, there are usually two repositories:

### 1. Application Repository

This is the actual project under development.

Examples:

- a software component,
- a platform service,
- a containerized application,
- a software factory project.

This repository contains:

- source code,
- build configuration,
- SBOM generation,
- scan results,
- deployment metadata,
- pipeline logic.

### 2. Governance Repository

This repository, `devsecops-governance-framework`, contains:

- the governance model,
- the control baseline,
- the OPA rules,
- the validation scripts,
- the reporting logic,
- the status viewer,
- the demo environment.

## What Happens In A Real Pipeline

The application pipeline typically performs these steps:

1. check out the application repository,
2. check out this governance repository,
3. generate or collect governance-relevant input from the application repository,
4. run governance validation and policy checks using this repository,
5. publish the resulting reports or gate the pipeline.

## Step-By-Step Example

Assume:

- application repository: `sample-app`
- governance repository: `devsecops-governance-framework`

### Step 1: Check Out Both Repositories

Example:

```bash
git clone <application-repo-url> sample-app
git clone <governance-repo-url> devsecops-governance-framework
```

### What this step does

It makes both the application and the governance logic available in the same pipeline workspace.

Without this governance repository, the pipeline would not have:

- the rules,
- the validators,
- the report generators,
- the governance documents.

## Step 2: Build Or Collect Governance Input From The Application Repo

The application repository is expected to produce or expose information such as:

- branch protection settings,
- SBOM presence,
- vulnerability scan results,
- artifact integrity metadata,
- dependency source information,
- IaC metadata,
- waiver information.

This information is then transformed into a JSON input for OPA.

## Example Input

This repository already contains an example input:

- `policies/example-input.release-candidate.json`

In a real project, the equivalent input would be generated from the application repository and its pipeline results.

## Step 3: Validate The Governance Repository Itself

Before using the governance rules, the pipeline should validate the governance repository:

```bash
cd devsecops-governance-framework
python3 scripts/validate_governance_repo.py
python3 -m unittest discover -s tests
opa check policies/opa
```

### What this step does

It ensures that the governance repository itself is healthy before it is trusted as a gate.

This protects the application pipeline from using:

- broken rules,
- invalid traceability,
- inconsistent governance metadata,
- failing generation scripts.

## Step 4: Evaluate The Application Against Governance Rules

Now the pipeline evaluates the application-specific input against the OPA rules.

Example:

```bash
opa eval -f pretty \
  -d devsecops-governance-framework/policies/opa \
  -i sample-app/generated/release-candidate.json \
  'data.devsecops.branch_protection.deny'
```

The same pattern can be used for:

- `sbom`
- `vulnerability_gate`
- `artifact_integrity`
- `access_control`
- `dependency_source_control`
- `iac`
- `artifact_signing`
- `pipeline_security_gates`
- `waiver_validity`

### What this step does

It checks whether the application repository complies with the governance rules defined here.

## Step 5: Generate Governance Artifacts For Review

The pipeline can also generate the governance artifacts from this repository:

```bash
python3 scripts/generate_traceability_csv.py
python3 scripts/generate_document_control_matrix.py
python3 scripts/generate_open_gap_report.py
python3 scripts/render_governance_documents.py
python3 scripts/generate_status_viewer.py
```

### What this step does

It creates:

- reviewable matrices,
- gap reports,
- rendered `Policy` and `Directive`,
- the governance status viewer.

These are useful for governance boards, platform owners, audit, and compliance reviews.

## Step 6: Decide What The Pipeline Should Do With The Result

There are usually two operational modes.

### Mode A: Advisory

The pipeline runs governance checks and publishes reports, but does not block delivery.

This is useful during pilot adoption.

### Mode B: Enforcing

The pipeline fails if governance checks fail.

This is useful once the organization is confident that:

- the governance model is stable,
- the input model is stable,
- teams understand the checks,
- waivers and exceptions are operationally defined.

## The Simplest Realistic Pipeline Pattern

This is the easiest real-world usage model:

1. the application pipeline checks out both repositories,
2. the application pipeline generates a release-candidate input JSON,
3. the pipeline runs OPA rules from this repository,
4. the pipeline publishes the results,
5. the pipeline optionally fails if denies are returned.

## Example Pseudo Pipeline

```bash
git clone <application-repo-url> sample-app
git clone <governance-repo-url> devsecops-governance-framework

cd devsecops-governance-framework
python3 scripts/validate_governance_repo.py
python3 -m unittest discover -s tests
opa check policies/opa

opa eval -f pretty \
  -d policies/opa \
  -i ../sample-app/generated/release-candidate.json \
  'data.devsecops.vulnerability_gate.deny'

python3 scripts/generate_open_gap_report.py
python3 scripts/generate_status_viewer.py
```

## When The Application Repo Does Not Want To Clone This Repo

That is possible later, but requires a more mature setup.

For example:

- publish OPA bundles,
- publish versioned governance artifacts,
- publish pre-rendered standards and reports,
- consume them through package or artifact feeds.

That is a more advanced target model.

Today, the most understandable and operationally safe pattern is still:

**clone the governance repository together with the application repository.**

## Operational Recommendation

For now, use this repository operationally in other projects like this:

1. treat this repository as the central governance source,
2. clone it in the application pipeline,
3. generate application input in the application repository,
4. evaluate governance from this repository against that input,
5. publish the resulting reports and status viewer artifacts.

## One-Sentence Summary

Another repository uses this governance repository by **checking it out alongside the application code and then executing the validation, policy, reporting, and viewer scripts from this repository against application-specific pipeline input**.
