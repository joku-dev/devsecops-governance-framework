# Wie das Repository arbeitet

Quellstand: `80ba315e56828f5186303045cc2792b576396c26`. 16 Folien für etwa 20 Minuten.

## 1. Wie das Repository arbeitet

DevSecOps Governance Framework
Vorgaben, Prüfungen und nachvollziehbare Ergebnisse


**Sprechernotizen**

Diese Präsentation erklärt den technischen Ablauf in verständlicher Form. Sie richtet sich an Führungskräfte und technische Verantwortliche. Die Darstellung beschreibt den festgehaltenen Repository-Stand, keinen neuen Anwendungslauf. Für den Vortrag sind etwa 20 Minuten vorgesehen.

Quellen: [1](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/docs/foundation/04_REFERENCE_ARCHITECTURE.md), [13](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/docs/demos/demo-end-to-end-governance.md)

## 2. Der vollständige Governance-Ablauf

Vier Ebenen verbinden fachliche Vorgaben mit der Auswertung von Anwendungen.

- **01  Vorgaben:** Menschen prüfen Quellen und entscheiden, welche Anforderungen gelten.
- **02  Modelle:** Kontrollen, Architekturmarker und Nachweisformate machen Anforderungen strukturiert nutzbar.
- **03  Auswertung:** Versionierte Regeln prüfen die Nachweise einer konkreten Anwendung.
- **04  Übersicht:** Intake und Review übernehmen Ergebnisse in die zentrale Statusanzeige.

**Sprechernotizen**

Die vier Ebenen entsprechen Governance Intent, Governance Model, Governance Runtime und Governance Intelligence. Die Übersetzung einer Quelle in eine Regel verlangt fachliche Arbeit und Review. Das Repository behauptet keine vollautomatische semantische Ableitung aus Dokumenten. Die zentrale Übersicht unterstützt weitere Entscheidungen und Verbesserungen.

Quellen: [1](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/docs/foundation/04_REFERENCE_ARCHITECTURE.md), [2](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/docs/governance/governance-change-lifecycle.md), [6](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/docs/operations/evidence/governance-result-intake-and-viewer-usage.md)

## 3. Zwei Repositories mit klaren Aufgaben

Das Governance-Repository liefert Regeln. Das Anwendungs-Repository liefert Nachweise.

- **Governance-Repository:** Quellen und Modelle pflegen Baselines veröffentlichen Ergebnisse aufnehmen und anzeigen
- **Anwendungs-Repository:** Anwendung bauen und prüfen Nachweise einem Lauf zuordnen Governance-Workflows ausführen

**Sprechernotizen**

Die aktuelle Referenz besteht aus joku-dev/devsecops-governance-framework und joku-dev/ha-CPsWMS. Wiederverwendbare Workflows verbinden beide. Große Laufartefakte bleiben im jeweiligen Artefaktspeicher. Zentral liegen normalisierte Ergebnissnapshots und deren Kontext. Plattformunabhängigkeit ist ein Architekturziel, GitHub Actions ist die gezeigte Integration.

Quellen: [1](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/docs/foundation/04_REFERENCE_ARCHITECTURE.md), [6](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/docs/operations/evidence/governance-result-intake-and-viewer-usage.md), [13](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/docs/demos/demo-end-to-end-governance.md)

## 4. Die wichtigsten Bereiche im Repository

Jeder Bereich hat eine eigene Rolle im Ablauf.

| Bereich | Inhalt und Aufgabe |
| --- | --- |
| docs/governance/ | Quellen, Entscheidungen und Änderungsprozess |
| model/ und architecture/ | Kontrollen, Zuordnungen und Architekturmarker |
| policies/opa/ und schemas/ | Ausführbare Regeln und gültige Datenstrukturen |
| releases/ | Veröffentlichte Baselines |
| status/ und generated/ | Ergebnisgeschichte, abgeleitete Berichte und Viewer |

**Sprechernotizen**

