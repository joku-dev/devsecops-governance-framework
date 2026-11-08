# Technische Funktionsliste des Repositories

## Nachtrag: Dokument-Arbeitsplatz (GCR-2026-156)

Der [Dokument-Arbeitsplatz](governance-review-workbench.md) ergänzt
`scripts/workbench/workspace-navigation.js` für Hash-Routen, Fortsetzungsaktionen
und Stale-Hinweise sowie `.github/workflows/workbench-ui.yml` für isolierte
DOM-Regressionen. Damit umfassen die hier inventarisierten Produktionspfade
**167 Python-Dateien, 4 Shell-Dateien, 8 weitere Skript-/Workbench-Dateien,
30 Workflows und 15 OPA-Module**. Die datierten Ausgangstabellen und ihre
Commit-Links bleiben erhalten.

Der bestehende Workbench-Server liefert additive lesende Diagnosen und getrennte
historische Entscheidungszähler. HTML/CSS/Frontend führen vollständige Review-Seiten
mit Browsernavigation und Sitzungseingaben ein. `package.json`, `package-lock.json`
und `.node-version` pinnen ausschließlich die Entwicklungs-/CI-Tests;
`tests/workbench-*.test.cjs` und die Python-HTTP-Regressionen prüfen das Verhalten.
Öffentlicher Viewer, fachliche Quellen, Baselines und Enforcement erhalten keine
neue Funktion. Siehe [GCR-2026-156](../../governance/change-requests/GCR-2026-156-document-workspace.md).

## Nachtrag: nachvollziehbare Agentenreviews (GCR-2026-155)

Die Agentenreview-Erweiterung ergänzt zwei Produktionsmodule. Damit wächst die
Python-Dateimenge gegenüber dem unten gebundenen Stand von 165 auf **167**;
Shell-, Workflow-, OPA- und sonstige Skript-Dateimengen bleiben gleich. Der
folgende vollständige Ausgangskatalog mit seinen Commit-Links bleibt als
Quellstand erhalten. Die neuen Module und der geänderte Einstieg sind:

| Datei | Aufgabe |
|---|---|
| `scripts/lib/agent_routing.py` | Produktives Routing, Vertragsprüfung, Auswahlgründe und Validierungen aus neutralen Rollen; vom Harness importiert. |
| `scripts/lib/agent_review.py` | Vollständige Git-Scope-Ermittlung, private Review-Pläne und Abschlussprüfung gegen Revision, Index, Bytes, Verträge und deklarierte Ergebnisse. |
| `scripts/dispatch_governance_agents.py` | Bestehender Einstieg mit zusätzlicher Plan-/Ergebnisbedienung; startet keine Modelle oder Subagenten. |

Gemeinsames Protokoll: `.agents/review-protocol.yaml`.
[Bedienung und Aussagegrenzen](../agents/how-to-run-agent-review.md).

## Gebundener Ausgangskatalog

Inventarabgleich: **7. November 2026**, Quellstand `ae423f34f75451b70b1ebffc71ea3683e4763c52`.
Die Tabellen erfassen exakt die versionierten Python-, Shell-, JavaScript-,
HTML- und CSS-Dateien unter `scripts/`, Workflow-YAML unter
`.github/workflows/` sowie Rego unter `policies/opa/` an diesem Stand.
Nicht jede Datei ist eine öffentliche API. Der [fachliche Katalog](repository-function-catalog.md)
erklärt die weiterhin 22 Aufgabenbereiche. Die [Workbench-Anleitung](governance-review-workbench.md)
beschreibt den lokalen Einstieg.

Umfang: **165 Python-Dateien**, **4 Shell-Dateien**, **7 weitere Skript-/Workbench-Dateien**,
**29 Workflows** und **15 OPA-Module**. `apps/governance-viewer/` enthält
zusätzlich die öffentlichen Viewer-Assets; Modelle, Schemas, Vorlagen und Tests
werden als Verzeichnisse unten eingeordnet.

<!-- DOCS_REFRESH_INVENTORY:start -->
### PR #336: feat(workbench): resumable AXIOM document review workspace (`7a00a13fcb22`)

- `.github/workflows/workbench-ui.yml`
- `scripts/serve_governance_workbench.py`
- `scripts/workbench/app.js`
- `scripts/workbench/index.html`
- `scripts/workbench/style.css`
- `scripts/workbench/workspace-navigation.js`
<!-- DOCS_REFRESH_INVENTORY:end -->

## Python-Skripte und Bibliotheksmodule

