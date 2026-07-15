# Detailed Architecture Evidence Adoption Guide

Status: draft / report-only adoption guidance

## Purpose

This guide explains how an application team can start providing detailed architecture evidence without changing release gates.

Detailed evidence is tool-neutral and report-only unless a future approved governance baseline says otherwise.

## Starting Point

Copy the template folder into the application repository:

```text
pipeline-baseline/templates/app-architecture-evidence/.governance/architecture/
```

Target application repository structure:

```text
.governance/architecture/
  solution-baseline.json
  release-compatibility-declaration.json
  security-evidence.json
  resilience-evidence.json
  operation-evidence.json
  feedback-evidence.json
  threat-model.json
  interface-contract.json
  deployment-manifest.json
  model-based-architecture.json
```

## Coarse Versus Detailed Evidence

| Layer | Example | Current behavior |
|---|---|---|
| Coarse evidence | `security_evidence` | Existing gate input. |
| Detailed evidence | `threat_model` | Report-only detail mapped to a coarse area. |

Detailed evidence appears in:

```text
architecture.detailed_evidence
```

The architecture governance report renders it under:

```text
Detailed Evidence
Report-Only Advisories
```

Report-only advisories are context-sensitive. A missing detailed evidence type is recommended only when matching coarse evidence exists or architecture markers indicate that the topic is relevant.

## Recommended Minimal Detailed Evidence

| Evidence type | Why it helps |
|---|---|
| `threat_model` | Makes security assumptions, mitigations, and residual risks reviewable. |
| `interface_contract` | Makes interface ownership, compatibility, and versioning explicit. |
| `deployment_manifest` | Links runtime configuration and deployment assumptions to architecture governance. |
| `model_based_architecture` | Provides model-based evidence for complex systems without mandating a vendor tool. |

## Status Values

| Status | Meaning |
|---|---|
| `draft` | Evidence exists but is not accepted for gate satisfaction. |
| `reviewed` | Evidence has been reviewed, but is not yet approved. |
| `approved` | Evidence is accepted for the relevant coarse evidence area. |

## Example

```json
{
  "evidence_type": "threat_model",
  "status": "draft",
  "owner": "Security Architect",
  "summary": "Tool-neutral threat model evidence for architecture review.",
  "evidence_refs": [
    "docs/ARCHITECTURE.md",
    "docs/DEPLOYMENT.md"
  ],
  "known_limitations": [
    "Template placeholder; not approved evidence until reviewed."
  ],
  "follow_up_actions": []
}
```

## CI Flow

The application CI should run the architecture collector:

```bash
python3 governance/scripts/collect_architecture_release_input.py \
  --repo . \
  --output governance/generated/app/architecture-release-input.json \
  --release-id "$RELEASE_ID" \
  --baseline "$SOLUTION_BASELINE"
```

Then generate the report:

```bash
python3 governance/scripts/generate_architecture_governance_report.py \
  --input governance/generated/app/architecture-release-input.json \
  --output-json governance/generated/app/architecture-governance-report.json \
  --output-md governance/generated/app/architecture-governance-report.md
```

Archive these files as CI artifacts.

## Adoption Rule

Start with `draft` or `reviewed`.

Move to `approved` only when the accountable owner and reviewer agree that the evidence is correct and current.

Do not treat missing detailed evidence as release-blocking until Enterprise Architecture has approved the rule, exception path, and rollout plan.
