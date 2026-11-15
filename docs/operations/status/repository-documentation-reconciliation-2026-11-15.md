# Dokumentationsabgleich — 15. November 2026

## Bezug und Einordnung

Betrachteter Main-Stand: `4f6f5bbc2614760a35fe9d79602bcf5b19bc6e74` nach dem
Merge von #344/#347/#349 am 15. November, 11:35 MEZ. Dieser Abgleich beschreibt
Implementierung und datierte Betriebsbeobachtungen; er ist keine neue fachliche
Freigabe. [GCR-2026-182](../../governance/change-requests/GCR-2026-182-current-platform-documentation.md)
klassifiziert ihn als erläuternde Dokumentation. Der
[Abgleich vom 7. November](repository-documentation-reconciliation-2026-11-07.md)
bleibt mit seiner damaligen Quellbindung erhalten.

## Was jetzt vorhanden ist

| Bedarf | Aktueller Einstieg und Grenze |
|---|---|
| Document Intake | [Workbench](../guides/governance-review-workbench.md): Dokument wählen, prüfen, weitergeben. Explizite Kennungen werden extrahiert; Prüfnotizen bleiben Vorschläge. Architektur bleibt über den Sitzungsfilter geparkt. |
| Freigegebene Anforderung bis Regel | [Fünf-Phasen-Leitfaden](../../governance/architecture/document-intake-to-opa-rulebook.md), exakte GRQ-/Artefaktbindungen und lesende Auswirkungsindikation. Eine Zuordnung beweist keine tatsächliche Anwendung. |
| Mac und VM parallel | [VM-/Betriebsleitfaden](../guides/linux-vm-installation.md): Mac-Port 8765 und VM-Port 8766 über SSH; eigene Schlüssel, Sitzungen und Drafts. Keine automatische Synchronisation. |
| Installation und Update | Ansible, voller Commit-Pin, systemd, geprüfte Sicherungen an zwei Orten, kontrollierte Rückkehr und selektiver Draft-Import. Ein Merge löst kein privates VM-Update aus. |
| Portable Pipeline-Prüfung | [Runtime](../adapters/portable-governance-runtime.md): gemeinsamer Kern, GitHub/GitLab/Bamboo-Adapter, fünf gemappte Pipeline-L1-Kontrollen; elf bleiben nicht ausgewertet. |
| Evidence und Sammlung | [Verifier/Intake](../evidence/portable-evidence-intake.md), private Schema2-Queue, immutable Receipts, Kandidatenansicht, eingefrorene Vorschläge und Recovery. Akzeptierte Ergebnisse bleiben separat in Git. |
| Offline und Skalierung | [Vorbereitetes Paket](../guides/prepared-runtime-package.md) und [1.000/2.000-Repository-Messprofile](../guides/portable-capacity-profile.md); reale Provider-/Payload-/Kapazitätsabnahmen stehen aus. |

Die vollständige Implementierungs-/Abnahmematrix ist unter
[WP0–WP8 / AC01–AC30](../planning/platform-portability-acceptance.md) verlinkt.
Der [fachliche Katalog](../guides/repository-function-catalog.md) ordnet die
Funktionen ein. Das [technische Inventar](../guides/repository-technical-function-inventory.md)
zählt 275 Dateien in seinen definierten Produktionspfaden und ergänzt alle
55 seit `ae423f3` hinzugekommenen Dateien.

## Gemergter und installierter Stand

