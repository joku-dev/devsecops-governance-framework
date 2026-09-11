# DevSecOps Governance Repository: Zweck, Nutzen und Funktionsweise

Stand: **11. September 2026**, geprüfter Implementierungs- und Ergebnisstand
`4abe88294f299d7f801c74ff0161df234960c092`.
Dieser Artikel erläutert die vorhandenen Funktionen. Für den laufenden Betrieb
sind das [Betriebshandbuch](../operations/guides/governance-repository-operations-handbook.md)
und die jeweils angenommenen Ergebnisse maßgeblich.

## Kurzfassung

Das Repository `devsecops-governance-framework` verbindet fachliche Vorgaben mit
strukturierten Kontrollmodellen, ausführbaren Prüfungen und nachvollziehbaren
Ergebnissen aus Anwendungs-Repositories. Es unterstützt damit Entscheidungen
über Softwarelieferungen und deren Nachweise.

Governance-Verantwortliche entscheiden, welche Anforderungen gelten. Das
Framework prüft die technisch auswertbaren Teile, dokumentiert Befunde und
stellt sie für Review, Audit und Betrieb bereit. Seine Referenzimplementierung
verwendet Git, GitHub Actions, Python, JSON-Schemas und OPA/Rego. Die Architektur
trennt diese Werkzeuge von den fachlichen Governance-Modellen.

Für den derzeitigen Testbetrieb ist keine zusätzliche Datenbank und kein
Anwendungsserver erforderlich. Git hält strukturierte Modelle und normalisierte
Ergebnisse; ein statischer Viewer zeigt daraus abgeleitete Übersichten.

## Welches Problem löst das Repository?

Vorgaben in Word, PDF oder Confluence bleiben wichtige fachliche Referenzen.
Im Lieferprozess müssen Teams daraus jedoch konkrete Fragen beantworten:
Welche Kontrollen gelten, welche Nachweise sind erforderlich, zu welchem
Softwarestand gehören sie und wer entscheidet über Abweichungen?

Das Framework verbindet diese Informationen über stabile Identitäten und
versionierte Beziehungen. Wiederverwendbare Baselines vermeiden mehrfach
gepflegte Prüflogik. Ergebnisformate und Quellenverweise erleichtern gemeinsame
Reviews. Ob dadurch Aufwand und Entscheidungszeiten sinken, muss der Testbetrieb
messen; bisher gibt es dafür keine belastbaren Einsparungszahlen.

## Aufbau des Repositories

| Bereich | Aufgabe |
|---|---|
| `docs/` | Erklärungen, Betriebsanleitungen, Onboarding und Veröffentlichungen. |
| `docs/governance/source-documents/` | Öffentliche Platzhalter für Quellenherkunft und Review-Status; Originalquellen sind teilweise zurückgehalten. |
| `model/` | Quellenregister, Anforderungen, Controls, Plattformzuordnungen, Evidenzverträge, Trust- und Enforcement-Modelle. |
| `governance/` | Rollen-, Reporting-, Waiver- und Adoption-Regeln. |
| `architecture/` | Architekturlevel, Guardrails, Quality Marker und Review Gates. |
| `pipeline-baseline/` | Toolunabhängige Pipeline-Baseline und Integrationsvorlagen. |
| `policies/opa/` und `schemas/` | Ausführbare Prüfregeln und zulässige Datenstrukturen. |
| `.github/workflows/` und `scripts/` | Wiederverwendbare Prüfungen, Intake, Generatoren und Validierung. |
| `.agents/`, `.codex/` und `tests/agent_harness/` | Rollenverträge, Agentenadapter und deterministische Routing-Prüfungen. |
| `status/` | Angenommene Ergebnissnapshots, Historie, Intake-Ereignisse und Indizes. |
| `generated/` | Abgeleitete Berichte, Governance-Graph und Status-Viewer. |
| `releases/` | Veröffentlichte, kontrolliert versionierte Baseline-Pakete. |

Die freigegebenen Baselines sind **DevSecOps L1 `l1-baseline-v1.1.3`** und
**Architecture L1 `architecture-baseline-l1-v0.1.0`**. Modellierte L2-/L3-Inhalte
bedeuten noch keine entsprechende freigegebene Betriebsreife.

## Funktionsweise in sechs Schritten

### 1. Quellen aufnehmen und fachlich entscheiden

Neue Artefakte werden zuerst eingeordnet. Mögliche neue oder ersetzende
Governance-Quellen werden als Kandidaten registriert. Menschen prüfen
Gültigkeit, Überschneidungen und Auswirkungen, bevor daraus aktive Kontrollen
oder Baselines abgeleitet werden. Ein Governance Change Request dokumentiert
die Änderung. Herkunfts-, Impact- und Delta-Berichte unterstützen das Review.