| Datei | Aufgabe |
|---|---|
| [scripts/adapt_document_consistency_provider_response.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/adapt_document_consistency_provider_response.py) | Überführt neutrale Provider-Ausgaben in den autoritativen semantischen Review-Vertrag. |
| [scripts/assess_governance_repository_security.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/assess_governance_repository_security.py) | Collect and assess the security posture of the governance repository. |
| [scripts/check_lifecycle_personal_channel.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/check_lifecycle_personal_channel.py) | Check or replay a personal-channel probe; this command never posts a statement. |
| [scripts/check_public_artifact_hygiene.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/check_public_artifact_hygiene.py) | Reject configured private terms in public text and Office metadata. |
| [scripts/check_repo_governance_integration.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/check_repo_governance_integration.py) | Check whether a target repository appears to integrate governance CI. |
| [scripts/check_repository_onboarding_readiness.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/check_repository_onboarding_readiness.py) | Assess a repository before central governance baseline onboarding. |
| [scripts/collect_architecture_release_input.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/collect_architecture_release_input.py) | Collect a demo architecture release-readiness input from a target repo. |
| [scripts/collect_devsecops_release_input.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/collect_devsecops_release_input.py) | Collect DevSecOps release-readiness input from an application repository. |
| [scripts/collect_vulnerability_scan_evidence.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/collect_vulnerability_scan_evidence.py) | Collect normalized vulnerability evidence and derive report-only Trust. |
| [scripts/control_evaluation.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/control_evaluation.py) | Shared helpers for control-level governance evaluation reports. |
| [scripts/dispatch_governance_agents.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/dispatch_governance_agents.py) | Ermittelt Rollen und Skills aus geänderten Pfaden und protokolliert bei Auswahl deren Nutzung; führt selbst keinen fachlichen LLM-Review aus. |
| [scripts/evaluate_document_consistency_semantic_report.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/evaluate_document_consistency_semantic_report.py) | Bewertet einen validierten semantischen Bericht gegen einen begrenzten kuratierten Katalog. |
| [scripts/export_repository_sbom.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/export_repository_sbom.py) | Exportiert das GitHub-Dependency-Graph als commitgebundenes SPDX-SBOM-Artefakt; nur lesend und ohne Merge-Gate. |
| [scripts/generate_agent_usage_snapshot.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_agent_usage_snapshot.py) | Erzeugt JSON-/Markdown-Nutzungsübersichten aus dem Dispatch-Protokoll. |
| [scripts/generate_architecture_governance_report.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_architecture_governance_report.py) | Generate an architecture runtime governance report from OPA gate results. |
| [scripts/generate_architecture_results_index.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_architecture_results_index.py) | Aggregate Architecture Runtime Governance results into a central index. |
| [scripts/generate_architecture_source_replacement_assessment.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_architecture_source_replacement_assessment.py) | Assess architecture source document replacement candidates. |
| [scripts/generate_architecture_traceability_csv.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_architecture_traceability_csv.py) | Generate architecture runtime governance traceability CSV. |
| [scripts/generate_automation_report.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_automation_report.py) | Generate a Markdown report for automation coverage. |
| [scripts/generate_blocking_mode_alignment.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_blocking_mode_alignment.py) | Assess current enforcement modes against Blocking Readiness without changing them. |
| [scripts/generate_blocking_readiness.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_blocking_readiness.py) | Generate a report-only blocking-readiness decision aid. |
| [scripts/generate_control_coverage_report.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_control_coverage_report.py) | Generate a control automation coverage report. |
| [scripts/generate_control_evaluation_report.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_control_evaluation_report.py) | Generate a control-by-control evaluation report for a governance run input. |
| [scripts/generate_devsecops_governance_report.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_devsecops_governance_report.py) | Generate a DevSecOps governance report from OPA release-readiness results. |
| [scripts/generate_document_consistency_review_manifest.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_document_consistency_review_manifest.py) | Erstellt ein textfreies, commit- und hashgebundenes Manifest ausgewählter registrierter Quellen. |
| [scripts/generate_document_consistency_review_model.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_document_consistency_review_model.py) | Erstellt aus einem Quellenmanifest eine deterministische, textfreie Strukturaufnahme. |
| [scripts/generate_document_control_matrix.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_document_control_matrix.py) | Generate document-to-control authority reports from governance YAML. |
| [scripts/generate_end_to_end_governance_report.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_end_to_end_governance_report.py) | Generate a combined architecture and DevSecOps governance report. |
| [scripts/generate_evidence_agent_provenance_index.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_evidence_agent_provenance_index.py) | Generate a deterministic index for explicit evidence-agent provenance. |
| [scripts/generate_governance_change_impact_report.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_governance_change_impact_report.py) | Generate a lightweight governance change impact report. |
| [scripts/generate_governance_compliance_result.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_governance_compliance_result.py) | Generate an extended governance compliance result artifact. |
| [scripts/generate_governance_graph.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_governance_graph.py) | Generate a deterministic read-only graph from governed repository artifacts. |
| [scripts/generate_governance_lifecycle_exceptions.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_governance_lifecycle_exceptions.py) | Generate a synthetic exception projection/report at an explicit evaluation instant. |
| [scripts/generate_governance_lifecycle_index.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_governance_lifecycle_index.py) | Generate a synthetic-only index from the complete immutable lifecycle ledger. |
| [scripts/generate_governance_lifecycle_overview.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_governance_lifecycle_overview.py) | Replay three separate synthetic histories into an explicit-time overview. |
| [scripts/generate_governance_lifecycle_pilot.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_governance_lifecycle_pilot.py) | Generate explicit-time synthetic CLG-04 projection and pilot report. |
| [scripts/generate_governance_lifecycle_viewer.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_governance_lifecycle_viewer.py) | Generate a standalone read-only viewer from the verified synthetic overview. |
| [scripts/generate_governance_traceability_csv.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_governance_traceability_csv.py) | Generate a flat governance traceability CSV for Policy and Directive requirements. |
| [scripts/generate_harmonized_requirements_maturity_report.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_harmonized_requirements_maturity_report.py) | Generate non-normative maturity decision support for harmonized requirements. |
| [scripts/generate_implemented_requirement_migration.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_implemented_requirement_migration.py) | Inventory active artifacts and propose requirement mappings for human review. |
| [scripts/generate_intake_health.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_intake_health.py) | Generate a report-only operational health projection from intake telemetry. |
| [scripts/generate_lifecycle_pilot_actions.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_lifecycle_pilot_actions.py) | Generate the separate action-validation projection; never publish official state. |
| [scripts/generate_lifecycle_pilot_validation.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_lifecycle_pilot_validation.py) | Generate the separate durable pilot validation projection from complete receipts. |
| [scripts/generate_multi_consumer_readiness.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_multi_consumer_readiness.py) | Generate a report-only proof that central intake isolates multiple consumers. |
| [scripts/generate_open_gap_report.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_open_gap_report.py) | Generate an open gap report for governance model follow-up. |
| [scripts/generate_operations_report.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_operations_report.py) | Read-only daily operational report; findings never authorize enforcement. |
| [scripts/generate_personal_channel_evidence.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_personal_channel_evidence.py) | Retained diagnostic channel captures and independent checks; never action consent. |
| [scripts/generate_personal_channel_probe.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_personal_channel_probe.py) | Render the bound personal statement for the appointed person to issue themselves. |
| [scripts/generate_pipeline_baseline_report.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_pipeline_baseline_report.py) | Generate a Markdown report for the CI/CD Pipeline Control Baseline. |
| [scripts/generate_pipeline_evidence.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_pipeline_evidence.py) | Generate normalized DevSecOps pipeline evidence for CI/CD adapters. |
| [scripts/generate_platform_context.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_platform_context.py) | Generate normalized CI/CD platform context from native environment variables. |
| [scripts/generate_portfolio_onboarding_status.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_portfolio_onboarding_status.py) | Generate a portfolio onboarding status report from the integration registry. |
| [scripts/generate_pra_requirement_platform_review.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_pra_requirement_platform_review.py) | Build the advisory PRA requirement-to-platform review packet. |
| [scripts/generate_replay_triage_report.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_replay_triage_report.py) | Explain stored replay checks without rewriting evidence or Trust records. |
| [scripts/generate_repository_results_index.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_repository_results_index.py) | Aggregate repository governance results into a central index. |
| [scripts/generate_source_document_intake_review_briefs.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_source_document_intake_review_briefs.py) | Generate source-document intake review briefs. |
| [scripts/generate_source_document_intake_status.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_source_document_intake_status.py) | Generate a source-document intake status report. |
| [scripts/generate_source_document_process_status.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_source_document_process_status.py) | Project the full source-intake process and authorized-source baseline gate. |
| [scripts/generate_source_document_requirement_delta.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_source_document_requirement_delta.py) | Generate requirement-level deltas for source-document replacement candidates. |
| [scripts/generate_source_lineage_report.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_source_lineage_report.py) | Generate source-document lineage report for governance artifacts. |
| [scripts/generate_status_viewer.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_status_viewer.py) | Generate a static governance status viewer. |
| [scripts/generate_traceability_csv.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_traceability_csv.py) | Generate a flat control traceability CSV from the YAML control library. |
| [scripts/generate_typed_evidence_results_index.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/generate_typed_evidence_results_index.py) | Aggregate typed Evidence Trust results without changing governance outcomes. |
| [scripts/import_harmonized_requirements_workbook.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/import_harmonized_requirements_workbook.py) | Create a public-neutral candidate mapping without publishing source text. |
| [scripts/intake_architecture_github_actions_run.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/intake_architecture_github_actions_run.py) | Intake a downstream Architecture Runtime Governance GitHub Actions run. |
| [scripts/intake_ci_artifact_bundle.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/intake_ci_artifact_bundle.py) | Intake platform-neutral CI artifact bundles into central status snapshots. |
| [scripts/intake_evidence_trust_github_actions_run.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/intake_evidence_trust_github_actions_run.py) | Intake and centrally reverify typed Evidence Trust from a GitHub Actions run. |
| [scripts/intake_github_actions_run.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/intake_github_actions_run.py) | Intake a downstream GitHub Actions governance run into central status. |
| [scripts/intake_governance_lifecycle_action.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/intake_governance_lifecycle_action.py) | Intake an explicit synthetic decision/remediation/closure/exception packet; never approve a real decision. |
| [scripts/intake_governance_lifecycle_observation.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/intake_governance_lifecycle_observation.py) | Append one explicitly synthetic GRS-002 packet to a local lifecycle ledger. |
| [scripts/intake_governance_result.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/intake_governance_result.py) | Create a normalized governance result snapshot from pipeline metadata. |
| [scripts/intake_ha_container_trust.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/intake_ha_container_trust.py) | Intake five complete ha-CPsWMS images and write separate vulnerability-scan and SBOM Trust snapshots from one successful mainline run. |
| [scripts/intake_lifecycle_pilot_action.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/intake_lifecycle_pilot_action.py) | Capture an action-bound personal statement into pilot validation; never post or execute it. |
| [scripts/intake_lifecycle_pilot_run.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/intake_lifecycle_pilot_run.py) | Collect fresh provider evidence into durable pilot validation; no live activation. |
| [scripts/intake_measured_l1.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/intake_measured_l1.py) | Aufnahme ausgewählter Rohartefakte eines erfolgreichen ha-CPsWMS-Messlaufs und der Anforderungszuordnung am exakten Commit |
| [scripts/intake_measured_security.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/intake_measured_security.py) | Nimmt echte Container-Scans mit Run-, Rohdatei- und Image-Prüfung auf. |
| [scripts/intake_staging_deployment_evidence.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/intake_staging_deployment_evidence.py) | Nimmt ein bereits autorisiertes Report-only-Staging-Bundle auf und gleicht es mit passenden gemessenen L1-Nachweisen ab; führt kein Deployment aus. |
| [scripts/lib/__init__.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/__init__.py) | Shared helpers for governance repository scripts. |
| [scripts/lib/collection_attempts.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/collection_attempts.py) | Shared lifecycle projection for append-only evidence collection attempts. |
| [scripts/lib/consolidated_l1.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/consolidated_l1.py) | Verbindet eine gemessene L1-Bewertung ausschließlich mit dem exakt passenden Staging-Snapshot und speichert die abgeleitete 16-Kontroll-Sicht append-only. |
| [scripts/lib/consumer_lifecycle_next_step.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/consumer_lifecycle_next_step.py) | Erzeugt aus der validierten Consumer-Lifecycle-Projektion eine lesende nächste-Schritte-Ansicht; ungültige Projektionen bleiben unverfügbar. |
| [scripts/lib/container_typed_evidence.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/container_typed_evidence.py) | Bind raw Trivy scans and CycloneDX SBOMs to Docker config/layers, source revision, image IDs and archive hashes for the fixed ha-CPsWMS profile. |
| [scripts/lib/control_evidence_assurance.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/control_evidence_assurance.py) | Kontrollweise Trust-/Freshness-Bewertung; fehlender Pflichtumfang bleibt `unverified` |
| [scripts/lib/document_consistency_view.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/document_consistency_view.py) | Validiert und redigiert Document-Consistency-Daten für die lesende Viewer-Projektion. |
| [scripts/lib/evidence_attestation.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/evidence_attestation.py) | Report-only public-key verification for the evidence attestation pilot. |
| [scripts/lib/evidence_trust.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/evidence_trust.py) | Shared helpers for additive, report-only evidence trust capture. |
| [scripts/lib/explicit_requirements.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/explicit_requirements.py) | Gemeinsamer Parser für explizite Requirement-Deklarationen; schließt Fließtext, ID-Verweise und synthetische Zeilen-IDs aus. |
| [scripts/lib/governance_lifecycle/__init__.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/governance_lifecycle/__init__.py) | Paketmarker des Lifecycle-Moduls; konkrete synthetische und Live-Funktionen liegen in den nachfolgenden Untermodulen. |
| [scripts/lib/governance_lifecycle/adapter.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/governance_lifecycle/adapter.py) | GRS-002 adapter for explicitly synthetic report/trust packets only. |
| [scripts/lib/governance_lifecycle/architecture_candidates.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/governance_lifecycle/architecture_candidates.py) | Candidate gate outcomes from the current unversioned architecture report shape. |
| [scripts/lib/governance_lifecycle/candidates.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/governance_lifecycle/candidates.py) | Diagnostic normalization, deliberately outside accepted lifecycle contracts. |
| [scripts/lib/governance_lifecycle/closure.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/governance_lifecycle/closure.py) | Synthetic evidence-bound closure acceptance. No live authentication or waiver closure. |
| [scripts/lib/governance_lifecycle/consumer_acceptance.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/governance_lifecycle/consumer_acceptance.py) | Separate personal operating acceptance for demo operation-readiness. |
| [scripts/lib/governance_lifecycle/consumer_actions.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/governance_lifecycle/consumer_actions.py) | Personally bound actions for the single operation-readiness consumer pilot. |
| [scripts/lib/governance_lifecycle/consumer_admission.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/governance_lifecycle/consumer_admission.py) | Durable operation-readiness receipts; operating acceptance remains separate. |
| [scripts/lib/governance_lifecycle/consumer_contracts.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/governance_lifecycle/consumer_contracts.py) | Versioned contracts for the single confirmed demo-consumer architecture scope. |
| [scripts/lib/governance_lifecycle/consumer_evidence.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/governance_lifecycle/consumer_evidence.py) | GitHub GET capture and offline verification for operation_readiness only. |
| [scripts/lib/governance_lifecycle/contracts.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/governance_lifecycle/contracts.py) | CLG-01 record contracts and bounded synthetic example checks. |
| [scripts/lib/governance_lifecycle/decisions.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/governance_lifecycle/decisions.py) | Synthetic consent/withdrawal and remediation acceptance; no live authorization. |
| [scripts/lib/governance_lifecycle/devsecops_candidates.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/governance_lifecycle/devsecops_candidates.py) | Preserve explicit control outcomes; never infer them from gate summaries. |
| [scripts/lib/governance_lifecycle/exceptions.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/governance_lifecycle/exceptions.py) | Synthetic observation-bound risk acceptance. Never a waiver-based finding closure. |
| [scripts/lib/governance_lifecycle/kernel.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/governance_lifecycle/kernel.py) | Deterministic synthetic lifecycle reduction; live authority is unavailable. |
| [scripts/lib/governance_lifecycle/live_admission.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/governance_lifecycle/live_admission.py) | Durable, reproducible pilot eligibility receipts; operational activation is separate. |
| [scripts/lib/governance_lifecycle/live_evidence.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/governance_lifecycle/live_evidence.py) | Read-only Self-Security preflight: verify captured bindings, never accept lifecycle state. |
| [scripts/lib/governance_lifecycle/live_preparation.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/governance_lifecycle/live_preparation.py) | Validate versioned pilot appointments and disabled preparation; never authorize intake. |
| [scripts/lib/governance_lifecycle/operating_acceptance.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/governance_lifecycle/operating_acceptance.py) | Explicit personal LD-07 acceptance and bounded operational pilot projection. |
| [scripts/lib/governance_lifecycle/personal_probe.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/governance_lifecycle/personal_probe.py) | Read-only verification of an explicit personal-channel probe, never lifecycle consent. |
| [scripts/lib/governance_lifecycle/pilot_actions.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/governance_lifecycle/pilot_actions.py) | Action-bound GitHub proof and reproducible pilot validation; no operational activation. |
| [scripts/lib/governance_lifecycle/store.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/governance_lifecycle/store.py) | Atomic append-only file transactions on a local POSIX filesystem. |
| [scripts/lib/governance_lifecycle/synthetic.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/governance_lifecycle/synthetic.py) | Explicitly fabricated packets for tests/demo; not a source of real trust. |
| [scripts/lib/governance_lifecycle/synthetic_actions.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/governance_lifecycle/synthetic_actions.py) | Explicit synthetic consent/progress fixtures. Not a human-authentication adapter. |
| [scripts/lib/governance_lifecycle/synthetic_exceptions.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/governance_lifecycle/synthetic_exceptions.py) | Fabricate labelled waiver and consent fixtures; never authenticate live authority. |
| [scripts/lib/identifiers.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/identifiers.py) | Identifier and timestamp helpers used by governance intake scripts. |
| [scripts/lib/json_io.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/json_io.py) | JSON file helpers used by governance repository scripts. |
| [scripts/lib/measured_l1.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/measured_l1.py) | Kontext-/Hash-Prüfung, Bindung von Build-/Scan-Digest an Archiv-Tag und importierte Runtime-Image-ID, zentrale konservative Bewertung aller 16 L1-Kontrollen, Schema- und Append-only-Prüfung |
| [scripts/lib/measured_security.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/measured_security.py) | Validiert und speichert separate unveränderliche Container-Sicherheitsnachweise. |
| [scripts/lib/measured_security_view.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/measured_security_view.py) | Erzeugt den Sicherheitsbereich im technischen Viewer. |
| [scripts/lib/release_integrity.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/release_integrity.py) | Verifies trusted direct release-tag signatures and the closed signed integrity manifest for historical tags. |
| [scripts/lib/requirement_lifecycle.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/requirement_lifecycle.py) | Parses requirement extracts and implements deterministic classification and immutable revisions. |
| [scripts/lib/result_ledger.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/result_ledger.py) | Append-only storage and report-only replay assessment for result snapshots. |
| [scripts/lib/safe_archive.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/safe_archive.py) | Validiert und entpackt externe ZIP-Evidenz mit Pfad-, Typ-, Anzahl-, Größen- und Kompressionsgrenzen. |
| [scripts/lib/secure_http.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/secure_http.py) | Erzwingt HTTPS, begrenzt Antworten und entfernt Autorisierung bei Redirects auf einen anderen Ursprung. |
| [scripts/lib/source_document_text.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/source_document_text.py) | Read supported governance source formats without changing source bytes. |
| [scripts/lib/staging_deployment.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/staging_deployment.py) | Validiert Subjektbindung, Rohdaten und autorisierte Staging-Nachweise und speichert unveränderliche Snapshots. |
| [scripts/lib/viewer_app.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/viewer_app.py) | Getrennte L1-Projektion, Kontrollsuche, Statusfilter, Quelldateien und Laufvergleich zur offiziellen Baseline |
| [scripts/lib/viewer_experience.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/viewer_experience.py) | Validiert den Lifecycle-Fall für die verständliche Viewer-Übersicht und verlinkt die erhaltenen Nachweise. |
| [scripts/lib/viewer_technical.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/lib/viewer_technical.py) | Integriert alle technischen Abschnitte mit sicherer HTML-Projektion und Linkauflösung in die Anwendung. |
| [scripts/manage_requirement_lifecycle.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/manage_requirement_lifecycle.py) | Imports, analyzes, decides, activates, reports, and completes requirement migrations. |
| [scripts/preflight_lifecycle_live_evidence.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/preflight_lifecycle_live_evidence.py) | Capture or replay diagnostic live evidence; never submit lifecycle observations. |
| [scripts/prepare_collection_attempt_retry.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/prepare_collection_attempt_retry.py) | Validate a collection-attempt record and prepare a controlled intake retry. |
| [scripts/prepare_document_consistency_semantic_catalog_run.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/prepare_document_consistency_semantic_catalog_run.py) | Bereitet ein isoliertes, provider-ungebundenes Paket für einen semantischen Kataloglauf vor. |
| [scripts/prepare_lifecycle_architecture_candidates.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/prepare_lifecycle_architecture_candidates.py) | Prepare diagnostic architecture gate candidates without inferring marker findings. |
| [scripts/prepare_lifecycle_devsecops_candidates.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/prepare_lifecycle_devsecops_candidates.py) | Prepare diagnostic control candidates, never accepted lifecycle observations. |
| [scripts/prepare_lifecycle_pilot_action.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/prepare_lifecycle_pilot_action.py) | Prepare a complete action request and printable statement; never issue personal consent. |
| [scripts/publish_consumer_lifecycle.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/publish_consumer_lifecycle.py) | Publish allowlisted operational changes as a reviewed PR, never to main. |
| [scripts/publish_document_consistency_projection.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/publish_document_consistency_projection.py) | Create a one-time, redacted public projection from private DCR inputs. |
| [scripts/publish_operational_update.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/publish_operational_update.py) | Publish allowlisted operational changes as a reviewed PR, never to main. |
| [scripts/publish_self_security_refresh.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/publish_self_security_refresh.py) | Vergleicht Self-Security-Berichte ohne flüchtige Beobachtungszeit, begrenzt versionierte Änderungen auf JSON-/Markdown-Bericht und erstellt oder aktualisiert genau einen Review-PR ohne Force-Push oder Main-Schreibzugriff. Die ignorierte Viewer-Projektion wird nach dem Merge neu gebaut. |
| [scripts/publish_typed_evidence_assurance_update.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/publish_typed_evidence_assurance_update.py) | Erweitert ausschließlich diesen Intake um die beiden append-only L1-Speicher, ohne die persönlich abgenommene Lifecycle-Publikationslogik zu verändern. |
| [scripts/publishing/build_executive_whitepaper.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/publishing/build_executive_whitepaper.py) | Build editable executive whitepaper and readable Markdown from shared content. |
| [scripts/reconcile_documentation_after_merge.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/reconcile_documentation_after_merge.py) | Erstellt aus PR-Zusammenfassung, Diff-Pfaden, lokaler Markdown-Linkprüfung und Build-Ergebnis den nachvollziehbaren Dokumentationsentwurf und Auditbericht. |
| [scripts/record_collection_attempt.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/record_collection_attempt.py) | Persist a report-only failed or partial GitHub Actions collection attempt. |
| [scripts/record_evidence_agent_provenance.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/record_evidence_agent_provenance.py) | Record an explicit report-only agent-to-evidence provenance association. |
| [scripts/record_intake_event.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/record_intake_event.py) | Persist one report-only central intake operation event. |
| [scripts/render_governance_documents.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/render_governance_documents.py) | Render governance documents from repository-managed sources. |
| [scripts/run_consumer_lifecycle.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/run_consumer_lifecycle.py) | Prepare, verify or operate the bounded consumer lifecycle through reviewed PRs. |
| [scripts/run_demo.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/run_demo.py) | Run an end-to-end governance demo using local sample inputs. |
| [scripts/run_governance_lifecycle_action_demo.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/run_governance_lifecycle_action_demo.py) | Reproduce CLG-02 then append synthetic CLG-03 consent, progress and withdrawal. |
| [scripts/run_governance_lifecycle_closure_demo.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/run_governance_lifecycle_closure_demo.py) | Run an isolated synthetic FAIL/consent/remediation/PASS/closure/reopening pilot. |
| [scripts/run_governance_lifecycle_exception_demo.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/run_governance_lifecycle_exception_demo.py) | Exercise partial/overlapping coverage, recurrence, withdrawal, expiry and fresh consent. |
| [scripts/run_governance_lifecycle_synthetic_demo.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/run_governance_lifecycle_synthetic_demo.py) | Reproduce a bounded synthetic CLG-02 history; no live repository settings change. |
| [scripts/run_lifecycle_pilot_update.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/run_lifecycle_pilot_update.py) | Prepare a bounded pilot update from protected main; publication remains a separate PR step. |
| [scripts/serve_governance_workbench.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/serve_governance_workbench.py) | Authentifizierter lokaler Workbench-Server für private Kandidaten, registrierte Quellenprüfungen, Prüfnotizen und ZIP-Weitergabe. |
| [scripts/simulate_consumer_scale.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/simulate_consumer_scale.py) | Erzeugt ausschließlich in temporären Verzeichnissen 300-/1.500-Consumer-Szenarien und misst Index-, Portfolio- und Viewer-Projektionen, ohne offizielle Statusdaten zu verändern. |
| [scripts/validate_ci_artifact_bundle.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/validate_ci_artifact_bundle.py) | Validate platform-neutral CI artifact bundles before central intake. |
| [scripts/validate_document_consistency_review.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/validate_document_consistency_review.py) | Führt deterministische Strukturprüfungen ohne semantische Interpretation durch. |
| [scripts/validate_document_consistency_review_operations.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/validate_document_consistency_review_operations.py) | Validiert provider-neutrale Betriebsartefakte des Document Consistency Review. |
| [scripts/validate_document_consistency_semantic_review.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/validate_document_consistency_semantic_review.py) | Prüft nicht vertrauenswürdige semantische Review-Ausgaben gegen ein exaktes Quellenmanifest. |
| [scripts/validate_evidence_agent_provenance.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/validate_evidence_agent_provenance.py) | Validate explicit evidence-agent provenance records and subject digests. |
| [scripts/validate_governance_lifecycle_contracts.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/validate_governance_lifecycle_contracts.py) | Validate checked-in CLG-01 synthetic contracts only; never perform live intake. |
| [scripts/validate_governance_lifecycle_ledger.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/validate_governance_lifecycle_ledger.py) | Prüft synthetische und reale Pilotverläufe, unveränderte akzeptierte Historie sowie optional neue GitHub-Evidenz und persönliche Freigaben. |
| [scripts/validate_governance_repo.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/validate_governance_repo.py) | Validiert Modelle, Schemas, Herkunft, Beispiele, veröffentlichte Baselines, erzeugte Berichte und Repository-Konsistenz. |
| [scripts/validate_requirement_lifecycle.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/validate_requirement_lifecycle.py) | Validates the Authority Ledger, catalog, cases, fingerprints, coverage, and enforcement boundary. |
| [scripts/validate_runtime_governance.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/validate_runtime_governance.py) | Validate the SDD runtime governance addendum. |
| [scripts/verify_evidence_attestation.py](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/verify_evidence_attestation.py) | Verify one evidence attestation against the report-only pilot registry. |

