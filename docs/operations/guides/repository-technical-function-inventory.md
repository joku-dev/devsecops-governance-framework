# Technische Funktionsliste des Repositories

Stand: 13. September 2026, Quellstand `8df643db37ec4d6da7196b94aaa77b5e0e0844d8`.

Dies ist die vollständige Dateiliste der implementierten Skripte und Bibliotheksmodule
unter `scripts/`, der GitHub-Workflows und der OPA-Module am genannten Stand.
Der [fachliche Katalog](repository-function-catalog.md) erläutert die 21 Aufgabenbereiche
mit Eingaben, Verarbeitung, Ausgaben und Grenzen. Einzelne interne Python-Symbole
werden ihrem Modul zugeordnet; diese Liste ist keine öffentliche API-Zusage.

Umfang: **120 Skripte/Module**, **19 Workflows**, **15 OPA-Module**.

Einträge wurden aus den versionierten Dateien, Python-Modulbeschreibungen und
Workflow-Definitionen ermittelt. Englische Beschreibungen übernehmen die
Quellsprache der Module; unvollständige Paketbeschreibungen wurden fachlich präzisiert.

## Ausführung und Seiteneffekte

Zuerst `./scripts/bootstrap_validation_env.sh` ausführen. Python-CLI-Werkzeuge
benutzen `.venv-validation/bin/python`; Parameter sind anhand des jeweiligen
Argumentparsers zu wählen. Nicht jedes Modul besitzt eine CLI oder `--help`.
Generatoren können Dateien schreiben, Intake-Werkzeuge GitHub lesen und lokale
Nachweise ergänzen. Der Publisher schreibt einen Remote-Branch und öffnet einen PR.
Persönliche Erklärungen werden von der benannten Person selbst abgegeben.
Bibliotheken werden importiert, Publishing-Builder benötigen die dokumentierte
Artefaktumgebung. Kein Werkzeug pauschal ausführen, um nur seine Funktion zu ermitteln.

## Skripte und gemeinsame Auswertungsmodule