### 2. Modelle und Regeln pflegen und validieren

Fachliche Anforderungen werden mit Controls, erwarteten Nachweisen,
Plattformfähigkeiten und OPA-Regeln verknüpft. Architekturmodelle ergänzen
Guardrails, Marker und Gates. Automatische Prüfungen betreffen die objektiv
auswertbaren Angaben; fachliche Freigaben bleiben menschliche Entscheidungen.

Vor einem Commit werden die vollständigen Prüfungen mit der festgelegten
Toolchain ausgeführt:

```bash
./scripts/bootstrap_validation_env.sh
./scripts/validate_all.sh
```

Dazu gehören OPA-, Runtime-, Schema-, Konsistenz-, Provenance- und Regressionstests.
Für Dokumentationsänderungen wird zusätzlich der strenge MkDocs-Build geprüft.

### 3. Identifizierbare Baselines veröffentlichen

Ein Release bindet Modelle, Regeln, Schemas und Metadaten an einen festgelegten
Prüfstand. Consumer verwenden einen veröffentlichten Tag oder einen geprüften
Commit. Änderungen an einer bestehenden Release-Datei dürfen die Bedeutung einer
bereits verwendeten Baseline nicht nachträglich verändern.

### 4. Nachweise im Anwendungs-Repository erzeugen

Das Anwendungsteam erstellt Build-Artefakte, SBOMs, Schwachstellenberichte und
gegebenenfalls Architektur- und weitere Governance-Nachweise. Ein
wiederverwendbarer Workflow bewertet die Eingaben anhand der gewählten Baseline.

Die Auswertung gehört zu einem konkreten Repository, Commit, Lauf und Ereignis.
Ein vollständiger Control-Report und ein zusammengefasster Baseline-Gate-Report
haben unterschiedliche Aussagekraft. Ein bestandenes einzelnes Gate belegt
nicht automatisch die Prüfung des gesamten Kontrollkatalogs.

### 5. Ergebnisse sammeln, verifizieren und reviewen

Ein Consumer-Ereignis oder manueller Workflow-Aufruf startet den zentralen
Intake. Dieser lädt Laufmetadaten und Artefakte, normalisiert das Ergebnis und
prüft den verfügbaren Trust-Kontext. DevSecOps verwendet einen
`control-evaluation-report.json` oder als Fallback einen
`baseline-gate-result.json`; Architektur und typisierte Evidenz haben eigene
Intake-Pfade. `pipeline-evidence.json` ist ein ergänzender Nachweis und ersetzt
nicht diese ausgewerteten Ergebnisse.

Die Automation eröffnet einen begrenzten Bot-PR. Erst erfolgreiche Checks,
Review und Merge übernehmen die Daten offiziell nach `main`. Derselbe Snapshot
bleibt bei einer identischen Wiederholung unverändert; abweichende Daten zur
gleichen Identität werden als Konflikt erhalten. Fehlgeschlagene Sammlungen und
Intake-Ereignisse bleiben nachvollziehbar. Zulässige Wiederholungen werden
kontrolliert durch einen Operator ausgelöst.

### 6. Ergebnisse anzeigen und Maßnahmen verfolgen

Generatoren erstellen Domänenindizes, Portfolio-Berichte, Readiness-Projektionen,
den Governance-Graph und den Viewer. Der Graph macht Beziehungen zwischen
Quellen, Kontrollen, Baselines, Anwendungen, Läufen und Nachweisen untersuchbar.
Er ist eine abgeleitete Ansicht und verändert keine Entscheidungen.

Die offizielle Auswahl bevorzugt vorhandene `push`-Ergebnisse auf `main`.
Branch-, PR- und manuelle Diagnoseläufe bleiben in der Historie sichtbar.
Ein täglicher Betriebsbericht ergänzt die angenommenen Daten um Beobachtungen
zu Workflows, PRs, Evidenzalter, Intake und Repository-Sicherheit. Er erzeugt
selbst keine Aufgaben oder Warnmeldungen; Verantwortliche müssen ihn auswerten.

## Drei getrennte Aussagen lesen

| Signal | Bedeutung |
|---|---|
| Workflow-Status | Ist die technische Ausführung erfolgreich abgeschlossen? |
| Governance-Ergebnis | Welche ausgewerteten Anforderungen bestehen oder erzeugen Befunde? |
| Evidence Trust | Wie weit sind Identität, Integrität, Herkunft, Aktualität und Wiederverwendung der Nachweise geprüft? |

