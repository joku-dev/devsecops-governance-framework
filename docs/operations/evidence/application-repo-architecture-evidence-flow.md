# Ablauf im Applikationsrepo bis zur Architektur-Evidence

Dieses Dokument erklärt Schritt für Schritt, was in einem Applikationsrepo beim Thema Architektur-Governance passiert, bis die Architektur-Nachweise als JSON-Reports abgelegt werden.

Der Ablauf ist dem DevSecOps-Evidence-Flow ähnlich. Der Unterschied liegt in der Art der Nachweise:

- DevSecOps-Evidence kommt stark aus Tools wie Build, SBOM, Scanner und Pipeline-Gates.
- Architektur-Evidence kommt stärker aus strukturierten Architekturartefakten, Reviews, Baselines, Kompatibilitätserklärungen und Betriebsnachweisen.

Die finale Architektur-Report-JSON wird trotzdem nicht manuell geschrieben. Menschen pflegen die fachlichen Quellnachweise. Die Pipeline sammelt, validiert und bewertet sie automatisch.

## Zielbild

Das Applikationsrepo bleibt Eigentümer seiner Architektur-Nachweise. Es beschreibt seine Architektur, Baseline-Kompatibilität, Security-, Resilience-, Operations- und Feedback-Evidence in kontrollierten Dateien.

Das Governance-Repository bleibt Eigentümer der Architektur-Governance-Logik. Es stellt den Collector, die OPA-Policies, die Marker-Bewertung, die Reports und den wiederverwendbaren Workflow bereit.

Für ein vollständiges Timing-Diagramm über Applikationsrepo, CI/CD, Governance-Repo-Tooling, Intake und Viewer siehe:

```text
docs/operations/processes/application-repo-governance-timing.md
```

Für eine vorgeschlagene Architektur-Evidence-Type-Taxonomie als Diskussionsgrundlage mit Enterprise Architecture siehe:

```text
docs/operations/evidence/architecture-evidence-type-taxonomy.md
```

Für die Kompatibilitätszuordnung zwischen bestehenden Input-Evidence-Namen, neutraler Taxonomie und aktuellem Schema siehe:

```text
docs/operations/evidence/architecture-evidence-taxonomy-mapping.md
```

Für eine kurze Entscheidungsvorlage für Enterprise Architecture siehe:

```text
docs/operations/evidence/architecture-evidence-ea-decision-brief.md
```

Für die Einführung detaillierter Architektur-Evidence in Applikationsrepos siehe:

```text
docs/operations/evidence/detailed-architecture-evidence-adoption-guide.md
```

Für das vollständige Paket zur Abstimmung mit Enterprise Architecture siehe:

```text
docs/operations/evidence/architecture-evidence-ea-package.md
```

Für einen kontrollierten Architektur-Lauf mit erwarteten Findings siehe:

```text
docs/operations/reference-runs/2026-07-06-architecture-findings-reference-run.md
```

```text
Applikationsrepo
  docs/ARCHITECTURE.md
  docs/DEPLOYMENT.md
  docker-compose.yml
  tests/
  schemas/
  .governance/architecture/*.json
        |
        v
Architecture Governance Workflow
        |
        v
architecture-release-input.json
        |
        v
OPA Architektur-Gates und Report-Generator
        |
        v
architecture-governance-report.json
architecture-governance-report.md
        |
        v
GitHub Actions Artifact: architecture-governance-evidence
        |
        v
optionaler Intake ins Governance-Repo:
status/architecture-results/<repository>/<timestamp>-run-<run-id>.json
```

## Beteiligte Rollen

| Rolle | Verantwortung |
|---|---|
| Product Architect | Verantwortet Produktarchitektur, Architekturentscheidungen, Kompatibilität und Release-Fähigkeit. |
| Solution Architect | Verantwortet Solution Baseline, Schnittstellen- und Lösungskompatibilität. |
| Application Team | Pflegt technische Architekturartefakte, Tests, Schnittstellen, Deployment- und Runtime-Nachweise. |
| Security Architect oder Security Engineer | Verantwortet Security Evidence, Threat Model, Security Review und sicherheitsrelevante Findings. |
| Operations oder SRE | Verantwortet Operations-, Monitoring-, Resilience- und Recovery-Nachweise. |
| Release Owner | Verantwortet Release-Kontext, Freigabe und bekannte Einschränkungen. |
| Governance Maintainer | Pflegt Architektur-Baseline, OPA-Policies, Collector und Report-Generator. |
| GitHub Actions | Führt Workflow aus, erzeugt Reports und speichert Artifacts. |

