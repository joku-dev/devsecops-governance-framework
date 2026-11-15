# V2-Funktions- und Einstiegspunktinventar

Stand: V2-Kandidat, 15. November 2026. Die folgende Altpfadliste bleibt das
Inventar der Foundation. Neue neutrale Gegenstücke und ihr offener Abnahmestand
stehen verbindlich in der [Paritätsmatrix](axiom-v2-functional-parity.md). Der Vertrag in
`config/axiom-v2-distribution.json` bestimmt die installierten Dateien.
Die Prüfung umfasst jeden Python-Einstiegspunkt direkt unter `scripts/`.
Ein fehlender Altpfad kann vom V2-Launcher nicht nachgeladen werden.

## Funktionsabdeckung

Die Nummern entsprechen dem [Funktionskatalog](../guides/repository-function-catalog.md).
Lokale Autorenwerkzeuge bleiben im Entwicklungscheckout verfügbar. Die V2-Installation
führt ausschließlich die unten aufgeführten Laufzeitmodule aus. Bestehende Quellen,
Anforderungen und Baselines behalten ihre Bedeutung.

| Bereich | V2-Pfad und Grenze |
| --- | --- |
| 1 Quellen verwalten | Workbench: lokale Entwürfe, Extraktion und explizites Adapterprofil für Draft-PR/MR. |
| 2 Vorgabenänderungen | Workbench sowie private `requirements`-/`dcr`-Kandidatenarbeitsbereiche. Entscheidungen und Publikation bleiben explizit; vollständige installierte Abnahme offen. |
| 3 Herkunft | Vorhandene Modelle und Berichte lesend; Generatoren im Entwicklungscheckout. |
| 4 Kontrollmodell | Versionierte Modelle im Paket; Modellpflege im Entwicklungscheckout. |
| 5 Kontrollen auswerten | Pipeline-Gate weiterhin fünf Kontrollen. Separates `evaluate --domain controls` erhält alle 46 V1-Berichtszeilen; Eingabeevidenz/Trust bleiben separat. |
| 6 OPA | Ein gepinntes OPA je Zielplattform; gemeinsame Policies und Auswertungslogik. |
| 7 Architekturmodell | Vorhandene Modell-/Baseline-Dateien erhalten; keine neue normative Architekturarbeit. |
| 8 Architektur-Readiness | `evaluate --domain architecture` führt alle vier bisherigen Gates mit detailliertem Bericht aus; keine neue normative Architekturarbeit. |
| 9 Nachweise sammeln | Explizite SCM-/CI-Profile, Provider-Adapter, Bundle-Verifikation und frische V2-Daten. |
| 10 Baselines | Bestehende unveränderte Baselines konsumieren; Freigabe neuer Baselines bleibt separater Prozess. |
| 11 Intake | `evidence` und `collector`; keine automatische Übernahme alter Indizes in aktive Queue. |
| 12 Geschichte | Neue SQLite-/Receipt-Daten, Backup und inaktiver Restore-Kandidat; V1-Geschichte bleibt Rückfallstand. |
| 13 Vertrauen | Gemeinsame Herkunfts-, Hash-, Frische- und Kontextprüfungen; keine implizite Abnahme. |
| 14 Replay | Lokale Bundle-Verifikation mit gemeinsamer Runtime; alte GitHub-Replay-CLIs nicht installiert. |
| 15 Sammlungsfehler | Collector-Status, Quarantäne, Retry und private Auditdaten über gemeinsame Logik. |
| 16 PR-Veröffentlichung | Explizite Adapterprofile und getrennte Zugangsdaten; keine implizite GitHub-Anmeldung oder Merge-Autorität. |
| 17 Status | Workbench und private Consumer-Projektion; historische statische Ansichten bleiben Referenzdaten. |
| 18 Readiness | Profile und Vertragsprüfungen; Live-Abnahmen für unbekannte GitLab/Bamboo/Bitbucket-Versionen offen. |
| 19 Betrieb/Sicherheit | Eigene Instanz, gepinnte Werkzeuge und Drift-Prüfung. GitHub-Sicherheitsbewertung nur innerhalb des Adapters. |
| 20 Reviews/Kommunikation | Bestehende lokale Autoren-, Validierungs- und Reviewwerkzeuge im Entwicklungscheckout. |
| 21 Lifecycle | V1-Live-Pilot-Einstiegspunkte in V2 stillgelegt. Keine Übertragung persönlicher Betriebsabnahme oder Aktionsrechte; neue Live-Zulassung bleibt gesondert. |
| 22 Dokumentationsabgleich | Bestehender GitHub-Workflow bleibt Adapter des Entwicklungsrepositories; kein aktiver V2-Betriebsdienst. |

