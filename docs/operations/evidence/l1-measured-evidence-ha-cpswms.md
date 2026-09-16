# L1 mit gemessenen Nachweisen in ha-CPsWMS

Stand: 16. September 2026. Referenz ist die unveränderte DevSecOps-Baseline
`l1-baseline-v1.1.3` mit 16 Kontrollen. Die Erweiterung ist in
[ha-CPsWMS PR #16](https://github.com/joku-dev/ha-CPsWMS/pull/16) umgesetzt.

## Was ausgeführt wird

Der zusätzliche Consumer-Workflow **L1 Measured Evidence** führt Anwendungstests,
SAST, echte HTTP-/Neo4j-Integration, Container-Builds, CycloneDX-SBOM-Erzeugung und
Trivy-Scans aus. Die vier Anwendungsimages und das Neo4j-Image werden unter ihrer
exakten Image-ID untersucht und als Archive gespeichert. Die Query-Integration
verwendet das zuvor gebaute und gescannte Archiv. Ein mit fünf Knoten und
Beziehungen befüllter Testgraph ersetzt den bisher leeren Benchmark als Grundlage
für konkrete Ergebnisassertionen. Ein Datenbankausfall samt Wiederanlauf wird
gegen die echte HTTP-API geprüft.

GitHub-API-Abfragen liefern Commit-, PR-, Review- und Schutzeinstellungen.
403/fehlende Rechte bleiben Nachweislücken. Tests, Scans, Laufzeiten, Exit-Codes,
SBOMs und Deployment-IDs erhalten maschinenlesbare Artefakte. Der Aggregator
prüft heruntergeladene Dateien gegen Run-/Commit-Bindung und SHA-256-Manifeste.

Die konkrete [Consumer-Anleitung und Kontrollmatrix](https://github.com/joku-dev/ha-CPsWMS/blob/main/docs/quality/L1_MEASURED_EVIDENCE.md)
nennt alle 16 Kontrollen, ausführbare Werkzeuge und verbleibende Grenzen.

## Bedeutung der Ergebnisse

`l1-control-coverage` enthält `l1-coverage.json` und `l1-coverage.md`.
Der neue Bericht beschreibt **Nachweisabdeckung**, keine vollständige
L1-Konformität oder Produktionsfreigabe:

| Status | Bedeutung |
|---|---|
| `measured` | Der benannte technische Nachweis wurde erzeugt und geprüft |
| `partial` | Nachweise liegen vor, weitere Teile der Kontrollanforderung fehlen |
| `findings` | Tatsächliche Werkzeugbefunde brauchen Bewertung |
| `gap` | Nachweise fehlen, sind ungültig oder nicht zugänglich |

Ein Scanner-Exitcode mit Findings wird von einem Werkzeugabsturz unterschieden.
Testfehler und fehlende/inkonsistente Ausgaben lassen die Ausführung fehlschlagen;
Governance-/Security-Findings bleiben report-only. Es wird kein neuer Required
Check gesetzt. Der registrierte bisherige ha-CPsWMS-Blocking-Modus bleibt getrennt.

## Noch offene Kontrollbestandteile

- Vollständige freigegebene Systemanforderungen und Abdeckung aller Komponenten
  einschließlich tatsächlicher Testfall-/Berichtszuordnung (L1-001).
- Vollständig lesbare und bewertete Branch-/Bypass-Konfiguration (L1-003).
- Fachliche Bewertung der SAST-/CVE-Befunde, keine automatisch behauptete
  Review oder Risikofreigabe (L1-004/010).
- Gelockte Python-Auflösung und Nachweis reproduzierbarer Builds (L1-007).
- Release-Archivierung, Zugriffsschutz und unabhängige Provenienz ergänzend zur
  Prüfung von Dateiintegrität (L1-011).
- Autorisierte Deployment-Freigabe und ausschließlich freigegebene Artefakte in
  einer konkret benannten Zielumgebung (L1-013/014).
- Betriebsregister und Aufbewahrung relevanter Security-Ereignisse außerhalb
  der kurzlebigen CI-Umgebung (L1-016).

Die CI nutzt weder eine reale Home-Assistant-Instanz noch bezahlte LLM-Aufrufe.
Sie erzeugt keine Produktions-SLOs oder repräsentative Lasttestergebnisse.

## Verhältnis zu Baseline, Intake und Viewer

Die bisherige L1-Auswertung kann auf deklarierte Eingabefelder zurückgreifen.
Ihr `16/16 pass` ist deshalb kein Ersatz für den neuen Bericht über tatsächlich
vorliegende Nachweise. Historische Berichte bleiben unverändert erhalten.

Die ergänzende Abdeckungsanalyse ist ein eigener Consumer-Artefakttyp und wird
nicht unter dem bestehenden Compliance-Vertrag als offizieller PASS eingespielt.
Der Viewer behält seine tatsächlichen Intake-Snapshots. Eine spätere Integration
benötigt eine explizite Zuordnung dieses Evidenztyps und dessen Statussemantik.
Die freigegebene Baseline, OPA-Regeln und beide akzeptierten Lifecycle-Piloten
werden durch diese Erweiterung nicht geändert.
