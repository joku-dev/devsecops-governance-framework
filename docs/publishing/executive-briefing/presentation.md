# Engineering Governance Präsentation für die Geschäftsführung

Quellstand: `4abe88294f299d7f801c74ff0161df234960c092`. Vorgesehene Vortragsdauer etwa 15 Minuten.

## Folie 1 Engineering Governance

Nutzen und Einführung für die Geschäftsführung

### Sprechernotizen

Ziel ist eine Entscheidung über einen kontrollierten Testbetrieb. Die Plattform verbindet fachliche Vorgaben mit ausgewählten automatisierten Prüfungen. Der Vortrag beschreibt den Stand vom 11. September 2026 und keine bestätigte unternehmensweite Betriebsreife.

Quellen: [1](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/docs/foundation/05_CURRENT_DIRECTION.md), [5](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/docs/operations/guides/governance-repository-operations-handbook.md)

## Folie 2 Entscheidung über einen begrenzten Pilot

Ein bis zwei Anwendungen, vorgeschlagen zwei Wochen

- **Startvoraussetzung:** Benannte Verantwortliche, aktuelle Nachweise und eingeplante Kapazität

- **Betriebsmodus:** Befunde sichtbar machen, neue Piloten ausdrücklich Report-only

- **Abschluss:** Beobachteten Nutzen, Aufwand und Risiken gemeinsam bewerten

### Sprechernotizen

Die zwei Wochen sind ein Vorschlag für die Beobachtung nach der Vorbereitung. Es gibt noch keine Aufwandsschätzung oder Budgetfreigabe. Ein Pilotbeschluss erlaubt keine neuen verbindlichen Lieferstopps.

Quellen: [5](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/docs/operations/guides/governance-repository-operations-handbook.md), [7](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/generated/reports/blocking-readiness.json)

## Folie 3 Geschäftlicher Ausgangspunkt

Softwareentscheidungen brauchen nachvollziehbare Nachweise

- **Geltende Vorgaben:** Welcher Regelsatz gilt für diese Softwareversion?

- **Belegbare Ergebnisse:** Welche Prüfung stützt die Entscheidung und wie aktuell ist sie?

- **Offene Verantwortung:** Wer bearbeitet Abweichungen und entscheidet über Ausnahmen?

### Sprechernotizen

Das ist die Problemstellung des Projekts. Die konkrete Ausgangslage und der heutige Aufwand müssen für die Pilotanwendungen noch erhoben werden.

Quellen: [1](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/docs/foundation/05_CURRENT_DIRECTION.md), [3](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/docs/foundation/02_CONSTITUTION.md), [4](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/docs/operations/evidence/governance-evidence-contract.md)

## Folie 4 Erwarteter Nutzen und Messung

Der Pilot prüft den Nutzen statt Einsparungen vorauszusetzen

| Nutzenhypothese | Beobachtung |
|---|---|
| Weniger Nachweisaufwand | Zeit für ein vergleichbares Nachweispaket |
| Weniger Rückfragen | Ursachen fachlicher Nachforderungen |
| Klarere Bearbeitung | Zeit bis zur Zuordnung offener Befunde |
| Tragfähiger Betrieb | Pflegeaufwand und ungeklärte Fehler |

### Sprechernotizen

Es liegen keine belastbaren ROI- oder Einsparungswerte vor. Dieselben ausgewählten Aufgaben sollen vor und während der Erprobung beobachtet werden. Eine kleine Stichprobe liefert eine erste Einschätzung.

Quellen: [4](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/docs/operations/evidence/governance-evidence-contract.md), [5](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/docs/operations/guides/governance-repository-operations-handbook.md), [9](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/docs/operations/status/daily-governance-operations.md)

## Folie 5 Funktionsweise im Überblick

Anwendungsteams liefern Nachweise, die Zentrale prüft und bündelt

| Ebene | Aufgabe |
|---|---|
| Vorgaben | Fachliche Eigentümer legen die Anforderungen fest |
| Modell | Kontrollen und erwartete Nachweise verbinden |
| Auswertung | Softwarestand gegen versionierte Regeln prüfen |
| Berichte | Nach Review Ergebnisse und offene Punkte anzeigen |

### Sprechernotizen