Diese Übersicht ist eine Orientierung für den Repository-Rundgang. Generated-Dateien entstehen normalerweise durch Generatoren. Status-Snapshots entstehen durch Intake. Veröffentlichte Release-Pakete bleiben als Referenz erhalten. Eine manuelle Änderung am Viewer ist kein neuer Anwendungsnachweis.

Quellen: [1](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/docs/foundation/04_REFERENCE_ARCHITECTURE.md), [2](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/docs/governance/governance-change-lifecycle.md), [6](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/docs/operations/evidence/governance-result-intake-and-viewer-usage.md), [9](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/releases/l1/v1.1.3/baseline-package.md), [10](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/releases/architecture/l1/v0.1.0/baseline-package.md)

## 5. Aufnahme und Änderung von Vorgaben

Ein neues Dokument löst zunächst eine fachliche Entscheidung aus.

- **01  Einordnen:** Quelle registrieren und mögliche Dublette oder Ablösung kennzeichnen.
- **02  Entscheiden:** Kandidaten prüfen, Entscheidung festhalten und Auswirkungen bestimmen.
- **03  Umsetzen:** Betroffene Modelle, Regeln und Nachweisverträge gezielt anpassen.
- **04  Freigeben:** Validierung und Review abschließen, Release-Bedarf entscheiden.

**Sprechernotizen**

Der Status candidate hält neue oder möglicherweise ersetzende Quellen von einer ungeprüften Ableitung fern. Die Source-Lineage verknüpft Quellen mit abgeleiteten Artefakten. Generierte Impact- und Delta-Berichte unterstützen Menschen. Sie genehmigen keine Quelle und ändern keine Policy selbstständig. Das öffentliche Repository enthält auch Platzhalter für zurückgehaltene Originalquellen.

Quellen: [2](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/docs/governance/governance-change-lifecycle.md), [13](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/docs/demos/demo-end-to-end-governance.md)

## 6. Eine Anforderung als ausführbare Kontrolle

Beispiel DSCB-L1-REQ-006: Eine SBOM dokumentiert die Software-Komponenten.

- **Vorgabe:** Für auslieferbare Artefakte muss eine Komponentenliste entstehen.
- **Kontrollmodell:** Die Kontroll-ID verbindet Ziel, Nachweise und die zugehörige Policy.
- **Prüfregel:** sbom_required.rego prüft die Existenz und die Zuordnung zum Artefakt.

**Sprechernotizen**

SBOM bedeutet Software Bill of Materials. Im L1-Katalog ist die Anforderung DSCB-L1-REQ-006 mit der Policy policies/opa/sbom_required.rego verbunden. Das Beispiel illustriert eine konkret implementierte Teilprüfung. Die Policy prüft die übergebenen Angaben und beweist allein weder die Vollständigkeit der Komponentenliste noch ihre unabhängige Herkunft.

Quellen: [3](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/model/controls/dscb-l1.yaml), [4](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/policies/opa/sbom_required.rego)

## 7. Die SBOM-Prüfung im Detail

Die folgenden Fälle gelten für release_candidate = true.

| Übergebene Angaben | Ergebnis dieser Policy |
| --- | --- |
| exists = false | Befund: Die SBOM fehlt. |
| exists = true linked_to_artifact = false | Befund: Die Zuordnung zum Artefakt fehlt. |
| exists = true linked_to_artifact = true | Kein SBOM-Befund aus dieser Regel. |

**Sprechernotizen**

In der Policy erzeugt deny eine Meldung, wenn input.evidence.sbom.exists fehlt oder falsch ist. Wenn exists wahr ist, linked_to_artifact aber fehlt oder falsch ist, entsteht eine andere Meldung. Sind beide Werte wahr, erzeugt diese einzelne Policy keinen SBOM-Befund. Das bedeutet nicht, dass alle anderen Kontrollen bestanden sind. Die Beispiele zeigen die tatsächliche Logik, keine neuen Live-Ergebnisse.