| Datei | Aufgabe |
|---|---|
| [scripts/assess_governance_repository_security.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/assess_governance_repository_security.py) | Collect and assess the security posture of the governance repository. |
| [scripts/bootstrap_validation_env.sh](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/bootstrap_validation_env.sh) | Installiert die versionierte Python-/OPA-Prüfumgebung idempotent. |
| [scripts/check_lifecycle_personal_channel.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/check_lifecycle_personal_channel.py) | Check or replay a personal-channel probe; this command never posts a statement. |
| [scripts/check_public_artifact_hygiene.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/check_public_artifact_hygiene.py) | Reject configured private terms in public text and Office metadata. |
| [scripts/check_repo_governance_integration.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/check_repo_governance_integration.py) | Check whether a target repository appears to integrate governance CI. |
| [scripts/check_repository_onboarding_readiness.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/check_repository_onboarding_readiness.py) | Assess a repository before central governance baseline onboarding. |
| [scripts/collect_architecture_release_input.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/collect_architecture_release_input.py) | Collect a demo architecture release-readiness input from a target repo. |
| [scripts/collect_devsecops_release_input.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/collect_devsecops_release_input.py) | Collect DevSecOps release-readiness input from an application repository. |
| [scripts/collect_vulnerability_scan_evidence.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/collect_vulnerability_scan_evidence.py) | Collect normalized vulnerability evidence and derive report-only Trust. |
| [scripts/control_evaluation.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/control_evaluation.py) | Shared helpers for control-level governance evaluation reports. |
| [scripts/dispatch_governance_agents.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/dispatch_governance_agents.py) | Ermittelt Rollen und Skills aus geänderten Pfaden und protokolliert bei Auswahl deren Nutzung; führt selbst keinen fachlichen LLM-Review aus. |
| [scripts/generate_agent_usage_snapshot.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_agent_usage_snapshot.py) | Erzeugt JSON-/Markdown-Nutzungsübersichten aus dem Dispatch-Protokoll. |
| [scripts/generate_architecture_governance_report.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_architecture_governance_report.py) | Generate an architecture runtime governance report from OPA gate results. |
| [scripts/generate_architecture_results_index.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_architecture_results_index.py) | Aggregate Architecture Runtime Governance results into a central index. |
| [scripts/generate_architecture_source_replacement_assessment.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_architecture_source_replacement_assessment.py) | Assess architecture source document replacement candidates. |
| [scripts/generate_architecture_traceability_csv.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_architecture_traceability_csv.py) | Generate architecture runtime governance traceability CSV. |
| [scripts/generate_automation_report.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_automation_report.py) | Generate a Markdown report for automation coverage. |
| [scripts/generate_blocking_mode_alignment.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_blocking_mode_alignment.py) | Assess current enforcement modes against Blocking Readiness without changing them. |
| [scripts/generate_blocking_readiness.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_blocking_readiness.py) | Generate a report-only blocking-readiness decision aid. |
| [scripts/generate_control_coverage_report.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_control_coverage_report.py) | Generate a control automation coverage report. |
| [scripts/generate_control_evaluation_report.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_control_evaluation_report.py) | Generate a control-by-control evaluation report for a governance run input. |
| [scripts/generate_devsecops_governance_report.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_devsecops_governance_report.py) | Generate a DevSecOps governance report from OPA release-readiness results. |
| [scripts/generate_document_control_matrix.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_document_control_matrix.py) | Generate document-to-control authority reports from governance YAML. |
| [scripts/generate_end_to_end_governance_report.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_end_to_end_governance_report.py) | Generate a combined architecture and DevSecOps governance report. |
| [scripts/generate_evidence_agent_provenance_index.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_evidence_agent_provenance_index.py) | Generate a deterministic index for explicit evidence-agent provenance. |
| [scripts/generate_governance_change_impact_report.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_governance_change_impact_report.py) | Generate a lightweight governance change impact report. |
| [scripts/generate_governance_compliance_result.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_governance_compliance_result.py) | Generate an extended governance compliance result artifact. |
| [scripts/generate_governance_graph.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_governance_graph.py) | Generate a deterministic read-only graph from governed repository artifacts. |
| [scripts/generate_governance_lifecycle_exceptions.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_governance_lifecycle_exceptions.py) | Generate a synthetic exception projection/report at an explicit evaluation instant. |
| [scripts/generate_governance_lifecycle_index.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_governance_lifecycle_index.py) | Generate a synthetic-only index from the complete immutable lifecycle ledger. |
| [scripts/generate_governance_lifecycle_overview.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_governance_lifecycle_overview.py) | Replay three separate synthetic histories into an explicit-time overview. |
| [scripts/generate_governance_lifecycle_pilot.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_governance_lifecycle_pilot.py) | Generate explicit-time synthetic CLG-04 projection and pilot report. |
| [scripts/generate_governance_lifecycle_viewer.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_governance_lifecycle_viewer.py) | Generate a standalone read-only viewer from the verified synthetic overview. |
| [scripts/generate_governance_traceability_csv.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_governance_traceability_csv.py) | Generate a flat governance traceability CSV for Policy and Directive requirements. |
| [scripts/generate_harmonized_requirements_maturity_report.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_harmonized_requirements_maturity_report.py) | Generate non-normative maturity decision support for harmonized requirements. |
| [scripts/generate_intake_health.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_intake_health.py) | Generate a report-only operational health projection from intake telemetry. |
| [scripts/generate_lifecycle_pilot_actions.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_lifecycle_pilot_actions.py) | Generate the separate action-validation projection; never publish official state. |
| [scripts/generate_lifecycle_pilot_validation.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_lifecycle_pilot_validation.py) | Generate the separate durable pilot validation projection from complete receipts. |
| [scripts/generate_multi_consumer_readiness.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_multi_consumer_readiness.py) | Generate a report-only proof that central intake isolates multiple consumers. |
| [scripts/generate_open_gap_report.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_open_gap_report.py) | Generate an open gap report for governance model follow-up. |
| [scripts/generate_operations_report.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_operations_report.py) | Read-only daily operational report; findings never authorize enforcement. |
| [scripts/generate_personal_channel_evidence.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_personal_channel_evidence.py) | Retained diagnostic channel captures and independent checks; never action consent. |
| [scripts/generate_personal_channel_probe.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_personal_channel_probe.py) | Render the bound personal statement for the appointed person to issue themselves. |
| [scripts/generate_pipeline_baseline_report.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_pipeline_baseline_report.py) | Generate a Markdown report for the CI/CD Pipeline Control Baseline. |
| [scripts/generate_pipeline_evidence.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_pipeline_evidence.py) | Generate normalized DevSecOps pipeline evidence for CI/CD adapters. |
| [scripts/generate_platform_context.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_platform_context.py) | Generate normalized CI/CD platform context from native environment variables. |
| [scripts/generate_portfolio_onboarding_status.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_portfolio_onboarding_status.py) | Generate a portfolio onboarding status report from the integration registry. |
| [scripts/generate_replay_triage_report.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_replay_triage_report.py) | Explain stored replay checks without rewriting evidence or Trust records. |
| [scripts/generate_repository_results_index.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_repository_results_index.py) | Aggregate repository governance results into a central index. |
| [scripts/generate_source_document_intake_review_briefs.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_source_document_intake_review_briefs.py) | Generate source-document intake review briefs. |
| [scripts/generate_source_document_intake_status.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_source_document_intake_status.py) | Generate a source-document intake status report. |
| [scripts/generate_source_document_requirement_delta.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_source_document_requirement_delta.py) | Generate requirement-level deltas for source-document replacement candidates. |
| [scripts/generate_source_lineage_report.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_source_lineage_report.py) | Generate source-document lineage report for governance artifacts. |
| [scripts/generate_status_viewer.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_status_viewer.py) | Generate a static governance status viewer. |
| [scripts/generate_traceability_csv.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_traceability_csv.py) | Generate a flat control traceability CSV from the YAML control library. |
| [scripts/generate_typed_evidence_results_index.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/generate_typed_evidence_results_index.py) | Aggregate typed Evidence Trust results without changing governance outcomes. |
| [scripts/import_harmonized_requirements_workbook.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/import_harmonized_requirements_workbook.py) | Create a public-neutral candidate mapping without publishing source text. |
| [scripts/intake_architecture_github_actions_run.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/intake_architecture_github_actions_run.py) | Intake a downstream Architecture Runtime Governance GitHub Actions run. |
| [scripts/intake_ci_artifact_bundle.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/intake_ci_artifact_bundle.py) | Intake platform-neutral CI artifact bundles into central status snapshots. |
| [scripts/intake_evidence_trust_github_actions_run.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/intake_evidence_trust_github_actions_run.py) | Intake and centrally reverify typed Evidence Trust from a GitHub Actions run. |
| [scripts/intake_github_actions_run.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/intake_github_actions_run.py) | Intake a downstream GitHub Actions governance run into central status. |
| [scripts/intake_governance_lifecycle_action.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/intake_governance_lifecycle_action.py) | Intake an explicit synthetic decision/remediation/closure/exception packet; never approve a real decision. |
| [scripts/intake_governance_lifecycle_observation.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/intake_governance_lifecycle_observation.py) | Append one explicitly synthetic GRS-002 packet to a local lifecycle ledger. |
| [scripts/intake_governance_result.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/intake_governance_result.py) | Create a normalized governance result snapshot from pipeline metadata. |
| [scripts/intake_lifecycle_pilot_action.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/intake_lifecycle_pilot_action.py) | Capture an action-bound personal statement into pilot validation; never post or execute it. |
| [scripts/intake_lifecycle_pilot_run.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/intake_lifecycle_pilot_run.py) | Collect fresh provider evidence into durable pilot validation; no live activation. |
| [scripts/preflight_lifecycle_live_evidence.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/preflight_lifecycle_live_evidence.py) | Capture or replay diagnostic live evidence; never submit lifecycle observations. |
| [scripts/prepare_collection_attempt_retry.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/prepare_collection_attempt_retry.py) | Validate a collection-attempt record and prepare a controlled intake retry. |
| [scripts/prepare_lifecycle_architecture_candidates.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/prepare_lifecycle_architecture_candidates.py) | Prepare diagnostic architecture gate candidates without inferring marker findings. |
| [scripts/prepare_lifecycle_devsecops_candidates.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/prepare_lifecycle_devsecops_candidates.py) | Prepare diagnostic control candidates, never accepted lifecycle observations. |
| [scripts/prepare_lifecycle_pilot_action.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/prepare_lifecycle_pilot_action.py) | Prepare a complete action request and printable statement; never issue personal consent. |
| [scripts/publish_operational_update.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/publish_operational_update.py) | Publish allowlisted operational changes as a reviewed PR, never to main. |
| [scripts/record_collection_attempt.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/record_collection_attempt.py) | Persist a report-only failed or partial GitHub Actions collection attempt. |
| [scripts/record_evidence_agent_provenance.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/record_evidence_agent_provenance.py) | Record an explicit report-only agent-to-evidence provenance association. |
| [scripts/record_intake_event.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/record_intake_event.py) | Persist one report-only central intake operation event. |
| [scripts/render_governance_documents.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/render_governance_documents.py) | Render governance documents from repository-managed sources. |
| [scripts/run_demo.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/run_demo.py) | Run an end-to-end governance demo using local sample inputs. |
| [scripts/run_governance_lifecycle_action_demo.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/run_governance_lifecycle_action_demo.py) | Reproduce CLG-02 then append synthetic CLG-03 consent, progress and withdrawal. |
| [scripts/run_governance_lifecycle_closure_demo.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/run_governance_lifecycle_closure_demo.py) | Run an isolated synthetic FAIL/consent/remediation/PASS/closure/reopening pilot. |
| [scripts/run_governance_lifecycle_exception_demo.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/run_governance_lifecycle_exception_demo.py) | Exercise partial/overlapping coverage, recurrence, withdrawal, expiry and fresh consent. |
| [scripts/run_governance_lifecycle_synthetic_demo.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/run_governance_lifecycle_synthetic_demo.py) | Reproduce a bounded synthetic CLG-02 history; no live repository settings change. |
| [scripts/run_lifecycle_pilot_update.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/run_lifecycle_pilot_update.py) | Prepare a bounded pilot update from protected main; publication remains a separate PR step. |
| [scripts/validate_all.sh](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/validate_all.sh) | Führt die vollständige gepinnte Repository-Validierung einschließlich Regressionstests und Generatoren aus. |
| [scripts/validate_ci_artifact_bundle.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/validate_ci_artifact_bundle.py) | Validate platform-neutral CI artifact bundles before central intake. |
| [scripts/validate_evidence_agent_provenance.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/validate_evidence_agent_provenance.py) | Validate explicit evidence-agent provenance records and subject digests. |
| [scripts/validate_governance_lifecycle_contracts.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/validate_governance_lifecycle_contracts.py) | Validate checked-in CLG-01 synthetic contracts only; never perform live intake. |
| [scripts/validate_governance_lifecycle_ledger.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/validate_governance_lifecycle_ledger.py) | Prüft synthetische und reale Pilotverläufe, unveränderte akzeptierte Historie sowie optional neue GitHub-Evidenz und persönliche Freigaben. |
| [scripts/validate_governance_repo.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/validate_governance_repo.py) | Validiert Modelle, Schemas, Herkunft, Beispiele, veröffentlichte Baselines, erzeugte Berichte und Repository-Konsistenz. |
| [scripts/validate_runtime_governance.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/validate_runtime_governance.py) | Validate the SDD runtime governance addendum. |
| [scripts/verify_evidence_attestation.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/verify_evidence_attestation.py) | Verify one evidence attestation against the report-only pilot registry. |