## Vollständige Einstiegspunktliste

**Laufzeit:** über den endlichen V2-Launcher aufgerufen. **Bibliothek:** wird von
dieser Laufzeit lokal importiert. **Distribution:** ausschließlich Paket-/Werkzeugvorbereitung.
**Quellwerkzeug:** nicht im V2-Laufzeitpaket, weiterhin im Entwicklungscheckout vorhanden.
**V1 stillgelegt:** frühere Provider-/Pilot-/Publikations-CLIs fehlen physisch im V2-Paket.
Diese Einordnung erteilt keinem Quellwerkzeug neue Betriebsrechte.

| Datei unter `scripts/` | Klasse |
| --- | --- |
| `adapt_document_consistency_provider_response.py` | Quellwerkzeug |
| `assess_governance_repository_security.py` | V1 stillgelegt |
| `axiom_v2.py` | Laufzeit |
| `check_lifecycle_personal_channel.py` | Quellwerkzeug |
| `check_public_artifact_hygiene.py` | Quellwerkzeug |
| `check_repo_governance_integration.py` | Quellwerkzeug |
| `check_repository_onboarding_readiness.py` | Quellwerkzeug |
| `collect_architecture_release_input.py` | V1 stillgelegt |
| `collect_devsecops_release_input.py` | V1 stillgelegt |
| `collect_vulnerability_scan_evidence.py` | V1 stillgelegt |
| `consumer_intake.py` | V1 stillgelegt |
| `control_evaluation.py` | Bibliothek |
| `deploy_vm.py` | Quellwerkzeug |
| `dispatch_governance_agents.py` | Quellwerkzeug |
| `evaluate_agent_reviews.py` | Quellwerkzeug |
| `evaluate_document_consistency_semantic_report.py` | Quellwerkzeug |
| `export_repository_sbom.py` | V1 stillgelegt |
| `generate_agent_usage_snapshot.py` | Quellwerkzeug |
| `generate_architecture_governance_report.py` | Quellwerkzeug |
| `generate_architecture_results_index.py` | Quellwerkzeug |
| `generate_architecture_source_replacement_assessment.py` | Quellwerkzeug |
| `generate_architecture_traceability_csv.py` | Quellwerkzeug |
| `generate_automation_report.py` | Quellwerkzeug |
| `generate_blocking_mode_alignment.py` | Quellwerkzeug |
| `generate_blocking_readiness.py` | Quellwerkzeug |
| `generate_control_coverage_report.py` | Quellwerkzeug |
| `generate_control_evaluation_report.py` | Quellwerkzeug |
| `generate_devsecops_governance_report.py` | Quellwerkzeug |
| `generate_document_consistency_review_manifest.py` | Quellwerkzeug |
| `generate_document_consistency_review_model.py` | Bibliothek |
| `generate_document_control_matrix.py` | Quellwerkzeug |
| `generate_end_to_end_governance_report.py` | Quellwerkzeug |
| `generate_evidence_agent_provenance_index.py` | Quellwerkzeug |
| `generate_governance_change_impact_report.py` | Quellwerkzeug |
| `generate_governance_compliance_result.py` | Quellwerkzeug |
| `generate_governance_graph.py` | Quellwerkzeug |
| `generate_governance_lifecycle_exceptions.py` | Quellwerkzeug |
| `generate_governance_lifecycle_index.py` | Quellwerkzeug |
| `generate_governance_lifecycle_overview.py` | Quellwerkzeug |
| `generate_governance_lifecycle_pilot.py` | Quellwerkzeug |
| `generate_governance_lifecycle_viewer.py` | Quellwerkzeug |
| `generate_governance_traceability_csv.py` | Quellwerkzeug |
| `generate_harmonized_requirements_maturity_report.py` | Quellwerkzeug |
| `generate_implemented_requirement_migration.py` | Quellwerkzeug |
| `generate_intake_health.py` | Quellwerkzeug |
| `generate_lifecycle_pilot_actions.py` | Quellwerkzeug |
| `generate_lifecycle_pilot_validation.py` | Quellwerkzeug |
| `generate_multi_consumer_readiness.py` | Quellwerkzeug |
| `generate_open_gap_report.py` | Quellwerkzeug |
| `generate_operations_report.py` | Quellwerkzeug |
| `generate_personal_channel_evidence.py` | Quellwerkzeug |
| `generate_personal_channel_probe.py` | Quellwerkzeug |
| `generate_pipeline_baseline_report.py` | Quellwerkzeug |
| `generate_pipeline_evidence.py` | Quellwerkzeug |
| `generate_platform_context.py` | Quellwerkzeug |
| `generate_portable_candidate_index.py` | Quellwerkzeug |
| `generate_portfolio_onboarding_status.py` | Quellwerkzeug |
| `generate_pra_requirement_platform_review.py` | Quellwerkzeug |
| `generate_replay_triage_report.py` | Quellwerkzeug |
| `generate_repository_results_index.py` | Quellwerkzeug |
| `generate_source_document_intake_review_briefs.py` | Quellwerkzeug |
| `generate_source_document_intake_status.py` | Quellwerkzeug |
| `generate_source_document_process_status.py` | Bibliothek |
| `generate_source_document_requirement_delta.py` | Bibliothek |
| `generate_source_lineage_report.py` | Quellwerkzeug |
| `generate_status_viewer.py` | Quellwerkzeug |
| `generate_traceability_csv.py` | Quellwerkzeug |
| `generate_typed_evidence_results_index.py` | Quellwerkzeug |
| `governance_runtime.py` | Laufzeit |
| `import_harmonized_requirements_workbook.py` | Quellwerkzeug |
| `install_axiom_v2.py` | Distribution |
| `install_validation_opa.py` | Distribution |
| `intake_architecture_github_actions_run.py` | V1 stillgelegt |
| `intake_ci_artifact_bundle.py` | V1 stillgelegt |
| `intake_evidence_trust_github_actions_run.py` | V1 stillgelegt |
| `intake_github_actions_run.py` | V1 stillgelegt |
| `intake_governance_lifecycle_action.py` | V1 stillgelegt |
| `intake_governance_lifecycle_observation.py` | V1 stillgelegt |
| `intake_governance_result.py` | V1 stillgelegt |
| `intake_ha_container_trust.py` | V1 stillgelegt |
| `intake_lifecycle_pilot_action.py` | V1 stillgelegt |
| `intake_lifecycle_pilot_run.py` | V1 stillgelegt |
| `intake_measured_l1.py` | V1 stillgelegt |
| `intake_measured_security.py` | V1 stillgelegt |
| `intake_portable_evidence.py` | Laufzeit |
| `intake_staging_deployment_evidence.py` | V1 stillgelegt |
| `manage_requirement_lifecycle.py` | Quellwerkzeug |
| `observe_provider_assurance.py` | Quellwerkzeug |
| `package_governance_runtime.py` | Distribution (nur Entwicklungscheckout) |
| `portable_consumer_intake.py` | Laufzeit |
| `preflight_lifecycle_live_evidence.py` | Quellwerkzeug |
| `prepare_collection_attempt_retry.py` | Quellwerkzeug |
| `prepare_document_consistency_semantic_catalog_run.py` | Quellwerkzeug |
| `prepare_lifecycle_architecture_candidates.py` | V1 stillgelegt |
| `prepare_lifecycle_devsecops_candidates.py` | V1 stillgelegt |
| `prepare_lifecycle_pilot_action.py` | V1 stillgelegt |
| `publish_consumer_lifecycle.py` | V1 stillgelegt |
| `publish_document_consistency_projection.py` | V1 stillgelegt |
| `publish_operational_update.py` | V1 stillgelegt |
| `publish_self_security_refresh.py` | V1 stillgelegt |
| `publish_typed_evidence_assurance_update.py` | V1 stillgelegt |
| `reconcile_documentation_after_merge.py` | V1 stillgelegt |
| `record_agent_review.py` | Quellwerkzeug |
| `record_collection_attempt.py` | Quellwerkzeug |
| `record_evidence_agent_provenance.py` | Quellwerkzeug |
| `record_intake_event.py` | Quellwerkzeug |
| `render_governance_documents.py` | Quellwerkzeug |
| `report_agent_review_status.py` | Quellwerkzeug |
| `run_agent_reviews.py` | Quellwerkzeug |
| `run_consumer_lifecycle.py` | V1 stillgelegt |
| `run_demo.py` | Quellwerkzeug |
| `run_governance_lifecycle_action_demo.py` | Quellwerkzeug |
| `run_governance_lifecycle_closure_demo.py` | Quellwerkzeug |
| `run_governance_lifecycle_exception_demo.py` | Quellwerkzeug |
| `run_governance_lifecycle_synthetic_demo.py` | Quellwerkzeug |
| `run_lifecycle_pilot_update.py` | V1 stillgelegt |
| `serve_governance_workbench.py` | Laufzeit |
| `simulate_consumer_scale.py` | Quellwerkzeug |
| `validate_axiom_v2.py` | Quellwerkzeug |
| `validate_ci_artifact_bundle.py` | Quellwerkzeug |
| `validate_document_consistency_review.py` | Quellwerkzeug |
| `validate_document_consistency_review_operations.py` | Quellwerkzeug |
| `validate_document_consistency_semantic_review.py` | Quellwerkzeug |
| `validate_evidence_agent_provenance.py` | Quellwerkzeug |
| `validate_governance_lifecycle_contracts.py` | Quellwerkzeug |
| `validate_governance_lifecycle_ledger.py` | Quellwerkzeug |
| `validate_governance_repo.py` | Quellwerkzeug |
| `validate_requirement_lifecycle.py` | Quellwerkzeug |
| `validate_runtime_governance.py` | Quellwerkzeug |
| `verify_evidence_attestation.py` | Quellwerkzeug |