Ein erfolgreicher Workflow kann fachliche Befunde enthalten. `integrity_verified`
belegt geprüfte Integrität innerhalb des vorhandenen Kontexts und ist keine
allgemeine Compliance- oder Produktionsfreigabe. Typisierte Schwachstellenevidenz
wird separat verifiziert. Der Attestierungsmechanismus ist als technischer Pilot
vorhanden; die Freigabe produktiver Aussteller und Schlüsselprozesse bleibt offen.

## Report-only und verpflichtende Gates

Neue Consumer-Piloten wählen ausdrücklich `governance_mode: report-only` für
alle Trigger und `fail_on_findings: false` für Architektur. Der veröffentlichte
DevSecOps-Wrapper hat dagegen standardmäßig `block-on-error`; deshalb muss der
Pilotmodus im Consumer gesetzt werden.

Report-only zeigt fachliche Befunde, ohne allein deshalb den Lauf scheitern zu
lassen. Technische Fehler können weiterhin zum Abbruch führen. Blocking lässt
relevante Befunde den Lauf fehlschlagen. Erst die konkrete Branchschutzregel
bestimmt zusätzlich, ob ein solcher Lauf einen Merge verhindert. Ein als
Required Check eingetragener Report-only-Lauf erzwingt keine Befundfreiheit.

Neue verbindliche Gates benötigen erfüllte Readiness-Kriterien, eine
verantwortliche Freigabe und eine separate Consumer-Umstellung. Das ältere
DevSecOps-Blocking von `ha-CPsWMS` bleibt ein dokumentiertes Bestandsrisiko mit
Review-Frist **12.12.2026, 23:59:59 Europe/Berlin**.

## Belegter Stand am 11. September 2026

| Consumer | Angenommenes Ergebnis | Einordnung |
|---|---|---|
| `ha-CPsWMS` | DevSecOps: 16/16 anwendbare Controls bestanden; Architektur: 4/4 Gates, 0 Befunde. | Separater DevSecOps-Replay-Befund bleibt offen. |
| `ai-native-engineering-factory` | DevSecOps-Baseline-Gate fehlgeschlagen wegen gemeldetem erlaubtem Direkt-Push. | Report-only; zusammengefasste Gate-Auswertung. |
| `governance-framework-demo-consumer` | DevSecOps-Gate bestanden; Architektur: 25 Befunde; typisierte Evidenz mit geprüfter Integrität. | Report-only; Gate-Ergebnis ist kein vollständiger Kontrollkatalog. |

Das Portfolio enthält drei Consumer und zum festgehaltenen Beobachtungszeitpunkt
keine veralteten oder fehlenden in den Bericht einbezogenen Nachweise. Die
Blocking-Readiness bleibt **0 von 3**. Neue Läufe oder das Alter der Nachweise
können diese Aussagen verändern. Lauf-IDs und Quellen stehen im
[aktuellen Plattformstand](../operations/status/current-governance-platform-state.md).

## Einführung und Verantwortlichkeiten

1. Sponsor, Maintainer, Stellvertretung, Consumer-Eigentümer und Reviewer benennen.
2. Pilotumfang, Baseline-Pins, Zeitraum und Entscheidungstermin festhalten.
3. Consumer-Workflows mit explizitem Report-only-Modus integrieren.
4. Echte Nachweise erzeugen und ihren vollständigen Weg durch Intake, Review und Veröffentlichung prüfen.
5. Fehlerfälle, Wiederholungen, Zugänge und Wiederherstellung im vereinbarten Testkontext erproben.
6. Den täglichen Bericht auswerten und Befunde mit Eigentümern und Maßnahmen verfolgen.
7. Nutzen, Aufwand und offene Risiken dokumentieren und über die Fortsetzung entscheiden.
8. Neue Blocking-Gates erst nach dem gesonderten Readiness- und Freigabeverfahren aktivieren.

Governance Owner verantworten Vorgaben und Ausnahmen. Security und Architektur
prüfen die fachlichen Aussagen. Plattformverantwortliche betreiben die zentralen
Mechanismen. Anwendungsteams erzeugen geeignete Nachweise. Auditoren und
Management nutzen die dokumentierten Beziehungen und Ergebnisse für ihre Reviews.

## Weiterführende Dokumentation

- [Detaillierter Funktionskatalog](../operations/guides/repository-function-catalog.md)
- [Betriebshandbuch](../operations/guides/governance-repository-operations-handbook.md)
- [Consumer-Pilot](../onboarding/pilot-runbook.md)
- [Evidence Trust](../operations/evidence/evidence-trust-model.md)
- [Ergebnisaufnahme und Viewer](../operations/evidence/governance-result-intake-and-viewer-usage.md)
- [Blocking Readiness](../operations/status/blocking-readiness.md)
- [Whitepaper und Präsentation für die Geschäftsführung](executive-briefing/README.md)