## Bibliotheksmodule

| Datei | Aufgabe |
|---|---|
| [scripts/lib/__init__.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/lib/__init__.py) | Shared helpers for governance repository scripts. |
| [scripts/lib/collection_attempts.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/lib/collection_attempts.py) | Shared lifecycle projection for append-only evidence collection attempts. |
| [scripts/lib/evidence_attestation.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/lib/evidence_attestation.py) | Report-only public-key verification for the evidence attestation pilot. |
| [scripts/lib/evidence_trust.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/lib/evidence_trust.py) | Shared helpers for additive, report-only evidence trust capture. |
| [scripts/lib/governance_lifecycle/__init__.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/lib/governance_lifecycle/__init__.py) | Paketmarker des Lifecycle-Moduls; konkrete synthetische und Live-Funktionen liegen in den nachfolgenden Untermodulen. |
| [scripts/lib/governance_lifecycle/adapter.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/lib/governance_lifecycle/adapter.py) | GRS-002 adapter for explicitly synthetic report/trust packets only. |
| [scripts/lib/governance_lifecycle/architecture_candidates.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/lib/governance_lifecycle/architecture_candidates.py) | Candidate gate outcomes from the current unversioned architecture report shape. |
| [scripts/lib/governance_lifecycle/candidates.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/lib/governance_lifecycle/candidates.py) | Diagnostic normalization, deliberately outside accepted lifecycle contracts. |
| [scripts/lib/governance_lifecycle/closure.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/lib/governance_lifecycle/closure.py) | Synthetic evidence-bound closure acceptance. No live authentication or waiver closure. |
| [scripts/lib/governance_lifecycle/contracts.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/lib/governance_lifecycle/contracts.py) | CLG-01 record contracts and bounded synthetic example checks. |
| [scripts/lib/governance_lifecycle/decisions.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/lib/governance_lifecycle/decisions.py) | Synthetic consent/withdrawal and remediation acceptance; no live authorization. |
| [scripts/lib/governance_lifecycle/devsecops_candidates.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/lib/governance_lifecycle/devsecops_candidates.py) | Preserve explicit control outcomes; never infer them from gate summaries. |
| [scripts/lib/governance_lifecycle/exceptions.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/lib/governance_lifecycle/exceptions.py) | Synthetic observation-bound risk acceptance. Never a waiver-based finding closure. |
| [scripts/lib/governance_lifecycle/kernel.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/lib/governance_lifecycle/kernel.py) | Deterministic synthetic lifecycle reduction; live authority is unavailable. |
| [scripts/lib/governance_lifecycle/live_admission.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/lib/governance_lifecycle/live_admission.py) | Durable, reproducible pilot eligibility receipts; operational activation is separate. |
| [scripts/lib/governance_lifecycle/live_evidence.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/lib/governance_lifecycle/live_evidence.py) | Read-only Self-Security preflight: verify captured bindings, never accept lifecycle state. |
| [scripts/lib/governance_lifecycle/live_preparation.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/lib/governance_lifecycle/live_preparation.py) | Validate versioned pilot appointments and disabled preparation; never authorize intake. |
| [scripts/lib/governance_lifecycle/operating_acceptance.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/lib/governance_lifecycle/operating_acceptance.py) | Explicit personal LD-07 acceptance and bounded operational pilot projection. |
| [scripts/lib/governance_lifecycle/personal_probe.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/lib/governance_lifecycle/personal_probe.py) | Read-only verification of an explicit personal-channel probe, never lifecycle consent. |
| [scripts/lib/governance_lifecycle/pilot_actions.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/lib/governance_lifecycle/pilot_actions.py) | Action-bound GitHub proof and reproducible pilot validation; no operational activation. |
| [scripts/lib/governance_lifecycle/store.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/lib/governance_lifecycle/store.py) | Atomic append-only file transactions on a local POSIX filesystem. |
| [scripts/lib/governance_lifecycle/synthetic.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/lib/governance_lifecycle/synthetic.py) | Explicitly fabricated packets for tests/demo; not a source of real trust. |
| [scripts/lib/governance_lifecycle/synthetic_actions.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/lib/governance_lifecycle/synthetic_actions.py) | Explicit synthetic consent/progress fixtures. Not a human-authentication adapter. |
| [scripts/lib/governance_lifecycle/synthetic_exceptions.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/lib/governance_lifecycle/synthetic_exceptions.py) | Fabricate labelled waiver and consent fixtures; never authenticate live authority. |
| [scripts/lib/identifiers.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/lib/identifiers.py) | Identifier and timestamp helpers used by governance intake scripts. |
| [scripts/lib/json_io.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/lib/json_io.py) | JSON file helpers used by governance repository scripts. |
| [scripts/lib/result_ledger.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/lib/result_ledger.py) | Append-only storage and report-only replay assessment for result snapshots. |

