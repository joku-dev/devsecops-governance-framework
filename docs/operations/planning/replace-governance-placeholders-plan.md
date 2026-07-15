# Plan zum Ersetzen der Governance-Platzhalter in ha-CPsWMS

Dieses Dokument beschreibt die erforderlichen Schritte, um die noch vorhandenen Platzhalter-Belege in `ha-CPsWMS` durch echte Governance-Evidence zu ersetzen.

## Ziel

Erstelle echte CI-/Repo-Evidence für die folgenden Lücken im aktuellen ha-CPsWMS-Baseline-Workflow:

- `artifact_digest`
- `governance_control_report`
- `static_analysis_summary`
- `traceability_mapping`
- `operations_evidence`
- sowie die korrekte Rückkopplung in `governance/governance-run-input.json`

## Kontext

Der aktuelle ha-CPsWMS-Workflow erzeugt bereits:

- `security/sbom.cyclonedx.json`
- `security/vulnerability-scan.json`
- `governance/governance-run-input.json`

Dabei sind jedoch noch folgende Bereiche nicht vollständig realisiert:

- `artifact_digest` wird nicht als echtes Digest gespeist.
- `governance_control_report` wird nicht vollständig als auswertbarer Control-Evaluation-Report bereitgestellt.
- `static_analysis_summary` basiert auf Demo-placeholder-Daten, nicht auf echten Analyse-Output-Dateien.
- `traceability_mapping` wird zwar geschrieben, aber nicht als echte Traceability-Werkstrom-Evidence gepflegt.
- `operations_evidence` setzt nur Platzhalter-Flags, ohne echte Deployment- und Sicherheitsereignis-Belege.

## Schritt 1: Echtes Artefaktdigest erzeugen

1. Erzeuge oder prüfe das veröffentlichte Artefakt, z. B. `dist/ha-cpswms-source.tar.gz`.
2. Berechne einen SHA-256-Hash des Artefakts.
3. Schreibe eine JSON-Datei, z. B. `security/artifact-digest.json`, mit folgenden Daten:
   - `artifact`: Pfad oder Name des Artefakts
   - `digest`: SHA-256-Wert
   - `algorithm`: `sha256`
   - `created_at` / `generated_by`
4. Stelle sicher, dass diese Datei im Upload-Artifact-Satz enthalten ist.
5. Passe die Governance-Input-Erzeugung an, damit `artifact.digest.exists` und `artifact.digest.linked_to_artifact` echte Werte repräsentieren.

## Schritt 2: Governance Control Report erzeugen

1. Führe den Governance-Evaluator gegen `governance/governance-run-input.json` aus.
2. Erzeuge die Ausgabe-Dateien:
   - `application/generated/control-evaluation-report.json`
   - `application/generated/control-evaluation-report.md`
3. Lade die generierten Dateien als Artifact `governance-control-evaluation` hoch.
4. Verifiziere, dass die Intake-/Snapshot-Pipeline im Governance-Repo das Artefact korrekt erkennt.

## Schritt 3: Echte statische Analyse-Ergebnisse einbinden

1. Führe mindestens zwei geprüfte Tools aus:
   - `ruff` / `ruff-report.json`
   - `bandit` / `bandit-report.json`
   - optional: CodeQL, semgrep, etc.
2. Aktualisiere `security/static-analysis-summary.json` so, dass die Felder:
   - `performed`
   - `findings_reviewed`
   - `tools`
   - `ruff_findings`
   - `bandit_findings`
   - `bandit_high`
   - `bandit_medium`

   echte Ausgaben widerspiegeln.
3. Setze `performed` auf `true` nur, wenn die gewählten Analyse-Tools tatsächlich ausgeführt wurden.

## Schritt 4: Traceability-Mapping vervollständigen

1. Sammle echte Belege und Verknüpfungen zwischen:
   - Anforderungen/Dokumenten
   - Testfällen
   - Berichten
2. Fülle `governance/traceability.json` mit realen `traceability_records`.
3. Aktualisiere die Summary-Felder:
   - `requirements_linked`
   - `testcases_linked`
   - `reports_linked`
4. Ergänze `requirement_source`, `testcase_refs` und `report_refs` mit realen Pfaden.

## Schritt 5: Operations Evidence absichern

1. Belege die Deployment-Referenz aus `docs/DEPLOYMENT.md` oder echten Deployment-Konfigurationen.
2. Dokumentiere die eingesetzten Komponenten und ihre Quellen.
3. Verifiziere echte Sicherheitsereignisquellen:
   - `security/vulnerability-scan.json`
   - `security/static-analysis-summary.json`
   - andere echte Sicherheitsreports
4. Setze in `governance/operations-evidence.json` die Summary-Felder:
   - `deployed_versions_recorded`
   - `security_events_recorded`

## Schritt 6: Governance Run Input aktualisieren

1. Erzeuge `governance/governance-run-input.json` neu nach Abschluss der obigen Schritte.
2. Nutze die aktuellen Statuswerte aus:
   - `security/static-analysis-summary.json`
   - `governance/traceability.json`
   - `governance/operations-evidence.json`
   - `security/artifact-digest.json`
3. Stelle sicher, dass die Felder in `governance_run_input` die Realität abbilden:
   - `static_analysis.performed`
   - `traceability.*`
   - `operations.*`
   - `artifact.digest.*`

## Optional: Review und Nachverfolgung

- Prüfe den Workflow `ha-CPsWMS/.github/workflows/devsecops-baseline.yml` auf die relevanten Generierungs- oder Upload-Schritte.
- Erstelle ggf. zusätzliche Tests oder Validierungen im Governance-Repo, um sicherzustellen, dass:
  - `security/artifact-digest.json` vorhanden ist,
  - `governance-control-evaluation` Artifact korrekt hochgeladen wird,
  - `governance/governance-run-input.json` konsistent bleibt.

## Nächste Schritte

- `git add docs/operations/planning/replace-governance-placeholders-plan.md`
- `git commit -m "Add placeholder replacement plan for ha-CPsWMS governance evidence"
- `git push`

> Hinweis: Dieses Dokument ist als Erinnerungsplan gedacht. Wenn du möchtest, kann ich auch direkt einen Workflow-Vorschlag für die automatische Erzeugung dieser Dateien machen.
