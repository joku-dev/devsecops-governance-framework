# GCR-2026-171 — Consumer-Ergebnisse auf der VM sammeln

## Auftrag und Klassifikation

Der Maintainer beauftragt am 14. November 2026 die Umsetzung des besprochenen
Consumer-Intake-Plans in einem eigenen Branch auf dem Linux-IaC-Prototyp.

| Feld | Einordnung |
|---|---|
| Artefakte | Private SQLite-Warteschlange, App-Zugänge, Collector/Publisher, systemd/IaC, lesende Workbench-Projektion, Tests und Anleitung |
| Ziel | `scripts/`, `infra/ansible/`, `config/`, `tests/`, `docs/operations/guides/` |
| Typ | Betriebsautomation und Evidence-Intake; keine normative Quelle |
| Owner | Repository Maintainer |
| Full Source Document Intake | Nein |
| Pilot | `joku-dev/ha-CPsWMS`, DevSecOps L1, `devsecops-baseline.yml`, Mainline Push |
| Evidence | Bestehender Normalizer, Trust-, Frische-, Replay- und Kontextvertrag; private VM-Telemetrie getrennt |
| Veröffentlichung | Schattenbetrieb voreingestellt; maximal 25 Ergebnisse je Review-PR, ein offener VM-PR |
| Umschaltung | Mindestens 24 Stunden plus Vergleich eines neuen realen Mainline-Laufs; explizite geprüfte Route und private Aktivierung |
| Release | Keine neue Baseline, keine Paket-, Tag-, Policy- oder Enforcement-Änderung |
| Review | Governance Analysis, Evidence and Intake, DevSecOps Baseline, Release Management; Repo Steward zuletzt, jeweils tatsächliche `role_lens` |
| Validierung | Queue/API-/Archiv-/Recovery-Tests, Workbench HTTP/DOM, isoliertes Linux/systemd, gepinnte Gesamtvalidierung, MkDocs strict und revisionsgebundener Review |

## Grenzen

Architektur, eigene SBOM-/Scan-Pipelines, Consumer-CI-Auslösung, produktive
Mehrbenutzerfreigabe und verteilte Ausführung bleiben außerhalb dieses Piloten.
Die bestehende Legacy-Blocking-Einstellung des Consumers bleibt unverändert.
Die 24 Dateien der Operating Acceptance werden nicht geändert. GitHub Apps,
Installationsrechte und private Schlüssel werden durch den Maintainer separat
bereitgestellt; dieser Branch erteilt keine solchen Rechte und schaltet die
Produktivroute nicht um.

Die Workbench liest nur eine reduzierte Projektion. Offizielle Ergebnisse stammen
aus einem validierten, unveränderlich benannten zentralen Main-Commit. Abfragen,
Downloads, verifizierte Kandidaten und offene PRs sind keine Übernahme.