## Schritt 1: Architektur-Evidence-Struktur ins Applikationsrepo aufnehmen

Das Applikationsrepo erhält eine strukturierte Evidence-Ablage:

```text
.governance/architecture/
```

Typische Dateien:

```text
.governance/architecture/solution-baseline.json
.governance/architecture/release-compatibility-declaration.json
.governance/architecture/security-evidence.json
.governance/architecture/resilience-evidence.json
.governance/architecture/operation-evidence.json
.governance/architecture/feedback-evidence.json
```

Diese Dateien können aus dem Template übernommen werden:

```text
pipeline-baseline/templates/app-architecture-evidence/.governance/architecture/
```

Verantwortlich:

- Product Architect und Solution Architect definieren Architektur- und Baseline-Inhalte.
- Application Team legt die Dateien im Repository ab.
- Governance Maintainer stellt Templates und Schema bereit.

## Schritt 2: Status der Architektur-Nachweise setzen

Jede Architektur-Evidence-Datei besitzt einen Status:

| Status | Bedeutung |
|---|---|
| `draft` | Evidence existiert, ist aber noch nicht verifiziert. |
| `reviewed` | Evidence wurde geprüft, zählt aber noch nicht als akzeptierter Gate-Nachweis. |
| `approved` | Evidence ist akzeptiert und kann Gate Findings reduzieren. |

Beispiel:

```json
{
  "evidence_type": "release_compatibility_declaration",
  "status": "approved",
  "owner": "Product Architect",
  "baseline_version": "ha-CPsWMS-demo-baseline",
  "approved_by": "Solution Architect",
  "approval_date": "2026-07-03",
  "summary": "Declares compatibility of this release with the referenced solution baseline.",
  "evidence_refs": [
    "docs/ARCHITECTURE.md",
    "docs/DEPLOYMENT.md"
  ],
  "known_limitations": [],
  "follow_up_actions": []
}
```

Wichtig: Der Status ist fachlich bedeutsam. Eine Datei mit `draft` zeigt, dass ein Thema erkannt wurde. Eine Datei mit `approved` zeigt, dass der Nachweis akzeptiert ist.

Verantwortlich:

- Der fachliche Owner setzt Inhalt und Status.
- Reviewer oder approver bestätigen `approved_by` und `approval_date`.
- Die Pipeline liest den Status automatisch.

## Schritt 2a: Coarse Evidence und Detailed Evidence unterscheiden

Aktuell gibt es zwei Evidence-Ebenen:

| Ebene | Zweck | Beispiel | Gate-Wirkung |
|---|---|---|---|
| Coarse Evidence | Bestehende grobe Gate-Evidence | `security_evidence`, `operation_evidence` | Kann bestehende Marker und Gates beeinflussen. |
| Detailed Evidence | Neutrale, feinere Taxonomie | `threat_model`, `interface_contract`, `deployment_manifest`, `model_based_architecture` | Wird zunächst report-only ausgewiesen. |

Detailed Evidence hilft beim Schärfen der Architektur-Nachweise, ohne sofort neue Blocking-Gates einzuführen. Enterprise Architecture kann später entscheiden, welche detaillierten Typen für welche Systemklasse verpflichtend werden.

## Schritt 3: Technische Architekturartefakte im Repository pflegen

Der Collector wertet nicht nur `.governance/architecture/*.json` aus. Er erkennt auch technische Repository-Signale.

Typische Dateien:

| Datei oder Ordner | Bedeutung |
|---|---|
| `docs/ARCHITECTURE.md` | Beschreibt System, Komponenten, Schnittstellen, Ownership und Entscheidungen. |
| `docs/DEPLOYMENT.md` | Beschreibt Deployment, Betrieb, Health Checks, Rollback, Secrets und Recovery. |
| `docker-compose.yml` | Liefert Runtime- und Deployment-Hinweise. |
| `**/Dockerfile` | Liefert Build- und Deployment-Evidence. |
| `tests/**/*.py` | Liefert Test- und Verifikationsnachweise. |
| `**/schemas/*.json` | Liefert Interface-, Daten- oder Contract-Evidence. |
| `benchmark/reports/*benchmark.json` | Liefert Performance-Evidence. |