Diese vier Ebenen beschreiben die Architektur. Heute bilden GitHub Actions und OPA die Referenzimplementierung. Plattformunabhängigkeit ist das Ziel, keine Zusage bereits gleichwertig erprobter Adapter.

Quellen: [2](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/docs/foundation/04_REFERENCE_ARCHITECTURE.md), [4](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/docs/operations/evidence/governance-evidence-contract.md), [6](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/docs/operations/evidence/governance-result-intake-and-viewer-usage.md)

## Folie 6 Menschliche Verantwortung

Automatisierte Befunde unterstützen die Entscheidung

- **Verantwortliche der Anwendung:** Verantworten die erzeugten Nachweise und die Behebung von Befunden

- **Governance und Security:** Bewerten Regeln, Ausnahmen und fachliche Risiken

- **Zentraler Betrieb:** Sichert Aufnahme, Review, Beobachtung und Wiederherstellung

### Sprechernotizen

Individuelle Personen und Stellvertretungen müssen vor Pilotbeginn benannt werden. Ein erfolgreicher automatisierter Lauf bedeutet keine pauschale Sicherheits-, Compliance- oder Produktionsfreigabe.

Quellen: [3](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/docs/foundation/02_CONSTITUTION.md), [5](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/docs/operations/guides/governance-repository-operations-handbook.md), [11](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/docs/operations/security/github-access-and-token-maintenance.md)

## Folie 7 Belegter Entwicklungsstand

Die Referenzimplementierung ist vorhanden

| Vorhanden | Noch im Pilot zu belegen |
|---|---|
| Versionierte Regeln und Prüfungen | Eignung für ausgewählte Anwendungen |
| Aktuelle Ergebnisse für drei Consumer | Wiederholbarkeit und Befundbearbeitung |
| Betriebsbericht und Anleitungen | Verlässliche Bearbeitung im Alltag |
| Lokale Git-Wiederherstellung | Vollständiger Wiederanlauf mit Zugängen |

### Sprechernotizen

Der Quellstand 4abe882 enthält veröffentlichte Baselines, geschützte PR-Abläufe und tägliche Betriebsberichte. Governance CI, CodeQL, Self-Security und Dokumentationsveröffentlichung waren erfolgreich. Neue reale Ergebnisse für drei Consumer sind angenommen. Die Tabelle trennt technische Verfügbarkeit von längerfristiger Betriebserprobung.