| Stand | Nachweis und Bedeutung |
|---|---|
| Portabilität auf Main | #368–#377 über [#377](https://github.com/joku-dev/devsecops-governance-framework/pull/377), `4fe9586` |
| VM-Testkorrektur | [#387](https://github.com/joku-dev/devsecops-governance-framework/pull/387), `59bc6d1`: Test-Fixtures vom realen Host-Speicher entkoppelt; produktive Speicherreserve unverändert |
| Proxmox-Installation | Am 15. November, 10:59 MEZ auf `59bc6d1` geprüft: Full Validation, aktive Workbench, echte Anmeldung/Datenabfrage/Logout, HTTP 200 und anonyme API 401; Workbench-Backup auf VM und Controller bytegleich |
| Mac daneben | Workbench HTTP 200 während der VM-Prüfung; ursprünglicher Arbeitscheckout erhalten. Das belegt Erreichbarkeit, keine automatische Quellstandsangleichung. |
| Collector auf der VM | Legacy-Engine erhalten; Timer aktiv, keine neue Konfiguration aktiviert. Keine vorhandene Datenbank für eine Sicherung. Sammlung oder portable Betriebsabnahme daraus nicht ableiten. |
| Späterer Main | [#344](https://github.com/joku-dev/devsecops-governance-framework/pull/344), [#347](https://github.com/joku-dev/devsecops-governance-framework/pull/347), [#349](https://github.com/joku-dev/devsecops-governance-framework/pull/349) gemeinsam `4f6f5bb`: Leitfaden und CI-Action-Pins; kein anschließendes VM-Deployment |

Die Betriebsbeobachtung stammt aus dem privaten Deployment-Ergebnis und dessen
geprüften Backups. Private Dateipfade, Schlüssel und Originalprotokolle werden
nicht veröffentlicht. Nach einem späteren Update ist eine neue Beobachtung nötig.

## Abdeckung der automatischen Dokumentationsentwürfe

Diese Zuordnung erfasst ihre Themen im konsolidierten Text. Die Entwürfe bleiben
bis zur Entscheidung über den geprüften Dokumentations-PR eigenständige PRs;
ein Tabellenverweis ist kein Merge und keine Freigabe.

| Dokumentations-PR | Quelländerung | Abdeckung |
|---|---|---|
| #365–#367 | #362 Workbench, #363 IaC, #364 VM-Collector | Workbench-, Installations-, Legacy-Collector-Leitfaden und Inventar |
| #378 | #372 persistenter portabler Collector | Collector-Leitfaden, Engineering-Matrix und Inventar |
| #379 | #369 gemeinsamer Runtime-Kern | Runtime-Leitfaden und Engineering-Matrix |
| #380 | #373 vorbereitetes Offline-Paket | Paket-Leitfaden und Engineering-Matrix |
| #381 | #371 SCM/CI-/Git-Betriebsgrenzen | Operations-Leitfaden und Engineering-Matrix |
| #382 | #370 Evidence-Verifier/Store | Evidence-Intake-Leitfaden und Inventar |
| #383 | #374 Kapazitätsprofil | Kapazitätsleitfaden und offene Lastabnahme |
| #384 | #377 Gesamtabnahme und Recovery | Datierter Plattformstatus, Matrix und Recovery-Runbook |
| #385 | #376 Port-Sitzungsisolation | Workbench- und VM-Anleitung |
| #386 | #375 Provider-Kandidaten | Provider-Assurance-Leitfaden und offene Live-Abnahmen |
| #388 | #344 Fünf-Phasen-Leitfaden | README, Einstiegspunkte und Funktionskatalog |
| #389–#390 | #347 CodeQL, #349 setup-node | Technisches Inventar; Repository-CI, keine neue Governance-Regel |

## Offene nächste Betriebsschritte

GitLab-, Bamboo- und Bitbucket-DC-Versionen sowie Instanz-URLs bleiben offene
Zielprofile. Native Imports, echte Runs und Rollen-/Berechtigungsabnahmen sind
je Profil nachzuweisen. Für den portablen Collector fehlen die reale Migration
bei vorhandenem Legacy-Zustand, mindestens 24 Stunden Shadow mit einem neuen
passenden Default-Branch-Lauf sowie geprüfte Ownership-/Publisher-Umschaltung.
Last-Fixtures ersetzen keine Produktionsabnahme für 1.000–2.000 Repositories.

Die akzeptierten Consumer-Indizes, historischen Trust-Stufen, bestehenden
Baseline-Pins und persönlichen Lifecycle-Abnahmen werden nicht aktualisiert.
[#348](https://github.com/joku-dev/devsecops-governance-framework/pull/348)
bleibt zum Beobachtungszeitpunkt für eine separate Baseline-Referenzprüfung offen.
Die Live-Abfrage am 15. November bestätigt v0.2.0/v0.1.0 als GitHub Releases,
keinen v0.3.0-Tag und den vorhandenen Baseline-Tag v1.2.1. Details im
[Release-Index](../../releases/index.md);
der portable Main-Stand ist kein neuer Release-Tag.