Zusätzlich zu den 130 Python-Dateien direkt unter `scripts/` existieren diese
acht Shell-/Node-/verschachtelten Python-Einstiege. Auch sie sind im V2-Paket
physisch ausgeschlossen; die Workbench-Browserdateien sind UI-Assets.

| Datei unter `scripts/` | Klasse |
| --- | --- |
| `bootstrap_validation_env.sh` | Quellwerkzeug: gepinnte Entwicklungsvalidierung |
| `bootstrap_source_document_intake_env.sh` | Quellwerkzeug: Parser-Vorbereitung |
| `validate_all.sh` | Quellwerkzeug: vollständige Entwicklungsvalidierung |
| `deploy_vm.sh` | V1-Installationspfad; nicht für den getrennten V2-Präfix verwenden |
| `start_governance_workbench.sh` | V1-Startpfad; V2 verwendet seinen eigenen Launcher |
| `publishing/build_executive_presentation.mjs` | Quellwerkzeug: Dokumentausgabe |
| `publishing/build_repository_presentation.mjs` | Quellwerkzeug: Dokumentausgabe |
| `publishing/build_executive_whitepaper.py` | Quellwerkzeug: Dokumentausgabe |

Native CI-Workflows und Deploymentvorlagen bleiben Provider-/Entwicklungs-
Metadaten. Der V2-Installer aktiviert keine davon. `tests/acceptance/axiom_v2_host_smoke.py`
ist ein separat aufgerufener Test des fertigen Kandidaten und kein Produkt-Einstieg.

Die vier bisherigen Importfassaden und ihre Altmodule werden nicht installiert.
Die Adapterbibliothek und ihre expliziten neutralen Abhängigkeiten werden vollständig
aufgenommen. Tests prüfen die importierte Dateimenge transitiv und erkennen neue,
noch nicht klassifizierte Einstiegspunkte. Historische Release-Pakete sind Daten;
der Launcher führt darin enthaltene alte Skripte nicht aus.
