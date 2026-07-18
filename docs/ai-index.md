# AI Index

## Purpose

This index helps AI agents and human maintainers find the right files before changing the repository.

Use it as the first navigation point after `AGENTS.md`.

## Fast Orientation

| Need | Read first |
|---|---|
| Understand the repository | `README.md`, `docs/official-entrypoints.md` |
| Understand the current as-built Governance-as-Code system architecture | `docs/governance/architecture/governance-as-code-system-architecture.md` |
| Understand foundation, direction, and architectural guardrails | `docs/foundation/01_VISION.md`, `docs/foundation/02_CONSTITUTION.md`, `docs/foundation/03_ARCHITECTURE_PRINCIPLES.md`, `docs/foundation/05_CURRENT_DIRECTION.md` |
| Run the live demo | `docs/demos/demo-end-to-end-governance.md` |
| Understand current ha-CPsWMS status | `docs/operations/status/ha-cpswms-governance-validation-status.md`, `docs/demos/ha-cpswms-architecture-governance-results.md` |
| Understand source-document lineage | `generated/reports/source-lineage-report.md` |
| Classify a new artifact before adding it | `docs/operations/processes/new-artifact-intake-process.md` |
| Add a new artifact safely | `docs/operations/guides/how-to-add-a-new-artifact.md` |
| Intake updated input documents | `docs/governance/governance-change-lifecycle.md`, `docs/operations/processes/source-document-intake-process.md`, `docs/operations/processes/source-document-intake-review-operating-model.md`, `model/documents/source-document-register.yaml` |
| Understand ADO and DevSecOps-as-Code as one system | `docs/governance/architecture/ado-devsecops-integrated-governance-model.md` |
| Explain the repository as an answer to software industrialisation problems | `docs/governance/architecture/software-industrialisation-problem-capability-map.md` |
| Compare governance with central repository versus without central repository | `docs/governance/architecture/governance-repository-architecture-comparison.md` |
| Classify documentation and plan safe docs restructuring | `docs/operations/planning/document-structure-model.md` |
| Audit the current documentation structure after migrations | `docs/operations/planning/document-structure-audit.md` |
| Understand organisational DevSecOps governance responsibilities | `docs/governance/devsecops-governance-organisational-role-model.md` |
| Understand source update impact | `generated/reports/governance-change-impact.md` |
| Review the harmonized standards-requirements candidate | `docs/governance/review-packets/CISO-REQ-SRC-001/README.md`, `docs/governance/review-packets/CISO-REQ-SRC-001/harmonized-requirements-candidate.md`, `docs/governance/review-packets/CISO-REQ-SRC-001/ciso-review-brief.md`, `model/requirements/harmonized-devsecops-requirements.yaml`, `model/traceability/harmonized-requirements-to-maturity-levels.yaml`, `generated/reports/harmonized-requirements-coverage.md`, `generated/reports/harmonized-requirements-maturity.md` |
| Assess architecture source replacements | `generated/reports/architecture-source-replacement-assessment.md` |
| Route reviews by role | `docs/governance/governance-roles-and-agent-profiles.md` |
| Use model-neutral agent contracts | `.agents/roles/`, `.agents/routing/governance-agent-routing.yaml`, `.agents/skills/`, `docs/operations/agents/agent-system-usage.md` |
| Use Codex agent adapters | `.codex/agents/`, `.github/codex/prompts/`, `docs/operations/agents/agent-system-usage.md` |
| Check deterministic agent routing | `docs/operations/agents/agent-harness-usage.md`, `tests/agent_harness/` |
| Inspect agent usage | `docs/operations/agents/agent-usage-snapshot-latest.md`, `generated/agent-usage/agent-usage-summary.json` |
| Understand DevSecOps baseline releases | `docs/releases/index.md`, `docs/releases/l1-baseline-v1.1.3.md` |
| Understand architecture baseline releases | `docs/releases/architecture-baseline-l1-v0.1.0.md` |
| Understand intake and viewer | `docs/operations/evidence/governance-result-intake-and-viewer-usage.md` |
| Operate Evidence- und Governance-Hardening | `docs/operations/guides/evidence-and-governance-hardening-guide.md` |
| Operate the vulnerability-scan collector pilot | `docs/operations/evidence/vulnerability-scan-collector-usage.md`, `scripts/collect_vulnerability_scan_evidence.py` |
| Understand portfolio adoption reporting | `docs/operations/status/portfolio-adoption-reporting.md`, `governance/portfolio-adoption-reporting.yaml` |
| Implement Bamboo 12.1.9 adapter | `docs/operations/adapters/bitbucket-bamboo-governance-adapter.md`, `pipeline-baseline/templates/bamboo/bamboo-specs/bamboo.yaml` |
| Understand report-only versus blocking | `docs/operations/processes/operational-governance-enforcement-options.md` |
| Work as an AI agent | `AGENTS.md`, `docs/operations/ai-working-rules.md` |

