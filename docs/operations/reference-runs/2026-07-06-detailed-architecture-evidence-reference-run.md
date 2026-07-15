# Detailed Architecture Evidence Reference Run

Date: 2026-07-06

## Purpose

This reference run demonstrates the tool-neutral, report-only detailed architecture evidence path.

It verifies that:

- application repositories can declare neutral detailed evidence types
- the collector maps detailed evidence to current coarse evidence areas
- the architecture release input contains `architecture.detailed_evidence`
- the governance report renders detailed evidence without changing OPA gate semantics
- no new blocking gate is introduced by detailed evidence alone

## Inputs

The run used the app architecture evidence template:

```text
pipeline-baseline/templates/app-architecture-evidence/.governance/architecture/
```

The template included both current coarse evidence and detailed neutral evidence:

```text
solution_baseline
release_compatibility_declaration
security_evidence
resilience_evidence
operation_evidence
feedback_evidence
threat_model
interface_contract
deployment_manifest
model_based_architecture
```

No vendor-specific architecture modeling tool was required.

## Commands

```bash
tmpdir=$(mktemp -d)
cp -R pipeline-baseline/templates/app-architecture-evidence/.governance "$tmpdir/.governance"
mkdir -p "$tmpdir/docs"
printf 'Architecture with REST API endpoint, ownership, model export and deployment context.\n' > "$tmpdir/docs/ARCHITECTURE.md"
printf 'Deployment uses compose, health checks, rollback and runtime logs.\n' > "$tmpdir/docs/DEPLOYMENT.md"

python3 scripts/collect_architecture_release_input.py \
  --repo "$tmpdir" \
  --output "$tmpdir/architecture-release-input.json" \
  --release-id detailed-evidence-reference \
  --baseline example-solution-baseline

python3 scripts/generate_architecture_governance_report.py \
  --input "$tmpdir/architecture-release-input.json" \
  --output-json "$tmpdir/architecture-governance-report.json" \
  --output-md "$tmpdir/architecture-governance-report.md"
```

## Observed Result

```text
marker assessments: 32
declared detailed evidence types: 10
detailed_evidence.report_only: true
gate count: 4
finding count: 24
Markdown report contains Detailed Evidence section: true
```

The finding count is expected because the template evidence files are intentionally `draft` unless an application team reviews and approves them.

## Interpretation

The run proves that detailed evidence can be introduced safely before Enterprise Architecture decides which types should become report-only expectations or blocking gates.

Detailed evidence currently improves visibility and can strengthen existing coarse areas such as:

| Detailed type | Current coarse area |
|---|---|
| `threat_model` | `security_evidence` |
| `interface_contract` | `release_compatibility_declaration` |
| `deployment_manifest` | `deployment_evidence` |
| `model_based_architecture` | `solution_baseline` |

## Guardrails

This run did not:

- introduce a new blocking OPA rule
- change release baseline semantics
- require a vendor-specific modeling tool
- make model-based architecture mandatory for all systems

## Follow-Up

The next safe adoption step is to keep collecting these fields in CI artifacts and discuss the taxonomy with Enterprise Architecture before promoting any detailed type to a blocking expectation.