Quellen: [4](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/policies/opa/sbom_required.rego)

## 8. Baselines legen den Prüfstand fest

Eine Anwendung bezieht sich auf einen veröffentlichten, identifizierbaren Regelsatz.

- **DevSecOps L1:** l1-baseline-v1.1.3 Kontrollen und Nachweise für den Software-Lieferprozess
- **Architecture L1:** architecture-baseline-l1-v0.1.0 Architekturmodell und Prüfungen zur Einsatzbereitschaft

**Sprechernotizen**

Beide Baselines sind am betrachteten Stand veröffentlicht. Release-Pakete enthalten identifizierbare Modelle, Regeln, Schemas und Metadaten. Tag oder festgelegter Commit verbindet einen Anwendungslauf mit seinem Prüfstand. Eine neue Governance-Version verlangt eine bewusste Übernahme beim Consumer. Die Contract-Version 1.0 beschreibt dagegen die Datenstruktur des DevSecOps-Eingangs und ist keine Baseline-Version.

Quellen: [5](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/docs/operations/evidence/governance-evidence-contract.md), [9](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/releases/l1/v1.1.3/baseline-package.md), [10](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/releases/architecture/l1/v0.1.0/baseline-package.md)

## 9. Ausführung in der Anwendung

Der Architektur-Workflow zeigt den Ablauf als konkretes Beispiel.

- **01  Laden:** Anwendung und Governance-Baseline in getrennte Arbeitsverzeichnisse laden.
- **02  Sammeln:** Anwendungsnachweise zu einem strukturierten Eingang zusammenstellen.
- **03  Prüfen:** Schema validieren und den Governance-Bericht erzeugen.
- **04  Bereitstellen:** Eingang und Berichte als Laufartefakt veröffentlichen.

**Sprechernotizen**

Der Workflow architecture-baseline-l1-v0.1.0.yml checkt application und governance getrennt aus. Der Governance-Checkout verwendet den Baseline-Tag. collect_architecture_release_input.py sammelt den Eingang. Eine JSON-Schema-Prüfung validiert seine Struktur. generate_architecture_governance_report.py erzeugt JSON und Markdown. Das Artefakt heißt architecture-governance-evidence. fail_on_findings steuert gesondert den Abbruch bei Befunden.

Quellen: [7](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/.github/workflows/architecture-baseline-l1-v0.1.0.yml)

## 10. DevSecOps und Architektur prüfen andere Fragen

Die beiden Domänen ergänzen sich und behalten eigene Ergebnisse.

- **DevSecOps:** Wie entstehen Software und Nachweise? Beispiele: Branch-Schutz, SBOM, Schwachstellen und Artefaktintegrität.
- **Architektur:** Welche Voraussetzungen erfüllen Entwurf und Betrieb? Gates: Architecture, Integration, Release und Operation Readiness.

**Sprechernotizen**

DevSecOps kontrolliert Aspekte des Lieferprozesses. Das Architekturmodell beschreibt Marker, erwartete Nachweise und Review-Gates. Die vier Gate-Namen sind im Modell hinterlegt. Automatische Befunde unterstützen die fachliche Entscheidung. Ein grüner Workflow-Lauf ist keine allgemeine Produktionsfreigabe. Die konkrete Abdeckung hängt von Baseline und verfügbaren Nachweisen ab.

Quellen: [3](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/model/controls/dscb-l1.yaml), [8](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/architecture/review-gates.yaml), [13](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/docs/demos/demo-end-to-end-governance.md)

## 11. Die Aufnahme eines Ergebnisses

Ein Ereignis startet die Sammlung. Erst Review und Merge übernehmen den Stand offiziell.