## Foundation Documents

The foundation documents define the strategic and architectural context for this repository. They are helpful before changing governance structure, agent behavior, adapter strategy, or portfolio-level reporting.

| File | Purpose |
|---|---|
| `docs/foundation/01_VISION.md` | Engineering Governance Runtime vision and target outcome |
| `docs/foundation/02_CONSTITUTION.md` | Stable operating principles and decision constraints |
| `docs/foundation/03_ARCHITECTURE_PRINCIPLES.md` | Architecture principles for capability separation and runtime governance |
| `docs/foundation/04_REFERENCE_ARCHITECTURE.md` | Reference architecture context for the repository structure |
| `docs/foundation/05_CURRENT_DIRECTION.md` | Current milestone direction and explicit scope boundaries |
| `docs/foundation/06_KEYNOTE_STORY.md` | Narrative explanation for stakeholder communication |
| `docs/foundation/07_AI_CONTEXT.md` | AI-agent working context and decision priorities |
| `docs/foundation/08_GLOSSARY.md` | Shared terminology |

These files are architectural and strategic guardrails. They do not replace approved policy, directive, standards, released baselines, source-document registers, or recorded governance decisions.

## Source Documents

The public source placeholders live in:

```text
docs/governance/source-documents/
```

The original source documents are withheld from the public repository. The files below preserve lineage and review state only.

Current public placeholders:

| Source document | Main derived area |
|---|---|
| `DSCB-STD-SRC-001.public.md` | DevSecOps controls and OPA policy candidates |
| `PRA-STD-SRC-001.public.md` | Platform levels and pipeline baseline |
| `DEVSECOPS-DIR-SRC-001.public.md` | Governance directive |
| `DEVSECOPS-POL-SRC-001.public.md` | Governance policy |
| `ARCH-SDD-SRC-001.public.md` | Architecture runtime governance |

When adding or changing derived governance artifacts, update or validate lineage:

```bash
python3 scripts/generate_source_lineage_report.py
python3 scripts/validate_governance_repo.py
```

Use the lifecycle and template for future updates:

```text
docs/governance/governance-change-lifecycle.md
docs/governance/change-requests/TEMPLATE.md
model/documents/source-document-register.yaml
```

For new documents that may match or replace an existing source, register them as `candidate` first and use `candidate_replacement_for` plus `similarity_assessment`.

Use role profiles to decide who should review the change:

```text
docs/governance/governance-roles-and-agent-profiles.md
```

Generate the current source-document impact overview:

```bash
python3 scripts/generate_governance_change_impact_report.py
```

Generate the architecture source replacement assessment:

```bash
python3 scripts/generate_architecture_source_replacement_assessment.py
```

For human intake reviews, use the operating model and review packet:

```text
docs/operations/processes/source-document-intake-review-operating-model.md
generated/reports/source-document-intake-status.md
generated/reports/source-document-intake-review-briefs.md
generated/reports/source-document-requirement-delta.md
```

The Intake Agent may prepare evidence and options, but the final source
decision must be recorded by a human reviewer in a governance change request.

## DevSecOps Governance Map

