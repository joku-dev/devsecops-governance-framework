# Governance Workspace: Viewer-Anwendung

Die eigenständige, lesende Frontend-Anwendung bündelt Übersicht, Repositories,
Container-Befunde, Repository Security, Nachweise, Governance und Betrieb. Sie läuft im bestehenden Repository auf GitHub
Pages. Ein Backend oder ein Benutzerkonto ist für die veröffentlichte Ansicht
nicht erforderlich.

[Anwendung öffnen](https://joku-dev.github.io/devsecops-governance-framework/generated/viewer/app/index.html)
· [ha-CPsWMS öffnen](https://joku-dev.github.io/devsecops-governance-framework/generated/viewer/app/index.html#repository/joku-dev%2Fha-CPsWMS/summary)

## Bedienung

| Bereich | Inhalt |
|---|---|
| Übersicht | Repository-Anzahl, gemessene kritische/hohe Meldungen, Governance mit Befunden und abgeleitete nächste Prüfungen |
| Repositories | Suche, offizielle DevSecOps-/Architektur-Ergebnisse und separate Container-Scans |
| Repository-Detail | Zusammenfassung, Evidence Trust je Governance-Domain, L1-Nachweise je Kontrolle, reales Staging-Deployment, Container-Sicherheit mit Laufvergleich, filterbare Befunde und Nachweise |
| Befunde | HIGH/CRITICAL nach Repository, Schweregrad, Image und CVE/Paket durchsuchen; 20 Gruppen pro Seite |
| Repository Security | Aktueller Self-Security-Stand des zentralen Governance-Repositories, alle 16 Kriterien, offene kritische/hohe Punkte und dokumentierte Maßnahmen |
| Nachweise | Ergebnisnachweise, Evidence Trust, Replay-Prüfung, Nachweisherkunft, vollständige Governance-Laufhistorie, Artefakte und Daten |
| Governance | Governance-Graph, Runtime-Referenzartefakte, Kontrollen, Modell, Quellenaufnahme und offene Aufgaben |
| Betrieb | Integrationsstatus, Intake-Zustand, Sammelversuche, Intake-Konflikte und Agent-Nutzung |

Die technischen Funktionen sind direkt in die Anwendung integriert. Pro Bereich
wird eine Ansicht angezeigt. Auf Desktop wechseln Reiter zwischen Unterbereichen;
auf Mobilgeräten bietet ein Auswahlfeld alle Unterbereiche an. Technische Tabellen
ab acht Zeilen erhalten Suche und Seitennavigation mit zehn Zeilen je Seite.
Vorhandene Kontroll- und Laufkontextfilter wirken gemeinsam mit der Seitennavigation.
Der Graph unterstützt Suche, Typ-/Bereichsfilter und Auswahl per Maus oder Tastatur.

[Replay-Prüfung öffnen](https://joku-dev.github.io/devsecops-governance-framework/generated/viewer/app/index.html#evidence/replay)
· [Repository Security öffnen](https://joku-dev.github.io/devsecops-governance-framework/generated/viewer/app/index.html#repository-security)
· [Governance öffnen](https://joku-dev.github.io/devsecops-governance-framework/generated/viewer/app/index.html#governance/controls)
· [Betrieb öffnen](https://joku-dev.github.io/devsecops-governance-framework/generated/viewer/app/index.html#operations/intake)

Die frühere Gesamtansicht bleibt als Rückfallansicht unter ihrem bisherigen Pfad
verfügbar. Ihre bestehenden Deep Links funktionieren weiterhin. Die neue Anwendung
verwendet Hash-Routen und unterstützt Browser-Zurück sowie direkte Links. Alte
Abschnittsnamen wie `#replay-triage` werden innerhalb der Anwendung auf die passende
Ansicht abgebildet. `#overview` öffnet die neue Übersicht.

## Evidence Trust je Repository

Die globale Ansicht **Nachweise → Evidence Trust** zeigt zuerst **Latest Governance
Evidence Trust** für die offiziellen DevSecOps- und Architektur-Ergebnisse aller
erfassten Repositories, einschließlich ha-CPsWMS. **Latest Typed Evidence** ist eine
separate Tabelle für den Typed-Evidence-Intake. Das ha-CPsWMS-Profil erfasst alle
fünf Container-Images mit zentral geprüften Archiven. Solange für ein Repository
kein Eintrag aufgenommen wurde, nennt die Ansicht diese Lücke ausdrücklich. Die
gemessene L1-Bewertung erhält über ihren eigenen Kontroll-Assurance-Vertrag eine
Trust- und Freshness-Aussage je Kontrolle; diese wird nicht aus einem
Governance-Ergebnis geerbt.

Unter **Repositories → ha-CPsWMS → Evidence Trust** stehen die gespeicherten
Trust-Stufen für DevSecOps und Architektur mit Prüfzeitpunkt, Commit, Replay,
Anzahl bestandener/fehlgeschlagener/nicht bewerteter Einzelprüfungen und Links
zu den vollständigen Snapshots. Die Zusammenfassung, der Nachweise-Reiter und
die L1-Ansicht verlinken diesen Bereich direkt.

[ha-CPsWMS Evidence Trust öffnen](https://joku-dev.github.io/devsecops-governance-framework/generated/viewer/app/index.html#repository/joku-dev%2Fha-CPsWMS/trust).
`integrity_verified` kann neben Replay `FAIL` stehen: Es bestätigt die geprüfte
Integrität, hebt aber offene Replay-Befunde oder nicht bewertete Dimensionen nicht
auf. Fehlender Trust bleibt ausdrücklich nicht erfasst. Die Trust-Stufen der
offiziellen Governance-Ergebnisse werden nicht auf andere Ergebnisarten
übertragen. Typisierte SBOM-/Scan-Nachweise und Kontroll-Assurance verwenden ihre
jeweils dokumentierten Prüfgrenzen.

## L1-Nachweise je Repository

Unter **Repositories → ha-CPsWMS → L1-Nachweise** stehen 16 zentrale
Report-only-Bewertungen aus tatsächlichen Prüfungen. Jede Kontrolle nennt
Messwerte, Werkzeuge, verbleibende Lücken und die Originaldateien mit Prüfsummen.
Zusätzlich zeigt sie Abdeckung, Trust, Freshness-Policy, Integrität, Provenienz,
Replay, Custody, Attestation, Entscheidungskontext und Subjektbindung. Vorhandene
und fehlende Nachweisgruppen bleiben getrennt sichtbar.
Kontrollzeilen für Details aufklappen, nach Kontroll-ID, Werkzeug oder Text
suchen und nach Nachweisstatus filtern.
Die Zusammenfassung verlinkt diese Ansicht; die offizielle Baseline bleibt daneben
als eigener Status sichtbar. Fehlende Messungen ergeben keinen PASS.

[Kontrollen öffnen](https://joku-dev.github.io/devsecops-governance-framework/generated/viewer/app/index.html#repository/joku-dev%2Fha-CPsWMS/l1)
· [Vertrag und Prüfgrenzen](../evidence/l1-measured-evidence-ha-cpswms.md#zentrale-bewertung-je-l1-kontrolle)

## Reales Staging-Deployment

Unter **Repositories → ha-CPsWMS → Staging** steht der tatsächlich auf der
isolierten VM ausgeführte Lauf. Die Ansicht zeigt Ziel, deployten Commit,
Quelllauf, exakte Runtime-Image-IDs, 19 Laufzeitprüfungen, Security-Grenzen,
Ausfall/Wiederherstellung, Evidence Trust und die ergänzende Bewertung für
L1-013, L1-014 und L1-016.

[Staging-Lauf öffnen](https://joku-dev.github.io/devsecops-governance-framework/generated/viewer/app/index.html#repository/joku-dev%2Fha-CPsWMS/staging)

Der Staging-Nachweis verändert den früheren CI-Snapshot nicht. Er ist ein späterer,
append-only gespeicherter Laufzeitnachweis für den dort genannten Commit. Seine
Freigabe ist weder Produktionsfreigabe noch allgemeine Risikoakzeptanz.

## Bedeutung der Daten

- Governance-Ergebnisse stammen unverändert aus `latest_result` der vorhandenen
  DevSecOps- und Architektur-Indizes. Die Anwendung wählt keine neueren PR-,
  Branch- oder manuellen Ergebnisse als offiziellen Stand aus.
- Repository Security stammt aus dem schema-validierten Self-Security-Bericht
  `generated/reports/governance-repository-security.json`. Die Ansicht zeigt
  dessen gespeicherten Beobachtungszeitpunkt, Gesamtstatus, Kriterien und
  Maßnahmen unverändert als report-only Projektion. Sie fragt GitHub nicht live
  ab und verändert keine Repository-Einstellung.
- L1-Nachweise stammen aus validierten `status/measured-l1-results/`-Snapshots.
  Sie verändern weder offizielle Ergebnisse noch historische Replay-Befunde.
- Kontroll-Assurance stammt aus validierten, append-only gespeicherten
  `status/control-evidence-assurance/`-Snapshots. Fehlende erforderliche
  Nachweisanteile führen für die betreffende Kontrolle zu `unverified`.
- Staging-Deployment-Ergebnisse stammen aus validierten, append-only gespeicherten
  `status/staging-deployment-results/`-Snapshots. Der Intake prüft Bundle-Hashes,
  Quelllauf, Approval und Subjektbindung und projiziert sie getrennt von CI.
- Container-Sicherheit stammt aus den validierten, separat aufgenommenen
  `status/measured-security-results/`-Snapshots. Diese sind report-only.
- HIGH/CRITICAL-Meldungen zählen Image-/Paketvorkommen. CVE-IDs werden zusätzlich
  dedupliziert; die Befundliste gruppiert CVE, Schweregrad, Paket und Versionen.
- Fehlende Scans heißen **nicht erfasst**, nicht null Befunde. Ladefehler zeigen
  einen Fehlerzustand. Ein PASS ist weder Schwachstellenfreiheit noch
  Produktionsfreigabe oder Risikoakzeptanz.
- Commit und Datum werden pro Ergebnis angezeigt. Unterschiedliche Commits von
  Governance und Scan werden in der Repository-Zusammenfassung hervorgehoben.
  Das angezeigte Alter wird aus dem Quellzeitpunkt und der Browser-Uhr berechnet;
  daraus wird keine neue verbindliche Frist oder Freigaberegel abgeleitet.
- Evidence Trust und der aufgezeichnete Replay-Status bleiben getrennt sichtbar.
  Die technische Replay-Triage bietet die weitergehende Interpretation.
- Prüfhinweise in der Befundliste sind technische Hinweise, kein bearbeitbarer
  Ticketstatus, keine VEX-Feststellung und keine formale Risikobewertung.

Die Anwendung enthält die Governance-Indizes für drei Repositories sowie
gemessene, typisierte und reale Staging-Nachweise für ha-CPsWMS. Sie führt selbst
keine Tests oder Scans aus. Die aktuell veröffentlichten Daten kombinieren die
jeweils versionierten Governance-, Security-, Typed-Evidence-, L1- und
Staging-Snapshots. Zukünftige geprüfte
Intakes können diese Stände verändern.

## Architektur und Aktualisierung

Quellen der Anwendung: `apps/governance-viewer/index.html`, `app.css`, `app.js`,
`technical.css` und `technical.js`.
Es handelt sich um eine eigenständige Browser-Anwendung mit lokalem Routing,
Filtern und Seitennavigation, ohne externe JavaScript- oder CSS-Abhängigkeiten.
Die Python-Projektion `scripts/lib/viewer_app.py` validiert den Self-Security-Bericht
gegen sein JSON-Schema und verbindet die gemessene Bewertung mit der
Kontroll-Assurance nur bei identischem Repository, Run, Versuch und Commit. Sie erzeugt ein internes
Darstellungsformat (`version: 1`), keinen neuen Consumer-Evidence-Vertrag.

`scripts/generate_status_viewer.py` baut beide Viewer. Die Anwendung liegt danach
unter `generated/viewer/app/` mit den fünf Frontend-Dateien und `data.json`.
Diese Dateien werden nicht von Hand bearbeitet. Der Build ist bei gleichen
Eingaben deterministisch und prüft Container-Snapshots über den bestehenden
Validator. Die Veröffentlichung baut die Dateien erneut und kopiert sie zusammen
mit der Dokumentation nach GitHub Pages.

`scripts/lib/viewer_technical.py` übernimmt die fachlichen Abschnittsinhalte direkt
aus dem bestehenden Renderer. Es entsteht keine zweite Auswahl- oder Bewertungslogik.
Das interne Feld `technical` enthält zugeordnete Ansichten und getrennte Graphdaten.
Inline-Skripte, Eventhandler und Inline-Stile werden entfernt, Links geprüft und für
den neuen Pfad aufgelöst. Der Browser bindet Filter und Graphinteraktionen über
das eigene Modul. Unbekannte technische Abschnitte führen zu einem Buildfehler;
fehlende optionale Projektionen zu einer expliziten Leermeldung.

Status-JSON-Dateien werden aus dem Git-Repository verlinkt; generierte Berichte
bleiben direkt auf Pages erreichbar. Runtime-Demo- und lokale Kontrollberichte
bleiben als Referenzartefakte von offiziellen Repository-Ergebnissen getrennt.
Der separate synthetische Lifecycle-Szenario-Viewer ist eine eigene Anwendung und
wird durch diese Integration nicht zu offiziellen Live-Ergebnissen umgedeutet.

Nach einem angenommenen Intake wird die Datendatei beim Pages-Build neu erzeugt.
`generated/viewer/app/data.json` ist ein ignoriertes Build-Artefakt und wird nicht
zusätzlich als Git-Historie geführt; die zugrunde liegenden Indizes und
Evidenz-Snapshots bleiben versioniert. Die bestehende operative Publikations-
Allowlist und das an die persönliche Lifecycle-Abnahme gebundene Skript bleiben
unverändert. Anwendungscode wird über einen normalen Code-PR veröffentlicht.

Neue gemessene Scans erfordern weiterhin den
[gemessenen L1-Intake](../evidence/l1-measured-evidence-ha-cpswms.md), Validierung,
Merge und Veröffentlichung. Die Anwendung liest nur die veröffentlichte
Datendatei; sie fragt Consumer-Repositories nicht live ab. Anmeldedaten werden
weder benötigt noch eingebettet. Die Daten haben dieselbe öffentliche Sichtbarkeit
wie die vorhandene Pages-Site.

## Lokal entwickeln und prüfen

```bash
./scripts/bootstrap_validation_env.sh
.venv-validation/bin/python scripts/generate_status_viewer.py
python3 -m http.server 8000 --bind 127.0.0.1
```

Anschließend `http://127.0.0.1:8000/generated/viewer/app/index.html` öffnen.
Wegen des JSON-Abrufs ist ein lokaler HTTP-Server erforderlich.

Vor Änderungen veröffentlichen:

```bash
./scripts/validate_all.sh
.venv-docs/bin/mkdocs build --strict
```

Zusätzliche Browser-Abnahme in einer separaten Testumgebung mit
`playwright==1.63.0` und installiertem Chromium:

```bash
python tests/browser/check_viewer_app.py http://127.0.0.1:8000/generated/viewer/app/index.html
python tests/browser/check_viewer_technical.py http://127.0.0.1:8000/generated/viewer/app/index.html
```

Die Browser-Abnahme verwendet die initialen Referenzdaten (1 kritisch, 332 hoch,
121 unterschiedliche hohe/kritische CVE-IDs, 57 Tests). Bei einem späteren
Daten-Intake die erwarteten Werte anhand der neuen validierten Snapshots prüfen
und aktualisieren. Sie prüft Desktop/Mobil, Routing, Filter, Seitennavigation,
Ladefehler, leere Daten und HTML-Escaping. Synthetische Fehlerdaten werden nur im
Testbrowser eingespeist. Die technische Abnahme prüft zusätzlich alle integrierten
Ansichten, kombinierte Kontextfilter, Graphauswahl, mobile Navigation, Rückwärts-
navigation, Linkauflösung und die HTML-Projektionsgrenze.

## Weiterentwicklung

Die Anwendung ist zunächst lesend. Anmeldung, Rollen, serverseitige Bearbeitung,
Tickets und automatische Live-Aktualisierung gehören nicht zu dieser Version.
Ein Backend kann später ergänzt werden, wenn ein konkreter Schreib- oder
Berechtigungsbedarf besteht. Ein eigener Repository-Split ist dafür aktuell
nicht erforderlich.
