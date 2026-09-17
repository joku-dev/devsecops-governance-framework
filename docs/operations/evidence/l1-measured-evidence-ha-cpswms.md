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

Die ergänzende Abdeckungsanalyse bleibt ein eigener Consumer-Artefakttyp.
Der Viewer zeigt Container-Schwachstellen jetzt in einem separaten Bereich
**Container Security**. Das verändert weder den offiziellen Compliance-PASS noch
die freigegebene Baseline, OPA-Regeln oder akzeptierte Lifecycle-Piloten.

## Container Security im Viewer

[Viewer öffnen](https://joku-dev.github.io/devsecops-governance-framework/generated/viewer/status-viewer.html#measured-security).
Der Bereich zeigt den erfassten Main-Lauf, Datum, Commit und Versuch, Schweregrade,
Image-IDs, Scan-Hashes und einen Vergleich mit dem vorherigen erfassten Main-Lauf.
Die ausklappbare Detailtabelle lässt sich nach HIGH/CRITICAL sowie CVE, Paket oder
Image filtern. Image-/Paketmeldungen und unterschiedliche CVE-IDs werden getrennt
gezählt. Ein kritischer Treffer bleibt sichtbar, auch wenn der Governance-Status
PASS ist. Fehlende Daten werden nicht als null Schwachstellen dargestellt.

Erste erfasste Messpunkte:

| Run | Commit | Kritisch | Hoch | Tests |
|---|---|---:|---:|---:|
| [35128325507](https://github.com/joku-dev/ha-CPsWMS/actions/runs/35128325507) | 9aa1806 | 13 | 373 | 57 |
| [35131185085](https://github.com/joku-dev/ha-CPsWMS/actions/runs/35131185085) | 4c57eb1 | 1 | 332 | 57 |

Der Vergleich zählt Meldungen über fünf Images. Er belegt allein keine Kausalität:
Auch eine geänderte Scanner-Datenbank kann Zahlen ändern. Die
[Consumer-Bewertung](https://github.com/joku-dev/ha-CPsWMS/blob/main/docs/quality/CONTAINER_SECURITY_REMEDIATION.md)
beschreibt die tatsächlich installierten Paketkorrekturen und offenen Gruppen.
Die Hinweise im Viewer sind technische Prüfansätze, keine VEX-Freigabe,
Risikobilligung oder Bestätigung tatsächlicher Ausnutzbarkeit. Insbesondere ist
ein Linux-Headerpaket kein Nachweis über den Kernel einer späteren Staging-VM.

## Wiederholbarer Intake

Der neue, ausdrücklich auf `joku-dev/ha-CPsWMS` und dessen fünf Images begrenzte
Pilot verwendet `scripts/intake_measured_security.py`. Voraussetzungen:
GitHub CLI mit Leserechten für Actions und die gepinnte Validierungsumgebung.

```sh
./scripts/bootstrap_validation_env.sh
.venv-validation/bin/python scripts/intake_measured_security.py --run-id 35131185085
.venv-validation/bin/python scripts/generate_status_viewer.py
./scripts/validate_all.sh
```

Bei einem externen `VALIDATION_VENV` dessen Python-Pfad einsetzen. Anschließend
die neuen Snapshots und den generierten Viewer über den normalen PR-/Merge-Weg
veröffentlichen. **Kein automatischer Refresh ist eingerichtet.** Die Seite
bezeichnet den Stand ausdrücklich als erfassten Snapshot; neuere Consumer-Runs
erscheinen erst nach erneutem Intake und Merge. Der Pages-Workflow generiert den
Viewer beim Veröffentlichen erneut aus den eingecheckten Snapshots.

Der Intake lässt ausschließlich erfolgreiche, abgeschlossene `push/main`-Runs
von `.github/workflows/l1-measured-evidence.yml` zu. PRs, Branch-Runs, manuelle
Runs, fremde Repositories, andere Versuche und widersprüchliche Counts werden
abgewiesen. Die Run-Auswahl erfolgt nach Quellzeit und Versuch, nicht Dateinamen.

Aus den GitHub-Artefakten werden gezielt JSON-Dateien per ZIP-Bytebereich gelesen.
Dabei werden ZIP-CRC, Rohdatei-SHA-256 und Größen gegen Producer-Manifeste,
Run-/Commit-/Versuchsbindung, Image-ID sowie erfolgreiche Scanausführung geprüft.
Die Summen aller Schweregrade müssen mit `l1-control-coverage` übereinstimmen.
Coverage-Testzahlen stammen aus diesem Producer-Bericht. Es werden keine
vollständigen Docker-/ZIP-Archive erneut gehasht und keine unabhängige Attestation
oder bestehende Evidence-Trust-Stufe behauptet. `archive_digest_verified` bleibt
explizit false. GitHub-Zugangsdaten und signierte Download-URLs werden nicht
persistiert oder an den Viewer übergeben.

## Speicherung und Vertrag

- `schemas/measured-container-security.schema.json`: additiver, report-only Vertrag.
- `status/measured-security-results/`: append-only normalisierte Snapshots mit
  Schweregradsummen, vollständigen HIGH-/CRITICAL-Details, Image- und Quellen-IDs.
- `scripts/lib/measured_security.py`: Kontext-, Hash-, Summen- und Schema-Prüfung.
- `scripts/lib/measured_security_view.py`: HTML-Projektion und sichere Textausgabe.

Wiederholung desselben Intakes ist idempotent. Abweichende Daten für dieselbe
Run-/Versuchsidentität führen zu einem Fehler; der bestehende Snapshot wird nicht
überschrieben. Fehlgeschlagener Intake ersetzt keinen vorherigen Stand. Der
Viewer speichert keine Fremdtexte als ausführbares HTML. Originale GitHub-Artefakte
bleiben nur für die Consumer-Aufbewahrungsfrist verfügbar; normalisierte hohe
und kritische Befunde bleiben in Git erhalten. Detaildaten niedrigerer
Schweregrade werden nicht übernommen, deren Summen werden angezeigt.