| Concern | Files |
|---|---|
| Controls | `model/controls/dscb-l1.yaml`, `model/controls/dscb-l2.yaml`, `model/controls/dscb-l3.yaml`, `model/controls/dscb-gov.yaml` |
| Coverage | `model/controls/control-coverage.yaml`, `generated/reports/control-coverage-report.md` |
| Evidence | `model/evidence/evidence-types.yaml`, `model/evidence/evidence-trust-model.yaml`, `model/evidence/evidence-freshness-policies.yaml`, `model/evidence/evidence-collector-contract.yaml`, `docs/operations/evidence/governance-evidence-contract.md`, `docs/operations/evidence/evidence-trust-model.md`, `docs/operations/evidence/evidence-collector-contract.md`, `docs/operations/evidence/vulnerability-scan-collector-usage.md` |
| Pipeline placement | `pipeline-baseline/` |
| OPA policies | `policies/opa/*` |
| Current release | `releases/l1/v1.1.3/`, `docs/releases/l1-baseline-v1.1.3.md` |
| Reusable workflow | `.github/workflows/devsecops-baseline-l1-v1.1.3.yml` |

Typical validation:

```bash
python3 scripts/validate_governance_repo.py
python3 -m unittest discover -s tests
```

## Architecture Runtime Governance Map

| Concern | Files |
|---|---|
| Runtime addendum | `docs/governance/architecture/runtime-governance-addendum.md` |
| Runtime transformation | `docs/governance/architecture/runtime-governance-transformation.md` |
| Levels | `architecture/arch-l1.yaml`, `architecture/arch-l2.yaml`, `architecture/arch-l3.yaml`, `architecture/arch-gov.yaml` |
| Markers | `architecture/quality-markers.yaml` |
| Guardrails and gates | `architecture/guardrails.yaml`, `architecture/review-gates.yaml` |
| Remediation | `architecture/remediation-actions.yaml` |
| OPA policies | `policies/opa/architecture_*.rego` |
| Schemas | `schemas/architecture-release-candidate.schema.json`, `schemas/app-architecture-evidence.schema.json` |
| Current release | `releases/architecture/l1/v0.1.0/`, `docs/releases/architecture-baseline-l1-v0.1.0.md` |
| Reusable workflow | `.github/workflows/architecture-baseline-l1-v0.1.0.yml` |

Typical validation:

```bash
python3 scripts/validate_runtime_governance.py
python3 -m unittest discover -s tests
```

## Viewer And Status Map

