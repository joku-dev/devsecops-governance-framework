# Evidence- und Governance-Hardening – Betriebsanleitung

Dieses Dokument beschreibt die seit dem Graph- und Ledger-Ausbau verfügbaren
Funktionen. Es ist die operative Referenz für zentrale Intake-Läufe,
Evidence-Collector, Agent-Provenance und lokale Validierung.

Alle beschriebenen Funktionen sind derzeit report-only. Keine der Funktionen
ändert einen Governance-Status, erhöht selbstständig einen Evidence-Trust-Level
oder macht einen Workflow automatisch blocking.

## 1. Überblick

Der aktuelle Datenfluss besteht aus fünf getrennten Schichten:

1. Downstream-Workflow erzeugt Governance- oder Typed-Evidence-Artefakte.
2. Intake lädt die Artefakte zentral und erzeugt append-only Snapshots.
3. Der Evidence-Trust-Verifier prüft Subjects, Custody, Freshness und Replay.
4. Index- und Graph-Generatoren projizieren die Historie für Suche und Viewer.
5. Optionale Agent-Provenance verknüpft eine konkrete Agenten-Aktivität mit
   einem bereits bekannten Subject-Digest.

Die Schichten bleiben bewusst getrennt: Ein Agenten-Eintrag ist keine
Attestation, ein Replay-Finding ist kein neuer Governance-Fail und ein
Collector-Fehler ist kein erfolgreicher Evidence-Snapshot.

## 2. Append-only Result Ledger

### Zweck

Der Result Ledger verhindert, dass ein erneuter Intake-Lauf historische
Evidence überschreibt.

Implementierung:

- `scripts/lib/result_ledger.py`
- `schemas/intake-conflict.schema.json`
- `status/intake-conflicts/`

Verwendet wird der Ledger von Governance-, Architektur- und Typed-Evidence-
Intakes.

### Verhalten

| Situation | Ergebnis |
|---|---|
| Neuer Run und neue Subject-Digests | neuer Snapshot |
| Identischer Run und identische Digests | idempotenter No-op |
| Gleicher Zielpfad, andere Evidence | Original bleibt unverändert; Konflikt wird quarantänisiert |
| Gleicher Subject-Digest in kompatiblem Kontext | report-only Replay-Pass |
| Digest-Reuse in inkompatiblem Repository-, Commit- oder Artefakt-Kontext | report-only Replay-Fail |

Die Replay-Identität bindet Repository, Commit, Workflow, Run, Run Attempt,
Artefakt und Subject-Digests. Sie verändert nicht den unabhängig berechneten
Trust-Level.

### Prüfung

```bash
python3 -m unittest tests.test_result_ledger
python3 scripts/generate_repository_results_index.py
python3 scripts/generate_architecture_results_index.py
python3 scripts/generate_typed_evidence_results_index.py
```

Konflikte werden unter `status/intake-conflicts/` gespeichert und mit dem
Schema `intake-conflict.schema.json` validiert. Sie dürfen nicht manuell
gelöscht oder in den Original-Snapshot zurückgeschrieben werden.

## 3. Governance Intelligence Graph

### Zweck

Der Graph ist eine deterministische, read-only Projektion der Governance-
Beziehungen. Git und die versionierten JSON-Dateien bleiben die Quelle der
Wahrheit.

Implementierung:

- Schema: `schemas/governance-graph.schema.json`
- Generator: `scripts/generate_governance_graph.py`
- Ausgabe: `generated/graph/governance-graph.json`
- Viewer-Generator: `scripts/generate_status_viewer.py`
- Dokumentation: `docs/operations/status/governance-intelligence-graph-viewer.md`

### Aktualisierung

```bash
python3 scripts/generate_governance_graph.py
python3 scripts/generate_status_viewer.py
```

Der Graph enthält unter anderem Source Documents, Governance-Artefakte,
Baselines, Repositories, Workflow-Runs, Result-Snapshots, Evidence und Trust-
Assessments. Er darf nicht als Ersatz für die Detaildateien verwendet werden.

## 4. Reproduzierbare Validation Toolchain

### Zweck

Lokale und zentrale Prüfungen sollen dieselben Tool-Versionen verwenden.

