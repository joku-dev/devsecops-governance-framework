# Governance Workspace: Viewer-Anwendung

Die eigenständige, lesende Frontend-Anwendung bündelt Übersicht, Repositories,
Container-Befunde und Nachweise. Sie läuft im bestehenden Repository auf GitHub
Pages. Ein Backend oder ein Benutzerkonto ist für die veröffentlichte Ansicht
nicht erforderlich.

[Anwendung öffnen](https://joku-dev.github.io/devsecops-governance-framework/generated/viewer/app/index.html)
· [ha-CPsWMS öffnen](https://joku-dev.github.io/devsecops-governance-framework/generated/viewer/app/index.html#repository/joku-dev%2Fha-CPsWMS/summary)

## Bedienung

| Bereich | Inhalt |
|---|---|
| Übersicht | Repository-Anzahl, gemessene kritische/hohe Meldungen, Governance mit Befunden und abgeleitete nächste Prüfungen |
| Repositories | Suche, offizielle DevSecOps-/Architektur-Ergebnisse und separate Container-Scans |
| Repository-Detail | Zusammenfassung, Container-Sicherheit mit Laufvergleich, filterbare Befunde und Nachweise |
| Befunde | HIGH/CRITICAL nach Repository, Schweregrad, Image und CVE/Paket durchsuchen; 20 Gruppen pro Seite |
| Nachweise | Offizielle Governance-Stände und erfasste Scan-Historie mit Commit, UTC-Datum, Run- und Snapshot-Links |

Der technische Viewer bleibt unter seinem bisherigen Pfad verfügbar und ist in
beide Richtungen verlinkt. Dort bleiben Graph, Intake, Modelle, Lifecycle und die
vollständige Governance-Laufhistorie erreichbar. Bestehende Deep Links bleiben
funktional. Neue Ansichten verwenden Hash-Routen; Browser-Zurück und direkte Links
funktionieren auch auf statischem Hosting.

## Bedeutung der Daten

- Governance-Ergebnisse stammen unverändert aus `latest_result` der vorhandenen
  DevSecOps- und Architektur-Indizes. Die Anwendung wählt keine neueren PR-,
  Branch- oder manuellen Ergebnisse als offiziellen Stand aus.
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

Die erste Version enthält die vorhandenen Governance-Indizes für drei Repositories
und gemessene Scans für ha-CPsWMS. Sie führt keine neuen Tests oder Scans aus. Der
Sicherheitsscan vom 16. September 2026 und die Governance-Stände vom 11./13.
September 2026 illustrieren die getrennten Erfassungszeitpunkte; zukünftige Intakes
können diese Stände verändern.

## Architektur und Aktualisierung

Quellen der Anwendung: `apps/governance-viewer/index.html`, `app.css` und `app.js`.
Es handelt sich um eine eigenständige Browser-Anwendung mit lokalem Routing,
Filtern und Seitennavigation, ohne externe JavaScript- oder CSS-Abhängigkeiten.
Die Python-Projektion `scripts/lib/viewer_app.py` erzeugt ein internes
Darstellungsformat (`version: 1`), keinen neuen Consumer-Evidence-Vertrag.

`scripts/generate_status_viewer.py` baut beide Viewer. Die Anwendung liegt danach
unter `generated/viewer/app/` mit `index.html`, `app.css`, `app.js` und `data.json`.
Diese Dateien werden nicht von Hand bearbeitet. Der Build ist bei gleichen
Eingaben deterministisch und prüft Container-Snapshots über den bestehenden
Validator. Die Veröffentlichung baut die Dateien erneut und kopiert sie zusammen
mit der Dokumentation nach GitHub Pages.

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
```

Die Browser-Abnahme verwendet die initialen Referenzdaten (1 kritisch, 332 hoch,
121 unterschiedliche hohe/kritische CVE-IDs, 57 Tests). Bei einem späteren
Daten-Intake die erwarteten Werte anhand der neuen validierten Snapshots prüfen
und aktualisieren. Sie prüft Desktop/Mobil, Routing, Filter, Seitennavigation,
Ladefehler, leere Daten und HTML-Escaping. Synthetische Fehlerdaten werden nur im
Testbrowser eingespeist.

## Weiterentwicklung

Die Anwendung ist zunächst lesend. Anmeldung, Rollen, serverseitige Bearbeitung,
Tickets und automatische Live-Aktualisierung gehören nicht zu dieser Version.
Ein Backend kann später ergänzt werden, wenn ein konkreter Schreib- oder
Berechtigungsbedarf besteht. Ein eigener Repository-Split ist dafür aktuell
nicht erforderlich.