## Publishing-Builder

| Datei | Aufgabe |
|---|---|
| [scripts/publishing/build_executive_presentation.mjs](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/publishing/build_executive_presentation.mjs) | Erzeugt die editierbare Executive-PowerPoint aus content.json in der Artefaktumgebung. |
| [scripts/publishing/build_executive_whitepaper.py](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/publishing/build_executive_whitepaper.py) | Build editable executive whitepaper and readable Markdown from shared content. |
| [scripts/publishing/build_repository_presentation.mjs](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/scripts/publishing/build_repository_presentation.mjs) | Erzeugt die editierbare Repository-Walkthrough-PowerPoint aus content.json in der Artefaktumgebung. |

## GitHub-Workflows

Die Trigger stammen aus der Workflow-Datei auf dem betrachteten `main`-Stand.
Das ist keine Aussage, dass jeder Workflow im Unternehmen eingerichtet ist.
Versionierte Wrapper werden von Consumern mit ihrem veröffentlichten Tag verwendet;
der Stand einer gleichnamigen Datei auf `main` ersetzt diesen Tag nicht.

| Datei | Trigger | Aufgabe |
|---|---|---|
| [.github/workflows/architecture-baseline-l1-v0.1.0.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/.github/workflows/architecture-baseline-l1-v0.1.0.yml) | `workflow_call` | Konsumierbare Architektur-L1-Baseline; sammelt Eingang, prüft Gates und publiziert Evidenz. Standard: report-only. |
| [.github/workflows/codeql.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/.github/workflows/codeql.yml) | `workflow_dispatch`, `push`, `pull_request`, `schedule` | Statische Python-Sicherheitsanalyse mit CodeQL. |
| [.github/workflows/dependency-review.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/.github/workflows/dependency-review.yml) | `pull_request` | Prüft Änderungen an Abhängigkeiten im PR. |
| [.github/workflows/devsecops-baseline-l1-v1.0.0.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/.github/workflows/devsecops-baseline-l1-v1.0.0.yml) | `workflow_call` | Versionierter DevSecOps-L1-Wrapper v1.0.0; historische veröffentlichte Version, für bestehende Pins erhalten. |
| [.github/workflows/devsecops-baseline-l1-v1.1.0.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/.github/workflows/devsecops-baseline-l1-v1.1.0.yml) | `workflow_call` | Versionierter DevSecOps-L1-Wrapper v1.1.0; historische veröffentlichte Version, für bestehende Pins erhalten. |
| [.github/workflows/devsecops-baseline-l1-v1.1.1.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/.github/workflows/devsecops-baseline-l1-v1.1.1.yml) | `workflow_call` | Versionierter DevSecOps-L1-Wrapper v1.1.1; historische veröffentlichte Version, für bestehende Pins erhalten. |
| [.github/workflows/devsecops-baseline-l1-v1.1.2.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/.github/workflows/devsecops-baseline-l1-v1.1.2.yml) | `workflow_call` | Versionierter DevSecOps-L1-Wrapper v1.1.2; historische veröffentlichte Version, für bestehende Pins erhalten. |
| [.github/workflows/devsecops-baseline-l1-v1.1.3.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/.github/workflows/devsecops-baseline-l1-v1.1.3.yml) | `workflow_call` | Versionierter DevSecOps-L1-Wrapper v1.1.3; aktuell konsumierte L1-Baseline. |
| [.github/workflows/devsecops-baseline-reusable.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/.github/workflows/devsecops-baseline-reusable.yml) | `workflow_call` | Gemeinsamer DevSecOps-Workflow; explizite Moduswahl, Standard block-on-error. |
| [.github/workflows/governance-ci.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/.github/workflows/governance-ci.yml) | `workflow_dispatch`, `push`, `pull_request` | Modell-, OPA-, Ledger-/Provider-, Test- und Dokumentationsprüfung; schützt neue operative Veröffentlichungen auch bei manuellem Dispatch. |
| [.github/workflows/governance-operations.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/.github/workflows/governance-operations.yml) | `schedule`, `workflow_dispatch`, `pull_request` | Lesender täglicher Betriebsbericht (06:43 UTC) und manueller Abruf; keine automatische Alarmzustellung. |
| [.github/workflows/governance-repository-security.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/.github/workflows/governance-repository-security.yml) | `pull_request`, `push`, `schedule`, `workflow_dispatch` | Report-only-Self-Security des Governance-Repositories; zugelassener Mainline-Producer für GRS-002. |
| [.github/workflows/intake-architecture-result.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/.github/workflows/intake-architecture-result.yml) | `workflow_dispatch`, `repository_dispatch` | Erfasst reale Architektur-Ergebnisse und schlägt deren Veröffentlichung als begrenzten PR vor. |
| [.github/workflows/intake-evidence-trust.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/.github/workflows/intake-evidence-trust.yml) | `workflow_dispatch`, `repository_dispatch` | Erfasst und verifiziert typisierte Evidenz; separate Trust-Snapshots und PR-Veröffentlichung. |
| [.github/workflows/intake-governance-result.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/.github/workflows/intake-governance-result.yml) | `workflow_dispatch`, `repository_dispatch` | Erfasst DevSecOps-Ergebnisse mit Laufkontext, Telemetrie und begrenzter PR-Veröffentlichung. |
| [.github/workflows/lifecycle-pilot-update.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/.github/workflows/lifecycle-pilot-update.yml) | `workflow_dispatch` | Manueller abgenommener GRS-002-Pilot: acceptance, observe, action, refresh; Providerprüfung und PR-Vorschlag. |
| [.github/workflows/portfolio-status.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/.github/workflows/portfolio-status.yml) | `schedule`, `workflow_dispatch` | Projiziert das registrierte Consumer-Portfolio und schlägt eine Aktualisierung per PR vor. |
| [.github/workflows/publish-docs.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/.github/workflows/publish-docs.yml) | `push`, `workflow_dispatch` | Baut MkDocs und stellt Dokumentation samt konfigurierten generierten Assets auf GitHub Pages bereit. |
| [.github/workflows/retry-collection-attempt.yml](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/.github/workflows/retry-collection-attempt.yml) | `workflow_dispatch` | Prüft einen aufgezeichneten Sammlungsfehler und startet den zulässigen Intake erneut. |