- **01  Auslösen:** Ein Consumer meldet Repository und Lauf-ID oder ein Operator startet den Intake.
- **02  Sammeln:** Der Intake lädt Laufmetadaten und Artefakte und erzeugt einen Snapshot.
- **03  Vorschlagen:** Die Automation erzeugt Projektionen und eröffnet einen begrenzten Bot-PR.
- **04  Übernehmen:** Nach Checks und Review übernimmt main die Daten für die Veröffentlichung.

**Sprechernotizen**

Die aktuelle GitHub-Integration verwendet repository_dispatch oder workflow_dispatch. Intake normalisiert den Laufkontext und dokumentiert die Übernahme. publish_operational_update.py beschränkt Änderungen auf den erlaubten Umfang. Der Bot eröffnet PRs, genehmigt oder merged sie aber nicht. Bei parallelen PRs müssen Konflikte unter Erhalt aller angenommenen Datensätze aufgelöst und Projektionen neu erzeugt werden. Ein erfolgreicher Consumer-Lauf allein aktualisiert daher noch nicht die veröffentlichte Übersicht.

Quellen: [6](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/docs/operations/evidence/governance-result-intake-and-viewer-usage.md), [11](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/.github/workflows/intake-governance-result.yml)

## 12. Ergebnisgeschichte und aktuelle Übersicht

Unveränderliche Snapshots und neu berechenbare Ansichten erfüllen unterschiedliche Aufgaben.

- **Snapshots:** Neue Ergebnisse ergänzen die Geschichte. Identische Wiederholungen bleiben ohne Änderung.
- **Konflikte:** Abweichende Daten zur gleichen Snapshot-Identität landen als Konflikt im separaten Speicher.
- **Projektionen:** Generatoren berechnen Indizes und Viewer aus den gespeicherten Datensätzen.

**Sprechernotizen**

Append-only bedeutet: Ein existierender Ergebnissnapshot wird nicht durch einen anderen Inhalt überschrieben. Konflikte liegen unter status/intake-conflicts/. Result-Indizes und Viewer sind abgeleitete Projektionen. latest_result bevorzugt den letzten main-push-Lauf, wenn ein solcher vorhanden ist. Branch-, PR- und manuelle Ergebnisse bleiben als Historie sichtbar und verdrängen diesen offiziellen Zustand nicht. Eine zusätzliche Datenbank ist für diesen Mechanismus nicht erforderlich.

Quellen: [6](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/docs/operations/evidence/governance-result-intake-and-viewer-usage.md)

## 13. Drei getrennte Signale im Viewer

Technischer Laufstatus, fachlicher Befund und Nachweisvertrauen beantworten eigene Fragen.

| Signal | Was es aussagt |
| --- | --- |
| Workflow-Status | Konnte der technische Ablauf erfolgreich enden? |
| Governance-Ergebnis | Welche ausgewerteten Anforderungen erfüllen die Nachweise? |
| Evidence Trust | Wie weit ist das Vertrauen in die erfassten Nachweise geprüft? |

**Sprechernotizen**

Diese Unterscheidung verhindert eine falsche Interpretation grüner Statusanzeigen. Evidence Trust untersucht unter anderem Integrität, Herkunftsbindung, Aktualität und Replay-Kontext. Ein Hash-Vergleich beweist allein keine inhaltliche Wahrheit. Historische Snapshots können unverified bleiben. Trust und Replay-Triage sind report-only und ändern weder Governance-Ergebnis noch latest_result-Auswahl.

Quellen: [5](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/docs/operations/evidence/governance-evidence-contract.md), [6](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/docs/operations/evidence/governance-result-intake-and-viewer-usage.md), [14](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/docs/operations/evidence/evidence-trust-model.md)

## 14. Report-only und Blocking

Der Ausführungsmodus bestimmt die technische Reaktion auf Befunde.

- **Report-only:** Befunde erscheinen im Bericht. Technische Fehler können den Lauf dennoch stoppen.
- **Blocking:** Relevante Befunde lassen den Lauf scheitern. Branch-Schutz entscheidet über die Wirkung auf einen Merge.

