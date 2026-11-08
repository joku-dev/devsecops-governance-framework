# GCR-2026-154 — Konsolidierte Beschreibung des aktuellen Repositories

## Anlass und Umfang

Der Maintainer hat die autonome Aktualisierung der Repository-Beschreibung
beauftragt. Die Übersichten beschreiben teilweise den September-/Oktober-Stand,
14 offene automatische Dokumentationsentwürfe überlagern dieselben Textblöcke,
und v0.3.0 wurde vor seiner tatsächlichen Veröffentlichung als Release bezeichnet.

Die Änderung beschreibt den Implementierungsstand `ae423f3` vom 7. November 2026:
private Workbench, explizite Requirement-Extraktion, getrennte historische
Aufzeichnungen, Authority-Grenzen, vollständiges technisches Dateiinventar und
datierte Verbraucher-/Publikationszustände. Der
[Abgleich mit Entwurfsabdeckung](../../operations/status/repository-documentation-reconciliation-2026-11-07.md)
enthält die Zuordnung aller 14 offenen Entwürfe.

## Artifact Intake Classification

| Feld | Einordnung |
|---|---|
| Artefakttyp | documentation |
| Zielpfade | README, bestehende erläuternde Dokumentation, dieser GCR und Abgleich unter `docs/operations/status/` |
| Owner | Governance Platform Maintainers |
| Source Document Intake erforderlich? | no; keine Quelle und keine Registeränderung |
| Evidence-Vertrag | none |
| Governance-Verhalten | documentation-only |
| Release-Auswirkung | none; kein Release erforderlich |

## Auswirkungen und Grenzen

Geändert werden erläuternde Texte und die MkDocs-Navigation. Keine Änderung an
Quellen, Quellprovenienz, Lifecycle-Entscheidungen, kanonischen Anforderungen,
OPA-Verhalten, Schemas, Enforcement, akzeptierten Ergebnissen, Release-Paketen,
Tags, Consumer-Pins oder fingerprintgebundener Operating Acceptance.
Historische Beobachtungen bleiben datiert beziehungsweise über ihren
unveränderlichen Git-Quellstand zugänglich. Der korrigierte Release-Index
veröffentlicht weder v0.3.0 noch eine Baseline.

## Validierung und Review

Vor Commit sind gepinnter Bootstrap und `validate_all.sh`, ein lokaler Demo-Lauf,
`mkdocs build --strict`, Dateimengenabgleich des Inventars und `git diff --check`
auszuführen. Generator-Ausgaben aus der Validierung gehören nur dann in den
Commit, wenn sie zur Dokumentationsänderung gehören. Der PR protokolliert die
Ergebnisse und fordert die bestehende unabhängige Review an.

Nach geprüftem Merge ersetzt dieser Abgleich die 14 zugeordneten
Dokumentationsentwürfe. Sie können mit einem Verweis auf den konsolidierten PR
geschlossen werden; Branch- oder Historienlöschung ist dafür nicht erforderlich.

## Lokale Prüfergebnisse

- Gepinnter Bootstrap erfolgreich; vollständiges `validate_all.sh`: 810 Tests
  bestanden, einschließlich HTTP- und Node-Client-Regressionen.
- Lokaler `run_demo.py` mit gepinntem Python/OPA und OpenSSL 3 erfolgreich.
- `mkdocs build --strict` erfolgreich; lokale Links der geänderten Dokumente
  aufgelöst, technisches Inventar exakt mit 220 eindeutigen Dateien abgeglichen.
- Geänderte Pfade überschneiden sich nicht mit dem Operating-Acceptance-Record.
  Durch die Prüfung erzeugte Berichtsänderungen wurden aus dem Commit entfernt.

Die GitHub-About-Kurzbeschreibung ist im Abgleich vorbereitet. Das bei der
Browserprüfung angemeldete Konto bietet keine Bearbeitung des About-Felds an;
eine Änderung dort wurde deshalb nicht durchgeführt. Die Veröffentlichung der
Repository-Texte folgt der bestehenden unabhängigen PR-Review.