Verantwortlich:

- Application Team pflegt diese Dateien.
- Product Architect stellt sicher, dass Architektur und Implementierung zusammenpassen.
- Operations und Security ergänzen Betriebs- und Sicherheitsinformationen.

## Schritt 4: Architektur-Governance-Workflow im Applikationsrepo anlegen

Das Applikationsrepo erhält einen Workflow, zum Beispiel:

```text
.github/workflows/architecture-governance.yml
```

Der Workflow kann direkt den released Architecture Baseline Workflow aufrufen:

```yaml
name: Architecture Runtime Governance

on:
  pull_request:
  push:
    branches:
      - main
  workflow_dispatch:

jobs:
  architecture-governance:
    uses: joku-dev/devsecops-governance-as-code/.github/workflows/architecture-baseline-l1-v0.1.0.yml@architecture-baseline-l1-v0.1.0
    with:
      release_id: ${{ github.sha }}
      solution_baseline: ha-CPsWMS-demo-baseline
      application_path: .
      upload_evidence: true
      fail_on_findings: false
```

Wichtig: Während der Einführung kann `fail_on_findings: false` sinnvoll sein. Dann erzeugt der Workflow Findings, blockiert aber noch nicht. Später kann der Wert auf `true` gesetzt werden.

Verantwortlich:

- DevSecOps Engineer legt den Workflow an.
- Product oder Solution Architect setzt `solution_baseline`.
- Governance Maintainer veröffentlicht den versionierten Baseline-Workflow.

## Schritt 5: Pipeline wird ausgelöst

Der Architektur-Governance-Workflow läuft typischerweise bei:

- Pull Request
- Push auf `main`
- manuellem `workflow_dispatch`

GitHub Actions stellt Kontext bereit:

| Kontext | Beispiel |
|---|---|
| Repository | `joku-dev/ha-CPsWMS` |
| Branch | `main` |
| Commit | `${{ github.sha }}` |
| Run-ID | `${{ github.run_id }}` |
| Event | `push`, `pull_request`, `workflow_dispatch` |

Diese Informationen werden später in Reports und optional im zentralen Status-Snapshot verwendet.

## Schritt 6: Applikationsrepo wird ausgecheckt

Der released Architecture Baseline Workflow checkt das Applikationsrepo aus:

```yaml
- name: Checkout application repository
  uses: actions/checkout@v4
  with:
    path: application
```

Danach liegt der Applikationscode unter:

```text
application/
```

Verantwortlich:

- GitHub Actions führt den Checkout aus.
- Das Application Team stellt sicher, dass die relevanten Architekturdateien im Repository vorhanden sind.

## Schritt 7: Governance-Repository wird versioniert ausgecheckt

Der Workflow checkt zusätzlich das Governance-Repository mit der freigegebenen Architektur-Baseline aus:

```yaml
- name: Checkout governance repository
  uses: actions/checkout@v4
  with:
    repository: joku-dev/devsecops-governance-as-code
    ref: architecture-baseline-l1-v0.1.0
    path: governance
```

Dadurch liegen Collector, Policies, Schemas und Report-Generator im Runner unter:

```text
governance/
```

Verantwortlich:

- Governance Maintainer pflegt und versioniert diese Baseline.
- Application Team konsumiert die freigegebene Version.

## Schritt 8: Python-Abhängigkeiten und OPA werden installiert

Der Workflow installiert technische Laufzeitabhängigkeiten:

```bash
python -m pip install --upgrade jsonschema pyyaml
```

Zusätzlich wird OPA installiert:

```bash
curl -L -o opa https://openpolicyagent.org/downloads/latest/opa_linux_amd64_static
chmod +x opa
sudo mv opa /usr/local/bin/opa
opa version
```

OPA wird später genutzt, um Architektur-Gates gegen die gesammelte Evidence auszuwerten.

Verantwortlich:

- Der Workflow führt die Installation aus.
- Governance Maintainer definiert, welche Tools benötigt werden.