## OPA-Module

| Datei | Rego-Paket / Prüfgebiet |
|---|---|
| [policies/opa/access_control.rego](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/policies/opa/access_control.rego) | `devsecops.access_control` |
| [policies/opa/architecture_integration_readiness.rego](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/policies/opa/architecture_integration_readiness.rego) | `architecture.integration_readiness` |
| [policies/opa/architecture_operation_readiness.rego](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/policies/opa/architecture_operation_readiness.rego) | `architecture.operation_readiness` |
| [policies/opa/architecture_readiness.rego](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/policies/opa/architecture_readiness.rego) | `architecture.readiness` |
| [policies/opa/architecture_release_readiness.rego](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/policies/opa/architecture_release_readiness.rego) | `architecture.release_readiness` |
| [policies/opa/artifact_integrity.rego](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/policies/opa/artifact_integrity.rego) | `devsecops.artifact_integrity` |
| [policies/opa/artifact_signing.rego](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/policies/opa/artifact_signing.rego) | `devsecops.artifact_signing` |
| [policies/opa/branch_protection.rego](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/policies/opa/branch_protection.rego) | `devsecops.branch_protection` |
| [policies/opa/dependency_source_control.rego](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/policies/opa/dependency_source_control.rego) | `devsecops.dependency_source_control` |
| [policies/opa/devsecops_release_readiness.rego](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/policies/opa/devsecops_release_readiness.rego) | `devsecops.release_readiness` |
| [policies/opa/iac_required.rego](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/policies/opa/iac_required.rego) | `devsecops.iac` |
| [policies/opa/pipeline_security_gates.rego](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/policies/opa/pipeline_security_gates.rego) | `devsecops.pipeline_security_gates` |
| [policies/opa/sbom_required.rego](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/policies/opa/sbom_required.rego) | `devsecops.sbom` |
| [policies/opa/vulnerability_gate.rego](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/policies/opa/vulnerability_gate.rego) | `devsecops.vulnerability_gate` |
| [policies/opa/waiver_validity.rego](https://github.com/joku-dev/devsecops-governance-framework/blob/8df643db37ec4d6da7196b94aaa77b5e0e0844d8/policies/opa/waiver_validity.rego) | `devsecops.waiver_validity` |

Die fachlichen Prüfgebiete erklärt [Abschnitt 6 des Katalogs](repository-function-catalog.md#6-opa-prufregeln-ausfuhren).
Nicht jedes Modul ist in jeder veröffentlichten Baseline aktiv. Insbesondere
Policy-Kandidaten sind von veröffentlichten Baseline-Bestandteilen zu unterscheiden.

## Modelle, Schemas, Vorlagen und Tests

| Bereich | Aufgabe / Einstieg |
|---|---|
| `model/` | Kontrollkataloge, Plattformfähigkeiten, Quellenregister, Evidenz- und Rollen-/Betriebsprofile |
| `architecture/` | Architekturlevel, Qualitätsmarker, Guardrails, Review-Gates und Remediation-Aktionskatalog |
| `schemas/` | Geschlossene beziehungsweise versionierte Datenverträge; kein Betriebsfreigabenachweis allein durch Schemaerfolg |
| `pipeline-baseline/`, `examples/`, `adoption-package/` | Integrationsvorlagen; GitHub-Referenz und getrennte Bamboo-, Bitbucket-Cloud-, Jenkins- und GitLab-Pfade |
| `.agents/`, `.codex/`, `.github/codex/` | Modellneutrale Rollen/Skills/Routing und Provideradapter |
| `tests/`, `demo/` | Regression, negative Fälle und reproduzierbare Demonstrationen; Testdaten bleiben als solche gekennzeichnet |
| `status/`, `governance/lifecycle/` | Angenommene Evidenz, Historien und ihre getrennten Projektionen |
| `generated/` | Durch Skripte erzeugte Berichte, Graph und Viewer |
| `releases/` | Unveränderte versionierte Baseline-Pakete |

## Vollständigkeit bei der Pflege prüfen

Diese Liste ist ein datierter Quellstand. Bei neuen oder entfernten Dateien zuerst
die Dateimenge mit den Tabellen vergleichen und die Beschreibung anhand des Codes prüfen:

```bash
git ls-files 'scripts/*.py' 'scripts/*.sh' 'scripts/*.mjs' '.github/workflows/*.yml' 'policies/opa/*.rego'
```

Die [Dokumentationsprüfung vom 13. September](../reference-runs/2026-09-13-documentation-currency-review.md)
beschreibt den geprüften Umfang und die getrennten historischen Artefakte.
