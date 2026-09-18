# L1 mit gemessenen Nachweisen in ha-CPsWMS

Stand: 17. September 2026. Referenz ist die unveränderte DevSecOps-Baseline
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
Eine zentrale, aus ausgewählten Rohdaten neu berechnete Bewertung und eine
separate Nachweis-Assurance je Kontrolle sind zusätzlich
unter **Repositories → ha-CPsWMS → L1-Nachweise** verfügbar (siehe unten).
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

Der neueste kombinierte Typed-Evidence-/L1-Lauf
[`35241262722`](https://github.com/joku-dev/ha-CPsWMS/actions/runs/35241262722)
gehört zum Commit `ce02be6`, enthält 58 bestandene Tests und liefert über den
strengeren Typed-Evidence-Intake 1 kritische und 329 hohe Image-/Paketvorkommen.
Er ersetzt den zweiten Messpunkt in der getrennten Container-Security-Historie
nicht automatisch; beide Speicher behalten ihre jeweilige Intake- und
Auswahlregel.

Der Vergleich zählt Meldungen über fünf Images. Er belegt allein keine Kausalität:
Auch eine geänderte Scanner-Datenbank kann Zahlen ändern. Die
[Consumer-Bewertung](https://github.com/joku-dev/ha-CPsWMS/blob/main/docs/quality/CONTAINER_SECURITY_REMEDIATION.md)
beschreibt die tatsächlich installierten Paketkorrekturen und offenen Gruppen.
Die Hinweise im Viewer sind technische Prüfansätze, keine VEX-Freigabe,
Risikobilligung oder Bestätigung tatsächlicher Ausnutzbarkeit. Insbesondere ist
ein Linux-Headerpaket kein Nachweis über den Kernel einer späteren Staging-VM.

## Automatischer und wiederholbarer Intake

Der neue, ausdrücklich auf `joku-dev/ha-CPsWMS` und dessen fünf Images begrenzte
Pilot verwendet `scripts/intake_measured_security.py`. Voraussetzungen:
GitHub CLI mit Leserechten für Actions und die gepinnte Validierungsumgebung.

```sh
./scripts/bootstrap_validation_env.sh
.venv-validation/bin/python scripts/intake_measured_security.py --run-id 35241262722
.venv-validation/bin/python scripts/generate_status_viewer.py
./scripts/validate_all.sh
```

Bei einem externen `VALIDATION_VENV` dessen Python-Pfad einsetzen. Anschließend
die neuen Snapshots und den generierten Viewer über den normalen PR-/Merge-Weg
veröffentlichen. Ein erfolgreicher `main`-Lauf sendet über
`.github/workflows/typed-evidence-intake.yml` automatisch genau einen Intake-
Dispatch an das zentrale Repository. Der zentrale Workflow prüft zuerst die
typisierten SBOM- und Schwachstellennachweise und erzeugt danach die gemessene
L1-Bewertung samt Kontroll-Assurance. Er eröffnet einen begrenzten operativen PR;
erst dessen Merge aktualisiert den offiziellen gespeicherten Stand und Pages.
Der CLI-Aufruf bleibt als kontrollierter Backfill verfügbar.

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

## Zentrale Bewertung je L1-Kontrolle

[L1-Nachweise im neuen Viewer](https://joku-dev.github.io/devsecops-governance-framework/generated/viewer/app/index.html#repository/joku-dev%2Fha-CPsWMS/l1).

`scripts/intake_measured_l1.py` prüft die vorhandenen Artefakte desselben
Messlaufs erneut. Es berechnet die 16 Kontrollbewertungen zentral aus JUnit,
Bandit, Ruff, CycloneDX, Trivy, GitHub-API-Antworten und CI-Deployment-Metadaten.
Producer-Statusangaben werden nicht als Kontrollfreigabe übernommen.

```sh
.venv-validation/bin/python scripts/intake_measured_l1.py --run-id 35241262722
.venv-validation/bin/python scripts/generate_status_viewer.py
./scripts/validate_all.sh
```

Die Aufbereitung verwendet für neue Läufe das versionierte Pilotprofil
`ha-cpswms-l1-measured-v2` in `scripts/lib/measured_l1.py`; historische
v1-Snapshots bleiben weiter validierbar. Das Profil prüft zusätzlich den
Main-Ruleset, Python-3.12-Locks samt SHA-256, Anwendungs-/CI-SBOMs und
`pip-audit`-Rohdaten. Es referenziert die
bestehenden 16 Kontrollen in `model/controls/dscb-l1.yaml`, führt keine neuen
Anforderungen ein und ersetzt weder OPA noch die freigegebene Baseline.
Änderungen an der Bedeutung dieses Profils benötigen eine neue Profil-/Vertragsversion.

| Anzeige | Bedeutung |
|---|---|
| Technisch belegt | Der beschriebene technische Teil wurde zentral nachgeprüft; keine vollständige Kontroll- oder Release-Freigabe |
| Teilweise belegt | Messwerte liegen vor, weitere Bestandteile oder organisatorische Entscheidungen fehlen |
| Befunde offen | Werkzeuge haben Befunde geliefert, deren Bewertung noch nachzuweisen ist |
| Nachweis fehlt | Erforderliche Nachweise fehlen oder erlauben keine positive Feststellung |

Im aktuellen erfassten Lauf `35241262722` ergeben sich **5 technisch belegte,
6 teilweise belegte, 2 Kontrollen mit Befunden und 3 Nachweislücken**.
Historische v1-Läufe behalten ihre damalige Bewertung. In v2 können L1-003,
L1-004, L1-005 und L1-007 nur dann technisch auf `measured` steigen, wenn die
neuen Rohdaten zentral nachgerechnet werden. L1-002 bleibt trotz Commit-/Autor-
Nachweis teilweise, solange keine organisatorische VCS-Freigabe belegt ist.
Die 58 erfolgreichen Tests (50 Quelltests und 8 Runtime-Integrationstests) und
Scanbefunde werden aus Rohdaten nachgerechnet.

Jede Kontrolle zeigt Beobachtung, Prüfmittel, verbleibenden Umfang und konkrete
Nachweisdateien mit SHA-256, Größe und Actions-Artefakt-ID. Die Übersicht stellt
sie neben das offizielle Baseline-Ergebnis; eine gemeinsame Commit-Zuordnung
wird nur angezeigt, wenn sie tatsächlich vorliegt. Suche und Statusfilter helfen
bei der Bearbeitung. Alte erfasste Bewertungen bleiben über ihre Snapshots zugänglich.

### Assurance für alle 16 Kontrollen

Das Profil `model/evidence/control-evidence-assurance-profile.yaml` ordnet jede
L1-Kontrolle einem katalogisierten Nachweistyp, Freshness-Verfahren,
Entscheidungskontext und einer Subjektbindung zu. Der additive Vertrag
`schemas/control-evidence-assurance.schema.json` speichert für jede Kontrolle:

- Abdeckung (`complete`, `partial`, `missing`),
- effektive Trust-Stufe,
- Inhaltsintegrität, Provenienz und Freshness,
- Replay, Custody und Attestation,
- vorhandene und fehlende Nachweisgruppen.

Ein `findings`-Ergebnis kann einen verlässlich gebundenen Nachweis haben; der
Befund ändert dessen Trust nicht. Umgekehrt macht ein verifiziertes SBOM fehlende
Freigabe- oder Deployment-Nachweise nicht wett. Sobald ein erforderlicher Teil
fehlt, bleibt die aggregierte Trust-Stufe der betroffenen Kontrolle
`unverified`; vorhandene Teilnachweise behalten ihre einzeln geprüfte Stufe.
Nicht bewertete Dimensionen werden ausdrücklich als `not_evaluated` gespeichert.
Diese Assurance bleibt report-only und ändert weder Kontrollstatus noch Baseline,
Blocking-Modus, Produktionsfreigabe oder Risikoakzeptanz.

Für Lauf `35241262722` sind 7 Kontrollen vollständig abgedeckt,
`integrity_verified` und innerhalb ihrer Freshness-Regel. Sechs Kontrollen sind
teilweise und drei nicht abgedeckt; zusammen bleiben 9 Kontrollen
`unverified`. Keine Kontrolle erreicht `provenance_verified` oder `attested`,
weil die dafür erforderlichen unabhängigen Nachweise nicht vorliegen.

### Prüfgrenze und Aufbewahrung

Der Intake prüft GitHub-Repository, erfolgreichen `push/main`-Lauf, Workflow,
Commit, Versuch und Artefaktzuordnung. Producer-Manifeste binden ausgewählte
Rohdateien an diesen Kontext. JUnit-Zahlen und SAST-Befunde werden nachgerechnet;
SBOMs und Scan-Reports müssen zum Build-Config-Digest gehören. Bei portablen
Docker-Archiven prüft der Intake zusätzlich den Archiv-Tag sowie die nach dem
Import ermittelte Runtime-Image-ID. Der Runtime-Nachweis muss den Build-Digest
jedes getesteten Containers wieder auf den gescannten Digest abbilden; fehlende,
ungültige oder doppelte Runtime-IDs und falsche Archiv-Tags werden abgewiesen.
Die technische Anforderungszuordnung wird aus dem exakten Quell-Commit gelesen.
Fremde Kontexte, falsche Hashes, fehlende Dateien und widersprüchliche Summen
brechen den Intake ab und ersetzen keinen bisherigen Stand. HTTP 403 innerhalb
einer gültigen Plattformaufzeichnung wird als Nachweislücke sichtbar.

Die zentrale Prüfung lädt nicht die kompletten Image-Archive. Deren Digests
bleiben ausdrücklich Producer-Angaben. Auch ein gültiges Manifest beweist keine
unabhängige Attestation oder die Vertrauenswürdigkeit des Producers. Die
Nachweisbindung ist eine deterministische Kontext-/Hash-Zuordnung, keine Signatur.

`schemas/measured-l1-assessment.schema.json` validiert die gemessene Bewertung;
`schemas/control-evidence-assurance.schema.json` validiert die getrennte Assurance.
Die Snapshots liegen unter `status/measured-l1-results/` und
`status/control-evidence-assurance/`. Wiederholung ist idempotent;
abweichende Inhalte derselben Lauf-/Versuchsidentität überschreiben keine Historie.
Rohdateien verbleiben bei GitHub für die Consumer-Aufbewahrungsfrist; normalisierte
Beobachtungen und Hashes bleiben im Repository. Geheimnisse, signierte Download-URLs
und vollständige Rohlogs werden nicht eingecheckt. Automatischer und manueller
Intake verwenden denselben geprüften PR-Weg.

Diese Bewertung entfernt keine historischen Replay-Findings und ändert keine
Trust-Stufen anderer Ergebnisarten. Der alte Baseline-Workflow hat weiter seine eigenen Eingaben. Für
seine Umstellung auf gemessene Kontrollergebnisse ist ein gesonderter
Baseline-/Migrationsschritt erforderlich. Ein neu erfasster Bericht ist weder
Deployment-Zustimmung noch Risikoakzeptanz. L1-013/014 und Teile von L1-016 bleiben
bis zur bereitgestellten VM und den zugehörigen autorisierten Nachweisen offen.