Festgelegt sind:

- Python-Abhängigkeiten: `requirements-validation.txt`
- OPA-Version und Checksums: `scripts/validation-toolchain.env`
- Bootstrap: `scripts/bootstrap_validation_env.sh`
- Vollständige Prüfung: `scripts/validate_all.sh`

OPA darf nicht auf `latest` zeigen. GitHub-Workflows verwenden OPA `1.18.2`;
der Architektur-Workflow prüft zusätzlich den SHA-256-Hash des Binaries.

### Vollständige Prüfung

```bash
./scripts/bootstrap_validation_env.sh
./scripts/validate_all.sh
```

Oder mit einer isolierten Umgebung:

```bash
VALIDATION_VENV=/tmp/devsecops-governance-validation \
  ./scripts/bootstrap_validation_env.sh
VALIDATION_VENV=/tmp/devsecops-governance-validation \
  ./scripts/validate_all.sh
```

Die Prüfung umfasst OPA-Syntax, Runtime-Governance, Repository-Schemas,
Evidence-Agent-Provenance und die Unit-Tests.

## 5. Failed und Partial Collection Attempts

### Zweck

Ein Collector-Fehler darf nicht als erfolgreicher Snapshot erscheinen, soll
aber für Betrieb und Audit sichtbar bleiben.

Implementierung:

- Schema: `schemas/evidence-collection-attempt.schema.json`
- Recorder: `scripts/record_collection_attempt.py`
- Speicherung: `status/collection-attempts/`
- Quarantäne: `status/intake-conflicts/collection-attempts/`
- Viewer: Abschnitt „Collection Attempts"

Diese Funktion ist in den DevSecOps-, Architecture- und Typed-Evidence-Intake
integriert. Ein `failed`-Versuch wird gespeichert, bevor der Workflow weiterhin
als fehlgeschlagen beendet wird. Kann GitHub-Metadaten nicht gelesen werden,
bleibt der Versuch über eine Fallback-Identität und den zusätzlichen Fehler
`source_metadata_unavailable` sichtbar.

Der manuelle Workflow `Retry Collection Attempt` kann einen vollständig als
`retryable` markierten Versuch erneut an den passenden bestehenden Intake
übergeben. Der Viewer leitet anschließend `open`, `resolved` oder `permanent`
aus dem unveränderten Attempt und passenden erfolgreichen Snapshots ab.

### Manuelle Erfassung

```bash
python3 scripts/record_collection_attempt.py \
  --repository-id joku-dev/governance-framework-demo-consumer \
  --run-id 123456789 \
  --evidence-type vulnerability_scan \
  --collector-id central-vulnerability-scan-collector \
  --artifact-name application-evidence \
  --error-code artifact_not_found \
  --message "Expected application-evidence artifact was not available." \
  --retryable
```

Identische Versuche sind idempotent. Ein anderer Payload mit derselben
Attempt-ID wird nicht überschrieben, sondern als Konflikt gemeldet.

## 6. Evidence-Agent-Provenance

### Zweck und Grenzen

Die Provenance-Schicht dokumentiert, welcher Agent an welchem konkreten
Evidence-Subject beteiligt war. Sie beweist nicht die Echtheit des Subjects.

Implementierung:

- Schema: `schemas/evidence-agent-provenance.schema.json`
- Index-Schema: `schemas/evidence-agent-provenance-index.schema.json`
- Recorder: `scripts/record_evidence_agent_provenance.py`
- Validator: `scripts/validate_evidence_agent_provenance.py`
- Speicherung: `status/evidence-agent-provenance/`
- Dokumentation: `docs/operations/agents/agent-usage-tracking.md`

Zulässige Beteiligungen:

| Wert | Bedeutung |
|---|---|
| `selected` | Routing hat die Rolle ausgewählt |
| `executed` | Agent hat die Aufgabe tatsächlich ausgeführt |
| `reviewed` | Agent hat das Subject geprüft |
| `approved` | Agent hat eine dokumentierte Freigabe erteilt |

Nur explizit gespeicherte Zuordnungen werden angezeigt. Das System leitet
keine Agentenbeziehung aus Dateipfaden, Commit-Autoren oder Zeitstempeln ab.

