# GCR-2026-172 — Portability-Goal Version 1.2

## Auftrag und Artefaktklassifikation

Der Maintainer beauftragt am 15. November 2026 die Überarbeitung des analysierten
Portability-Goals um die sechs vereinbarten Präzisierungen. Dieser PR dokumentiert
den technischen Entwicklungsauftrag; er implementiert noch nicht M1 oder M2.

| Feld | Einordnung |
|---|---|
| Artefakte | `AXIOM_Platform_Portability_Codex_Goal.md` Version 1.2 in der Repositorywurzel und dieser Change Request |
| Typ und Ziel | Technischer Entwicklungsauftrag am vorhandenen Rootpfad; Governance-Änderungsdokumentation unter `docs/governance/change-requests/` |
| Owner | Repository Maintainer |
| Full Source Document Intake | Nein; keine normative Quelle, kein Registereintrag und keine Ableitung neuer Controls oder Baselines |
| Integrierte Ausgangslage | `edf16239e9274dbc33f38f204ef80f58c989f969`; PRs #362–#364 zusammengeführt |
| APIs/Evidence/Enforcement | In diesem PR unverändert; neue Verträge und Verhalten bleiben spätere versionierte Implementierung |
| Releases und Akzeptanz | Keine Veröffentlichung oder Änderung historischer Pakete, Tags, Signaturen, Entscheidungen oder Fingerprints |
| Betriebswirkung | Kein VM-Update, keine Credentialänderung, kein Routingwechsel und keine Publisher-/Blocking-Aktivierung |
| Review | Governance-Analyse, anschließend Repo Steward als fokussierte Rollenperspektiven eines Koordinators |
| Validierung | Gepinnter Bootstrap und Gesamtvalidierung, Diff-/Fingerprintprüfung und Dokumentationsprüfung |

## Vereinbarte Präzisierungen

1. Historische Analyse- und VM-Draftreferenzen erhalten; den integrierten Stand
   gesondert benennen und vom tatsächlich beobachteten VM-Stand unterscheiden.
2. Parallelen Mac-/VM-Betrieb mit gleicher fachlicher Bewertung, getrennten
   Sessions/Daten/Credentials und eindeutiger Veröffentlichungszuständigkeit
   ausdrücklich abnehmen.
3. 1.000–2.000 Consumer-Repositories als Kapazitätsziel aufnehmen; synthetische
   Lastprofile, Messwerte und eine spätere reale Kapazitätsfreigabe trennen.
4. Fingerprintgebundene Ledger-/Publikationspfade konkret schützen; neue
   Funktionalität über additive versionierte Nachfolger vorbereiten.
5. GitHub/Actions, GitLab/GitLab CI und Bitbucket Data Center/Bamboo als erste
   Profile festlegen; unbekannte Versionen/Editionen und zusätzliche Kombinationen
   explizit offen führen.
6. Repo-seitigen Abschluss, operative Report-only-Freigabe, Blocking-Abnahme
   und Kapazitätsfreigabe in Akzeptanzmatrix und Abschlusscheckliste trennen.

## Abnahme und Grenzen dieser Überarbeitung

Alle sechs Punkte müssen konsistent in Ausgangslage, Anforderungen,
Arbeitspaketen, Akzeptanzmatrix und Liefercheckliste enthalten sein. Das Goal
bleibt bei M1 vor M2 einschließlich VM-Migration. Geparkte Architektur-Governance
wird nicht wieder aufgenommen. `ready_for_execution` bestätigt keine erledigte
Implementierung und keine operative Freigabe.

Betriebliche Lastannahmen, Grenzwerte sowie unbestätigte GitLab-/Atlassian-Versionen
bleiben als zu klärende Eingaben für die jeweils passende spätere Abnahme sichtbar.
Die ursprüngliche lokale Datei wird bei dieser isolierten Bearbeitung erhalten.
Nur die überarbeitete Kopie und dieser Change Request gehören zur Lieferung.