**Sprechernotizen**

Neue Piloten wählen report-only ausdrücklich für alle Trigger. Der wiederverwendbare DevSecOps-Workflow hat dagegen den Default block-on-error. Der Architektur-Wrapper verwendet fail_on_findings=false als Default. Deshalb muss jede konkrete Consumer-Konfiguration geprüft werden. Für ha-CPsWMS besteht ein älteres DevSecOps-Blocking als befristetes Bestandsrisiko mit Überprüfung bis 12. Dezember 2026. Neue verbindliche Gates verlangen Reifeprüfung und Freigabe.

Quellen: [7](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/.github/workflows/architecture-baseline-l1-v0.1.0.yml), [12](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/docs/operations/guides/governance-repository-operations-handbook.md), [13](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/docs/demos/demo-end-to-end-governance.md), [16](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/.github/workflows/devsecops-baseline-reusable.yml)

## 15. Fehlerbehandlung und täglicher Betrieb

Auch fehlgeschlagene Sammlungen brauchen einen sichtbaren und nachvollziehbaren Weg.

- **Fehler erfassen:** Collection Attempts dokumentieren fehlgeschlagene Sammlungen über denselben PR-Weg.
- **Gezielt wiederholen:** Ein Operator startet einen zulässigen Retry. Das ursprüngliche Fehlerereignis bleibt erhalten.
- **Betrieb beobachten:** Der tägliche Bericht zeigt Handlungsbedarf. Verantwortliche verfolgen offene Punkte.

**Sprechernotizen**

Collection Attempts ersetzen keine erfolgreichen Nachweise. Ein später erfolgreicher passender Snapshot kann den Lebenszyklus als resolved darstellen, ohne den alten Datensatz zu verändern. Automatische Retries sind nicht aktiviert. Intake Events erfassen auch erfolgreiche Ausführungen und speisen die Intake-Health-Projektion. Der tägliche Bericht läuft um 06:43 UTC. Er verschickt selbst keine Warnungen und erstellt keine Aufgaben. Publikationsfehler müssen in Actions untersucht werden, ungemergte Datensätze sind noch kein angenommener main-Stand.

Quellen: [6](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/docs/operations/evidence/governance-result-intake-and-viewer-usage.md), [11](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/.github/workflows/intake-governance-result.yml), [12](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/docs/operations/guides/governance-repository-operations-handbook.md), [15](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/docs/operations/status/daily-governance-operations.md)

## 16. Ein Ergebnis bis zur Quelle erklären

Der Repository-Rundgang folgt einer überprüfbaren Frage: Woher stammt diese Aussage?

- **Im Viewer:** Ergebnis und Laufkontext auswählen, Befunde und Trust getrennt lesen.
- **Im Nachweis:** Repository, Commit, Lauf und verwendete Baseline zuordnen.
- **In der Regel:** Kontrolle und Policy über die dokumentierte Herkunft auf die Vorgabe zurückführen.

**Sprechernotizen**

Zum Abschluss kann der Vortragende den Viewer, einen Ergebnis-Snapshot, die Baseline, DSCB-L1-REQ-006 und sbom_required.rego öffnen. Der Demo-Runbook enthält dafür historische ha-CPsWMS-Läufe vom 15. Juli 2026. Diese sind Referenzbelege und keine aktuelle Anwendungsevaluation. Der Nutzen des Systems liegt darin, genau diese Zuordnung nachvollziehbar zu machen und Änderungen kontrolliert fortzuschreiben.

Quellen: [2](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/docs/governance/governance-change-lifecycle.md), [3](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/model/controls/dscb-l1.yaml), [4](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/policies/opa/sbom_required.rego), [6](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/docs/operations/evidence/governance-result-intake-and-viewer-usage.md), [13](https://github.com/joku-dev/devsecops-governance-framework/blob/80ba315e56828f5186303045cc2792b576396c26/docs/demos/demo-end-to-end-governance.md)