## Shell-Einstiegspunkte

| Datei | Aufgabe |
|---|---|
| [scripts/bootstrap_source_document_intake_env.sh](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/bootstrap_source_document_intake_env.sh) | Installiert die hashgepinnten optionalen PDF-Abhängigkeiten in einer eigenen Intake-Umgebung. |
| [scripts/bootstrap_validation_env.sh](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/bootstrap_validation_env.sh) | Installiert die versionierte Python-/OPA-Prüfumgebung idempotent. |
| [scripts/start_governance_workbench.sh](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/start_governance_workbench.sh) | Startet die lokale Workbench und bereitet bei Bedarf die gesperrte Validierungsumgebung vor. |
| [scripts/validate_all.sh](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/validate_all.sh) | Führt die vollständige gepinnte Repository-Validierung einschließlich Regressionstests und Generatoren aus. |

## Weitere Skript- und Workbench-Dateien

| Datei | Aufgabe |
|---|---|
| [scripts/publishing/build_executive_presentation.mjs](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/publishing/build_executive_presentation.mjs) | Erzeugt die editierbare Executive-PowerPoint aus content.json in der Artefaktumgebung. |
| [scripts/publishing/build_repository_presentation.mjs](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/publishing/build_repository_presentation.mjs) | Erzeugt die editierbare Repository-Walkthrough-PowerPoint aus content.json in der Artefaktumgebung. |
| [scripts/templates/governance-lifecycle-viewer.html](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/templates/governance-lifecycle-viewer.html) | HTML-Vorlage für den generierten statischen Governance-Lifecycle-Szenarienviewer. |
| [scripts/workbench/app.js](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/workbench/app.js) | Geführte Dokumentaufnahme, Navigation und private Review-Entwürfe. |
| [scripts/workbench/index.html](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/workbench/index.html) | Lokale Workbench-Oberfläche; wird nicht als öffentlicher Viewer veröffentlicht. |
| [scripts/workbench/requirement-review.js](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/workbench/requirement-review.js) | Anforderungsauswahl mit Originalkontext, Prüfnotizen, Fortschritt und getrennter Historie. |
| [scripts/workbench/style.css](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/scripts/workbench/style.css) | Darstellung der lokalen Workbench und ihrer Review-Ansichten. |