| Concern | Files |
|---|---|
| DevSecOps result index | `status/repository-results-index.json` |
| DevSecOps result history | `status/results/` |
| Architecture result index | `status/architecture-results-index.json` |
| Architecture result history | `status/architecture-results/` |
| Viewer generator | `scripts/generate_status_viewer.py` |
| Viewer output | `generated/viewer/status-viewer.html` |
| Intake docs | `docs/operations/evidence/governance-result-intake-and-viewer-usage.md` |
| Vulnerability collector guide | `docs/operations/evidence/vulnerability-scan-collector-usage.md` |
| Typed evidence result index | `status/typed-evidence-results-index.json` |
| Typed evidence result history | `status/typed-evidence-results/` |
| Typed evidence intake | `scripts/intake_evidence_trust_github_actions_run.py` |
| Governance graph schema | `schemas/governance-graph.schema.json` |
| Governance graph generator | `scripts/generate_governance_graph.py` |
| Governance graph output | `generated/graph/governance-graph.json` |
| Governance graph guide | `docs/operations/status/governance-intelligence-graph-viewer.md` |
| Append-only ledger and replay logic | `scripts/lib/result_ledger.py` |
| Replay triage guide | `docs/operations/evidence/replay-triage.md` |
| Replay triage generator and output | `scripts/generate_replay_triage_report.py`, `generated/reports/replay-triage.json` |
| Intake conflict quarantine | `status/intake-conflicts/` |
| Intake conflict schema | `schemas/intake-conflict.schema.json` |
| Append-only ledger and replay logic | `scripts/lib/result_ledger.py` |
| Intake conflict quarantine | `status/intake-conflicts/` |
| Intake conflict schema | `schemas/intake-conflict.schema.json` |
| Agent usage snapshot | `docs/operations/agents/agent-usage-snapshot-latest.md` |
| Agent usage summary | `generated/agent-usage/agent-usage-summary.json` |
| Evidence collection attempts | `schemas/evidence-collection-attempt.schema.json`, `scripts/record_collection_attempt.py`, `status/collection-attempts/` |
| Intake operation telemetry | `docs/operations/evidence/intake-operation-telemetry.md`, `schemas/intake-operation-event.schema.json`, `scripts/record_intake_event.py`, `status/intake-events/` |
| Intake Health projection | `docs/operations/evidence/intake-health-projection.md`, `schemas/intake-health.schema.json`, `scripts/generate_intake_health.py`, `status/intake-health.json` |
| Multi-consumer readiness | `docs/operations/status/multi-consumer-readiness.md`, `schemas/multi-consumer-readiness.schema.json`, `scripts/generate_multi_consumer_readiness.py`, `generated/reports/multi-consumer-readiness.json` |
| Blocking readiness | `docs/operations/status/blocking-readiness.md`, `model/enforcement/blocking-readiness.yaml`, `scripts/generate_blocking_readiness.py`, `generated/reports/blocking-readiness.json` |
| Blocking mode alignment | `docs/operations/status/blocking-mode-alignment.md`, `model/enforcement/blocking-mode-alignment.yaml`, `scripts/generate_blocking_mode_alignment.py`, `generated/reports/blocking-mode-alignment.json` |
| Evidence attestation pilot | `docs/operations/evidence/evidence-attestation-pilot.md`, `model/evidence/evidence-trust-roots.yaml`, `schemas/evidence-attestation.schema.json`, `scripts/verify_evidence_attestation.py`, `generated/reports/evidence-attestation-pilot.json` |
| Controlled collection retry | `.github/workflows/retry-collection-attempt.yml`, `scripts/prepare_collection_attempt_retry.py` |
| Collection-attempt lifecycle projection | `scripts/generate_status_viewer.py`, `generated/viewer/status-viewer.html` |
| Evidence agent provenance | `schemas/evidence-agent-provenance.schema.json`, `scripts/record_evidence_agent_provenance.py`, `scripts/validate_evidence_agent_provenance.py`, `status/evidence-agent-provenance/` |

Regenerate viewer:

```bash
python3 scripts/generate_governance_graph.py
python3 scripts/generate_status_viewer.py
```

## Demo Map

| Demo need | File |
|---|---|
| Full end-to-end demo | `docs/demos/demo-end-to-end-governance.md` |
| Consumer typed-evidence demo | `docs/demos/demo-consumer-typed-evidence-trust.md` |
| Typed-evidence presentation guide | `docs/demos/presentation-guide-typed-evidence-trust-de.md` |
| Architecture-only demo | `docs/demos/demo-ha-cpswms-runtime-governance.md` |
| Architecture result explanation | `docs/demos/ha-cpswms-architecture-governance-results.md` |
| DevSecOps historical demo guide | `docs/demos/demo-guide-2026-07-02-ha-cpswms.md` |
| Viewer | `generated/viewer/status-viewer.html` |

Current known-good ha-CPsWMS runs:

| Domain | Run | Expected |
|---|---:|---|
| DevSecOps Baseline | `29415015878` | pass, `16/16` controls |
| Architecture Runtime Governance | `29415015294` | PASS, `4/4` gates |

## Release Map

| Domain | Current release | Key files |
|---|---|---|
| DevSecOps L1 | `l1-baseline-v1.1.3` | `docs/releases/l1-baseline-v1.1.3.md`, `releases/l1/v1.1.3/` |
| Architecture L1 | `architecture-baseline-l1-v0.1.0` | `docs/releases/architecture-baseline-l1-v0.1.0.md`, `releases/architecture/l1/v0.1.0/` |

When creating a new release, update:

- release docs
- technical release package
- checksums
- reusable workflow or template if applicable
- source lineage
- README and official entrypoints if the release becomes the recommended baseline

## Before Committing

Run:

```bash
python3 scripts/validate_runtime_governance.py
python3 scripts/validate_governance_repo.py
python3 -m unittest discover -s tests
git status --short
```

Commit only intentional files. Do not add `.DS_Store`.
