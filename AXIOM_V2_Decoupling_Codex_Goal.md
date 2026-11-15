---
goal_id: AXIOM-V2-DECOUPLING-001
version: "2.0"
date: "2026-11-15"
status: in_progress
source_reference: 6b557fefe295b58272d2271326576ca3a3687197
branch: feat/axiom-v2-decoupling
change_request: GCR-2026-185
default_mode: report-only
default_collection_mode: paused
---

# AXIOM V2: vollständige Entkopplung der Anbieterzugriffe

Der Maintainer hat am 15. November 2026 die autonome Umsetzung der zuvor
besprochenen V2 beauftragt. Dies ist ein technischer Entwicklungsauftrag und
keine normative Governance-Quelle oder Betriebsabnahme. Er ergänzt den früheren
Portabilitätsauftrag um einen klaren Versionsbruch: V2 muss keine alten
Ausführungspfade, Queue-Daten oder Receipts als aktive Kompatibilität übernehmen.
Der ursprüngliche Auftrag und bisherige Nachweise bleiben historische Referenzen.

## Ziel

Ein gemeinsames Produkt für Mac und Linux-VM. Fachlicher Kern, Workbench,
Collector, Verifier und Publisher verwenden ausschließlich explizite Adapter
für SCM, CI, Evidenztransport und Veröffentlichungen. Providerprofile bestimmen
Anbieter, Instanzen und Credentials; weder Geschäftscode noch Oberfläche wählen
GitHub implizit. GitHub-spezifischer Code darf in seinen Adaptern und nativen
Workflow-Dateien stehen. GitLab sowie Bitbucket DC/Bamboo erhalten dieselben
Verträge; tatsächliche Versions-/Instanz-Abnahmen bleiben separat nachzuweisen.

## Autorisierter Umfang

Autonom Bestandsaufnahme, disjunkte Modulgrenzen, Implementierung, sinnvolle
Regressionstests, Dokumentation, reproduzierbare Pakete und isolierte Mac-/VM-
Testinstallation erstellen. In kohärenten, vollständig validierten Schritten
auf dem eigenen Branch liefern und einen überprüfbaren PR vorbereiten.
Gewöhnliche technische Entscheidungen benötigen keine erneute Bestätigung.

Bestehende Installationen, gespeicherte Entwürfe, Schlüssel, Git-Historie,
akzeptierte Entscheidungen und veröffentlichte Baseline-Bytes bleiben erhalten.
V2 erhält frische private Zustände und getrennte Ports/Installationsverzeichnisse.
Alte akzeptierte GitHub-Pilotpfade verbleiben im V1-Rückfallstand; sie dürfen
weder transitiv aus der V2-Anwendung geladen noch durch deren Launcher gestartet
werden. Eine bloße neue Fassade vor unverändert aktiven Altpfaden genügt nicht.

Keine automatische Übertragung von Rollen, persönlicher Zustimmung, Trust,
Waivern, Publisher-Zuständigkeit oder Blocking. Neue Integrationen bleiben
report-only, Sammlung zunächst paused. Ein Produkt-Versionswechsel ist keine
neue fachliche Baseline. Produktiver Ersatz benötigt den überprüfbaren Kandidaten
und die gegebenenfalls erforderliche konkrete externe Freigabe.

## Arbeitspakete und Abnahmekriterien

| Paket | Prüffähiges Ergebnis |
|---|---|
| V2-01 Inventar | Alle bisherigen Einstiegspunkte sind als V2 aktiv, reines Build-/Review-Werkzeug oder V1-Rückfallpfad klassifiziert; keine stillschweigend entfallene fachliche Funktion. |
| V2-02 Verträge | SCM, CI, Evidence und Publication haben ausdrückliche Schnittstellen und Profile; fehlende Fähigkeiten bleiben unbekannt/unsupported. |
| V2-03 Adapter | Anbieter-APIs, CI-Variablen, URL-/ID-Formate und Sonderfälle einschließlich Credentials/Rate-Limits liegen in Adaptermodulen. |
| V2-04 Kern | Auswertung, Integrität, Freshness, Replay, Queue und Batchentscheidungen enthalten keine Anbieter-API-Pfade, CLI-Aufrufe, festen Hosts oder providerabhängigen Imports. |
| V2-05 Workbench | Dieselben dokumentierten Intake-/Review-Funktionen mit generischer Weitergabe über das konfigurierte SCM-Profil; keine direkte gh-Abhängigkeit. |
| V2-06 Dienste | V2 verwendet ausschließlich die gemeinsame portable Verarbeitung und frische Operations-Roots; alte Jobs/Receipts werden nicht automatisch importiert. |
| V2-07 Stilllegung | Der V2-Launcher/Paketumfang exponiert keine alten Intake-/Lifecycle-/Publisher-Einstiege; Importgraph und Laufzeittests verhindern Rückfall. |
| V2-08 Tests | Architekturregeln, Adapterverträge und Negativfälle decken Anbieterzugriffe, fehlende Profile, falsche Instanzen, doppelte Publikation und Ergebnisparität ab. |
| V2-09 Installation | Dasselbe revisions- und digestgebundene Paket startet auf Mac/Linux in einem frischen Verzeichnis; separate Konfiguration, Ports, Credentials und Zustand. |
| V2-10 Nachweise | Vollständige gepinnte Validierung, strenger Dokumentationsbuild, isolierte Mac-/Linux-Smokes, exakte Änderungen und Grenzen im PR. |

Eine erfolgreiche Fixture ist keine Live-Kompatibilitätsabnahme eines nicht
verfügbaren GitLab-/Atlassian-Systems. Gleiche Inputs, Runtime, Baseline,
Auswertungszeit und Referenzzustände müssen gleiche fachliche Ergebnisse liefern.
Die vorhandene fünf-Kontrollen-Pipeline-Abdeckung wird durch Modularisierung
nicht als vollständige L1-/Lifecycle-Abdeckung ausgegeben. Bestehende fachliche
Fähigkeiten und neue Betriebsgrenzen sind im Funktionsinventar ausdrücklich
zuzuordnen, bevor ein V2-Gesamterfolg erklärt wird.

## Arbeits- und Nachweisführung

Artefakte gemäß Intake-Prozess klassifizieren; GCR-2026-185 führt den technischen
Versionsbruch. Quelländerungen und Adapterumfang werden in Runtime-/Verifier-
Digests eingeschlossen. Vor Commit die gepinnte Bootstrap-/Gesamtvalidierung
ausführen. Revisionsgebundene Rollenreviews korrekt als Koordinator-Linsen oder
tatsächlich ausgeführte unabhängige Reviews ausweisen; Steward zuletzt.
Private Providerdaten, Pläne, Credentials und Rohbelege bleiben außerhalb Git.

Abschluss erst nach Implementierung der Kriterien und Lieferung eines konkreten
PR-/Installationskandidaten. Unabhängig ausführbare Arbeit wird bei fehlenden
externen Zugängen fortgesetzt; offene Live-Abnahmen und nötige Codeowner-
Freigaben werden präzise benannt und nicht durch Erfolgsbehauptungen ersetzt.