### Zuordnung erfassen

```bash
python3 scripts/record_evidence_agent_provenance.py \
  --repository-id joku-dev/governance-framework-demo-consumer \
  --evidence-type vulnerability_scan \
  --subject-id vulnerability_scan_report \
  --subject-digest <64-hex-sha256> \
  --source-file status/typed-evidence-results/<repo>/<result>.json \
  --agent-id evidence-and-intake \
  --role-version 1.0.0 \
  --skill evidence-and-intake \
  --provider codex \
  --involvement reviewed \
  --dispatch-id dispatch-2026-07-17-001 \
  --run-type provider_review \
  --dispatch-source manual
```

Danach werden Index und Viewer neu erzeugt:

```bash
python3 scripts/generate_evidence_agent_provenance_index.py
python3 scripts/generate_status_viewer.py
```

### Validierung

```bash
python3 scripts/validate_evidence_agent_provenance.py
```

Die Validierung prüft Schema, Quelldatei, Subject-ID und Digest. Ein nicht
passender Digest macht die Repository-Validierung fehlgeschlagen.

## 7. Viewer und Statusprojektionen

Der statische Viewer wird nicht direkt bearbeitet. Änderungen erfolgen über
Generatoren:

```bash
python3 scripts/generate_repository_results_index.py
python3 scripts/generate_architecture_results_index.py
python3 scripts/generate_typed_evidence_results_index.py
python3 scripts/generate_governance_graph.py
python3 scripts/generate_evidence_agent_provenance_index.py
python3 scripts/generate_status_viewer.py
```

Relevante Viewer-Bereiche sind:

- Governance-Status und historische Runs
- Typed Evidence Trust
- Governance Intelligence Graph
- Intake Conflict Quarantine
- Collection Attempts
- Evidence Agent Provenance

## 8. Intake Operation Telemetry

Jeder zentrale DevSecOps-, Architecture- und Typed-Evidence-Intake erfasst nun
ein append-only, report-only Betriebsereignis – auch bei Erfolg. Dadurch steht
erstmals ein korrekter Nenner für spätere Erfolgs-, Fehler- und Latenzmetriken
zur Verfügung.

Implementierung:

- Schema: `schemas/intake-operation-event.schema.json`
- Beispiel: `docs/examples/intake-operation-event.example.json`
- Recorder: `scripts/record_intake_event.py`
- Speicherung: `status/intake-events/`
- Dokumentation: `docs/operations/evidence/intake-operation-telemetry.md`

Die Telemetrie ersetzt keine Collection Attempts. Bei einem Fehler werden beide
Records erzeugt: der Collection Attempt für Retry und Lifecycle, das Intake-
Event für die Betriebsmetrik. Viewer, `latest_result`, Trust-Level und
Enforcement bleiben in diesem ersten Schritt unverändert.

## 9. End-to-End-Betrieb

### Deterministische Reports und Replay-Prüfung

Ein identischer normalisierter Control-Report ist bei einem neuen, legitim
erzeugten Workflow-Lauf nicht automatisch ein Replay. Der Intake bindet solche
Reports deshalb zusätzlich an den Digest des GitHub-Artefakts. Ein neuer
Artefakt-Digest bei gleichem Report-Inhalt wird als kompatible Wiederverwendung
bewertet; ein wiederverwendeter Artefakt-Digest in einem inkompatiblen Kontext
bleibt ein report-only Replay-Finding.

Für eine Änderung oder einen neuen Intake-Lauf:

1. Downstream-Workflow und Artifact prüfen.
2. Intake-Skript ausführen.
3. Bei Fehlern Collection Attempt erfassen.
4. Result- und Typed-Evidence-Indizes regenerieren.
5. Graph und Viewer regenerieren.
6. Provenance nur bei tatsächlich erfolgter Agentenbeteiligung erfassen.
7. `./scripts/validate_all.sh` ausführen.
8. Änderungen prüfen, committen und pushen.

Keine der report-only Schichten darf als Ersatz für signierte Attestierungen,
Trust Roots oder Subject Binding interpretiert werden. Diese Funktionen sind
der nächste geplante Ausbau.