Quellen: [5](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/docs/operations/guides/governance-repository-operations-handbook.md), [8](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/status/repository-results-index.json), [9](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/docs/operations/status/daily-governance-operations.md), [13](https://github.com/joku-dev/devsecops-governance-framework/actions/runs/34611502655), [14](https://github.com/joku-dev/devsecops-governance-framework/actions/runs/34611502609), [15](https://github.com/joku-dev/devsecops-governance-framework/actions/runs/34611502982), [16](https://github.com/joku-dev/devsecops-governance-framework/actions/runs/34611502768), [18](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/generated/reports/portfolio-onboarding-status.json)

## Folie 8 Angenommene Anwendungsergebnisse

ha-CPsWMS am 11. September 2026

- **16 von 16:** Anwendbare DevSecOps-Kontrollen bestanden

- **4 von 4:** Architekturgates bestanden

Separater Replay-Befund bleibt offen · keine Produktionsfreigabe

### Sprechernotizen

Neue main-push-Läufe: DevSecOps 34602002201, Architektur 34602001140, Consumer-Commit 6976bb2af2b9d47d2934273c444b6c9b62a81ea2. 16 von 16 anwendbaren Controls bestehen, 30 weitere sind nicht anwendbar. Architektur: vier von vier Gates, null Befunde. Der separate DevSecOps-Replay-Check bleibt fehlgeschlagen. Die Factory meldet einen Branchschutz-Befund, der neutrale Demo-Consumer 25 Architektur-Befunde. Dessen DevSecOps-pass ist ein einzelnes zusammengefasstes Baseline-Gate. Das Portfolio enthält drei Consumer ohne veraltete oder fehlende Ergebnisse im Beobachtungszeitpunkt. Diese Nachweise sind keine Produktionsfreigabe.

Quellen: [8](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/status/repository-results-index.json), [17](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/status/architecture-results-index.json), [18](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/generated/reports/portfolio-onboarding-status.json)

## Folie 9 Voraussetzungen für verbindliche Prüfungen

Die gespeicherte Bewertung sieht keine der drei Integrationen bereit

- **Aktuelle Nachweise:** Herkunft, Integrität und ausreichende Beobachtung prüfen

- **Verantwortliche Freigabe:** Ausnahmen und Rücknahmeweg vor einer Aktivierung festlegen

- **Bestehendes Risiko:** Älterer ha-CPsWMS-Modus mit Überprüfung bis 12. Dezember 2026

### Sprechernotizen

Bewertungsstand: generated_at 2026-09-11T14:34:14Z, drei Integrationen, null ready, drei not_ready und eine bereits blockierende Integration unterhalb der neuen Anforderungen. Aktuelle Typed Evidence des neutralen Consumers ist angenommen, weitere Trust-, Architektur- und Betriebskriterien bleiben offen. Der Bestandsmodus ist keine Freigabe für neues Blocking. Ein erfolgreicher Workflow allein genügt nicht.

Quellen: [7](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/generated/reports/blocking-readiness.json), [12](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/docs/operations/status/blocking-mode-alignment.md)

## Folie 10 Vorgeschlagener Ablauf

Vorbereitung und zwei Wochen Beobachtung

| Phase | Ergebnis |
|---|---|
| Vorbereitung | Umfang, Kapazität, Eigentümer und Zugänge stehen fest |
| Woche 1 | Echte Nachweise durchlaufen Aufnahme und Review |
| Woche 2 | Fehlerbehandlung, Wiederholung und Sicherung erprobt |
| Entscheidung | Fortsetzen, nacharbeiten oder beenden |

### Sprechernotizen

Die Vorbereitung muss vor Beginn der Beobachtung abgeschlossen sein. Absichtliche Fehler werden in einem vereinbarten isolierten Kontext getestet. Produktive Nachweise dürfen nicht zur Simulation umgeschrieben werden.

Quellen: [5](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/docs/operations/guides/governance-repository-operations-handbook.md), [6](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/docs/operations/evidence/governance-result-intake-and-viewer-usage.md), [10](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/docs/operations/processes/governance-repository-backup-and-recovery.md)

## Folie 11 Betriebsaufwand und Grenzen

Der Nutzen setzt eine verbindliche Bearbeitung voraus

- **Aufwand:** Integration, Nachweispflege, Reviews und Befundbearbeitung einplanen

- **Beobachtung:** Täglicher Bericht vorhanden, automatische Alarmierung noch offen

- **Ausweitung:** Skalierung, Aufbewahrung und Wiederanlauf gesondert bewerten

### Sprechernotizen

Für den aktuellen Pilot ist keine zusätzliche Datenbank erforderlich. Die Aufwände sind noch nicht für das Unternehmen beziffert. Der Bericht läuft täglich um 06:43 UTC und sendet selbst keine Warnmeldungen. Zugangspflege, externe Sicherung und Stellvertretung bleiben Aufgaben des Betriebs.

Quellen: [5](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/docs/operations/guides/governance-repository-operations-handbook.md), [9](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/docs/operations/status/daily-governance-operations.md), [10](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/docs/operations/processes/governance-repository-backup-and-recovery.md), [11](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/docs/operations/security/github-access-and-token-maintenance.md)

## Folie 12 Nächste Entscheidung

Kontrollierte Erprobung mit klarer Auswertung

- **Festlegen:** Sponsor, Pilotanwendungen, Verantwortliche und verfügbare Kapazität

- **Erproben:** Ergebnisfluss, tägliche Bearbeitung und Nutzenmessung

- **Bewerten:** Fortsetzung anhand dokumentierter Ergebnisse entscheiden

### Sprechernotizen

Empfehlung: begrenzten Pilot vorbereiten, keine pauschale Produktionsfreigabe. Die vollständigen Quellen und die ausführliche Einordnung stehen im begleitenden Whitepaper. Alle Quellen dieser Präsentation sind zusätzlich in den jeweiligen Sprechernotizen verlinkt.

Quellen: [1](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/docs/foundation/05_CURRENT_DIRECTION.md), [3](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/docs/foundation/02_CONSTITUTION.md), [5](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/docs/operations/guides/governance-repository-operations-handbook.md), [7](https://github.com/joku-dev/devsecops-governance-framework/blob/4abe88294f299d7f801c74ff0161df234960c092/generated/reports/blocking-readiness.json)