## GitHub-Workflows

| Datei | Aufgabe |
|---|---|
| [.github/workflows/architecture-baseline-l1-v0.1.0.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/.github/workflows/architecture-baseline-l1-v0.1.0.yml) | `workflow_call` |
| [.github/workflows/codeql.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/.github/workflows/codeql.yml) | `workflow_dispatch`, `push`, `pull_request`, `schedule` |
| [.github/workflows/consumer-lifecycle-guard.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/.github/workflows/consumer-lifecycle-guard.yml) | Erforderliche unabhängige Consumer-Prüfung von Historie, GitHub-Evidenz und persönlichen Freigaben. |
| [.github/workflows/consumer-lifecycle-update.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/.github/workflows/consumer-lifecycle-update.yml) | Manueller Betrieb für den benannten Consumer nach eigener Betriebsabnahme; ausschließlich PR-Vorschläge. |
| [.github/workflows/dependency-review.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/.github/workflows/dependency-review.yml) | `pull_request`, `workflow_dispatch` |
| [.github/workflows/devsecops-baseline-l1-v1.0.0.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/.github/workflows/devsecops-baseline-l1-v1.0.0.yml) | `workflow_call` |
| [.github/workflows/devsecops-baseline-l1-v1.1.0.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/.github/workflows/devsecops-baseline-l1-v1.1.0.yml) | `workflow_call` |
| [.github/workflows/devsecops-baseline-l1-v1.1.1.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/.github/workflows/devsecops-baseline-l1-v1.1.1.yml) | `workflow_call` |
| [.github/workflows/devsecops-baseline-l1-v1.1.2.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/.github/workflows/devsecops-baseline-l1-v1.1.2.yml) | `workflow_call` |
| [.github/workflows/devsecops-baseline-l1-v1.1.3.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/.github/workflows/devsecops-baseline-l1-v1.1.3.yml) | `workflow_call` |
| [.github/workflows/devsecops-baseline-l1-v1.2.0.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/.github/workflows/devsecops-baseline-l1-v1.2.0.yml) | Wiederverwendbares Workflow-Gate für den veröffentlichten DevSecOps-L1-Baseline-Stand v1.2.0. |
| [.github/workflows/devsecops-baseline-l1-v1.2.1.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/.github/workflows/devsecops-baseline-l1-v1.2.1.yml) | Wiederverwendbares Workflow-Gate für den versionierten DevSecOps-L1-Baseline-Stand v1.2.1. |
| [.github/workflows/devsecops-baseline-reusable.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/.github/workflows/devsecops-baseline-reusable.yml) | `workflow_call` |
| [.github/workflows/doc-as-code-preview.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/.github/workflows/doc-as-code-preview.yml) | Workflow: Doc-as-Code Publication Preview |
| [.github/workflows/documentation-refresh.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/.github/workflows/documentation-refresh.yml) | Reagiert auf gemergte Implementierungs-PRs, baut einen Dokumentationsvorschlag, prüft MkDocs und öffnet einen Draft-PR; schreibt nicht direkt nach `main`. |
| [.github/workflows/governance-ci.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/.github/workflows/governance-ci.yml) | `workflow_dispatch`, `push`, `pull_request` |
| [.github/workflows/governance-operations.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/.github/workflows/governance-operations.yml) | `schedule`, `workflow_dispatch`, `pull_request` |
| [.github/workflows/governance-repository-security.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/.github/workflows/governance-repository-security.yml) | `pull_request`, `push`, `workflow_dispatch` |
| [.github/workflows/intake-architecture-result.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/.github/workflows/intake-architecture-result.yml) | `workflow_dispatch`, `repository_dispatch` |
| [.github/workflows/intake-evidence-trust.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/.github/workflows/intake-evidence-trust.yml) | `workflow_dispatch`, `repository_dispatch` |
| [.github/workflows/intake-governance-result.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/.github/workflows/intake-governance-result.yml) | `workflow_dispatch`, `repository_dispatch` |
| [.github/workflows/lifecycle-pilot-update.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/.github/workflows/lifecycle-pilot-update.yml) | `workflow_dispatch` |
| [.github/workflows/portfolio-status.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/.github/workflows/portfolio-status.yml) | `schedule`, `workflow_dispatch` |
| [.github/workflows/publish-docs.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/.github/workflows/publish-docs.yml) | `push`, `workflow_dispatch` |
| [.github/workflows/refresh-governance-repository-security.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/.github/workflows/refresh-governance-repository-security.yml) | `schedule`, `workflow_dispatch` |
| [.github/workflows/repository-sbom.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/.github/workflows/repository-sbom.yml) | Erzeugt das Repository-SBOM bei Main-Push, Wochenplan oder manuellem Start. |
| [.github/workflows/requirement-lifecycle.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/.github/workflows/requirement-lifecycle.yml) | Workflow: Requirement Lifecycle |
| [.github/workflows/retry-collection-attempt.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/.github/workflows/retry-collection-attempt.yml) | `workflow_dispatch` |
| [.github/workflows/source-document-intake.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/.github/workflows/source-document-intake.yml) | Workflow: Source Document Intake |