## Schritt 9: Architektur-Release-Input wird gesammelt

Der wichtigste Sammelschritt ist:

```bash
python governance/scripts/collect_architecture_release_input.py \
  --repo "application/." \
  --output governance/generated/app/architecture-release-input.json \
  --release-id "${GITHUB_SHA}" \
  --baseline "ha-CPsWMS-demo-baseline"
```

Das Skript liest:

- `.governance/architecture/*.json`
- `docs/ARCHITECTURE.md`
- `docs/DEPLOYMENT.md`
- `docker-compose.yml`
- Dockerfiles
- Tests
- JSON Schemas
- Benchmark Reports
- weitere erkennbare Repository-Signale

Ergebnis:

```text
governance/generated/app/architecture-release-input.json
```

Diese Datei ist die normalisierte Architektur-Evidence des Applikationsrepos.

Verantwortlich:

- Product Architect und Application Team liefern die Quellen.
- Collector erzeugt daraus automatisch die normalisierte JSON.

## Schritt 10: Was im architecture-release-input.json steht

Die Datei enthält zwei große Bereiche:

```json
{
  "release_candidate": true,
  "target_repository": {
    "path": "application/.",
    "commit": "abc1234",
    "release_id": "abc1234",
    "detected_services": 4
  },
  "architecture": {
    "marker_assessments": [],
    "release_compatibility_declaration": {},
    "solution_baseline": {},
    "compatibility_evidence": {},
    "security_evidence": {},
    "deployment_evidence": {},
    "runtime_evidence": {},
    "review_evidence": {},
    "exception_evidence": {},
    "feedback_evidence": {},
    "detailed_evidence": {
      "report_only": true,
      "declared_types": [],
      "by_type": {},
      "by_coarse_type": {}
    },
    "exceptions": []
  }
}
```

`detailed_evidence` ist eine report-only Sicht auf neutrale Evidence-Typen aus der Architektur-Evidence-Type-Taxonomie. Diese Sicht hilft beim Schärfen der Evidence, ohne bestehende Release-Gates sofort zu verschärfen.

Der Abschnitt `target_repository` beschreibt den geprüften Repository-Stand.

Der Abschnitt `architecture` enthält die Architektur-Evidence.

## Schritt 11: Marker Assessments werden automatisch berechnet

Der Collector erzeugt `marker_assessments`.

Ein Marker ist eine bewertbare Architektur-Frage oder Architektur-Eigenschaft.

Beispiele:

| Marker-Bereich | Bedeutung |
|---|---|
| `B*` | Business-, Ownership- und Feedback-Aspekte. |
| `P*` | Product Architecture und Runtime-Aspekte. |
| `S*` | Solution- und Integrationsaspekte. |
| `E*` | Engineering-, Security-, Deployment- oder Verifikationsaspekte. |

Die Bewertung erfolgt mit Scores:

| Score | Bedeutung |
|---|---|
| `1` | Nicht oder kaum belegt. |
| `3` | Beschrieben oder vorhanden. |
| `4` | Verifiziert oder approved. |
| `5` | Kontinuierlich gemessen oder verbessert. |

Beispiel:

```json
{
  "id": "S6",
  "score": 4,
  "evidence": [
    ".governance/architecture/release-compatibility-declaration.json",
    ".governance/architecture/solution-baseline.json",
    "docs/ARCHITECTURE.md"
  ]
}
```

Wichtig: Der Score wird automatisch aus vorhandenen Dateien, erkannten Signalen und `approved`-Status berechnet. Der Ingenieur trägt ihn nicht manuell in den Report ein.

Verantwortlich:

- Die fachlichen Rollen liefern Nachweise.
- Der Collector berechnet die Scores.
- Governance Maintainer pflegt die Bewertungslogik.

## Schritt 12: Schema-Validierung des Architektur-Inputs

Der Workflow validiert:

```text
generated/app/architecture-release-input.json
```

gegen:

```text
schemas/architecture-release-candidate.schema.json
```

Wenn die Struktur nicht stimmt, schlägt der Workflow fehl.

Verantwortlich:

- Governance Maintainer pflegt das Schema.
- Application Team korrigiert ungültige Evidence-Dateien.

## Schritt 13: Architektur-Governance-Report wird erzeugt

Der Workflow führt den Report-Generator aus:

