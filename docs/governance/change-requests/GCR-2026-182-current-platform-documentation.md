# GCR-2026-182 — Dokumentation von Main und VM-Betrieb abgleichen

Date: 2026-11-15. Status: documentation update for review.

## Auftrag und Klassifikation

Der Maintainer beauftragt die Anpassung von README und Dokumentation an den
aktuellen Stand. Gemergte Portabilitäts-/CI-Arbeiten und das ausgeführte VM-Update
werden noch teilweise als ausstehend beschrieben. Dieser Abgleich bindet die
Implementierung an Main `4f6f5bbc2614760a35fe9d79602bcf5b19bc6e74` und die
Betriebsbeobachtung an den separat installierten Commit `59bc6d1`.

| Artifact-intake field | Classification |
|---|---|
| Artefakttyp | Erläuternde Dokumentation und datierter Betriebsabgleich |
| Owner | Governance Platform Maintainers |
| Zielpfade | README, bestehende Einstiegspunkte/Leitfäden, Statusabgleich und MkDocs-Navigation |
| Source Document Intake | Nicht erforderlich; keine normative Quelle oder Registeränderung |
| Governance-/Evidence-Vertrag | Keine Änderung |
| Release-Auswirkung | No release; kein Baseline-/Tag-/Consumer-Update |

## Inhalt und Grenzen

[Abgleich und Entwurfsabdeckung](../../operations/status/repository-documentation-reconciliation-2026-11-15.md):
Mac-/VM-Parallelbetrieb, Installation, getrennte Quellstände und Zustände,
gemergte Runtime-/Verifier-/Collector-/Recovery-Funktionen, 275-Dateien-Inventar,
Fünf-Phasen-Leitfaden und weiterhin offene Provider-/Shadow-/Kapazitätsabnahmen.
Historische Beobachtungen und ihre Inventarstände bleiben datiert erhalten.

Keine Änderung an Quellen, Anforderungen, Policies, Schemas, Statusindizes,
Operating-Acceptance-Fingerprints, veröffentlichten Paketen, Consumer-Pins oder
Enforcement. Kein neues VM-Deployment, keine Collector-Migration oder
Publisher-Aktivierung. Automatische Dokumentationsentwürfe werden zugeordnet;
ihre Schließung bleibt eine getrennte PR-Verwaltungsentscheidung.

## Prüfung

Gepinnter Bootstrap und vollständiges `validate_all.sh`, strenger MkDocs-Build,
exakter Dateimengenabgleich, lokale Link-/Anchorprüfung, geschützte Fingerprints
und `git diff --check`. Revision-bound Governance-Analyst- und abschließender
Repo-Steward-Review als Koordinator-Rollenperspektiven; keine Behauptung
unabhängiger Agenten oder menschlicher Freigabe. Ergebnisse im PR am finalen Commit.