## OPA-Module

| Datei | Aufgabe |
|---|---|
| [policies/opa/access_control.rego](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/policies/opa/access_control.rego) | `devsecops.access_control` |
| [policies/opa/architecture_integration_readiness.rego](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/policies/opa/architecture_integration_readiness.rego) | `architecture.integration_readiness` |
| [policies/opa/architecture_operation_readiness.rego](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/policies/opa/architecture_operation_readiness.rego) | `architecture.operation_readiness` |
| [policies/opa/architecture_readiness.rego](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/policies/opa/architecture_readiness.rego) | `architecture.readiness` |
| [policies/opa/architecture_release_readiness.rego](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/policies/opa/architecture_release_readiness.rego) | `architecture.release_readiness` |
| [policies/opa/artifact_integrity.rego](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/policies/opa/artifact_integrity.rego) | `devsecops.artifact_integrity` |
| [policies/opa/artifact_signing.rego](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/policies/opa/artifact_signing.rego) | `devsecops.artifact_signing` |
| [policies/opa/branch_protection.rego](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/policies/opa/branch_protection.rego) | `devsecops.branch_protection` |
| [policies/opa/dependency_source_control.rego](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/policies/opa/dependency_source_control.rego) | `devsecops.dependency_source_control` |
| [policies/opa/devsecops_release_readiness.rego](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/policies/opa/devsecops_release_readiness.rego) | `devsecops.release_readiness` |
| [policies/opa/iac_required.rego](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/policies/opa/iac_required.rego) | `devsecops.iac` |
| [policies/opa/pipeline_security_gates.rego](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/policies/opa/pipeline_security_gates.rego) | `devsecops.pipeline_security_gates` |
| [policies/opa/sbom_required.rego](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/policies/opa/sbom_required.rego) | `devsecops.sbom` |
| [policies/opa/vulnerability_gate.rego](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/policies/opa/vulnerability_gate.rego) | `devsecops.vulnerability_gate` |
| [policies/opa/waiver_validity.rego](https://github.com/joku-dev/devsecops-governance-framework/blob/ae423f34f75451b70b1ebffc71ea3683e4763c52/policies/opa/waiver_validity.rego) | `devsecops.waiver_validity` |

## Weitere Implementierungsbereiche

| Bereich | Rolle |
|---|---|
| `apps/governance-viewer/` | Öffentlicher, lesender Viewer; kein privater Intake-Speicher |
| `model/documents/` | Quellenregister und Herkunftsmetadaten |
| `model/requirements/` | Authority Ledger, Lifecycle Cases, kanonischer Katalog und Artifact Register |
| `model/controls/`, `model/platform/`, `model/traceability/` | Kontroll- und Plattformmodelle mit Zuordnungen |
| `architecture/` | Marker, Guardrails, Gates und Runtime-Level |
| `schemas/` | Validierungsverträge für Modelle, Evidenz und lokale Review-Entwürfe |
| `tests/` | Unit-, CLI-, HTTP- und Client-Regressionen einschließlich Agent Harness |
| `.agents/`, `.codex/` | Modellneutrale Rollen, Routing und Skills sowie Codex-Adapter |
| `adoption-package/`, `pipeline-baseline/` | Consumer-Vorlagen und Plattformadapter |
| `status/` | Übernommene Ergebnisse und append-only Historie |
| `generated/` | Generierte Berichte, Graphen und Viewer-Projektionen |
| `releases/` | Unveränderte versionierte Baseline-Pakete |

## Vollständigkeit bei der Pflege prüfen

```bash
git ls-files 'scripts/*.py' 'scripts/*.sh' 'scripts/*.mjs' 'scripts/*.js' 'scripts/*.html' 'scripts/*.css' '.github/workflows/*.yml' '.github/workflows/*.yaml' 'policies/opa/*.rego'
```

Zählungen und Links gelten für den angegebenen Commit. Neue Dateien erfordern
einen erneuten Dateimengenabgleich und eine Prüfung ihrer Aufgaben am Code.