```bash
python scripts/generate_architecture_governance_report.py \
  --input generated/app/architecture-release-input.json \
  --output-json generated/app/architecture-governance-report.json \
  --output-md generated/app/architecture-governance-report.md
```

Ergebnis:

```text
governance/generated/app/architecture-governance-report.json
governance/generated/app/architecture-governance-report.md
```

Die Markdown-Datei wird zusätzlich in die GitHub Actions Step Summary geschrieben.

Verantwortlich:

- Der Report-Generator erzeugt JSON und Markdown.
- Governance Maintainer pflegt Report-Logik und Remediation-Mapping.

## Schritt 14: OPA-Gates bewerten die Architektur-Evidence

Der Report-Generator ruft OPA für mehrere Architektur-Gates auf.

Aktuelle Gates:

| Gate | Policy |
|---|---|
| Architecture Readiness | `policies/opa/architecture_readiness.rego` |
| Integration Readiness | `policies/opa/architecture_integration_readiness.rego` |
| Operation Readiness | `policies/opa/architecture_operation_readiness.rego` |
| Release Readiness | `policies/opa/architecture_release_readiness.rego` |

Jedes Gate erzeugt Findings oder einen Pass-Status.

Beispielhafte Report-Struktur:

```json
{
  "target": {
    "path": "application/.",
    "commit": "abc1234",
    "release_id": "abc1234",
    "detected_services": 4
  },
  "gates": [
    {
      "id": "release_readiness",
      "title": "Release Readiness",
      "status": "findings",
      "findings": [
        "Release compatibility declaration is missing or not approved."
      ],
      "remediations": []
    }
  ],
  "summary": {
    "gate_count": 4,
    "passed": 3,
    "with_findings": 1,
    "finding_count": 1
  }
}
```

Verantwortlich:

- Governance Maintainer schreibt und versioniert die OPA-Policies.
- Product Architect und Application Team liefern Evidence, damit Findings reduziert werden.

## Schritt 15: Remediation Actions werden ergänzt

Wenn Findings entstehen, versucht der Report-Generator passende Empfehlungen aus:

```text
architecture/remediation-actions.yaml
```

zu ergänzen.

Dadurch wird aus einem Finding nicht nur ein Fehlertext, sondern eine handlungsfähige Empfehlung.

Verantwortlich:

- Governance Maintainer pflegt Remediation Actions.
- Application Team und Architekturrollen setzen die Maßnahmen um.

## Schritt 16: Architektur-Evidence wird als Artifact hochgeladen

Der Workflow lädt die erzeugten Dateien hoch:

```yaml
- name: Upload architecture governance evidence
  uses: actions/upload-artifact@v4
  with:
    name: architecture-governance-evidence
    path: |
      governance/generated/app/architecture-release-input.json
      governance/generated/app/architecture-governance-report.json
      governance/generated/app/architecture-governance-report.md
```

Artifact-Name:

```text
architecture-governance-evidence
```

Dieses Artifact ist die prüfbare Architektur-Evidence des Pipeline-Laufs.

Verantwortlich:

- GitHub Actions speichert das Artifact.
- Governance und Architekturrollen können es herunterladen und reviewen.

## Schritt 17: Optional Findings als Gate erzwingen

Der Workflow besitzt den Input:

```yaml
fail_on_findings: false
```

Wenn `false`, dokumentiert der Workflow Findings, blockiert aber nicht.

Wenn `true`, schlägt der Workflow fehl, sobald `architecture-governance-report.json` Findings enthält.

Das Erzwingen passiert durch Lesen von:

```text
generated/app/architecture-governance-report.json
```

und Prüfung:

```text
summary.finding_count
```

Verantwortlich:

- Governance oder Release Management entscheidet, ab wann Findings blockieren.
- Application Team und Architekturrollen arbeiten Findings ab.

## Schritt 18: Optionaler Intake ins Governance-Repository

Die Architektur-Evidence liegt nach Schritt 16 bereits im GitHub Actions Run des Applikationsrepos.

Für zentrale Sichtbarkeit kann das Governance-Repository den Run intaken.

Das relevante Skript ist:

```text
scripts/intake_architecture_github_actions_run.py
```

Beispiel:

```bash
python3 scripts/intake_architecture_github_actions_run.py \
  --repository-id joku-dev/ha-CPsWMS \
  --run-id 28592256765 \
  --architecture-baseline-ref architecture-baseline-l1-v0.1.0
```

Das Skript macht folgende Dinge:

1. Es liest über die GitHub API den Workflow Run.
2. Es sucht das Artifact `architecture-governance-evidence`.
3. Es lädt das Artifact herunter.
4. Es liest `architecture-release-input.json`.
5. Es liest `architecture-governance-report.json`.
6. Es prüft, ob der Branch geschützt ist.
7. Es schreibt einen normalisierten Architektur-Status-Snapshot.

Verantwortlich:

- Governance Automation führt den Intake aus.
- GitHub stellt Run- und Artifact-Daten bereit.
- Governance Repository speichert den zentralen Status.

## Schritt 19: Zentrale Architektur-Statusdatei wird geschrieben

Der Intake schreibt nach:

```text
status/architecture-results/<owner>__<repo>/<timestamp>-run-<run-id>.json
```

Beispiel:

```text
status/architecture-results/joku-dev__ha-CPsWMS/2026-07-02T13-05-12Z-run-28592256765.json
```

Diese Datei ist nicht dasselbe wie `architecture-release-input.json` oder `architecture-governance-report.json`.

Der Unterschied:

| Datei | Ort | Zweck |
|---|---|---|
| `architecture-release-input.json` | GitHub Actions Artifact des Applikationsrepos | Normalisierte Architektur-Evidence als Input für Gates. |
| `architecture-governance-report.json` | GitHub Actions Artifact des Applikationsrepos | Ergebnis der Architektur-Gates und Findings. |
| `status/architecture-results/...json` | Governance-Repository | Verdichtete zentrale Statussicht für Reporting und Viewer. |

Beispielhafte zentrale Statusstruktur:

```json
{
  "schema_version": "1.0.0",
  "repository_id": "joku-dev/ha-CPsWMS",
  "architecture_baseline_ref": "architecture-baseline-l1-v0.1.0",
  "governance_repository": "joku-dev/devsecops-governance-as-code",
  "result_type": "architecture-runtime-governance-run",
  "pipeline": {
    "pipeline_name": "Architecture Runtime Governance",
    "pipeline_run_id": "28592256765",
    "event": "push",
    "status": "success"
  },
  "repository": {
    "branch": "main",
    "branch_protected": true,
    "commit_id": "..."
  },
  "evidence": {
    "release_input": true,
    "architecture_report": true,
    "marker_assessments": 32,
    "release_compatibility_declaration": true,
    "solution_baseline": true,
    "security_evidence": true,
    "deployment_evidence": true,
    "runtime_evidence": true
  },
  "architecture_summary": {
    "gate_count": 4,
    "passed": 4,
    "with_findings": 0,
    "finding_count": 0
  },
  "overall_status": "pass"
}
```

Verantwortlich:

- Governance Automation erzeugt den Snapshot.
- Governance Maintainer reviewt zentrale Statusdaten.

## Schritt 20: Viewer und Docs werden aktualisiert

Nach dem Intake kann der Status-Viewer aktualisiert werden:

```bash
python3 scripts/generate_status_viewer.py
```

Der Viewer nutzt unter anderem:

```text
status/architecture-results/
status/architecture-results-index.json
generated/viewer/status-viewer.html
```

Danach veröffentlicht `Publish Docs` die MkDocs-Seite nach GitHub Pages.

Verantwortlich:

- Governance Automation erzeugt Viewer-Artefakte.
- GitHub Pages veröffentlicht die Dokumentation.

## Was ist manuell und was ist automatisiert?

Manuell oder fachlich kontrolliert:

- Architekturentscheidungen
- Solution Baseline
- Release Compatibility Declaration
- Review-Status
- Approval
- bekannte Einschränkungen
- Follow-up Actions
- Referenzen auf echte Nachweise
- fachliche Einschätzung, ob Evidence `draft`, `reviewed` oder `approved` ist

Automatisch:

- Checkout von App- und Governance-Repo
- Einsammeln der `.governance/architecture/*.json`
- Erkennen von Architektur-, Deployment-, Test-, Schema- und Runtime-Signalen
- Erzeugen von `architecture-release-input.json`
- Schema-Validierung
- OPA-Gate-Auswertung
- Erzeugen von `architecture-governance-report.json`
- Erzeugen von `architecture-governance-report.md`
- Upload von `architecture-governance-evidence`
- optional Intake nach `status/architecture-results/...json`
- optional Viewer-Aktualisierung

## Kompletter Ablauf als Checkliste

| Schritt | Wer | Was | Ergebnis |
|---|---|---|---|
| 1 | Application Team / Architect | `.governance/architecture/` anlegen. | Strukturierte Architektur-Evidence |
| 2 | Architect / Reviewer | Status `draft`, `reviewed` oder `approved` setzen. | Bewertbarer Evidence-Status |
| 3 | Application Team | Architektur-, Deployment-, Test- und Schema-Dateien pflegen. | Technische Architekturartefakte |
| 4 | DevSecOps Engineer | Workflow anlegen. | `.github/workflows/architecture-governance.yml` |
| 5 | GitHub Actions | Pipeline starten. | Run mit Commit- und Event-Kontext |
| 6 | GitHub Actions | Applikationsrepo auschecken. | `application/` |
| 7 | GitHub Actions | Governance-Repo auschecken. | `governance/` |
| 8 | Workflow | Python-Abhängigkeiten und OPA installieren. | Ausführbare Prüfwerkzeuge |
| 9 | Collector | Architektur-Evidence sammeln. | `architecture-release-input.json` |
| 10 | Collector | Target- und Architecture-Abschnitte schreiben. | Normalisierte Evidence |
| 11 | Collector | Marker Assessments berechnen. | Scores und Evidence-Refs |
| 12 | Workflow | Schema validieren. | Gültiger Architektur-Input |
| 13 | Report Generator | Report erzeugen. | JSON- und Markdown-Report |
| 14 | OPA | Architektur-Gates bewerten. | Pass oder Findings |
| 15 | Report Generator | Remediation Actions ergänzen. | Handlungsempfehlungen |
| 16 | GitHub Actions | Evidence hochladen. | Artifact `architecture-governance-evidence` |
| 17 | Workflow | Optional Findings erzwingen. | Blockierender oder nicht blockierender Gate-Status |
| 18 | Governance Automation | Optional Run intaken. | Zentraler Architektur-Snapshot |
| 19 | Governance Repo | Statusdatei speichern. | `status/architecture-results/...json` |
| 20 | Governance Automation | Viewer aktualisieren. | Sichtbarer Architekturstatus |

## Häufige Fehlerquellen

| Fehler | Ursache | Lösung |
|---|---|---|
| Viele Findings trotz vorhandener Dateien | Evidence steht auf `draft` statt `approved`. | Review durchführen und Status kontrolliert auf `approved` setzen. |
| Release Readiness Finding | Release Compatibility Declaration fehlt oder ist nicht approved. | `release-compatibility-declaration.json` ergänzen und freigeben. |
| Solution Baseline Finding | Solution Baseline fehlt. | `solution-baseline.json` ergänzen. |
| Security Findings | Security Evidence oder Security Tests fehlen. | `security-evidence.json`, Security Tests oder Security Review referenzieren. |
| Operation Readiness Findings | Runtime-, Monitoring- oder Operations-Nachweise fehlen. | `operation-evidence.json`, Runbooks, Health Checks oder Monitoring-Referenzen ergänzen. |
| Resilience Findings | Recovery-, Failover- oder Degraded-Mode-Nachweise fehlen. | `resilience-evidence.json` und passende Tests oder Betriebsnachweise ergänzen. |
| Schema-Validierung schlägt fehl | JSON-Struktur ist ungültig. | Gegen `schemas/app-architecture-evidence.schema.json` prüfen. |
| Workflow erzeugt keine zentrale Statusdatei | Intake wurde nicht ausgeführt. | `scripts/intake_architecture_github_actions_run.py` mit Run-ID ausführen. |

## Merksatz

Bei Architektur-Governance pflegen Menschen die fachlichen Architektur-Nachweise. Die Pipeline erzeugt daraus automatisch den Architektur-Input, bewertet ihn gegen Gates und schreibt die JSON-Reports. Die finale Architektur-Governance-JSON wird nicht händisch gepflegt.
